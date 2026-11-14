"""Standard application scoring configuration; the shared runtime stays opaque.

Investigation progress, annotation support and native timing retain separate
meanings. Configuration is chosen here once, before opening an episode. Resume
uses the original recorded values rather than today's defaults.
"""
import json
from collections.abc import Mapping
from pathlib import Path

from .investigation_progress import FindingProgressPolicy, ScientificFindingProgress


VERSION = 'standard_received_scientific_progress_v2'


def bind_default_science(store, *, run_dir, resume, provider_config, credit_policy,
                         initial_known_record_refs, project_child_credit,
                         project_annotation_score, binding_definitions):
    if not resume:
        raise ValueError('explicit_root_task_credit_required')
    if provider_config is not None and not isinstance(provider_config, Mapping):
        raise TypeError('provider_config must be a mapping')
    supplied = {} if provider_config is None else dict(provider_config)
    definitions = {} if binding_definitions is None else dict(binding_definitions)
    # This resolver reads an existing manifest; fresh runs must select a root
    # task calculation explicitly before opening an episode.
    from .runtime import _run_location
    run_dir, _ = _run_location(store, run_dir, True)
    saved = json.loads((Path(run_dir)/'run.json').read_text())
    original = saved.get('binding_definitions', {})
    credit = original.get('credit', {})
    if credit.get('default_entrypoint') != VERSION:
        raise ValueError('resume_requires_original_scientific_binding_and_code_snapshot')
    progress = {'finding_unit': credit['policy']['finding_unit'],
                'loss_preview_size': credit['loss_preview_size'],
                'initial_known_record_refs': saved['scientific_knowledge']['initial_known_record_refs']}
    if 'annotation_score' in original and project_annotation_score is None:
        raise ValueError('resume_requires_original_annotation_score_binding')
    configured = supplied.get('scientific_progress', {})
    if not isinstance(configured, Mapping):
        raise TypeError('scientific_progress must be a mapping')
    progress.update(configured)
    if set(progress) != {'finding_unit', 'loss_preview_size', 'initial_known_record_refs'}:
        raise ValueError('scientific_progress_requires_finding_unit_loss_preview_size_and_initial_known_record_refs')
    if initial_known_record_refs is None:
        initial_known_record_refs = progress['initial_known_record_refs']
    scientific = ScientificFindingProgress(FindingProgressPolicy(progress['finding_unit']),
                                         progress['loss_preview_size'])

    def declare(name, value):
        if name in definitions and definitions[name] != value:
            raise ValueError('default_scientific_binding_definition_conflict:'+name)
        definitions[name] = value

    declare('credit', {**scientific.as_record(), 'default_entrypoint': VERSION})
    if project_child_credit is None and 'scientific_child_credit' in original:
        if original['scientific_child_credit'] != scientific.as_record():
            raise ValueError('resume_requires_original_scientific_child_binding')
        # Reconstruct only the actual saved historical choice. Absence in a
        # manifest never authorizes copying the root calculation into children.
        project_child_credit = scientific
        declare('scientific_child_credit', scientific.as_record())
    selected_policy = credit_policy if credit_policy is not None else supplied.get('credit')
    if selected_policy is not None:
        raise ValueError('categorical_annotation_policy_retired_supply_explicit_numeric_scorer')
    # There is no default numerical annotation scorer while the component
    # scoring sheets are unfinished. None is deliberately not a zero-valued
    # projector. An explicit caller scorer still uses the separate channel.
    # Consumed settings remain in the recorded definitions, rather than being
    # interpreted again as a runtime-owned credit or model configuration.
    configuration = (None if provider_config is None else
                     {key: value for key, value in supplied.items()
                      if key not in {'credit', 'scientific_progress'}})
    return {'run_dir': run_dir, 'provider_config': configuration, 'credit_policy': None,
            'project_credit': scientific, 'project_child_credit': project_child_credit,
            'project_annotation_score': project_annotation_score,
            'initial_known_record_refs': initial_known_record_refs,
            'binding_definitions': definitions}
