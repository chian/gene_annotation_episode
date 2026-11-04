"""Structured model calls through the existing authenticated Codex connection.

One ephemeral conversation per Episode/role keeps histories and model settings
separate. Models propose data; method_loop and the workflow own tool execution
and numerical continuation. Scientific credit is not calculated here.
"""

import asyncio
from collections import deque
from collections.abc import Mapping
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import fcntl
import os
from pathlib import Path
import signal
import sqlite3
import tomllib

from .boundary_validation import parse_json_object, parse_json_value
from .decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame
from .infernal_result_presentation import infernal_receiver_context
from .execution_prompt import is_api_launch_context, render_api_launch_prompt
from .scientific_process_prompt import (is_published_scientific_context,
    render_scientific_process_prompt, text_instructions)


class ModelCallError(RuntimeError):
    pass


class _StructuredWhitespaceStall(ModelCallError):
    def __init__(self, text):
        super().__init__("Structured response emitted 4096 consecutive whitespace characters outside strings")
        self.text = text


_NATIVE_TOOLS_DISABLED = {
    'features.shell_tool':False,'features.multi_agent':False,
    'features.apps':False,'features.plugins':False,
    'features.browser_use':False,'features.computer_use':False,
    'features.image_generation':False,'features.view_image':False,
    'features.sleep_tool':False,'features.skip_host_skill_discovery':True,
    'features.memories':False,'features.external_agent_memory_import':False,
    'features.daemon_auto_start':False,
    'web_search':'disabled','mcp_servers.openaiDeveloperDocs.enabled':False,
}


def _seed_codex_index(directory):
    """Take a consistent read-only index snapshot; never rescan all rollouts."""
    original = Path(os.environ.get('CODEX_SQLITE_HOME') or
        os.environ.get('CODEX_HOME') or Path.home()/'.codex').expanduser().resolve()
    copied = []
    for source in sorted(original.glob('state_*.sqlite')):
        destination = directory/source.name
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as reader:
            with closing(sqlite3.connect(destination)) as writer:
                reader.backup(writer)
        copied.append({'source':str(source),'snapshot':str(destination),
            'bytes':destination.stat().st_size})
    return copied


def _rna_comparison_receiver_context(value):
    """Recognize the supplied receiving capability before its first child return.

    ExecutionEpisodes supplies this field only to annotation/scientific
    receivers. Starting their general text TASK while the group is empty keeps
    both frame reconstruction and fixed conversation instructions stable when
    an actual RNA result later arrives. This does not select or invent a result.
    """
    from .rna_structure_comparison_views import PROJECTION_SOURCE
    if not isinstance(value, Mapping) or 'received_rna_comparison_values' not in value:
        return False
    groups = value['received_rna_comparison_values']
    return isinstance(groups, list) and all(
        isinstance(group, Mapping) and set(group) == {'fact_source', 'facts'}
        and group['fact_source'] == PROJECTION_SOURCE and isinstance(group['facts'], list)
        for group in groups)


