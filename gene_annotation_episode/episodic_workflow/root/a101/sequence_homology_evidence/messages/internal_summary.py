"""Where the episode stands, as a pure function of the loop's view: the commission, one row per completed unit
(a selected tool, a reasoning commit, a revision of the process selection or a child commission), what each child
reported, the records this episode committed, the handoff records its children returned, the working state of the
scope and the controller's yield table.

Carried from the old ``internal_summary.py`` (the ``sequence_homology_evidence`` block of the decision context:
selection, initial selection digest, the assignment, the permitted children), ``decision_state.py``,
``standalone_credit_presentation.py`` and ``commissioned_credit_presentation.py`` (goal, scope, working_state,
visible_record_refs, last_local_outcome, controller state, credit binding). The library entries the selection
refers to (evidence axis, thought pattern) are read by ``task.decide`` from the process library of the settings;
the summary holds the selection. The old standalone presentation of proposed annotations, annotation comparisons
and the root's arms is the root episode's; the old own-attempt lookup (``episode.history``) is this unit list,
paged in ``task.decide``. The old ``time_accounting`` is ``ctx.clock`` in ``task.decide``."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    scientific_digest)

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    ALL, axis_features)

from ..credit import A101SequenceCredit
from ..task import CHILD_SLOTS

EXECUTED = ('completed', 'partial')
EVIDENCE_RECORD_TYPES = ('observation', 'assessment')


def internal_summary(view):
    records = view.records
    parent = view.parent_input
    units, child_reports, committed, handoff_refs, last = [], [], [], [], None
    for position, outcome in enumerate(view.outcomes):
        if outcome['kind'] == 'tool':
            result = outcome['outcome']
            row = {'position': position, 'kind': 'tool', 'tool': outcome['tool'],
                   'selected': outcome['arguments'].get('tool'), 'status': result['status'],
                   'record_refs': list(result['record_refs']), 'feedback': result.get('feedback')}
            if outcome['tool'] == 'reason' and result['status'] in EXECUTED:
                committed.extend(ref for ref in result['record_refs'] if ref not in committed)
        else:
            report = outcome['report']
            row = {'position': position, 'kind': 'child', 'slot': outcome['slot'], 'status': 'completed',
                   'credit': report['credit'], 'record_refs': list(report['record_refs'])}
            child_reports.append({'slot': outcome['slot'], **report})
            handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
        units.append(row)
        last = row
    held = [ref for ref in records.refs() if not ref.startswith('row_')]
    assignment = {'scope': parent['scope'], 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    details = A101SequenceCredit().read_details(records, parent['scope'], known_record_refs=held, assignment=assignment,
                                                details_limit=ALL, details_offset=0)
    return {**parent,
            'path_depth': len(view.path),
            'initial_selection_sha256': scientific_digest(parent['selection']),
            'permitted_children': sorted(CHILD_SLOTS),
            'units': units, 'last_local_outcome': last, 'child_reports': child_reports,
            'committed_record_refs': committed, 'handoff_refs': handoff_refs,
            'held_record_refs': held,
            'evidence_refs': [row['id'] for kind in EVIDENCE_RECORD_TYPES for row in records.list(kind)],
            'working_state': records.reasoning_view(parent['scope']),
            'reasoning_schema': records.reasoning_schema(),
            'credit_binding': A101SequenceCredit().as_record(), 'axis_findings': axis_features(details),
            'units_consumed': view.units_consumed,
            'action_yields': (None if view.controller_state is None
                              else yield_table(view.controller_state, forecast_unit='native_correspondence_credit'))}

