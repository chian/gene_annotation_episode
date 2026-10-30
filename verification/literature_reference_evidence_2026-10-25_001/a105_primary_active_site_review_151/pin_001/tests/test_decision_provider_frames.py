"""Local transport fixture: no server, credentials or inference calls."""
import asyncio
from copy import deepcopy
import json
import pytest

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.providers import ModelConnection, _SessionConnection, load_config


class ConversationWire(_SessionConnection):
    def __init__(self, directory, image_resolver=None):
        super().__init__(load_config(), directory, directory.parent,
                         image_resolver=image_resolver)
        self.sent = []
        self.compact = False
        self.turn = 0
        self.reply = {"fixture": True}

    async def _rpc(self, method, params):
        self.sent.append((method, deepcopy(params)))
        if method == "thread/start":
            return {"thread": {"id": "thread-fixture"},
                    "model": params["model"], "reasoningEffort": "medium"}
        assert method == "turn/start"
        self.turn += 1
        identity = "turn-" + str(self.turn)
        if self.compact:
            self.pending.extend([
                {"method": "item/started", "params": {"threadId": "thread-fixture",
                    "item": {"id": "compact", "type": "contextCompaction"}}},
                {"method": "item/completed", "params": {"threadId": "thread-fixture",
                    "item": {"id": "compact", "type": "contextCompaction"}}},
            ])
            self.compact = False
        self.pending.extend([
            {"method": "item/completed", "params": {"threadId": "thread-fixture",
                "item": {"type": "agentMessage", "text": json.dumps(self.reply)}}},
            {"method": "turn/completed", "params": {"threadId": "thread-fixture",
                "turn": {"id": identity, "status": "completed"}}},
        ])
        return {"turn": {"id": identity}}


def test_same_native_thread_gets_only_each_exact_frame_and_compaction_is_visible(tmp_path):
    wire = ConversationWire(tmp_path / "wire")
    assert wire.conversation_key("episode", "REASONING") is None
    first = state_frame({"goal": {"id": "retained"}, "counter": 1})
    update = state_frame({"goal": {"id": "retained"}, "counter": 2},
                         {"goal": {"id": "retained"}, "counter": 1})
    async def exercise():
        await wire.complete("episode", "REASONING", "fixed", first, {})
        assert wire.conversation_key("episode", "REASONING") == ("thread-fixture", 0)
        wire.compact = True
        await wire.complete("episode", "REASONING", "fixed", update, {})
    asyncio.run(exercise())
    assert len([method for method, _ in wire.sent if method == "thread/start"]) == 1
    dispatched = [params for method, params in wire.sent if method == "turn/start"]
    assert [json.loads(params["input"][0]["text"]) for params in dispatched] == [first, update]
    assert dispatched[0]["threadId"] == dispatched[1]["threadId"]
    assert "goal" not in json.loads(dispatched[1]["input"][0]["text"])["fields"]
    assert wire.conversation_key("episode", "REASONING") == ("thread-fixture", 1)
    assert wire.conversation_key("other-episode", "REASONING") is None
    saved = json.loads((tmp_path / "wire/call-00002/request.json").read_text())
    assert saved["input"] == dispatched[1]["input"]


def test_frame_pixels_are_attached_once_and_lookup_replies_do_not_repeat_them(tmp_path):
    resolved = []
    def resolve(value):
        resolved.append(value)
        return {"type": "localImage", "path": str(tmp_path / "selected.png")}
    wire = ConversationWire(tmp_path / "wire", resolve)
    selected = {"id": "image-fixture"}
    initial = state_frame({"visual_evidence": [selected], "other": "retained"})
    reply = {"version": "decision_context_v1", "kind": "decision_lookup_result",
             "result": {"records": []}}
    async def exercise():
        await wire.complete("episode", "REASONING", "fixed", initial, {})
        await wire.complete("episode", "REASONING", "fixed", reply, {})
    asyncio.run(exercise())
    dispatched = [params for method, params in wire.sent if method == "turn/start"]
    assert len(dispatched[0]["input"]) == 2
    assert len(dispatched[1]["input"]) == 1
    assert resolved == [selected]


def test_connection_key_is_scoped_by_episode_and_role_without_starting_workers(tmp_path):
    connection = ModelConnection(load_config(), tmp_path / "provider", tmp_path)
    assert connection.conversation_key("episode", "REASONING") is None
    wire = ConversationWire(tmp_path / "wire")
    connection.workers[("episode", "REASONING")] = wire
    wire.sessions[("episode", "REASONING")] = ("native-thread", "instructions")
    assert connection.conversation_key("episode", "REASONING") == ("native-thread", 0)
    wire.compaction_epochs[("episode", "REASONING")] = 2
    assert connection.conversation_key("episode", "REASONING") == ("native-thread", 2)
    assert connection.conversation_key("episode", "FAST") is None
    assert connection.conversation_key("child", "REASONING") is None


@pytest.mark.parametrize("value", [None, [], 42, "invalid envelope"])
def test_native_finite_invalid_exchange_value_reaches_runtime_feedback_path(tmp_path, value):
    wire = ConversationWire(tmp_path / "wire")
    wire.reply = value
    result = asyncio.run(wire.complete("episode", "REASONING", "fixed", state_frame({}), {}))
    assert result == value
    assert json.loads((tmp_path / "wire/call-00001/response.json").read_text()) == value


def test_legacy_native_response_still_requires_an_object(tmp_path):
    from gene_annotation_episode.boundary_validation import ModelOutputError
    wire = ConversationWire(tmp_path / "wire")
    wire.reply = None
    with pytest.raises(ModelOutputError, match="must be a JSON object"):
        asyncio.run(wire.complete("episode", "REASONING", "fixed", {"legacy": True}, {}))
