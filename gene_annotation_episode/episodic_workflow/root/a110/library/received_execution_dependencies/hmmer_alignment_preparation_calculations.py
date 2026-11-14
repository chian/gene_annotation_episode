from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.hmmer_alignment_preparation_data import ALIMASK_PROFILE, ALIMASK_PROFILE_EXECUTABLE_SHA256, _PB_CONFIG, alimask_map_context_valid
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.hmmer_model_data import _occurrence_valid

def resolve_alimask_map_context(*, operation, software, source_occurrence, requested_options):
    """Bind only the recorded selected executable to the retained source profile.

    This pure adapter consumes an authenticated bundle's records. In particular,
    it never uses the installed executable or substitutes expected for an unknown
    actual digest. The CLI seed and PB's internal seed are distinct operands.
    """
    if type(operation) is not dict or operation.get('program') != 'alimask' or operation.get('engine_version') != '3.4' or (type(operation.get('settings')) is not dict) or (type(software) is not dict) or (set(software) != {'executable', 'expected_sha256', 'actual_sha256', 'declared_engine_version'}) or (not _occurrence_valid(source_occurrence)) or (type(requested_options) is not list) or any((type(token) is not str for token in requested_options)):
        raise ValueError('map_context_invalid')
    positions = [i for i, token in enumerate(requested_options) if token == '--seed']
    requested_seed = None
    if positions:
        try:
            if len(positions) != 1 or positions[0] + 1 >= len(requested_options):
                raise ValueError
            token = requested_options[positions[0] + 1]
            if not token.removeprefix('+').isascii() or not token.removeprefix('+').isdigit():
                raise ValueError
            requested_seed = int(token)
        except (ValueError, OverflowError):
            raise ValueError('map_context_invalid') from None
    actual = software['actual_sha256']
    bound = actual == software['expected_sha256'] == ALIMASK_PROFILE_EXECUTABLE_SHA256 and software['declared_engine_version'] == operation['engine_version']
    context = {'version': 'hmmer_alignment_map_context_v1', 'source_occurrence_id': source_occurrence['occurrence_id'], 'source_sha256': source_occurrence['sha256'], 'producer': {'program': 'alimask', 'engine_version': operation['engine_version'], 'executable_sha256': actual}, 'profile': deepcopy(ALIMASK_PROFILE) if bound else None, 'binding': 'retained_executable_profile' if bound else 'unavailable', 'requested_cli_seed': requested_seed, 'resolved_cli_seed': operation['settings'].get('--seed', 42), 'effective_pb_config': {**_PB_CONFIG, 'ignore_rf': not bool(operation['settings'].get('--hand'))} if bound else None}
    if software['declared_engine_version'] != operation['engine_version'] or not alimask_map_context_valid(context, settings=operation['settings'], source_occurrence=source_occurrence, operation=operation):
        raise ValueError('map_context_invalid')
    return context
