"""Fresh-process saved-form reconstruction with both receive methods forbidden."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
index = int(sys.argv[1])
if index not in (0, 1, 2):
    raise ValueError('case_index_required')
case = ROOT/'verification/a105_worksheet_integration_271/attempt_002/pytest'/f'test_selected_worksheet_links_{index}'
state = case/'state'
before = {str(p.relative_to(state)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in state.rglob('*') if p.is_file()}
form = json.loads((case/'ORIGINAL_FORM_271.json').read_text())
schema = json.loads((case/'ORIGINAL_SCHEMA_271.json').read_text())
descriptor = json.loads((case/'ORIGINAL_DESCRIPTOR_271.json').read_text())

import pytest
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.runtime import _references_in
from gene_annotation_episode import literature_kinetic_storage as native
from gene_annotation_episode import literature_a105_worksheet as worksheet
from test_literature_compiled_assay_185 import readonly
from test_literature_kinetic_summary_precision_binding_251 import block_science, forbid

with pytest.MonkeyPatch.context() as patch:
    block_science(patch)
    patch.setattr(native, 'read_kinetic_inputs', forbid)
    patch.setattr(native, 'populate_kinetic_contrast', forbid)
    for name in ('receive_cells', 'populate'):
        patch.setattr(native.LiteratureKineticRepository, name, forbid)
    for name in ('a105_worksheet_template', '_schema', 'import_module'):
        patch.setattr(worksheet, name, forbid)
    with readonly(state) as store:
        store.db.create_function('library_scope_record', 2, store._scope_filter_record)
        report = store.db.execute('SELECT * FROM runtime_report_attempts WHERE failure IS NULL ORDER BY rowid DESC LIMIT 1').fetchone()
        child = store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (report['run_id'], report['child_episode_id'])).fetchone()
        request = json.loads(child['request'])
        scope = request['message']['scope']
        references = _references_in({}, store.get, forms=[(form, schema)],
            reference_subset=lambda refs: store.reference_subset(refs, scope))
        sources = list(dict.fromkeys(row['evidence_source_ref']
            for field in ('native_parameter', 'precision') for row in form[field]))
        context = BindingContext(report['run_id'], report['child_episode_id'], 'literature',
            tuple(map(tuple, json.loads(child['path']))), scope,
            request['message']['episode_assignment'], request, tuple(references))
        receiver = BindingContext(report['run_id'], report['parent_episode_id'], 'annotation',
            (('annotation', report['parent_episode_id']),), scope, {}, {}, tuple(references))
        allowed = {store.get(row['sheet_ref'])[key]
            for field in ('native_parameter', 'precision') for row in form[field]
            for key in ('artifact_ref', 'request_ref')}
        get_artifact = store.get_artifact
        def receipt_only(reference):
            if reference not in allowed:
                raise AssertionError('source_acquisition_forbidden')
            return get_artifact(reference)
        patch.setattr(store, 'get_artifact', receipt_only)
        host = SimpleNamespace(store=store, run_id=report['run_id'], tools=None)
        restored = compose_episode_bindings(WorkflowServices(host), store=store,
            journal=SimpleNamespace(store=store, run_id=report['run_id']), execution_backend=None,
            descriptors=descriptor, job_episodes=None, resource_estimator=None, role_credit_bindings={})
        host.episode_bindings = EpisodeBindingRegistry(restored.bindings)
        binding, = restored.bindings
        assert binding.as_record() == descriptor[0]
        facts = binding.received_report_facts(receiver)
        assert facts[worksheet.NATIVE] == form['native_parameter']
        assert facts[worksheet.SUMMARY] == form['precision']
        validate_form(form, schema, lambda ref, namespace: binding.resolve(context, ref, namespace))
        binding.validate_received_report(context, form, schema)
        assert store.db.total_changes == 0
assert before == {str(p.relative_to(state)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in state.rglob('*') if p.is_file()}
result = {'case': index, 'status': 'passed', 'fresh_python_process': True,
    'native_and_summary_receive_and_populate_forbidden': True,
    'source_artifacts_scientific_readers_calculators_and_new_worksheet_factories_forbidden': True,
    'legacy_native_immutable_metadata_formatting_allowed': ['_bindings', 'project_cells', 'native structural type grammar'],
    'original_form_schema_descriptor_reused': True, 'state_unchanged': True,
    'actual_model_science': False}
output = ROOT/'verification/a105_worksheet_integration_271'/f'FIRST_COLD_RECEIVERS_BLOCKED_003_{index}.json'
with output.open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
