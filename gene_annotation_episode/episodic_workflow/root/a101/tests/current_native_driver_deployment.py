"""Exact selected current A101 deployment files for synthetic driver controls.

Only the original driver, its actually bound contract, optional syntax parser,
standard program-context provider, and their real package initializers are
copied. This creates a new controlled deployment; retained producer manifests
and profiles are never read or rewritten.
"""
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[5]
AXIS = 'gene_annotation_episode.episodic_workflow.root.a101'


def deployment_module_path(module):
    """Use the selected module's actual own source, including its library home."""
    name = module.__name__
    assert name.startswith(AXIS + '.')
    path = Path(module.__file__).resolve()
    relative = path.relative_to(PROJECT_ROOT)
    assert relative == Path(*name.split('.')).with_suffix('.py')
    assert path.is_file()
    return relative.as_posix()


def copy_current_driver_deployment(deployment, driver, contracts, *, parser, write):
    """Copy exact current selected source bytes while retaining package layout."""
    assert driver.__name__ in {
        AXIS + '.native_blast_database_driver',
        AXIS + '.native_blast_standard_database_driver',
    }
    assert driver.contracts is contracts
    modules = [driver, contracts]
    if driver.__name__.endswith('.native_blast_standard_database_driver'):
        context = sys.modules[contracts.resolve_blast_program_context.__module__]
        assert context.__name__.startswith(AXIS + '.')
        modules.append(context)
    if parser is not None:
        assert parser.__name__.startswith(AXIS + '.')
        assert parser.__name__.rsplit('.', 1)[1] == 'blast_pssm_inputs'
        modules.append(parser)
    selected = {}
    for module in modules:
        relative = Path(deployment_module_path(module))
        selected[relative] = PROJECT_ROOT / relative
        package = relative.parent
        while package.parts:
            initializer = package / '__init__.py'
            source = PROJECT_ROOT / initializer
            assert source.is_file(), str(source)
            selected[initializer] = source
            package = package.parent
    for relative, source in sorted(selected.items()):
        write(Path(deployment) / relative, source.read_bytes())
