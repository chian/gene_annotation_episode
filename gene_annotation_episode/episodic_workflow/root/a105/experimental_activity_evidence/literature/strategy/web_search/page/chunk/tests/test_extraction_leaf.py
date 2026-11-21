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


def run_to_the_end(world, chunk, answer, run_id):
    run = linked(world, run_id)
    asyncio.run(run.next_decision())
    summary = EPISODE._summary(EPISODE(), run.view)
    assert summary['chunk'] == chunk
    call = EPISODE.action(answer, summary, run.view.records, None)
    assert isinstance(call, ToolCall) and call.name == 'extract'
    unit = asyncio.run(run.run_unit(call))
    return run, unit


def test_the_commission_accepts_alphascreen_as_an_experiment_type_and_the_earlier_ones_still():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:11] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen')     # the earlier ones are unchanged; radioligand follows


def test_the_commission_accepts_radioligand_as_an_experiment_type():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:12] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand')     # the earlier ones are unchanged; spa follows


def test_the_commission_accepts_spa_as_an_experiment_type_and_the_earlier_ones_still():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:13] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa')     # the earlier ones are unchanged; pulldown follows


from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import spectro_direct_passages


def spectro_direct_synthetic_world(tmp_path, name='world'):
    data = spectro_direct_passages.SYNTHETIC.encode()
    return held_world(tmp_path, 'Preceding text. ' + spectro_direct_passages.SYNTHETIC + ' Following text.', 16, len(data), name=name, experiment_type='spectro_direct')


def spectro_direct_real_world(tmp_path):
    text = 'Preceding text. ' + spectro_direct_passages.REAL + ' Following text.'
    return held_world(tmp_path, text, 16, len(spectro_direct_passages.REAL.encode()), experiment_type='spectro_direct')


def test_the_commission_accepts_spectro_direct_the_first_activity_rate_type_and_the_earlier_ones_still():
    from ..messages.read_from_parent import EXPERIMENT_TYPES
    assert EXPERIMENT_TYPES[:13] == ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa')     # the earlier ones are unchanged
    assert EXPERIMENT_TYPES[-1] == 'spectro_direct' and len(EXPERIMENT_TYPES) == 26

