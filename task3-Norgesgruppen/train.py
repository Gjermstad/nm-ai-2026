from ultralytics import YOLO
import torch
import os

def main():
    """
    Main training script for the YOLOv8 model on the NorgesGruppen dataset.
    """
    # 1. Verify GPU is available
    print(f"CUDA available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("CUDA not available. Training on CPU will be very slow.")
        return
    
    print(f"Device count: {torch.cuda.device_count()}")
    print(f"Current device: {torch.cuda.current_device()}")
    print(f"Device name: {torch.cuda.get_device_name(0)}")

    # 2. Load a pretrained YOLOv8 model
    # We use a larger model (yolov8l.pt) for better accuracy, feasible on the L4 GPU.
    model = YOLO('yolov8l.pt')

    # 3. Train the model
    # The data.yaml file is inside the 'dataset' directory, which we'll download from GCS.
    # The 'name' parameter determines the output directory for the trained model.
    results = model.train(
        data='dataset/data.yaml',
        epochs=50,          # A good starting point, can be adjusted.
        imgsz=640,          # Standard input size for YOLOv8.
        batch=8,            # Adjust based on VRAM; 8 should be fine for a 24GB L4 GPU.
        name='yolov8l_norgesgruppen_final',
        exist_ok=True,
    )

    print(f"Training complete. Best model saved at: {results.save_dir}/weights/best.pt")

if __name__ == '__main__':
    main()

