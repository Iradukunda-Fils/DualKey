# SPDX-License-Identifier: MIT
"""DualKey application entry point and CLI.

Supports four modes:
    --run       Start the access control loop (default)
    --enroll    Interactive person enrollment
    --calibrate Run face model threshold calibration
    --model     Select recognition backend (lbph or sface)

Reference: DOC-03-LLD (docs/03-design/low-level-design.md)
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from app.adapters.monotonic_clock import MonotonicClock
from app.adapters.sqlite_repositories import (
    SqliteEventRepository,
    SqliteIdentityRepository,
    create_connection,
)
from app.application.access_controller import AccessController
from app.application.enrollment_service import EnrollmentService
from app.application.event_logger import EventLogger
from app.application.health_service import HealthService
from app.config import load_config
from app.domain.models import SystemConfig

logger = logging.getLogger("dualkey")

_DB_PATH = "data/app.db"
_LBPH_MODEL_PATH = "data/models/lbph.yml"
_SFACE_PROTO_PATH = "data/models/sface_prototypes.json"
_YUNET_MODEL_PATH = "models/yunet/face_detection_yunet_2023mar.onnx"
_SFACE_MODEL_PATH = "models/sface/face_recognition_sface_2021dec.onnx"


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate mode."""
    parser = argparse.ArgumentParser(
        prog="dualkey",
        description="DualKey -- Two-Factor Physical Access Control System",
    )
    parser.add_argument(
        "--run", action="store_true", default=False, help="Start the access control loop"
    )
    parser.add_argument(
        "--enroll", action="store_true", default=False, help="Enroll a new person"
    )
    parser.add_argument(
        "--name", type=str, default=None, help="Display name for enrollment"
    )
    parser.add_argument(
        "--card", type=str, default=None, help="RFID card UID for enrollment"
    )
    parser.add_argument(
        "--samples", type=int, default=20, help="Number of face samples for enrollment"
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["lbph", "sface"],
        default="lbph",
        help="Face recognition backend",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        default=False,
        help="Display real-time visual camera feed with bounding boxes",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = load_config()

    if args.enroll:
        _run_enrollment(config, args)
    else:
        _run_access_loop(config, args)


def _run_access_loop(config: SystemConfig, args: argparse.Namespace) -> None:
    """Start the main access control event loop."""
    from app.adapters.esp32_serial import Esp32SerialAdapter
    from app.adapters.haar_detector import HaarFaceDetector
    from app.adapters.lbph_recognizer import LBPHRecognizer
    from app.adapters.opencv_camera import OpenCVCameraAdapter

    logger.info("Starting DualKey access control loop (model=%s)", args.model)

    # Ensure data directories exist
    Path("data/models").mkdir(parents=True, exist_ok=True)
    Path("data/logs").mkdir(parents=True, exist_ok=True)

    # Initialize adapters
    clock = MonotonicClock()
    conn = create_connection(_DB_PATH)
    identity_repo = SqliteIdentityRepository(conn)
    event_repo = SqliteEventRepository(conn)

    # Camera
    camera = OpenCVCameraAdapter(camera_index=config.camera_index)
    camera.open()

    # Detector + Recognizer
    if args.model == "sface" and _sface_available():
        from app.adapters.sface_recognizer import SFaceRecognizer
        from app.adapters.yunet_detector import YuNetFaceDetector

        detector = YuNetFaceDetector(model_path=_YUNET_MODEL_PATH)
        recognizer: LBPHRecognizer | SFaceRecognizer = SFaceRecognizer(
            model_path=_SFACE_MODEL_PATH,
            threshold=config.sface_threshold,
        )
        if Path(_SFACE_PROTO_PATH).exists():
            recognizer.load(_SFACE_PROTO_PATH)
        logger.info("Using SFace/YuNet backend")
    else:
        detector = HaarFaceDetector()
        recognizer = LBPHRecognizer(threshold=config.lbph_threshold)
        if Path(_LBPH_MODEL_PATH).exists():
            recognizer.load(_LBPH_MODEL_PATH)
            # Restore label mapping from identity repo
            persons = identity_repo.list_active_persons()
            mapping = {p.face_label: p.person_id for p in persons}
            recognizer.set_label_mapping(mapping)
        logger.info("Using LBPH/Haar baseline backend")

    # Serial transport
    transport = Esp32SerialAdapter(
        port=config.serial_port,
        baud=config.serial_baud,
    )
    try:
        transport.open()
    except Exception:
        logger.error("Serial port %s not available -- running without device", config.serial_port)

    # Services
    event_logger = EventLogger(event_repo)
    health_service = HealthService(
        camera=camera,
        transport=transport,
        clock=clock,
        heartbeat_timeout_s=config.heartbeat_timeout_s,
    )

    controller = AccessController(
        config=config,
        identity_repo=identity_repo,
        transport=transport,
        camera=camera,
        detector=detector,
        recognizer=recognizer,
        clock=clock,
        event_logger=event_logger,
        health_service=health_service,
        show_preview=args.preview,
    )

    # Graceful shutdown
    running = True

    def _signal_handler(signum: int, frame: object) -> None:
        nonlocal running
        logger.info("Shutdown signal received")
        running = False

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("DualKey is ready -- waiting for RFID events")

    try:
        while running:
            controller.tick()
            time.sleep(0.033)  # ~30 Hz tick rate
    finally:
        camera.close()
        transport.close()
        conn.close()
        logger.info("DualKey shutdown complete")


def _run_enrollment(config: SystemConfig, args: argparse.Namespace) -> None:
    """Run interactive enrollment for a new person."""
    from app.adapters.haar_detector import HaarFaceDetector
    from app.adapters.lbph_recognizer import LBPHRecognizer
    from app.adapters.opencv_camera import OpenCVCameraAdapter

    name = args.name
    card_uid: str | None = args.card

    if not name:
        name = input("Enter person's full name: ").strip()
    if not card_uid:
        from app.adapters.esp32_serial import Esp32SerialAdapter
        print("\n[INFO] Tap your RFID card on the RC522 reader now (waiting up to 15s)...")
        try:
            transport = Esp32SerialAdapter(port=config.serial_port, baud=config.serial_baud)
            transport.open()
            deadline = time.time() + 15.0
            while time.time() < deadline:
                events = transport.poll()
                for ev in events:
                    if ev.event_type == "rfid_detected":
                        raw_uid = ev.payload.get("uid") or ev.payload.get("card_uid")
                        if raw_uid:
                            card_uid = str(raw_uid).upper()
                            print(f"[SUCCESS] Scanned Card UID: {card_uid}")
                            break
                if card_uid:
                    break
                time.sleep(0.05)
            transport.close()
        except Exception as e:
            logger.debug("Live serial card read skipped: %s", e)

        if not card_uid:
            card_uid = input("Enter RFID card UID (hex): ").strip()

    if not name or not card_uid:
        logger.error("Name and card UID are required for enrollment")
        sys.exit(1)

    # Ensure data directories
    Path("data/faces").mkdir(parents=True, exist_ok=True)
    Path("data/models").mkdir(parents=True, exist_ok=True)

    conn = create_connection(_DB_PATH)
    identity_repo = SqliteIdentityRepository(conn)

    camera = OpenCVCameraAdapter(camera_index=config.camera_index)
    camera.open()

    # Use appropriate detector + recognizer
    if args.model == "sface" and _sface_available():
        from app.adapters.sface_recognizer import SFaceRecognizer
        from app.adapters.yunet_detector import YuNetFaceDetector

        detector = YuNetFaceDetector(model_path=_YUNET_MODEL_PATH)
        recognizer: LBPHRecognizer | SFaceRecognizer = SFaceRecognizer(
            model_path=_SFACE_MODEL_PATH,
            threshold=config.sface_threshold,
        )
    else:
        detector = HaarFaceDetector()
        recognizer = LBPHRecognizer(threshold=config.lbph_threshold)
        if Path(_LBPH_MODEL_PATH).exists():
            recognizer.load(_LBPH_MODEL_PATH)
            persons = identity_repo.list_active_persons()
            mapping = {p.face_label: p.person_id for p in persons}
            recognizer.set_label_mapping(mapping)

    service = EnrollmentService(
        camera=camera,
        detector=detector,
        recognizer=recognizer,
        identity_repo=identity_repo,
    )

    try:
        person = service.enroll_person(
            display_name=name,
            rfid_uid=card_uid,
            num_samples=args.samples,
        )
        # Save the trained model
        model_id, _ = recognizer.get_model_info()
        if model_id == "lbph_recognizer":
            recognizer.save(_LBPH_MODEL_PATH)
        elif model_id == "sface_recognizer":
            recognizer.save(_SFACE_PROTO_PATH)

        logger.info("Enrollment successful: %s (id=%s)", person.display_name, person.person_id)
    except RuntimeError as e:
        logger.error("Enrollment failed: %s", e)
        sys.exit(1)
    finally:
        camera.close()
        conn.close()


def _sface_available() -> bool:
    """Check if SFace/YuNet model files are present."""
    return Path(_YUNET_MODEL_PATH).exists() and Path(_SFACE_MODEL_PATH).exists()


if __name__ == "__main__":
    main()
