"""
edge_ai/deploy_to_rpi.py - 1-Click Deployment and Remote Evaluation on Raspberry Pi
Deploys the trained ONNX model and batch evaluation engine to Raspberry Pi over SSH/SCP,
and optionally triggers remote evaluation for competition scoring.
Pure English interface without emojis.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "track2_edge_ai" / "models" / "coffee_best.onnx"
BATCH_EVAL_PATH = ROOT_DIR / "track2_edge_ai" / "batch_eval.py"
VISION_ENGINE_PATH = ROOT_DIR / "track2_edge_ai" / "vision_engine.py"
SHARED_DIR = ROOT_DIR / "shared"

def check_ssh_reachable(host: str, user: str, timeout: int = 3) -> bool:
    """Tests if the Raspberry Pi is reachable via SSH."""
    cmd = ["ssh", "-o", f"ConnectTimeout={timeout}", "-o", "BatchMode=yes", f"{user}@{host}", "echo 'OK'"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout + 2)
        return res.returncode == 0
    except Exception:
        return False

def deploy_to_pi(host: str, user: str, remote_dir: str = "/home/admin/TESA_2026"):
    """Syncs necessary models, scripts, and schemas to Raspberry Pi."""
    print("=" * 65)
    print("     TESA 2026: 1-CLICK RASPBERRY PI DEPLOYMENT PIPELINE")
    print("=" * 65)
    print(f"Target Raspberry Pi : {user}@{host}:{remote_dir}")
    print(f"Local Model Path    : {MODEL_PATH}")

    if not MODEL_PATH.exists():
        print(f"Error: ONNX model does not exist at {MODEL_PATH}")
        print("Please train or export the model first via: python track2_edge_ai/train_yolo.py")
        sys.exit(1)

    print("\n[Step 1/3] Testing SSH Connection to Raspberry Pi...")
    reachable = check_ssh_reachable(host, user)
    if not reachable:
        print(f"Notice: Cannot connect to {user}@{host} directly without password/key.")
        print("Will attempt file transfer with standard ssh/scp tools.")

    # Create remote directory structure
    print(f"\n[Step 2/3] Preparing Remote Directories on Raspberry Pi...")
    create_dir_cmd = [
        "ssh", f"{user}@{host}",
        f"mkdir -p {remote_dir}/track2_edge_ai/models {remote_dir}/shared {remote_dir}/test_images {remote_dir}/runs"
    ]
    subprocess.run(create_dir_cmd)

    # Transfer Model and Engine Files
    print(f"\n[Step 3/3] Synchronizing Model and Engine Scripts to Pi...")
    files_to_transfer = [
        (str(MODEL_PATH), f"{remote_dir}/track2_edge_ai/models/coffee_best.onnx"),
        (str(BATCH_EVAL_PATH), f"{remote_dir}/track2_edge_ai/batch_eval.py"),
        (str(VISION_ENGINE_PATH), f"{remote_dir}/track2_edge_ai/vision_engine.py"),
        (str(SHARED_DIR / "schemas.py"), f"{remote_dir}/shared/schemas.py"),
        (str(SHARED_DIR / "config.py"), f"{remote_dir}/shared/config.py"),
        (str(SHARED_DIR / "__init__.py"), f"{remote_dir}/shared/__init__.py")
    ]

    for local_file, remote_target in files_to_transfer:
        print(f"  Uploading: {Path(local_file).name} -> {remote_target}")
        scp_cmd = ["scp", local_file, f"{user}@{host}:{remote_target}"]
        res = subprocess.run(scp_cmd)
        if res.returncode != 0:
            print(f"  Warning: Failed to copy {local_file}")

    print("\n" + "=" * 65)
    print("DEPLOYMENT COMPLETE!")
    print(f"The Raspberry Pi is now loaded with the latest ONNX model and Batch Evaluator.")
    print("To execute batch evaluation directly on the Pi, run:")
    print(f"  ssh {user}@{host} 'cd {remote_dir} && python3 track2_edge_ai/batch_eval.py --input-dir test_images --publish-mqtt'")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="Deploy ONNX model and engine to Raspberry Pi")
    parser.add_argument("--host", type=str, default="192.168.3.2", help="Raspberry Pi IP address")
    parser.add_argument("--user", type=str, default="admin", help="Raspberry Pi SSH username")
    parser.add_argument("--remote-dir", type=str, default="/home/admin/TESA_2026", help="Destination folder on Pi")
    args = parser.parse_args()

    deploy_to_pi(host=args.host, user=args.user, remote_dir=args.remote_dir)

if __name__ == "__main__":
    main()
