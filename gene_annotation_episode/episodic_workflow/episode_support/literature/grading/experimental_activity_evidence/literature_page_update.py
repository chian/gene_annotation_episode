"""The page-level composition of the A105 scoring flow (contract SIGNATURES['page_update'], OWNER_DECISION 10): one page
finalizes its graders and UPDATES the persistent subscoring sheet; that update updates the main scoring sheet, the credit and
the per-annotation scores in the SAME step. Arguments in, controlled records out; it holds no Store and no custody: the subject is identified only through the two functions it is handed (resolve_subject, and the awaited subject_closeness, which runs the pairwise BLAST).
Persistence (saving the state, the results, the rows) belongs to the wiring step that calls this function.

await page_update(sheet_state, graders, claims, target_sequence_refs, resolve_subject, subject_closeness) -> {'sheet_state', 'rows', 'main_sheet', 'axis', 'credit', 'scores', 'features'}

ARGUMENTS
  sheet_state  {(sheet, assertion_ref): SHEET_STATE} the persistent subscoring sheet before this page (None or {} for the
               first page). Each state is validated; the page stores PARTIAL rows (without weight, resolution, credit).
  graders      a list; each item is a mapping {'grader': a FINALIZED grader record (GRADER_REF_FIELDS, finalized true),
               'member_records': the leaf records of its member_record_refs}, and optionally 'finding'. SIGNATURE GAP: the
               contract's grader record holds only the member refs, and this function reads no store, so the page hands the
               member records in beside it. An item whose 'finding' is SKIPPED_GRADER (a source-grounded "no applicable
               experiment") is skipped.
  claims       {assertion_ref: claim}: the candidates of this call; each claim has exactly the CLAIM_FIELDS. SIGNATURE GAP:
               a claim (CLAIM_FIELDS) carries no assertion_ref, so the candidate's ref is the key of the mapping.

PER GRADER (finalized): merged_record(type, members, grader_ref) -> GRADERS[type] (the grade function) -> CONVERTERS[type]
(the converter) -> per claim: bearing; direction_and_ratio only when the bearing is 'direct' (else direction unknown, with null
log_ratio and effect_support); the weight of the one result by literature_resolution.row_weight; the converted RESULT is
assembled from the converter output and checked with validate_result.

HOW THE TARGET AND THE PARTNER REACH BEARING (OWNER_DECISION 18). The merged record of the grader carries the identity keys
target_id and partner_id (the single normalized value its members state; None when no member states one or they conflict).
The page hands bearing exactly {'experiment_type', 'target_id', 'partner_id'} read from that merged record, and the claim
(its subject_id is the target, its partner_id the partner). The result's target_id is the record's normalized target (None when
the grader states none, which bearing answers with none / target_not_stated: no score, and the grader still counts in credit).

HOW THE TARGETS REACH merge_main. merge_main takes them as its optional last argument: {assertion_ref: normalize_identity_ref(
claim['subject_id'])}, derived from the claims here. classes_needed is derived from the claims too: for each candidate, the
classes whose CLAIM_PREDICATES_BY_CLASS list the claim's predicate (N_k). A claim whose predicate no class lists raises ValueError.

THEN: group_by_candidate; merge_row_state with the prior state (a repeat result_ref changes nothing); complete_row with
weight = row_weight over the held results, resolution = row_resolution(row), credit = credit_change(before, after) (a prior
row's R is recomputed from its stored row; a first fill has before 0); merge_main (with the dataset_ref / source_ref stamps);
axis_output; row_features.

PRIOR MAIN SHEET. The page holds no main sheet, so the prior main sheet is rebuilt from the prior states (complete rows, credit 0),
each with source_row_ref = the prior row's row_ref. The subscoring row_ref is content-addressed (literature_row.row_ref_of), so
merge_main's test 'prior source_row_ref == row_ref' holds exactly for an unchanged row (carried with credit 0.0), and a row with
new members has a new ref and is rebuilt with its main credit R(after) - R(before).

STAMPS. A subscoring row rests on several results; the page stamps dataset_ref / source_ref (MAIN_ROW_INPUT_KEYS) on the row
handed to merge_main only when ALL its member results share one non-null value; otherwise None (the row is its own dependence
unit). Judgement call, flagged for the owner.

CONVERTERS. All 26 (25 ligand_binding and the activity_rate type spectro_direct) are named convert_<module suffix> and take one argument, the grade dict of the type's grade function.
The suffix differs from the experiment type for trp_quenching (convert_trp) and alphascreen (convert_alpha).
"""
import hashlib
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import convert_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_auc_converter import convert_auc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_axis_output import axis_output
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bearing import assayed_molecule, bearing
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import convert_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_converter import convert_bret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_converter import convert_cetsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import convert_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_direction import direction_and_ratio
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import activity_direction_and_ratio
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dsf_converter import convert_dsf
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_converter import convert_elisa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import convert_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import convert_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import convert_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import convert_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import convert_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_grader_record import merged_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import convert_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_main_sheet import merge_main
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import convert_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pla_converter import convert_pla
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_populated_grader import GRADERS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_proximity_converter import convert_proximity
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import convert_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import convert_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_resolution import credit_change, row_resolution, row_weight
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row import complete_row, group_by_candidate, merge_row_state
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    BEARING_SCORING,
    CLAIM_FIELDS,
    CLAIM_PREDICATES_BY_CLASS,
    CLASS_OF_EXPERIMENT_TYPE,
    EXPERIMENT_TYPES,
    REF_PATTERN,
    ROW_CALLER_FIELDS,
    SKIPPED_GRADER,
    is_name,
    normalize_identity_ref,
    validate_axis,
    validate_features,
    validate_grader_ref,
    validate_result,
    validate_sheet_state,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import convert_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sheet_features import row_features
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import convert_spa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_converter import convert_spectro_direct
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_converter import convert_split_reporter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import convert_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import convert_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_y2h_converter import convert_y2h

