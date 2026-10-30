"""Fresh-process first read of a controlled selected run, with scientific IO blocked."""
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
from gene_annotation_episode.communication import validate_form, _compiled_schema_content
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_measurement_comparison_storage import NAMESPACE, LiteratureMeasurementComparisonRepository

CASE = Path(sys.argv[1]).resolve()
form = json.loads((CASE/'ORIGINAL_FORM_268.json').read_text())
schema = json.loads((CASE/'ORIGINAL_SCHEMA_268.json').read_text())
descriptors = json.loads((CASE/'ORIGINAL_DESCRIPTOR_268.json').read_text())
context_data = json.loads((CASE/'ORIGINAL_RECEIVER_268.json').read_text())
allowed = set(json.loads((CASE/'ORIGINAL_ARTIFACTS_268.json').read_text()))
before = {str(p.relative_to(CASE/'state')): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (CASE/'state').rglob('*') if p.is_file()}
patch = pytest.MonkeyPatch()
block_science(patch)
_compiled_schema_content.cache_clear()
context = BindingContext(**context_data, received_record_refs=tuple(
    LiteratureMeasurementComparisonRepository.cell_record_refs(form['numbers'])))
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
    assert binding.received_report_facts(context)[NAMESPACE] == form['numbers']
    validate_form(form, schema, lambda reference, namespace: True)
    assert store.db.total_changes == 0
after = {str(p.relative_to(CASE/'state')): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (CASE/'state').rglob('*') if p.is_file()}
assert before == after
record = {'pid': os.getpid(), 'fresh_process': True, 'requested_rows': len(form['numbers']),
    'scientific_factories_readers_calculators_projection_model_writes_blocked': True,
    'only_original_two_receipt_artifacts_read': set(reads) == allowed,
    'state_byte_hashes_unchanged': before == after, 'sqlite_changes': 0,
    'scope': 'Controlled selected execution followed by fresh-process cold reconstruction; no configured-model claim.'}
(CASE/'FRESH_COLD_PROCESS_268.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record))