def _ordinary_runtime_receiver_context(value):
    """Recognize the existing ordinary decision view, not a protocol frame."""
    if not isinstance(value, Mapping):
        return False
    goal, scope, working, tools = (value.get(name) for name in ("goal", "scope", "working_state", "tools"))
    return (isinstance(goal, Mapping) and isinstance(goal.get("objective"), str)
        and bool(goal["objective"].strip()) and isinstance(scope, Mapping)
        and isinstance(scope.get("subject_refs"), (list, tuple))
        and isinstance(working, Mapping) and isinstance(working.get("subjects"), (list, tuple))
        and isinstance(working.get("scope"), Mapping) and working["scope"] == scope
        and isinstance(tools, (list, tuple)) and all(isinstance(tool, Mapping)
            and isinstance(tool.get("name"), str) and bool(tool["name"]) for tool in tools)
        and "requested_form" in value and (value["requested_form"] is None or isinstance(value["requested_form"], Mapping))
        and isinstance(value.get("controller"), Mapping)
        and isinstance(value.get("current_report_update"), Mapping) and "last_local_outcome" in value)


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
        self.compaction_epochs = {}
        # One current authoritative presentation state, never an action history.
        # New bootstrap frames replace it after restart or native compaction.
        self.scientific_prompt_states = {}
        self.provider_lease = None

    def has_session(self, episode_id, role):
        return (episode_id, role) in self.sessions

    def conversation_key(self, episode_id, role):
        """Identify the live conversation and observed context maintenance."""
        key = (episode_id, role)
        session = self.sessions.get(key)
        return None if session is None else (session[0], self.compaction_epochs.get(key, 0))


    async def __aenter__(self):
        from .workflow_budget import active_budget
        budget=active_budget()
        # A durable child has its own coordinator while the parent waits for
        # its result. They share the workflow cgroup, not a model connection.
        # A workflow-wide lease here prevents every durable child from ever
        # obtaining its first response. Retain one provider per coordinator;
        # the launcher owns admission and aggregate limits for the whole tree.
        leases=Path(budget['run_directory'])/'provider-locks'
        leases.mkdir(exist_ok=True)
        self.provider_lease=(leases/(str(os.getpid())+'.lock')).open('a')
        try:
            fcntl.flock(self.provider_lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.provider_lease.close();self.provider_lease=None
            raise ModelCallError('single_provider_process_already_active')
        try:
            self.stderr = (self.directory / "transport-stderr.log").open("w")
            command = list(self.command)
            environment = dict(os.environ)
            if Path(command[0]).name in {'codex','codex.exe'} and 'app-server' in command:
                sqlite_directory = (self.directory/'sqlite').resolve()
                log_directory = (self.directory/'logs').resolve()
                sqlite_directory.mkdir(mode=0o700);log_directory.mkdir(mode=0o700)
                # Reuse authentication, but keep writable batch state separate
                # from interactive databases and within this workflow's caps.
                command = [command[0],'-c','sqlite_home='+json.dumps(str(sqlite_directory)),
                    '-c','log_dir='+json.dumps(str(log_directory)),
                    *[part for key,value in _NATIVE_TOOLS_DISABLED.items()
                        for part in ('-c',key+'='+json.dumps(value))],*command[1:]]
                environment['CODEX_SQLITE_HOME'] = str(sqlite_directory)
                (self.directory/'sqlite-index-snapshot.json').write_text(json.dumps(
                    _seed_codex_index(sqlite_directory),indent=2)+'\n')
            (self.directory/'transport-launch.json').write_text(json.dumps({
                'command':command,'cwd':str(self.cwd)},indent=2)+'\n')
            self.process = await asyncio.create_subprocess_exec(
                *command, cwd=self.cwd,env=environment,stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=self.stderr, limit=16 * 1024 * 1024,
                start_new_session=True,
            )
            await self._rpc("initialize", {"clientInfo": {
                "name": "gene_annotation_episode", "version": "0.1.0",
            }})
            await self._send({"method": "initialized", "params": {}})
        except BaseException as error:
            natural_returncode = None
            if self.process is not None:
                try:
                    natural_returncode = await asyncio.wait_for(self.process.wait(),.25)
                except asyncio.TimeoutError:
                    pass
            await self.__aexit__(None, None, None)
            (self.directory/'startup-failure.json').write_text(json.dumps({
                'error':type(error).__name__+': '+str(error),
                'returncode_before_cleanup':natural_returncode,
                'returncode_after_cleanup':self.process.returncode if self.process is not None else None,
            },indent=2)+'\n')
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
        if self.provider_lease is not None:
            self.provider_lease.close()
            self.provider_lease=None

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
        config = {'model_reasoning_effort':selected.reasoning_effort,**_NATIVE_TOOLS_DISABLED}
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
        self.compaction_epochs.setdefault(key, 0)
        self.session_index += 1
        (self.directory / f"session-{self.session_index:03}.json").write_text(json.dumps({
            "episode_id": episode_id, "role": role, "model": selected.model,
            "effort": selected.reasoning_effort, "thread_id": thread,
            "server_model": response.get("model"),
            "server_effort": response.get("reasoningEffort"),
        }, indent=2))
        return thread

    async def _collect_turn(self, thread, turn_id, directory, episode_id, role):
        """Collect one turn; reject a stalled stream without repairing its JSON."""
        final_text, streams, phases, lexical = [], {}, {}, {}
        stalled = False
        interrupt_deadline = None
        with (directory / "events.jsonl").open("a") as events:
            while True:
                remaining = (None if interrupt_deadline is None else
                    interrupt_deadline - asyncio.get_running_loop().time())
                if remaining is not None and remaining <= 0:
                    raise ModelCallError("Timed out waiting for interrupted structured response")
                event = (self.pending.popleft() if self.pending else
                    await asyncio.wait_for(self._read(), remaining))
                events.write(json.dumps(event) + "\n")
                events.flush()
                params = event.get("params", {})
                if params.get("threadId") != thread:
                    continue
                if "id" in event and "method" in event:
                    await self._send({"id": event["id"], "error": {
                        "code": -32601, "message": "Only structured reasoning is bound here"}})
                    raise ModelCallError(f"Unexpected model-side request: {event['method']}")
                if params.get("turnId", turn_id) != turn_id:
                    continue
                method = event.get("method")
                if method in ("item/started", "item/completed"):
                    item = params.get("item", {})
                    kind = item.get("type")
                    if kind not in ("userMessage", "agentMessage", "reasoning", "contextCompaction"):
                        await self._rpc("turn/interrupt", {"threadId": thread, "turnId": turn_id})
                        raise ModelCallError(f"Model attempted {kind}; workflow owns execution")
                    if method == "item/completed" and kind == "contextCompaction":
                        key = (episode_id, role)
                        self.compaction_epochs[key] = self.compaction_epochs.get(key, 0) + 1
                    if kind == "agentMessage":
                        phases[item.get("id")] = item.get("phase")
                        if method == "item/completed" and item.get("phase") != "commentary":
                            final_text.append(item.get("text", ""))
                if method == "item/agentMessage/delta" and phases.get(params.get("itemId")) != "commentary":
                    item_id, delta = params.get("itemId"), params.get("delta", "")
                    streams.setdefault(item_id, []).append(delta)
                    quoted, escaped, whitespace = lexical.get(item_id, (False, False, 0))
                    for character in delta:
                        if quoted:
                            whitespace = 0
                            if escaped:
                                escaped = False
                            elif character == "\\":
                                escaped = True
                            elif character == '"':
                                quoted = False
                        elif character == '"':
                            quoted, whitespace = True, 0
                        elif character in " \t\r\n":
                            whitespace += 1
                        else:
                            whitespace = 0
                    lexical[item_id] = (quoted, escaped, whitespace)
                    if not stalled and whitespace >= 4096:
                        stalled = True
                        await asyncio.wait_for(self._rpc("turn/interrupt",
                            {"threadId": thread, "turnId": turn_id}), 30)
                        interrupt_deadline = asyncio.get_running_loop().time() + 30
                if method == "turn/completed" and params["turn"]["id"] == turn_id:
                    if stalled:
                        raise _StructuredWhitespaceStall("\n".join(
                            "".join(parts) for parts in streams.values()))
                    turn = params["turn"]
                    if turn["status"] != "completed":
                        raise ModelCallError(f"Model turn {turn['status']}: {turn.get('error')}")
                    return "\n".join(final_text)

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
            model_text, model_instructions = self._presentation(
                episode_id, role, instructions, context)
            turn_input = [{"type": "text", "text": model_text}]
            # Decision state frames carry changed fields explicitly. Attach
            # pixels only when that frame actually supplies the selected view;
            # lookup replies do not repeat prior multimodal input.
            image_context = context
            if (context.get("version") == "decision_context_v1"
                    and context.get("kind") in {"decision_bootstrap", "decision_update"}):
                image_context = context["fields"]
            for selected_image in image_context.get("visual_evidence", []):
                if self.image_resolver is None:
                    raise ModelCallError("Selected image has no bound artifact resolver")
                turn_input.append(self.image_resolver(selected_image))
            # Record the exact actual multimodal inputs before model dispatch.
            # Paths point only to content-addressed, verified local artifacts.
            request["input"] = turn_input
            # Keep original instructions/context for reconstruction and record
            # the exact text supplied at the native conversation boundary.
            if model_instructions != instructions:
                request["model_instructions"] = model_instructions
            (directory / "request.json").write_text(json.dumps(request, indent=2, allow_nan=False))
            thread = await self._session(episode_id, role, model_instructions)
            for attempt in range(2):
                turn_request = {"threadId": thread, "model": selected.model,
                    "effort": selected.reasoning_effort, "input": turn_input,
                    "outputSchema": output_schema}
                prefix = directory / f"turn-{attempt + 1:02}"
                prefix.with_suffix(".request.json").write_text(json.dumps(turn_request,
                    indent=2, allow_nan=False))
                response = await self._rpc("turn/start", turn_request)
                turn_id = response["turn"]["id"]
                try:
                    text = await self._collect_turn(thread, turn_id, directory, episode_id, role)
                    break
                except _StructuredWhitespaceStall as error:
                    prefix.with_suffix(".incomplete.txt").write_text(error.text)
                    prefix.with_suffix(".failure.json").write_text(json.dumps({
                        "code": "structured_whitespace_stall", "thread_id": thread,
                        "turn_id": turn_id, "format_retry_available": attempt == 0,
                        "characters_retained": len(error.text), "action_executed": False,
                    }, indent=2))
                    if attempt:
                        raise
                    turn_input = [{"type": "text", "text":
                        "Your previous turn did not finish its structured response and was interrupted "
                        "after repeatedly emitting whitespace. No action from that turn was executed. "
                        "Return your selected response as one complete JSON value matching the supplied "
                        "schema, including all closing delimiters, and finish the turn."}]
            (directory / "response.txt").write_text(text)
            # The decision exchange journal must retain a finite but invalid
            # envelope (including JSON null) so the runtime can give structured
            # feedback inside the same decision. Legacy callers still require
            # an object. Malformed, duplicate-key and nonfinite JSON stay errors.
            parser = (parse_json_value if context.get("version") == "decision_context_v1"
                      else parse_json_object)
            result = parser(text)
            (directory / "response.json").write_text(json.dumps(result, indent=2))
            return result
        except BaseException as error:
            (directory / "error.json").write_text(json.dumps({
                "error": type(error).__name__, "message": str(error),
                "thread_id": thread, "turn_id": turn_id,
            }, indent=2))
            raise

    def _presentation(self, episode_id, role, instructions, context):
        """Render declared TASKs from reconstructed state; preserve other inputs."""
        from .hpc_prompt import is_hpc_context, render_hpc_prompt
        from .literature_experimental_prompt import (
            is_literature_experimental_context, render_literature_experimental_prompt)
        from .rna_structure_comparison_presentation import is_rna_comparison_results_context
        from .rna_structure_presentation import (
            has_rna_structure_receiver_context, is_rna_structure_results_context)
        from .scientific_process_prompt import (
            has_molecular_receiver_context, is_selected_execution_context, render_selected_execution_prompt)

        def has_text_task(value):
            return (is_hpc_context(value) or is_published_scientific_context(value)
                    or is_api_launch_context(value)
                    or is_literature_experimental_context(value)
                    or is_rna_comparison_results_context(value)
                    or is_rna_structure_results_context(value)
                    or has_rna_structure_receiver_context(value)
                    or _rna_comparison_receiver_context(value)
                    or has_molecular_receiver_context(value)
                    or is_selected_execution_context(value)
                    or _ordinary_runtime_receiver_context(value))

        key = (episode_id, role)
        previous = self.scientific_prompt_states.get(key)
        state = None
        lookups = []
        if context.get("version") == DECISION_CONTEXT_VERSION:
            kind = context.get("kind")
            if kind == "decision_bootstrap":
                if has_text_task(context.get("fields")):
                    state = apply_state_frame(None, context)
                    lookups = [row["lookup_result"] for row in
                        context.get("restored_public_exchanges", ()) if "lookup_result" in row]
                else:
                    self.scientific_prompt_states.pop(key, None)
            elif kind == "decision_update" and previous is not None:
                state = apply_state_frame(previous, context)
            elif kind == "decision_update" and has_text_task(context.get("fields")):
                # A delta cannot establish the missing task/base state.
                state = apply_state_frame(None, context)
            elif kind == "decision_lookup_result" and previous is not None:
                state = previous
                lookups = [context.get("result")]
                if previous.get('contract_information_profile') == 'operation_contract_information_v1':
                    lookups = list(context.get('pending_contract_information', ()))
                    if context.get('result') not in lookups:
                        lookups.append(context.get('result'))
        elif has_text_task(context):
            # The legacy exchange protocol can carry a newly published process.
            # It already supplies the full state; its response schema is intact.
            state = deepcopy(context)
        if state is not None and has_text_task(state):
            if is_hpc_context(state):
                renderer = render_hpc_prompt
            elif is_literature_experimental_context(state):
                renderer = render_literature_experimental_prompt
            elif is_published_scientific_context(state):
                renderer = render_scientific_process_prompt
            elif is_api_launch_context(state):
                renderer = render_api_launch_prompt
            elif is_rna_comparison_results_context(state):
                from .rna_structure_comparison_prompt import render_rna_comparison_results_prompt
                renderer = render_rna_comparison_results_prompt
            elif is_rna_structure_results_context(state):
                from .rna_structure_prompt import render_rna_structure_results_prompt
                renderer = render_rna_structure_results_prompt
            elif (is_selected_execution_context(state)
                    and not has_rna_structure_receiver_context(state)
                    and not _rna_comparison_receiver_context(state)):
                renderer = render_selected_execution_prompt
            else:
                from .rna_structure_comparison_receiver_prompt import render_rna_comparison_receiver_prompt
                renderer = render_rna_comparison_receiver_prompt
            rendered = renderer(state, instructions, lookup_results=lookups)
            self.scientific_prompt_states[key] = state
            return rendered, text_instructions(instructions)
        if state is not None:
            self.scientific_prompt_states.pop(key, None)
        # Legacy full contexts need the same received-result projection as
        # model_snapshot. Framed contexts were projected before their hashes
        # were computed; do not rewrite a frame or its revision here.
        presented = (context if context.get("version") == DECISION_CONTEXT_VERSION
                     else infernal_receiver_context(context))
        return json.dumps(presented, allow_nan=False), instructions


class ModelConnection:
    """One live provider per coordinator; retire it when switching episodes.

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
        self.worker_lock=asyncio.Lock()

    @property
    def sessions(self):
        return {key: value for worker in self.workers.values() for key, value in worker.sessions.items()}

    def has_session(self, episode_id, role):
        return (episode_id, role) in self.workers

    def conversation_key(self, episode_id, role):
        worker = self.workers.get((episode_id, role))
        return None if worker is None else worker.conversation_key(episode_id, role)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exception):
        for episode_id in tuple(dict.fromkeys(key[0] for key in self.workers)):
            await self.release(episode_id)

    async def complete(self, episode_id, role, instructions, context, output_schema):
        async with self.worker_lock:
            return await self._complete_serial(episode_id,role,instructions,context,output_schema)

    async def _complete_serial(self, episode_id, role, instructions, context, output_schema):
        key = (episode_id, role)
        if key not in self.workers:
            for previous in tuple(dict.fromkeys(k[0] for k in self.workers)):
                await self.release(previous)
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
            worker.compaction_epochs.clear()
            worker.scientific_prompt_states.clear()
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
        async with self.worker_lock:
            for previous in tuple(dict.fromkeys(k[0] for k in self.workers)):
                await self.release(previous)
            async with _SessionConnection(self.config, self.directory / "catalog", self.cwd) as worker:
                return await worker.catalog()


def default_config_path():
    """The single packaged default; callers can supply their own full config."""
    return Path(__file__).with_name("defaults.toml")


def load_config(path=None):
    if path is None:
        path = default_config_path()
    return tomllib.loads(Path(path).read_text())["models"]