CONVERTERS = {
    'spr': convert_spr, 'itc': convert_itc, 'bli': convert_bli, 'gci': convert_gci, 'fp': convert_fp, 'fret': convert_fret,
    'mst': convert_mst, 'trp_quenching': convert_trp, 'fcs': convert_fcs, 'elisa': convert_elisa, 'alphascreen': convert_alpha,
    'radioligand': convert_radioligand, 'spa': convert_spa, 'pulldown': convert_pulldown, 'emsa': convert_emsa, 'sec': convert_sec,
    'dialysis': convert_dialysis, 'auc': convert_auc, 'dsf': convert_dsf, 'cetsa': convert_cetsa, 'bret': convert_bret,
    'y2h': convert_y2h, 'split_reporter': convert_split_reporter, 'pla': convert_pla, 'proximity': convert_proximity,
    'spectro_direct': convert_spectro_direct,
}


def _check_claims(claims):
    """{assertion_ref: claim} checked; returns ({assertion_ref: classes commissioned}, {assertion_ref: normalized target})."""
    if not isinstance(claims, dict) or not claims:
        raise ValueError('claims must be a non-empty mapping assertion_ref -> claim')
    needed, targets = {}, {}
    for assertion_ref, claim in claims.items():
        if not isinstance(assertion_ref, str) or not REF_PATTERN.match(assertion_ref):
            raise ValueError(f'a claim key must be a record reference (the candidate assertion_ref): {assertion_ref!r}')
        if not isinstance(claim, dict) or set(claim) != set(CLAIM_FIELDS):
            raise ValueError(f'claim {assertion_ref} must hold exactly the CLAIM_FIELDS {sorted(CLAIM_FIELDS)}')
        classes = tuple(sheet for sheet, predicates in CLAIM_PREDICATES_BY_CLASS.items() if claim['predicate'] in predicates)
        if not classes:
            raise ValueError(f"claim {assertion_ref} has a predicate no class lists: {claim['predicate']!r}")
        if not isinstance(claim['subject_id'], str) or not is_name(normalize_identity_ref(claim['subject_id'])):
            raise ValueError(f"claim {assertion_ref}.subject_id must be a molecule name: {claim['subject_id']!r}")
        needed[assertion_ref] = classes
        targets[assertion_ref] = normalize_identity_ref(claim['subject_id'])
    return needed, targets


def _partial(row):
    return {name: value for name, value in row.items() if name not in ROW_CALLER_FIELDS}


