"""Replay actual retained tool output; fresh execution is tested separately."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import a102_native_worker as worker
from gene_annotation_episode.a102_scoring import grade_comparison

FIXTURE=Path(__file__).with_name('fixtures')/'a102/native'


def test_actual_usalign_output_joins_original_native_map_and_transform(tmp_path,monkeypatch):
    request=json.loads((FIXTURE/'tpi_inputs.json').read_text())
    request['software']=request['usalign_software'];request['executable']=request['software']['path']
    request.update(reference=request['references'][0]['binding'],
        reference_binding_ref=request['references'][0]['binding_ref'],comparison_group='retained-TPI',variant_ref='retained-USalign')
    def retained(command,directory,name):
        (directory/'transform.txt').write_bytes((FIXTURE/'usalign_tpi.transform').read_bytes())
        return (FIXTURE/'usalign_tpi.stdout').read_text()
    monkeypatch.setattr(worker,'_run',retained)
    native=worker.usalign(request,tmp_path)['comparisons'][0]
    grade=grade_comparison(native)
    assert grade['components']['n_pairs']==246
    assert grade['components']['rmsd_A']==pytest.approx(1.4758433323)
    assert grade['components']['B']==pytest.approx(.6345494784)


def test_actual_foldseek_output_is_credited_without_followup_despite_rounded_reverse_transform(tmp_path,monkeypatch):
    request=json.loads((FIXTURE/'tpi_inputs.json').read_text());calls=[]
    def retained(command,directory,name):
        calls.append(name)
        if name=='foldseek-version':return request['software']['version']+'\n'
        (directory/'hits.tsv').write_bytes((FIXTURE/'foldseek_tpi.tsv').read_bytes())
        return ''
    monkeypatch.setattr(worker,'_run',retained)
    result=worker.foldseek(request,tmp_path)
    assert not result['leads'] and len(result['comparisons'])==1
    assert calls==['foldseek-version','foldseek']
    grade=grade_comparison(result['comparisons'][0]);components=grade['components']
    assert components['B']==pytest.approx(.6351024940)
    assert components['n_pairs']==246
    assert not grade['native_metrics']['reported_rmsd_reproduces_retained_transform']
    assert components['B_rounding_interval'][0]<components['B']<components['B_rounding_interval'][1]
