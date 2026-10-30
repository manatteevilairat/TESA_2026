"""
edge_ai/batch_eval.py - TESA 2026 Official Batch Image Evaluation Pipeline
Performs offline and high-throughput batch inspection on image folders provided by competition organizers.
Extracts 7-class bean statistics, computes Primary vs Secondary defects, assigns Robusta grades,
outputs annotated visualization frames, and publishes summary telemetry via MQTT.
Pure English interface without emojis.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import cv2
import numpy as np
from shared.config import (
    DEFAULT_ONNX_MODEL,
    DEFAULT_TEST_IMAGES,
    ROBUSTA_CLASSES,
    PRIMARY_DEFECT_CLASSES,
    SECONDARY_DEFECT_CLASSES,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT
)
from shared.schemas import VisionData, DefectCounts
from edge_ai.vision_engine import CoffeeVisionAnalyzer

def evaluate_directory(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    batch_id: str = "CPN-2026-BATCH",
    conf_thresh: float = 0.30,
    iou_thresh: float = 0.45,
    threads: int = 4,
    publish_mqtt: bool = False,
    broker_host: str = MQTT_BROKER_HOST
) -> Dict[str, Any]:
    """Runs batch inference across all images in input_dir and aggregates defect metrics."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
    image_paths: List[Path] = []
    for ext in image_extensions:
        image_paths.extend(input_dir.glob(ext))
    image_paths.sort()

    if not image_paths:
        raise ValueError(f"No valid image files found in {input_dir}")

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = CoffeeVisionAnalyzer(model_path=str(DEFAULT_ONNX_MODEL), threads=threads)

    class_totals: Dict[str, int] = {c: 0 for c in ROBUSTA_CLASSES}
    image_results: List[Dict[str, Any]] = []

    start_total_time = time.time()
    inference_latencies = []

    print(f"============================================================")
    print(f"Starting TESA 2026 Batch Evaluation")
    print(f"Batch Identifier : {batch_id}")
    print(f"Input Directory  : {input_dir} ({len(image_paths)} images)")
    print(f"Output Directory : {output_dir or 'Disabled'}")
    print(f"Confidence Level : {conf_thresh:.2f} | IoU: {iou_thresh:.2f}")
    print(f"============================================================")

    for idx, img_path in enumerate(image_paths, start=1):
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue

        t0 = time.time()
        detected_classes, annotated = analyzer.analyze_frame_onnx(
            frame, conf_thresh=conf_thresh, iou_thresh=iou_thresh
        )
        dt = time.time() - t0
        inference_latencies.append(dt)

        img_class_counts: Dict[str, int] = {c: 0 for c in ROBUSTA_CLASSES}
        for c in detected_classes:
            matched = False
            for target_class in ROBUSTA_CLASSES:
                if target_class.lower() in c.lower():
                    img_class_counts[target_class] += 1
                    class_totals[target_class] += 1
                    matched = True
                    break
            if not matched:
                class_totals["Broken"] += 1
                img_class_counts["Broken"] += 1

        if output_dir:
            out_img_path = output_dir / f"annotated_{img_path.name}"
            cv2.imwrite(str(out_img_path), annotated)
            if idx == 1:
                cv2.imwrite(str(ROOT_DIR / "shared" / "latest_vision.jpg"), annotated)

        image_results.append({
            "filename": img_path.name,
            "latency_ms": round(dt * 1000, 2),
            "beans_detected": len(detected_classes),
            "counts": img_class_counts
        })

        if idx % 10 == 0 or idx == len(image_paths):
            fps = 1.0 / max(0.001, np.mean(inference_latencies))
            print(f"[{idx:>3}/{len(image_paths)}] Processed {img_path.name:<25} | Detected: {len(detected_classes):>2} beans | Avg FPS: {fps:.2f}")

    total_processing_time = time.time() - start_total_time
    total_beans = sum(class_totals.values())
    good_beans = class_totals.get("Good bean", 0)
    total_defects = total_beans - good_beans

    primary_defect_count = sum(class_totals.get(c, 0) for c in PRIMARY_DEFECT_CLASSES)
    secondary_defect_count = sum(class_totals.get(c, 0) for c in SECONDARY_DEFECT_CLASSES)

    defect_rate_pct = round((total_defects / max(1, total_beans)) * 100, 2)
    primary_rate_pct = round((primary_defect_count / max(1, total_beans)) * 100, 2)

    # Official Chumphon Robusta Grading Rubric
    if defect_rate_pct <= 3.0 and primary_defect_count == 0:
        grade = "FINE_ROBUSTA"
        grade_desc = "Chumphon Fine Robusta (Specialty Grade)"
        estimated_fair_price = 320.0
    elif defect_rate_pct <= 6.0 and primary_rate_pct <= 1.0:
        grade = "PREMIUM"
        grade_desc = "Premium Robusta (Grade 1 High Commercial)"
        estimated_fair_price = 230.0
    elif defect_rate_pct <= 14.0:
        grade = "COMMERCIAL_GRADE"
        grade_desc = "Commercial Robusta (Standard Market Grade)"
        estimated_fair_price = 145.0
    else:
        grade = "REJECT"
        grade_desc = "Off-Grade / Reject (Defect Exceeds Standard)"
        estimated_fair_price = 65.0

    defects_schema = DefectCounts(
        black_beans=class_totals.get("Black", 0),
        broken_beans=class_totals.get("Broken", 0),
        empty_beans=class_totals.get("Empty", 0),
        insect_beans=class_totals.get("Insect damage", 0),
        unripe_beans=class_totals.get("Quaker", 0),
        scorched_beans=class_totals.get("Scorched", 0)
    )

    summary = {
        "batch_id": batch_id,
        "total_images": len(image_paths),
        "total_beans_detected": total_beans,
        "healthy_beans": good_beans,
        "total_defects": total_defects,
        "defect_rate_pct": defect_rate_pct,
        "primary_defects_count": primary_defect_count,
        "secondary_defects_count": secondary_defect_count,
        "grade": grade,
        "grade_description": grade_desc,
        "estimated_fair_price_thb": estimated_fair_price,
        "class_breakdown": class_totals,
        "average_latency_ms": round(float(np.mean(inference_latencies)) * 1000, 2),
        "throughput_fps": round(1.0 / float(np.mean(inference_latencies)), 2),
        "total_runtime_seconds": round(total_processing_time, 2),
        "detailed_images": image_results
    }

    print("\n" + "=" * 60)
    print("                BATCH EVALUATION SUMMARY REPORT")
    print("=" * 60)
    print(f"Batch Identifier       : {batch_id}")
    print(f"Total Evaluated Images : {len(image_paths)}")
    print(f"Total Beans Inspected  : {total_beans}")
    print(f"Healthy Beans (Good)   : {good_beans} ({(good_beans/max(1,total_beans)*100):.1f}%)")
    print(f"Total Defects Detected : {total_defects} ({defect_rate_pct:.1f}%)")
    print("-" * 60)
    print("DEFECT BREAKDOWN BY CLASS:")
    for c in ROBUSTA_CLASSES:
        cnt = class_totals[c]
        tag = " [PRIMARY]" if c in PRIMARY_DEFECT_CLASSES else (" [SECONDARY]" if c in SECONDARY_DEFECT_CLASSES else "")
        print(f"  - {c:<16}: {cnt:>4} beans ({cnt/max(1,total_beans)*100:>5.1f}%){tag}")
    print("-" * 60)
    print(f"Assigned Robusta Grade : {grade} ({grade_desc})")
    print(f"Fair Intrinsic Value   : {estimated_fair_price:.2f} THB/kg")
    print(f"Mean Latency Per Frame : {summary['average_latency_ms']} ms ({summary['throughput_fps']} FPS)")
    print("=" * 60)

    if publish_mqtt:
        try:
            import paho.mqtt.client as mqtt
            import base64
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="batch_evaluator")
            client.connect(broker_host, MQTT_BROKER_PORT, 60)
            client.loop_start()

            img_b64 = None
            if output_dir:
                sample_annotated = sorted(list(output_dir.glob("*.jpg")))
                if sample_annotated:
                    with open(sample_annotated[0], "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode("utf-8")

            vision_data = VisionData(
                device_id="batch_eval_engine",
                batch_id=batch_id,
                timestamp=time.time(),
                sample_count=total_beans,
                defects=defects_schema,
                defect_rate_pct=defect_rate_pct,
                primary_grade=grade,
                image_annotated_url=str(output_dir) if output_dir else None,
                image_base64=img_b64
            )

            topic = f"tgr2026/coffee/{batch_id}/vision"
            client.publish(topic, vision_data.model_dump_json())
            time.sleep(0.5)
            client.loop_stop()
            client.disconnect()
            print(f"Successfully published batch summary to MQTT: {topic}")
        except Exception as e:
            print(f"Notice: Failed to publish MQTT telemetry ({e})")

    return summary


def main():
    parser = argparse.ArgumentParser(description="TESA 2026 Batch Image Evaluation Pipeline")
    parser.add_argument("--input-dir", type=str, default=str(DEFAULT_TEST_IMAGES), help="Path to input images directory")
    parser.add_argument("--output-dir", type=str, default=str(ROOT_DIR / "runs" / "batch_eval_output"), help="Path to output annotated images")
    parser.add_argument("--batch-id", type=str, default="CPN-2026-CHAMPION", help="Coffee batch identifier")
    parser.add_argument("--export-json", type=str, default=str(ROOT_DIR / "shared" / "batch_report.json"), help="Output JSON report file")
    parser.add_argument("--conf", type=float, default=0.30, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold for NMS")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads for ONNX Runtime")
    parser.add_argument("--broker", type=str, default=MQTT_BROKER_HOST, help="MQTT Broker host")
    parser.add_argument("--publish-mqtt", action="store_true", help="Publish summary to MQTT broker")
    args = parser.parse_args()

    summary = evaluate_directory(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        batch_id=args.batch_id,
        conf_thresh=args.conf,
        iou_thresh=args.iou,
        threads=args.threads,
        publish_mqtt=args.publish_mqtt,
        broker_host=args.broker
    )

    if args.export_json:
        export_path = Path(args.export_json)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"Saved complete evaluation report to: {export_path}")


if __name__ == "__main__":
    main()
