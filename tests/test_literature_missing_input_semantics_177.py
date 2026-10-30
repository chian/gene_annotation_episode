"""Synthetic prospective input semantics and authentic pre-change v1 custody.

The retained v1 stores were produced by real selected writers before the change;
tests never relabel a prospective result as historical output.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from gene_annotation_episode import literature_transport_calculations as transport
from gene_annotation_episode import literature_binding_models as binding
from gene_annotation_episode.literature_transport_storage import LiteratureTransportRepository, transport_response_cells_schema
from gene_annotation_episode.literature_binding_model_storage import LiteratureBindingModelRepository, binding_model_cells_schema
from test_literature_transport_calculations import example
from test_literature_binding_models import sheet, model
from test_literature_transport_storage import fixture as transport_fixture
from test_literature_binding_model_storage import fixture as binding_fixture

HERE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001/a105_missing_input_semantics_177'
LEGACY = json.loads((HERE / 'LEGACY_RECEIPT_001.json').read_text())

def baseline(name):
    spec = importlib.util.spec_from_file_location('gene_annotation_episode._baseline177_' + name,
                                                HERE / 'baseline' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.mark.parametrize('primitive', transport.PRIMITIVE_ORDER)
def test_partial_concentrations_establish_only_missing_input(primitive):
    inputs = example()
    inputs['values'][primitive] = None
    # A supplied covariance cannot describe an absent operand.
    inputs['covariance'] = None
    result = transport.populate_transport_response(inputs)
    name = 'apparent_km' if primitive == 'km' else primitive
    assert result['cells'][name]['unavailable_reason'] == 'concentration_not_supplied'
    assert result['cells']['condition_response']['unavailable_reason'] == 'concentration_inputs_not_supplied'
    for other in transport.PRIMITIVE_ORDER:
        if other != primitive:
            native = 'apparent_km' if other == 'km' else other
            assert result['cells'][native]['value'] == inputs['values'][other]

@pytest.mark.parametrize('field,key,reason,component', [
    ('curve_keys', 'km', 'kinetic_curve_identity_not_supplied', 'condition_response'),
    ('measurement_keys', 'km', 'primitive_measurement_identity_not_supplied', 'condition_response_variance'),
    ('covariance', None, 'primitive_covariance_not_supplied', 'condition_response_variance'),
])
def test_distinct_missing_transport_inputs(field, key, reason, component):
    inputs = example()
    if key is None:
        inputs[field] = None
    else:
        inputs[field][key] = None
    result = transport.populate_transport_response(inputs)
    assert result['cells'][component]['unavailable_reason'] == reason
    assert result['cells']['apparent_km']['value'] == 12

def test_available_transport_math_and_uncertainty_exactly_match_original_code():
    old = baseline('literature_transport_calculations')
    for variance in ('known', 'estimated', 'unknown'):
        inputs = example()
        inputs['variance_status'] = variance
        before, after = old.populate_transport_response(inputs), transport.populate_transport_response(inputs)
        assert before.pop('version') == 'a105_transport_response_v1'
        assert after.pop('version') == 'a105_transport_response_v2'
        assert before == after
    assert transport.populate_transport_response(example())['cells']['condition_response']['value'] == .55

@pytest.mark.parametrize('status', ['known', 'estimated', 'unknown'])
def test_supplied_binding_model_math_and_uncertainty_exactly_match_original_code(status):
    source = sheet()
    declaration = model(source, variance_status=status)
    before = baseline('literature_binding_models').populate_binding_model(source, declaration)
    after = binding.populate_binding_model(source, declaration)
    assert before.pop('version') == 'binding_model_sheet_v1'
    assert after.pop('version') == 'binding_model_sheet_v2'
    assert before == after

def test_absent_binding_model_retains_native_contrast_without_publication_claim():
    source = sheet(100, 200)
    result = binding.populate_binding_model(source, None)
    old = baseline('literature_binding_models').populate_binding_model(source, None)
    assert result['cells']['log_parameter_contrast'] == old['cells']['log_parameter_contrast']
    assert result['model'] is None
    assert all(cell['unavailable_reason'] == 'binding_sampling_model_not_supplied'
               for name, cell in result['cells'].items() if name != 'log_parameter_contrast')
    assert source['cells']['native_parameter_ratio']['value'] == 2

@pytest.mark.parametrize('kind', ['transport', 'binding'])
def test_new_selected_writer_publishes_v2_and_new_typed_missing_labels(tmp_path, kind):
    if kind == 'transport':
        store, context, args, _ = transport_fixture(tmp_path, km=False)
        cls, schema = LiteratureTransportRepository, transport_response_cells_schema
    else:
        store, context, args, _ = binding_fixture(tmp_path, model=False)
        cls, schema = LiteratureBindingModelRepository, binding_model_cells_schema
    with store:
        repo = cls(store, context.run_id)
        outcome = repo.populate(context, args, 'new-v2-selected')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        assert saved['version'] == repo.record_version
        assert saved['version'].endswith('_v2')
        rows = repo.project_cells([ref], permitted_record_refs=[ref])
        validate_schema(rows, schema())
        missing = [row for row in rows if row['unavailable_reason']]
        assert missing and all(row['unavailable_reason'].endswith('_not_supplied') for row in missing)
        if kind == 'binding':
            assert all(row['model_kind'] == 'not_supplied' for row in rows)
        assert repo.populate(context, args, 'new-v2-selected') == outcome
        assert not store.list('observation')

def forbid(*_args, **_kwargs):
    raise AssertionError('saved v1 projection must not read scientific inputs or recalculate')

def open_readonly(path):
    # A complete checkpoint and closed original writer precede immutable mode.
    assert not Path(str(path / 'state.sqlite3') + '-wal').exists()
    store = Store.__new__(Store)
    store.path = path
    store._savepoint = 0
    store.db = sqlite3.connect(f'file:{path / "state.sqlite3"}?mode=ro&immutable=1', uri=True)
    store.db.row_factory = sqlite3.Row
    store.db.execute('PRAGMA query_only=ON')
    return store

@pytest.mark.parametrize('name', sorted(LEGACY))
def test_authentic_v1_exact_readonly_projection_forms_and_scoped_facts(name, monkeypatch):
    item = LEGACY[name]
    cls = LiteratureTransportRepository if item['kind'] == 'transport' else LiteratureBindingModelRepository
    schema = transport_response_cells_schema if item['kind'] == 'transport' else binding_model_cells_schema
    path = HERE / 'legacy' / name
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
    # Block before constructing the repository, including upstream calculators.
    for module, names in {
        'literature_transport_storage': ('read_transport_inputs', 'populate_transport_response', '_quantity_key'),
        'literature_binding_model_storage': ('read_binding_model', 'populate_binding_model', 'binding_model_operand_keys'),
        'literature_binding_storage': ('read_binding_parameter_table', 'populate_binding_contrast'),
        'literature_activity_calculations': ('populate_corrected_activity',),
        'literature_prose_reader': ('read_jats_quantity',),
    }.items():
        for function in names:
            monkeypatch.setattr(f'gene_annotation_episode.{module}.{function}', forbid)
    with open_readonly(path) as store:
        original = store.get_artifact
        # Saved numerical/request artifacts remain readable; original scientific
        # evidence and declarations do not. No raw input can be consulted.
        allowed = {store.get(row['id'])[field] for row in store.list('source')
                   if row['origin'] == 'tool' for field in ('artifact_ref', 'request_ref')}
        def saved_only(ref):
            assert ref in allowed
            return original(ref)
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        repo = cls(store, item['run_id'])
        ref = item['outcome']['result']['sheet_ref']
        assert repo.read(ref) == item['payload']
        owner = BindingContext(**item['context'])
        assert repo.populate(owner, item['arguments'], 'original-v1-selected') == item['outcome']
        projected = repo.project_cells([ref], permitted_record_refs=[ref])
        assert projected == item['projected']
        for row_schema in (item['schema'], schema()):
            validate_schema(projected, row_schema)
            namespace = 'literature_transport_cells' if item['kind'] == 'transport' else 'literature_binding_model_cells'
            form_schema = obj({'rows': row_schema})
            form = form_with_facts({}, form_schema, {namespace: projected})
            assert validate_form(form, form_schema, lambda r, n: store.get(r)['record_type'] == n) == form
        receiver = BindingContext(**item['receiver'])
        assert repo.received_cells(receiver) == item['received_subset']
        assert repo.fact_cells(receiver, [ref], components=repo.components) == item['received_subset']
        with pytest.raises(ContractError, match='not_received'):
            repo.project_cells([ref], permitted_record_refs=[])
        altered = deepcopy(projected[:1])
        altered[0]['value'] = 999
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_returned_values(altered, permitted_record_refs=[ref])
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            store.db.execute('DELETE FROM records')
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}

@pytest.mark.parametrize('name', ['transport_missing', 'binding_missing'])
@pytest.mark.parametrize('bad', ['version', 'artifact'])
def test_authentic_v1_rejects_bad_record_version_or_mutated_artifact(tmp_path, name, bad):
    item = LEGACY[name]
    path = tmp_path / name
    shutil.copytree(HERE / 'legacy' / name, path)
    with Store(path) as store:
        cls = LiteratureTransportRepository if item['kind'] == 'transport' else LiteratureBindingModelRepository
        repo = cls(store, item['run_id'])
        ref = item['outcome']['result']['sheet_ref']
        source = store.get(ref)
        if bad == 'version':
            # Deliberate corruption copy only: not a fabricated legacy fixture.
            row = json.loads(store.db.execute('SELECT data FROM records WHERE id=?', (ref,)).fetchone()[0])
            row['version'] = 'unsupported_v999'
            store.db.execute('UPDATE records SET data=? WHERE id=?', (json.dumps(row), ref))
            reason = 'version_mismatch'
        else:
            digest = source['artifact_ref'].removeprefix('artifact_')
            artifact_path = path / 'artifacts' / digest[:2] / digest
            artifact_path.write_bytes(artifact_path.read_bytes() + b' ')
            reason = 'artifact_digest_mismatch'
        with pytest.raises(ContractError, match=reason):
            repo.read(ref)
