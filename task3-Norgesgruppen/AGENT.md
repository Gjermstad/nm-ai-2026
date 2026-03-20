# Context: NM i AI 2026 - Task 3 (NorgesGruppen Object Detection)

## 1. Environment & Infrastructure
- GCP Project ID: ai-nm26osl-1730
- Primary Region: europe-north1 (Finland) — for Cloud Run only
- Storage Bucket: gs://ai-nm26osl-1730-nmd-dataset/
- Training VM: yolo-training-vm, zone: europe-west1-c (NOT europe-west1-b!)
- Working Directory on VM: ~/nm-ai-2026/task3-Norgesgruppen
- Repo: https://github.com/Gjermstad/nm-ai-2026
- Constraints: Scoring sandbox uses Python 3.11, prohibits os module (use pathlib), requires ultralytics==8.1.0 and torch==2.6.0

## 2. Current Submission Status
- Score: 0.1786 mAP — Rank #157
- Submission: ONNX-based run.py + best.onnx (138.2 MB)
- Top of leaderboard: ~0.92 mAP (fine-tuned models)
- Gap is due to ONNX output parsing — classification may be off
- 4 submissions remaining today

## 3. Dataset Structure (on Training VM)
task3-Norgesgruppen/
├── preprocess.py
├── train.py
├── run.py              # ONNX inference (current working version)
├── best.onnx           # 167.6 MB — used in submission
├── best_stripped.pt    # 84 MB FP16 — NOT used (caused exit code 1)
└── dataset/
    ├── train/
    │   ├── images/         # 248 shelf JPEG images
    │   ├── labels/         # YOLO .txt files
    │   ├── annotations.json
    │   └── data.yaml       # Uses absolute paths (see section 5)
    ├── annotations.json
    └── NM_NGD_product_images/

## 4. Trained Model
- Architecture: YOLOv8l (large), nc=356
- Epochs: 50, completed in 0.364 hours (~22 min)
- Final mAP50: 0.481, mAP50-95: 0.331
- best.pt location: runs/detect/yolov8l_norgesgruppen_final/weights/best.pt (504 MB)
- best.onnx: exported with opset=17, half=False (167.6 MB)

## 5. Current run.py (ONNX-based — WORKING)
Uses onnxruntime with CUDAExecutionProvider fallback to CPU.
Key logic:
- Loads best.onnx
- Resizes images to 640x640
- Parses output shape (1, 360, 8400): first 4 rows = boxes, rest = class scores
- Scales boxes back to original image dimensions
- Confidence threshold: 0.25

## 6. Critical Fixes Applied
1. Training VM is in europe-west1-c (L4 not available in europe-north1)
2. train.py: data='dataset/train/data.yaml'
3. ultralytics patch for torch 2.6.0:
   sed -i 's/torch.load(file, map_location="cpu")/torch.load(file, map_location="cpu", weights_only=False)/' \
   /opt/conda/lib/python3.10/site-packages/ultralytics/nn/tasks.py
4. data.yaml must use absolute path:
   path: /home/devstar17301/nm-ai-2026/task3-Norgesgruppen/dataset/train
   train: images
   val: images
   nc: 356
5. numpy must stay at 1.26.4:
   pip install "numpy<2" --force-reinstall --no-deps
6. ray uninstalled to fix raytune callback crash after epoch 1:
   pip uninstall ray -y

## 7. How to Repackage and Submit
On training VM:
```
  cd ~/nm-ai-2026/task3-Norgesgruppen
  zip -j ~/submission.zip run.py best.onnx
```
In Cloud Shell:
  `gcloud compute scp yolo-training-vm:~/submission.zip ~/submission.zip --zone=europe-west1-c`

Download from Cloud Shell (⋮ menu → Download) and submit at app.ainm.no.
Use incognito window if upload gives network error.

## 8. Potential Improvements (ranked by impact)
1. Fix ONNX output parsing — verify box decoding is correct (may explain low score)
2. Retrain with more epochs (100+) or larger batch size
3. Use YOLOv8x (extra large) for better accuracy
4. Add NMS (non-maximum suppression) post-processing to ONNX output
5. Use the ultralytics .pt directly if torch.load patch holds in sandbox

## 9. Submission Format Reminder
- run.py must be at zip root
- Output: predictions.json as JSON array with image_id, category_id, bbox [x,y,w,h], score
- Scoring: 70% detection mAP + 30% classification mAP
- Sandbox: Python 3.11, NVIDIA L4, CUDA 12.4, no network, 300s timeout
- Max zip: 420 MB uncompressed
- Blocked imports: os, sys, subprocess, socket — use pathlib instead
- Daily quota: 6 submissions, max 2 in-flight
