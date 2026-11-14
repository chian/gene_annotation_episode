"""Actual annotation projector and factual credit selection."""
from __future__ import annotations

def credit_view(self, source):
    projector = self.scientific_projector_for_context(self.binding_context(source))
    result = self.projection_view(projector, source.scope,
        **self.projection_arguments(source))
    return result
