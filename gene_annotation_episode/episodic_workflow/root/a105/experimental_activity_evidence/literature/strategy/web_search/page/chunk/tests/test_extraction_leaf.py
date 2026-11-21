"""The extraction leaf through the real runner, without the model: the class and the folder; the real request the
model is sent (printed and checked); an answer the validator refuses is rejected before any unit exists; a valid answer
runs the one unit (the record is held through custody), the controller stops the Episode,
the return is admitted and resume replays it. Nothing is faked."""
import asyncio
import json
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding, ModelRequest, Rejected, ToolCall
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_extraction import (
    answer_schema, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.spr_passages import (
    POPZ_FIRST, PRIMARY, SYNTHETIC, popz_answer, popz_chunk, synthetic_answer)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import (
    literature_alpha_extraction, literature_bli_extraction, literature_elisa_extraction, literature_fcs_extraction, literature_fp_extraction, literature_fret_extraction, literature_gci_extraction, literature_itc_extraction, literature_mst_extraction, literature_pulldown_extraction, literature_radioligand_extraction, literature_spa_extraction, literature_trp_extraction)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import (
    alpha_passages, bli_passages, elisa_passages, fcs_passages, fp_passages, fret_passages, gci_passages, itc_passages, mst_passages, pulldown_passages, radioligand_passages, spa_passages, trp_passages)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_emsa_extraction
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import emsa_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_sec_extraction
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import sec_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_dialysis_extraction
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import dialysis_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_auc_extraction
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import auc_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import y2h_passages
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import proximity_passages
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    generation_schema)

from .leaf_world import EPISODE, PACKAGE, PATH, held_world, linked, resumed

FOLDER = Path(__file__).resolve().parents[1]
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/leaf_world.py', 'tests/test_extraction_leaf.py',
         'tests/test_extraction_model_run.py'}


def synthetic_world(tmp_path):
    data = SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + SYNTHETIC + ' Following text.', 16, len(data))


def popz_world(tmp_path):
    chunk, offset = popz_chunk()
    return held_world(tmp_path, PRIMARY.read_text(encoding='utf-8'), offset, len(chunk.encode())), chunk


def itc_synthetic_world(tmp_path, name='world'):
    data = itc_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + itc_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='itc')


def itc_real_world(tmp_path):
    text = 'Preceding text. ' + itc_passages.HSP90_HOP + ' Following text.'
    return held_world(tmp_path, text, 16, len(itc_passages.HSP90_HOP.encode()), experiment_type='itc')


def bli_synthetic_world(tmp_path, name='world'):
    data = bli_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + bli_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='bli')


def bli_real_world(tmp_path):
    text = 'Preceding text. ' + bli_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(bli_passages.REAL.encode()), experiment_type='bli')


def gci_synthetic_world(tmp_path, name='world'):
    data = gci_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + gci_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='gci')


def gci_real_world(tmp_path):
    text = 'Preceding text. ' + gci_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(gci_passages.REAL.encode()), experiment_type='gci')


def fp_synthetic_world(tmp_path, name='world'):
    data = fp_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + fp_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='fp')


def fp_real_world(tmp_path):
    text = 'Preceding text. ' + fp_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(fp_passages.REAL.encode()), experiment_type='fp')


def fret_synthetic_world(tmp_path, name='world'):
    data = fret_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + fret_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='fret')


def fret_real_world(tmp_path):
    text = 'Preceding text. ' + fret_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(fret_passages.REAL.encode()), experiment_type='fret')


def mst_synthetic_world(tmp_path, name='world'):
    data = mst_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + mst_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='mst')


def mst_real_world(tmp_path):
    text = 'Preceding text. ' + mst_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(mst_passages.REAL.encode()), experiment_type='mst')


def trp_synthetic_world(tmp_path, name='world'):
    data = trp_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + trp_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='trp_quenching')


def trp_real_world(tmp_path):
    text = 'Preceding text. ' + trp_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(trp_passages.REAL.encode()), experiment_type='trp_quenching')


def fcs_synthetic_world(tmp_path, name='world'):
    data = fcs_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + fcs_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='fcs')


def fcs_real_world(tmp_path):
    text = 'Preceding text. ' + fcs_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(fcs_passages.REAL.encode()), experiment_type='fcs')


def elisa_synthetic_world(tmp_path, name='world'):
    data = elisa_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + elisa_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='elisa')


def elisa_real_world(tmp_path):
    text = 'Preceding text. ' + elisa_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(elisa_passages.REAL.encode()), experiment_type='elisa')


def radioligand_synthetic_world(tmp_path, name='world'):
    data = radioligand_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + radioligand_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='radioligand')


def radioligand_real_world(tmp_path):
    text = 'Preceding text. ' + radioligand_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(radioligand_passages.REAL.encode()), experiment_type='radioligand')


def spa_synthetic_world(tmp_path, name='world'):
    data = spa_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + spa_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='spa')


def spa_real_world(tmp_path):
    text = 'Preceding text. ' + spa_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(spa_passages.REAL.encode()), experiment_type='spa')


def pulldown_synthetic_world(tmp_path, name='world'):
    data = pulldown_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + pulldown_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='pulldown')


def pulldown_real_world(tmp_path):
    text = 'Preceding text. ' + pulldown_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(pulldown_passages.REAL.encode()), experiment_type='pulldown')


def emsa_synthetic_world(tmp_path, name='world'):
    data = emsa_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + emsa_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='emsa')


def emsa_real_world(tmp_path):
    text = 'Preceding text. ' + emsa_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(emsa_passages.REAL.encode()), experiment_type='emsa')


def sec_synthetic_world(tmp_path, name='world'):
    data = sec_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + sec_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='sec')