def _check_state(sheet_state):
    """The prior state with PARTIAL rows: {(sheet, assertion_ref): state}."""
    prior = {}
    for key, state in (sheet_state or {}).items():
        validate_sheet_state(state)
        if key != (state['row']['sheet'], state['row']['assertion_ref']):
            raise ValueError(f'sheet_state key {key!r} is not the (sheet, assertion_ref) of its row')
        prior[key] = {**state, 'row': _partial(state['row'])}
    return prior


def _weight_input(result):
    """The result in the form row_weight reads: its 'interpretations' ({criterion: {'status', 'degree'?}}) and its
    'experiment_type' (whose unknown weight applies). (It used to pass 'criteria'/'degrees', which row_weight does not
    read, so every row got the no-criteria weight: a bug, fixed 2026-11-21.)"""
    return {'interpretations': result.get('interpretations') or {}, 'experiment_type': result['experiment_type'],
            **{name: result[name] for name in ('subject_resolution', 'subject_match_count', 'subject_closeness')}}


def _result_ref(grader_ref, assertion_ref):
    return 'result_' + hashlib.sha256(json.dumps([grader_ref, assertion_ref]).encode('utf-8')).hexdigest()[:24]


UNIDENTIFIED = {'record_ref': None, 'sequence_ref': None, 'resolution': 'unresolved', 'match_count': 0, 'closeness': None, 'comparison_ref': None}
SUBJECT_KEYS = {'target': ('target_id', 'subject_database_id', 'subject_database', 'subject_organism'),
                'partner': ('partner_id', 'partner_database_id', 'partner_database', 'partner_organism')}


async def _identified_subject(record, bearing_record, claim, assertion_ref, identify):
    """What the page knows of the assayed protein for this claim: the I2 resolution (reference record, sequence, how it resolved,
    how many records matched) and the I3 closeness of its sequence to the claim subject's, or the unidentified record.
    Resolved only where the grader bears on the claim by its names (a molecule is stated, the predicate is borne, the partner
    does not contradict): other results never score and need no identification. The molecule identified is the record's target,
    or its partner on the symmetric partner route (the partner is the claim's subject)."""
    first = bearing(bearing_record, claim, None)
    if first['bearing'] == 'none' or first['reasons'] == ['partner_contradicts_claim']:
        return UNIDENTIFIED
    name_key, id_key, database_key, organism_key = SUBJECT_KEYS[assayed_molecule(bearing_record, claim)]
    return await identify(assertion_ref, record[name_key], record[id_key], record[database_key], record[organism_key])


