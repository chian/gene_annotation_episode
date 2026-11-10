"""Replay the scientific adapter after a real authenticated HPC boundary.

The retained Aurora record is input data, not another execution or proof of a
fresh workflow. Publication is intercepted to examine exactly what is admitted.
"""
import base64
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import zlib

import pytest

from gene_annotation_episode import component_axis_native_hpc as native
from gene_annotation_episode.domain import ContractError


@pytest.fixture
def recorded():
    return json.loads((Path(__file__).parent / 'fixtures' /
        'component_hpc_admission' / 'a110-terminal-plan-result.json').read_text())


def admit_record(recorded, monkeypatch):
    expected, authority = recorded['expected'], recorded['authority']
    monkeypatch.setattr(native, 'publish', lambda store, provider, body: (provider, body))
    context = SimpleNamespace(run_id=expected['run_id'], scope=expected['scope'])
    return native.admit(SimpleNamespace(store=object()), expected,
        authority['source_ref'], context=context, known=set(expected['evidence_refs']),
        reader=lambda context, reference: authority)


@pytest.mark.parametrize('plan_format', ['current_contract', 'historical_contract'])
def test_recorded_native_result_preserves_components(recorded, monkeypatch, plan_format):
    if plan_format == 'historical_contract':
        plan = recorded['authority']['plan']
        plan['files_to_stage'] = plan.pop('supplied_files')
    provider, admitted = admit_record(recorded, monkeypatch)
    document = recorded['authority']['receipt']['document']
    original = json.loads(zlib.decompress(base64.b64decode(document['payload'])))
    assert provider == native.RESULT_PROVIDER
    assert admitted['status'] == 'scientifically_admitted'
    assert admitted['native_components'] == original
    assert admitted['pbs_job_id'] == recorded['provenance']['pbs_job_id']
    assert admitted['scientific_credit'] is None
    assert admitted['dependencies']['independence'] == (
        'not_inferred_from_distinct_sources_or_missing_dataset_identity')


@pytest.mark.parametrize('defect', ['missing_inputs', 'conflicting_formats', 'changed_text'])
def test_plan_input_custody_is_required(recorded, monkeypatch, defect):
    plan = recorded['authority']['plan']
    if defect == 'missing_inputs':
        del plan['supplied_files']
    elif defect == 'conflicting_formats':
        plan['files_to_stage'] = deepcopy(plan['supplied_files'])
        plan['files_to_stage'][0]['path'] += '.different'
    else:
        plan['supplied_files'][0]['text'] += '\nchanged recorded bytes\n'
    with pytest.raises(ContractError, match='hpc_scientific_original_plan_files_'):
        admit_record(recorded, monkeypatch)