def sec_real_world(tmp_path):
    text = 'Preceding text. ' + sec_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(sec_passages.REAL.encode()), experiment_type='sec')


def dialysis_synthetic_world(tmp_path, name='world'):
    data = dialysis_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + dialysis_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='dialysis')


def dialysis_real_world(tmp_path):
    text = 'Preceding text. ' + dialysis_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(dialysis_passages.REAL.encode()), experiment_type='dialysis')


def dialysis_real_result_world(tmp_path):
    text = 'Preceding text. ' + dialysis_passages.REAL_RESULT + ' Following text.'
    return held_world(tmp_path, text, 16, len(dialysis_passages.REAL_RESULT.encode()), experiment_type='dialysis')


def dsf_synthetic_world(tmp_path, name='world'):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import dsf_passages
    data = dsf_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + dsf_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='dsf')


def dsf_real_world(tmp_path):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import dsf_passages
    text = 'Preceding text. ' + dsf_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(dsf_passages.REAL.encode()), experiment_type='dsf')


def auc_synthetic_world(tmp_path, name='world'):
    data = auc_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + auc_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='auc')


def cetsa_synthetic_world(tmp_path, name='world'):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import cetsa_passages
    data = cetsa_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + cetsa_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='cetsa')


def cetsa_real_world(tmp_path):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import cetsa_passages
    text = 'Preceding text. ' + cetsa_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(cetsa_passages.REAL.encode()), experiment_type='cetsa')


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import split_reporter_passages


def split_reporter_synthetic_world(tmp_path, name='world'):
    data = split_reporter_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + split_reporter_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='split_reporter')


def split_reporter_real_world(tmp_path):
    text = 'Preceding text. ' + split_reporter_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(split_reporter_passages.REAL.encode()), experiment_type='split_reporter')


def bret_synthetic_world(tmp_path, name='world'):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import bret_passages
    data = bret_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + bret_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='bret')


def bret_real_world(tmp_path):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import bret_passages
    text = 'Preceding text. ' + bret_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(bret_passages.REAL.encode()), experiment_type='bret')


def auc_real_world(tmp_path):
    text = 'Preceding text. ' + auc_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(auc_passages.REAL.encode()), experiment_type='auc')


def proximity_synthetic_world(tmp_path, name='world'):
    data = proximity_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + proximity_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='proximity')


def proximity_real_world(tmp_path):
    text = 'Preceding text. ' + proximity_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(proximity_passages.REAL.encode()), experiment_type='proximity')


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import pla_passages


def pla_synthetic_world(tmp_path, name='world'):
    data = pla_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + pla_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='pla')


def pla_real_world(tmp_path):
    text = 'Preceding text. ' + pla_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(pla_passages.REAL.encode()), experiment_type='pla')


def y2h_synthetic_world(tmp_path, name='world'):
    data = y2h_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + y2h_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='y2h')


def y2h_real_world(tmp_path):
    text = 'Preceding text. ' + y2h_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(y2h_passages.REAL.encode()), experiment_type='y2h')


def alpha_synthetic_world(tmp_path, name='world'):
    data = alpha_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + alpha_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='alphascreen')


def alpha_real_world(tmp_path):
    text = 'Preceding text. ' + alpha_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(alpha_passages.REAL.encode()), experiment_type='alphascreen')


def test_the_class_is_its_own_binding_and_the_folder_holds_the_files_of_a_leaf():
    assert EPISODE.__bases__ == (EpisodeBinding,) and dict(EPISODE.child_slots) == {}
    assert EPISODE.binding_path == importlib_path()
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    assert found == FILES


def importlib_path():
    import importlib
    return importlib.import_module(PACKAGE + '.goal').BINDING_PATH


def test_the_real_request_is_the_chunk_the_instructions_and_the_derived_schema(tmp_path):
    world = synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-request')
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    schema_text = json.dumps(request.output_schema)
    print('REQUEST instructions chars', len(request.instructions), 'schema chars', len(schema_text),
          'context chars', len(json.dumps(request.context)))
    print('INSTRUCTIONS (first lines)\n' + '\n'.join(request.instructions.split('\n')[:3]))
    print('CONTEXT keys', list(request.context))
    assert request.output_schema == generation_schema(answer_schema())
    assert list(request.output_schema['properties']) == list(field_names()) == list(request.output_schema['required'])
    assert request.context['chunk'] == SYNTHETIC
    assert request.context['previous_answer_was_rejected_because'] is None
    assert 'grad' not in json.dumps(request.context).lower()    # nothing about the grader reaches the model
    world['store'].close()


def test_an_answer_with_a_quote_not_at_its_span_is_rejected_before_any_unit(tmp_path):
    world = synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    print('FEEDBACK', rejected.value.feedback)
    assert rejected.value.feedback['category'] == 'extraction_refused'
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    again = EPISODE.decide(summary, rejected.value.feedback, None)
    assert again.context['previous_answer_was_rejected_because'] == rejected.value.feedback
    world['store'].close()


def run_to_the_end(world, chunk, answer, run_id):
    run = linked(world, run_id)
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    assert summary['chunk'] == chunk
    call = EPISODE.action(answer, summary, run.view.records, None)
    assert isinstance(call, ToolCall) and call.name == 'extract'
    unit = asyncio.run(run.run_unit(call))
    return run, unit


