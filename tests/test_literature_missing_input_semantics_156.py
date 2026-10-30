"""Synthetic missing selections, exact pre-change v1 returns and cold v2 reads."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.literature_assay_storage import assay_cells_schema
from gene_annotation_episode.literature_quantity_storage import quantity_cells_schema
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from method_loop.durable import DurableExecutionError
import test_literature_assay_integration as assay
import test_literature_quantity_integration as quantity
from test_runtime import FixtureController, ScriptedProvider


BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001/a105_missing_input_semantics_156'
HELPERS = {'assay': assay, 'quantity': quantity}


def context_record(context):
    return {**context.as_record(), 'received_record_refs': list(context.received_record_refs)}


def forbid(*args, **kwargs):
    raise AssertionError('saved return must not reacquire, parse or calculate')


@pytest.mark.parametrize('kind', HELPERS)
def test_exact_prechange_v1_replay_projection_original_schema_and_admission(tmp_path, monkeypatch, kind):
    """The fixtures were actually populated before this repair, not relabeled v2."""
    saved = json.loads((BASE / 'legacy_v1' / f'{kind}.json').read_text())
    shutil.copytree(BASE / 'legacy_v1' / kind, tmp_path / 'state')
    context, parent = BindingContext(**saved['context']), BindingContext(**saved['parent'])
    helper = HELPERS[kind]
    with Store(tmp_path / 'state') as store:
        binding = helper.binding_for(store, context)
        repository = getattr(binding.services, f'literature_{kind}_repository')()
        ref = saved['outcome']['result']['sheet_ref']
        assert saved['payload']['version'].endswith('_v1')
        assert saved['payload']['sheet']['correction']['version'] == 'a105_corrected_activity_v1'
        # Old executable descriptors are intentionally distinct from old records.
        with pytest.raises(DurableExecutionError, match='identity_conflict'):
            compose_episode_bindings(binding.services, store=store,
                journal=Journal(store, context.run_id), execution_backend=None,
                descriptors=[saved['descriptor']], job_episodes=None,
                resource_estimator=None, role_credit_bindings={})
        current = replace(context, received_record_refs=tuple(parent.received_record_refs))
        metadata = store.get(ref)
        allowed_artifacts = {metadata['artifact_ref'], metadata['request_ref']}
        original_get = store.get_artifact
        def retained_only(reference):
            assert reference in allowed_artifacts, 'scientific input bytes must not be reread'
            return original_get(reference)
        monkeypatch.setattr(store, 'get_artifact', retained_only)
        monkeypatch.setattr('gene_annotation_episode.literature_activity_calculations.populate_corrected_activity', forbid)
        monkeypatch.setattr('gene_annotation_episode.literature_assay_inputs.read_assay_inputs', forbid)
        monkeypatch.setattr('gene_annotation_episode.literature_prose_reader.read_jats_quantity', forbid)
        assert repository.populate(context, saved['arguments'], saved['operation_key']) == saved['outcome']
        assert repository.read(ref) == saved['payload']
        rows = repository.project_cells([ref], permitted_record_refs=current.received_record_refs,
            components=[row['component'] for row in saved['form']['measurements']])
        assert rows == saved['form']['measurements']
        assert any(row['unavailable_reason'] == 'correction_inputs_unreported' for row in rows)
        binding.validate_report(current, saved['form'], saved['schema'])
        current_schema = obj({'measurements': (assay_cells_schema if kind == 'assay' else quantity_cells_schema)()})
        validate_schema(saved['form'], current_schema)
        binding.received_form_references(parent, saved['form'], saved['schema'], 'new-exact-v1-admission')
        assert repository.received_cells(parent) == rows
        # Successful replay and projection also work without any database writes.
        store.db.execute('PRAGMA query_only=ON')
        assert repository.populate(context, saved['arguments'], saved['operation_key']) == saved['outcome']
        assert repository.read(ref) == saved['payload']
        assert repository.received_cells(parent) == rows


@pytest.mark.parametrize('missing,component,reason', [
    ('g', 'attributed_rate', 'correction_inputs_not_supplied'),
    ('u', 'condition_response', 'correction_inputs_not_supplied'),
    ('covariance', 'effect_variance', 'primitive_covariance_not_supplied'),
    ('residual', 'effect_variance', 'distinct_residual_variance_not_supplied'),
])
def test_selected_null_does_not_claim_omission_even_when_fixture_contains_operand(tmp_path, missing, component, reason):
    store, context, arguments = assay.setup_store(tmp_path, full=True)
    with store:
        # Full original synthetic text and covariance packet remain received.
        # Only this operation's selected operand is omitted.
        if missing in ('g', 'u'):
            arguments['primitives'][missing] = None
            arguments['covariance_source_ref'] = None
        elif missing == 'covariance':
            arguments['covariance_source_ref'] = None
        else:
            arguments['distinct_residual_variance'] = None
        context = replace(context, assignment={**plain(context.assignment),
            'requested_assay_components': [component]})
        binding = assay.binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.assay.populate', arguments, 'missing-selection'))
        assert outcome['status'] == 'completed'
        repository = binding.services.literature_assay_repository()
        ref = outcome['result']['sheet_ref']
        payload = repository.read(ref)
        assert payload['version'] == 'literature_assay_population_record_v2'
        assert payload['sheet']['correction']['version'] == 'a105_corrected_activity_v2'
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        form = form_with_facts({}, assay.FORM, binding.facts(current, {'committed_record_refs': [ref]}))
        binding.validate_report(current, form, assay.FORM)
        row, = form['measurements']
        assert row['component'] == component and row['value'] is None
        assert row['unavailable_reason'] == reason
        assert all('unreported' not in (cell['unavailable_reason'] or '') for cell in payload['sheet']['cells'].values())
        if missing in ('covariance', 'residual'):
            assert payload['sheet']['cells']['corrected_activity']['value'] == pytest.approx(.68)
        # Narrowing a v1 contract does not silently gain new meanings.
        legacy_schema = json.loads((BASE / 'legacy_v1' / 'assay.json').read_text())['schema']
        with pytest.raises(ContractError):
            validate_schema(form, legacy_schema)


@pytest.mark.parametrize('kind', HELPERS)
@pytest.mark.parametrize('payload_version,source_version', [('unrelated_v99', 'unrelated_v99'), (None, 'unrelated_v99')])
def test_only_explicit_supported_payload_versions_can_be_read(tmp_path, kind, payload_version, source_version):
    helper = HELPERS[kind]
    store, context, arguments = helper.setup_store(tmp_path, **({'full': False} if kind == 'assay' else {}))
    with store:
        binding = helper.binding_for(store, context)
        repository = getattr(binding.services, f'literature_{kind}_repository')()
        outcome = repository.populate(context, arguments, 'selected')
        original = store.get(outcome['result']['sheet_ref'])
        payload = repository.read(original['id'])
        if payload_version is not None:
            payload['version'] = payload_version
        artifact = store.artifact(canonical(payload), 'application/json')
        fields = {key: value for key, value in original.items() if key not in ('id', 'record_type', 'origin')}
        fields.update(artifact_ref=artifact, text_ref=artifact, version=source_version)
        altered = store.put('source', fields, origin='tool', scope=plain(context.scope))
        outcome['result']['sheet_ref'] = altered['id']
        repository.store.db.execute(f'UPDATE {repository.operations_table} SET outcome=?', (canonical(outcome),))
        with pytest.raises(ContractError, match='version_mismatch'):
            repository.read(altered['id'])


@pytest.mark.parametrize('kind', HELPERS)
def test_fresh_v2_selected_operation_typed_subset_and_cold_descriptor_reconstruction(tmp_path, kind):
    helper = HELPERS[kind]
    state = tmp_path / 'state'
    store, context, arguments = helper.setup_store(state, **({'full': False} if kind == 'assay' else {}))
    with store:
        binding = helper.binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, f'literature.{kind}.populate', arguments, 'selected-v2'))
        assert outcome['status'] == 'completed'
        ref = outcome['result']['sheet_ref']
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        form = form_with_facts({}, helper.FORM, binding.facts(current, {'committed_record_refs': [ref]}))
        binding.validate_report(current, form, helper.FORM)
        assert any(row['unavailable_reason'] == 'correction_inputs_not_supplied' for row in form['measurements'])
        parent = replace(current, role='annotation', episode_id='parent', path=(('annotation', 'root'),), assignment={})
        binding.received_form_references(parent, form, helper.FORM, 'v2-delivery')
        repository = getattr(binding.services, f'literature_{kind}_repository')()
        data = {'kind': kind, 'context': context_record(context), 'parent': context_record(parent),
            'arguments': arguments, 'operation_key': 'selected-v2', 'outcome': outcome,
            'form': form, 'schema': helper.FORM, 'descriptor': binding.as_record(), 'payload': repository.read(ref)}
        assert data['payload']['version'].endswith('_v2')
        assert data['payload']['sheet']['correction']['version'] == 'a105_corrected_activity_v2'
        manifest = tmp_path / 'manifest.json'
        manifest.write_text(json.dumps(data))
    result = subprocess.run([sys.executable, str(BASE / 'cold_reconstruct.py'), str(state), str(manifest)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {'kind': kind, 'version': data['payload']['version'],
        'exact_admitted_cells': len(form['measurements']), 'source_reads': 0, 'calculations': 0}


def test_synthetic_quantity_shared_loop_returns_missing_input_meaning_without_extra_observations(tmp_path):
    store, context, arguments = quantity.setup_store(tmp_path / 'state')
    with store:
        seen, controllers = [], []
        child = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Extract the synthetic reported quantity',
            'scope': plain(context.scope), 'purpose': 'Preserve reported activity and unavailable correction',
            'schema_json': json.dumps(quantity.FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        selected = {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate',
            'arguments': arguments}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            seen.append(form)
            assert [row['value'] for row in form['measurements']] == [12, 2/12, None]
            assert form['measurements'][-1]['unavailable_reason'] == 'correction_inputs_not_supplied'
            commit = {name: [] for name in store.reasoning_schema()['required']}
            source = store.get(arguments['source_ref'])
            start = quantity.SYNTHETIC.index('Protein P')
            commit['source_subjects'] = [{'alias': 'synthetic_subject', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': 'Protein P', 'anchor': {
                    'source_ref': source['id'], 'artifact_ref': source['artifact_ref'],
                    'start': start, 'end': start + len('Protein P'), 'quote': 'Protein P'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([child, selected, receive]), run_dir=tmp_path / 'run',
            controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[arguments['source_ref']],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(seen) == 1
        assert [value.scores for value in controllers] == [[0, 0], [0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_quantity_operations').fetchone()[0] == 1
        assert json.loads(store.db.execute('SELECT cells FROM literature_quantity_received').fetchone()[0]) == seen[0]['measurements']
        assert not store.list('observation') and not store.list('assessment')
