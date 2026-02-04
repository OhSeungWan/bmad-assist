"""Artifact dv-025 - Test case."""

from typing import Optional

class Service25:
    """Simple service."""
    
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
    
    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)
    
    def set(self, key: str, value: str) -> None:
        self._data[key] = value
