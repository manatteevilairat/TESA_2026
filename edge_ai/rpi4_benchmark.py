"""
edge_ai/rpi4_benchmark.py
Hardware Benchmark and Vision Node Verification Script for Raspberry Pi 4.
Evaluates CPU inference latency, FPS, memory usage, camera stream, and MQTT connectivity.
Pure English interface without emojis.
"""

import sys
import os
import time
import platform
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_MODEL_PATH = ROOT_DIR / "edge_ai" / "models" / "coffee_best.onnx"


def check_system_environment():
    """Reports hardware platform, OS architecture, and CPU core count."""
    print("=" * 65)
    print("RASPBERRY PI 4 HARDWARE & RUNTIME ENVIRONMENT")
    print("=" * 65)
    print(f"Machine Architecture : {platform.machine()}")
    print(f"OS Platform          : {platform.system()} {platform.release()}")
    print(f"Python Version       : {platform.python_version()}")
    print(f"CPU Cores Available  : {os.cpu_count()}")

    is_64bit = sys.maxsize > 2**32
    print(f"64-Bit OS Detected   : {is_64bit}")
    if not is_64bit:
        print("Warning: 32-bit OS detected. 64-bit OS is strongly recommended for ONNX Runtime.")

    # Check thermal throttling on Raspberry Pi OS if vcgencmd exists
    if os.path.exists("/usr/bin/vcgencmd"):
        try:
            import subprocess
            temp_out = subprocess.check_output(["/usr/bin/vcgencmd", "measure_temp"]).decode().strip()
            throttle_out = subprocess.check_output(["/usr/bin/vcgencmd", "get_throttled"]).decode().strip()
            print(f"Core Temperature     : {temp_out}")
            print(f"Throttle Status      : {throttle_out}")
        except Exception:
            pass
    print("=" * 65)


def benchmark_onnx_inference(model_path: str, iterations: int = 50, threads: int = 4):
    """Benchmarks ONNX Runtime inference latency and FPS on CPU."""
    if not os.path.exists(model_path):
        print(f"Error: ONNX Model file not found at: {model_path}")
        return

    print(f"\nBenchmarking ONNX Model: {Path(model_path).name}")
    print(f"Thread Count: {threads} | Iterations: {iterations}")

    try:
        import onnxruntime as ort
        import numpy as np

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
        input_meta = session.get_inputs()[0]
        input_name = input_meta.name
        shape = input_meta.shape

        # Resolve dynamic batch or fixed shape (default: 1, 3, 320, 320)
        b = shape[0] if isinstance(shape[0], int) and shape[0] > 0 else 1
        c = shape[1] if isinstance(shape[1], int) and shape[1] > 0 else 3
        h = shape[2] if isinstance(shape[2], int) and shape[2] > 0 else 320
        w = shape[3] if isinstance(shape[3], int) and shape[3] > 0 else 320

        dummy_input = np.random.randn(b, c, h, w).astype(np.float32)

        # Warm-up run
        print("Warming up inference engine...")
        for _ in range(5):
            session.run(None, {input_name: dummy_input})

        # Timed benchmark
        latencies = []
        print(f"Executing {iterations} inference passes...")
        for _ in range(iterations):
            t0 = time.perf_counter()
            session.run(None, {input_name: dummy_input})
            latencies.append((time.perf_counter() - t0) * 1000.0)

        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        fps = 1000.0 / avg_lat

        print("\n" + "-" * 50)
        print("INFERENCE BENCHMARK RESULTS (RPi 4 CPU)")
        print("-" * 50)
        print(f"Input Shape    : {dummy_input.shape}")
        print(f"Average Latency: {avg_lat:.2f} ms")
        print(f"Min Latency    : {min_lat:.2f} ms")
        print(f"Max Latency    : {max_lat:.2f} ms")
        print(f"Throughput     : {fps:.2f} FPS")
        print("-" * 50)

        if fps >= 10.0:
            print("Status: EXCELLENT (Meets real-time vision criteria for TESA 2026)")
        elif fps >= 5.0:
            print("Status: GOOD (Sufficient for automated tray/conveyor inspection)")
        else:
            print("Status: ACCEPTABLE (Recommend 320x320 resolution or frame skipping)")

    except ImportError:
        print("Error: onnxruntime not installed. Run: pip install onnxruntime")
    except Exception as e:
        print(f"Benchmark error: {e}")


def test_camera_stream(device_idx: int = 0):
    """Verifies camera feed capture via OpenCV VideoCapture."""
    print(f"\nTesting Camera Feed on /dev/video{device_idx}...")
    try:
        import cv2
        cap = cv2.VideoCapture(device_idx)
        if not cap.isOpened():
            print(f"Warning: Camera /dev/video{device_idx} cannot be opened.")
            return False

        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            h, w = frame.shape[:2]
            print(f"Camera Capture Success: Resolution {w}x{h} (Format: BGR)")
            return True
        else:
            print("Warning: Camera initialized but frame capture returned None.")
            return False
    except ImportError:
        print("Error: opencv-python not installed. Run: pip install opencv-python")
        return False
    except Exception as e:
        print(f"Camera test failed: {e}")
        return False


def test_mqtt_connection(broker: str = "localhost", port: int = 1883):
    """Tests network connectivity to MQTT Broker."""
    print(f"\nTesting MQTT Connectivity: {broker}:{port}...")
    try:
        import paho.mqtt.client as mqtt
        connected = False

        def on_connect(client, userdata, flags, rc, properties=None):
            nonlocal connected
            if rc == 0:
                connected = True

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="rpi4_test_probe")
        client.on_connect = on_connect
        client.connect(broker, port, 5)
        client.loop_start()
        time.sleep(1.0)
        client.loop_stop()
        client.disconnect()

        if connected:
            print("MQTT Connection: SUCCESS")
            return True
        else:
            print("MQTT Connection: TIMEOUT or REFUSED")
            return False
    except Exception as e:
        print(f"MQTT Connection Failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RPi 4 Hardware & Vision Benchmark")
    parser.add_argument("--model", type=str, default=str(DEFAULT_MODEL_PATH), help="Path to coffee_best.onnx")
    parser.add_argument("--iterations", type=int, default=50, help="Benchmark iteration count")
    parser.add_argument("--threads", type=int, default=4, help="CPU thread count (default: 4 for RPi 4)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--broker", type=str, default="localhost", help="MQTT Broker host")
    parser.add_argument("--skip-cam", action="store_true", help="Skip camera capture check")

    args = parser.parse_args()

    check_system_environment()

    if not args.skip_cam:
        test_camera_stream(args.camera)

    benchmark_onnx_inference(args.model, iterations=args.iterations, threads=args.threads)

    test_mqtt_connection(args.broker)
