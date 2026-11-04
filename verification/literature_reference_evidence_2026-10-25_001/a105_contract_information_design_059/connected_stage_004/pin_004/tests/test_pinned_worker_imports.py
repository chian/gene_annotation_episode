"""Real durable workers keep selected imports while preserving caller cwd.

Temporary shadow packages make an implicit cwd import fail. The selected
factory still runs an ordinary two-action Episode and returns its original form.
All subprocess deadlines below bound engineering tests, not episode execution.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from method_loop.durable import content_digest
from test_durable_episode import commission_spec


FACTORY = '''from contextlib import asynccontextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from method_loop import ClosedRecord, Context, Episode, EpisodeCompletion, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain, Leaf
from method_loop.archive import JsonArchive
from method_loop.communication import ReportContract
from method_loop.durable import DurableExecutionError, canonical, content_digest
import method_loop.durable as durable
import method_loop.durable_worker as worker

@dataclass(frozen=True)
class Record(ClosedRecord):
    value: dict
    def as_record(self):
        return self.value

class Controller:
    epoch = "fixture"
    def __init__(self):
        self.values = []
    def observe(self, label, value, *, is_root):
        self.values.append(value.as_record()["value"])
        return SimpleNamespace(stop=len(self.values) == 2, requests_transition=False)
    def state(self):
        return SimpleNamespace(stop=len(self.values) == 2, values=list(self.values))
    def transitioned(self, epoch):
        raise AssertionError("fixture does not transition")

@asynccontextmanager
async def open_commission(spec):
    binding = spec["runtime_binding"]
    args = binding["arguments"]
    if (binding["implementation_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or binding["settings_sha256"] != content_digest(args)):
        raise DurableExecutionError("identity_conflict", affected_refs=[spec["handle"]])
    root = Path(args["fixture_directory"])
    observed = int(Path(args["relative_operand"]).read_text())
    (root / "imports.json").write_text(json.dumps({"cwd": os.getcwd(),
        "factory": __file__, "durable": durable.__file__, "worker": worker.__file__,
        "episode": __import__("inspect").getfile(Episode), "observed": observed}))
    with (root / "invocations").open("a") as stream:
        stream.write(str(os.getpid()) + "\\n")
    archive = JsonArchive(root / "archive")
    grain = Grain("science", "One fixture action", "Fixture observations", lambda _: Controller())
    tree = EpisodeTree.recursive(grain)
    saved = spec["child"]["request"]
    goal = EpisodeGoal.from_record(saved["goal"])
    request = EpisodeRequest(goal, Record(saved["message"]), ReportContract.from_record(saved["report_contract"]))
    context = Context.from_commission(tree=tree, run_id=spec["run_id"],
        parent_path=spec["parent"]["path"], parent_goal_id=spec["parent"]["goal_id"],
        child_goal_id=goal.goal_id, grain=grain.name, key=spec["child"]["key"])
    class Source:
        earlier = None
        def first(self):
            self.earlier = observed
            return Record({"value": observed})
        def next(self, view):
            if view.units_consumed == 0:
                return Leaf(None, lambda _: self.first(), lambda _, result: result, "first")
            return Leaf(None, lambda _: Record({"value": self.earlier * 2}), lambda _, result: result, "second")
    def pack(record, result):
        return {"completion": EpisodeCompletion.from_record(record).as_record(),
            "episode_archive": archive.store(record).descriptor(),
            "result_archive": archive.store(result).descriptor(), "form": result.as_record(),
            "facts_archive": archive.store({"version": "fixture_facts_v1"}).descriptor(),
            "pending_handles": []}
    yield {"episode": Episode(grain, spec["child"]["key"], Source(), request,
        lambda record: Record({"value": record.controller_state.values[-1]}), archive_record=archive.store),
        "context": context, "pack_result": pack}
'''


DRIVER = '''import asyncio,json,sys
from pathlib import Path
from method_loop.durable import DurableExecutionStore
spec=json.load(sys.stdin)
store=DurableExecutionStore(spec["runtime_binding"]["arguments"]["execution_directory"])
store.commission(spec)
first=store.start(spec["handle"])
asyncio.run(asyncio.wait_for(store.wait_events({"version":"event_condition_v1",
    "events":[{"handle":spec["handle"],"event":"returned","after_cursor":0}],"reconsider_at":None}),10))
status=store.status(spec["handle"])
envelope=store.load_return(spec["handle"],status["return_id"])
again=store.start(spec["handle"])
print(json.dumps({"first":first,"again":again,"envelope":envelope,
    "original_commission":store.load_commission(spec["handle"])}))
'''


@pytest.mark.parametrize('factory_location', ['runtime', 'caller_extension'])
def test_worker_uses_selected_packages_and_factory_despite_shadowing_cwd(tmp_path, factory_location):
    root = Path(__file__).resolve().parents[1]
    pin = tmp_path / 'selected-runtime'
    shutil.copytree(root / 'method_loop', pin / 'method_loop',
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    factory_dir = pin if factory_location == 'runtime' else tmp_path / 'caller-extension'
    factory_dir.mkdir(parents=True, exist_ok=True)
    factory = factory_dir / 'pinned_worker_fixture.py'
    factory.write_text(FACTORY)
    shadow = tmp_path / 'caller-working-directory'
    (shadow / 'method_loop').mkdir(parents=True)
    (shadow / 'method_loop/__init__.py').write_text(
        'from pathlib import Path\nPath("shadow_package_loaded").write_text("wrong")\n'
        'raise RuntimeError("implicit cwd selected the wrong shared runtime")\n')
    (shadow / 'pinned_worker_fixture.py').write_text(
        'from pathlib import Path\nPath("shadow_factory_loaded").write_text("wrong")\n'
        'raise RuntimeError("implicit cwd selected the wrong factory")\n')
    (shadow / 'relative-caller-input.txt').write_text('3')
    spec = commission_spec(tmp_path)
    binding = spec['runtime_binding']
    binding['factory_module'] = 'pinned_worker_fixture'
    binding['implementation_sha256'] = hashlib.sha256(factory.read_bytes()).hexdigest()
    binding['arguments']['relative_operand'] = 'relative-caller-input.txt'
    binding['settings_sha256'] = content_digest(binding['arguments'])
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=os.pathsep.join(dict.fromkeys((str(pin), str(factory_dir)))))
    # The starter explicitly chooses its runtime. Its actual durable.start
    # must independently preserve that choice in the separate worker process.
    result = subprocess.run([sys.executable, '-P', '-B', '-c', DRIVER],
        input=json.dumps(spec), capture_output=True, text=True, env=environment,
        cwd=shadow, timeout=20)
    assert result.returncode == 0, result.stderr
    returned = json.loads(result.stdout)
    assert returned['original_commission'] == spec
    assert returned['envelope']['outcome'] == 'closed'
    assert returned['envelope']['failure'] is None
    assert returned['envelope']['form'] == {'value': 6}
    assert returned['envelope']['completion']['units_consumed'] == 2
    assert returned['first']['execution_identity'] == returned['again']['execution_identity']
    actual = json.loads((tmp_path / 'child/imports.json').read_text())
    assert actual['cwd'] == str(shadow)
    assert actual['observed'] == 3
    assert Path(actual['factory']).resolve() == factory
    for field, filename in (('durable', 'durable.py'), ('worker', 'durable_worker.py'), ('episode', 'episode.py')):
        assert Path(actual[field]).resolve() == pin / 'method_loop' / filename
    assert not (shadow / 'shadow_package_loaded').exists()
    assert not (shadow / 'shadow_factory_loaded').exists()
    assert (tmp_path / 'child/invocations').read_text().splitlines() == [str(returned['first']['execution_identity']['pid'])]
