"""Current A107 worker source discovery for the preparation snapshot."""
from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path


AXIS = 'gene_annotation_episode.episodic_workflow.root.a107'
CURRENT_WORKERS = {
    'flux_balance': AXIS + '.library.flux_balance_result_worker',
    'genomic_overlap': AXIS + '.library.genomic_overlap_result_worker',
}
_PACKAGE_PARENTS = {'gene_annotation_episode', 'gene_annotation_episode.episodic_workflow',
    'gene_annotation_episode.episodic_workflow.root'}


def _project_source(root, module):
    if module not in _PACKAGE_PARENTS and module != 'gene_annotation_episode.workflow_budget' and module != AXIS and not module.startswith(AXIS + '.'):
        raise ValueError('received_worker_foreign_source_owner')
    relative = Path(*module.split('.'))
    file = root / relative.with_suffix('.py')
    package = root / relative / '__init__.py'
    if file.is_file():
        return file
    if package.is_file():
        return package
    raise ValueError('native_dependency_unavailable')


def current_worker_sources(worker_module, *, module_root=None):
    """Find the current worker's dependency source files without importing them.

    The resulting file paths are copied by the preparation primitives.
    """
    if worker_module not in CURRENT_WORKERS.values():
        raise ValueError('received_worker_source_identity_invalid')
    root = Path(module_root) if module_root is not None else Path(__file__).resolve().parents[5]
    pending, sources = [worker_module], {}
    while pending:
        module = pending.pop()
        if module in sources:
            continue
        source = _project_source(root, module)
        sources[module] = source
        # Include executable package initializers as part of this source epoch.
        pieces = module.split('.')
        for index in range(1, len(pieces)):
            parent = '.'.join(pieces[:index])
            if (root / Path(*pieces[:index]) / '__init__.py').is_file():
                pending.append(parent)
        package = module if source.name == '__init__.py' else module.rsplit('.', 1)[0]
        for node in ast.walk(ast.parse(source.read_bytes(), filename=str(source))):
            if isinstance(node, ast.Import):
                pending.extend(alias.name for alias in node.names if alias.name == 'gene_annotation_episode' or alias.name.startswith('gene_annotation_episode.'))
            elif isinstance(node, ast.ImportFrom):
                imported = resolve_name('.' * node.level + (node.module or ''), package) if node.level else node.module
                if not imported or not (imported == 'gene_annotation_episode' or imported.startswith('gene_annotation_episode.')):
                    continue
                pending.append(imported)
                # A package attribute may be a submodule. Only an actual source
                # path establishes that obligation; an ordinary exported name
                # is authenticated through its defining module above.
                for alias in node.names:
                    candidate = imported + '.' + alias.name
                    relative = root / Path(*candidate.split('.'))
                    if relative.with_suffix('.py').is_file() or (relative / '__init__.py').is_file():
                        pending.append(candidate)
    return sources


def snapshot_relative_source(module, source):
    """Keep each package initializer and module at its actual import identity."""
    relative = Path(*module.split('.'))
    return relative / '__init__.py' if Path(source).name == '__init__.py' else relative.with_suffix('.py')
