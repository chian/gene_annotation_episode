"""The support library reaches the system and the Store only by what custody offers.

These read the source of every module under ``episode_support`` (they import none of it)."""
import ast
from pathlib import Path
import re

import episode_runtime
from episode_runtime import EPISODE_API

LIBRARY = Path(episode_runtime.__file__).parents[1] / 'gene_annotation_episode' / 'episodic_workflow' / 'episode_support'
RUNNER_MODULES = ('episode_runtime.recording', 'episode_runtime.runner', 'episode_runtime.store_scope',
                  'episode_runtime.work_tables', 'episode_runtime.services', 'episode_runtime.episode_type',
                  'episode_runtime.store_ledger')
RUNNER_NAMES = ('Custody', 'UnitAttempts', 'UnitPosition', 'RecordedModel', 'Attempt', 'BoundEpisode', 'ChildBuilder',
                'WorkRows', 'StoreLedger', 'admit_entry', 'pass_records', 'return_records')
STORE_MODULE = 'gene_annotation_episode.state'


def _type_checking(test):
    return ((isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING')
            or (isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING'))


def _walk(node, runtime_only):
    """Every node below ``node``; with ``runtime_only`` the body of an ``if TYPE_CHECKING:`` is left out (it is
    never executed; its ``else`` branch is)."""
    yield node
    if runtime_only and isinstance(node, ast.If) and _type_checking(node.test):
        children = node.orelse
    else:
        children = ast.iter_child_nodes(node)
    for child in children:
        yield from _walk(child, runtime_only)


def imports(path, runtime_only=False):
    """``(module, name)`` of every import in the file, at any depth (function-level imports included); with
    ``runtime_only`` without the imports made only for type checking."""
    found = []
    for node in _walk(ast.parse(path.read_text(), filename=str(path)), runtime_only):
        if isinstance(node, ast.Import):
            found += [(name.name, None) for name in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found += [(node.module, name.name) for name in node.names]
    return found


def library_modules(tests):
    return sorted(path for path in LIBRARY.rglob('*.py') if ('tests' in path.relative_to(LIBRARY).parts) == tests)


def test_the_library_is_where_these_tests_look():
    assert len(library_modules(False)) > 2000 and len(library_modules(True)) > 100


def test_the_library_imports_no_recording_internal_of_the_system():
    """No module of the library, its tests included, imports the runner's recording, custody or store-scoping
    modules, or one of the runner's own names from ``episode_runtime``."""
    offending = []
    for path in library_modules(False) + library_modules(True):
        for module, name in imports(path):
            if module in RUNNER_MODULES or (module == 'episode_runtime' and name in RUNNER_NAMES):
                offending.append(str(path.relative_to(LIBRARY)) + ': ' + module + ('' if name is None else '.' + name))
    assert offending == []
    assert not set(RUNNER_NAMES) & set(EPISODE_API)


def test_no_library_function_module_imports_the_store_class():
    """A library function used inside an episode run is handed the custody-scoped store; a module that imports the
    ``Store`` class when it runs can open or address the Store outside custody. An import made only under
    ``if TYPE_CHECKING:`` (for an annotation) is never executed and is not counted. (Library tests build a real
    Store to test against and are not library function modules.)"""
    offending = []
    for path in library_modules(False):
        for module, name in imports(path, runtime_only=True):
            if (module == STORE_MODULE and name in (None, 'Store')) or (module == 'gene_annotation_episode'
                                                                         and name in ('Store', 'state')):
                offending.append(str(path.relative_to(LIBRARY)))
    assert sorted(set(offending)) == []


RAW_STORE = {'store.db': re.compile(r'\bstore\.db\b'), 'store.path': re.compile(r'\bstore\.path\b'),
             'private Store method': re.compile(r'\bstore\._[a-z]\w*')}


def raw_store_sites():
    """``{family: {pattern: (sites, files)}}`` over the library function modules: how often each function family
    (the first folder below ``episode_support``) still addresses the Store outside custody."""
    counts = {}
    for path in library_modules(False):
        parts = path.relative_to(LIBRARY).parts
        family = parts[0] if len(parts) > 1 else '(top level)'
        text = path.read_text()
        for name, pattern in RAW_STORE.items():
            sites = len(pattern.findall(text))
            if sites:
                found = counts.setdefault(family, {}).setdefault(name, [0, 0])
                found[0] += sites
                found[1] += 1
    return counts


def test_report_the_raw_store_sites_left_in_each_function_family(capsys, record_property):
    """A report, not a requirement: it prints one line per function family (``RAW_STORE_SITES ...``) and never
    fails on a count, so the carry-over can follow the numbers down to zero."""
    counts = raw_store_sites()
    totals = {name: [sum(found.get(name, (0, 0))[index] for found in counts.values()) for index in (0, 1)]
              for name in RAW_STORE}
    lines = ['RAW_STORE_SITES ' + family + ' ' + '; '.join(
        name + ': ' + str(found[name][0]) + ' sites in ' + str(found[name][1]) + ' files'
        for name in RAW_STORE if name in found) for family, found in sorted(counts.items())]
    lines.append('RAW_STORE_SITES TOTAL ' + '; '.join(
        name + ': ' + str(sites) + ' sites in ' + str(files) + ' files' for name, (sites, files) in totals.items()))
    with capsys.disabled():
        print('\n' + '\n'.join(lines))
    for name, (sites, files) in totals.items():
        record_property('raw_store_sites:' + name, str(sites) + ' in ' + str(files) + ' files')
    assert all(type(value) is int for found in counts.values() for pair in found.values() for value in pair)
