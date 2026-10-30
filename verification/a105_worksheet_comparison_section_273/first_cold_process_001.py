"""First saved reconstruction occurs here, in a new process with science blocked."""
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from test_literature_measurement_comparison_binding_268 import block_science, forbid
from test_literature_compiled_assay_185 import readonly
from test_literature_a105_worksheet import render_text
from gene_annotation_episode import literature_a105_worksheet as worksheet
from gene_annotation_episode.communication import validate_form, _compiled_schema_content
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_measurement_comparison_storage import NAMESPACE, LiteratureMeasurementComparisonRepository

CASE = Path(sys.argv[1]).resolve()
def load(name):
    return json.loads((CASE/name).read_text())
form = load('ORIGINAL_FORM_273.json')
schema = load('ORIGINAL_SCHEMA_273.json')
assignment = load('ORIGINAL_ASSIGNMENT_273.json')
descriptors = load('ORIGINAL_DESCRIPTOR_273.json')
context_data = load('ORIGINAL_RECEIVER_273.json')
allowed = set(load('ORIGINAL_ARTIFACTS_273.json'))
before = {str(p.relative_to(CASE/'state')): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (CASE/'state').rglob('*') if p.is_file()}
patch = pytest.MonkeyPatch()
block_science(patch)
for name in ('_schema', '_components', 'a105_worksheet_template', 'import_module'):
    patch.setattr(worksheet, name, forbid)
_compiled_schema_content.cache_clear()
context = BindingContext(**context_data, received_record_refs=tuple(
    LiteratureMeasurementComparisonRepository.cell_record_refs(form['comparison'])))
with readonly(CASE/'state') as store:
    get = store.get_artifact
    reads = []
    def saved_only(ref):
        assert ref in allowed, 'Original scientific bytes forbidden'
        reads.append(ref)
        return get(ref)
    patch.setattr(store, 'get_artifact', saved_only)
    for name in ('artifact', 'put', 'create_problem'):
        patch.setattr(store, name, forbid)
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=None)
    restored = compose_episode_bindings(WorkflowServices(host), store=store,
        journal=SimpleNamespace(store=store, run_id=context.run_id), execution_backend=None,
        descriptors=descriptors, job_episodes=None, resource_estimator=None, role_credit_bindings={})
    host.episode_bindings = EpisodeBindingRegistry(restored.bindings)
    binding, = restored.bindings
    assert binding.as_record() == descriptors[0]
    assert binding.received_report_facts(context)[NAMESPACE] == form['comparison']
    validate_form(form, schema, lambda reference, namespace: True)
    worksheet.validate_a105_worksheet_links(form, schema, assignment,
        read_public_record=lambda *_: pytest.fail('empty context needs no public records'))
    rendered = render_text(form, {})
    assert 'A105 experimental evidence worksheet' in rendered and 'Source comparison scope' in rendered
    assert store.db.total_changes == 0
after = {str(p.relative_to(CASE/'state')): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (CASE/'state').rglob('*') if p.is_file()}
assert before == after
assert set(reads) == allowed
record = {'pid': os.getpid(), 'fresh_process': True, 'requested_rows': len(form['comparison']),
    'scientific_factories_readers_calculators_projection_model_receive_writes_blocked': True,
    'worksheet_constructor_and_current_native_factories_blocked': True,
    'original_descriptor_equal': binding.as_record() == descriptors[0],
    'original_rows_scope_order_and_conditional_qualifications_equal': True,
    'only_original_two_receipt_artifacts_read': set(reads) == allowed,
    'state_byte_hashes_unchanged': before == after, 'sqlite_changes': 0,
    'scope': 'Mechanical reuse of already root-converted source; controlled selected execution, no configured-model claim.'}
(CASE/'FIRST_COLD_PROOF_273.json').write_text(json.dumps(record, indent=2)+'\n')
(CASE/'FIRST_COLD_RENDER_273.txt').write_text(rendered)
imports = []
for name, module in sorted(sys.modules.items()):
    path = getattr(module, '__file__', None)
    if path:
        path = Path(path).resolve()
        if path.is_file() and path.is_relative_to(ROOT) and path.relative_to(ROOT).parts[0] in ('gene_annotation_episode', 'method_loop', 'tests'):
            imports.append({'module': name, 'path': str(path.relative_to(ROOT)),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
(CASE/'FIRST_COLD_LOCAL_IMPORTS_273.json').write_text(json.dumps(imports, indent=2)+'\n')
print(json.dumps(record))
