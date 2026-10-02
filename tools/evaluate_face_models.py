#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""DualKey face model evaluation tool.

Measures real latency, CPU utilization, memory usage, and recognition
stability for each detector+recognizer combination under controlled
conditions. Results are written to data/evaluation/.

Usage:
    .venv/bin/python tools/evaluate_face_models.py --backend lbph
    .venv/bin/python tools/evaluate_face_models.py --backend sface
    .venv/bin/python tools/evaluate_face_models.py --all

Backends evaluated:
    Haar + LBPH    (MVP baseline)
    YuNet + LBPH   (modern detector, baseline recognizer)
    YuNet + SFace  (modern pipeline)

IMPORTANT:
    Do not invent benchmark numbers. This tool measures them.
    Results are hardware-dependent: CPU model, RAM, camera FPS.

Reference: DOC-09-PLAN Phase 12 (docs/09-ai-engineering/master-implementation-plan.md)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters.haar_detector import HaarFaceDetector
from app.adapters.lbph_recognizer import LBPHRecognizer

logger = logging.getLogger("evaluate")

_OUTPUT_DIR = Path("data/evaluation")
_WARMUP_FRAMES = 10
_MEASUREMENT_FRAMES = 100


@dataclass
class BenchmarkResult:
    """Captured benchmark measurements for one pipeline configuration."""

    backend_name: str
    detector_name: str
    recognizer_name: str
    detector_version: str
    recognizer_version: str

    # Startup
    detector_init_ms: float = 0.0
    recognizer_init_ms: float = 0.0

    # Per-frame latency (milliseconds)
    detection_latencies_ms: list[float] = field(default_factory=list)
    recognition_latencies_ms: list[float] = field(default_factory=list)
    end_to_end_latencies_ms: list[float] = field(default_factory=list)

    # Aggregate stats (computed)
    detection_mean_ms: float = 0.0
    detection_p50_ms: float = 0.0
    detection_p95_ms: float = 0.0
    detection_p99_ms: float = 0.0
    recognition_mean_ms: float = 0.0
    recognition_p50_ms: float = 0.0
    recognition_p95_ms: float = 0.0
    recognition_p99_ms: float = 0.0
    e2e_mean_ms: float = 0.0
    e2e_p50_ms: float = 0.0
    e2e_p95_ms: float = 0.0
    e2e_p99_ms: float = 0.0

    # Resource usage
    peak_rss_mb: float = 0.0
    cpu_percent: float = 0.0

    # Detection stats
    total_frames: int = 0
    frames_with_face: int = 0
    frames_no_face: int = 0
    frames_multi_face: int = 0
    detection_rate: float = 0.0

    # Recognition stats (only for frames with exactly 1 face)
    recognition_attempts: int = 0
    recognition_matches: int = 0
    recognition_mismatches: int = 0
    recognition_no_match: int = 0
    recognition_match_rate: float = 0.0

    # Stability (consecutive match count distribution)
    max_consecutive_matches: int = 0

    # Environment
    opencv_version: str = ""
    python_version: str = ""
    camera_resolution: str = ""
    timestamp: str = ""


