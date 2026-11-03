mod detector;
mod eval;

use std::fs;
use std::path::PathBuf;
use clap::Parser;
use eval::{run_batch_evaluation, BatchReport, PRIMARY_DEFECTS, SECONDARY_DEFECTS};

#[derive(Parser, Debug)]
#[command(name = "edge_rust")]
#[command(author = "TESA 2026 Team")]
#[command(version = "0.1.0")]
#[command(about = "Ultra-Fast Rust Edge AI Vision Engine for Raspberry Pi 5 / macOS", long_about = None)]
struct Args {
    /// Directory containing coffee bean inspection images
    #[arg(short, long, default_value = "../edge_ai/dataset/test/images")]
    input_dir: PathBuf,

    /// Path to ONNX model weights
    #[arg(short, long, default_value = "../edge_ai/models/coffee_best.onnx")]
    model: PathBuf,

    /// Unique batch identifier for tournament tracking
    #[arg(short, long, default_value = "CPN-RUST-CHAMPION")]
    batch_id: String,

    /// Confidence threshold for YOLOv8 object detection
    #[arg(short, long, default_value_t = 0.30)]
    conf: f32,

    /// Intersection-over-Union (IoU) threshold for Non-Maximum Suppression
    #[arg(long, default_value_t = 0.45)]
    iou: f32,

    /// Number of CPU threads for ONNX Runtime execution
    #[arg(short, long, default_value_t = 4)]
    threads: usize,

    /// Path to save JSON batch summary report
    #[arg(short, long, default_value = "../runs/rust_batch_report.json")]
    output_json: PathBuf,
}

fn print_summary_report(report: &BatchReport) {
    println!("\n============================================================");
    println!("                BATCH EVALUATION SUMMARY REPORT");
    println!("============================================================");
    println!("Batch Identifier       : {}", report.batch_id);
    println!("Total Evaluated Images : {}", report.total_images);
    println!("Total Beans Inspected  : {}", report.total_beans_detected);

    let good_pct = if report.total_beans_detected > 0 {
        (report.healthy_beans as f64 / report.total_beans_detected as f64) * 100.0
    } else {
        0.0
    };
    let defect_pct = if report.total_beans_detected > 0 {
        (report.total_defects as f64 / report.total_beans_detected as f64) * 100.0
    } else {
        0.0
    };

    println!("Healthy Beans (Good)   : {} ({:.1}%)", report.healthy_beans, good_pct);
    println!("Total Defects Detected : {} ({:.1}%)", report.total_defects, defect_pct);
    println!("------------------------------------------------------------");
    println!("DEFECT BREAKDOWN BY CLASS:");

    for (cname, count) in &report.class_breakdown {
        let pct = if report.total_beans_detected > 0 {
            (*count as f64 / report.total_beans_detected as f64) * 100.0
        } else {
            0.0
        };
        let tag = if PRIMARY_DEFECTS.contains(&cname.as_str()) {
            " [PRIMARY]"
        } else if SECONDARY_DEFECTS.contains(&cname.as_str()) {
            " [SECONDARY]"
        } else {
            ""
        };
        println!("  - {:<16}: {:>4} beans ({:>5.1}%){}", cname, count, pct, tag);
    }

    println!("------------------------------------------------------------");
    println!("Assigned Robusta Grade : {} ({})", report.grade, report.grade_description);
    println!("Fair Intrinsic Value   : {:.2} THB/kg", report.estimated_fair_price_thb);
    println!("Mean Latency Per Frame : {:.2} ms ({:.2} FPS)", report.average_latency_ms, report.throughput_fps);
    println!("Total Processing Time  : {:.2} seconds", report.total_runtime_seconds);
    println!("============================================================");
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let report = run_batch_evaluation(
        &args.input_dir,
        &args.model,
        &args.batch_id,
        args.conf,
        args.iou,
        args.threads,
    )?;

    print_summary_report(&report);

    // Save JSON report
    if let Some(parent) = args.output_json.parent() {
        if !parent.exists() {
            fs::create_dir_all(parent)?;
        }
    }
    let json_str = serde_json::to_string_pretty(&report)?;
    fs::write(&args.output_json, json_str)?;
    println!("Saved complete evaluation report to: {:?}", args.output_json);

    Ok(())
}
