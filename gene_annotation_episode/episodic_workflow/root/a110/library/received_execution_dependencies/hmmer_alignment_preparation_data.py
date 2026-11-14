from __future__ import annotations
import math
import re
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.hmmer_model_data import _occurrence_valid
ALIMASK_PROFILE_EXECUTABLE_SHA256 = '4cf273b7b4b52363468b758a39bedf8f00540b01983bf6641ffd36140afad547'
ALIMASK_PROFILE = {'name': 'infernal_1_1_5_hmmer_3_4_alimask', 'source_sha256s': {'hmmer/src/alimask.c': '504e52c49a249facca5887d96f5efeaaf8012820b47bbe75e782aa14af7034ab', 'easel/esl_msaweight.c': '0195e7c2a4428f02a84e3c239922090e72a5a72a5cc5de8a3a5551f06b6efe68', 'easel/esl_msaweight.h': 'caf345d5c9053af80e899b697a648430306f2db6240f8724b017490b94ffb106', 'easel/esl_rand64.c': 'abd4b05b7bf619f196b1ca99c0de452e0fe38b3ffa0f7e2f5991d88d763e5359', 'easel/esl_vectorops.c': '6226cb25818a1319811f7fdec2aa590df0b60f40aa01521a806cf484ea117463'}}
MAP_CONTEXT_FIELDS = frozenset({'version', 'source_occurrence_id', 'source_sha256', 'producer', 'profile', 'binding', 'requested_cli_seed', 'resolved_cli_seed', 'effective_pb_config'})
_PB_CONFIG = {'fragthresh': 0.5, 'symfrac': 0.5, 'ignore_rf': True, 'allow_samp': True, 'sampthresh': 50000, 'nsamp': 10000, 'maxfrag': 5000, 'seed': 42, 'rng': 'easel_mt19937_64', 'sampler': 'esl_rand64_Deal_vitter_D_A'}

def alimask_map_context_shape(context):
    """Closed JSON operand shape, separate from its semantic association."""
    digest = lambda value: type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None
    integer = lambda value: type(value) is int and 0 <= value <= 2147483647
    if type(context) is not dict or set(context) != MAP_CONTEXT_FIELDS or context['version'] != 'hmmer_alignment_map_context_v1' or (type(context['source_occurrence_id']) is not str) or (not context['source_occurrence_id']) or (not digest(context['source_sha256'])) or (type(context['binding']) is not str) or (context['binding'] not in {'retained_executable_profile', 'unavailable'}) or (context['requested_cli_seed'] is not None and (not integer(context['requested_cli_seed']))) or (not integer(context['resolved_cli_seed'])):
        return False
    producer = context['producer']
    if type(producer) is not dict or set(producer) != {'program', 'engine_version', 'executable_sha256'} or producer['program'] != 'alimask' or (producer['engine_version'] != '3.4') or (producer['executable_sha256'] is not None and (not digest(producer['executable_sha256']))):
        return False
    profile, config = (context['profile'], context['effective_pb_config'])
    if profile is not None and (type(profile) is not dict or set(profile) != {'name', 'source_sha256s'} or type(profile['name']) is not str or (not profile['name']) or (type(profile['source_sha256s']) is not dict) or (set(profile['source_sha256s']) != set(ALIMASK_PROFILE['source_sha256s'])) or any((not digest(value) for value in profile['source_sha256s'].values()))):
        return False
    if config is not None and (type(config) is not dict or set(config) != set(_PB_CONFIG) or any((type(config[k]) is not bool for k in ('ignore_rf', 'allow_samp'))) or any((not integer(config[k]) for k in ('sampthresh', 'nsamp', 'maxfrag', 'seed'))) or any((not finite(config[k]) or not 0 <= config[k] <= 1 for k in ('fragthresh', 'symfrac'))) or any((type(config[k]) is not str for k in ('rng', 'sampler')))):
        return False
    return True

def alimask_map_context_valid(context, *, settings, source_occurrence=None, operation=None, alignment=None):
    """Validate retained identities/settings; never resolve a source or profile."""
    if not alimask_map_context_shape(context) or type(settings) is not dict:
        return False
    if operation is not None and (operation.get('program') != 'alimask' or operation.get('engine_version') != '3.4'):
        return False
    if source_occurrence is not None and (not _occurrence_valid(source_occurrence) or source_occurrence['direction'] != 'input' or source_occurrence['role'] != 'alignment' or (source_occurrence['ordinal'] != 0) or (context['source_occurrence_id'] != source_occurrence['occurrence_id']) or (context['source_sha256'] != source_occurrence['sha256'])):
        return False
    if alignment is not None and (context['source_occurrence_id'] != alignment.get('occurrence_id') or alignment.get('record_key') != context['source_occurrence_id'] + '#alignment/0' or alignment.get('engine_version') != '3.4'):
        return False
    resolved = settings.get('--seed', 42)
    if type(resolved) is not int or context['resolved_cli_seed'] != resolved or (context['requested_cli_seed'] is not None and context['requested_cli_seed'] != resolved) or (context['requested_cli_seed'] is None and resolved != 42):
        return False
    if context['binding'] == 'unavailable':
        return context['profile'] is None and context['effective_pb_config'] is None
    return context['producer']['executable_sha256'] == ALIMASK_PROFILE_EXECUTABLE_SHA256 and context['profile'] == ALIMASK_PROFILE and (context['effective_pb_config'] == {**_PB_CONFIG, 'ignore_rf': not bool(settings.get('--hand'))})

def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False
