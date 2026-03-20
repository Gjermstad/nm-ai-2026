import json
from collections import defaultdict
from pathlib import Path

# --- Configuration ---
JSON_FILE = Path("annotations.json")
OUTPUT_LABELS_DIR = Path("labels")
DATA_YAML_FILE = Path("data.yaml")

def main():
    # 1. Create the output directory using pathlib (os module is banned in sandbox)
    OUTPUT_LABELS_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Load the COCO JSON data
    print(f"Loading {JSON_FILE}...")
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 3. Extract Categories 
    # The docs specify category_ids are 0 to 356. We will use these EXACT IDs 
    # so the YOLO predictions perfectly match the submission requirements.
    # We find the max category_id to properly pad the names array in data.yaml
    max_cat_id = max(cat["id"] for cat in data.get("categories",[])) if "categories" in data else 356
    
    # Create a list for YOLO names where the index directly matches the category_id
    yolo_names = ["unknown"] * (max_cat_id + 1)
    if "categories" in data:
        for cat in data["categories"]:
            yolo_names[cat["id"]] = cat["name"]
    else:
        # Fallback if no categories block exists in your snippet
        for cid in range(max_cat_id + 1):
            yolo_names[cid] = f"class_{cid}"

    # 4. Map image_id to image info
    images_info = {img["id"]: img for img in data["images"]}

    # 5. Group annotations by image_id
    image_annotations = defaultdict(list)
    for ann in data["annotations"]:
        image_annotations[ann["image_id"]].append(ann)

    # 6. Convert and save labels
    print("Converting bounding boxes to YOLO format...")
    for image_id, img in images_info.items():
        # Get filename without extension (e.g., "img_00001")
        base_name = Path(img["file_name"]).stem
        label_path = OUTPUT_LABELS_DIR / f"{base_name}.txt"
        
        img_w = img["width"]
        img_h = img["height"]

        lines =[]
        for ann in image_annotations.get(image_id,[]):
            # USE RAW CATEGORY ID directly!
            yolo_class_idx = ann["category_id"] 
            
            # COCO format:[x_min, y_min, width, height]
            x_min, y_min, box_w, box_h = ann["bbox"]

            # YOLO format:[x_center, y_center, width, height] (Normalized 0.0 to 1.0)
            x_center = (x_min + box_w / 2.0) / img_w
            y_center = (y_min + box_h / 2.0) / img_h
            norm_w = box_w / img_w
            norm_h = box_h / img_h

            # Clip values to[0, 1] to prevent YOLO training errors on out-of-bounds boxes
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            norm_w = max(0.0, min(1.0, norm_w))
            norm_h = max(0.0, min(1.0, norm_h))

            # Format to 6 decimal places
            lines.append(f"{yolo_class_idx} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}")

        # Write to .txt file
        with open(label_path, "w", encoding="utf-8") as f:
            if lines:
                f.write("\n".join(lines) + "\n")

    # 7. Generate data.yaml for YOLOv8
    print(f"Generating {DATA_YAML_FILE}...")
    
    yaml_content = "path: .\n"
    yaml_content += "train: images\n"
    yaml_content += "val: images  # Change this to your validation folder if you create a split\n\n"
    
    # Explicitly set nc=357 as requested by the documentation
    yaml_content += f"nc: {len(yolo_names)}\n"
    yaml_content += "names:\n"
    for idx, name in enumerate(yolo_names):
        # Escape single quotes in product names (e.g., if a name has an apostrophe)
        safe_name = name.replace("'", "''")
        yaml_content += f"  {idx}: '{safe_name}'\n"

    with open(DATA_YAML_FILE, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print("---")
    print("✅ Conversion complete!")
    print(f"   • Labels saved to: {OUTPUT_LABELS_DIR}/")
    print(f"   • Dataset config:  {DATA_YAML_FILE}")

if __name__ == "__main__":
    main()