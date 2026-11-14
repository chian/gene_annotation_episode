"""Original recursive scientific role with its own ordinary decision task."""
from .source_contracts import ROLE, ROLES, VERSION
from .configuration import ScientificConfiguration
from .binding_record import ScientificBindingRecord
from .assignments import ScientificAssignments
from .saved_identity import ScientificSavedIdentity
from .instructions import ScientificInstructions
from .tools import ScientificTools
from .facts import ScientificFacts
from .report_validation import ScientificReportValidation
from .credit import ScientificCredit
from .references import ScientificReferences
from .decision_source import ScientificDecisionSource

class ScientificProcessEpisodes(ScientificConfiguration, ScientificBindingRecord, ScientificAssignments, ScientificSavedIdentity, ScientificInstructions, ScientificTools, ScientificFacts, ScientificReportValidation, ScientificCredit, ScientificReferences):
    """One recursive C7 role with parent-selected A/P and actual tool assignment data."""
    roles = ROLES
    entry_roles = ROLES
    binding_path = 'scientific_process'
    commissioning_parent = 'annotation'
    decision_source_type = ScientificDecisionSource


    @staticmethod
    def child_message_exchange(role):
        if role == 'literature':
            from .to_child_published_evidence_assessment import prepare_request
            from .from_child_published_evidence_assessment import admit_return
            return prepare_request, admit_return
        return None

__all__ = ["ScientificProcessEpisodes", "ROLE", "ROLES", "VERSION"]


# Exact private declaration identity; custom callbacks retain runtime fallback.
_declared_child_message_exchange = vars(ScientificProcessEpisodes)["child_message_exchange"]
