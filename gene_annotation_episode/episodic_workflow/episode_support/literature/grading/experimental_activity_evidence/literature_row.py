"""Merger (1), class-agnostic: UPDATE one row (class = sheet, candidate = assertion_ref) of a persistent subscoring sheet.

Pure: results in, a controlled row out; no Store, no custody, no I/O. The page wiring persists. The contract
(literature_row_contract) owns every vocabulary, field list and dependence key; nothing is redefined here.

INPUT RESULT. A converted result of RESULT_FIELDS, validated in full with validate_result; its carried fields are read
directly: interpretations {criterion: {'status': CRITERION_STATUS, 'degree': 0..1 (optional)}}, measured_effect,
effect_variance, effect_unit, analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref
(ROW_DEPENDENCE_KEYS; absent or null = unknown), direction_field_support, statement, statement_support_refs, source_ref.
An unknown preparation counts as dependent (port of the old binding merger).
Every direct result carries a non-null target_id (OWNER_DECISION 18).

TARGET (OWNER_DECISION 18). The row is the annotation score of one candidate for ONE target: its target_id is the
normalized (normalize_identity_ref) target_id of its direct results. All results of one (sheet, assertion_ref), and the
prior state, must share that normalized target; a different target raises ValueError (group_by_candidate and
merge_row_state). The score group (target_id, support, opposition, net) and the credit group (resolution, credit) stay apart.

DEPENDENCE (ported). Two results are dependent when they are the same experiment (same experiment_ref), or either has
an unknown preparation key, or they share a known value of any ROW_DEPENDENCE_KEYS, or a preparation of one is a
preparation of the other in either role. Connected components are the independent groups.

SCORES. m_i = log_ratio_i * weight_i * effect_support_i. Per group: support_g = mean over members of (m_i if direction is
supports else 0); opposition_g = mean over members of (m_i if direction is opposes else 0). The mean divides by ALL members of the group (a
member of unknown direction contributes 0 and dilutes its group, OWNER_DECISION 4d). Row support = sum over groups,
row opposition = sum over groups, net = support - opposition. Status: unknown when no group has a member with a known
direction (a group is known when ANY member is known, OWNER_DECISION 4e; support, opposition, net null); measured_zero
when every group with a known direction has only neutral known members (all three exactly 0.0); else measured.
A qualitative result enters through its direction (the contract fixes it from its statement) like any other result, and
through the statement counts and support refs of the row (below).

QUALITATIVE. qualitative_statements holds counts only, all three QUALITATIVE_STATEMENT keys: the number of distinct
experiments with a result stating it. qualitative_support_refs is the sorted distinct statement_support_refs of the
results, or null when there are none.

INDEPENDENCE. independence_known is true when no dependence group rests on an unknown preparation (no member of any group
has a null analyte or immobilized preparation ref); row_resolution reads it.

POOLING (ported, native scale, unit from POOLED_UNIT_BY_CLASS). Only results with a measured_effect take part. A group's
effect is the mean of its members' effects; its variance is (mean of the members' sds)^2 when every member has a variance,
else none. Across groups: inverse-variance mean when every pooled group has a variance > 0, else the plain mean with
variance and precision null (a missing variance is never 0). relative_deviation = sqrt(variance) / |effect|, else null.

CRITERIA (ported). Row criterion: conflicting if any contributing result is conflicting, supported if all are supported
(not_applicable results are dropped; all dropped = not_applicable), else unknown; a criterion a result did not give
counts as unknown for it. interpretation_degrees keeps {criterion: {experiment_ref: degree}} without combining.

UPDATE. The state is SHEET_STATE_FIELDS: {'row': the partial row, 'member_results': the results the row holds ordered by
result_ref, 'version'}. The prior state is validated with validate_sheet_state; new results are combined with the held
ones; a result whose result_ref is already held changes nothing (a repeat earns no credit). The output does not depend on
the order of arrival and is validated with validate_sheet_state.

CALLER FIELDS. weight, resolution and credit belong to the resolution module (row_weight, row_resolution, credit_change)
and are not filled here: the returned row is PARTIAL (validate_partial_row) and the caller adds them with complete_row.

ROW REF. The row_ref is content-addressed (row_ref_of): 'row:<sheet>:<assertion_ref>:<16 hex of the sha256 of the sorted member
result refs and the row version>'. New members give a new ref, an unchanged row keeps its ref, so the main sheet's unchanged test
(prior source_row_ref == row_ref) means unchanged content.
"""
import hashlib
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_target import identified_closeness
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLASSES,
    CLASS_OF_EXPERIMENT_TYPE,
    QUALITATIVE_STATEMENT,
    normalize_identity_ref,
    on_row,
    ROW_CALLER_FIELDS,
    ROW_DEPENDENCE_KEYS,
    ROW_REF_HASH_CHARS,
    ROW_REF_MAX_LENGTH,
    ROW_SHEET_VERSION,
    SHEET_STATE_FIELDS,
    validate_partial_row,
    validate_result,
    validate_row,
    validate_sheet_state,
)

