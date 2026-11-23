"""The answers an A105 literature episode holds for its commissioned literature task, and their credit.

Carried from the old ``credit.py`` of the A105 literature episodes at ``97308b94c`` (``LiteratureTaskCredit._answers``,
``lead_dispositions``, ``screening_answers``, ``_current_assessments``, ``measured_answers``,
``graded_experiment_answers``, ``assembled_answers``): ``credit_unit`` times the number of answers, finite, never
bounded, clamped or rescaled. Revision, activity and repeated reading earn nothing; annotation support stays
separate. Each episode's ``credit.py`` calls ``task_credit`` with its own summary.

The summary keys read: ``task``, ``task_key``, ``proposed_annotation_ref``, ``scope``, ``lead_source_refs`` (the
relevant lead sources, own and returned), ``screening_covered``, ``assay_sheets`` and ``aggregation_sheets`` (the
features of the current grading and aggregation sheets the Episode saved or its children returned, each sheet held).

A105 evidence processing: an accepted interpretation receives credit only through its saved subscoring sheet. An
experiment of an ``a105_experiments`` task is answered by a current grading sheet of the proposed annotation and the
experiment's assay type; a sheet this Episode saved must also match a current assessment it holds
(``_matches_grading``); a sheet a child returned was saved by the child's required grading together with the
interpretation it grades, and the child's assessments stay inside the child."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.finding_validity import (
    FindingValidity, target_eligible)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_required_grading import (
    _matches_grading)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_unknown_classification import (
    graded_share)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import (
    LiteratureA105AggregationRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)

VERSION = 'literature_local_task'
QUANTITY_PROVIDER = 'literature.a105.source_quantity'
MEASUREMENT_UNAVAILABLE_OK = {'reported_spread_unavailable', 'zero_reported_value'}


def credit_binding(task_key, task):
    """The old projector's ``as_record()``: the credit definition the model is shown."""
    unit = ('one_current_graded_assessment_per_original_experiment' if task['kind'] == 'a105_experiments'
            else 'one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
            else 'one_answer_to_original_commission')
    return {'kind': VERSION, 'task': task_key, 'credit_unit': task['credit_unit'], 'unit': unit,
            'revision_credit': False, 'activity_credit': False, 'annotation_support': 'separate'}


def current_assessments(records, summary):
    """The old ``_current_assessments``: retained current assessments of the proposed annotation among the held
    records that are eligible for the target."""
    scope, proposed = summary['scope'], summary['proposed_annotation_ref']
    known = set(records.refs())
    with FindingValidity(records, scope) as validity:
        for record in validity.current_records():
            if (record['id'] in known and record['hypothesis_ref'] == proposed
                    and record['investigation_finding']['status'] == 'retained'
                    and target_eligible(records, record, scope)):
                yield record


def assessment_answers(summary, records):
    """The first current retained assessment whose observation is in one of the task's sources and is anchored."""
    for record in current_assessments(records, summary):
        observation = records.get(record['observation_ref'])
        if (observation['source_ref'] in summary['task']['source_refs']
                and (observation.get('anchor') is not None or observation.get('visual_anchor') is not None)):
            return [{'assessment_ref': record['id'], 'source_ref': observation['source_ref']}]
    return []


def measured_answers(summary, records):
    """A held quantity sheet whose saved selection is the commissioned selection and whose cells for every
    commissioned component are populated (or unavailable for the two allowed reasons)."""
    task = summary['task']
    for source in records.list('source'):
        if source['provider'] != QUANTITY_PROVIDER:
            continue
        request = json.loads(records.get_artifact(source['request_ref']))
        if request['arguments'] != task['selection']:
            continue
        cells = json.loads(records.get_artifact(source['artifact_ref']))['sheet']['cells']
        if not set(task['components']) <= set(cells):
            continue
        if all(cells[name]['status'] == 'populated' or cells[name]['unavailable_reason'] in MEASUREMENT_UNAVAILABLE_OK
               for name in task['components']):
            return [{'sheet_ref': source['id'], 'source_ref': task['selection']['source_ref'],
                     'components': task['components']}]
    return []


