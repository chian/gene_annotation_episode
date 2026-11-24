"""The real model on the extraction leaf (selected only with ``-m model_run``): the real PopZ paragraph (the SPR
result of PMC2745220) and a synthetic passage that states many SPR details. For each: the model's own answer is
validated and held, the grader is run by code on the held record, the Episode ends by the yield estimator, the
return is admitted and resume replays the run with no new model call."""
import asyncio
import importlib
import json

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_extraction import (
    quote_span)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_extraction import (
    field_names)

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_identity_extraction import (
    ASKED, NAME_FIELDS, identity_record_keys, quote_span as identity_quote_span, split_answer, validate_identity_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    IDENTITY_FIELDS, IDENTITY_UNAVAILABLE_REASONS, LEAF_RECORD_IDENTITY, normalize_identity_ref, validate_identity)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    experiment_types_of_class)

from .leaf_world import EPISODE, PATH, linked, resumed
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import (
    alpha_passages, bli_passages, elisa_passages, emsa_passages, fcs_passages, fp_passages, fret_passages, gci_passages, itc_passages, mst_passages, pulldown_passages, radioligand_passages, sec_passages, spa_passages, trp_passages)

from .test_extraction_leaf import sec_real_world, sec_synthetic_world, emsa_real_world, emsa_synthetic_world, pulldown_real_world, pulldown_synthetic_world, spa_real_world, spa_synthetic_world, radioligand_real_world, radioligand_synthetic_world, alpha_real_world, alpha_synthetic_world, elisa_real_world, elisa_synthetic_world, fcs_real_world, fcs_synthetic_world, trp_real_world, trp_synthetic_world, bli_real_world, bli_synthetic_world, fp_real_world, fp_synthetic_world, fret_real_world, fret_synthetic_world, gci_real_world, gci_synthetic_world, itc_real_world, itc_synthetic_world, mst_real_world, mst_synthetic_world, popz_world, synthetic_world


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import dialysis_passages
from .test_extraction_leaf import dialysis_real_world, dialysis_real_result_world, dialysis_synthetic_world
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import auc_passages
from .test_extraction_leaf import auc_real_world, auc_synthetic_world
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import y2h_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_y2h_extraction
from .test_extraction_leaf import y2h_real_world, y2h_synthetic_world
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import cetsa_passages
from .test_extraction_leaf import cetsa_real_world, cetsa_synthetic_world


def naming_calls(calls):
    """The calls that name the method of a window (the decision's model call of a unit; their context has the sheet class and
    the listed methods, not an experiment type)."""
    return [call for call in calls if 'methods' in (call['request'].get('context') or {})]


def fill_calls(calls):
    """The calls that fill the form of the type the leaf named (the unit's own model calls; their context names the type)."""
    return [call for call in calls if 'experiment_type' in (call['request'].get('context') or {})]


def check_named(world, calls, records):
    """The leaf was handed the sheet class (never a type) and named the type the test expects: every naming call offered exactly
    the types of that class and answered with the expected type, every fill call is for it, and every held record carries it."""
    expected = world['expected_type']
    sheet_class = world['input']['assignment']['sheet_class']
    assert 'experiment_type' not in world['input']['assignment']
    named = naming_calls(calls)
    assert named, 'the leaf must name the method before it fills a form'
    for call in named:
        assert call['request']['context']['sheet_class'] == sheet_class
        assert set(call['request']['context']['methods']) == set(experiment_types_of_class(sheet_class))
        print('NAMED', call['response']['method'])
        assert call['response']['method'] == expected, ('the leaf named another method', call['response']['method'], expected)
    for call in fill_calls(calls):
        assert call['request']['context']['experiment_type'] == expected
    for record in records:
        assert record['experiment_type'] == expected


def type_answer(call):
    """The type form's answer of a model call: the response without its identity block."""
    return split_answer(call['response'])[0]


PASSAGES_PACKAGE = 'gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests'
PASSAGES_MODULE_OF_TYPE = {'alphascreen': 'alpha', 'trp_quenching': 'trp'}      # an experiment type whose passages file is not named <type>_passages.py


def asked_again_because(call):
    """The reason the model was asked again, carried by the request of a call that follows a refused answer; None for a first ask."""
    return (call['request'].get('context') or {}).get('previous_answer_was_rejected_because')


def accepted_of(calls):
    """The accepted calls: a call is accepted unless the next call asks again because of its refusal (the last call is accepted)."""
    return [call for index, call in enumerate(calls) if index + 1 == len(calls) or asked_again_because(calls[index + 1]) is None]


def rejection_counts(calls, units):
    """(retried, failed, details). A refused call that is asked again and accepted is normal (retried). Only a refusal never followed by an
    accepted call is a failure: a run with fewer units than accepted calls has an accepted-looking last call that never produced its unit."""
    accepted = accepted_of(calls)
    retried = len(calls) - len(accepted)
    failed = max(0, len(accepted) - len(units))
    details = [asked_again_because(call) for call in calls if asked_again_because(call) is not None]
    return retried, failed, details


def no_unrecovered_rejection(calls, units):
    """Fail only on a rejection that never succeeded (a refused answer with no later accepted call) or on a run with no accepted call.
    A call refused for a quote or schema error and then asked again and accepted is NORMAL behaviour (owner ruling). Returns the accepted calls,
    which every per-call assertion of a test then runs over."""
    retried, failed, details = rejection_counts(calls, units)
    assert failed == 0, ('a rejection was never followed by an accepted call', details)
    accepted = accepted_of(calls)
    assert len(accepted) == len(units) >= 1
    return accepted


def chunk_of(world):
    """The chunk text of the world (the window of the source's text the assignment names)."""
    assignment = world['input']['assignment']
    text = world['store'].get_artifact(world['artifact'])
    data = text if isinstance(text, bytes) else text.encode('utf-8')
    return data[assignment['offset']:assignment['offset'] + assignment['limit']].decode('utf-8'), assignment


def expected_identity(experiment_type, run_id):
    """The expected target and partner of the run, read from the type's passages module, or None when it defines no target constant.
    Returns (kind, target, partner) with kind 'SYNTHETIC' or 'REAL'; target is a normalized name or None (REAL: the paragraph names no single target);
    partner is a normalized name or None (also when the constant is not defined). The run id gives the kind and the variant: '...-synthetic-real' is SYNTHETIC; '...-real-real' or
    '<name>-real' is REAL; '...-real-<variant>-real' (dialysis: 'methods', 'result') is REAL with the variant."""
    module = importlib.import_module(f'{PASSAGES_PACKAGE}.{PASSAGES_MODULE_OF_TYPE.get(experiment_type, experiment_type)}_passages')
    tokens = run_id[len('a105-extract-'):].removesuffix('-real').split('-')
    kind = 'SYNTHETIC' if 'synthetic' in tokens else 'REAL'
    variant = tokens[tokens.index('real') + 1:] if 'real' in tokens else []
    suffix = ('_' + '_'.join(variant).upper()) if variant else ''
    target_name, partner_name = (('SYNTHETIC_TARGET', 'SYNTHETIC_PARTNER') if kind == 'SYNTHETIC' else ('REAL_EXPECTED_TARGET', 'REAL_EXPECTED_PARTNER'))
    missing = object()
    target = getattr(module, target_name + suffix, getattr(module, target_name, missing))
    partner = getattr(module, partner_name + suffix, getattr(module, partner_name, missing))
    if target is missing:
        return None
    return kind, target, (None if partner is missing else partner)


