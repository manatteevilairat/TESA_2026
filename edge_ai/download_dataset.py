"""
edge_ai/download_dataset.py
Automated Dataset Downloader and Structure Verifier for YOLOv8.
Pure English interface without emojis.
"""

import os
import sys
import shutil
import zipfile
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "edge_ai" / "dataset"


def verify_dataset_structure(dataset_path: Path) -> bool:
    """Verifies that the dataset contains data.yaml and standard train/val folders."""
    if not dataset_path.exists():
        print(f"Error: Dataset directory does not exist: {dataset_path}")
        return False

    yaml_candidates = list(dataset_path.glob("*.yaml")) + list(dataset_path.glob("data.yml"))
    if not yaml_candidates:
        print(f"Error: No data.yaml found inside {dataset_path}")
        return False

    yaml_file = yaml_candidates[0]
    print(f"Verified data configuration file: {yaml_file}")

    train_candidates = [dataset_path / "train", dataset_path / "train" / "images"]
    valid_candidates = [dataset_path / "valid", dataset_path / "val", dataset_path / "valid" / "images"]

    has_train = any(p.exists() for p in train_candidates)
    has_valid = any(p.exists() for p in valid_candidates)

    print(f"Train split detected: {has_train}")
    print(f"Validation split detected: {has_valid}")

    return has_train and has_valid


def download_with_roboflow_sdk(api_key: str, workspace: str, project_id: str, version: int = 1):
    """Downloads dataset directly via Roboflow Python SDK."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("Roboflow library not installed. Run: uv add roboflow")
        return False

    print(f"Connecting to Roboflow Workspace: '{workspace}', Project: '{project_id}', Version: {version}...")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace(workspace).project(project_id)
    version_obj = project.version(version)

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    dataset = version_obj.download("yolov8", location=str(DATASET_DIR))
    print(f"Dataset successfully downloaded to: {DATASET_DIR}")
    return verify_dataset_structure(DATASET_DIR)


def extract_zip(zip_path: str):
    """Extracts a manually downloaded Roboflow YOLOv8 zip file."""
    src = Path(zip_path)
    if not src.exists():
        print(f"Error: Zip file not found at: {src}")
        return False

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {src} to {DATASET_DIR}...")
    with zipfile.ZipFile(src, 'r') as zf:
        zf.extractall(DATASET_DIR)

    print("Extraction completed.")
    return verify_dataset_structure(DATASET_DIR)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coffee Bean YOLOv8 Dataset Downloader")
    parser.add_argument("--zip", type=str, help="Path to downloaded Roboflow YOLOv8 .zip archive")
    parser.add_argument("--api-key", type=str, help="Roboflow User API Key")
    parser.add_argument("--workspace", type=str, default="coffee-beans-ixp8d", help="Roboflow Workspace name")
    parser.add_argument("--project", type=str, default="robusta-coffee-bean-defects-hatuw", help="Roboflow Project ID")
    parser.add_argument("--version", type=int, default=1, help="Dataset version number")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing dataset directory")

    args = parser.parse_args()

    if args.verify_only:
        valid = verify_dataset_structure(DATASET_DIR)
        sys.exit(0 if valid else 1)

    if args.zip:
        success = extract_zip(args.zip)
        sys.exit(0 if success else 1)

    if args.api_key:
        success = download_with_roboflow_sdk(args.api_key, args.workspace, args.project, args.version)
        sys.exit(0 if success else 1)

    print("Usage Instructions:")
    print("Option 1: If you downloaded a .zip from Roboflow Universe:")
    print("  uv run edge_ai/download_dataset.py --zip ~/Downloads/your_dataset.zip\n")
    print("Option 2: If you have a Roboflow API Key:")
    print("  uv run edge_ai/download_dataset.py --api-key YOUR_KEY\n")
    print("Option 3: Verify existing dataset folder:")
    print("  uv run edge_ai/download_dataset.py --verify-only\n")
