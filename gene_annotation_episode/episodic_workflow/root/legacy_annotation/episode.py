"""Original predefined improvement task; implicit host parent, not a specialist."""
from importlib import import_module
from .task import LegacyAnnotationTask
from .credit import source_credit_view, source_credit_binding

from .yield_estimator import controller as _controller

class LegacyAnnotationEpisodeBinding:
    roles = ('improvement',)
    entry_roles = ('improvement',)
    binding_path = 'legacy_annotation'
    commissioning_parent = 'annotation'
    decision_source_type = LegacyAnnotationTask
    source_credit_view = staticmethod(source_credit_view)
    source_credit_binding = staticmethod(source_credit_binding)
    controller = staticmethod(_controller)