async def _results_of_grader(grader, converted, record, claims, identify):
    """One converted RESULT per claim (RESULT_FIELDS), validated; direction only for bearing 'direct' or 'transfer'. ``identify``
    is identify(assertion_ref, name, database_id, database, organism) -> the identified subject (see page_update)."""
    quantities = converted['extraction']['quantities']
    effect, variance = quantities.get('effect'), quantities.get('effect_variance')
    has_effect = effect is not None and effect['status'] == 'point'
    interpretations = {name: ({'status': item['status'], 'degree': item['degree']} if item.get('degree') is not None else {'status': item['status']})
                       for name, item in converted['extraction']['interpretations'].items()}
    qualitative = converted.get('qualitative_effect')
    support_refs = list(dict.fromkeys(qualitative['support_refs'])) if qualitative is not None else []
    bearing_record = {'experiment_type': grader['experiment_type'], 'target_id': record.get('target_id'), 'partner_id': record.get('partner_id')}
    dependence = converted['dependence']
    results = []
    for assertion_ref in sorted(claims):
        claim = claims[assertion_ref]
        subject = await _identified_subject(record, bearing_record, claim, assertion_ref, identify)
        is_direct = bearing(bearing_record, claim, subject['closeness'])['bearing']
        subject_fields = {
            'subject_record_ref': subject['record_ref'], 'subject_sequence_ref': subject['sequence_ref'],
            'subject_resolution': subject['resolution'], 'subject_match_count': subject['match_count'],
            'subject_closeness': subject['closeness'], 'comparison_ref': subject['comparison_ref'],
        }
        weight = row_weight([_weight_input({'interpretations': interpretations, 'experiment_type': grader['experiment_type'], **subject_fields})])
        if is_direct not in BEARING_SCORING:
            direction = {'direction': 'unknown', 'log_ratio': None, 'effect_support': None}
        elif CLASS_OF_EXPERIMENT_TYPE[grader['experiment_type']] == 'activity_rate':
            # an activity_rate converter carries 'enzyme_mass_g_per_mol' (the stated molar mass, or None): specific activity ends need it
            direction = activity_direction_and_ratio(converted, converted['enzyme_mass_g_per_mol'])
        else:
            direction = direction_and_ratio(converted)
        known = direction['direction'] != 'unknown'
        result = {
            'result_ref': _result_ref(grader['grader_ref'], assertion_ref),
            'experiment_ref': grader['grader_ref'],
            'assertion_ref': assertion_ref,
            'target_id': None if record.get('target_id') is None else normalize_identity_ref(claim['subject_id'] if is_direct in BEARING_SCORING else record['target_id']),
            'experiment_type': grader['experiment_type'],
            'sheet': CLASS_OF_EXPERIMENT_TYPE[grader['experiment_type']],
            'bearing': is_direct,
            'direction': direction['direction'],
            'log_ratio': direction['log_ratio'],
            'weight': weight,
            'effect_support': direction['effect_support'],
            'source_ref': converted['source_ref'],
            'dataset_ref': dependence['dataset_ref'],
            'interpretations': interpretations,
            'measured_effect': effect['value'] if has_effect else None,
            'effect_variance': variance['value'] if has_effect and variance is not None and variance['status'] == 'point' else None,
            'effect_unit': effect['unit'] if has_effect else None,
            'analyte_preparation_ref': dependence['analyte_preparation_ref'],
            'immobilized_preparation_ref': dependence['immobilized_preparation_ref'],
            'surface_ref': dependence['surface_ref'],
            'direction_field_support': converted['direction_field_support'] if known else None,
            'statement': None if qualitative is None else qualitative['statement'],
            'statement_support_refs': support_refs or None,
            **subject_fields,
        }
        results.append(validate_result(result))
    return results


def _stamp(row, members):
    """The row with the dataset_ref / source_ref stamps merge_main reads: one non-null value shared by ALL members, else None."""
    stamped = dict(row)
    for name in ('dataset_ref', 'source_ref'):
        values = {member[name] for member in members}
        stamped[name] = values.pop() if len(values) == 1 and None not in values else None
    return stamped


def _prior_main_row(row):
    return {'sheet': row['sheet'], 'assertion_ref': row['assertion_ref'], 'target_id': row['target_id'],
            'row_ref': f"main:{row['row_ref']}", 'source_row_ref': row['row_ref'],
            'row_status': row['row_status'], 'support': row['support'], 'opposition': row['opposition'], 'net': row['net'],
            'weight': row['weight'], 'resolution': row['resolution'], 'credit': 0.0,
            'experiments': row['experiments'], 'independent_groups': row['independent_groups'], 'dependence_unit_ref': None}


def _identifier(target_sequence_refs, resolve_subject, subject_closeness):
    """identify(assertion_ref, name, database_id, database, organism), awaited: I2 (resolve_subject) on the stated identity, then
    I3 (subject_closeness, awaited) of the resolved record against the target's input record of that claim. A name that
    resolves to several candidates ('name_ambiguous') has the closeness of EACH candidate measured and the closest kept (its
    record and sequence are the ones the result carries; the match count stays the number of candidates, which lowers the
    standing in identified_closeness). Each distinct question is asked once."""
    resolved_held, closeness_held = {}, {}

    async def closeness_of(subject_record_ref, target_record_ref):
        pair = (subject_record_ref, target_record_ref)
        if pair not in closeness_held:
            closeness_held[pair] = await subject_closeness(subject_record_ref=pair[0], target_record_ref=pair[1])
        return closeness_held[pair]

    async def identify(assertion_ref, name, database_id, database, organism):
        key = (name, database_id, database, organism)
        if key not in resolved_held:
            resolved_held[key] = resolve_subject(name=name, database_id=database_id, database=database, organism=organism)
        resolved = resolved_held[key]
        target_record_ref = target_sequence_refs[assertion_ref]
        held = resolved['candidates'] if resolved['resolution'] == 'name_ambiguous' else [resolved]
        closest, measured = resolved, None
        if target_record_ref is not None:
            for candidate in held:
                if candidate['sequence_ref'] is None:
                    continue
                result = await closeness_of(candidate['record_ref'], target_record_ref)
                if measured is None or result['closeness'] > measured['closeness']:
                    closest, measured = candidate, result
        return {'record_ref': closest['record_ref'], 'sequence_ref': closest['sequence_ref'], 'resolution': resolved['resolution'],
                'match_count': resolved['match_count'], 'closeness': None if measured is None else measured['closeness'],
                'comparison_ref': None if measured is None else measured['comparison_ref']}
    return identify


