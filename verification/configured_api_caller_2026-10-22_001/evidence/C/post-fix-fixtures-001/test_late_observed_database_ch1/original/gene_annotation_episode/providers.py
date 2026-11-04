"""Structured model calls through the existing authenticated Codex connection.

One ephemeral conversation per Episode/role keeps histories and model settings
separate. Models propose data; method_loop and the workflow own tool execution
and numerical continuation. Scientific credit is not calculated here.
"""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import tomllib

from .boundary_validation import parse_json_object


class ModelCallError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelRole:
    model: str
    reasoning_effort: str


class _SessionConnection:
    def __init__(self, config: dict, directory: Path, cwd: Path, *, image_resolver=None):
        self.command = config["connection"]["command"]
        self.roles = {name: ModelRole(**config[name]) for name in ("FAST", "REASONING")}
        self.routing = config["routing"]
        self.directory, self.cwd = directory, cwd.resolve()
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "configuration.json").write_text(json.dumps(config, indent=2))
        self.process = None
        self.stderr = None
        self.pending = deque()
        self.request_index = 0
        self.call_index = 0
        self.sessions = {}
        self.session_index = 0
        self.retirement_index = 0
        self.image_resolver = image_resolver

    def has_session(self, episode_id, role):
        return (episode_id, role) in self.sessions


    async def __aenter__(self):
        self.stderr = (self.directory / "transport-stderr.log").open("w")
        self.process = await asyncio.create_subprocess_exec(
            *self.command, cwd=self.cwd, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=self.stderr, limit=16 * 1024 * 1024,
            start_new_session=True,
        )
        try:
            await self._rpc("initialize", {"clientInfo": {
                "name": "gene_annotation_episode", "version": "0.1.0",
            }})
            await self._send({"method": "initialized", "params": {}})
        except BaseException:
            await self.__aexit__(None, None, None)
            raise
        return self

    async def __aexit__(self, *exception):
        if self.process is not None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                if self.process.returncode is None:
                    await asyncio.wait_for(self.process.wait(), 3)
            except asyncio.TimeoutError:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await self.process.wait()
            finally:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if self.stderr is not None:
            self.stderr.close()

    async def _send(self, message):
        self.process.stdin.write((json.dumps(message, allow_nan=False) + "\n").encode())
        await self.process.stdin.drain()

    async def _read(self):
        line = await self.process.stdout.readline()
        if not line:
            raise ModelCallError("Codex transport closed; see transport-stderr.log")
        return json.loads(line)

    async def _rpc(self, method, params):
        self.request_index += 1
        identity = self.request_index
        await self._send({"id": identity, "method": method, "params": params})
        while True:
            message = await self._read()
            if message.get("id") == identity and "method" not in message:
                if "error" in message:
                    raise ModelCallError(f"{method}: {message['error']}")
                return message["result"]
            self.pending.append(message)

    async def catalog(self):
        models = []
        cursor = None
        while True:
            params = {"includeHidden": True, "limit": 100}
            if cursor is not None:
                params["cursor"] = cursor
            response = await self._rpc("model/list", params)
            models.extend(response["data"])
            cursor = response.get("nextCursor")
            if cursor is None:
                break
        selected = [{key: item.get(key) for key in
                     ("model", "supportedReasoningEfforts", "defaultReasoningEffort", "inputModalities")}
                    for item in models if item.get("model") in
                    {role.model for role in self.roles.values()}]
        (self.directory / "catalog.json").write_text(json.dumps(selected, indent=2))
        return selected

    async def _session(self, episode_id, role, instructions):
        key = (episode_id, role)
        if key in self.sessions:
            thread, original_instructions = self.sessions[key]
            if original_instructions != instructions:
                raise ValueError("Episode model instructions are fixed for its conversation")
            return thread
        selected = self.roles[role]
        # Per-thread overrides leave the user's own Codex configuration intact.
        # Native coding/research tools are disabled: the workflow executes its
        # declared scientific tools after a model proposes the next action.
        config = {
            "model_reasoning_effort": selected.reasoning_effort,
            "features.shell_tool": False, "features.multi_agent": False,
            "features.apps": False, "features.plugins": False,
            "features.browser_use": False, "features.computer_use": False,
            "features.image_generation": False, "features.view_image": False,
            "features.sleep_tool": False, "features.skip_host_skill_discovery": True,
            "web_search": "disabled", "mcp_servers.openaiDeveloperDocs.enabled": False,
        }
        response = await self._rpc("thread/start", {
            "model": selected.model, "cwd": str(self.cwd),
            "ephemeral": True, "approvalPolicy": "never", "sandbox": "read-only",
            "config": config,
            "baseInstructions": "You are a scientific reasoning component. Return the requested structured data. "
                "Do not run commands, read files, call tools, or delegate. The caller executes scientific actions.",
            "developerInstructions": instructions,
        })
        if response.get("model") != selected.model:
            raise ModelCallError(f"Requested {selected.model}; server selected {response.get('model')}")
        if response.get("reasoningEffort") != selected.reasoning_effort:
            raise ModelCallError(
                f"Requested effort {selected.reasoning_effort}; "
                f"server selected {response.get('reasoningEffort')}"
            )
        thread = response["thread"]["id"]
        self.sessions[key] = (thread, instructions)
        self.session_index += 1
        (self.directory / f"session-{self.session_index:03}.json").write_text(json.dumps({
            "episode_id": episode_id, "role": role, "model": selected.model,
            "effort": selected.reasoning_effort, "thread_id": thread,
            "server_model": response.get("model"),
            "server_effort": response.get("reasoningEffort"),
        }, indent=2))
        return thread

    async def complete(self, episode_id: str, role: str, instructions: str,
                       context: dict, output_schema: dict):
        self.call_index += 1
        directory = self.directory / f"call-{self.call_index:05}"
        directory.mkdir()
        selected = self.roles[role]
        request = {"episode_id": episode_id, "role": role, "model": selected.model,
                   "effort": selected.reasoning_effort, "instructions": instructions,
                   "context": context, "output_schema": output_schema,
                   "started_at": datetime.now(timezone.utc).isoformat()}
        (directory / "request.json").write_text(json.dumps(request, indent=2, allow_nan=False))
        turn_id = thread = None
        try:
            turn_input = [{"type": "text", "text": json.dumps(context, allow_nan=False)}]
            for selected_image in context.get("visual_evidence", []):
                if self.image_resolver is None:
                    raise ModelCallError("Selected image has no bound artifact resolver")
                turn_input.append(self.image_resolver(selected_image))
            # Record the exact actual multimodal inputs before model dispatch.
            # Paths point only to content-addressed, verified local artifacts.
            request["input"] = turn_input
            (directory / "request.json").write_text(json.dumps(request, indent=2, allow_nan=False))
            thread = await self._session(episode_id, role, instructions)
            response = await self._rpc("turn/start", {
                "threadId": thread, "model": selected.model, "effort": selected.reasoning_effort,
                "input": turn_input,
                "outputSchema": output_schema,
            })
            turn_id = response["turn"]["id"]
            final_text = []
            with (directory / "events.jsonl").open("w") as events:
                while True:
                    event = self.pending.popleft() if self.pending else await self._read()
                    events.write(json.dumps(event) + "\n")
                    events.flush()
                    params = event.get("params", {})
                    if params.get("threadId") != thread:
                        continue
                    if "id" in event and "method" in event:
                        await self._send({"id": event["id"], "error": {
                            "code": -32601, "message": "Only structured reasoning is bound here"}})
                        raise ModelCallError(f"Unexpected model-side request: {event['method']}")
                    if event.get("method") in ("item/started", "item/completed"):
                        item = params.get("item", {})
                        kind = item.get("type")
                        # The local app-server protocol declares contextCompaction
                        # as internal thread maintenance, not a tool/acquisition.
                        # It stays in the event log and contributes no response text.
                        if kind not in ("userMessage", "agentMessage", "reasoning", "contextCompaction"):
                            await self._rpc("turn/interrupt", {"threadId": thread, "turnId": turn_id})
                            raise ModelCallError(f"Model attempted {kind}; workflow owns execution")
                        if event["method"] == "item/completed" and kind == "agentMessage":
                            if item.get("phase") != "commentary":
                                final_text.append(item.get("text", ""))
                    if event.get("method") == "turn/completed" and params["turn"]["id"] == turn_id:
                        turn = params["turn"]
                        if turn["status"] != "completed":
                            raise ModelCallError(f"Model turn {turn['status']}: {turn.get('error')}")
                        break
            text = "\n".join(final_text)
            (directory / "response.txt").write_text(text)
            result = parse_json_object(text)
            (directory / "response.json").write_text(json.dumps(result, indent=2))
            return result
        except BaseException as error:
            (directory / "error.json").write_text(json.dumps({
                "error": type(error).__name__, "message": str(error),
                "thread_id": thread, "turn_id": turn_id,
            }, indent=2))
            raise


