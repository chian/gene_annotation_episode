"""A105 main scoring sheet: merger (2). Pure: arguments in, controlled records out; no Store or custody access, no I/O.

Implements OWNER_DECISIONS 6 and 16 (cross-class dependence at merger 2: rows resting on the same dataset_ref, then the same
source_ref, share one dependence unit; CROSS_CLASS_COLLAPSE_RULE) and, with literature_axis_output, OWNER_DECISION 11
(the per-candidate credit comes out of this table unchanged). It runs at the page in the same step as the subscoring-sheet
update (OWNER_DECISION 10).

The main sheet is a list of MAIN_ROW_FIELDS rows: one row per class (sheet) for each candidate (assertion_ref).
Per row the SCORE quantities (support, opposition, net, row_status, weight) are copied from the subscoring row; the
CREDIT quantities (resolution, credit) are copied or derived from its resolution. The two are never mixed: nothing here
reads credit to compute a score, and nothing reads a sign or magnitude to compute credit.

Choices of this file (flagged in the builder report):
* A main row carries only its own evidence. Rows sharing a dependence unit are collapsed when the axis sums them
  (literature_axis_output: mean over the unit's known rows, then sum over units); dependence_unit_ref marks the unit
  ('dataset:<ref>' if the row rests on a dataset_ref, else 'source:<ref>'; null when the row states neither).
* credit of a main row = R(after) - R(before) of this update; before comes from prior_main (no prior row = 0.0).
  A row whose row_ref is unchanged against prior_main changes nothing and earns credit 0.0. The subscoring row_ref is
  content-addressed (literature_row.row_ref_of: it holds a hash of the member result refs), so equal refs mean equal content.
* A commissioned class (classes_needed) with no subscoring row gets a placeholder row: status unknown, null scores,
  weight 0.0, resolution 0.0 (the class counts R = 0), credit 0.0, source_row_ref 'no_row'. This is how N_k reaches the axis.
* classes_needed is a mapping assertion_ref -> classes commissioned for it. A row of a candidate or class that was not
  commissioned fails (no repair, no fallback).
* Input rows are COMPLETE ROW_FIELDS rows (weight, resolution, credit, independence_known and the qualitative fields
  included). The page stamps their dataset_ref / source_ref (MAIN_ROW_INPUT_KEYS, not in ROW_FIELDS) as optional keys of
  the row mapping; they are removed before the row is validated with validate_row.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLASSES,
    CROSS_CLASS_COLLAPSE_RULE,
    MAIN_ROW_INPUT_KEYS,
    NO_ROW_REF,
    normalize_identity_ref,
    validate_main_row,
    validate_row,
)

_COPIED = ('row_status', 'support', 'opposition', 'net', 'weight', 'resolution', 'experiments', 'independent_groups')


def _dependence_split(row):
    """Return (the row without dependence keys, its dependence_unit_ref or None): dataset_ref first, then source_ref."""
    if not isinstance(row, dict):
        raise ValueError('row must be a mapping')
    keys = {name: row.get(name) for name in MAIN_ROW_INPUT_KEYS}
    plain = {name: value for name, value in row.items() if name not in MAIN_ROW_INPUT_KEYS}
    validate_row(plain)
    unit = None
    for name in CROSS_CLASS_COLLAPSE_RULE['key_order']:
        if keys[name] is not None:
            unit = f"{name.removesuffix('_ref')}:{keys[name]}"
            break
    return plain, unit


def _same_target(first, second):
    return normalize_identity_ref(first) == normalize_identity_ref(second)


def _targets(targets, needed):
    """The commissioned target of each commissioned candidate (OWNER_DECISION 18): {assertion_ref: normalized target_id}."""
    if targets is None:
        return {}
    if not isinstance(targets, dict):
        raise ValueError('targets must be a mapping assertion_ref -> target_id')
    for assertion_ref in targets:
        if assertion_ref not in needed:
            raise ValueError(f'targets names {assertion_ref!r}, which is not a commissioned candidate')
    return {assertion_ref: normalize_identity_ref(target) for assertion_ref, target in targets.items()}


def _placeholder(sheet, assertion_ref, target):
    return {
        'sheet': sheet, 'assertion_ref': assertion_ref, 'target_id': target,
        'row_ref': f'main:{sheet}:{assertion_ref}:{NO_ROW_REF}', 'source_row_ref': NO_ROW_REF,
        'row_status': 'unknown', 'support': None, 'opposition': None, 'net': None,
        'weight': 0.0, 'resolution': 0.0, 'credit': 0.0,
        'experiments': 0, 'independent_groups': 0, 'dependence_unit_ref': None,
    }


def _commissioned(classes_needed):
    if not isinstance(classes_needed, dict) or not classes_needed:
        raise ValueError('classes_needed must be a non-empty mapping assertion_ref -> classes')
    for assertion_ref, classes in classes_needed.items():
        if not isinstance(classes, (list, tuple, set, frozenset)) or not classes:
            raise ValueError(f'classes_needed[{assertion_ref}] must hold at least one class')
        for sheet in classes:
            if sheet not in CLASSES:
                raise ValueError(f'classes_needed[{assertion_ref}] names a class outside CLASSES: {sheet!r}')
    return {assertion_ref: set(classes) for assertion_ref, classes in classes_needed.items()}


def merge_main(rows, classes_needed, prior_main=None, targets=None):
    """Merger (2) (OWNER_DECISION 6, with 7 and 11 completed in literature_axis_output).

    rows: the complete subscoring rows (ROW_FIELDS), one per (sheet, assertion_ref), optionally with the input keys
    'dataset_ref' / 'source_ref' (MAIN_ROW_INPUT_KEYS) stamped by the page.
    classes_needed: {assertion_ref: classes commissioned for it} (N_k).
    prior_main: the main sheet before this update, or None for the first fill (before = no rows).
    targets: {assertion_ref: the commissioned target_id} (OWNER_DECISION 18), or None. The contract's signature has no
    target source for a placeholder (classes_needed carries none), so this optional last argument is it. A placeholder
    needs its candidate's target: without one ValueError. When given, every row's target must equal it.
    Every main row carries target_id: a built row copies its source row's, which must equal the prior row's and the
    commissioned target; the rows of one candidate share one target; a mismatch raises ValueError (no repair).
    Returns the updated main sheet: a list of validated MAIN_ROW_FIELDS rows, one per commissioned class for each
    candidate, ordered by assertion_ref then CLASSES order. A row whose row_ref equals the prior source_row_ref is
    carried unchanged with credit 0.0; a new or changed row has credit = resolution(after) - resolution(before)."""
    needed = _commissioned(classes_needed)
    commissioned = _targets(targets, needed)
    prior = {}
    for main_row in prior_main or ():
        validate_main_row(main_row)
        if main_row['source_row_ref'] == NO_ROW_REF:
            continue   # a placeholder is rebuilt from classes_needed
        prior[(main_row['sheet'], main_row['assertion_ref'])] = main_row

    table = {}
    for row in rows:
        plain, unit = _dependence_split(row)
        key = (plain['sheet'], plain['assertion_ref'])
        if key in table:
            raise ValueError(f'two subscoring rows for {key}: the sheet holds one row per class and candidate')
        if key[1] in commissioned and not _same_target(plain['target_id'], commissioned[key[1]]):
            raise ValueError(f"row {plain['row_ref']} is about target {plain['target_id']!r}, the commissioned target of {key[1]} is {commissioned[key[1]]!r} (OWNER_DECISION 18)")
        before = prior.get(key)
        if before is not None and not _same_target(before['target_id'], plain['target_id']):
            raise ValueError(f"row {plain['row_ref']} is about target {plain['target_id']!r}, its prior main row is about {before['target_id']!r} (OWNER_DECISION 18)")
        if before is not None and before['source_row_ref'] == plain['row_ref']:
            table[key] = dict(before, credit=0.0, dependence_unit_ref=unit)   # unchanged content; the unit follows the keys the page stamps now
            continue
        main_row = {'sheet': plain['sheet'], 'assertion_ref': plain['assertion_ref'], 'target_id': plain['target_id'],
                    'row_ref': f"main:{plain['row_ref']}", 'source_row_ref': plain['row_ref']}
        main_row.update({name: plain[name] for name in _COPIED})
        main_row['credit'] = plain['resolution'] - (before['resolution'] if before is not None else 0.0)
        main_row['dependence_unit_ref'] = unit
        table[key] = main_row

    for key, main_row in prior.items():   # accumulator: prior rows the update does not touch stay
        if key not in table:
            table[key] = dict(main_row, credit=0.0)

    for (sheet, assertion_ref) in list(table):
        if assertion_ref not in needed or sheet not in needed[assertion_ref]:
            raise ValueError(f'row ({sheet}, {assertion_ref}) is not a commissioned class of a commissioned candidate')
    for (sheet, assertion_ref), main_row in table.items():   # a kept prior row must also be about the commissioned target
        if assertion_ref in commissioned and not _same_target(main_row['target_id'], commissioned[assertion_ref]):
            raise ValueError(f"main row {main_row['row_ref']} is about target {main_row['target_id']!r}, the commissioned target of {assertion_ref} is {commissioned[assertion_ref]!r} (OWNER_DECISION 18)")
    for assertion_ref, classes in needed.items():
        for sheet in classes:
            if (sheet, assertion_ref) in table:
                continue
            if assertion_ref not in commissioned:
                raise ValueError(f'the placeholder of ({sheet}, {assertion_ref}) needs the commissioned target of {assertion_ref}: pass it in targets (OWNER_DECISION 18)')
            table[(sheet, assertion_ref)] = _placeholder(sheet, assertion_ref, commissioned[assertion_ref])

    candidate_target = {}
    for (sheet, assertion_ref), main_row in table.items():   # the rows of one candidate are about one target
        first_target = candidate_target.setdefault(assertion_ref, main_row['target_id'])
        if not _same_target(first_target, main_row['target_id']):
            raise ValueError(f'the main rows of {assertion_ref} are about different targets (OWNER_DECISION 18)')

    order = {sheet: index for index, sheet in enumerate(CLASSES)}
    result = [table[key] for key in sorted(table, key=lambda k: (k[1], order[k[0]]))]
    for main_row in result:
        validate_main_row(main_row)
    return result
