# Internal Python Port Protocols

**Document ID:** `DOC-04-PORTS`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Architectural Role of Ports

Internal interfaces define the structural typing contracts (Ports) between application use cases and external adapters. By adhering to Python's `typing.Protocol` with `@runtime_checkable`, adapters can be tested and substituted without concrete inheritance coupling.

---

## 2. Port Definitions (`app/ports/`)

### 2.1 `CameraPort` (`app/ports/camera.py`)
```python
from typing import Protocol, Optional, runtime_checkable
import numpy as np
from numpy.typing import NDArray

Frame = NDArray[np.uint8]

@runtime_checkable
class CameraPort(Protocol):
    def open(self) -> None:
        """Initializes and opens the video capture device."""
        ...

    def read(self) -> Optional[Frame]:
        """
        Captures and returns the latest video frame (BGR format).
        Returns None if frame capture fails.
        """
        ...

    def close(self) -> None:
        """Releases the camera device hardware."""
        ...
```

### 2.2 `FaceDetectorPort` (`app/ports/detector.py`)
```python
from typing import Protocol, List, Optional, Tuple, runtime_checkable
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

@dataclass(frozen=True)
class DetectedFace:
    bbox: Tuple[int, int, int, int]           # (x, y, w, h)
    confidence: float
    landmarks: Optional[NDArray[np.float32]] = None # Optional 5-point landmarks (YuNet)

@runtime_checkable
class FaceDetectorPort(Protocol):
    def detect(self, frame: NDArray[np.uint8]) -> List[DetectedFace]:
        """
        Detects faces in a BGR/Grayscale frame and returns bounding boxes,
        detection confidence scores, and optional 5-point facial landmarks.
        """
        ...

    def get_model_info(self) -> Tuple[str, str]:
        """Returns (model_id, model_version)."""
        ...
```

### 2.3 `FaceRecognizerPort` (`app/ports/recognizer.py`)
```python
from typing import Protocol, Sequence, Tuple, Optional, runtime_checkable
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

@dataclass(frozen=True)
class RecognitionResult:
    identity: Optional[str]                   # Resolved person_id or None
    score: float                              # Raw distance or similarity
    is_match: bool                            # True if score passes threshold
    confidence_level: str                     # "HIGH", "MEDIUM", "LOW"
    model_id: str                             # "lbph" or "sface"
    model_version: str                        # e.g., "1.0.0" or "opencv_zoo_2021dec"
    quality_state: str = "USABLE"             # "USABLE", "BLURRY", "OCCLUDED"

@runtime_checkable
class FaceRecognizerPort(Protocol):
    def recognize(
        self,
        face_crop: NDArray[np.uint8],
        expected_identity: Optional[str] = None
    ) -> RecognitionResult:
        """
        Extracts features/embeddings from a cropped/aligned face and matches
        against enrolled identity prototypes or classifiers.
        """
        ...

    def enroll(
        self,
        person_id: str,
        face_samples: Sequence[NDArray[np.uint8]]
    ) -> None:
        """
        Processes enrollment samples:
        - For LBPH: trains classifier with integer label mapping.
        - For SFace: extracts 128D embeddings and computes normalized mean prototype.
        """
        ...

    def save(self, artifact_path: str) -> None:
        """Serializes trained model or embedding prototypes to disk."""
        ...

    def load(self, artifact_path: str) -> None:
        """Restores model weights or embedding prototypes from disk."""
        ...

    def get_model_info(self) -> Tuple[str, str]:
        """Returns (model_id, model_version)."""
        ...
```

### 2.3 `DeviceTransportPort` (`app/ports/device_transport.py`)
```python
from typing import Protocol, List, Optional, runtime_checkable
from dataclasses import dataclass

@dataclass(frozen=True)
class DeviceEvent:
    event_type: str
    payload: dict
    event_id: str

@dataclass(frozen=True)
class DeviceCommand:
    command_id: str
    session_id: str
    decision: str
    reason: str
    door_hold_ms: int

@runtime_checkable
class DeviceTransportPort(Protocol):
    def send_access_command(self, command: DeviceCommand) -> None:
        """Dispatches an access command to the microcontroller."""
        ...

    def poll(self) -> List[DeviceEvent]:
        """Polls buffered incoming messages and returns parsed device events."""
        ...

    def is_connected(self) -> bool:
        """Returns True if the physical serial connection is open and active."""
        ...
```

### 2.4 `IdentityRepository` (`app/ports/repositories.py`)
```python
from typing import Protocol, Optional, List, runtime_checkable
from app.domain.models import Person, RFIDCard

@runtime_checkable
class IdentityRepository(Protocol):
    def get_card_owner(self, uid: str) -> Optional[Person]:
        """Retrieves the Person owning the specified active card UID."""
        ...

    def get_person(self, person_id: str) -> Optional[Person]:
        """Retrieves a Person by their unique identifier."""
        ...

    def get_person_by_label(self, face_label: int) -> Optional[Person]:
        """Retrieves a Person corresponding to an OpenCV integer label."""
        ...

    def create_person(self, person: Person) -> None:
        """Persists a new Person record."""
        ...

    def bind_card(self, card: RFIDCard) -> None:
        """Binds an RFID card to a person."""
        ...

    def list_active_persons(self) -> List[Person]:
        """Lists all active registered identities."""
        ...
```

### 2.5 `EventRepository` (`app/ports/repositories.py`)
```python
from typing import Protocol, runtime_checkable
from app.domain.models import AccessEvent

@runtime_checkable
class EventRepository(Protocol):
    def append(self, event: AccessEvent) -> None:
        """Appends an immutable audit event to persistent storage."""
        ...
```

### 2.6 `ClockPort` (`app/ports/clock.py`)
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ClockPort(Protocol):
    def now_monotonic(self) -> float:
        """Returns the current monotonic time in seconds."""
        ...
```