PREPARATION_KEYS = tuple(k for k in ROW_DEPENDENCE_KEYS if k.endswith('_preparation_ref'))
POOLED_UNIT_BY_CLASS = {'ligand_binding': 'nM'}      # the pooled native unit of each class; other classes add theirs with their converters
KNOWN_DIRECTIONS = ('supports', 'opposes', 'neutral')
# Classes whose results are NOT pooled (decided 2026-11-21, owner to confirm): the effect of an activity_rate result is ONE of several quantities in different
# units (kcat/Km, kcat, specific activity, a fold over the control), chosen per experiment, so no two results need share a unit and no mean of them has one. The
# row's pooled effect, variance and precision (and the relative deviation) are null for such a class; the direction, strength and weight are unaffected.
NOT_POOLED_CLASSES = ('activity_rate',)


def _check_result(result):
    validate_result(result)
    if not on_row(result):
        raise ValueError(f"result {result['result_ref']} has target_match {result['target_match']!r} and relevance {result['relevance']!r}: only results on the row enter a row")
    if result['target_id'] is None:
        raise ValueError(f"result {result['result_ref']} is on the row and has no target_id (OWNER_DECISION 18)")
    return result


def _target_of(result):
    """The normalized target of a direct result (OWNER_DECISION 18)."""
    return normalize_identity_ref(result['target_id'])


def _dependence(result):
    out = {k: result.get(k) for k in ROW_DEPENDENCE_KEYS}
    return out


def dependent(first, second):
    """True when two results cannot be counted as independent."""
    if first['experiment_ref'] == second['experiment_ref']:
        return True
    a, b = _dependence(first), _dependence(second)
    if any(a[k] is None or b[k] is None for k in PREPARATION_KEYS):
        return True
    if any(a[k] is not None and a[k] == b[k] for k in ROW_DEPENDENCE_KEYS):
        return True
    return bool({a[k] for k in PREPARATION_KEYS} & {b[k] for k in PREPARATION_KEYS})


