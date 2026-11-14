"""Canonical iterator and exception defining sources used by private A108 callbacks."""
from pathlib import Path
import hashlib

_REPOSITORY = Path(__file__).resolve().parents[4]
_SHARED_INFRASTRUCTURE_SOURCES = (
    'gene_annotation_episode/episodic_workflow/root/method_loop/__init__.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/archive.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/binding.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/communication.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/durable.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/durable_worker.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/episode.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/identities.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/independent.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/reconstruction.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/runtime.py',
    'gene_annotation_episode/episodic_workflow/root/method_loop/suspension.py',
    'gene_annotation_episode/domain.py',
    'gene_annotation_episode/episodic_workflow/root/communication.py',
    'gene_annotation_episode/episodic_workflow/root/episode_journal.py',
    'gene_annotation_episode/episodic_workflow/root/episode_contract_information.py',
    'gene_annotation_episode/acquisition.py',
    'gene_annotation_episode/episodic_workflow/root/provider_errors.py',
    'gene_annotation_episode/episodic_workflow/root/task_action_units.py',
    'gene_annotation_episode/episodic_workflow/root/task_values.py',
)

def shared_infrastructure_source_paths():
    return {key: _REPOSITORY / key for key in _SHARED_INFRASTRUCTURE_SOURCES}

def shared_infrastructure_source_bytes():
    return b''.join(path.read_bytes() for path in shared_infrastructure_source_paths().values())

def shared_infrastructure_source_fingerprints():
    return {key: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in shared_infrastructure_source_paths().items()}
