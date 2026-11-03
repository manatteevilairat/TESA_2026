# TESA 2026: Edge AI Engine in Pure Rust 🦀

High-performance, memory-safe, ultra-low latency coffee bean defect inspection engine written in pure Rust with ONNX Runtime.

Designed as an optional high-speed alternative to the Python pipeline for the **TESA Top Gun Rally 2026** competition on Raspberry Pi 5.

---

## ⚡ Performance Highlights (macOS Apple Silicon Benchmark)

| Implementation | Framework | Average Latency | Throughput (FPS) | 62 Images Runtime |
| :--- | :--- | :--- | :--- | :--- |
| **Rust Edge Engine** | Pure `ort` 2.0 (Release) | **3.10 ms** | **322.5 FPS** | **0.19 s** |
| **Python Edge Engine** | ONNX Runtime CPU | 6.76 ms | 147.9 FPS | 0.51 s |

> **Silicon Portability Note:**  
> On Raspberry Pi 5, Python reaches ~24.0 FPS (41.5 ms). With this Rust implementation, overhead from Python GC and dynamic object creation is eliminated, running near native C++ silicon speed with deterministic memory usage.

---

## 🏗️ Architecture

```
edge_rust/
├── Cargo.toml          # Dependencies: ort (ndarray), image, serde, clap
├── src/
│   ├── main.rs         # CLI interface & formatted tournament summary report
│   ├── detector.rs     # Pure ONNX inference, 320x320 RGB preprocessing, IoU & NMS
│   └── eval.rs         # TESA 2026 7-class aggregation, SCA grading & JSON output
└── README.md
```

### Active 7-Class Taxonomy
- **Good bean** (Healthy)
- **Primary Defects**: Black, Insect damage, Scorched
- **Secondary Defects**: Broken, Empty, Quaker

---

## 🚀 Quick Start Guide

### 1. Requirements
Ensure Rust toolchain is installed:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### 2. Run Batch Evaluation (Mac or Raspberry Pi 5)
```bash
cd edge_rust
cargo run --release -- --input-dir ../edge_ai/dataset/test/images --batch-id CPN-RUST-CHAMPION
```

### 3. CLI Options
```
Usage: edge_rust [OPTIONS]

Options:
  -i, --input-dir <INPUT_DIR>      Directory containing test images [default: ../edge_ai/dataset/test/images]
  -m, --model <MODEL>              Path to ONNX weights [default: ../edge_ai/models/coffee_best.onnx]
  -b, --batch-id <BATCH_ID>        Unique tournament batch ID [default: CPN-RUST-CHAMPION]
  -c, --conf <CONF>                Confidence threshold [default: 0.30]
      --iou <IOU>                  IoU threshold for NMS [default: 0.45]
  -t, --threads <THREADS>          CPU threads [default: 4]
  -o, --output-json <OUTPUT_JSON>  Output JSON path [default: ../runs/rust_batch_report.json]
  -h, --help                       Print help
  -V, --version                    Print version
```

### 4. Output Compatibility
The generated JSON report (`../runs/rust_batch_report.json`) strictly conforms to the schema used by the Python Streamlit dashboard and Trading Agent in `market_platform/app.py`.