def expected_pair(experiment_type):
    """REAL_EXPECTED_PAIR of the type's passages module (a tuple of two groups of acceptable normalized spellings), or None when it defines none."""
    module = importlib.import_module(f'{PASSAGES_PACKAGE}.{PASSAGES_MODULE_OF_TYPE.get(experiment_type, experiment_type)}_passages')
    return getattr(module, 'REAL_EXPECTED_PAIR', None)


def check_expected_identity(keys, experiment_type, run_id):
    """The expected-target mechanism. CONVENTION: a type's passages module may define the optional constants SYNTHETIC_TARGET and SYNTHETIC_PARTNER
    (the normalized name, casefolded and whitespace collapsed, of the molecule the synthetic passage is about, and of its partner or None) and
    REAL_EXPECTED_TARGET and REAL_EXPECTED_PARTNER (the normalized name of the molecule the real paragraph's assay is about, or None when the paragraph
    names no single target; the partner likewise). A type with several real chunks suffixes the real constants with the variant the run id names
    (dialysis: REAL_EXPECTED_TARGET_METHODS, REAL_EXPECTED_TARGET_RESULT, REAL_EXPECTED_PARTNER_METHODS, REAL_EXPECTED_PARTNER_RESULT); a suffixed constant
    wins over the plain one. SYNTHETIC: every accepted call states target_id and it equals SYNTHETIC_TARGET; partner_id equals SYNTHETIC_PARTNER when that
    is not None. REAL with a target name: the call states that target or leaves it unavailable, never another; REAL with None: no call may state a
    target (overreach); a real partner name is held the same way, a real partner None is not checked. A module defining none of them is not checked
    (a line says so). OPTIONAL REAL_EXPECTED_PAIR (a tuple of two groups, each a tuple of the acceptable normalized spellings of one molecule), for a real
    paragraph that names a SYMMETRIC interacting pair: when defined it REPLACES the real target/partner checks; every stated target_id and partner_id must
    be in the union of the groups, and when both are stated they must not be in the same group (so either orientation passes); unavailable is fine."""
    expected = expected_identity(experiment_type, run_id)
    if expected is None:
        print('NO EXPECTED TARGET DEFINED for', experiment_type)
        return
    kind, target, partner = expected
    stated_target, stated_partner = keys['target_id'], keys['partner_id']
    print('EXPECTED', kind, 'TARGET', repr(target), 'PARTNER', repr(partner), 'STATED TARGET', repr(stated_target), 'PARTNER', repr(stated_partner))
    if kind == 'SYNTHETIC':
        # a stated name that contains the expected spelling is the same molecule: the passage's own tag or prefix ('His-tagged DX
        # receptor') is kept by the identity rule (tag prefixes stay), as the real-paragraph pair check already accepts
        assert stated_target is not None and target in stated_target, ('synthetic target', stated_target, target)
        if partner is not None:
            assert stated_partner is not None and partner in stated_partner, ('synthetic partner', stated_partner, partner)
    elif expected_pair(experiment_type) is not None:
        pair = expected_pair(experiment_type)
        print('EXPECTED PAIR', pair)
        union = {name for group in pair for name in group}
        # a stated name matches a molecule when one of its spellings is contained in it: the paragraph's own fusion suffix (TLR1/2-Rluc8,
        # PII-LgBiT) or plural (nucleosomes) is the same molecule
        # a stated name belongs to the group of the LONGEST spelling it contains, so 'crca' is CrcA, not Crc ('crc' is inside 'crca')
        def group_of(stated):
            matches = [(len(name), index) for index, group in enumerate(pair) for name in group if name in stated]
            return max(matches)[1] if matches else None
        for label, stated in (('target', stated_target), ('partner', stated_partner)):
            assert stated is None or group_of(stated) is not None, (f'real pair {label}', stated, pair)
        if stated_target is not None and stated_partner is not None:
            assert group_of(stated_target) != group_of(stated_partner), ('target and partner are the same molecule of the pair', stated_target, stated_partner, pair)
    else:
        if target is None:
            assert stated_target is None, ('the paragraph names no single target; a stated target is an overreach', stated_target)
        else:
            assert stated_target is None or stated_target == target, ('real target', stated_target, target)
        if partner is not None:
            assert stated_partner is None or stated_partner == partner, ('real partner', stated_partner, partner)


def check_identity(world, call, run_id=None):
    """The generic checks of the identity block of an accepted call, for every type, real and synthetic: print the stated identity fields
    (value, quote, support) and check that every stated quote occurs exactly once in the chunk, every vocabulary value is valid, a name
    is inside its quote and the target_id is the normalized form of it, and that no field is stated that the generic rules forbid
    (a partner equal to the target, a partner role without a partner, a panel letter without a label number, a number outside the
    contract range, a temperature that does not convert). When ``run_id`` is given the expected target and partner of the type's passages module are
    checked (``check_expected_identity``, which documents the constant names SYNTHETIC_TARGET, SYNTHETIC_PARTNER, REAL_EXPECTED_TARGET,
    REAL_EXPECTED_PARTNER and the per-variant suffixes)."""
    chunk, assignment = chunk_of(world)
    block = split_answer(call['response'])[1]
    assert set(block) == set(ASKED)
    stated = {name for name in block if block[name]['status'] == 'stated'}
    for name in ASKED:
        item = block[name]
        if name in stated:
            print('IDENTITY STATED', name, item.get('value'), item.get('unit'), 'SUPPORT=' + str(item['support']), repr(item['quote']))
            assert identity_quote_span(chunk, item['quote']) is not None, (name, 'the quote must occur exactly once in the chunk')
            spec = IDENTITY_FIELDS[name]
            if spec['kind'] == 'vocab':
                assert item['value'] in spec['vocab'], (name, item['value'])
            if name in NAME_FIELDS:
                assert item['value'] in item['quote'] and normalize_identity_ref(item['value']) in normalize_identity_ref(item['quote']), name
        else:
            assert item['reason'] in IDENTITY_UNAVAILABLE_REASONS and item['value'] is None and item['quote'] is None, (name, item)
    print('IDENTITY UNAVAILABLE', {name: block[name]['reason'] for name in ASKED if name not in stated})
    validate_identity_answer(block, chunk)           # the same generic rules the leaf applies
    assert not ('partner_role' in stated and 'partner_id' not in stated)
    assert not ('panel_letter' in stated and 'label_number' not in stated)
    keys = identity_record_keys(block, chunk, assignment['offset'], experiment_type=world['expected_type'], source_ref=assignment['source_ref'])
    if 'target_id' in stated:
        assert keys['target_id'] == normalize_identity_ref(block['target_id']['value'])
    else:
        assert keys['target_id'] is None and 'target_id' in keys['unavailable_reasons']
    print('IDENTITY TARGET', repr(keys['target_id']), 'PARTNER', repr(keys['partner_id']), 'TEMPERATURE_C', keys['temperature_c'])
    if run_id is not None:
        check_expected_identity(keys, world['expected_type'], run_id)
    return keys