def test_the_synthetic_passage_fills_the_grader_and_every_criterion_is_decided(tmp_path):
    world = synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, SYNTHETIC, synthetic_answer(), 'a105-extract-synthetic')
    outcome = unit['outcome']
    assert outcome['status'] == 'completed' and sorted(unit['produced']) == [outcome['record_ref']] and 'grader_ref' not in outcome
    records = run.view.records
    assert records.receipt(outcome['record_ref'])['how'] == 'produced'
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['assertion_ref'] == world['proposed']
    kd_span = record['spans'][record['quantities']['kd']['source_refs'][0]]
    assert kd_span['locator'] == 'bytes ' + str(16 + SYNTHETIC.encode().index(b'KD = 20 nM')) + '-' + str(16 + SYNTHETIC.encode().index(b'KD = 20 nM') + 10) + ' of the source'
    full = world['store'].get_artifact(world['artifact'])
    start = int(kd_span['locator'].split()[1].split('-')[0])
    assert full[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    print('RESULT', result)
    assert world['directory'].joinpath('journal.sqlite3').exists()
    assert run.journal.run_state('a105-extract-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    assert result['record_refs'] == [outcome['record_ref']]
    again = asyncio.run(resumed(world, 'a105-extract-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_popz_paragraph_with_only_the_kd_stated_decides_nothing_and_still_ends_by_yield_stop(tmp_path):
    world, chunk = popz_world(tmp_path)
    assert chunk.startswith(POPZ_FIRST)
    run, unit = run_to_the_end(world, chunk, popz_answer(chunk), 'a105-extract-popz')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert 1 <= summary['counts']['newly_stated'] < summary['counts']['asked']
    assert EPISODE.credit(summary, run.view.records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 20
    span = record['spans']['span_kd']
    start, end = (int(part) for part in span['locator'].split()[1].split('-'))
    assert PRIMARY.read_bytes()[start:end].decode() == span['quote'] and '20 nanomolar' in span['quote']
    # One unit that decides nothing does not by itself stop the estimator (its forecast of a further gain is still
    # above the cost); the same extraction again decides nothing either, and the estimator stops the Episode.
    call = EPISODE.action(popz_answer(chunk), summary, run.view.records, None)
    units = 1
    while not run.view.controller_state.stop:
        asyncio.run(run.run_unit(call))
        units += 1
    print('UNITS BEFORE THE ESTIMATOR STOPPED THE EPISODE', units)
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-popz')[1]['ended_by'] == 'yield_stop'
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and 0 < result['credit'] < 1  # the same answer holds the same records: one grader
    world['store'].close()


def test_the_itc_commission_asks_for_the_itc_form_and_the_spr_commission_for_the_spr_form(tmp_path):
    spr = synthetic_world(tmp_path)
    itc = itc_synthetic_world(tmp_path, 'second_world')
    requests = {}
    for kind, world in (('spr', spr), ('itc', itc)):
        run = linked(world, 'a105-extract-request-' + kind)
        requests[kind] = asyncio.run(run.next_decision())
        assert requests[kind].context['experiment_type'] == kind
    assert requests['spr'].output_schema == generation_schema(answer_schema())
    assert requests['itc'].output_schema == generation_schema(literature_itc_extraction.answer_schema())
    assert requests['spr'].output_schema != requests['itc'].output_schema
    assert 'isothermal titration calorimetry' in requests['itc'].instructions and 'plasmon' not in requests['itc'].instructions
    assert 'plasmon resonance' in requests['spr'].instructions and 'calorimetry' not in requests['spr'].instructions
    assert 'grad' not in json.dumps(requests['itc'].context).lower()
    for world in (spr, itc):
        world['store'].close()


def test_an_itc_answer_is_checked_by_the_itc_validator_and_an_spr_answer_is_refused_for_an_itc_commission(tmp_path):
    world = itc_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-itc-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = itc_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(synthetic_answer(), summary, run.view.records, None)   # an SPR-shaped answer is not an ITC answer
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_itc_synthetic_passage_fills_the_itc_grader_and_every_criterion_is_decided(tmp_path):
    world = itc_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, itc_passages.SYNTHETIC, itc_passages.synthetic_answer(), 'a105-extract-itc-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'itc'
    assert record['experiment_ref'].startswith('itc:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-itc-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-itc-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_itc_paragraph_states_only_its_numbers_and_decides_one_criterion(tmp_path):
    world = itc_real_world(tmp_path)
    run, unit = run_to_the_end(world, itc_passages.HSP90_HOP, itc_passages.hsp90_hop_answer(), 'a105-extract-itc-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 0.578 and record['quantities']['enthalpy']['value'] is None
    span = record['spans']['span_kd']
    start, end = (int(part) for part in span['locator'].split()[1].split('-'))
    assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_bli_commission_asks_for_the_bli_form_and_neither_the_spr_nor_the_itc_form(tmp_path):
    bli = bli_synthetic_world(tmp_path)
    run = linked(bli, 'a105-extract-request-bli')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'bli'
    assert request.output_schema == generation_schema(literature_bli_extraction.answer_schema())
    assert request.output_schema != generation_schema(answer_schema()) and request.output_schema != generation_schema(literature_itc_extraction.answer_schema())
    assert 'bio-layer interferometry' in request.instructions and 'plasmon' not in request.instructions and 'calorimetry' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    bli['store'].close()


def test_a_bli_answer_is_checked_by_the_bli_validator_and_an_itc_answer_is_refused_for_a_bli_commission(tmp_path):
    world = bli_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-bli-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = bli_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(itc_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_bli_synthetic_passage_fills_the_bli_grader_and_every_criterion_is_decided(tmp_path):
    world = bli_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, bli_passages.SYNTHETIC, bli_passages.synthetic_answer(), 'a105-extract-bli-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'bli'
    assert record['experiment_ref'].startswith('bli:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-bli-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-bli-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_bli_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = bli_real_world(tmp_path)
    run, unit = run_to_the_end(world, bli_passages.REAL, bli_passages.real_answer(), 'a105-extract-bli-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 9.29 and record['quantities']['koff']['value'] is None
    for span in record['spans'].values():
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_gci_commission_asks_for_the_gci_form_and_none_of_the_others(tmp_path):
    gci = gci_synthetic_world(tmp_path)
    run = linked(gci, 'a105-extract-request-gci')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'gci'
    assert request.output_schema == generation_schema(literature_gci_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'grating-coupled interferometry' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    gci['store'].close()


def test_a_gci_answer_is_checked_by_the_gci_validator_and_a_bli_answer_is_refused_for_a_gci_commission(tmp_path):
    world = gci_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-gci-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = gci_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(bli_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_gci_synthetic_passage_fills_the_gci_grader_and_every_criterion_is_decided(tmp_path):
    world = gci_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, gci_passages.SYNTHETIC, gci_passages.synthetic_answer(), 'a105-extract-gci-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'gci'
    assert record['experiment_ref'].startswith('gci:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-gci-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-gci-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_gci_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = gci_real_world(tmp_path)
    run, unit = run_to_the_end(world, gci_passages.REAL, gci_passages.real_answer(), 'a105-extract-gci-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 10.99 and record['quantities']['koff']['value'] is None
    for span in record['spans'].values():
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_fp_commission_asks_for_the_fp_form_and_none_of_the_others(tmp_path):
    fp = fp_synthetic_world(tmp_path)
    run = linked(fp, 'a105-extract-request-fp')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'fp'
    assert request.output_schema == generation_schema(literature_fp_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'fluorescence polarization' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    fp['store'].close()


def test_an_fp_answer_is_checked_by_the_fp_validator_and_a_gci_answer_is_refused_for_an_fp_commission(tmp_path):
    world = fp_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-fp-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = fp_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(gci_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_fp_synthetic_passage_fills_the_fp_grader_and_every_criterion_is_decided(tmp_path):
    world = fp_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, fp_passages.SYNTHETIC, fp_passages.synthetic_answer(), 'a105-extract-fp-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'fp'
    assert record['experiment_ref'].startswith('fp:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-fp-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-fp-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_fp_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = fp_real_world(tmp_path)
    run, unit = run_to_the_end(world, fp_passages.REAL, fp_passages.real_answer(), 'a105-extract-fp-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 0.4 and record['quantities']['ki']['value'] is None
    for span in record['spans'].values():
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_fret_commission_asks_for_the_fret_form_and_none_of_the_others(tmp_path):
    fret = fret_synthetic_world(tmp_path)
    run = linked(fret, 'a105-extract-request-fret')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'fret'
    assert request.output_schema == generation_schema(literature_fret_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'energy transfer' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    fret['store'].close()


def test_a_fret_answer_is_checked_by_the_fret_validator_and_an_fp_answer_is_refused_for_a_fret_commission(tmp_path):
    world = fret_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-fret-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = fret_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(fp_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_fret_synthetic_passage_fills_the_fret_grader_and_every_criterion_is_decided(tmp_path):
    world = fret_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, fret_passages.SYNTHETIC, fret_passages.synthetic_answer(), 'a105-extract-fret-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'fret'
    assert record['experiment_ref'].startswith('fret:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-fret-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-fret-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_fret_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = fret_real_world(tmp_path)
    run, unit = run_to_the_end(world, fret_passages.REAL, fret_passages.real_answer(), 'a105-extract-fret-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 20 and record['quantities']['ki']['value'] is None
    for span in record['spans'].values():
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_mst_commission_asks_for_the_mst_form_and_none_of_the_others(tmp_path):
    mst = mst_synthetic_world(tmp_path)
    run = linked(mst, 'a105-extract-request-mst')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'mst'
    assert request.output_schema == generation_schema(literature_mst_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'microscale thermophoresis' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    mst['store'].close()


def test_an_mst_answer_is_checked_by_the_mst_validator_and_a_fret_answer_is_refused_for_an_mst_commission(tmp_path):
    world = mst_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-mst-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = mst_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(fret_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_mst_synthetic_passage_fills_the_mst_grader_and_every_criterion_is_decided(tmp_path):
    world = mst_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, mst_passages.SYNTHETIC, mst_passages.synthetic_answer(), 'a105-extract-mst-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'mst'
    assert record['experiment_ref'].startswith('mst:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-mst-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-mst-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_mst_paragraph_states_only_what_it_states_and_decides_no_criterion(tmp_path):
    world = mst_real_world(tmp_path)
    run, unit = run_to_the_end(world, mst_passages.REAL, mst_passages.real_answer(), 'a105-extract-mst-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] is None and record['quantities']['labelled_concentration']['value'] == 10
    for span in record['spans'].values():
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_trp_commission_asks_for_the_trp_form_and_none_of_the_others(tmp_path):
    trp = trp_synthetic_world(tmp_path)
    run = linked(trp, 'a105-extract-request-trp')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'trp_quenching'
    assert request.output_schema == generation_schema(literature_trp_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'tryptophan' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    trp['store'].close()


def test_a_trp_answer_is_checked_by_the_trp_validator_and_an_mst_answer_is_refused_for_a_trp_commission(tmp_path):
    world = trp_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-trp-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = trp_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(mst_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_trp_synthetic_passage_fills_the_trp_grader_and_every_criterion_is_decided(tmp_path):
    world = trp_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, trp_passages.SYNTHETIC, trp_passages.synthetic_answer(), 'a105-extract-trp-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'trp_quenching'
    assert record['experiment_ref'].startswith('trp_quenching:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-trp-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-trp-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_trp_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = trp_real_world(tmp_path)
    run, unit = run_to_the_end(world, trp_passages.REAL, trp_passages.real_answer(), 'a105-extract-trp-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] is None and record['quantities']['protein_concentration']['value'] == 50
    for span in record['spans'].values():
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_fcs_commission_asks_for_the_fcs_form_and_none_of_the_others(tmp_path):
    fcs = fcs_synthetic_world(tmp_path)
    run = linked(fcs, 'a105-extract-request-fcs')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'fcs'
    assert request.output_schema == generation_schema(literature_fcs_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'correlation spectroscopy' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    fcs['store'].close()


def test_an_fcs_answer_is_checked_by_the_fcs_validator_and_a_trp_answer_is_refused_for_an_fcs_commission(tmp_path):
    world = fcs_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-fcs-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = fcs_passages.synthetic_answer()
    answer['kd']['quote'] = 'KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(trp_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_fcs_synthetic_passage_fills_the_fcs_grader_and_every_criterion_is_decided(tmp_path):
    world = fcs_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, fcs_passages.SYNTHETIC, fcs_passages.synthetic_answer(), 'a105-extract-fcs-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'fcs'
    assert record['experiment_ref'].startswith('fcs:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 10] == b'KD = 20 nM'
    for span in record['spans'].values():       # the multi-byte quotes (a degree sign, micro signs, superscript twos) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-fcs-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-fcs-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_fcs_paragraph_states_only_what_it_states_and_decides_two_criteria_one_of_them_conflicting(tmp_path):
    world = fcs_real_world(tmp_path)
    run, unit = run_to_the_end(world, fcs_passages.REAL, fcs_passages.real_answer(), 'a105-extract-fcs-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 5 and record['quantities']['labelled_concentration']['value'] == 100 and record['quantities']['free_diffusion_time']['value'] is None
    for span in record['spans'].values():
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_elisa_commission_asks_for_the_elisa_form_and_none_of_the_others(tmp_path):
    elisa = elisa_synthetic_world(tmp_path)
    run = linked(elisa, 'a105-extract-request-elisa')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'elisa'
    assert request.output_schema == generation_schema(literature_elisa_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'ELISA-style' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    elisa['store'].close()


def test_an_elisa_answer_is_checked_by_the_elisa_validator_and_an_fcs_answer_is_refused_for_an_elisa_commission(tmp_path):
    world = elisa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-elisa-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = elisa_passages.synthetic_answer()
    answer['kd']['quote'] = 'apparent KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(fcs_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_elisa_synthetic_passage_fills_the_elisa_grader_and_every_criterion_is_decided(tmp_path):
    world = elisa_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, elisa_passages.SYNTHETIC, elisa_passages.synthetic_answer(), 'a105-extract-elisa-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'elisa'
    assert record['experiment_ref'].startswith('elisa:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 19] == b'apparent KD = 20 nM'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-elisa-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-elisa-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_elisa_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = elisa_real_world(tmp_path)
    run, unit = run_to_the_end(world, elisa_passages.REAL, elisa_passages.real_answer(), 'a105-extract-elisa-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['coating_concentration']['value'] == 10 and record['quantities']['wash_count']['value'] == 3 and record['quantities']['kd']['value'] is None
    assert record['fit_model'] == '1:1' and record['facts']['blank_subtracted']['answer'] == 'yes'
    for span in record['spans'].values():       # the thin spaces, micro and minus signs of the real paragraph are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_alphascreen_commission_asks_for_the_alphascreen_form_and_none_of_the_others(tmp_path):
    alpha = alpha_synthetic_world(tmp_path)
    run = linked(alpha, 'a105-extract-request-alphascreen')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'alphascreen'
    assert request.output_schema == generation_schema(literature_alpha_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema(), literature_elisa_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'AlphaScreen' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions and 'ELISA' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    alpha['store'].close()


def test_an_alphascreen_answer_is_checked_by_the_alphascreen_validator_and_an_elisa_answer_is_refused_for_an_alphascreen_commission(tmp_path):
    world = alpha_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-alphascreen-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = alpha_passages.synthetic_answer()
    answer['kd']['quote'] = 'apparent KD = 21 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(elisa_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_alphascreen_synthetic_passage_fills_the_alphascreen_grader_and_every_criterion_is_decided(tmp_path):
    world = alpha_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, alpha_passages.SYNTHETIC, alpha_passages.synthetic_answer(), 'a105-extract-alphascreen-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'alphascreen'
    assert record['experiment_ref'].startswith('alphascreen:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 19] == b'apparent KD = 20 nM'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-alphascreen-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-alphascreen-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_alphascreen_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = alpha_real_world(tmp_path)
    run, unit = run_to_the_end(world, alpha_passages.REAL, alpha_passages.real_answer(), 'a105-extract-alphascreen-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['bead_concentration']['value'] == 17 and record['quantities']['kd']['value'] is None
    assert record['titration_design'] == 'cross_titration' and record['facts']['hook_effect_handled']['answer'] == 'yes'
    for span in record['spans'].values():       # the Greek mu and the en dash of the real paragraph are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_commission_accepts_alphascreen_as_an_experiment_type_and_the_earlier_ones_still():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:11] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen')     # the earlier ones are unchanged; radioligand follows


def test_the_radioligand_commission_asks_for_the_radioligand_form_and_none_of_the_others(tmp_path):
    world = radioligand_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-request-radioligand')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'radioligand'
    assert request.output_schema == generation_schema(literature_radioligand_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema(), literature_elisa_extraction.answer_schema(), literature_alpha_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'radioligand binding experiment' in request.instructions and 'Cheng-Prusoff' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions and 'ELISA' not in request.instructions and 'AlphaScreen' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'the exact quote text must appear only once in the chunk' in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    world['store'].close()


def test_a_radioligand_answer_is_checked_by_the_radioligand_validator_and_an_alphascreen_answer_is_refused_for_a_radioligand_commission(tmp_path):
    world = radioligand_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-radioligand-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = radioligand_passages.synthetic_answer()
    answer['kd']['quote'] = 'a KD = 2.1 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(alpha_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_radioligand_synthetic_passage_fills_the_radioligand_grader_and_every_criterion_is_decided(tmp_path):
    world = radioligand_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, radioligand_passages.SYNTHETIC, radioligand_passages.synthetic_answer(), 'a105-extract-radioligand-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'radioligand'
    assert record['experiment_ref'].startswith('radioligand:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 13] == b'a KD = 2.0 nM'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-radioligand-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-radioligand-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_radioligand_paragraph_states_only_what_it_states_and_decides_one_criterion(tmp_path):
    world = radioligand_real_world(tmp_path)
    run, unit = run_to_the_end(world, radioligand_passages.REAL, radioligand_passages.real_answer(), 'a105-extract-radioligand-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] is None and record['quantities']['specific_activity']['value'] == 2200 and record['quantities']['bmax']['value'] is None
    assert record['quantities']['radioligand_concentration']['value'] == 0.1 and record['facts']['nonlinear_fit_used']['answer'] == 'yes'
    for span in record['spans'].values():       # the thin spaces of the real paragraph are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_commission_accepts_radioligand_as_an_experiment_type():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:12] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand')     # the earlier ones are unchanged; spa follows


def test_the_commission_accepts_spa_as_an_experiment_type_and_the_earlier_ones_still():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:13] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa')     # the earlier ones are unchanged; pulldown follows


def test_the_spa_commission_asks_for_the_spa_form_and_none_of_the_others(tmp_path):
    world = spa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-request-spa')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'spa'
    assert request.output_schema == generation_schema(literature_spa_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema(), literature_elisa_extraction.answer_schema(), literature_alpha_extraction.answer_schema(), literature_radioligand_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'scintillation proximity assay (SPA) binding experiment' in request.instructions and 'Cheng-Prusoff' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions and 'ELISA' not in request.instructions and 'AlphaScreen' not in request.instructions
    assert 'radioligand binding experiment' not in request.instructions and 'filtration' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'the exact quote text must appear only once in the chunk' in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    world['store'].close()


def test_an_spa_answer_is_checked_by_the_spa_validator_and_a_radioligand_answer_is_refused_for_an_spa_commission(tmp_path):
    world = spa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-spa-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = spa_passages.synthetic_answer()
    answer['kd']['quote'] = 'a KD = 2.1 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(radioligand_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_spa_synthetic_passage_fills_the_spa_grader_and_every_criterion_is_decided(tmp_path):
    world = spa_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, spa_passages.SYNTHETIC, spa_passages.synthetic_answer(), 'a105-extract-spa-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'spa'
    assert record['experiment_ref'].startswith('spa:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 13] == b'a KD = 2.0 nM'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-spa-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-spa-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_spa_paragraph_states_only_what_it_states_and_decides_two_criteria(tmp_path):
    world = spa_real_world(tmp_path)
    run, unit = run_to_the_end(world, spa_passages.REAL, spa_passages.real_answer(), 'a105-extract-spa-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] is None and record['quantities']['specific_activity']['value'] == 25 and record['quantities']['bmax']['value'] is None
    assert record['quantities']['bead_concentration']['value'] == 1.25 and record['facts']['ligand_depletion_checked']['answer'] == 'yes' and record['bead_type'] == 'ysi'
    for span in record['spans'].values():       # the micro signs, degree sign and greater-or-equal sign of the real paragraph are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_commission_accepts_emsa_sec_dialysis_and_auc_as_experiment_types_and_the_earlier_ones_still():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis', 'auc')
    assert len(EXPERIMENT_TYPES) == 18 and EXPERIMENT_TYPES[:17] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis') and EXPERIMENT_TYPES[-1] == 'auc'


def test_the_emsa_commission_asks_for_the_emsa_form_and_none_of_the_others(tmp_path):
    world = emsa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-request-emsa')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'emsa'
    assert request.output_schema == generation_schema(literature_emsa_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema(), literature_elisa_extraction.answer_schema(), literature_alpha_extraction.answer_schema(), literature_radioligand_extraction.answer_schema(), literature_spa_extraction.answer_schema(), literature_pulldown_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'electrophoretic mobility shift assay (EMSA' in request.instructions and 'apparent dissociation constant' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'ELISA' not in request.instructions and 'AlphaScreen' not in request.instructions and 'scintillation' not in request.instructions and 'Cheng-Prusoff' not in request.instructions and 'pull-down' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'the exact quote text must appear only once in the chunk' in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    world['store'].close()


def test_an_emsa_answer_is_checked_by_the_emsa_validator_and_a_pulldown_answer_is_refused_for_an_emsa_commission(tmp_path):
    world = emsa_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-emsa-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = emsa_passages.synthetic_answer()
    answer['kd']['quote'] = 'an apparent KD of 25 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(pulldown_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_emsa_synthetic_passage_fills_the_emsa_grader_and_every_criterion_is_decided(tmp_path):
    world = emsa_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, emsa_passages.SYNTHETIC, emsa_passages.synthetic_answer(), 'a105-extract-emsa-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'emsa'
    assert record['experiment_ref'].startswith('emsa:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 23] == b'an apparent KD of 20 nM'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-emsa-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-emsa-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_emsa_paragraph_states_only_what_it_states_and_decides_four_criteria(tmp_path):
    world = emsa_real_world(tmp_path)
    run, unit = run_to_the_end(world, emsa_passages.REAL, emsa_passages.real_answer(), 'a105-extract-emsa-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['kd']['value'] == 11 and record['quantities']['kd']['unit'] == 'nM' and record['facts']['shift_detected']['answer'] == 'yes' and record['facts']['probe_alone_lane_shown']['answer'] == 'unknown'
    for span in record['spans'].values():       # the quotes of the real paragraph (with its minus and plus-minus signs) are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_sec_commission_asks_for_the_sec_form_and_none_of_the_others(tmp_path):
    world = sec_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-request-sec')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'sec'
    assert request.output_schema == generation_schema(literature_sec_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema(), literature_elisa_extraction.answer_schema(), literature_alpha_extraction.answer_schema(), literature_radioligand_extraction.answer_schema(), literature_spa_extraction.answer_schema(), literature_pulldown_extraction.answer_schema(), literature_emsa_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'size-exclusion chromatography (SEC' in request.instructions and 'multi-angle light scattering' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'ELISA' not in request.instructions and 'AlphaScreen' not in request.instructions and 'scintillation' not in request.instructions and 'Cheng-Prusoff' not in request.instructions and 'pull-down' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'electrophoretic' not in request.instructions and 'gel shift' not in request.instructions
    assert 'the exact quote text must appear only once in the chunk' in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    world['store'].close()


def test_an_sec_answer_is_checked_by_the_sec_validator_and_an_emsa_answer_is_refused_for_an_sec_commission(tmp_path):
    world = sec_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-sec-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = sec_passages.synthetic_answer()
    answer['kd']['quote'] = 'an apparent KD of 250 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(emsa_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_sec_synthetic_passage_fills_the_sec_grader_and_every_criterion_is_decided(tmp_path):
    world = sec_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, sec_passages.SYNTHETIC, sec_passages.synthetic_answer(), 'a105-extract-sec-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'sec'
    assert record['experiment_ref'].startswith('sec:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 24] == b'an apparent KD of 200 nM'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-sec-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-sec-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_sec_paragraph_states_only_what_it_states_and_decides_four_criteria(tmp_path):
    world = sec_real_world(tmp_path)
    run, unit = run_to_the_end(world, sec_passages.REAL, sec_passages.real_answer(), 'a105-extract-sec-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['complex_mass_measured']['value'] == 21.7 and record['quantities']['complex_mass_measured']['unit'] == 'kDa' and record['facts']['complex_peak_detected']['answer'] == 'yes' and record['facts']['single_component_control_done']['answer'] == 'unknown'
    for span in record['spans'].values():       # the quotes of the real paragraph (with its non-breaking spaces and plus-minus signs) are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_dialysis_commission_asks_for_the_dialysis_form_and_none_of_the_others(tmp_path):
    world = dialysis_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-request-dialysis')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'dialysis'
    assert request.output_schema == generation_schema(literature_dialysis_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema(), literature_elisa_extraction.answer_schema(), literature_alpha_extraction.answer_schema(), literature_radioligand_extraction.answer_schema(), literature_spa_extraction.answer_schema(), literature_pulldown_extraction.answer_schema(), literature_emsa_extraction.answer_schema(), literature_sec_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'equilibrium dialysis or ultrafiltration binding experiment' in request.instructions and 'semipermeable membrane' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'ELISA' not in request.instructions and 'AlphaScreen' not in request.instructions and 'Cheng-Prusoff' not in request.instructions and 'pull-down' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'electrophoretic' not in request.instructions and 'gel shift' not in request.instructions and 'size-exclusion' not in request.instructions
    assert 'the exact quote text must appear only once in the chunk' in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    world['store'].close()


def test_a_dialysis_answer_is_checked_by_the_dialysis_validator_and_an_sec_answer_is_refused_for_a_dialysis_commission(tmp_path):
    world = dialysis_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-dialysis-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = dialysis_passages.synthetic_answer()
    answer['kd']['quote'] = 'a KD of 250 nM'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('kd:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(sec_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_dialysis_synthetic_passage_fills_the_dialysis_grader_and_every_criterion_is_decided(tmp_path):
    world = dialysis_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, dialysis_passages.SYNTHETIC, dialysis_passages.synthetic_answer(), 'a105-extract-dialysis-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'dialysis'
    assert record['experiment_ref'].startswith('dialysis:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['kd']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 14] == b'a KD of 200 nM'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-dialysis-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-dialysis-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_dialysis_paragraphs_state_only_what_they_state_and_decide_two_criteria(tmp_path):
    world = dialysis_real_world(tmp_path)
    run, unit = run_to_the_end(world, dialysis_passages.REAL, dialysis_passages.real_answer(), 'a105-extract-dialysis-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['membrane_cutoff']['value'] == 10 and record['quantities']['equilibration_time']['unit'] == 'h' and record['facts']['protein_retained']['answer'] == 'yes' and record['facts']['binding_detected']['answer'] == 'unknown'
    for span in record['spans'].values():       # the quotes of the real paragraphs (with their Greek micro signs) are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()


def test_the_real_dialysis_result_paragraph_gives_the_kd_and_the_binding(tmp_path):
    world = dialysis_real_result_world(tmp_path)
    run, unit = run_to_the_end(world, dialysis_passages.REAL_RESULT, dialysis_passages.real_result_answer(), 'a105-extract-dialysis-real-result')
    summary = EPISODE._summary(EPISODE(), run.view)
    assert summary['counts']['newly_stated'] >= 1
    world['store'].close()


def test_the_commission_accepts_pulldown_as_an_experiment_type_and_the_earlier_ones_still():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:14] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown')     # the earlier ones are unchanged; emsa and sec follow
    assert len(EXPERIMENT_TYPES) == 17 and EXPERIMENT_TYPES[:13] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa')


def test_the_pulldown_commission_asks_for_the_pulldown_form_and_none_of_the_others(tmp_path):
    world = pulldown_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-request-pulldown')
    request = asyncio.run(run.next_decision())
    assert request.context['experiment_type'] == 'pulldown'
    assert request.output_schema == generation_schema(literature_pulldown_extraction.answer_schema())
    for other in (answer_schema(), literature_itc_extraction.answer_schema(), literature_bli_extraction.answer_schema(), literature_gci_extraction.answer_schema(), literature_fp_extraction.answer_schema(), literature_fret_extraction.answer_schema(), literature_mst_extraction.answer_schema(), literature_trp_extraction.answer_schema(), literature_fcs_extraction.answer_schema(), literature_elisa_extraction.answer_schema(), literature_alpha_extraction.answer_schema(), literature_radioligand_extraction.answer_schema(), literature_spa_extraction.answer_schema()):
        assert request.output_schema != generation_schema(other)
    assert 'pull-down or co-immunoprecipitation (co-IP) experiment' in request.instructions and 'reports no binding constant' in request.instructions and 'plasmon resonance (SPR) binding' not in request.instructions
    assert 'ELISA' not in request.instructions and 'AlphaScreen' not in request.instructions and 'scintillation' not in request.instructions and 'Cheng-Prusoff' not in request.instructions
    assert 'calorimetry' not in request.instructions and 'bio-layer' not in request.instructions and 'grating' not in request.instructions and 'polarization' not in request.instructions and 'energy transfer' not in request.instructions and 'thermophoresis' not in request.instructions and 'tryptophan' not in request.instructions and 'correlation spectroscopy' not in request.instructions
    assert 'the exact quote text must appear only once in the chunk' in request.instructions
    assert 'grad' not in json.dumps(request.context).lower()
    world['store'].close()


def test_a_pulldown_answer_is_checked_by_the_pulldown_validator_and_an_spa_answer_is_refused_for_a_pulldown_commission(tmp_path):
    world = pulldown_synthetic_world(tmp_path)
    run = linked(world, 'a105-extract-pulldown-rejected')
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    answer = pulldown_passages.synthetic_answer()
    answer['fold_enrichment']['quote'] = '15-fold stronger than in the control'
    with pytest.raises(Rejected) as rejected:
        EPISODE.action(answer, summary, run.view.records, None)
    assert rejected.value.feedback['detail'].startswith('fold_enrichment:quote_is_not_in_the_chunk')
    assert run.view.units_consumed == 0 and run.view.outcomes == ()
    with pytest.raises(Exception):
        EPISODE.action(spa_passages.synthetic_answer(), summary, run.view.records, None)
    assert run.view.units_consumed == 0
    world['store'].close()


def test_the_pulldown_synthetic_passage_fills_the_pulldown_grader_and_every_criterion_is_decided(tmp_path):
    world = pulldown_synthetic_world(tmp_path)
    run, unit = run_to_the_end(world, pulldown_passages.SYNTHETIC, pulldown_passages.synthetic_answer(), 'a105-extract-pulldown-synthetic')
    outcome = unit['outcome']
    records = run.view.records
    record = json.loads(records.get_artifact(outcome['record_ref']))
    assert record['experiment_type'] == 'pulldown'
    assert record['experiment_ref'].startswith('pulldown:') and record['assertion_ref'] == world['proposed']
    start = int(record['spans'][record['quantities']['fold_enrichment']['source_refs'][0]]['locator'].split()[1].split('-')[0])
    assert world['store'].get_artifact(world['artifact'])[start:start + 36] == b'12-fold stronger than in the control'
    for span in record['spans'].values():       # the multi-byte quotes (degree and micro signs) are at their byte spans in the stored text
        first, last = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[first:last].decode() == span['quote']
    summary = EPISODE._summary(EPISODE(), run.view)
    assert 1 <= summary['counts']['newly_stated'] <= summary['counts']['asked']
    assert EPISODE.credit(summary, records) == summary['counts']['newly_stated'] / summary['counts']['asked']
    result = asyncio.run(run.run())['result'].as_record()
    assert run.journal.run_state('a105-extract-pulldown-synthetic')[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(('record_refs',)).admit(result, 'return') == result
    assert result['credit'] == result['finding']['newly_stated'] / result['finding']['asked'] and result['finding']['newly_stated'] >= 1
    again = asyncio.run(resumed(world, 'a105-extract-pulldown-synthetic', run.journal).run())['result'].as_record()
    assert again == result and not list((world['directory'] / 'model_calls_resumed').glob('call-*'))
    world['store'].close()


def test_the_real_pulldown_paragraph_states_only_what_it_states_and_decides_four_criteria(tmp_path):
    world = pulldown_real_world(tmp_path)
    run, unit = run_to_the_end(world, pulldown_passages.REAL, pulldown_passages.real_answer(), 'a105-extract-pulldown-real')
    summary = EPISODE._summary(EPISODE(), run.view)
    print('COUNTS', summary['counts'])
    assert summary['counts']['newly_stated'] >= 1
    record = json.loads(run.view.records.get_artifact(unit['outcome']['record_ref']))
    assert record['quantities']['fold_enrichment']['value'] is None and record['facts']['prey_detected_in_eluate']['answer'] == 'yes' and record['capture_format'] == 'antibody'
    assert record['facts']['interaction_survives_nuclease']['answer'] == 'yes' and record['facts']['input_lane_shown']['answer'] == 'unknown'
    for span in record['spans'].values():       # the quotes of the real paragraph are at their byte spans in the stored text
        start, end = (int(part) for part in span['locator'].split()[1].split('-'))
        assert world['store'].get_artifact(world['artifact'])[start:end].decode() == span['quote']
    world['store'].close()
