"""Constructed unavailable joint scopes; no fabricated numerical alternatives."""
from copy import deepcopy as cp
from dataclasses import replace
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence import literature_controlled_response_storage as storage
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_controlled_response_local_calculations as local
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_controlled_response_storage_v3 import native_case, owned
from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence.tests.test_literature_controlled_response_render_v3 import text_for

def forbidden(*a, **k):
    raise AssertionError('numerical population must not run during projection')

@pytest.mark.parametrize('field,value', [('admissibility', 'unknown'), ('admissibility', 'conflicting'), ('normalization', 'unknown'), ('calibration', 'conflicting'), ('revision', 'conflicting')])
def test_unavailable_original_joint_index_map_and_independent_readings(tmp_path, monkeypatch, field, value):

    def modify(f):
        if field == 'admissibility':
            f.args['joint_reading_assignments'][0]['admissibility'] = {'value': value, 'witnesses': [] if value == 'unknown' else [f.witness('nmol/min'), f.witness('Physical A.')]}
        else:
            f.args['joint_scopes'][0][field] = {'value': value, 'witnesses': [] if value == 'unknown' else [f.witness('nmol/min'), f.witness('Physical A.')]}
    store, context, args, _ = native_case(tmp_path, companion=True, joints=True, modify=modify)
    try:
        repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        outcome = repo.populate_v3(context, args, 'unavailable')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        assert [r['scope_index'] for r in saved['population']['alternatives']] == [1]
        original = saved['extraction']['joint_scope_extractions'][0]
        assert original['effective_admissibility'] == value
        conditional = [r for r in outcome['result']['cells'] if r['kind'] == 'conditional']
        assert [r['component_key'] for r in conditional[:12]] == ['joint:0:' + c for c in storage.arithmetic.COMPONENTS]
        assert all((r['component_key'].startswith('joint:1:') for r in conditional[12:]))
        for row in conditional[:12]:
            assert row['reading_assignment'] == args['joint_reading_assignments'][0]['assignment']
            cell = row['cell']
            assert [cell[k] for k in ('value', 'lower', 'upper', 'unit', 'origin')] == [None] * 5
            assert cell['status'] == 'unavailable' and cell['unavailable_reason'] == [value + '_joint_applicability']
            assert row['native_reading'] is None and row['reported_uncertainty'] is None
            deps = row['dependencies']
            assert all((deps[k] == [] for k in ('numeric_readings', 'numeric_fields', 'uncertainty_readings', 'model_readings', 'covariance_owner_ids', 'source_variable_indices')))
            assert deps['covariance_index'] is None and (not deps['full_source_covariance_required'])
            assert row['context']['variance_status'] == 'unknown' and row['context']['model_kind'] == 'none'
        expected = {r['component']: r['cell'] for r in saved['population']['conditional_components']}
        assert all((r['cell'] == expected[r['component']] for r in conditional[12:]))
        assert outcome['result']['cells'][0]['cell']['value'] is not None
        assert next((r for r in outcome['result']['cells'] if r['kind'] == 'local_difference'))['cell']['value'] is not None
        monkeypatch.setattr(storage.population, 'populate_controlled_response_v3', forbidden)
        monkeypatch.setattr(local, 'populate_controlled_response_local', forbidden)
        monkeypatch.setattr(owner, 'populate_controlled_response_owner', forbidden)
        assert storage._component_rows(saved['extraction'], saved['population'], ref) == outcome['result']['cells']
        assert repo.read(ref) == saved
    finally:
        store.close()