def measure_startup(backend: str) -> tuple[float, float, object, object]:
    """Measure detector and recognizer initialization latency.

    Returns:
        (detector_init_ms, recognizer_init_ms, detector, recognizer)
    """
    if backend == "haar_lbph":
        t0 = time.perf_counter()
        detector = HaarFaceDetector()
        det_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        recognizer = LBPHRecognizer(threshold=65.0)
        rec_ms = (time.perf_counter() - t0) * 1000

        return det_ms, rec_ms, detector, recognizer

    elif backend == "yunet_lbph":
        from app.adapters.yunet_detector import YuNetFaceDetector

        yunet_path = "models/yunet/face_detection_yunet_2023mar.onnx"
        if not Path(yunet_path).exists():
            logger.error("YuNet model not found at %s", yunet_path)
            sys.exit(1)

        t0 = time.perf_counter()
        detector = YuNetFaceDetector(model_path=yunet_path)
        det_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        recognizer = LBPHRecognizer(threshold=65.0)
        rec_ms = (time.perf_counter() - t0) * 1000

        return det_ms, rec_ms, detector, recognizer

    elif backend == "yunet_sface":
        from app.adapters.sface_recognizer import SFaceRecognizer
        from app.adapters.yunet_detector import YuNetFaceDetector

        yunet_path = "models/yunet/face_detection_yunet_2023mar.onnx"
        sface_path = "models/sface/face_recognition_sface_2021dec.onnx"

        for p in (yunet_path, sface_path):
            if not Path(p).exists():
                logger.error("Model not found at %s", p)
                sys.exit(1)

        t0 = time.perf_counter()
        detector = YuNetFaceDetector(model_path=yunet_path)
        det_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        recognizer = SFaceRecognizer(model_path=sface_path, threshold=0.363)
        rec_ms = (time.perf_counter() - t0) * 1000

        return det_ms, rec_ms, detector, recognizer

    else:
        logger.error("Unknown backend: %s", backend)
        sys.exit(1)


