"""A106-owned synchronous updates of saved intervention-sheet dependencies.

A scientific population owns its interpretation and calculation.  This module
only retains the calculation's existing input bindings, follows an input's
current version and reruns dependent calculations.  It never creates a decision
or a credit event and never acquires an unreturned child component.
"""
from copy import deepcopy
from dataclasses import replace
from functools import wraps
from importlib import import_module
import inspect
import json

from gene_annotation_episode.episodic_workflow.root.a106.communication import plain
from gene_annotation_episode.episodic_workflow.root.a106.domain import ContractError, canonical, identity
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_sheet_policy

VERSION = 'literature_sheet_dependencies_v1'
TABLE = 'literature_sheet_dependencies'
CURRENT = 'literature_current_scoring_sheets'


def _policy_for(provider):
    """Resolve the A106 scientific use policy."""
    return literature_sheet_policy if provider.startswith('literature.a106.') else None


def _supported(repository):
    return repository.provider.startswith((
        'literature.a105.rate_population', 'literature.a106.', 'literature.experimental.'))


def _installed(store):
    return store.db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (TABLE,)).fetchone() is not None


def _install(store):
    store.db.execute(f'''CREATE TABLE IF NOT EXISTS {TABLE}(
        run_id TEXT NOT NULL, episode_id TEXT NOT NULL, sheet_ref TEXT NOT NULL,
        family TEXT NOT NULL, provider TEXT NOT NULL, adapter TEXT NOT NULL,
        method TEXT NOT NULL, arguments TEXT NOT NULL, assignment TEXT NOT NULL,
        possessed TEXT NOT NULL, dependencies TEXT NOT NULL, receipt TEXT NOT NULL,
        PRIMARY KEY(run_id,episode_id,sheet_ref))''')
    store.db.execute(f'''CREATE TABLE IF NOT EXISTS {CURRENT}(
        run_id TEXT NOT NULL, episode_id TEXT NOT NULL, family TEXT NOT NULL,
        sheet_ref TEXT, status TEXT NOT NULL, detail TEXT,
        PRIMARY KEY(run_id,episode_id,family))''')


