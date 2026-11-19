"""What the scientific parent gives: the results assignment, with the handoff of the work already submitted.

``ASSIGNMENT_FORM`` has one field per property of the old ``RESULTS_SCHEMA`` (old ``from_parent.py``
``assignment_schema``), under the same name. ``handoff`` is an ``execution_handoff_v1`` record; it holds nulls
(``failure``, ``version``, ``content_sha256`` of an input), which the form has no type for, so it is one untyped
``record`` field. The adapter that serves the episode is the one the handoff's ``resource_selection`` names
(old ``_adapter``); the service ``resources`` selects it. The subject ``scope`` and the parent's ``initial_report``
are fields of the commission's message, as in the old request message."""
from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import RESULTS_VERSION

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', RESULTS_VERSION),
    'handoff': Field('record', 'The execution_handoff_v1 of the work whose results are acquired (fixed)'),
    'requested_data_selector': Field('record', 'Which data the parent requests (fixed)'),
})


def read_from_parent(assignment, message):
    return {**assignment, 'scope': message['scope'],
            'initial_report': message['initial_report'] if 'initial_report' in message else None}