def run_benchmark(
    backend_name: str,
    detector: object,
    recognizer: object,
    camera_index: int = 0,
    num_frames: int = _MEASUREMENT_FRAMES,
) -> BenchmarkResult:
    """Run latency and accuracy benchmark on live camera frames.

    Args:
        backend_name: Human-readable name for the pipeline.
        detector: Must have .detect(frame) and .get_model_info().
        recognizer: Must have .recognize(crop) and .get_model_info().
        camera_index: OpenCV camera device index.
        num_frames: Number of measurement frames after warmup.

    Returns:
        Populated BenchmarkResult.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        logger.error("Cannot open camera %d", camera_index)
        sys.exit(1)

    # Read resolution
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    det_id, det_ver = detector.get_model_info()  # type: ignore[union-attr]
    rec_id, rec_ver = recognizer.get_model_info()  # type: ignore[union-attr]

    result = BenchmarkResult(
        backend_name=backend_name,
        detector_name=det_id,
        recognizer_name=rec_id,
        detector_version=det_ver,
        recognizer_version=rec_ver,
        opencv_version=cv2.__version__,
        python_version=sys.version.split()[0],
        camera_resolution=f"{width}x{height}",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )

    # Warmup
    logger.info("Warming up (%d frames)...", _WARMUP_FRAMES)
    for _ in range(_WARMUP_FRAMES):
        ret, frame = cap.read()
        if ret:
            detector.detect(frame)  # type: ignore[union-attr]

    # Measurement
    logger.info("Measuring %d frames for %s...", num_frames, backend_name)
    consecutive_matches = 0
    max_consecutive = 0

    try:
        import resource
        _mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        pass

    cpu_start = time.process_time()
    wall_start = time.perf_counter()

    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            continue

        result.total_frames += 1

        # Detection
        t0 = time.perf_counter()
        faces = detector.detect(frame)  # type: ignore[union-attr]
        det_ms = (time.perf_counter() - t0) * 1000
        result.detection_latencies_ms.append(det_ms)

        face_count = len(faces)
        if face_count == 0:
            result.frames_no_face += 1
            consecutive_matches = 0
            continue
        elif face_count > 1:
            result.frames_multi_face += 1
            consecutive_matches = 0
            continue

        result.frames_with_face += 1

        # Crop face
        bbox = faces[0].bbox
        x, y, w, h = bbox
        fh, fw = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, fw - x), min(h, fh - y)
        crop = frame[y : y + h, x : x + w]

        # Recognition
        t0 = time.perf_counter()
        rec_result = recognizer.recognize(crop)  # type: ignore[union-attr]
        rec_ms = (time.perf_counter() - t0) * 1000
        result.recognition_latencies_ms.append(rec_ms)
        result.end_to_end_latencies_ms.append(det_ms + rec_ms)

        result.recognition_attempts += 1
        if rec_result.is_match:
            result.recognition_matches += 1
            consecutive_matches += 1
            max_consecutive = max(max_consecutive, consecutive_matches)
        else:
            result.recognition_no_match += 1
            consecutive_matches = 0

        if i % 20 == 0:
            logger.info(
                "  Frame %d/%d: det=%.1fms rec=%.1fms faces=%d",
                i, num_frames, det_ms, rec_ms, face_count,
            )

    wall_elapsed = time.perf_counter() - wall_start
    cpu_elapsed = time.process_time() - cpu_start

    cap.release()

    # Compute aggregates
    if result.detection_latencies_ms:
        s = sorted(result.detection_latencies_ms)
        result.detection_mean_ms = statistics.mean(s)
        result.detection_p50_ms = _percentile(s, 50)
        result.detection_p95_ms = _percentile(s, 95)
        result.detection_p99_ms = _percentile(s, 99)

    if result.recognition_latencies_ms:
        s = sorted(result.recognition_latencies_ms)
        result.recognition_mean_ms = statistics.mean(s)
        result.recognition_p50_ms = _percentile(s, 50)
        result.recognition_p95_ms = _percentile(s, 95)
        result.recognition_p99_ms = _percentile(s, 99)

    if result.end_to_end_latencies_ms:
        s = sorted(result.end_to_end_latencies_ms)
        result.e2e_mean_ms = statistics.mean(s)
        result.e2e_p50_ms = _percentile(s, 50)
        result.e2e_p95_ms = _percentile(s, 95)
        result.e2e_p99_ms = _percentile(s, 99)

    result.detection_rate = (
        result.frames_with_face / result.total_frames * 100
        if result.total_frames > 0 else 0.0
    )
    result.recognition_match_rate = (
        result.recognition_matches / result.recognition_attempts * 100
        if result.recognition_attempts > 0 else 0.0
    )
    result.max_consecutive_matches = max_consecutive
    result.cpu_percent = cpu_elapsed / wall_elapsed * 100 if wall_elapsed > 0 else 0.0

    try:
        import resource
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result.peak_rss_mb = mem_after / 1024  # Linux returns KB
    except ImportError:
        result.peak_rss_mb = 0.0

    return result


def _percentile(sorted_data: list[float], pct: int) -> float:
    """Compute the pct-th percentile from sorted data."""
    if not sorted_data:
        return 0.0
    idx = int(len(sorted_data) * pct / 100)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


def save_results(result: BenchmarkResult) -> None:
    """Save benchmark results to JSON and CSV."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON (full detail)
    json_path = _OUTPUT_DIR / f"{result.backend_name}_benchmark.json"
    # Exclude raw latency arrays from JSON for readability
    data = asdict(result)
    data.pop("detection_latencies_ms", None)
    data.pop("recognition_latencies_ms", None)
    data.pop("end_to_end_latencies_ms", None)
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Results saved: %s", json_path)

    # CSV (raw latencies for analysis)
    csv_path = _OUTPUT_DIR / f"{result.backend_name}_latencies.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "detection_ms", "recognition_ms", "e2e_ms"])
        max_len = max(
            len(result.detection_latencies_ms),
            len(result.recognition_latencies_ms),
            len(result.end_to_end_latencies_ms),
        ) if result.detection_latencies_ms else 0
        for i in range(max_len):
            det_lat = result.detection_latencies_ms
            rec_lat = result.recognition_latencies_ms
            e2e_lat = result.end_to_end_latencies_ms
            det = det_lat[i] if i < len(det_lat) else ""
            rec = rec_lat[i] if i < len(rec_lat) else ""
            e2e = e2e_lat[i] if i < len(e2e_lat) else ""
            writer.writerow([i, det, rec, e2e])
    logger.info("Latencies saved: %s", csv_path)


