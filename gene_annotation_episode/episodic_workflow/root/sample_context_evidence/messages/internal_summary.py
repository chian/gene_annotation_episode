"""Where the head stands, as a pure function of the loop's view: what the parent commissioned, the process the selection
names (the evidence axis, the thought pattern and the selected tools, from the first lookup), the assessments the
episode knows, the records and sources it holds, the first page of its own outcomes, the controlled features of the sheets saved (own and the
children's), the preparations of revised selections, what its children returned, the finding progress the credit counts and the
yield table.

Carried from the old ``internal_summary.py`` (``ScientificSummary.decision_context``: the ``sample_context_evidence``
block with the selection, the evidence axis, the thought pattern and the tools), ``decision_inputs.py``
(``build_decision_inputs``: goal, scope, current credit, ``investigation_progress`` with ``retained_finding_count``,
``inactive_dependencies`` and ``detail_pages``, ``credit_binding``, the last local outcome, ``visual_evidence``, the
controller), ``presentation_fields.py`` (``frame_for``: the own form, the child forms and ``source_contributions``) and
``source_references.py`` (``initial_references``: the evidence references and the proposed annotation). The old reads
of ``runtime_actions`` are the unit outcomes of ``view``. ``known_assessment_refs`` is the old ``_State.known``: the
assessments the episode's own outcomes returned and its children's findings named, never the inherited ones.

Not carried: the old ``standalone_presentation`` (a root-shaped frame of arms, annotation credits, root score and
proposed annotations, chosen at path length 1 or for credit mode ``annotation_axis_credit``: it presents the root's
state, which this episode does not hold), ``annotation_support_routes`` (``services.scientific_support_routes``, for an
axis entry that is not an instruction entry: no such module is in ``episode_support/``), the contract-information
profile, ``pending_work``, the report deliveries and the native timing context (old-runner machinery or modules that
are not in ``episode_support/``).

What a child returns is controlled data only (credit, the features of its sheets with their references, the assessments
it committed with grading, the selected counts and record references); no child text reaches this episode's model."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    merged_findings, own_findings)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, credit_view
from .read_from_child import assessments

OUTCOME_PAGE_SIZE = 8
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
EXECUTED = ('completed', 'partial')



def source_custody(records, held):
    """The custody of each held source: its version, artifacts and the sources it derives from."""
    return {reference: {key: records.get(reference).get(key) for key in CUSTODY_KEYS}
            for reference in held if reference.startswith('source_')}


def internal_summary(view):
    parent = view.parent_input
    records = view.records
    held = sorted(records.refs())
    tools = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    children = [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                 'scope': outcome['message']['assignment']['scope'], **outcome['report']}
                for outcome in view.outcomes if outcome['kind'] == 'child']
    known = []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            known.extend(outcome['report']['finding']['assessment_refs'])
        elif outcome['outcome']['status'] in EXECUTED:
            known.extend(assessments(records, outcome['outcome']['record_refs']))
    known = list(dict.fromkeys(known))
    selected = [outcome['outcome'] for outcome in tools if outcome['tool'] == 'process_selection'
                and outcome['outcome'].get('status') == 'completed']
    reasons = [outcome['outcome'] for outcome in tools
               if outcome['tool'] == 'reason' and outcome['outcome']['status'] in EXECUTED]
    committed = list(dict.fromkeys(ref for outcome in reasons for ref in outcome['record_refs']))
    graded_assessments = [ref for ref in assessments(records, committed)
                          if records.get(ref)['investigation_finding']['status'] == 'retained'
                          and records.is_current(ref)]
    revisions = [{'result': outcome['outcome']['result'], 'revision_origin': outcome['outcome']['revision_origin']}
                 for outcome in tools if outcome['tool'] == 'process_revise'
                 and outcome['outcome'].get('status') == 'completed']
    last = tools[-1] if tools else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['tool'] == 'image_view'
              and last['outcome'].get('status') == 'completed' else [])
    summary = {
        'selection': parent['selection'], 'scope': parent['scope'], 'evidence_task': parent['evidence_task'],
        'proposed_annotation_ref': parent['proposed_annotation_ref'], 'evidence_refs': parent['evidence_refs'],
        'constraints': parent['constraints'], 'context': parent['context'],
        'revision_origin': parent['revision_origin'], 'received_record_refs': parent['received_record_refs'],
        'initial_references': list(dict.fromkeys([*parent['evidence_refs'], parent['proposed_annotation_ref']])),
        'assignment': {name: parent[name] for name in ('selection', 'proposed_annotation_ref', 'evidence_refs',
                                                      'constraints', 'context')},
        'process': selected[-1]['result'] if selected else None,
        'known_assessment_refs': known, 'held_record_refs': held,
        'held_source_custody': source_custody(records, held),
        'proposed_annotation_subject_refs': records.get(parent['proposed_annotation_ref'])['subject_refs'],
        'reasoning_schema': records.reasoning_schema(),
        'working_state': records.reasoning_view(parent['scope']),
        'own_outcomes': outcome_page(tools, offset=0, limit=OUTCOME_PAGE_SIZE),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual, 'revision_proposals': revisions, 'child_reports': children,
        'finding': {**merged_findings(own_findings(records), [child['finding'] for child in children]),
                    'assessment_refs': list(dict.fromkeys(
                        graded_assessments + [ref for child in children for ref in child['finding']['assessment_refs']]))},
        'committed_record_refs': list(dict.fromkeys(
            committed + [ref for child in children for ref in child.get('committed_record_refs', ())])),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
    summary['credit_binding'] = credit_binding(summary)
    progress = credit_view(summary, records)
    summary['current_credit'] = progress['credit']
    summary['investigation_progress'] = {name: progress[name] for name in
                                         ('retained_finding_count', 'inactive_dependencies', 'detail_pages',
                                          'source_contributions')}
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
