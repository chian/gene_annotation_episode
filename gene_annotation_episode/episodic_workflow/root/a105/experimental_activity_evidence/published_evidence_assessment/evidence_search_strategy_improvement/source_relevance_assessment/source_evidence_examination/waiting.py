"""This source episode's waiting observations."""
from __future__ import annotations

class SourceWaiting:

    @property
    def supports_wait(self):
        return False
