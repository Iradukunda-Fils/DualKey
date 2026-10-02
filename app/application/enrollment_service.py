# SPDX-License-Identifier: MIT
"""Enrollment service -- multi-sample identity registration.

Guides interactive face sample capture, validates quality, trains
recognition models, and persists identity records. Supports both
LBPH and SFace backends through the FaceRecognizerPort.

Reference: DOC-03-ENROLL (docs/03-design/enrollment.md)
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from app.domain.models import FaceSample, Person, RFIDCard, UserStatus
from app.ports.camera import CameraPort
from app.ports.detector import FaceDetectorPort
from app.ports.recognizer import FaceRecognizerPort
from app.ports.repositories import IdentityRepository

logger = logging.getLogger(__name__)

_DEFAULT_SAMPLES = 20
_FACES_DIR = "data/faces"


class EnrollmentService:
    """Multi-sample enrollment with quality filtering and dual-backend support.

    Captures face samples from the camera, validates that exactly one
    face is present per frame, crops and stores the samples, then
    trains/updates the recognizer model.
    """

    def __init__(
        self,
        camera: CameraPort,
        detector: FaceDetectorPort,
        recognizer: FaceRecognizerPort,
        identity_repo: IdentityRepository,
        faces_dir: str = _FACES_DIR,
    ) -> None:
        self._camera = camera
        self._detector = detector
        self._recognizer = recognizer
        self._identity_repo = identity_repo
        self._faces_dir = faces_dir

    def enroll_person(
        self,
        display_name: str,
        rfid_uid: str,
        num_samples: int = _DEFAULT_SAMPLES,
    ) -> Person:
        """Execute the full enrollment workflow for a new person.

        Steps:
            1. Create Person entity with next available face_label
            2. Capture num_samples face crops from the camera
            3. Save crops to data/faces/<person_id>/
            4. Train the recognizer with the collected samples
            5. Bind the RFID card to the person
            6. Persist all records to the IdentityRepository

        Args:
            display_name: Human-readable name for the person.
            rfid_uid: Hex-encoded RFID card UID to bind.
            num_samples: Number of face samples to capture.

        Returns:
            The newly created Person entity.

        Raises:
            RuntimeError: If not enough valid samples could be captured.
        """
        person_id = str(uuid.uuid4())
        face_label = self._next_label()

        person = Person(
            person_id=person_id,
            display_name=display_name,
            face_label=face_label,
            status=UserStatus.ACTIVE,
            created_at=time.time(),
        )

        # Create sample storage directory
        person_dir = Path(self._faces_dir) / person_id
        person_dir.mkdir(parents=True, exist_ok=True)

        # Capture face samples
        logger.info(
            "Starting enrollment for '%s' -- capturing %d samples", display_name, num_samples
        )
        crops = self._capture_samples(num_samples, person_dir, person_id)

        if len(crops) < 3:
            msg = (
                f"Only captured {len(crops)} valid samples "
                f"(minimum 3 required). Enrollment aborted."
            )
            raise RuntimeError(msg)

        # Train recognizer
        self._recognizer.enroll(person_id, crops)
        logger.info(
            "Recognizer trained with %d samples for %s", len(crops), display_name
        )

        # Persist identity records
        self._identity_repo.create_person(person)
        card = RFIDCard(
            rfid_uid=rfid_uid,
            person_id=person_id,
            status=UserStatus.ACTIVE,
            enrolled_at=time.time(),
        )
        self._identity_repo.bind_card(card)

        logger.info(
            "Enrollment complete: %s (label=%d, card=%s, samples=%d)",
            display_name,
            face_label,
            rfid_uid,
            len(crops),
        )
        return person

    def _capture_samples(
        self,
        num_samples: int,
        save_dir: Path,
        person_id: str,
    ) -> list[NDArray[np.uint8]]:
        """Capture face samples from the camera with quality filtering.

        Frames with zero or multiple faces are discarded. The user should
        vary head position (slight left/right/up/down) during capture.

        Args:
            num_samples: Target number of valid samples.
            save_dir: Directory to save the face crop PNGs.
            person_id: Person ID for FaceSample record creation.

        Returns:
            List of valid face crop arrays.
        """
        crops: list[NDArray[np.uint8]] = []
        attempts = 0
        max_attempts = max(num_samples * 25, 500)

        while len(crops) < num_samples and attempts < max_attempts:
            attempts += 1
            frame = self._camera.read()
            if frame is None:
                time.sleep(0.02)
                continue

            faces = self._detector.detect(frame)

            if len(faces) != 1:
                # Reject: zero or multiple faces
                time.sleep(0.02)
                continue

            # Crop the single detected face
            face = faces[0]
            x, y, w, h = face.bbox
            fh, fw = frame.shape[:2]
            x = max(0, x)
            y = max(0, y)
            w = min(w, fw - x)
            h = min(h, fh - y)

            if w < 30 or h < 30:
                continue  # Too small

            crop = frame[y : y + h, x : x + w]
            crops.append(crop)

            # Save crop to disk
            filename = f"{len(crops):03d}.png"
            filepath = save_dir / filename
            cv2.imwrite(str(filepath), crop)

            # Record sample metadata
            _ = FaceSample(
                sample_id=str(uuid.uuid4()),
                person_id=person_id,
                file_path=str(filepath),
                captured_at=time.time(),
            )
            logger.info("Captured face sample %d/%d", len(crops), num_samples)
            time.sleep(0.08)

        return crops

    def _next_label(self) -> int:
        """Determine the next available integer face label."""
        active = self._identity_repo.list_active_persons()
        if not active:
            return 0
        return max(p.face_label for p in active) + 1
