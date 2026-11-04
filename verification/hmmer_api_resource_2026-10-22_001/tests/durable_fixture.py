"""Subprocess fixtures: ordinary iterative Episodes, no models or science."""
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

from method_loop import (ClosedRecord, Context, Episode, EpisodeCompletion,
                         EpisodeGoal, EpisodeRequest, EpisodeTree, Grain, Leaf)
from method_loop.archive import JsonArchive
from method_loop.communication import ReportContract
from method_loop.durable import DurableExecutionError, DurableExecutionStore, canonical, content_digest


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
        raise AssertionError("fixture does not select an epoch transition")


@asynccontextmanager
async def open_commission(spec):
    arguments = spec["runtime_binding"]["arguments"]
    if (spec["runtime_binding"]["implementation_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or spec["runtime_binding"]["settings_sha256"] != content_digest(arguments)):
        raise DurableExecutionError("unavailable_binding", affected_refs=[spec["handle"]])
    root = Path(arguments["fixture_directory"])
    archive = JsonArchive(root / "archive")
    store = DurableExecutionStore(arguments["execution_directory"])
    grain = Grain("science", "One selected fixture action", "Fixture observations", lambda _: Controller())
    tree = EpisodeTree.recursive(grain)
    request_record = spec["child"]["request"]
    goal = EpisodeGoal.from_record(request_record["goal"])
    request = EpisodeRequest(goal, Record(request_record["message"]),
                             ReportContract.from_record(request_record["report_contract"]))
    context = Context.from_commission(tree=tree, run_id=spec["run_id"],
        parent_path=tuple(tuple(part) for part in spec["parent"]["path"]),
        parent_goal_id=spec["parent"]["goal_id"], child_goal_id=goal.goal_id,
        grain=grain.name, key=spec["child"]["key"])
    pending = []

    class Source:
        earlier = None

        async def first(self):
            with (root / "invocations").open("a") as stream:
                stream.write(str(os.getpid()) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            (root / "committed.json").write_text(canonical({"version": "fixture_commit_v1", "value": 3}))
            store.record_progress(spec["handle"], "fixture_committed_1", "committed_first_action")
            if arguments.get("gate"):
                await asyncio.to_thread(lambda: Path(arguments["gate"]).open("rb", buffering=0).read(1))
            if arguments.get("partial_failure"):
                raise DurableExecutionError("execution_failed", affected_refs=[spec["handle"]],
                                             partial_record_refs=["fixture_committed_1"])
            if arguments.get("descendant_spec"):
                descendant = arguments["descendant_spec"]
                store.commission(descendant)
                store.start(descendant["handle"])
                pending.append(descendant["handle"])
            self.earlier = 3
            return Record({"value": 3})

        def next(self, view):
            if view.units_consumed == 0:
                return Leaf(None, lambda _: self.first(), lambda _, value: value, "first")
            # The next selected action uses the earlier actual outcome.
            assert self.earlier == 3
            return Leaf(None, lambda _: Record({"value": self.earlier * 2}), lambda _, value: value, "second")

    async def pack_result(record, result):
        if arguments.get("pack_failure"):
            raise ValueError("fixture representation failure")
        form = result.as_record()
        if arguments.get("invalid_form"):
            form = {**form, "unrequested": True}
        return {"completion": EpisodeCompletion.from_record(record).as_record(),
            "episode_archive": archive.store(record).descriptor(),
            "result_archive": archive.store(result).descriptor(), "form": form,
            "facts_archive": archive.store({"version": "fixture_facts_v1", "record_refs": ["fixture_committed_1"]}).descriptor(),
            "pending_handles": pending}

    try:
        yield {"episode": Episode(grain, spec["child"]["key"], Source(), request,
                    lambda record: Record({"value": record.controller_state.values[-1]}),
                    archive_record=archive.store),
               "context": context, "pack_result": pack_result}
    finally:
        (root / "cleaned_up").write_text(str(os.getpid()))
