import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import torchvision
from PIL import Image


VALID_SUFFIXES = {".jpg", ".jpeg", ".png"}
INPUT_SIZE = (640, 640)  # (height, width)
CONF_THRESHOLD = 0.20
IOU_THRESHOLD = 0.70
MAX_DETECTIONS_PER_IMAGE = 300
ROUND_DIGITS_BBOX = 1
ROUND_DIGITS_SCORE = 4
CLASS_AGNOSTIC_NMS = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def choose_model_path(script_dir: Path) -> Path:
    candidate_names = ("best.onnx", "model.onnx")
    for name in candidate_names:
        candidate = script_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No ONNX model found. Expected best.onnx or model.onnx at zip root.")


def choose_providers() -> list[str]:
    available = set(ort.get_available_providers())
    preferred = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    selected = [provider for provider in preferred if provider in available]
    if not selected:
        selected = ["CPUExecutionProvider"]
    return selected


def parse_image_id(image_path: Path) -> int:
    return int(image_path.stem.split("_")[-1])


def letterbox_pil(image: Image.Image, target_shape: tuple[int, int]) -> tuple[np.ndarray, float, float, float]:
    orig_w, orig_h = image.size
    target_h, target_w = target_shape

    ratio = min(target_w / orig_w, target_h / orig_h)
    new_w = int(round(orig_w * ratio))
    new_h = int(round(orig_h * ratio))

    pad_w = (target_w - new_w) / 2.0
    pad_h = (target_h - new_h) / 2.0

    resized = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
    canvas = Image.new("RGB", (target_w, target_h), (114, 114, 114))
    canvas.paste(resized, (int(round(pad_w)), int(round(pad_h))))

    arr = np.asarray(canvas).astype(np.float32) / 255.0
    arr = np.transpose(arr, (2, 0, 1))[np.newaxis, ...]
    return arr, ratio, pad_w, pad_h


def decode_predictions(raw_output: np.ndarray) -> np.ndarray:
    pred = raw_output[0]
    if pred.ndim != 2:
        return np.empty((0, 6), dtype=np.float32)

    # Typical YOLO ONNX output is channels-first, e.g. (360, 8400).
    if pred.shape[0] < pred.shape[1]:
        pred = pred.T

    if pred.shape[1] <= 4:
        return np.empty((0, 6), dtype=np.float32)

    boxes_xywh = pred[:, :4]
    class_scores = pred[:, 4:]

    class_ids = np.argmax(class_scores, axis=1)
    confidences = np.max(class_scores, axis=1)

    keep_mask = confidences >= CONF_THRESHOLD
    if not np.any(keep_mask):
        return np.empty((0, 6), dtype=np.float32)

    filtered_boxes = boxes_xywh[keep_mask]
    filtered_scores = confidences[keep_mask]
    filtered_classes = class_ids[keep_mask]

    decoded = np.concatenate(
        [
            filtered_boxes.astype(np.float32),
            filtered_scores[:, None].astype(np.float32),
            filtered_classes[:, None].astype(np.float32),
        ],
        axis=1,
    )
    return decoded


def scale_and_clip_boxes(
    boxes_xywh: np.ndarray,
    ratio: float,
    pad_w: float,
    pad_h: float,
    orig_w: int,
    orig_h: int,
) -> np.ndarray:
    xyxy = np.empty_like(boxes_xywh, dtype=np.float32)
    xyxy[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2.0
    xyxy[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2.0
    xyxy[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2.0
    xyxy[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2.0

    # Reverse letterbox padding.
    xyxy[:, [0, 2]] -= pad_w
    xyxy[:, [1, 3]] -= pad_h
    xyxy /= ratio

    xyxy[:, [0, 2]] = np.clip(xyxy[:, [0, 2]], 0, orig_w)
    xyxy[:, [1, 3]] = np.clip(xyxy[:, [1, 3]], 0, orig_h)
    return xyxy


def run_nms(xyxy: np.ndarray, scores: np.ndarray, classes: np.ndarray) -> np.ndarray:
    if len(scores) == 0:
        return np.empty((0,), dtype=np.int64)

    boxes_t = torch.as_tensor(xyxy, dtype=torch.float32)
    scores_t = torch.as_tensor(scores, dtype=torch.float32)
    if CLASS_AGNOSTIC_NMS:
        keep = torchvision.ops.nms(boxes_t, scores_t, IOU_THRESHOLD)
    else:
        classes_t = torch.as_tensor(classes, dtype=torch.float32)
        # Offset boxes by class index to run class-aware NMS in one pass.
        max_wh = 8192.0
        nms_boxes = boxes_t + classes_t[:, None] * max_wh
        keep = torchvision.ops.nms(nms_boxes, scores_t, IOU_THRESHOLD)

    if keep.numel() > MAX_DETECTIONS_PER_IMAGE:
        keep = keep[:MAX_DETECTIONS_PER_IMAGE]
    return keep.cpu().numpy()


def build_json_predictions(
    image_id: int,
    xyxy: np.ndarray,
    scores: np.ndarray,
    classes: np.ndarray,
    keep_indices: np.ndarray,
) -> list[dict]:
    results = []
    for idx in keep_indices:
        x1, y1, x2, y2 = xyxy[idx]
        width = max(0.0, float(x2 - x1))
        height = max(0.0, float(y2 - y1))
        if width <= 0.0 or height <= 0.0:
            continue
        results.append(
            {
                "image_id": image_id,
                "category_id": int(classes[idx]),
                "bbox": [
                    round(float(x1), ROUND_DIGITS_BBOX),
                    round(float(y1), ROUND_DIGITS_BBOX),
                    round(width, ROUND_DIGITS_BBOX),
                    round(height, ROUND_DIGITS_BBOX),
                ],
                "score": round(float(scores[idx]), ROUND_DIGITS_SCORE),
            }
        )
    return results


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input)
    output_path = Path(args.output)
    script_dir = Path(__file__).resolve().parent

    model_path = choose_model_path(script_dir)
    providers = choose_providers()
    session = ort.InferenceSession(str(model_path), providers=providers)
    input_name = session.get_inputs()[0].name

    predictions: list[dict] = []
    for image_path in sorted(input_dir.iterdir()):
        if image_path.suffix.lower() not in VALID_SUFFIXES:
            continue

        image_id = parse_image_id(image_path)
        image = Image.open(image_path).convert("RGB")
        orig_w, orig_h = image.size

        input_tensor, ratio, pad_w, pad_h = letterbox_pil(image, INPUT_SIZE)
        output = session.run(None, {input_name: input_tensor})[0]
        decoded = decode_predictions(output)
        if len(decoded) == 0:
            continue

        boxes_xywh = decoded[:, :4]
        scores = decoded[:, 4]
        classes = decoded[:, 5].astype(np.int32)

        xyxy = scale_and_clip_boxes(boxes_xywh, ratio, pad_w, pad_h, orig_w, orig_h)
        keep = run_nms(xyxy, scores, classes)
        predictions.extend(build_json_predictions(image_id, xyxy, scores, classes, keep))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(predictions, f)


if __name__ == "__main__":
    main()
