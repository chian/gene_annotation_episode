"""Native BLAST database scientific inputs and actual submitted-command custody.

No staging, environment setup, submission or driver invocation is performed
here. The episode chooses those actions through its ordinary terminal.
"""
from copy import deepcopy
import importlib
from pathlib import PurePosixPath



PROFILES = ('native_blast_database', 'native_blast_standard_database')


def _require(condition, code='native_database_terminal_custody_conflict'):
    if not condition:
        raise ValueError(code)


def validate_native_database_resource(configuration, key):
    """Validate one configured native BLAST database deployment and its software bindings."""
    value = configuration[key]
    _require(isinstance(value, dict) and set(value) == {'version', 'producer', 'environment', 'bindings'}
        and value['version'] == key + '_resource'
        and isinstance(value['producer'], dict) and set(value['producer']) == {'module_root'}
        and isinstance(value['environment'], dict)
        and all(isinstance(k, str) and k and isinstance(v, str) and '\0' not in k + v
            for k, v in value['environment'].items()), key + '_resource_invalid')
    information = importlib.import_module('.' + key + '_tool_info',
        'gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search' if key == 'native_blast_database'
        else 'gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.gene_context_evidence')
    function = (information.native_blast_database_tool_contracts if key == 'native_blast_database'
        else information.standard_blast_database_tool_contracts)
    function(value['bindings'], resource_kind='hpc', resource_id='configuration-validation')
    paths = [value['producer']['module_root']]
    paths.extend(row['software']['executable'] for row in value['bindings'])
    paths.extend(item['path'] for row in value['bindings'] for item in row['database_manifests'])
    _require(all(isinstance(path, str) and PurePosixPath(path).is_absolute()
        and '..' not in PurePosixPath(path).parts and '\0' not in path for path in paths),
        key + '_resource_path_invalid')
    aurora = PurePosixPath('/lus/flare/projects/BioReason-Aurora-Test')
    if PurePosixPath(configuration['workspace']).is_relative_to(aurora):
        _require(configuration['account'] == 'BioReason-Aurora-Test'
            and all(PurePosixPath(path).is_relative_to(aurora)
                for path in [*paths, configuration['python_executable']]),
            key + '_aurora_storage_or_account_conflict')
    return deepcopy(value)


def validate_native_database_assignment(configuration, assignment):
    for key in PROFILES:
        if key not in assignment['requested_job']:
            continue
        binding = configuration.get(key)
        _require(binding is not None, key + '_hpc_binding_required')
        job = assignment['requested_job'][key]
        selected = [row for row in binding['bindings'] if row['program'] == job['program']]
        _require(len(selected) == 1 and selected[0]['software'] == job['software']
            and all(row['manifest_file'] in selected[0]['database_manifests'] for row in job['databases']),
            key + '_selected_binding_conflict')
        paths = [job['software']['executable'], *[row['path'] for row in job['inputs']]]
        for database in job['databases']:
            paths.extend(database['native_paths'])
            paths.append(database['manifest_file']['path'])
            manifest = database['manifest']
            paths.extend(row['path'] for row in manifest['files'])
            paths.extend(row['path'] for row in manifest['metadata_manifests'])
            paths.extend(row['path'] for row in (manifest['preparation']['receipt'],
                manifest['preparation']['input_manifest'], manifest['access']['offline_configuration']) if row is not None)
        root = PurePosixPath(configuration['workspace'])
        _require(all(PurePosixPath(path).is_relative_to(root) for path in paths),
            key + '_selected_path_outside_workspace')


