"""Candidate: retain an authentic old global factory's initial information.

Missing newly introduced catalog metadata is not missing original provenance.
This reader validates the actual persisted original setup and never selects a
descendant episode as its substitute.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.a107.state import Store

KNOWN_FACTORY_IDENTITIES = (
    'gene_annotation_episode.execution_service_setup.ExecutionServiceFactory',
    'gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup.ExecutionServiceFactory',
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def original_global_factory_provenance(store, *, run_id, directory):
    """Read actual matching Journal/run.json metadata and reconstruct data only."""
    if type(store) is not Store or not isinstance(run_id, str) or not run_id:
        raise TypeError('initial_information_original_run_required')
    row = store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?', (run_id,)).fetchone()
    if row is None:
        raise ValueError('initial_information_original_run_required')
    settings = json.loads(row['settings'])
    saved = json.loads((Path(directory) / 'run.json').read_text())
    if saved.get('run_id') != run_id:
        raise ValueError('initial_information_original_run_identity_conflict')
    saved_settings = {key: value for key, value in saved.items() if key != 'run_id'}
    if _canonical(saved_settings) != _canonical(settings):
        raise ValueError('initial_information_original_settings_conflict')
    service = settings.get('episode_application_services')
    if not isinstance(service, dict):
        raise ValueError('initial_information_original_factory_provenance_missing')
    version = service.get('version')
    expected = {'version', 'factory', 'definition'}
    if version == 'episode_application_services_v2':
        expected.add('inputs')
        if service.get('inputs') not in {'actual_tool_catalog_v1', 'actual_tool_registry_v1'}:
            raise ValueError('initial_information_original_factory_inputs_unavailable')
    elif version != 'episode_application_services_v1':
        raise ValueError('initial_information_original_factory_identity_unavailable')
    if set(service) != expected or service.get('factory') not in KNOWN_FACTORY_IDENTITIES:
        raise ValueError('initial_information_original_factory_identity_unavailable')
    # from_record is the literal reviewed own-axis implementation. The complete
    # original record must survive; unsupported tails may not be discarded.
    factory = ExecutionServiceFactory.from_record(service['definition'])
    if _canonical(factory.as_record()) != _canonical(service['definition']):
        raise ValueError('initial_information_original_factory_configuration_changed')
    if not isinstance(settings.get('episode_bindings'), list):
        raise ValueError('initial_information_original_binding_records_missing')
    source = {'run_id': run_id, 'settings_sha256': hashlib.sha256(_canonical(settings).encode()).hexdigest(),
        'episode_application_services': deepcopy(service),
        'episode_bindings': deepcopy(settings['episode_bindings'])}
    return factory, {'version': 'original_global_execution_information_provenance_v1',
        'axis': 'A107', 'source': source,
        'authority_id': 'original-global-factory:' + hashlib.sha256(_canonical(source).encode()).hexdigest(),
        'meaning': 'The authenticated original caller factory supplied global initial execution information. '
            'Current recipient declarations and reader implementation are recorded separately; '
            'the original service/binding records are retained unchanged.'}


def check_original_global_factory_provenance(provenance, store, *, run_id, directory):
    factory, current = original_global_factory_provenance(store, run_id=run_id, directory=directory)
    if _canonical(current) != _canonical(provenance):
        raise ValueError('initial_information_original_factory_provenance_changed')
    return factory