def report(world, run, run_id, result):
    journal = run.journal
    path = tuple(tuple(step) for step in journal.episodes(run_id)[0]['path'])
    every_call = journal.model_calls(run_id, path)
    calls = fill_calls(every_call)             # the unit's fills; the naming calls are checked by check_named
    units = [row[2] for row in journal.units(run_id, path)]
    print('ENDED', journal.run_state(run_id)[1])
    print('MODEL CALLS', len(calls), 'UNITS', len(units))
    for call in calls:
        answer = type_answer(call)
        print('CALL', call['position'], call['call_index'], 'asked again because:',
              (call['request'].get('context') or {}).get('previous_answer_was_rejected_because'))
        for name in answer:
            item = answer[name]
            if item['status'] == 'stated':
                print('STATED', name, item.get('value'), item.get('unit'), 'SUPPORT=' + str(item.get('support')), repr(item['quote']))
        print('UNAVAILABLE', [name for name in answer if answer[name]['status'] == 'unavailable'])
    # an accepted call is one that was not answered by a retry asking again because of its refusal
    accepted = accepted_of(calls)
    retried, failed, details = rejection_counts(calls, units)
    print('REJECTED AND RETRIED', len(calls) - len(accepted), 'ACCEPTED', len(accepted))
    print('REJECTED_RETRIED', retried)
    print('REJECTED_FAILED', failed)
    for detail in details:
        print('REJECTED DETAIL', detail)
    for call in accepted:
        check_identity(world, call, run_id)
    print('RETURN', result)
    store = world['store']
    check_named(world, every_call, [json.loads(store.get_artifact(ref)) for ref in result['record_refs']])
    for ref in result['record_refs']:
        record = json.loads(store.get_artifact(ref))
        if 'unavailable_reasons' in record:       # the stored leaf record: the identity keys at top level beside source_ref and experiment_type
            validate_identity({**{name: record[name] for name in LEAF_RECORD_IDENTITY}, 'source_ref': record['source_ref']})
            print('LEAF RECORD IDENTITY', {name: record[name] for name in LEAF_RECORD_IDENTITY})
    return calls, units


def finish(world, run, run_id):
    request = asyncio.run(run.next_decision())
    print('REQUEST instructions chars', len(request.instructions), 'schema chars', len(json.dumps(request.output_schema)),
          'context chars', len(json.dumps(request.context)))
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    calls, units = report(world, run, run_id, result)
    assert run.journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    asked = len(list((world['directory'] / 'model_calls').glob('call-*')))
    again = asyncio.run(resumed(world, run_id, run.journal).run())['result'].as_record()
    assert again == result
    assert len(list((world['directory'] / 'model_calls').glob('call-*'))) == asked
    assert not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    return result, calls, units