def _refs(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'sheet_ref' and isinstance(child, str):
                yield child
            else:
                yield from _refs(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _refs(child)


def _replace_refs(value, replacements):
    if isinstance(value, dict):
        return {key: _replace_refs(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_refs(child, replacements) for child in value]
    return replacements.get(value, value) if isinstance(value, str) else value


def _measurement_keys(value):
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'measurement_keys', 'physical_estimate_keys'} and isinstance(child, list):
                found.update(item for item in child if isinstance(item, str))
            elif key in {'measurement_key', 'physical_measurement_key', 'physical_estimate_key', 'estimate_key'} and isinstance(child, str):
                found.add(child)
            else:
                found.update(_measurement_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_measurement_keys(child))
    return sorted(found)


def _family(repository, arguments, saved, dependency_families):
    provider = repository.provider
    policy = _policy_for(provider)
    use = (policy.family_use(provider, arguments, saved, dependency_families,
        _measurement_keys, _replace_refs) if policy is not None else None)
    if use is None:
        # Unrelated source selections follow only their registered input family.
        use = _replace_refs(arguments, dependency_families)
    return identity('literature_scientific_sheet_use', {'provider': provider, 'use': use})


def _rows(store, context):
    if not _installed(store):
        return []
    return [dict(row) for row in store.db.execute(f'SELECT d.rowid,d.*, '
        f'c.sheet_ref AS current_ref,c.status AS current_status,c.detail AS current_detail '
        f'FROM {TABLE} d LEFT JOIN {CURRENT} c USING(run_id,episode_id,family) '
        'WHERE d.run_id=? AND d.episode_id=? ORDER BY d.rowid',
        (context.run_id, context.episode_id))]


def _heads(rows):
    result = {}
    for row in rows:
        if row['sheet_ref'] == row['current_ref']:
            result[row['family']] = row
    return result


def _register(repository, context, arguments, outcome, method):
    ref = (outcome.get('result') or {}).get('sheet_ref')
    if not ref:
        return None
    store = repository.store
    _install(store)
    saved = repository.read(ref)
    prior = _rows(store, context)
    families = {row['sheet_ref']: row['family'] for row in prior}
    args = plain(arguments)
    family = _family(repository, args, saved, families)
    owner = repository._sheet_owner(ref)
    policy = _policy_for(repository.provider)
    if policy is not None and repository.provider == policy.SCORING_PROVIDER:
        # A received child's main sheet and a receiver's calculation over its
        # own admitted inputs have different owners; neither replaces the
        # other's scientific scope merely by arriving later.
        family = identity('literature_scientific_sheet_owner_use',
            {'family': family, 'owner': owner})
    dependencies = list(dict.fromkeys([*_refs(args),
        *context.assignment.get('_automatic_literature_input_versions', ())]))
    receipt = {'version': VERSION, 'input_versions': dependencies,
        'publication_operation_ref': outcome.get('operation_ref'),
        'scientific_calculator': type(repository).__module__ + ':' + type(repository).__name__,
        'credit': 'belongs_to_original_scientific_action',
        'custody': 'owned' if owner == context.episode_id else 'admitted'}
    exists = store.db.execute(f'SELECT 1 FROM {TABLE} WHERE run_id=? AND episode_id=? '
        'AND sheet_ref=?', (context.run_id, context.episode_id, ref)).fetchone()
    store.db.execute(f'INSERT OR IGNORE INTO {TABLE} VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
        (context.run_id, context.episode_id, ref, family, repository.provider,
         type(repository).__module__ + ':' + type(repository).__name__, method,
         canonical(args), canonical(plain(context.assignment)),
         canonical(list(dict.fromkeys([*context.received_record_refs, *outcome['record_refs']]))),
         canonical(dependencies), canonical(receipt)))
    if exists is None:
        store.db.execute(f'INSERT OR REPLACE INTO {CURRENT} VALUES(?,?,?,?,?,?)',
            (context.run_id, context.episode_id, family, ref, 'current', None))
    return family


def _adapter(store, run_id, name):
    module, cls = name.split(':')
    module = {'gene_annotation_episode.episodic_workflow.root.a106.literature_a105_aggregation': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a105_aggregation', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a105_aggregation_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a105_aggregation_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a105_aggregation_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a105_aggregation_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a105_aggregation_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a105_aggregation_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a105_worksheet': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a105_worksheet', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a105_worksheet_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a105_worksheet_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a106_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a106_subscore': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore', 'gene_annotation_episode.episodic_workflow.root.a106.literature_a106_subscore_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_active_site_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_active_site_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_active_site_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_active_site_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_active_site_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_active_site_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_active_site_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_active_site_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_active_site_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_active_site_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_activity_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_activity_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_amount_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_amount_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_amount_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_amount_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_amount_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_amount_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_amount_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_amount_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_contribution': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_contribution', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_grading': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_grading', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_grading_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_grading_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_grading_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_grading_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_grading_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_grading_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_grading_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_grading_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assay_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_assets': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_assets', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_model_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_model_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_model_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_model_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_model_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_model_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_model_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_model_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_interaction_validation': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_interaction_validation', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_model_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_model_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_model_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_model_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_models': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_models', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_reader': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_reader', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_binding_visual_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_binding_visual_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_calibration_recovery_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_calibration_recovery_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_calibration_recovery_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_calibration_recovery_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_calibration_recovery_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_calibration_recovery_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_calibration_recovery_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_calibration_recovery_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_calibration_recovery_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_calibration_recovery_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_channel_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_channel_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_channel_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_channel_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_channel_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_channel_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_channel_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_channel_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_channel_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_channel_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_compiled_assay_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_compiled_assay_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_compiled_assay_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_compiled_assay_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_compiled_assay_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_compiled_assay_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_compiled_assay_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_compiled_assay_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_compiled_assay_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_compiled_assay_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_completion_time_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_completion_time_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_completion_time_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_completion_time_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_completion_time_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_completion_time_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_completion_time_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_completion_time_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_completion_time_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_completion_time_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_concentration_window_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_concentration_window_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_concentration_window_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_concentration_window_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_concentration_window_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_concentration_window_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_concentration_window_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_concentration_window_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_concentration_window_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_concentration_window_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_figure_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_figure_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_local_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_local_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_owner_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_owner_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_v2_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_v2_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_v3_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_v3_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_controlled_response_v3_population': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_controlled_response_v3_population', 'gene_annotation_episode.episodic_workflow.root.a106.literature_covariance_presentation': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_covariance_presentation', 'gene_annotation_episode.episodic_workflow.root.a106.literature_current_results': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_current_results', 'gene_annotation_episode.episodic_workflow.root.a106.literature_endpoint_signal_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_endpoint_signal_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_endpoint_signal_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_endpoint_signal_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_endpoint_signal_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_endpoint_signal_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_endpoint_signal_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_endpoint_signal_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_endpoint_signal_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_endpoint_signal_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_experimental_contracts': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_contracts', 'gene_annotation_episode.episodic_workflow.root.a106.literature_experimental_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_experimental_task': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_task', 'gene_annotation_episode.episodic_workflow.root.a106.literature_figure_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_figure_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_figure_measurements': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_figure_measurements', 'gene_annotation_episode.episodic_workflow.root.a106.literature_figure_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_figure_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_figure_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_figure_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_gel_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_gel_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_gel_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_gel_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_gel_native_contracts': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_gel_native_contracts', 'gene_annotation_episode.episodic_workflow.root.a106.literature_gel_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_gel_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_gel_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_gel_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_gel_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_gel_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_html_quantity_reader': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_html_quantity_reader', 'gene_annotation_episode.episodic_workflow.root.a106.literature_intervention_grading': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_grading', 'gene_annotation_episode.episodic_workflow.root.a106.literature_intervention_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_intervention_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_intervention_table': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_table', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ion_discrimination_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ion_discrimination_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ion_discrimination_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ion_discrimination_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ion_discrimination_numbers': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ion_discrimination_numbers', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ion_discrimination_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ion_discrimination_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ion_discrimination_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ion_discrimination_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ion_discrimination_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ion_discrimination_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_model_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_model_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_model_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_model_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_model_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_model_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_model_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_model_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_summary_precision_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_summary_precision_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_summary_precision_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_summary_precision_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_summary_precision_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_summary_precision_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_summary_precision_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_summary_precision_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_summary_precision_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_summary_precision_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_kinetic_validation': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_kinetic_validation', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_comparison_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_comparison_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_comparison_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_comparison_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_comparison_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_comparison_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_comparison_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_comparison_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_comparison_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_comparison_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_validation_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_validation_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_validation_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_validation_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_validation_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_validation_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_validation_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_validation_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_measurement_validation_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_measurement_validation_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_native_rate_operand_information': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_native_rate_operand_information', 'gene_annotation_episode.episodic_workflow.root.a106.literature_numerical_contracts': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_numerical_contracts', 'gene_annotation_episode.episodic_workflow.root.a106.literature_numerical_return_presentation': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_numerical_return_presentation', 'gene_annotation_episode.episodic_workflow.root.a106.literature_optical_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_optical_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_optical_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_optical_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_optical_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_optical_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_optical_validation': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_optical_validation', 'gene_annotation_episode.episodic_workflow.root.a106.literature_parent_depletion_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_depletion_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_parent_depletion_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_depletion_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_parent_depletion_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_depletion_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_parent_depletion_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_depletion_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_parent_depletion_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_depletion_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_parent_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_parent_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_partner_defined_units': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_partner_defined_units', 'gene_annotation_episode.episodic_workflow.root.a106.literature_partner_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_partner_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_partner_source_fields': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_partner_source_fields', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_assessments': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_assessments', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_operands': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_operands', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_source': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_source', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_summary': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_summary', 'gene_annotation_episode.episodic_workflow.root.a106.literature_perturbation_summary_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_summary_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_population_catalog': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_population_catalog', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_coupling_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_coupling_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_coupling_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_coupling_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_coupling_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_coupling_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_coupling_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_coupling_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_coupling_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_coupling_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_partition_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_partition_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_partition_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_partition_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_partition_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_partition_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_partition_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_partition_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_product_partition_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_product_partition_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_prompt_binding': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_prompt_binding', 'gene_annotation_episode.episodic_workflow.root.a106.literature_prose_reader': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_prose_reader', 'gene_annotation_episode.episodic_workflow.root.a106.literature_quantity_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_quantity_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_bound_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_bound_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_domains': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_domains', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_meaning_delivery': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_meaning_delivery', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_meaning_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_meaning_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_native_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_native_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_observation_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_observation_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_observation_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_observation_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_observation_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_observation_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_observation_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_observation_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_reader': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_reader', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_replicate_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_replicate_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_replicate_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_replicate_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_replicate_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_replicate_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_replicate_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_replicate_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_source_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_source_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_rate_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_rate_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_reader': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_reader', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_source_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_source_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_source_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_source_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_source_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_source_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_source_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_source_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_source_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_source_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_source_validation': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_source_validation', 'gene_annotation_episode.episodic_workflow.root.a106.literature_ratio_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_ratio_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_reaction_meanings_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_reaction_meanings_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_reaction_native_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_reaction_native_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_reaction_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_reaction_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_received_fact_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_received_fact_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_reference_parent_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_reference_parent_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_required_grading': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_required_grading', 'gene_annotation_episode.episodic_workflow.root.a106.literature_sequence_discovery': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_sequence_discovery', 'gene_annotation_episode.episodic_workflow.root.a106.literature_sheet_policy': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_sheet_policy', 'gene_annotation_episode.episodic_workflow.root.a106.literature_sheet_updates': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_sheet_updates', 'gene_annotation_episode.episodic_workflow.root.a106.literature_source_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_source_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_source_population_catalog': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_source_population_catalog', 'gene_annotation_episode.episodic_workflow.root.a106.literature_stoichiometric_balance_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_stoichiometric_balance_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_stoichiometric_balance_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_stoichiometric_balance_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_stoichiometric_balance_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_stoichiometric_balance_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_stoichiometric_balance_render': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_stoichiometric_balance_render', 'gene_annotation_episode.episodic_workflow.root.a106.literature_stoichiometric_balance_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_stoichiometric_balance_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_structure_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_structure_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_summary_figure_reader': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_summary_figure_reader', 'gene_annotation_episode.episodic_workflow.root.a106.literature_task_families': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_task_families', 'gene_annotation_episode.episodic_workflow.root.a106.literature_transport_calculations': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_transport_calculations', 'gene_annotation_episode.episodic_workflow.root.a106.literature_transport_inputs': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_transport_inputs', 'gene_annotation_episode.episodic_workflow.root.a106.literature_transport_prompt': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_transport_prompt', 'gene_annotation_episode.episodic_workflow.root.a106.literature_transport_storage': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_transport_storage', 'gene_annotation_episode.episodic_workflow.root.a106.literature_work_report': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_work_report', 'gene_annotation_episode.episodic_workflow.root.a106.literature_work_results': 'gene_annotation_episode.episodic_workflow.root.a106.library.literature_work_results'}.get(module, module)
    factory = getattr(import_module(module), cls)
    def read_cells(context, *selection):
        ref, components = selection[-2:]
        source = store.get(ref)
        candidates = store.db.execute(f'SELECT adapter FROM {TABLE} WHERE run_id=? '
            'AND sheet_ref=? ORDER BY rowid DESC', (run_id, ref)).fetchall()
        if not candidates:
            raise ContractError('literature_dependency_adapter_not_registered')
        for candidate in candidates:
            native = _adapter(store, run_id, candidate['adapter'])
            if native.provider == source.get('provider'):
                return native.fact_cells(context, [ref], components=components)
        raise ContractError('literature_dependency_adapter_not_registered')
    parameters = inspect.signature(factory).parameters
    return factory(store, run_id, **({'read_cells': read_cells} if 'read_cells' in parameters else {}))


def _context(context, row, refs):
    return replace(context, assignment=json.loads(row['assignment']),
        received_record_refs=tuple(dict.fromkeys([
            *context.received_record_refs, *json.loads(row['possessed']), *refs])))


def _refresh_dependents(repository, context):
    store = repository.store
    produced = []
    # Each pass replaces actual changed input versions.  A cycle is an invalid
    # dependency graph, not an excuse for an iteration/turn/time cutoff.
    visited = set()
    unavailable = set()
    while True:
        rows = _rows(store, context)
        heads = _heads(rows)
        replacements = {row['sheet_ref']: heads[row['family']]['sheet_ref'] for row in rows}
        pending = []
        for row in heads.values():
            if json.loads(row['receipt'])['custody'] != 'owned':
                continue
            args = json.loads(row['arguments'])
            policy = _policy_for(row['provider'])
            if policy is not None and hasattr(policy, 'dependent_revision'):
                decision, detail = policy.dependent_revision(row['provider'], args, replacements)
                if decision == 'unavailable':
                    store.db.execute(f'UPDATE {CURRENT} SET status=?,detail=? '
                        'WHERE run_id=? AND episode_id=? AND family=?',
                        ('unavailable', canonical(detail), context.run_id, context.episode_id, row['family']))
                if decision in {'unavailable', 'skip'}:
                    continue
            if policy is not None and row['provider'] == policy.SCORING_PROVIDER and hasattr(policy, 'revised_arguments'):
                updated = policy.revised_arguments(args, replacements, _replace_refs)
            else:
                updated = _replace_refs(args, replacements)
            if canonical(args) != canonical(updated):
                if (row['family'], canonical(updated)) not in unavailable:
                    pending.append((row, updated))
        if not pending:
            return produced
        for row, arguments in pending:
            fingerprint = row['family'], canonical(arguments)
            if fingerprint in visited:
                raise ContractError('literature_sheet_dependency_cycle')
            visited.add(fingerprint)
            adapter = _adapter(store, context.run_id, row['adapter'])
            refreshed = _context(context, row, replacements.values())
            key = identity('automatic_literature_sheet_refresh', {
                'version': VERSION, 'family': row['family'], 'arguments': arguments})
            try:
                outcome = getattr(adapter, row['method'])(refreshed, arguments, key)
            except ContractError as error:
                if not str(error).endswith(('component_not_received', 'cell_not_received',
                        'sheet_not_received')):
                    raise
                # A later child assessment does not grant its unreturned
                # components.  Invalidate the dependent current value, retain
                # its historical calculation and exact declared bindings, and
                # let a later authentic receipt make the same dependency usable.
                detail = {'version': VERSION, 'reason': str(error),
                    'input_versions': list(dict.fromkeys(_refs(arguments))),
                    'requirement': 'dependent_component_not_in_admitted_subset'}
                store.db.execute(f'UPDATE {CURRENT} SET status=?,detail=? '
                    'WHERE run_id=? AND episode_id=? AND family=?',
                    ('unavailable', canonical(detail), context.run_id,
                     context.episode_id, row['family']))
                unavailable.add(fingerprint)
                continue
            produced.append(outcome)


def _refresh_main(repository, context):
    """A106 finalization remains an explicit assessment action."""
    return []


def _merge(outcome, updates):
    if not updates:
        return outcome
    result = deepcopy(outcome)
    for field in ('record_refs', 'changed_record_refs'):
        result[field] = list(dict.fromkeys([*result.get(field, []),
            *(ref for update in updates for ref in update.get(field, []))]))
    return result


def _publication_receipt(repository, context, outcome):
    ref = (outcome.get('result') or {}).get('sheet_ref')
    if not ref or not _installed(repository.store):
        return None
    row = repository.store.db.execute(f'SELECT receipt FROM {TABLE} '
        'WHERE run_id=? AND episode_id=? AND sheet_ref=?',
        (context.run_id, context.episode_id, ref)).fetchone()
    return json.loads(row['receipt']) if row else None


def _replay_publication(repository, context, outcome):
    receipt = _publication_receipt(repository, context, outcome)
    if receipt is None:
        # Native sheets saved before dependency publication returned this result.
        return outcome
    if ('returned_record_refs' not in receipt
            or receipt['publication_operation_ref'] != outcome.get('operation_ref')):
        # Old publication did not save its merged return. Current heads cannot
        # reconstruct that historical result without changing what was returned.
        raise ContractError('literature_publication_return_not_retained')
    return {**outcome, **{field: receipt['returned_record_refs'][field]
        for field in ('record_refs', 'changed_record_refs') if field in receipt['returned_record_refs']}}


def _retain_publication(repository, context, outcome):
    receipt = _publication_receipt(repository, context, outcome)
    if receipt is not None:
        # These are the only fields publication adds to the native outcome.
        # Keep the native operation and its numerical-sheet validation intact.
        receipt['returned_record_refs'] = {field: outcome[field]
            for field in ('record_refs', 'changed_record_refs') if field in outcome}
        repository.store.db.execute(f'UPDATE {TABLE} SET receipt=? '
            'WHERE run_id=? AND episode_id=? AND sheet_ref=?',
            (canonical(receipt), context.run_id, context.episode_id,
             outcome['result']['sheet_ref']))
    return outcome


def publication(method):
    """Wrap the storage interface, including direct and atomic population."""
    if getattr(method, '_automatic_literature_updates', False):
        return method
    @wraps(method)
    def populate(repository, context, arguments, operation_key):
        store = repository.store
        # Only registered literature score owners participate in this update.
        if not _supported(repository):
            return method(repository, context, arguments, operation_key)
        installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (repository.operations_table,)).fetchone()
        if installed and isinstance(operation_key, str) and store.db.execute(
                f'SELECT 1 FROM {repository.operations_table} '
                'WHERE run_id=? AND episode_id=? AND operation_key=?',
                (repository.run_id, context.episode_id, operation_key)).fetchone():
            # Let the native reader validate the request and saved inputs first.
            # Replaying an operation does not publish or refresh anything.
            outcome = method(repository, context, arguments, operation_key)
            return _replay_publication(repository, context, outcome)
        outer = not getattr(store, '_literature_sheet_updating', False)
        if outer:
            store._literature_sheet_updating = True
        try:
            with store.transaction():
                outcome = method(repository, context, arguments, operation_key)
                if outcome.get('status') not in {'completed', 'partial'}:
                    return outcome
                _register(repository, context, arguments, outcome, method.__name__)
                if not outer:
                    return _retain_publication(repository, context, outcome)
                updates = _refresh_dependents(repository, context)
                updates.extend(_refresh_main(repository, context))
                updates.extend(_refresh_dependents(repository, context))
                return _retain_publication(repository, context, _merge(outcome, updates))
        finally:
            if outer:
                store._literature_sheet_updating = False
    populate._automatic_literature_updates = True
    return populate


def admitted(repository, context, cells, operation_key):
    """Refresh from the exact admitted subset; a handle grants no private cells."""
    if not cells or not _supported(repository):
        return
    store = repository.store
    _install(store)
    for ref in dict.fromkeys(row['sheet_ref'] for row in cells):
        source = store.get(ref)
        request = json.loads(store.get_artifact(source['request_ref']))
        owner = request['episode_id']
        row = store.db.execute(f'SELECT adapter,method FROM {TABLE} '
            'WHERE run_id=? AND episode_id=? AND sheet_ref=?',
            (context.run_id, owner, ref)).fetchone()
        if row is None:
            # Retained pre-update sheets can be admitted through their actual
            # repository.  The receipt still limits every later fact_cells read.
            adapter, method = repository, 'populate'
        else:
            adapter, method = _adapter(store, context.run_id, row['adapter']), row['method']
        cell_refs = (repository.cell_record_refs(cells) if hasattr(repository, 'cell_record_refs')
            else [cell['sheet_ref'] for cell in cells])
        refs = list(dict.fromkeys([*context.received_record_refs, *cell_refs]))
        receiving = replace(context, received_record_refs=tuple(refs))
        _register(adapter, receiving, request['arguments'], {
            'result': {'sheet_ref': ref}, 'record_refs': [ref],
            'operation_ref': operation_key}, method)
    outer = not getattr(store, '_literature_sheet_updating', False)
    if outer:
        store._literature_sheet_updating = True
        try:
            _refresh_dependents(repository, receiving)
            _refresh_main(repository, receiving)
            _refresh_dependents(repository, receiving)
        finally:
            store._literature_sheet_updating = False


def current_sheet_refs(store, context, provider=None):
    """Saved current versions, restricted to this scientific owner/receiver."""
    if not _installed(store):
        return []
    heads = _heads(_rows(store, context))
    return [row['sheet_ref'] for row in heads.values()
        if row['current_status'] == 'current' and
            (provider is None or row['provider'] == provider)]


def current_scoring_sheets(store, context):
    """Project saved current evidence sheets, without another grading action.

    Only this episode's own calculations and exact admitted cells participate.
    Old scientific artifacts and archived report forms remain historical.
    """
    rows = _rows(store, context)
    if not rows:
        return []
    heads = list(_heads(rows).values())
    known = list(dict.fromkeys([*context.received_record_refs,
        *(row['sheet_ref'] for row in heads)]))
    view = replace(context, received_record_refs=tuple(known))
    result = []
    for row in heads:
        policy = _policy_for(row['provider'])
        if policy is None or row['provider'] != policy.SCORING_PROVIDER:
            continue
        native = _adapter(store, context.run_id, row['adapter'])
        cells = (native.fact_cells(view, [row['sheet_ref']], components=list(native.components))
            if row['current_status'] == 'current' else [])
        args = json.loads(row['arguments'])
        axis = policy.AXIS
        inputs = []
        for grade in heads:
            if grade['provider'] != policy.GRADING_PROVIDER:
                continue
            arguments = json.loads(grade['arguments'])
            if arguments['assertion_ref'] != args['assertion_ref']:
                continue
            if not policy.includes_grade(args, grade['sheet_ref']):
                continue
            adapter = _adapter(store, context.run_id, grade['adapter'])
            actual = adapter.fact_cells(view, [grade['sheet_ref']], components=list(adapter.components))
            inputs.append({'sheet_ref': grade['sheet_ref'],
                'available_components': [cell['component'] for cell in actual],
                'cells': actual,
                'input_versions': json.loads(grade['dependencies'])})
        receipt = json.loads(row['receipt'])
        receipt.pop('returned_record_refs', None)
        result.append({'version': VERSION, 'axis': axis, 'sheet_ref': row['sheet_ref'],
            'assertion_ref': args['assertion_ref'], 'cells': cells,
            'status': row['current_status'],
            'missing_inputs': json.loads(row['current_detail']) if row['current_detail'] else None,
            'subscoring_sheets': inputs, 'dependency_receipt': receipt,
            'update_rule': 'automatic_before_original_action_credit',
            'scientific_combination': 'existing_axis_calculator_and_declared_bindings',
            'controller_progress': 'separate_from_evidence_scoring_sheet'})
    return result
