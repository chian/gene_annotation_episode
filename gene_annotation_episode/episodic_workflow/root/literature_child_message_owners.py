"""Select only authentic Root Literature parent/child message owners.

Unrelated axes, providers and custom bindings return None here and use the
shared host exchange. This selector declares no new available role or commissioning edge.
"""
def exchange_for_child(workflow, source, role, *, owner=None):
    _nominal = _selector_context(workflow, source, role, owner)
    if _nominal is None:
        return None
    registry, path = _nominal
    from .published_evidence_assessment.family import ROLES, classes
    from .literature_families import parent_families
    if role in ('launch', 'results', 'launch_api', 'launch_local', 'launch_hpc'):
        return execution_exchange_for_child(workflow, source, role, owner=owner)
    if role not in ROLES:
        return None
    parent = _cached_parent(registry, source, path)
    if any(type(parent) is declared for family in parent_families() for declared in family.classes()):
        return _declared_exchange(parent, role)
    if role == 'literature' and path[-1][0] == 'scientific_process':
        from .scientific_process.episode import ScientificProcessEpisodes
        if type(parent) is ScientificProcessEpisodes:
            return _declared_exchange(parent, role)
    if _implicit_parent(source, path) == 'annotation' and (role == 'literature'):
        from .operational_child_message_owners import _registered_child
        child = _registered_child(registry, 'annotation', role, owner)
        if type(child) is classes()[0]:
            from .to_child_published_evidence_assessment import prepare_request
            from .from_child_published_evidence_assessment import admit_return
            return (prepare_request, admit_return)
    return None


def execution_exchange_for_child(workflow, source, role, *, owner=None):
    _nominal = _selector_context(workflow, source, role, owner)
    if _nominal is None:
        return None
    registry, path = _nominal
    from .operational_child_message_owners import _registered_child
    parent = _cached_parent(registry, source, path)
    from .published_evidence_assessment.episode import LiteratureEpisode as Parent_published_evidence_assessment
    from .published_evidence_assessment.execution_job_submission.episode import ExecutionSubmissionBinding as Launch_published_evidence_assessment
    from .scientific_process.published_evidence_assessment.episode import LiteratureEpisode as Parent_scientific_process_published_evidence_assessment
    from .scientific_process.published_evidence_assessment.execution_job_submission.episode import ExecutionSubmissionBinding as Launch_scientific_process_published_evidence_assessment
    if any((type(parent) is _expected_type for _expected_type in (Parent_published_evidence_assessment, Launch_published_evidence_assessment, Parent_scientific_process_published_evidence_assessment, Launch_scientific_process_published_evidence_assessment))):
        child = _registered_child(registry, _plain_field(parent, 'binding_path'), role, owner)
        return _declared_exchange(parent, role, child_binding=child)
    return None

from .library.nominal_child_messages import (selector_context as _selector_context, cached_parent as _cached_parent, registered_child as _cached_child, declared_roles as _declared_roles, declared_exchange as _declared_exchange, homology_child_path as _homology_child_path, implicit_parent as _implicit_parent, _plain_field, _static)
