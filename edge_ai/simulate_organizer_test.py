"""
edge_ai/simulate_organizer_test.py - Simulates Organizer Test Day Scenario
Picks sample test images into a mock 'organizer_drop' folder,
runs batch evaluation, outputs defect statistics, and publishes to MQTT.
Pure English interface without emojis.
"""

import sys
import shutil
import random
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from edge_ai.batch_eval import evaluate_directory

TEST_POOL_DIR = ROOT_DIR / "edge_ai" / "dataset" / "test" / "images"
SIMULATED_DROP_DIR = ROOT_DIR / "runs" / "organizer_test_drop"
SIMULATED_OUTPUT_DIR = ROOT_DIR / "runs" / "organizer_test_annotated"

def simulate_competition_test(sample_size: int = 15):
    print("=" * 65)
    print("  SIMULATING TESA 2026 ORGANIZER EVALUATION SCENARIO")
    print("=" * 65)

    if not TEST_POOL_DIR.exists():
        print(f"Error: Test pool directory does not exist: {TEST_POOL_DIR}")
        sys.exit(1)

    all_images = list(TEST_POOL_DIR.glob("*.jpg"))
    if not all_images:
        print("Error: No images found in test pool.")
        sys.exit(1)

    selected = random.sample(all_images, min(sample_size, len(all_images)))

    # Reset simulated drop folder
    if SIMULATED_DROP_DIR.exists():
        shutil.rmtree(SIMULATED_DROP_DIR)
    SIMULATED_DROP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Simulating Organizer handing over {len(selected)} secret test images...")
    for img in selected:
        shutil.copy2(img, SIMULATED_DROP_DIR / img.name)

    print(f"Images deposited to: {SIMULATED_DROP_DIR}")
    print("\nExecuting Batch Evaluation Pipeline on Raspberry Pi Engine...")

    summary = evaluate_directory(
        input_dir=SIMULATED_DROP_DIR,
        output_dir=SIMULATED_OUTPUT_DIR,
        batch_id="CPN-2026-ORGANIZER-TEST",
        conf_thresh=0.30,
        publish_mqtt=True
    )

    print("\nSimulation completed successfully!")
    print(f"Annotated images saved to: {SIMULATED_OUTPUT_DIR}")
    return summary

if __name__ == "__main__":
    simulate_competition_test()