def print_summary(result: BenchmarkResult) -> None:
    """Print a human-readable benchmark summary."""
    print(f"\n{'=' * 60}")
    print(f"  BENCHMARK: {result.backend_name}")
    print(f"{'=' * 60}")
    print(f"  Detector:   {result.detector_name} ({result.detector_version})")
    print(f"  Recognizer: {result.recognizer_name} ({result.recognizer_version})")
    print(f"  OpenCV:     {result.opencv_version}")
    print(f"  Camera:     {result.camera_resolution}")
    print(f"  Timestamp:  {result.timestamp}")
    print()
    print("  STARTUP LATENCY")
    print(f"    Detector init:   {result.detector_init_ms:8.1f} ms")
    print(f"    Recognizer init: {result.recognizer_init_ms:8.1f} ms")
    print()
    r = result
    print("  DETECTION LATENCY (ms)")
    print(f"    Mean: {r.detection_mean_ms:7.1f}  P50: {r.detection_p50_ms:7.1f}"
          f"  P95: {r.detection_p95_ms:7.1f}  P99: {r.detection_p99_ms:7.1f}")
    print()
    print("  RECOGNITION LATENCY (ms)")
    print(f"    Mean: {r.recognition_mean_ms:7.1f}  P50: {r.recognition_p50_ms:7.1f}"
          f"  P95: {r.recognition_p95_ms:7.1f}  P99: {r.recognition_p99_ms:7.1f}")
    print()
    print("  END-TO-END LATENCY (ms)")
    print(f"    Mean: {r.e2e_mean_ms:7.1f}  P50: {r.e2e_p50_ms:7.1f}"
          f"  P95: {r.e2e_p95_ms:7.1f}  P99: {r.e2e_p99_ms:7.1f}")
    print()
    print("  DETECTION STATS")
    print(f"    Total frames:  {result.total_frames}")
    print(f"    With face:     {result.frames_with_face} ({result.detection_rate:.1f}%)")
    print(f"    No face:       {result.frames_no_face}")
    print(f"    Multi-face:    {result.frames_multi_face}")
    print()
    print("  RECOGNITION STATS")
    print(f"    Attempts:      {result.recognition_attempts}")
    print(f"    Matches:       {result.recognition_matches} ({result.recognition_match_rate:.1f}%)")
    print(f"    No match:      {result.recognition_no_match}")
    print(f"    Max consec.:   {result.max_consecutive_matches}")
    print()
    print("  RESOURCES")
    print(f"    CPU utilization:  {result.cpu_percent:.1f}%")
    print(f"    Peak RSS:         {result.peak_rss_mb:.1f} MB")
    print(f"{'=' * 60}\n")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="evaluate_face_models",
        description="DualKey face model benchmark tool",
    )
    parser.add_argument(
        "--backend",
        choices=["haar_lbph", "yunet_lbph", "yunet_sface"],
        help="Backend to evaluate",
    )
    parser.add_argument(
        "--all", action="store_true", help="Evaluate all available backends",
    )
    parser.add_argument(
        "--frames", type=int, default=_MEASUREMENT_FRAMES,
        help="Number of frames to measure (default: 100)",
    )
    parser.add_argument(
        "--camera", type=int, default=0, help="Camera device index",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.backend and not args.all:
        parser.print_help()
        sys.exit(1)

    backends: list[str] = []
    if args.all:
        backends.append("haar_lbph")
        # Only add YuNet backends if models exist
        if Path("models/yunet/face_detection_yunet_2023mar.onnx").exists():
            backends.append("yunet_lbph")
            if Path("models/sface/face_recognition_sface_2021dec.onnx").exists():
                backends.append("yunet_sface")
            else:
                logger.warning("SFace model not found -- skipping yunet_sface")
        else:
            logger.warning("YuNet model not found -- skipping YuNet backends")
    elif args.backend:
        backends.append(args.backend)

    for backend in backends:
        logger.info("Evaluating backend: %s", backend)

        det_ms, rec_ms, detector, recognizer = measure_startup(backend)
        result = run_benchmark(
            backend_name=backend,
            detector=detector,
            recognizer=recognizer,
            camera_index=args.camera,
            num_frames=args.frames,
        )
        result.detector_init_ms = det_ms
        result.recognizer_init_ms = rec_ms

        print_summary(result)
        save_results(result)

    logger.info("Evaluation complete. Results in %s/", _OUTPUT_DIR)


if __name__ == "__main__":
    main()