class ModelConnection:
    """One owned provider process per active episode/role; none for closed ones.

    Native unsubscribe does not unload ephemeral threads. A dedicated process
    makes retirement explicit without retaining another closed conversation.
    Parent conversation restoration uses the visible records already on disk.
    """

    def __init__(self, config, directory, cwd, *, image_resolver=None):
        self.config, self.directory, self.cwd = config, Path(directory), Path(cwd)
        self.roles = {name: ModelRole(**config[name]) for name in ("FAST", "REASONING")}
        self.routing = config["routing"]
        self.directory.mkdir(parents=True, exist_ok=False)
        (self.directory / "configuration.json").write_text(json.dumps(config, indent=2))
        self.workers = {}
        self.session_index = 0
        self.retirement_index = 0
        self.maximum_active_workers = 0
        self.image_resolver = image_resolver

    @property
    def sessions(self):
        return {key: value for worker in self.workers.values() for key, value in worker.sessions.items()}

    def has_session(self, episode_id, role):
        return (episode_id, role) in self.workers

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exception):
        for episode_id in tuple(dict.fromkeys(key[0] for key in self.workers)):
            await self.release(episode_id)

    async def complete(self, episode_id, role, instructions, context, output_schema):
        key = (episode_id, role)
        if key not in self.workers:
            self.session_index += 1
            worker = _SessionConnection(self.config,
                self.directory / f"session-{self.session_index:04}", self.cwd,
                image_resolver=self.image_resolver)
            await worker.__aenter__()
            self.workers[key] = worker
            self.maximum_active_workers = max(self.maximum_active_workers, len(self.workers))
        return await self.workers[key].complete(episode_id, role, instructions, context, output_schema)

    async def release(self, episode_id):
        for key in [key for key in self.workers if key[0] == episode_id]:
            worker = self.workers.pop(key)
            pid = worker.process.pid
            await worker.__aexit__(None, None, None)
            worker.sessions.clear()
            worker.pending.clear()
            self.retirement_index += 1
            target = self.directory / "retired-sessions"
            target.mkdir(exist_ok=True)
            (target / f"retired-{self.retirement_index:05}.json").write_text(json.dumps({
                "episode_id": episode_id, "role": key[1], "provider_process": pid,
                "provider_exit_code": worker.process.returncode,
                "local_session_removed": True, "remaining_active_workers": len(self.workers),
                "maximum_active_workers": self.maximum_active_workers,
            }, indent=2))

    async def catalog(self):
        async with _SessionConnection(self.config, self.directory / "catalog", self.cwd) as worker:
            return await worker.catalog()


def default_config_path():
    """The single packaged default; callers can supply their own full config."""
    return Path(__file__).with_name("defaults.toml")


def load_config(path=None):
    if path is None:
        path = default_config_path()
    return tomllib.loads(Path(path).read_text())["models"]
