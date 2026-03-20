# Context: NM i AI 2026 - Task 3 (NorgesGruppen Object Detection)

## 1. Environment & Infrastructure
GCP Project ID: ai-nm26osl-1730
Primary Region: europe-north1 (Finland)
Storage Bucket: gs://ai-nm26osl-1730-nmd-dataset/
Working Directory: ~/nm-ai-2026-1/task3-Norgesgruppen in GCP Cloud Shell.
Constraints: The scoring sandbox uses Python 3.11, prohibits the os module (use pathlib), and requires specific versions of ultralytics (8.1.0) and torch.

## 2. Dataset Structure (Local Cloud Shell)
The data is organized as follows to be YOLOv8-compatible:
```
Text
task3-Norgesgruppen/
├── preprocess.py           # Custom conversion script
└── dataset/
    ├── train/
    │   ├── images/         # 248 shelf JPEG images
    │   ├── labels/         # (Generated) YOLO .txt files
    │   ├── annotations.json # Original COCO format
    │   └── data.yaml       # (Generated) YOLOv8 config file
    └── NM_NGD_product_images/ # 345 folders of product reference photos
```
## 3. Preprocessing Logic (preprocess.py)
We successfully ran a script that performed these critical steps:
- COCO to YOLO Conversion: Converted [x, y, w, h] pixels to normalized [class, x_center, y_center, w, h].
- Direct Category Mapping: To meet competition requirements, we mapped YOLO classes directly to the raw category_id (0-356). This ensures the model predicts the correct IDs for submission without extra lookups.
- Security Compliance: The script uses pathlib for all file operations to align with the competition's security scannerr estrictions.
- Dataset Configuration: Generated data.yaml with nc: 357 and the full list of product names.
## 4. Progress Completed
- Code: preprocess.py has been written and executed.
- Labels: YOLO .txt labels are generated in dataset/train/labels/.
- GCP Config: Cloud Shell project is set to ai-nm26osl-1730.
- Cloud Storage: The bucket gs://ai-nm26osl-1730-nmd-dataset/ was created.
- Data Transfer: Initiated the upload of the 1GB dataset/ folder to the storage bucket via gcloud storage cp.
## 5. Pending Next Steps
- **Provision Training VM**: Create a Compute Engine VM with an NVIDIA L4 GPU to match the competition sandbox environment.
- **Train Model**: SSH into the VM, download the dataset from GCS, and run the training script (`train.py`) to produce `best.pt`.
- **Package Submission**: Create the final `submission.zip` containing `run.py` and the trained `best.pt`.

## 6. Training Plan
- **Environment**: Google Compute Engine VM (`yolo-training-vm`).
- **Instance Type**: `g2-standard-4` with one `NVIDIA L4` GPU.
- **Location**: `europe-north1-a`.
- **Training Script**: `train.py` will be used to train a `YOLOv8l` model.
- **Data Source**: The `dataset/` folder will be copied from GCS to the VM's local disk for faster training I/O.
- **Goal**: Produce a `best.pt` model file to be used by `run.py`.