def dependence_groups(results):
    """Connected components of the dependence relation; ordered by the least result_ref so arrival order does not matter."""
    ordered = sorted(results, key=lambda r: r['result_ref'])
    parent = list(range(len(ordered)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            if dependent(ordered[i], ordered[j]):
                parent[find(j)] = find(i)
    groups = {}
    for i, result in enumerate(ordered):
        groups.setdefault(find(i), []).append(result)
    return list(groups.values())


def group_by_candidate(results):
    """{(sheet, assertion_ref): [results on the row]}; results not on the row are left out. A result on the row
    has a target_id, and the results of one (sheet, assertion_ref) must share one normalized target_id (OWNER_DECISION 18):
    a candidate's score is about one target; different targets raise ValueError."""
    grouped, targets = {}, {}
    for result in results:
        validate_result(result)
        if not on_row(result):
            continue
        key = (result['sheet'], result['assertion_ref'])
        target = _target_of(result)
        if targets.setdefault(key, target) != target:
            raise ValueError(f"results of {key} state different targets: {targets[key]!r} and {target!r} (OWNER_DECISION 18)")
        grouped.setdefault(key, []).append(result)
    return grouped


def _magnitude(result):
    if result['direction'] not in KNOWN_DIRECTIONS:
        return 0.0
    return result['log_ratio'] * result['weight'] * result['effect_support']


def _scores(groups):
    support, opposition, known, all_neutral = [], [], 0, True
    for group in groups:
        n = len(group)
        support.append(math.fsum(_magnitude(r) for r in group if r['direction'] == 'supports') / n)
        opposition.append(math.fsum(_magnitude(r) for r in group if r['direction'] == 'opposes') / n)
        directions = [r['direction'] for r in group if r['direction'] in KNOWN_DIRECTIONS]
        if directions:
            known += 1
            if any(d != 'neutral' for d in directions):
                all_neutral = False
    if known == 0:
        return 'unknown', None, None, None
    if all_neutral:
        return 'measured_zero', 0.0, 0.0, 0.0
    s, o = math.fsum(support), math.fsum(opposition)
    return 'measured', s, o, s - o


def _pool(sheet, groups):
    if sheet in NOT_POOLED_CLASSES:
        return None, None, None
    unit = POOLED_UNIT_BY_CLASS.get(sheet)
    group_effects = []
    for group in groups:
        members = [r for r in group if r.get('measured_effect') is not None]
        if not members:
            continue
        if unit is None:
            raise ValueError(f'no pooled unit is declared for class {sheet}')
        for r in members:
            if r.get('effect_unit') is not None and r['effect_unit'] != unit:
                raise ValueError(f"result {r['result_ref']} has effect unit {r['effect_unit']!r}, the pooled unit of {sheet} is {unit!r}")
        effect = math.fsum(r['measured_effect'] for r in members) / len(members)
        variances = [r.get('effect_variance') for r in members]
        variance = None if any(v is None for v in variances) else (math.fsum(math.sqrt(v) for v in variances) / len(variances)) ** 2
        group_effects.append((effect, variance))
    if not group_effects:
        return None, None, None
    if all(v is not None and v > 0 for _, v in group_effects):
        weights = [1 / v for _, v in group_effects]
        total = math.fsum(weights)
        return math.fsum(w * e for w, (e, _) in zip(weights, group_effects)) / total, 1 / total, total
    return math.fsum(e for e, _ in group_effects) / len(group_effects), None, None


def _criteria(results):
    ordered = sorted(results, key=lambda r: r['result_ref'])
    names = sorted({c for r in ordered for c in (r.get('interpretations') or {})})
    criteria, degrees = {}, {}
    for name in names:
        statuses = [(r.get('interpretations') or {}).get(name, {'status': 'unknown'})['status'] for r in ordered]
        applicable = [s for s in statuses if s != 'not_applicable']
        if not applicable:
            criteria[name] = 'not_applicable'
        else:
            criteria[name] = 'conflicting' if 'conflicting' in applicable else 'supported' if all(s == 'supported' for s in applicable) else 'unknown'
    for r in ordered:
        for name, interpretation in (r.get('interpretations') or {}).items():
            if interpretation.get('degree') is not None:
                degrees.setdefault(name, {})[r['experiment_ref']] = interpretation['degree']
    return criteria, degrees


def _independence_known(groups):
    """True when no dependence group rests on an unknown (null) preparation ref."""
    return all(r.get(k) is not None for group in groups for r in group for k in PREPARATION_KEYS)


def _qualitative(ordered):
    """({statement: number of distinct experiments stating it} with all three keys, sorted distinct support refs or None)."""
    counts = {s: len({r['experiment_ref'] for r in ordered if r.get('statement') == s}) for s in QUALITATIVE_STATEMENT}
    # refs only from results that state detected or not-detected: the contract refuses refs on a row whose statements are all
    # 'not stated' (owner decision on the row merger's doubt 1)
    refs = sorted({ref for r in ordered if r.get('statement') in ('interaction_detected', 'interaction_not_detected')
                   for ref in (r.get('statement_support_refs') or [])})
    return counts, (refs or None)


def row_ref_of(sheet, assertion_ref, member_refs):
    """The content-addressed ref of a row: 'row:<sheet>:<assertion_ref>:<hash>', the hash being the first ROW_REF_HASH_CHARS hex
    characters of the sha256 of the sorted member result refs and ROW_SHEET_VERSION. Within ROW_REF_MAX_LENGTH: a too long
    assertion_ref is cut to its readable prefix and the hash stays last."""
    digest = hashlib.sha256(json.dumps([sorted(member_refs), ROW_SHEET_VERSION]).encode('utf-8')).hexdigest()[:ROW_REF_HASH_CHARS]
    head = f'row:{sheet}:'
    room = ROW_REF_MAX_LENGTH - len(head) - 1 - ROW_REF_HASH_CHARS
    if room < 1:
        raise ValueError(f'sheet {sheet!r} leaves no room for the assertion_ref in a row_ref')
    return f'{head}{assertion_ref[:room]}:{digest}'


def complete_row(row, weight, resolution, credit):
    """The complete ROW (ROW_FIELDS) from the partial row merge_row returns plus weight, resolution and credit, validated with
    validate_row. The partial row is not changed. A row that already carries weight, resolution or credit is refused; a value
    outside its range (weight and resolution 0..1, credit a finite number) is refused by validate_row. The three fields come
    from literature_resolution (row_weight, row_resolution, credit_change) and are never computed here."""
    held = [name for name in ROW_CALLER_FIELDS if name in row]
    if held:
        raise ValueError(f'row already carries {held}: complete_row takes the partial row of merge_row')
    validate_partial_row(row)
    return validate_row({**row, 'weight': weight, 'resolution': resolution, 'credit': credit})


def merge_row_state(sheet, assertion_ref, results, prior_row=None):
    """The updated state (SHEET_STATE_FIELDS); prior_row is the state this function returned before (or None)."""
    if sheet not in CLASSES:
        raise ValueError(f'sheet {sheet!r} is not a class')
    held = []
    target = None   # the normalized target of the row: the prior row's, else the first result's (OWNER_DECISION 18)
    if prior_row is not None:
        validate_sheet_state(prior_row)
        if prior_row['row']['sheet'] != sheet or prior_row['row']['assertion_ref'] != assertion_ref:
            raise ValueError('prior_row is the row of another sheet or candidate')
        held = list(prior_row['member_results'])
        target = normalize_identity_ref(prior_row['row']['target_id'])
    members = {r['result_ref']: r for r in held}
    for result in results:
        _check_result(result)
        if result['sheet'] != sheet or result['assertion_ref'] != assertion_ref:
            raise ValueError(f"result {result['result_ref']} belongs to ({result['sheet']}, {result['assertion_ref']}), not ({sheet}, {assertion_ref})")
        if CLASS_OF_EXPERIMENT_TYPE[result['experiment_type']] != sheet:
            raise ValueError('result experiment_type is not of this class')
        if target is None:
            target = _target_of(result)
        if _target_of(result) != target:
            raise ValueError(f"result {result['result_ref']} has target {_target_of(result)!r}, the row of ({sheet}, {assertion_ref}) is about {target!r} (OWNER_DECISION 18)")
        members.setdefault(result['result_ref'], result)   # a repeat of a held result changes nothing
    if target is None:
        raise ValueError(f'the row of ({sheet}, {assertion_ref}) has no result and no prior row: it has no target (OWNER_DECISION 18)')
    ordered = [members[ref] for ref in sorted(members)]
    groups = dependence_groups(ordered)
    status, support, opposition, net = _scores(groups)
    effect, variance, precision = _pool(sheet, groups)
    criteria, degrees = _criteria(ordered)
    all_degrees = [d for per in degrees.values() for d in per.values()]
    statements, support_refs = _qualitative(ordered)
    # the best identified member: the greatest identified_closeness, ties by the least result_ref (ordered is by result_ref)
    best = max(ordered, key=identified_closeness)
    row = {
        'sheet': sheet,
        'assertion_ref': assertion_ref,
        'target_id': target,
        'row_ref': row_ref_of(sheet, assertion_ref, list(members)),
        'row_status': status,
        'support': support,
        'opposition': opposition,
        'net': net,
        'experiments': len({r['experiment_ref'] for r in ordered}),
        'independent_groups': len(groups),
        'measured_effects': sum(1 for r in ordered if r['direction'] in KNOWN_DIRECTIONS),
        'criteria_supported': sum(1 for s in criteria.values() if s == 'supported'),
        'criteria_conflicting': sum(1 for s in criteria.values() if s == 'conflicting'),
        'criteria_unknown': sum(1 for s in criteria.values() if s == 'unknown'),
        'criteria_not_applicable': sum(1 for s in criteria.values() if s == 'not_applicable'),
        'min_degree': min(all_degrees) if all_degrees else None,
        'mean_degree': math.fsum(all_degrees) / len(all_degrees) if all_degrees else None,
        'relative_deviation': math.sqrt(variance) / abs(effect) if variance is not None and effect not in (None, 0) else None,
        'criteria': criteria,
        'interpretation_degrees': degrees,
        'pooled_effect': effect,
        'pooled_variance': variance,
        'pooled_precision': precision,
        'independence_known': _independence_known(groups),
        'qualitative_statements': statements,
        'qualitative_support_refs': support_refs,
        'identified_closeness': identified_closeness(best),
        'subject_record_ref': best['subject_record_ref'],
        'subject_sequence_ref': best['subject_sequence_ref'],
        'subject_resolution': best['subject_resolution'],
        'subject_match_count': best['subject_match_count'],
        'subject_closeness': best['subject_closeness'],
        'comparison_ref': best['comparison_ref'],
    }
    validate_partial_row(row)
    state = {'row': row, 'member_results': ordered, 'version': ROW_SHEET_VERSION}
    if set(state) != set(SHEET_STATE_FIELDS):
        raise ValueError('the sheet state does not hold exactly SHEET_STATE_FIELDS')
    return validate_sheet_state(state)


def merge_row(sheet, assertion_ref, results, prior_row=None):
    """The PARTIAL row (ROW_FIELDS without weight, resolution, credit) of (sheet, assertion_ref); prior_row is the state of
    merge_row_state, not a row. complete_row fills the three caller fields."""
    return merge_row_state(sheet, assertion_ref, results, prior_row)['row']
