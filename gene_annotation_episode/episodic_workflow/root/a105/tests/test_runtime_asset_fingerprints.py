"""Actual current binding descriptors include required packaged reader assets."""
import hashlib
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
AXIS = __package__.rsplit('.tests', 1)[0]
HOMES = sorted(path.parent.relative_to(ROOT).as_posix() for path in ROOT.rglob('binding_record.py') if 'tests' not in path.parts)
PILOT = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'


def test_required_assets_are_actual_loader_bytes():
    module = import_module(AXIS + '.runtime_assets')
    shared = module.required_runtime_asset_fingerprints()
    complete = module.required_runtime_asset_fingerprints(include_pilot=True)
    assert set(shared) == {'library/literature_assay_grading_legacy_cells_v1.json',
        'library/retained_input_authority/bvbrc_appservice_schemas.json'}
    assert set(complete) == {*shared, PILOT + '/grading/literature_assay_grading_legacy_cells_v1.json'}
    assert complete == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in complete}


@pytest.mark.parametrize('home', HOMES)
def test_current_descriptor_consumes_actual_asset_map(home, monkeypatch):
    module = import_module(AXIS + '.' + home.replace('/', '.') + '.binding_record')
    if home == 'scientific_process':
        instance = SimpleNamespace(_library_record={'fixture': 'source'}, _tools_record={'fixture': 'tools'},
            _child_roles=(), tool_retrieval=None, _contract_information_profile=None, _yield_bindings=None)
        record = lambda: module.ScientificBindingRecord.as_record(instance)
    else:
        binding = import_module(AXIS + '.' + home.replace('/', '.') + '.episode').LiteratureEpisode(object())
        record = binding.as_record
    original = module.required_runtime_asset_fingerprints
    selected = original(include_pilot=home in ('scientific_process', PILOT))
    before = record()
    for asset in selected:
        calls = []
        def changed(*, include_pilot=False):
            calls.append(include_pilot)
            values = original(include_pilot=include_pilot)
            values[asset] = '0' * 64 if values[asset] != '0' * 64 else '1' * 64
            return values
        with monkeypatch.context() as local:
            local.setattr(module, 'required_runtime_asset_fingerprints', changed)
            after = record()
        assert calls == [home in ('scientific_process', PILOT)]
        assert after['implementation_sha256'] != before['implementation_sha256']
        assert {k:v for k,v in after.items() if k != 'implementation_sha256'} == {k:v for k,v in before.items() if k != 'implementation_sha256'}
    assert record() == before
