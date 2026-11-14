"""Actual private A105 sources and the canonical iterator they execute.

Private keys retain their original axis-relative spelling. Canonical iterator
keys are repository-qualified and do not depend on the checkout location.
The two callers retain their original source filters and digest algorithms.
"""
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root import method_loop


CANONICAL_ITERATOR_PREFIX = 'gene_annotation_episode/episodic_workflow/root/method_loop/'
CANONICAL_ITERATOR_FILES = (
    '__init__.py', 'archive.py', 'binding.py', 'communication.py', 'durable.py',
    'durable_worker.py', 'episode.py', 'identities.py', 'independent.py',
    'reconstruction.py', 'runtime.py', 'suspension.py',
)


CANONICAL_APPLICATION_FILES = (
    'gene_annotation_episode/__init__.py',
    'gene_annotation_episode/episodic_workflow/__init__.py',
    'gene_annotation_episode/episodic_workflow/root/__init__.py',
    'gene_annotation_episode/domain.py',
    'gene_annotation_episode/acquisition.py',
    'gene_annotation_episode/public_configuration.py',
    'gene_annotation_episode/form_reference_validation.py',
    'gene_annotation_episode/episode_bindings.py',
    'gene_annotation_episode/schema_information_text.py',
    'gene_annotation_episode/schema_support.py',
    'gene_annotation_episode/boundary_validation.py',
    'gene_annotation_episode/journal_metadata.py',
    'gene_annotation_episode/episodic_workflow/root/communication.py',
    'gene_annotation_episode/episodic_workflow/root/episode_contract_information.py',
    'gene_annotation_episode/episodic_workflow/root/episode_journal.py',
    'gene_annotation_episode/episodic_workflow/root/provider_errors.py',
    'gene_annotation_episode/episodic_workflow/root/receiving_context.py',
    'gene_annotation_episode/episodic_workflow/root/task_action_units.py',
    'gene_annotation_episode/episodic_workflow/root/task_values.py',
    'gene_annotation_episode/episodic_workflow/root/execution_timing.py',
    'gene_annotation_episode/episodic_workflow/root/boundary_validation.py',
)

def _with_canonical_iterator(root, private_files):
    files = {str(path.relative_to(root)): path for path in private_files
             if path.relative_to(root).parts[0] != 'method_loop'}
    canonical = Path(method_loop.__file__).resolve().parent
    files.update({CANONICAL_ITERATOR_PREFIX + name: canonical / name
                  for name in CANONICAL_ITERATOR_FILES})
    repository = canonical.parents[3]
    files.update({name: repository / name for name in CANONICAL_APPLICATION_FILES})
    return files


def independent_source_files():
    """Retain the independent binding's relative tests/bytecode exclusions."""
    root = Path(__file__).resolve().parent
    private_files = (path for path in root.rglob('*.py')
                     if not {'tests', '__pycache__'}.intersection(path.relative_to(root).parts))
    return _with_canonical_iterator(root, private_files)


def scientific_source_files():
    """Retain the scientific descriptor's original absolute tests exclusion."""
    root = Path(__file__).parent
    private_files = (path for path in root.rglob('*.py') if 'tests' not in path.parts)
    return _with_canonical_iterator(root, private_files)
