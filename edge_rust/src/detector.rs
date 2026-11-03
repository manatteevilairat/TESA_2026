use std::path::Path;
use image::GenericImageView;
use ndarray::Array4;
use ort::{session::Session, value::TensorRef};

pub const CLASS_NAMES: [&str; 7] = [
    "Black",
    "Broken",
    "Empty",
    "Good bean",
    "Insect damage",
    "Quaker",
    "Scorched",
];

#[derive(Debug, Clone)]
pub struct Detection {
    pub bbox: [f32; 4], // [left, top, width, height]
    #[allow(dead_code)]
    pub class_id: usize,
    pub class_name: String,
    pub confidence: f32,
}

pub struct CoffeeDetector {
    session: Session,
}

impl CoffeeDetector {
    pub fn new<P: AsRef<Path>>(model_path: P, num_threads: usize) -> Result<Self, Box<dyn std::error::Error>> {
        let env = ort::init()
            .with_name("edge_rust_detector")
            .build()?;

        let session = Session::builder(&env)?
            .with_intra_threads(num_threads)?
            .commit_from_file(model_path)?;

        Ok(Self { session })
    }

    pub fn predict<P: AsRef<Path>>(
        &mut self,
        image_path: P,
        conf_thresh: f32,
        iou_thresh: f32,
    ) -> Result<(Vec<Detection>, (u32, u32)), Box<dyn std::error::Error>> {
        let img = image::open(image_path)?;
        let (orig_w, orig_h) = img.dimensions();

        // YOLOv8 320x320 RGB normalization
        let resized = img.resize_exact(320, 320, image::imageops::FilterType::Triangle);
        let rgb = resized.to_rgb8();

        let mut blob = Array4::<f32>::zeros((1, 3, 320, 320));
        for y in 0..320 {
            for x in 0..320 {
                let pixel = rgb.get_pixel(x, y);
                blob[[0, 0, y as usize, x as usize]] = pixel[0] as f32 / 255.0;
                blob[[0, 1, y as usize, x as usize]] = pixel[1] as f32 / 255.0;
                blob[[0, 2, y as usize, x as usize]] = pixel[2] as f32 / 255.0;
            }
        }

        // Run inference
        let outputs = self.session.run(ort::inputs![TensorRef::from_array_view(&blob)?])?;
        let output_value = &outputs[0];
        let (shape, data) = output_value.try_extract_tensor::<f32>()?;

        // Shape expected: [1, 11, 2100]
        let _num_channels = shape[1] as usize; // 11
        let num_anchors = shape[2] as usize;  // 2100

        let x_factor = orig_w as f32 / 320.0;
        let y_factor = orig_h as f32 / 320.0;

        let mut candidates: Vec<Detection> = Vec::new();

        for a in 0..num_anchors {
            let cx = data[0 * num_anchors + a];
            let cy = data[1 * num_anchors + a];
            let w = data[2 * num_anchors + a];
            let h = data[3 * num_anchors + a];

            // Find best class
            let mut best_class = 0;
            let mut max_conf = -1.0_f32;
            for c in 0..7 {
                let score = data[(4 + c) * num_anchors + a];
                if score > max_conf {
                    max_conf = score;
                    best_class = c;
                }
            }

            if max_conf > conf_thresh {
                let left = (cx - 0.5 * w) * x_factor;
                let top = (cy - 0.5 * h) * y_factor;
                let width = w * x_factor;
                let height = h * y_factor;

                candidates.push(Detection {
                    bbox: [left, top, width, height],
                    class_id: best_class,
                    class_name: CLASS_NAMES[best_class].to_string(),
                    confidence: max_conf,
                });
            }
        }

        // Non-Maximum Suppression (NMS)
        let filtered = apply_nms(candidates, iou_thresh);
        Ok((filtered, (orig_w, orig_h)))
    }
}

fn compute_iou(box_a: &[f32; 4], box_b: &[f32; 4]) -> f32 {
    let [ax, ay, aw, ah] = *box_a;
    let [bx, by, bw, bh] = *box_b;

    let x1 = ax.max(bx);
    let y1 = ay.max(by);
    let x2 = (ax + aw).min(bx + bw);
    let y2 = (ay + ah).min(by + bh);

    let inter_w = (x2 - x1).max(0.0);
    let inter_h = (y2 - y1).max(0.0);
    let inter_area = inter_w * inter_h;

    let area_a = aw * ah;
    let area_b = bw * bh;
    let union_area = area_a + area_b - inter_area;

    if union_area <= 0.0 {
        0.0
    } else {
        inter_area / union_area
    }
}

fn apply_nms(mut detections: Vec<Detection>, iou_thresh: f32) -> Vec<Detection> {
    detections.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap_or(std::cmp::Ordering::Equal));

    let mut selected: Vec<Detection> = Vec::new();

    for det in detections {
        let mut keep = true;
        for sel in &selected {
            if compute_iou(&det.bbox, &sel.bbox) > iou_thresh {
                keep = false;
                break;
            }
        }
        if keep {
            selected.push(det);
        }
    }

    selected
}
