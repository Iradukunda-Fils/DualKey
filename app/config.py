# SPDX-License-Identifier: MIT
"""System configuration loader.

Loads SystemConfig from environment variables with validation.
Follows the parameter reference in DOC-07-CONFIG.

Reference: DOC-07-CONFIG (docs/07-operations/configuration.md)
"""

from __future__ import annotations

import logging
import os

from app.domain.models import SystemConfig

logger = logging.getLogger(__name__)


def load_config() -> SystemConfig:
    """Load SystemConfig from environment variables with defaults.

    Environment variable mapping follows DOC-07-CONFIG exactly.
    Invalid values fall back to defaults with a warning log.

    Returns:
        A validated, frozen SystemConfig instance.
    """
    config = SystemConfig(
        verification_window_s=_float_env("DUALKEY_WINDOW_SEC", 10.0),
        door_hold_s=_float_env("DUALKEY_HOLD_SEC", 3.0),
        required_consistent_matches=_int_env("DUALKEY_MATCH_COUNT", 3),
        lbph_threshold=_float_env("DUALKEY_LBPH_THRESHOLD", 75.0),
        sface_threshold=_float_env("DUALKEY_SFACE_THRESHOLD", 0.363),
        camera_index=_int_env("DUALKEY_CAMERA_INDEX", 0),
        serial_port=os.environ.get("DUALKEY_SERIAL_PORT", "/dev/ttyUSB0"),
        serial_baud=_int_env("DUALKEY_SERIAL_BAUD", 115200),
        heartbeat_interval_s=_float_env("DUALKEY_HB_INTERVAL", 1.0),
        heartbeat_timeout_s=_float_env("DUALKEY_HB_TIMEOUT", 3.0),
        allow_multiple_faces=_bool_env("DUALKEY_ALLOW_MULTI", default=False),
    )

    _validate(config)
    return config


def _validate(config: SystemConfig) -> None:
    """Validate configuration ranges per DOC-07-CONFIG."""
    if not 3.0 <= config.verification_window_s <= 30.0:
        logger.warning(
            "verification_window_s=%.1f outside [3.0, 30.0]",
            config.verification_window_s,
        )

    if not 1.0 <= config.door_hold_s <= 10.0:
        logger.warning(
            "door_hold_s=%.1f outside [1.0, 10.0]",
            config.door_hold_s,
        )

    if config.required_consistent_matches < 1:
        logger.warning(
            "required_consistent_matches=%d < 1",
            config.required_consistent_matches,
        )

    if config.lbph_threshold <= 0.0:
        logger.warning("lbph_threshold=%.1f must be positive", config.lbph_threshold)


def _float_env(key: str, default: float) -> float:
    """Read a float from an environment variable."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r, using default %.3f", key, raw, default)
        return default


def _int_env(key: str, default: int) -> int:
    """Read an int from an environment variable."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r, using default %d", key, raw, default)
        return default


def _bool_env(key: str, *, default: bool) -> bool:
    """Read a boolean from an environment variable."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.lower() in ("true", "1", "yes")
