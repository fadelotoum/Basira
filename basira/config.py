"""Central settings for Basira."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraConfig:
    """Camera selection and window settings."""

    preferred_source: int = 1
    fallback_source: int = 0
    window_title: str = "Basira | Live Vision"
