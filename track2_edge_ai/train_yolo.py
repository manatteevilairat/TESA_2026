"""
edge_ai/train_yolo.py
End-to-End Training and ONNX Export Pipeline for YOLOv8n (Coffee Bean Detection).
Optimized for Apple Silicon M-series GPU (MPS) training and Raspberry Pi 5 CPU deployment.
Pure English interface without emojis.
"""

import sys
import os
import shutil
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT_DIR / "track2_edge_ai" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def detect_best_device() -> str:
    """Detects available hardware accelerator: Apple Silicon MPS, NVIDIA CUDA, or CPU."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "0"
    except Exception:
        pass
    return "cpu"


def find_dataset_yaml(preferred_path: str = None) -> Path:
    """Locates the dataset data.yaml file."""
    if preferred_path and Path(preferred_path).exists():
        return Path(preferred_path)

    # Check downloaded real dataset first
    real_dataset = ROOT_DIR / "track2_edge_ai" / "dataset" / "data.yaml"
    if real_dataset.exists():
        return real_dataset

    # Check sample dataset fallback
    sample_dataset = ROOT_DIR / "track2_edge_ai" / "sample_dataset" / "data.yaml"
    if sample_dataset.exists():
        return sample_dataset

    raise FileNotFoundError("Could not find data.yaml in track2_edge_ai/dataset/ or track2_edge_ai/sample_dataset/")


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 Training and ONNX Export Pipeline")
    parser.add_argument("--data", type=str, default=None, help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs (default: 30)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--imgsz", type=int, default=320, help="Image resolution: 320 or 416 recommended for RPi 5 CPU")
    parser.add_argument("--device", type=str, default=None, help="'mps', 'cpu', or CUDA device ID (auto-detected if omitted)")
    parser.add_argument("--name", type=str, default="coffee_yolo_run", help="Experiment run name")
    parser.add_argument("--export-only", type=str, default=None, help="Skip training and export existing .pt weights to ONNX")

    args = parser.parse_args()

    selected_device = args.device or detect_best_device()
    print("=" * 70)
    print("TESA TOP GUN RALLY 2026: COFFEE BEAN YOLOv8 TRAINING PIPELINE")
    print("=" * 70)
    print(f"Target Hardware for Deployment : Raspberry Pi 5 (CPU multi-threading)")
    print(f"Training Accelerator Detected  : {selected_device.upper()}")
    print(f"Target Input Resolution        : {args.imgsz}x{args.imgsz} (Optimized for edge latency)")
    print(f"Epochs                         : {args.epochs}")
    print(f"Batch Size                     : {args.batch}")
    print("=" * 70)

    from ultralytics import YOLO

    # Export-only mode
    if args.export_only:
        pt_path = Path(args.export_only)
        if not pt_path.exists():
            print(f"Error: Weights file does not exist: {pt_path}")
            sys.exit(1)
        print(f"Exporting existing weights {pt_path} to ONNX format...")
        model = YOLO(str(pt_path))
        exported_path = model.export(format="onnx", imgsz=args.imgsz, dynamic=False, simplify=True)
        dest_onnx = MODELS_DIR / "coffee_best.onnx"
        shutil.copyfile(exported_path, dest_onnx)
        print(f"ONNX Model saved to: {dest_onnx}")
        sys.exit(0)

    # Resolve dataset YAML
    data_yaml = find_dataset_yaml(args.data)
    print(f"Dataset Configuration : {data_yaml}")

    # Load Nano base model (yolov8n.pt ~6.2MB)
    print("\nLoading Pre-trained Base Architecture: yolov8n.pt...")
    model = YOLO("yolov8n.pt")

    # Start Fine-tuning
    print("\nStarting Model Fine-tuning...")
    results = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=selected_device,
        project="edge_ai/runs",
        name=args.name,
        exist_ok=True,
        plots=True,
        save=True
    )

    print("\nTraining Phase Completed.")

    # Validation
    print("\nEvaluating Best Model Checkpoint...")
    val_results = model.val()

    # Locate best.pt
    run_dir = Path("edge_ai/runs") / args.name
    best_pt = run_dir / "weights" / "best.pt"
    if not best_pt.exists():
        # Fallback to default ultralytics run path
        best_pt = Path(model.trainer.save_dir) / "weights" / "best.pt"

    print(f"Best PyTorch Checkpoint: {best_pt}")

    # Export to ONNX for Raspberry Pi 5 CPU Deployment
    print(f"\nExporting Model to ONNX format (Resolution: {args.imgsz}x{args.imgsz}, Non-dynamic)...")
    exported_onnx = model.export(
        format="onnx",
        imgsz=args.imgsz,
        dynamic=False,
        simplify=True,
        opset=12
    )

    dest_onnx = MODELS_DIR / "coffee_best.onnx"
    shutil.copyfile(exported_onnx, dest_onnx)

    file_size_mb = dest_onnx.stat().st_size / (1024 * 1024)
    print("=" * 70)
    print("TRAINING AND DEPLOYMENT PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Deployed ONNX Model : {dest_onnx} ({file_size_mb:.2f} MB)")
    print(f"PyTorch Weights     : {best_pt}")
    print(f"Metrics & Plots     : {run_dir}")
    print("\nThe ONNX model is now ready for Raspberry Pi 5 CPU inference via edge_ai/vision_engine.py.")
    print("=" * 70)


if __name__ == "__main__":
    main()
