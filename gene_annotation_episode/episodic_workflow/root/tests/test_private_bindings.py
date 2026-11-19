"""Acceptance test: every episode is its own private binding.

The owner's rule: "every episode is it's own private binding. if an episode inherets from another
episode, then when I tune that episode, it will alter behavior in unintended places. that means there
are potentially COPIES of that same set of binding with a different prompt, for example, for similar
literature episode tasks and so on. But if you don't do that, I cannot tune individually."

An episode folder is a folder of an axis tree (``root/<axis>/<role>/**``) that holds an ``episode.py``.
The shape of a private binding is the episode's own files in its own folder, as it had them in the last
commit (docs/axis_restructure_20261117/CARRY_OVER_GUIDE.md). This test reads the real source tree with
``ast`` and checks, for each of the nine axes:

1. every folder of the axis tree that is a package or holds a module is an episode folder;
2. each ``episode.py`` declares exactly one binding class, whose literal ``binding_path`` is its folder;
3. the binding class inherits only from classes defined in its own folder (so from no other episode and
   from no shared base class anywhere);
4. no module of an episode folder imports anything of ``episodic_workflow.root`` outside its own folder
   (no parent, child, sibling or other episode's folder, by a static, relative or computed import);
5. there is no shared base module and no binding table in an axis folder: a module outside every episode
   folder (the axis's composition, for example its home factory, directly in ``root/<axis>/``) defines no
   class and names no binding path, and a module inside an episode folder names no binding path other
   than its own, an ancestor's or a direct child's.

Test folders (``tests``) are not bindings and are not checked. Copies of similar bindings are intended.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROOT_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
AXES = {
    'a101': 'sequence_homology_evidence', 'a102': 'structural_homology_evidence',
    'a103': 'gene_context_evidence', 'a104': 'evolutionary_history_evidence',
    'a105': 'experimental_activity_evidence', 'a106': 'perturbation_evidence',
    'a107': 'partner_presence_evidence', 'a108': 'sample_context_evidence',
    'a110': 'biochemical_feasibility_evidence',
}
SKIPPED_FOLDERS = frozenset({'tests', '__pycache__', 'fixtures'})
SHOWN = 25


def _folders(axis):
    """Every folder of the axis tree outside test folders, from the head folder down."""
    found, pending = [], [ROOT / axis / AXES[axis]]
    while pending:
        folder = pending.pop()
        found.append(folder)
        pending.extend(child for child in folder.iterdir() if child.is_dir() and child.name not in SKIPPED_FOLDERS)
    return sorted(found)


def _modules(folder):
    return sorted(path for path in folder.glob('*.py'))


def _episode_folders(axis):
    return [folder for folder in _folders(axis) if (folder / 'episode.py').is_file()]


def _binding_path(axis, folder):
    return folder.relative_to(ROOT / axis).as_posix()


def _package(folder):
    return ROOT_PACKAGE + '.' + '.'.join(folder.relative_to(ROOT).parts)


def _tree(path):
    return ast.parse(path.read_text(), filename=str(path))


def _shown(path):
    return path.relative_to(ROOT).as_posix()


def _report(axis, rule, violations):
    assert not violations, (axis + ': ' + rule + ': ' + str(len(violations)) + ' violation(s)\n  '
                            + '\n  '.join(violations[:SHOWN])
                            + ('' if len(violations) <= SHOWN else '\n  ... and ' + str(len(violations) - SHOWN) + ' more'))


def _import_targets(module_path, tree):
    """Each import of ``tree`` as (absolute module name, imported name or None, line)."""
    package = _package(module_path.parent).split('.')
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, None, node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - (node.level - 1)]
                target = '.'.join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ''
            for alias in node.names:
                yield target, alias.name, node.lineno


def _own_module(folder, target, name):
    """Whether an import of ``name`` from ``target`` stays in ``folder``'s own modules."""
    own = _package(folder)
    if target == own:  # ``from . import x`` or ``from <own package> import x``: x must be a module of this folder
        return name is not None and (folder / (name + '.py')).is_file()
    if target.startswith(own + '.'):
        rest = target[len(own) + 1:]
        return '.' not in rest and (folder / (rest + '.py')).is_file()
    return False


def _binding_classes(tree):
    """The classes of an ``episode.py`` that assign ``binding_path`` in their body, with the assigned node."""
    found = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                targets = item.targets if isinstance(item, ast.Assign) else (
                    [item.target] if isinstance(item, ast.AnnAssign) and item.value is not None else [])
                if any(isinstance(target, ast.Name) and target.id == 'binding_path' for target in targets):
                    found.append((node, item.value))
    return found


@pytest.mark.parametrize('axis', sorted(AXES))
def test_every_folder_of_an_axis_tree_is_an_episode_folder(axis):
    violations = [_shown(folder) + ': holds ' + ', '.join(path.name for path in _modules(folder)[:4])
                  + ' but no episode.py'
                  for folder in _folders(axis) if _modules(folder) and not (folder / 'episode.py').is_file()]
    _report(axis, 'a folder of an axis tree without its own episode.py', violations)


@pytest.mark.parametrize('axis', sorted(AXES))
def test_each_episode_declares_exactly_its_own_binding_path(axis):
    violations = []
    episodes = _episode_folders(axis)
    if not episodes:
        violations.append(axis + ': the axis tree has no episode folder')
    for folder in episodes:
        classes = _binding_classes(_tree(folder / 'episode.py'))
        expected = _binding_path(axis, folder)
        if len(classes) != 1:
            violations.append(_shown(folder / 'episode.py') + ': ' + str(len(classes))
                              + ' classes assign binding_path (exactly one binding per episode folder)')
            continue
        value = classes[0][1]
        if not isinstance(value, ast.Constant) or value.value != expected:
            violations.append(_shown(folder / 'episode.py') + ': binding_path must be the literal ' + repr(expected))
    _report(axis, 'an episode folder that does not declare its own binding', violations)


