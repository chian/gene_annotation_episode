"""Real episode packages written to disk for one test.

A test that needs an episode differing from a kept test episode in one way gets a real package: the ten files of
the kept episode copied under a fresh package name, with the named text changes, imported like any episode. No
class is assembled by hand and no module name is assigned."""
import importlib
from pathlib import Path
import shutil
import sys
import uuid

import pytest

EPISODES = Path(__file__).parent
SOURCES = {'fact_collection': EPISODES / 'fact_collection',
           'fact_collection/fact_extraction': EPISODES / 'fact_collection' / 'fact_extraction'}
FILES = ('__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py')


def write_package(root, binding_path, edits, add):
    """Copy the episode ``binding_path`` below ``root/<tag>/`` with ``edits`` ({file: [(old, new), ...]}, each
    ``old`` occurring exactly once) and the new files ``add`` ({file: text}); the dotted name of the package."""
    tag = 'variant_' + uuid.uuid4().hex[:10]
    package = root / tag
    for part in binding_path.split('/'):
        package.mkdir(parents=True, exist_ok=True)
        (package / '__init__.py').touch()
        package = package / part
    (package / 'messages').mkdir(parents=True)
    source = SOURCES[binding_path]
    for name in FILES:
        shutil.copyfile(source / name, package / name)
    for path in (source / 'messages').glob('*.py'):
        shutil.copyfile(path, package / 'messages' / path.name)
    for name, changes in edits.items():
        text = (package / name).read_text()
        for old, new in changes:
            if text.count(old) != 1:
                raise ValueError('edit_must_match_exactly_once:' + name + ':' + old)
            text = text.replace(old, new)
        (package / name).write_text(text)
    for name, text in add.items():
        (package / name).write_text(text)
    return tag + '.' + binding_path.replace('/', '.')


@pytest.fixture
def episode_variant(tmp_path):
    """``make(binding_path, edits=None, add=None, module='episode')`` imports the named module of a fresh copy of
    a kept test episode and returns it (a class-definition refusal is raised by the import)."""
    root = tmp_path / 'episode_variants'
    root.mkdir()
    sys.path.insert(0, str(root))
    made = []

    def make(binding_path, edits=None, add=None, module='episode'):
        package = write_package(root, binding_path, edits or {}, add or {})
        made.append(package.split('.')[0])
        importlib.invalidate_caches()
        return importlib.import_module(package + '.' + module)
    yield make
    sys.path.remove(str(root))
    for name in [name for name in sys.modules if name.split('.')[0] in made]:
        del sys.modules[name]
