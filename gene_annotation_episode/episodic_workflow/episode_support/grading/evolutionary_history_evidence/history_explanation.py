"""The historical-cause sheet: the model-judged grade of a horizontal-transfer explanation of an actual outlier.

The owner's rubric (``research/slotted_process_library/publications/2026-10-23-002/SCORING_RUBRICS_A101_A104.md``
line 84 and ``entries/A104.json`` route ``hgt_explanation_grade``; tested at ``60889621e`` in
``tests/test_evidence_axis_scoring_A101_A104.py``): explaining an outlying placement by horizontal transfer is graded
on its own ordinal sheet, ``contradicted`` 0, ``plausible_only`` 1, ``corroborated`` 2, ``unknown`` no point score
with the possible interval [0, 2]. These numbers are ordered rubric levels, not probabilities, likelihoods, referral
credit or multiplicative weights on the native tree score; the grade does not manufacture a phylogenetic tree or
target-clade support. The grade is the one LLM-judged cell of the A104 sheet: the model chooses the level and the
held records that bear on it; code computes the score and its bounds, and the sheet fills the ``historical_cause``
sub-sheet of the per-use attribution of the measurement it explains."""
from __future__ import annotations

from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc import require
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.scoring import VERSION, digest

PROVIDER = 'native.a104.history_explanation'
SCHEMA = 'a104_history_explanation_v1'
CRITERION = 'hgt_outlier_explanation'
GRADE_SCORES = {'contradicted': 0, 'plausible_only': 1, 'corroborated': 2}
LEVELS = (*GRADE_SCORES, 'unknown')
# The HGT numerical route requires an actual phylogeny: the explained measurement is a received native placement
# or history comparison.
EXPLAINED_KINDS = ('a104_placement_v1', 'a104_history_comparison_v1')
EXPLANATIONS = TableDeclaration(name='a104_history_explanations', columns=('source_ref', 'measurement_ref', 'body'),
    key=('source_ref',), record_refs=('source_ref', 'measurement_ref'))
GRADING_INSTRUCTIONS = (
    'Historical-cause grading (tool phylogeny_explain_history, criterion hgt_outlier_explanation): grade a '
    'horizontal-transfer explanation of an actual outlying placement on its own ordinal sheet. contradicted (0): '
    'received biological, source/recipient or sequence/genomic evidence contradicts the stated transfer explanation; '
    'retain that contrary evidence. plausible_only (1): actual source/recipient circumstances permit the proposed '
    'explanation, but independent evidence does not distinguish it from retained alternatives; shared environment '
    'alone can reach this level, never the next. corroborated (2): the explanation fits the actual outlying placement '
    'and source/recipient circumstances and has independent received support bearing on transfer; retain unresolved '
    'alternatives and sampling/paralog limitations. unknown (no point score, possible interval [0,2]): the outlying '
    'placement, relevant context or evidence needed to assign a level is missing; do not substitute 0. The levels are '
    'ordered rubric levels, not probabilities, and never a weight on the native tree score. A statement incompatible '
    'with vertical inheritance does not alone prove transfer or refute the proposed function. Select the measurement_ref '
    'of the native placement or history comparison it explains and the held records that bear on the grade.')


def explanation_cell(grade):
    """The judged cell: score and its bounds from the chosen level (``unknown`` keeps the possible interval)."""
    require(grade in LEVELS, 'a104_history_explanation_level_unknown')
    if grade == 'unknown':
        return {'criterion': CRITERION, 'grade': grade, 'score': None, 'status': 'partial',
                'score_bounds': {'lower': 0, 'upper': 2}, 'score_unit': 'ordinal_evidence_level'}
    score = GRADE_SCORES[grade]
    return {'criterion': CRITERION, 'grade': grade, 'score': score, 'status': 'graded',
            'score_bounds': {'lower': score, 'upper': score}, 'score_unit': 'ordinal_evidence_level'}


def publish_explanation(store, measured, grade, support_refs):
    """Save the judged sheet for one received native measurement (``measured``: ``received_measurement``)."""
    require(measured['body']['schema'] in EXPLAINED_KINDS, 'a104_history_explanation_requires_actual_phylogeny')
    require(len(support_refs) == len(set(support_refs)) and all(store.holds(ref) for ref in support_refs),
            'a104_history_explanation_support_not_received')
    # contradicted retains the contrary evidence; corroborated needs independent received support.
    require(grade not in ('contradicted', 'corroborated') or support_refs,
            'a104_history_explanation_grade_requires_received_evidence')
    body = {'schema': SCHEMA, 'version': VERSION, 'measurement_ref': measured['source_ref'],
            'target_ref': measured['body']['target_ref'], 'target_regions': measured['body']['target_regions'],
            'cell': explanation_cell(grade), 'support_refs': sorted(support_refs),
            'interpretation': 'ordinal_rubric_level; separate_from_native_tree_score; not_a_probability'}
    with store.transaction():
        artifact = store.artifact(canonical(body), 'application/json')
        reference = store.put('source', {'provider': PROVIDER, 'accession': digest(body), 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
            'retrieved_at': None, 'operand_refs': [body['target_ref']]}, origin='tool')['id']
        store.table(EXPLANATIONS).put({'source_ref': reference, 'measurement_ref': measured['source_ref'],
                                       'body': body})
    return reference


def held_explanations(reader, known):
    """The latest held judged sheet per explained measurement, in receipt order."""
    latest = {}
    for row in reader.table(EXPLANATIONS).select():
        if row['source_ref'] in known:
            latest[row['measurement_ref']] = {**row['body'], 'source_ref': row['source_ref']}
    return latest
