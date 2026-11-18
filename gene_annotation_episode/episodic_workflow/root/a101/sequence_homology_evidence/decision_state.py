"""Own fresh scientific presentation and original saved-credit compatibility."""
from __future__ import annotations
from collections.abc import Mapping

class ScientificDecisionState:

    def credit_presentation(self, context=None):
        saved_root_credit = isinstance(context, Mapping) and isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit'
        if len(self.path) == 1 or saved_root_credit:
            from .standalone_credit_presentation import StandaloneScientificPresentation
            return StandaloneScientificPresentation
        from .commissioned_credit_presentation import CommissionedScientificPresentation
        return CommissionedScientificPresentation

    def decision_state(self, view):
        return self.credit_presentation().decision_state(self, view)