@pytest.mark.model_run
def test_the_real_popz_paragraph_fills_the_kd_with_its_quote_and_leaves_almost_everything_unknown(tmp_path):
    world, chunk = popz_world(tmp_path)
    run = linked(world, 'a105-extract-popz-real')
    result, calls, units = finish(world, run, 'a105-extract-popz-real')
    answer = type_answer(calls[0])
    kd = answer['kd']
    assert kd['status'] == 'stated' and kd['value'] == 20 and kd['unit'] == 'nM' and '20 nanomolar' in kd['quote']
    assert kd['quote'] in chunk
    stated = [name for name in answer if answer[name]['status'] == 'stated']
    print('SUPPORT CLASSES', {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_passage_with_many_spr_details_is_filled_and_the_grader_decides_criteria(tmp_path):
    world = synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-synthetic-real')
    stated = [name for name in field_names() if type_answer(calls[0])[name]['status'] == 'stated']
    print('STATED COUNT', len(stated), 'of', len(field_names()))
    assert result['finding']['newly_stated'] >= 5 and result['credit'] > 0.5
    world['store'].close()


@pytest.mark.model_run
def test_the_real_itc_paragraph_of_pmc7679967_states_only_what_it_states(tmp_path):
    """The real ITC legend of PMC7679967 (Hsp90 and Hop, Protein Science 2020, doi 10.1002/pro.3969): the model may
    state the KD with its error, n, the three independent experiments, the SD and the single-site model, and nothing
    else; everything else stays unavailable and no call is rejected."""
    world = itc_real_world(tmp_path)
    run = linked(world, 'a105-extract-itc-real-real')
    result, calls, units = finish(world, run, 'a105-extract-itc-real-real')
    # The estimator keeps asking while its forecast of a further gain is above the cost, so there are several calls:
    # every one of them is held to the same pass condition.
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        assert {'kd', 'stoichiometry'} <= stated <= set(itc_passages.HSP90_HOP_STATED)
        print('SUPPORT CLASSES', call['position'], {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
        kd = answer['kd']
        assert abs(kd['value'] * {'nM': 1, 'uM': 1000, 'mM': 1e6}[kd['unit']] - 578) < 1e-6 and kd['quote'] in itc_passages.HSP90_HOP
        assert answer['stoichiometry']['value'] == 0.544
        for name in ('enthalpy', 'entropy', 'temperature', 'cell_concentration', 'syringe_concentration', 'injection_count', 'expected_stoichiometry'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_itc_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = itc_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-itc-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-itc-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(itc_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_bli_paragraph_of_pmc13065029_states_only_what_it_states(tmp_path):
    """The real BLI Methods paragraph of PMC13065029 (pantinin-1 and the Chikungunya virus nsP2 protease, PLOS ONE,
    doi 10.1371/journal.pone.0346930): the model must state the KD of 9.29 uM and may state the 600 s dissociation, the
    triplicate, the control without the protease, and the few judgements the paragraph supports (sensor chemistry,
    the buffer reference, the fit); every other field stays unavailable and no call is rejected."""
    world = bli_real_world(tmp_path)
    run = linked(world, 'a105-extract-bli-real-real')
    result, calls, units = finish(world, run, 'a105-extract-bli-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(bli_passages.REAL_STATED) | bli_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        assert 'kd' in stated and stated <= allowed
        kd = answer['kd']
        assert abs(kd['value'] * {'nM': 1, 'uM': 1000, 'mM': 1e6}[kd['unit']] - 9290) < 1e-6 and kd['quote'] in bli_passages.REAL
        print('SUPPORT CLASSES', call['position'], {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
        for name in ('kon', 'koff', 'response_max', 'kd_spread', 'fit_r_squared', 'loading_level', 'concentration_series', 'kd_steady_state', 'regeneration', 'independent_sensors', 'baseline_stable'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_bli_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = bli_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-bli-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-bli-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(bli_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_gci_paragraph_of_pmc10213629_states_only_what_it_states(tmp_path):
    """The real GCI Results paragraph of PMC10213629 (CrcA and Crc, Frontiers in Microbiology 2023, doi
    10.3389/fmicb.2023.1195558): the model must state the KD of 10.99 uM and may state the equilibrium KD of 11.99 uM,
    the 15 pg/mm2, the 1:1 model and the few judgements the paragraph supports; the Hfq/amiE6ARN positive control is
    another experiment and every other field stays unavailable; no call is rejected."""
    world = gci_real_world(tmp_path)
    run = linked(world, 'a105-extract-gci-real-real')
    result, calls, units = finish(world, run, 'a105-extract-gci-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(gci_passages.REAL_STATED) | gci_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        assert 'kd' in stated and stated <= allowed
        kd = answer['kd']
        assert abs(kd['value'] * {'pM': 0.001, 'nM': 1, 'uM': 1000, 'mM': 1e6}[kd['unit']] - 10990) < 1e-6 and kd['quote'] in gci_passages.REAL
        print('SUPPORT CLASSES', call['position'], {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
        for name in ('kon', 'koff', 'response_max', 'kd_spread', 'concentration_series', 'replicate_count', 'regeneration', 'independent_channels_or_chips', 'baseline_stable', 'repeated_pulse_kinetics_used'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_gci_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = gci_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-gci-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-gci-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(gci_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_fp_paragraph_of_pmc10606924_states_only_what_it_states(tmp_path):
    """The real FP Results paragraph of PMC10606924 (FAM-labelled LANA1-22 peptide and nucleosomes, Int J Mol Sci 2023,
    doi 10.3390/ijms242015194): the model must state the Kd of 0.4 uM and may state its 0.09 uM uncertainty, the 100 nM tracer
    and the direct-titration format; every other field stays unavailable (the paragraph does not give the kind of the
    uncertainty, the model's name, a window, a series, a count or a control) and no call is rejected."""
    world = fp_real_world(tmp_path)
    run = linked(world, 'a105-extract-fp-real-real')
    result, calls, units = finish(world, run, 'a105-extract-fp-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(fp_passages.REAL_STATED) | fp_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        assert 'kd' in stated and stated <= allowed
        kd = answer['kd']
        assert abs(kd['value'] * {'pM': 0.001, 'nM': 1, 'uM': 1000, 'mM': 1e6}[kd['unit']] - 400) < 1e-6 and kd['quote'] in fp_passages.REAL
        print('SUPPORT CLASSES', call['position'], {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
        for name in ('ki', 'signal_minimum', 'signal_maximum', 'concentration_series', 'replicate_count', 'spread_kind', 'fit_model', 'equilibrium_reached', 'surface_adsorption_prevented', 'independent_titrations'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_fp_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = fp_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-fp-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-fp-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(fp_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_fret_paragraph_of_pmc10564622_states_only_what_it_states(tmp_path):
    """The real TR-FRET Results paragraph of PMC10564622 (CoraFluor-1 labelled KLHL11 and AF488-labelled CUL3 N-terminal
    domain, Free Radical Biology & Medicine 2023, doi 10.1016/j.freeradbiomed.2023.04.021): the model must state the KD of
    20 nM and may state the kind of its uncertainty (a confidence interval), the saturation (direct titration) format, that
    the read was time-resolved, that the labelling was direct (not through tag antibodies or streptavidin), that the dye
    labelling did not alter the binding, and the two judgements the paragraph supports (displacement by an unlabelled
    competitor, both formats used); every other field stays unavailable (no concentration, delay, window, ratio, plate,
    volume, incubation, count, model, kind of donor, or equilibrium is stated) and no call is rejected."""
    world = fret_real_world(tmp_path)
    run = linked(world, 'a105-extract-fret-real-real')
    result, calls, units = finish(world, run, 'a105-extract-fret-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(fret_passages.REAL_STATED) | fret_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        assert 'kd' in stated and stated <= allowed
        kd = answer['kd']
        assert abs(kd['value'] * {'pM': 0.001, 'nM': 1, 'uM': 1000, 'mM': 1e6}[kd['unit']] - 20) < 1e-6 and kd['quote'] in fret_passages.REAL
        print('SUPPORT CLASSES', call['position'], {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
        for name in ('ki', 'ec50', 'ic50', 'kd_spread', 'donor_concentration', 'acceptor_concentration', 'ratio_minimum', 'ratio_maximum', 'delay_time', 'integration_time', 'incubation_time', 'concentration_series', 'replicate_count', 'fit_model', 'donor_acceptor_pair', 'equilibrium_reached', 'ratiometric_readout_used', 'crosstalk_corrected', 'independent_titrations'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_fret_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = fret_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-fret-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-fret-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(fret_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_mst_paragraph_of_pmc13325309_states_only_what_it_states(tmp_path):
    """The real MST Methods paragraph of PMC13325309 (NHS-RED labelled BmpA with nucleoside ligands, Journal of Biological
    Chemistry 2026, doi 10.1016/j.jbc.2026.113206): the model must state the 1:1 fit model, and may state the other things the
    paragraph says as a number or a name (the labelled BmpA at 10 nM, the 10-min incubation, the
    100% excitation power, the triplicates, the NHS-RED dye label, the Tween-20 in the buffer) and that the ligands were
    titrated against the labelled partner (a direct titration); every other field stays unavailable (no KD, no list of
    concentrations, no number for the MST power, no temperature value, no readout kind, no signal size, no equilibrium
    statement, no capillary kind, no label-free detection) and no call is rejected."""
    world = mst_real_world(tmp_path)
    run = linked(world, 'a105-extract-mst-real-real')
    result, calls, units = finish(world, run, 'a105-extract-mst-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(mst_passages.REAL_STATED) | mst_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        assert 'fit_model' in stated and stated <= allowed
        print('SUPPORT CLASSES', call['position'], {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
        if 'labelled_concentration' in stated:       # 10 nM is the concentration of the labelled stock before equal volumes are mixed, so a careful reader may leave it unavailable
            fixed = answer['labelled_concentration']
            assert abs(fixed['value'] * {'pM': 0.001, 'nM': 1, 'uM': 1000, 'mM': 1e6}[fixed['unit']] - 10) < 1e-6 and fixed['quote'] in mst_passages.REAL
        assert answer['fit_model']['value'] == '1:1'
        for name in ('kd', 'ki', 'ec50', 'kd_spread', 'ki_spread', 'fnorm_amplitude', 'signal_to_noise', 'ir_laser_power', 'fhot_time', 'titration_point_count', 'temperature', 'concentration_series', 'spread_kind', 'readout_signal', 'capillary_type', 'equilibrium_reached', 'initial_fluorescence_checked', 'aggregation_or_adsorption_checked', 'independent_titrations'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_mst_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = mst_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-mst-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-mst-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(mst_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_trp_paragraph_of_pmc9654711_states_only_what_it_states(tmp_path):
    """The real Methods paragraph 4.14 of PMC9654711 (TRKB-ECD-His and coumarin compounds, International Journal of Molecular
    Sciences 2022, doi 10.3390/ijms232112734): the model must state the excitation at 295 nm and may state the protein at 50 nM and the
    330 nm at which the fit was made; every other field stays unavailable (no KD, the compounds are a range and not a list, the
    emission range is not one wavelength, 'room temperature' has no value, no size or direction of the change, no named model, no
    replicate count, no correction, blank or control) and no call is rejected."""
    world = trp_real_world(tmp_path)
    run = linked(world, 'a105-extract-trp-real-real')
    result, calls, units = finish(world, run, 'a105-extract-trp-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(trp_passages.REAL_STATED) | trp_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        assert 'excitation_wavelength' in stated and stated <= allowed
        print('SUPPORT CLASSES', call['position'], {support: sum(1 for name in stated if answer[name]['support'] == support) for support in ('direct', 'implied', 'about_something_else')})
        assert answer['excitation_wavelength']['value'] == 295 and answer['excitation_wavelength']['quote'] in trp_passages.REAL
        for name in ('kd', 'kd_spread', 'ksv', 'emission_shift', 'fluorescence_change', 'ligand_absorbance', 'added_volume_fraction', 'titration_point_count', 'incubation_time', 'temperature', 'replicate_count', 'concentration_series', 'spread_kind', 'fit_model', 'change_direction', 'emission_shift_direction', 'inner_filter_corrected', 'nonbinding_control_done', 'signal_saturates', 'equilibrium_reached', 'independent_titrations'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_trp_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = trp_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-trp-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-trp-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(trp_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_fcs_paragraph_of_pmc10782416_states_only_what_it_states(tmp_path):
    """The real Results paragraph 'Measurement of Binding Affinity' of PMC10782416 (the CLN3 aptamer and the c-Met protein, Analytical
    Chemistry 2023, doi 10.1021/acs.analchem.3c03341): the model must state the KD of 5 nM and may state its uncertainty of 1 nM, the
    100 pM of labelled aptamer, the single effective diffusing species of the correlation curves, the diffusion time as the readout
    and that another method (biolayer interferometry) also gave a value; every other field stays unavailable (the c-Met is a range and
    not a list, 'a simple binding model' is not named, the kind of the uncertainty, the diffusion times and coefficients, the particle
    number, the maximum fraction bound, the incubation, the replicates and every control are not stated in the chunk) and no call is
    rejected."""
    world = fcs_real_world(tmp_path)
    run = linked(world, 'a105-extract-fcs-real-real')
    result, calls, units = finish(world, run, 'a105-extract-fcs-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(fcs_passages.REAL_STATED) | fcs_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert 'kd' in stated and stated <= allowed
        kd = answer['kd']
        assert abs(kd['value'] * {'pM': 0.001, 'nM': 1, 'uM': 1000, 'mM': 1e6}[kd['unit']] - 5) < 1e-6 and kd['quote'] in fcs_passages.REAL
        for name in ('free_diffusion_time', 'bound_diffusion_time', 'free_diffusion_coefficient', 'bound_diffusion_coefficient', 'fraction_bound_maximum', 'particle_number', 'mass_ratio', 'laser_power', 'measurement_time', 'titration_point_count', 'incubation_time', 'temperature', 'replicate_count', 'concentration_series', 'spread_kind', 'fit_model', 'confocal_volume_calibrated', 'aggregates_checked', 'nonbinding_control_done', 'labelled_partner_at_or_below_kd', 'equilibrium_reached', 'independent_titrations'):
            assert answer[name]['status'] == 'unavailable'
    # the finding counts every held record's 21 criteria; the one conflict the real paragraph can give (the 100 pM aptamer below the window of
    # the labelled concentration) is at most one per held record
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_fcs_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = fcs_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-fcs-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-fcs-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(fcs_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_elisa_paragraph_of_pmc12527946_states_only_what_it_states(tmp_path):
    """The real Methods paragraph 'Solid-phase binding assay' of PMC12527946 (clusterin and RAP binding to the VLDLR ectodomain, Nature
    Structural & Molecular Biology 2025, doi 10.1038/s41594-025-01631-4): the model must state the coating concentration (10 ug/mL), the
    1 h binding step, the three washes after the ligand, the HRP enzyme, the BSA blocking, the absorbance readout, the one-site model and
    the subtraction of the no-ligand well signal, and may also state the indirect detection, the BSA-coated wells as a control and a
    format; every other field stays unavailable (no KD, EC50, IC50 or Ki value is in the paragraph, the concentrations are not a list or a
    number, 'room temperature' is not a number, no replicate count, plateau or background absorbance, and no statement of equilibrium,
    wash dissociation, avidity, coated-protein activity or detection interference) and no call is rejected."""
    world = elisa_real_world(tmp_path)
    run = linked(world, 'a105-extract-elisa-real-real')
    result, calls, units = finish(world, run, 'a105-extract-elisa-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(elisa_passages.REAL_STATED) | elisa_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert {'coating_concentration', 'incubation_time', 'wash_count'} <= stated and stated <= allowed
        assert answer['coating_concentration']['value'] == 10 and answer['coating_concentration']['unit'] == 'ug/mL' and answer['wash_count']['value'] == 3
        assert answer['incubation_time']['value'] * {'s': 1 / 3600, 'min': 1 / 60, 'h': 1}[answer['incubation_time']['unit']] == 1
        for name in ('kd', 'ki', 'ec50', 'ic50', 'kd_spread', 'ki_spread', 'signal_maximum', 'signal_background', 'titration_point_count', 'technical_replicate_count', 'temperature', 'replicate_count', 'concentration_series', 'spread_kind', 'saturation_reached', 'signal_in_linear_range', 'wash_dissociation_considered', 'equilibrium_reached', 'avidity_excluded', 'coated_protein_active', 'detection_does_not_interfere', 'independent_experiments', 'single_estimate_method'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_elisa_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = elisa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-elisa-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-elisa-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(elisa_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_alphascreen_paragraph_of_pmc4872087_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the optimal assay concentrations of PMC4872087 (AlphaLISA of His-Spindlin1 and biotin-H3(1-23)K4me3,
    Nucleic Acids Research 2016, doi 10.1093/nar/gkw089): the model must state the 17 ug/mL bead concentration, the streptavidin donor and
    nickel chelate acceptor beads, the cross-titration and the prevention of the hook effect; every other field stays unavailable (no KD,
    EC50, IC50 or Ki value, no signal, background, S/B or Z', no incubation time, temperature, plate format, replicate count or list of
    concentrations, no fit model, and no statement of a counter-screen, a linear range, equilibrium, a non-binding control, avidity, an
    effect of the tag or protection from light) and no call is rejected. The 15 nM and 30 nM partner concentrations are chosen 'for
    subsequent experiments' and are not allowed."""
    world = alpha_real_world(tmp_path)
    run = linked(world, 'a105-extract-alphascreen-real-real')
    result, calls, units = finish(world, run, 'a105-extract-alphascreen-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(alpha_passages.REAL_STATED) | alpha_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert set(alpha_passages.REAL_STATED) <= stated and stated <= allowed
        assert answer['bead_concentration']['value'] == 17 and answer['bead_concentration']['unit'] == 'ug/mL'
        assert answer['donor_bead']['value'] == 'streptavidin' and answer['acceptor_bead']['value'] == 'nickel_chelate' and answer['titration_design']['value'] == 'cross_titration'
        assert answer['hook_effect_handled']['value'] == 'yes'
        for name in ('kd', 'ki', 'ec50', 'ic50', 'kd_spread', 'ki_spread', 'signal_maximum', 'signal_background', 'signal_to_background', 'z_prime', 'labelled_partner_concentration', 'tagged_partner_concentration', 'plate_well_count', 'titration_point_count', 'technical_replicate_count', 'incubation_time', 'bead_incubation_time', 'temperature', 'replicate_count', 'concentration_series', 'assay_format', 'spread_kind', 'fit_model', 'counter_screen_done', 'partner_concentration_below_kd', 'signal_in_linear_range', 'equilibrium_reached', 'nonspecific_binding_checked', 'capture_does_not_alter_binding', 'light_protected', 'avidity_excluded', 'independent_experiments', 'single_estimate_method'):
            assert answer[name]['status'] == 'unavailable'
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_alphascreen_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = alpha_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-alphascreen-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-alphascreen-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(alpha_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_radioligand_paragraph_of_pmc11680790_states_only_what_it_states(tmp_path):
    """The real Methods paragraph on the analysis of the saturation and competition binding data of PMC11680790 (apelin receptor radioligand
    binding, Nature Communications 2024, doi 10.1038/s41467-024-55381-w). Pass: no call is rejected (none asked again because of a quote
    error); every field a call states is in the allowed set (the specific activity 2200 Ci/mmol, the radiolabel concentration of the
    competition fit 0.1 nM, the non-linear fit of the saturation data) with a quote that occurs exactly once in the chunk; nothing outside
    the allowed set is stated. The known KD of the radiolabel (0.076 nM) is cited, not measured, so it is outside the set (stating it
    fails); so are the Cheng-Prusoff equation, the fit model, the assay format and the protein concentration. Which allowed fields a
    call leaves unavailable is printed, not required."""
    world = radioligand_real_world(tmp_path)
    run = linked(world, 'a105-extract-radioligand-real-real')
    result, calls, units = finish(world, run, 'a105-extract-radioligand-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = set(radioligand_passages.REAL_STATED) | radioligand_passages.REAL_MAY_ALSO_STATE
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        # informational only: which of the allowed fields this call stated and which it left unavailable (not required)
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(radioligand_passages.REAL_STATED) - stated))
        # nothing outside the allowed set is stated (the borrowed 'known' KD of the radiolabel is outside it)
        assert stated <= allowed, sorted(stated - allowed)
        for name in stated:         # every stated field has the allowed value and unit, and its quote occurs exactly once in the chunk
            value, unit, _ = radioligand_passages.REAL_STATED[name]
            assert answer[name]['value'] == value and answer[name].get('unit') == unit
            assert quote_span(radioligand_passages.REAL, answer[name]['quote']) is not None
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_radioligand_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = radioligand_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-radioligand-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-radioligand-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(radioligand_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_spa_paragraph_of_pmc10945697_states_only_what_it_states(tmp_path):
    """The real Methods paragraph on the SPA experiments of purified LeuT variants of PMC10945697 (eLife 2024, doi 10.7554/eLife.87985). Pass: no call
    is rejected (none asked again because of a quote error); every field a call states is in the allowed set ``REAL_ALLOWED`` (the fields the
    paragraph clearly states by their general meaning, each with the values and units it allows) with a quote that occurs exactly once in the
    chunk and really says it; nothing outside the allowed set is stated. Which allowed fields a call leaves unavailable is printed, not
    required."""
    world = spa_real_world(tmp_path)
    run = linked(world, 'a105-extract-spa-real-real')
    result, calls, units = finish(world, run, 'a105-extract-spa-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = spa_passages.REAL_ALLOWED
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(allowed) - stated))
        assert stated <= set(allowed), sorted(stated - set(allowed))
        for name in stated:         # every stated field has an allowed value and unit, and its quote occurs exactly once in the chunk
            assert (answer[name]['value'], answer[name].get('unit')) in allowed[name], (name, answer[name]['value'], answer[name].get('unit'))
            assert quote_span(spa_passages.REAL, answer[name]['quote']) is not None
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_spa_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = spa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-spa-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-spa-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(spa_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_emsa_paragraph_of_pmc5137438_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the EMSA of purified SarA with the srn_9340 promoter fragment of PMC5137438 (Nucleic Acids Research 2016, doi 10.1093/nar/gkw777).
    Pass: no call is rejected (none asked again because of a quote error); every field a call states is in the allowed set ``REAL_ALLOWED`` (the fields the
    paragraph clearly states by their general meaning, each with the value and unit it allows) with a quote that occurs exactly once in the chunk and really says it;
    nothing outside the allowed set is stated. Which allowed fields a call leaves unavailable is printed, not required."""
    world = emsa_real_world(tmp_path)
    run = linked(world, 'a105-extract-emsa-real-real')
    result, calls, units = finish(world, run, 'a105-extract-emsa-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = emsa_passages.REAL_ALLOWED
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(allowed) - stated))
        assert stated <= set(allowed), sorted(stated - set(allowed))
        for name in stated:         # every stated field has an allowed value and unit, and its quote occurs exactly once in the chunk
            assert (answer[name]['value'], answer[name].get('unit')) in allowed[name], (name, answer[name]['value'], answer[name].get('unit'))
            assert quote_span(emsa_passages.REAL, answer[name]['quote']) is not None
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_emsa_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = emsa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-emsa-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-emsa-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(emsa_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_sec_mals_paragraph_of_pmc11068563_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the SEC-MALS of the MCU-NTD, the MCUb-NTD and their mixture of PMC11068563 (iScience 2024, doi 10.1016/j.isci.2024.109699).
    Pass: no call is rejected (none asked again because of a quote error); every field a call states is in the allowed set ``REAL_ALLOWED`` (the fields the
    paragraph clearly states by their general meaning, each with the value and unit it allows) with a quote that occurs exactly once in the chunk and really says it;
    nothing outside the allowed set is stated. Which allowed fields a call leaves unavailable is printed, not required."""
    world = sec_real_world(tmp_path)
    run = linked(world, 'a105-extract-sec-real-real')
    result, calls, units = finish(world, run, 'a105-extract-sec-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = sec_passages.REAL_ALLOWED
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(allowed) - stated))
        assert stated <= set(allowed), sorted(stated - set(allowed))
        for name in stated:         # every stated field has an allowed value and unit, and its quote occurs exactly once in the chunk
            assert (answer[name]['value'], answer[name].get('unit')) in allowed[name], (name, answer[name]['value'], answer[name].get('unit'))
            assert quote_span(sec_passages.REAL, answer[name]['quote']) is not None
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_sec_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = sec_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-sec-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-sec-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(sec_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import pla_passages
from .test_extraction_leaf import pla_real_world, pla_synthetic_world


@pytest.mark.model_run
def test_the_real_pla_methods_paragraph_of_pmc13709700_states_only_what_it_states(tmp_path):
    """The real Methods paragraph (2.10) on the proximity ligation assay of Flag-tagged Nsp1 and NXF1 of PMC13709700 (Viruses 2026, 'An N-Terminal Acidic Patch Underlies Differential Inhibition of mRNA Nuclear Export by Human Coronavirus Nsp1 Proteins', CC BY 4.0).
    Pass: ``check_real_run`` (no call is asked again because of a quote error; every stated field is in the allowed set with an allowed value and unit and a quote that occurs exactly once; nothing outside it is stated)."""
    check_real_run(pla_real_world(tmp_path), 'a105-extract-pla-real-real', pla_passages.REAL, pla_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_pla_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = pla_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-pla-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-pla-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(pla_passages.SYNTHETIC_STATED)
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


def check_real_run(world, run_id, passages_chunk, allowed):
    """The pass condition of a real-paragraph run: no call is rejected (none asked again because of a quote error); every field a call states is in ``allowed`` with an allowed value and unit and a quote that
    occurs exactly once in the chunk; nothing outside the allowed set is stated. Which allowed fields a call leaves unavailable is printed, not required."""
    run = linked(world, run_id)
    result, calls, units = finish(world, run, run_id)
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(allowed) - stated))
        assert stated <= set(allowed), sorted(stated - set(allowed))
        for name in stated:
            assert (answer[name]['value'], answer[name].get('unit')) in allowed[name], (name, answer[name]['value'], answer[name].get('unit'))
            assert quote_span(passages_chunk, answer[name]['quote']) is not None
    world['store'].close()


@pytest.mark.model_run
def test_the_real_dialysis_methods_paragraphs_of_pmc7996760_state_only_what_they_state(tmp_path):
    """The real Methods paragraphs on the equilibrium dialysis of the perfluoroalkyl acids with the proteins of PMC7996760 (Toxics 2021, doi 10.3390/toxics9030045, CC BY 4.0). Pass: ``check_real_run``."""
    check_real_run(dialysis_real_world(tmp_path), 'a105-extract-dialysis-real-methods-real', dialysis_passages.REAL, dialysis_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_the_real_dialysis_result_paragraph_of_pmc7996760_states_only_what_it_states(tmp_path):
    """The real Results paragraph on PFHxA and PPAR-alpha of PMC7996760. Pass: ``check_real_run``."""
    check_real_run(dialysis_real_result_world(tmp_path), 'a105-extract-dialysis-real-result-real', dialysis_passages.REAL_RESULT, dialysis_passages.REAL_RESULT_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_dialysis_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = dialysis_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-dialysis-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-dialysis-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(dialysis_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import split_reporter_passages
from .test_extraction_leaf import split_reporter_real_world, split_reporter_synthetic_world


@pytest.mark.model_run
def test_the_real_split_reporter_paragraphs_of_pmc8206089_state_only_what_they_state(tmp_path):
    """The two real Results paragraphs on the NanoBiT titration of PipX-SmBiT to PII-LgBiT of PMC8206089 (Scientific Reports 2021, 'Split NanoLuc technology allows quantitation of interactions between PII protein and its receptors with unprecedented sensitivity', CC BY 4.0).
    Pass: ``check_real_run`` (no call is asked again because of a quote error; every stated field is in the allowed set with an allowed value and unit and a quote that occurs exactly once; nothing outside it is stated)."""
    check_real_run(split_reporter_real_world(tmp_path), 'a105-extract-split-reporter-real-real', split_reporter_passages.REAL, split_reporter_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_split_reporter_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = split_reporter_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-split-reporter-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-split-reporter-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(split_reporter_passages.SYNTHETIC_STATED)
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import bret_passages
from .test_extraction_leaf import bret_real_world, bret_synthetic_world


@pytest.mark.model_run
def test_the_real_bret_paragraph_of_pmc6107161_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the BRET saturation assay of TLR1/2-Rluc8 with TIRAP-Venus, MyD88-Venus and V2R-Venus of PMC6107161 (PLoS One 2018, doi 10.1371/journal.pone.0202408, CC BY 4.0).
    Pass: ``check_real_run`` (no call is asked again because of a quote error; every stated field is in the allowed set with an allowed value and unit and a quote that occurs exactly once; nothing outside it is stated)."""
    check_real_run(bret_real_world(tmp_path), 'a105-extract-bret-real-real', bret_passages.REAL, bret_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_bret_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = bret_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-bret-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-bret-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(bret_passages.SYNTHETIC_STATED)
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_dsf_paragraph_of_pmc12686443_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the nanoDSF screening of the small molecule mimics of an Adhiron against the nucleoprotein of CCHFV of PMC12686443 (Communications Biology 2025, doi 10.1038/s42003-025-09137-x, CC BY 4.0).
    Pass: ``check_real_run`` (no call is asked again because of a quote error; every stated field is in the allowed set with an allowed value and unit and a quote that occurs exactly once; nothing outside it is stated)."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import dsf_passages
    from .test_extraction_leaf import dsf_real_world
    check_real_run(dsf_real_world(tmp_path), 'a105-extract-dsf-real-real', dsf_passages.REAL, dsf_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_dsf_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import dsf_passages
    from .test_extraction_leaf import dsf_synthetic_world
    world = dsf_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-dsf-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-dsf-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(dsf_passages.SYNTHETIC_STATED)
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_auc_paragraph_of_pmc12594183_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the sedimentation velocity of PPARgamma-DL, SIRT1 and their mixture of PMC12594183 (Proteins 2025, 'The SIRT1 N-Terminal Domain as a Common Binding Interface for PPARgamma Anchoring', CC BY 4.0).
    Pass: ``check_real_run`` (no call is asked again because of a quote error; every stated field is in the allowed set with an allowed value and unit and a quote that occurs exactly once; nothing outside it is stated)."""
    check_real_run(auc_real_world(tmp_path), 'a105-extract-auc-real-real', auc_passages.REAL, auc_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_auc_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = auc_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-auc-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-auc-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(auc_passages.SYNTHETIC_STATED)
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_cetsa_paragraph_of_pmc5760633_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the isothermal dose-response CETSA (46 degrees C) of the androgen receptor of PMC5760633 (Sci Rep 2018, 'Determining direct binders of the Androgen Receptor using a high-throughput Cellular Thermal Shift Assay', CC BY 4.0).
    Pass: ``check_real_run`` (no call is asked again because of a quote error; every stated field is in the allowed set with an allowed value and unit and a quote that occurs exactly once; nothing outside it is stated)."""
    check_real_run(cetsa_real_world(tmp_path), 'a105-extract-cetsa-real-real', cetsa_passages.REAL, cetsa_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_cetsa_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = cetsa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-cetsa-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-cetsa-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(cetsa_passages.SYNTHETIC_STATED)
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_y2h_paragraph_of_pmc5835670_states_only_what_it_states(tmp_path):
    """The real Methods paragraph 'Transcriptional Activity Detection and Yeast Two-Hybrid Assay' of PMC5835670 (Front. Plant Sci. 2018, doi 10.3389/fpls.2018.00258, CC BY).
    Pass: ``check_real_run`` (no call is asked again because of a quote error; every stated field is in the allowed set with an allowed value and unit and a quote that occurs exactly once; nothing outside it is stated)."""
    check_real_run(y2h_real_world(tmp_path), 'a105-extract-y2h-real-real', y2h_passages.REAL, y2h_passages.REAL_ALLOWED)


@pytest.mark.model_run
def test_a_synthetic_y2h_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = y2h_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-y2h-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-y2h-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(literature_y2h_extraction.field_names())
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_the_real_pulldown_paragraph_of_pmc3641083_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the reciprocal co-immunoprecipitation of RECQ1 and Ku70/80 of PMC3641083 (PLoS ONE 2013, doi 10.1371/journal.pone.0062481).
    Pass: no call is rejected (none asked again because of a quote error); every field a call states is in the allowed set ``REAL_ALLOWED`` (the fields the
    paragraph clearly states by their general meaning, each with the value it allows) with a quote that occurs exactly once in the chunk and really says it;
    nothing outside the allowed set is stated. Which allowed fields a call leaves unavailable is printed, not required."""
    world = pulldown_real_world(tmp_path)
    run = linked(world, 'a105-extract-pulldown-real-real')
    result, calls, units = finish(world, run, 'a105-extract-pulldown-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = pulldown_passages.REAL_ALLOWED
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(allowed) - stated))
        assert stated <= set(allowed), sorted(stated - set(allowed))
        for name in stated:         # every stated field has an allowed value and unit, and its quote occurs exactly once in the chunk
            assert (answer[name]['value'], answer[name].get('unit')) in allowed[name], (name, answer[name]['value'], answer[name].get('unit'))
            assert quote_span(pulldown_passages.REAL, answer[name]['quote']) is not None
    assert result['finding']['newly_stated'] < result['finding']['asked']


@pytest.mark.model_run
def test_a_synthetic_pulldown_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = pulldown_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-pulldown-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-pulldown-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(pulldown_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import spectro_direct_passages
from .test_extraction_leaf import spectro_direct_real_world, spectro_direct_synthetic_world


@pytest.mark.model_run
def test_the_real_spectro_direct_paragraph_of_pmc11795597_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the steady-state kinetics of the flavin reductase ThdF of PMC11795597 (J Biol Chem 2025, doi 10.1016/j.jbc.2024.108128, CC BY 4.0).
    Pass: no call is rejected without a later accepted call; every field a call states is in the allowed set ``REAL_ALLOWED`` (the fields the paragraph clearly states by their
    general meaning, each with the values it allows) with a quote that occurs exactly once in the chunk; nothing outside the allowed set is stated. Which allowed fields a call
    leaves unavailable is printed, not required."""
    world = spectro_direct_real_world(tmp_path)
    run = linked(world, 'a105-extract-spectro_direct-real-real')
    result, calls, units = finish(world, run, 'a105-extract-spectro_direct-real-real')
    calls = no_unrecovered_rejection(calls, units)
    allowed = spectro_direct_passages.REAL_ALLOWED
    for call in calls:
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(allowed) - stated))
        assert stated <= set(allowed), sorted(stated - set(allowed))
        for name in stated:         # every stated field has an allowed value and unit, and its quote occurs exactly once in the chunk
            assert (answer[name]['value'], answer[name].get('unit')) in allowed[name], (name, answer[name]['value'], answer[name].get('unit'))
            assert quote_span(spectro_direct_passages.REAL, answer[name]['quote']) is not None
    assert result['finding']['newly_stated'] < result['finding']['asked']
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_spectro_direct_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = spectro_direct_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-spectro_direct-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-spectro_direct-synthetic-real')
    calls = no_unrecovered_rejection(calls, units)
    for call in calls:
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        assert unstated == [] and set(answer) == set(spectro_direct_passages.SYNTHETIC_STATED)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import proximity_passages
from .test_extraction_leaf import proximity_real_world, proximity_synthetic_world


@pytest.mark.model_run
def test_the_real_proximity_paragraph_of_pmc11580435_states_only_what_it_states(tmp_path):
    """The real Results paragraph on the TurboID mass spectrometry and SAINT analysis of IpgC and MxiE of PMC11580435 (mSphere 2024, 'The promiscuous biotin ligase TurboID reveals the proxisome of the T3SS chaperone IpgC in Shigella flexneri', CC BY 4.0).
    Pass: every field an accepted call states is in the allowed set ``REAL_ALLOWED`` with an allowed value and unit and a quote that occurs exactly once in the chunk; nothing outside it is stated. A call asked again after a refusal is counted, not a failure."""
    world = proximity_real_world(tmp_path)
    run = linked(world, 'a105-extract-proximity-real-real')
    result, calls, units = finish(world, run, 'a105-extract-proximity-real-real')
    allowed = proximity_passages.REAL_ALLOWED
    for call in no_unrecovered_rejection(calls, units):
        answer = type_answer(call)
        stated = {name for name in answer if answer[name]['status'] == 'stated'}
        print('STATED FIELDS', call['position'], sorted(stated))
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        print('ALLOWED BUT NOT STATED', call['position'], sorted(set(allowed) - stated))
        assert stated <= set(allowed), sorted(stated - set(allowed))
        for name in stated:
            assert (answer[name]['value'], answer[name].get('unit')) in allowed[name], (name, answer[name]['value'], answer[name].get('unit'))
            assert quote_span(proximity_passages.REAL, answer[name]['quote']) is not None
    world['store'].close()


@pytest.mark.model_run
def test_a_synthetic_proximity_passage_stating_every_field_is_filled_and_every_criterion_decided(tmp_path):
    world = proximity_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-proximity-synthetic-real')
    result, calls, units = finish(world, run, 'a105-extract-proximity-synthetic-real')
    for call in no_unrecovered_rejection(calls, units):
        answer = type_answer(call)
        unstated = [name for name in answer if answer[name]['status'] != 'stated']
        print('NOT STATED', call['position'], unstated)
        stated = [name for name in answer if answer[name]['status'] == 'stated']
        print('SUPPORT CLASSES', call['position'], {support: sum(answer[name]['support'] == support for name in stated) for support in ('direct', 'implied', 'about_something_else')})      # informational only: no class distribution is asserted
        assert unstated == [] and set(answer) == set(proximity_passages.SYNTHETIC_FIELDS)
        assert all(answer[name]['support'] in ('direct', 'implied', 'about_something_else') for name in stated)
    assert result['finding']['newly_stated'] > 0 and result['credit'] == result['finding']['newly_stated'] / result['finding']['asked']
    world['store'].close()
