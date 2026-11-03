use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;
use serde::{Deserialize, Serialize};

use crate::detector::{CoffeeDetector, CLASS_NAMES};

pub const PRIMARY_DEFECTS: [&str; 3] = ["Black", "Insect damage", "Scorched"];
pub const SECONDARY_DEFECTS: [&str; 3] = ["Broken", "Empty", "Quaker"];

#[derive(Debug, Serialize, Deserialize)]
pub struct ImageEvalResult {
    pub filename: String,
    pub latency_ms: f64,
    pub beans_detected: usize,
    pub counts: BTreeMap<String, usize>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BatchReport {
    pub batch_id: String,
    pub total_images: usize,
    pub total_beans_detected: usize,
    pub healthy_beans: usize,
    pub total_defects: usize,
    pub defect_rate_pct: f64,
    pub primary_defects_count: usize,
    pub secondary_defects_count: usize,
    pub grade: String,
    pub grade_description: String,
    pub estimated_fair_price_thb: f64,
    pub class_breakdown: BTreeMap<String, usize>,
    pub average_latency_ms: f64,
    pub throughput_fps: f64,
    pub total_runtime_seconds: f64,
    pub detailed_images: Vec<ImageEvalResult>,
}

pub fn run_batch_evaluation<P: AsRef<Path>, M: AsRef<Path>>(
    input_dir: P,
    model_path: M,
    batch_id: &str,
    conf_thresh: f32,
    iou_thresh: f32,
    threads: usize,
) -> Result<BatchReport, Box<dyn std::error::Error>> {
    let input_dir = input_dir.as_ref();
    if !input_dir.exists() {
        return Err(format!("Directory not found: {:?}", input_dir).into());
    }

    let mut image_paths: Vec<PathBuf> = Vec::new();
    for entry in fs::read_dir(input_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_file() {
            if let Some(ext) = path.extension().and_then(|s| s.to_str()) {
                let ext_lower = ext.to_lowercase();
                if ext_lower == "jpg" || ext_lower == "jpeg" || ext_lower == "png" || ext_lower == "bmp" {
                    image_paths.push(path);
                }
            }
        }
    }
    image_paths.sort();

    println!("============================================================");
    println!("   TESA 2026: RUST HIGH-PERFORMANCE BATCH EVALUATION");
    println!("============================================================");
    println!("Batch Identifier : {}", batch_id);
    println!("Input Directory  : {:?} ({} images)", input_dir, image_paths.len());
    println!("Model Path       : {:?}", model_path.as_ref());
    println!("Confidence Level : {:.2} | IoU: {:.2} | CPU Threads: {}", conf_thresh, iou_thresh, threads);
    println!("============================================================");

    let mut detector = CoffeeDetector::new(model_path, threads)?;

    let mut class_totals: BTreeMap<String, usize> = BTreeMap::new();
    for name in CLASS_NAMES.iter() {
        class_totals.insert(name.to_string(), 0);
    }

    let mut detailed_images: Vec<ImageEvalResult> = Vec::with_capacity(image_paths.len());
    let mut latencies: Vec<f64> = Vec::with_capacity(image_paths.len());
    let total_start = Instant::now();

    for (idx, path) in image_paths.iter().enumerate() {
        let t0 = Instant::now();
        let (detections, _) = detector.predict(path, conf_thresh, iou_thresh)?;
        let dt_ms = t0.elapsed().as_secs_f64() * 1000.0;
        latencies.push(dt_ms);

        let mut image_counts: BTreeMap<String, usize> = BTreeMap::new();
        for name in CLASS_NAMES.iter() {
            image_counts.insert(name.to_string(), 0);
        }

        for det in &detections {
            *class_totals.entry(det.class_name.clone()).or_insert(0) += 1;
            *image_counts.entry(det.class_name.clone()).or_insert(0) += 1;
        }

        let file_name = path.file_name().and_then(|s| s.to_str()).unwrap_or("unknown").to_string();
        detailed_images.push(ImageEvalResult {
            filename: file_name.clone(),
            latency_ms: (dt_ms * 100.0).round() / 100.0,
            beans_detected: detections.len(),
            counts: image_counts,
        });

        let curr_idx = idx + 1;
        if curr_idx % 10 == 0 || curr_idx == image_paths.len() {
            let avg_ms = latencies.iter().sum::<f64>() / latencies.len() as f64;
            let current_fps = 1000.0 / avg_ms;
            let display_name = if file_name.len() > 30 {
                &file_name[..30]
            } else {
                &file_name
            };
            println!(
                "[{:>3}/{}] Processed {:<30} | Detected: {:>2} beans | Avg FPS: {:>5.2}",
                curr_idx,
                image_paths.len(),
                display_name,
                detections.len(),
                current_fps
            );
        }
    }

    let total_elapsed_sec = total_start.elapsed().as_secs_f64();
    let total_beans: usize = class_totals.values().sum();
    let healthy_beans = *class_totals.get("Good bean").unwrap_or(&0);
    let total_defects = total_beans.saturating_sub(healthy_beans);

    let primary_defects: usize = PRIMARY_DEFECTS
        .iter()
        .map(|c| *class_totals.get(*c).unwrap_or(&0))
        .sum();

    let secondary_defects: usize = SECONDARY_DEFECTS
        .iter()
        .map(|c| *class_totals.get(*c).unwrap_or(&0))
        .sum();

    let defect_rate_pct = if total_beans > 0 {
        (total_defects as f64 / total_beans as f64) * 100.0
    } else {
        0.0
    };

    let primary_rate_pct = if total_beans > 0 {
        (primary_defects as f64 / total_beans as f64) * 100.0
    } else {
        0.0
    };

    // Official TESA 2026 Chumphon Robusta Grading Rubric
    let (grade, grade_desc, fair_price) = if defect_rate_pct <= 3.0 && primary_defects == 0 {
        ("FINE_ROBUSTA", "Chumphon Fine Robusta (Specialty Grade)", 320.0)
    } else if defect_rate_pct <= 6.0 && primary_rate_pct <= 1.0 {
        ("PREMIUM", "Premium Robusta (Grade 1 High Commercial)", 230.0)
    } else if defect_rate_pct <= 14.0 {
        ("COMMERCIAL_GRADE", "Commercial Robusta (Standard Market Grade)", 145.0)
    } else {
        ("REJECT", "Off-Grade / Reject (Defect Exceeds Standard)", 65.0)
    };

    let avg_latency_ms = if !latencies.is_empty() {
        latencies.iter().sum::<f64>() / latencies.len() as f64
    } else {
        0.0
    };
    let avg_fps = if avg_latency_ms > 0.0 {
        1000.0 / avg_latency_ms
    } else {
        0.0
    };

    Ok(BatchReport {
        batch_id: batch_id.to_string(),
        total_images: image_paths.len(),
        total_beans_detected: total_beans,
        healthy_beans,
        total_defects,
        defect_rate_pct: (defect_rate_pct * 100.0).round() / 100.0,
        primary_defects_count: primary_defects,
        secondary_defects_count: secondary_defects,
        grade: grade.to_string(),
        grade_description: grade_desc.to_string(),
        estimated_fair_price_thb: fair_price,
        class_breakdown: class_totals,
        average_latency_ms: (avg_latency_ms * 100.0).round() / 100.0,
        throughput_fps: (avg_fps * 100.0).round() / 100.0,
        total_runtime_seconds: (total_elapsed_sec * 100.0).round() / 100.0,
        detailed_images,
    })
}
