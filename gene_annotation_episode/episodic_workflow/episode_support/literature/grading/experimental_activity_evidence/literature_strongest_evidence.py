"""The evidence held on a subscoring sheet for one proposed annotation, as the measure of what an episode above the page
has learned (owner, 2026-11-21: up the chain credit is "how much more you learn and gain in terms of overall knowledge
and certainty, not trading credit gain"; "credit will have to be for strongest evidence at closest relationship"; "closest
says the most, furthest adds some evidence but weakly"; "so it's additive weighed by distance").

``evidence_held(records, sheet_state_refs, assertion_ref)`` reads the persisted row states (each an artifact read through
the custody reader it is handed) and returns, over the rows of ``assertion_ref``,

    row['support'] + row['opposition']

These are the row's own totals as ``literature_row`` computes them: each independent group of results adds its magnitude
(the graded strength of the measurement times the result's weight), and the weight already carries
``literature_target.identified_closeness`` (how close the assayed protein is to the claim's target, smooth, never a gate).
So the measure is additive and weighed by distance: a strong result on the closest protein adds the most, a result on a
more distant protein adds a little, and nothing adds nothing. Support and opposition both count: either is knowledge of the
annotation. Dependent results (one group) are pooled inside the row and do not add twice.

A row has one current state: when the references hold several states of the same row, the last one stands (a later state
carries its member results forward). No sheet for the annotation gives 0.0, and so does a row whose results state no
direction (``row_status`` 'unknown': the row has no totals). No constant is introduced; nothing is bounded,
clamped or rescaled beyond what the row defines.

``evidence_gain`` is what an episode's held sheet adds to the sheet it was given at its start."""
import json


def evidence_held(records, sheet_state_refs, assertion_ref):
    rows = {}
    for ref in sheet_state_refs:
        row = json.loads(records.get_artifact(ref))['row']
        if row['assertion_ref'] == assertion_ref:
            rows[row['row_ref']] = row      # the last state of a row stands
    # A row whose results state no direction (row_status 'unknown') has no totals (null): it holds no evidence either way.
    return sum(row['support'] + row['opposition'] for row in rows.values() if row['support'] is not None)


def evidence_gain(records, held_state_refs, given_state_refs, assertion_ref):
    """What the sheet an episode holds adds to the evidence of the sheet it was given at its start (given none: 0)."""
    return evidence_held(records, held_state_refs, assertion_ref) - evidence_held(records, given_state_refs, assertion_ref)
