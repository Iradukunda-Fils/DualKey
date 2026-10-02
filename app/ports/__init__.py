# SPDX-License-Identifier: MIT
"""Port interfaces -- hexagonal architecture boundary contracts.

All ports are defined as typing.Protocol (structural subtyping) so
adapters need only implement the method signatures, never inherit.
"""

from app.ports.camera import CameraPort, Frame
from app.ports.clock import ClockPort
from app.ports.detector import DetectedFace, FaceDetectorPort
from app.ports.device_transport import DeviceCommand, DeviceEvent, DeviceTransportPort
from app.ports.recognizer import FaceRecognizerPort, RecognitionResult
from app.ports.repositories import EventRepository, IdentityRepository

__all__ = [
    "CameraPort",
    "ClockPort",
    "DetectedFace",
    "DeviceCommand",
    "DeviceEvent",
    "DeviceTransportPort",
    "EventRepository",
    "FaceDetectorPort",
    "FaceRecognizerPort",
    "Frame",
    "IdentityRepository",
    "RecognitionResult",
]
