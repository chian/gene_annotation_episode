"""The page assignment of the source evidence examination over the held A108 world of its ordered-reading child
(``source_coverage_improvement/tests/a108_world.py``), the settings of the subtree and the services the run's caller
supplies. Nothing is faked."""
import importlib

from ..source_coverage_improvement.tests.a108_world import SERVICES, SETTINGS, held_world  # noqa: F401

MODULE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(MODULE + '.episode').SourceEvidenceExamination
PATH = EPISODE.binding_path
CONTINUATION = {path: SETTINGS for path in (PATH, *EPISODE.child_slots.values())}


def leads_task():
    return {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'kind': 'verified_source_leads',
            'credit_unit': 1.0}


def page_assignment(world, task, requested=('evidence_amount',)):
    paper = world['paper']
    assignment = {'version': 'page_assignment_v1', 'source_ref': paper['id'], 'representation': 'original',
                  'artifact_ref': paper['artifact_ref'], 'question_context_refs': [world['organism']['id']],
                  'prior_delivery_refs': [], 'literature_task': task, 'proposed_annotation_ref': world['claim']['id'],
                  'scope': world['scope'], 'received_record_refs': list(dict.fromkeys(world['held']))}
    if requested:
        assignment['requested_a108_grading_components'] = list(requested)
    return assignment


def bindings():
    """The parent and its three children, as the run's registry needs them."""
    package = MODULE
    children = [importlib.import_module(package + '.' + slot + '.episode') for slot in EPISODE.child_slots]
    classes = [next(value for value in vars(module).values()
                    if isinstance(value, type) and value.__module__ == module.__name__) for module in children]
    return [EPISODE(), *(cls() for cls in classes)]