async def page_update(sheet_state, graders, claims, target_sequence_refs, resolve_subject, subject_closeness):
    """Awaited end to end. target_sequence_refs {assertion_ref: the reference of the claim's subject INPUT record (the record
    that carries the target's sequence_ref; the BLAST comparison reads its sequence through custody), or None};
    resolve_subject(name=, database_id=, database=, organism=) -> the I2 record of literature_subject_resolution.resolve_subject
    (bound to the scoped store by the caller: functools.partial(resolve_subject, store)) and the coroutine function
    subject_closeness(subject_record_ref=, target_record_ref=) -> the I3 record of
    literature_subject_closeness.subject_closeness (bound to the unit's context by the caller: functools.partial(
    subject_closeness, ctx))."""
    needed, targets = _check_claims(claims)
    if set(target_sequence_refs) != set(claims):
        raise ValueError('target_sequence_refs must hold exactly the claims keys')
    identify = _identifier(target_sequence_refs, resolve_subject, subject_closeness)
    prior = _check_state(sheet_state)

    results = []
    for item in graders:
        if item.get('finding') == SKIPPED_GRADER:
            continue
        grader, members = item['grader'], item['member_records']
        validate_grader_ref(grader)
        if not grader['finalized']:
            raise ValueError(f"grader {grader['grader_ref']} is not finalized (the page finalizes a grader before it updates the sheet)")
        if grader['experiment_type'] not in EXPERIMENT_TYPES:
            raise ValueError(f"grader {grader['grader_ref']} has an unknown experiment type")
        if sorted(member['experiment_ref'] for member in members) != sorted(grader['member_record_refs']):
            raise ValueError(f"the member records handed in are not the member_record_refs of grader {grader['grader_ref']}")
        record = merged_record(grader['experiment_type'], members, grader['grader_ref'])
        graded = GRADERS[grader['experiment_type']](record)
        converted = CONVERTERS[grader['experiment_type']](graded)
        results.extend(await _results_of_grader(grader, converted, record, claims, identify))

    grouped = group_by_candidate(results)
    state = dict(prior)
    for key in sorted(grouped):
        state[key] = merge_row_state(key[0], key[1], grouped[key], prior.get(key))

    rows, stamped, features, prior_rows = [], [], [], []
    for key in sorted(state):
        held = state[key]
        resolution = row_resolution(held['row'])
        before = None
        if key in prior:
            before_resolution = row_resolution(prior[key]['row'])
            before = {'resolution': before_resolution}
            prior_rows.append(complete_row(prior[key]['row'], row_weight([_weight_input(r) for r in prior[key]['member_results']]), before_resolution, 0.0))
        row = complete_row(held['row'], row_weight([_weight_input(r) for r in held['member_results']]), resolution, credit_change(before, {'resolution': resolution}))
        rows.append(row)
        stamped.append(_stamp(row, held['member_results']))
        features.append(validate_features(row_features(row)))

    prior_main = [_prior_main_row(row) for row in prior_rows] or None
    main_sheet = merge_main(stamped, needed, prior_main, targets)
    axis_result = axis_output(main_sheet)
    axis = [validate_axis({**axis_result['score'][a], **axis_result['credit'][a]}) for a in sorted(axis_result['score'])]
    return {
        'sheet_state': state,
        'rows': rows,
        'main_sheet': main_sheet,
        'axis': axis,
        'credit': {a: axis_result['credit'][a]['credit'] for a in sorted(axis_result['credit'])},
        'scores': {a: axis_result['score'][a] for a in sorted(axis_result['score'])},
        'features': features,
    }