def _class_origins(folder):
    """For each module of ``folder``: its top-level classes and where each imported name comes from."""
    classes, imported = {}, {}
    for path in _modules(folder):
        tree = _tree(path)
        classes[path] = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        names = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for target, name, _ in _import_targets(path, ast.Module(body=[node], type_ignores=[])):
                    alias = next(a for a in node.names if a.name == name)
                    names[alias.asname or alias.name] = (target, name)
        imported[path] = names
    return classes, imported


def _foreign_bases(folder, path, node, classes, imported, seen):
    """The bases of ``node`` (transitively) that are not classes defined in ``folder``'s own modules."""
    foreign = []
    for base in node.bases:
        text = ast.unparse(base)
        if not isinstance(base, ast.Name):
            foreign.append(text + ' (not a plain class name of this folder)')
            continue
        if base.id in classes[path]:
            origin, definition = path, classes[path][base.id]
        elif base.id in imported[path] and _own_module(folder, *imported[path][base.id]):
            target, name = imported[path][base.id]
            module = name if target == _package(folder) else target.rsplit('.', 1)[1]
            origin = folder / (module + '.py')
            definition = classes[origin].get(name)
            if definition is None:
                foreign.append(text + ' (imported from ' + origin.name + ', which does not define it)')
                continue
        elif base.id in imported[path] and imported[path][base.id][0].split('.')[0] == 'episode_runtime':
            continue  # the system's episode base type: the one allowed foreign base
        else:
            source = imported[path].get(base.id)
            foreign.append(text + (' (from ' + source[0] + ')' if source else ' (not defined in this folder)'))
            continue
        if (origin, definition.name) not in seen:
            seen.add((origin, definition.name))
            foreign.extend(_foreign_bases(folder, origin, definition, classes, imported, seen))
    return foreign


@pytest.mark.parametrize('axis', sorted(AXES))
def test_a_binding_inherits_only_from_its_own_folder_and_the_system_type(axis):
    violations = []
    for folder in _episode_folders(axis):
        classes, imported = _class_origins(folder)
        episode = folder / 'episode.py'
        for node, _ in _binding_classes(_tree(episode)):
            foreign = _foreign_bases(folder, episode, classes[episode][node.name], classes, imported, set())
            if foreign:
                violations.append(_shown(episode) + ': ' + node.name + ' inherits ' + '; '.join(foreign))
    _report(axis, 'a binding that inherits from outside its own folder', violations)


@pytest.mark.parametrize('axis', sorted(AXES))
def test_an_episode_folder_imports_nothing_from_another_episode(axis):
    violations = []
    for folder in _episode_folders(axis):
        own = _package(folder)
        for path in _modules(folder):
            tree = _tree(path)
            for target, name, line in _import_targets(path, tree):
                inside_root = target == ROOT_PACKAGE or target.startswith(ROOT_PACKAGE + '.')
                if inside_root and not _own_module(folder, target, name):
                    violations.append(_shown(path) + ':' + str(line) + ': imports ' + target
                                      + ('' if name is None else ':' + name))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and ROOT_PACKAGE + '.' in node.value \
                        and not (node.value.startswith(own + '.') and '.' not in node.value[len(own) + 1:]):
                    violations.append(_shown(path) + ':' + str(node.lineno) + ': names the module '
                                      + node.value[:120])
                if isinstance(node, ast.Call) and getattr(node.func, 'attr', getattr(node.func, 'id', None)) in (
                        'import_module', '__import__') and any(
                        isinstance(part, ast.Name) and part.id in ('__package__', '__name__')
                        for argument in node.args for part in ast.walk(argument)):
                    violations.append(_shown(path) + ':' + str(node.lineno) + ': computes an import from its package')
    _report(axis, 'an episode folder that imports from another episode or from the root tree', violations)


@pytest.mark.parametrize('axis', sorted(AXES))
def test_no_shared_base_module_or_binding_table_in_an_axis_folder(axis):
    violations = []
    episodes = _episode_folders(axis)
    paths = {_binding_path(axis, folder) for folder in _folders(axis)}
    outside = [path for path in sorted((ROOT / axis).glob('*.py'))]
    outside += [path for folder in _folders(axis) if folder not in episodes for path in _modules(folder)]
    for path in outside:
        tree = _tree(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                violations.append(_shown(path) + ':' + str(node.lineno) + ': defines class ' + node.name
                                  + ' outside every episode folder')
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
                    node.value in paths or node.value.startswith(AXES[axis] + '/')):
                violations.append(_shown(path) + ':' + str(node.lineno) + ': names the binding path '
                                  + repr(node.value) + ' outside every episode folder')
    for folder in episodes:
        own = _binding_path(axis, folder)
        allowed = {own, *(own.rsplit('/', count)[0] for count in range(1, own.count('/') + 1)),
                   *(_binding_path(axis, child) for child in folder.iterdir()
                     if child.is_dir() and child.name not in SKIPPED_FOLDERS)}
        for path in _modules(folder):
            named = sorted({node.value for node in ast.walk(_tree(path))
                            if isinstance(node, ast.Constant) and isinstance(node.value, str)
                            and node.value in paths and node.value not in allowed})
            if named:
                violations.append(_shown(path) + ': names the binding paths of other episodes: '
                                  + ', '.join(named[:4]) + (' ...' if len(named) > 4 else ''))
    _report(axis, 'a shared base module or a binding table', violations)