def graded_experiment_answers(summary, records):
    """One answer per commissioned experiment that has a current grading sheet of the proposed annotation and the
    experiment's assay type (an own sheet matched to a current assessment)."""
    task, proposed = summary['task'], summary['proposed_annotation_ref']
    wanted = {item['experiment_ref']: item['assay_type'] for item in task['experiments']}
    own = set(LiteratureAssayGradingRepository(records).current_sheet_refs())
    assessments = list(current_assessments(records, summary)) if own else []
    completed = {}
    for features in summary['assay_sheets']:
        experiment, sheet_ref = features['experiment_refs'][0], features['sheet_refs'][0]
        if features['assertion_refs'] != [proposed] or wanted.get(experiment) != features['evidence_type']:
            continue
        if sheet_ref not in own:
            completed[experiment] = {'experiment_ref': experiment, 'sheet_ref': sheet_ref}
            continue
        arguments = LiteratureAssayGradingRepository(records).read(sheet_ref)['selection']
        for assessment in assessments:
            if _matches_grading(records, assessment['id'], arguments):
                completed[experiment] = {'experiment_ref': experiment, 'sheet_ref': sheet_ref}
    return list(completed.values())


def assembled_answers(summary, records):
    """A current aggregation sheet of the proposed annotation over exactly the commissioned experiments whose
    selected metrics all come from current grading sheets."""
    task, proposed = summary['task'], summary['proposed_annotation_ref']
    current_grades = {features['sheet_refs'][0] for features in summary['assay_sheets']}
    for features in summary['aggregation_sheets']:
        arguments = LiteratureA105AggregationRepository(records).read(features['sheet_refs'][0])['selection']
        if (arguments['assertion_ref'] != proposed
                or set(task['experiment_refs']) != {item['experiment_ref'] for item in arguments['experiments']}):
            continue
        selected = [experiment['metrics'][metric] for experiment in arguments['experiments'] for metric in task['metrics']]
        if all(item is not None and item['sheet_ref'] in current_grades for item in selected):
            return [{'sheet_ref': features['sheet_refs'][0], 'experiment_refs': task['experiment_refs'],
                     'metrics': task['metrics']}]
    return []


def answers(summary, records):
    """The old ``LiteratureTaskCredit._answers``."""
    task = summary['task']
    kind, answer = task['kind'], task.get('answer_kind')
    if kind == 'verified_source_leads':
        return list(summary['lead_source_refs'])
    if answer == 'screening':
        return [task['examined']] if summary['screening_covered'] else []
    if answer == 'assessment':
        return assessment_answers(summary, records)
    if answer == 'measurement':
        return measured_answers(summary, records)
    if kind == 'a105_experiments':
        return graded_experiment_answers(summary, records)
    return assembled_answers(summary, records)


def task_credit(summary, records):
    """``credit_unit`` for each answer to the commissioned task."""
    value = summary['task']['credit_unit'] * len(answers(summary, records))
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value



def classified_credit_binding(task_key, task):
    """The credit definition the model is shown where credit rests on the classification of unknown fields."""
    binding = credit_binding(task_key, task)
    if task['kind'] != 'a105_experiments':
        return binding
    return {**binding, 'unit': 'graded_field_share_of_the_current_sheet_per_original_experiment',
            'entered_field_credit': 'its_share', 'justified_unknown_field_credit': 'its_share',
            'unjustified_unknown_field_credit': 'none', 'unclassified_unknown_field_credit': 'none'}


def graded_experiment_shares(summary, records):
    """For each answered experiment of an ``a105_experiments`` task, the share of the credit unit its current
    sheet earns (``literature_unknown_classification.graded_share`` of the sheet's features: its entered fields and
    the unknown fields its classification holds justified, over all its fields)."""
    by_sheet = {features['sheet_refs'][0]: features for features in summary['assay_sheets']}
    return [graded_share(by_sheet[answer['sheet_ref']]) for answer in graded_experiment_answers(summary, records)]


def classified_task_credit(summary, records):
    """``credit_unit`` for each answer to the commissioned task; for an ``a105_experiments`` task ``credit_unit``
    times the graded share of each answered experiment's current sheet. Credit rests on the classification of the
    fields a sheet leaves unknown, not on the sheet existing: unknown fields held unjustified earn nothing, so a
    sheet of nothing but unjustified unknowns earns nothing; unknown fields held justified earn their share (the
    partial or unresolved grading AGENTS.md requires for what a source does not give)."""
    task = summary['task']
    amount = (math.fsum(graded_experiment_shares(summary, records)) if task['kind'] == 'a105_experiments'
              else len(answers(summary, records)))
    value = task['credit_unit'] * amount
    if not math.isfinite(value):
        raise ValueError('literature_finite_task_credit_required')
    return value

__all__ = ['credit_binding', 'classified_credit_binding', 'answers', 'task_credit', 'graded_experiment_shares',
           'classified_task_credit']
