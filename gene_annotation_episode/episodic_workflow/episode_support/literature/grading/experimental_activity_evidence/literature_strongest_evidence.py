"""The evidence held on a subscoring sheet for one proposed annotation, as the measure of what an episode above the page
has learned (owner, 2026-11-21: up the chain credit is "how much more you learn and gain in terms of overall knowledge
and certainty, not trading credit gain"; "credit will have to be for strongest evidence at closest relationship"; "closest
says the most, furthest adds some evidence but weakly"; "so it's additive weighed by distance").

The strength of one result is ``log_ratio * weight * effect_support`` when it supports or opposes, else 0 (the magnitude
``literature_row`` scores it with). The weight already carries ``literature_target.identified_closeness`` (how close the
assayed protein is to the claim's target, smooth, never a gate), so a strong result on the closest protein counts the most
and a result on a more distant protein counts a little. Support and opposition both count: either is knowledge of the
annotation.

``evidence_held(records, sheet_state_refs, assertion_ref)`` reads the persisted row states (each an artifact read through
the custody reader it is handed) and returns, over the rows of ``assertion_ref``, the sum over the independent groups of
the row's member results (``literature_row.dependence_groups``) of the STRONGEST member of each group. Independent groups
add; dependent results (one group) do not add twice, and a repeat or a weaker dependent result adds nothing.

This is not the row's score. The row's support and opposition are means over all members of a group, so a member of
unknown direction dilutes them (OWNER_DECISION 4d): the score of the annotation may fall when a weak result arrives. What
has been learned does not fall with it (found in the real run a105_head_popz_chpt_10: a page added results of unknown
direction to a row it was given, the row total fell from 0.188 to 0.113, and the search above it failed with
``accumulation_credit_cannot_fall``).

``evidence_gain`` is what the results an episode's held sheet has added contribute over the results of the sheet it was
given at its start: for each independent group of the held sheet, the strongest member less the strongest member that was
already on the given sheet (0 when none was). A later state carries its member results forward, so the given results are
among the held ones and the gain is never negative; results found dependent later are counted as dependent on both sides,
so learning of a dependence is not a loss. A row has one current state per sheet and annotation: when the references hold
several, the last one stands. No sheet for the annotation gives 0.0. No constant is introduced; nothing is bounded, clamped
or rescaled."""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row import (
    dependence_groups)

DIRECTED = ('supports', 'opposes')


def _strength(result):
    if result['direction'] not in DIRECTED:
        return 0.0
    return result['log_ratio'] * result['weight'] * result['effect_support']


def _members(records, sheet_state_refs, assertion_ref):
    """{sheet: the member results of the row of ``assertion_ref`` on that sheet}; the last state of a row stands."""
    members = {}
    for ref in sheet_state_refs:
        state = json.loads(records.get_artifact(ref))
        if state['row']['assertion_ref'] == assertion_ref:
            members[state['row']['sheet']] = state['member_results']
    return members


def evidence_held(records, sheet_state_refs, assertion_ref):
    return math.fsum(max(_strength(result) for result in group)
                     for results in _members(records, sheet_state_refs, assertion_ref).values()
                     for group in dependence_groups(results))


def evidence_gain(records, held_state_refs, given_state_refs, assertion_ref):
    """What the results added to the sheet an episode holds contribute over the results of the sheet it was given."""
    held = _members(records, held_state_refs, assertion_ref)
    given = _members(records, given_state_refs, assertion_ref)
    gains = []
    for sheet, results in held.items():
        before = {result['result_ref'] for result in given.get(sheet, ())}
        for group in dependence_groups(results):
            gains.append(max(_strength(result) for result in group)
                         - max((_strength(result) for result in group if result['result_ref'] in before), default=0.0))
    return math.fsum(gains)
