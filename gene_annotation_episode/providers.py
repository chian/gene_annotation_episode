"""Structured model calls through the existing authenticated Codex connection.

Each model call uses an admitted ephemeral provider process. The runtime restores
the Episode's authoritative scientific state and history between calls. Models
propose data; method_loop and the workflow own tool execution and numerical
continuation. Scientific credit is not calculated here.
"""

import asyncio
from collections import deque
from collections.abc import Mapping
from contextlib import asynccontextmanager, closing
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import fcntl
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import tomllib

from .boundary_validation import parse_json_object, parse_json_value
from .provider_authentication import (
    ProviderAuthenticationError, authentication_policy,
    authentication_transport, verify_authentication)
from .decision_context import VERSION as DECISION_CONTEXT_VERSION, apply_state_frame
from .infernal_result_presentation import infernal_receiver_context
from .execution_prompt import is_api_launch_context, render_api_launch_prompt
from .scientific_process_prompt import (is_published_scientific_context,
    render_scientific_process_prompt, text_instructions)


class ModelCallError(RuntimeError):
    def __init__(self, *args, diagnostic=None):
        super().__init__(*args)
        self.diagnostic = diagnostic


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

_THREAD_CREATION_PANIC = re.compile(
    rb"(?:^|\n)thread '[^\r\n]+'(?: \([0-9]+\))? panicked at [^\r\n]+:\r?\n"
    rb"failed to spawn thread:")


def _resource_snapshot(budget):
    """Retain observed aggregate task pressure without an admission guess."""
    root = Path('/sys/fs/cgroup') / budget['slice_cgroup'].lstrip('/')
    values = {'observed_at': datetime.now(timezone.utc).isoformat(),
              'slice_cgroup': budget['slice_cgroup']}
    for name in ('pids.current', 'pids.max', 'pids.events',
                 'memory.current', 'memory.events'):
        try:
            raw = (root / name).read_text().strip()
            values[name] = (raw if raw == 'max' else int(raw) if raw.isdecimal() else
                           {key: int(value) for key, value in
                            (line.split() for line in raw.splitlines())})
        except (OSError, ValueError) as error:
            values[name] = {'unavailable': type(error).__name__}
    return values


class _ProviderAdmission:
    """FIFO ownership of one provider process across this workflow's coordinators.

    The ticket lock lasts through the admitted call and native process teardown.
    It does not span an Episode or a scientific child acquisition. A queued
    parent therefore cannot overtake an already queued child. Lock ownership,
    rather than elapsed time, identifies abandoned requests.
    """
    def __init__(self, directory, transport_directory):
        self.directory = directory
        self.transport_directory = transport_directory
        self.ticket = None
        self.ticket_path = None
        self.record = {'requested_at': datetime.now(timezone.utc).isoformat(),
                       'coordinator_pid': os.getpid(),
                       'lifetime': 'one_model_call_through_provider_exit'}

    @asynccontextmanager
    async def _mutex(self):
        with (self.directory / 'queue.lock').open('a') as mutex:
            while True:
                try:
                    fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    # Resource admission only: no Episode action or deadline.
                    await asyncio.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(mutex, fcntl.LOCK_UN)

    def _save(self):
        (self.transport_directory / 'provider-admission.json').write_text(
            json.dumps(self.record, indent=2) + '\n')

    async def acquire(self):
        self._save()
        try:
            async with self._mutex():
                counter = self.directory / 'sequence'
                number = int(counter.read_text()) + 1 if counter.exists() else 1
                temporary = self.directory / ('sequence-' + str(os.getpid()) + '.tmp')
                temporary.write_text(str(number) + '\n')
                temporary.replace(counter)
                self.ticket_path = self.directory / (str(number) + '.request')
                self.ticket = self.ticket_path.open('x+')
                fcntl.flock(self.ticket, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.record['ticket'] = number
                self.ticket.write(json.dumps(self.record) + '\n')
                self.ticket.flush()
            while True:
                async with self._mutex():
                    for path in sorted(self.directory.glob('*.request'),
                                       key=lambda item: int(item.stem)):
                        if path == self.ticket_path:
                            self.record['admitted_at'] = datetime.now(timezone.utc).isoformat()
                            self._save()
                            return
                        try:
                            other = path.open('r+')
                        except FileNotFoundError:
                            continue
                        with other:
                            try:
                                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            except BlockingIOError:
                                break
                            # No coordinator or inherited provider fd owns it.
                            path.unlink(missing_ok=True)
                    else:
                        raise ModelCallError('provider_admission_ticket_missing')
                await asyncio.sleep(0.05)
        except BaseException:
            self.release()
            raise

    def release(self):
        if self.ticket is not None:
            self.ticket_path.unlink(missing_ok=True)
            self.ticket.close()
            self.ticket = None
        self.record['released_at'] = datetime.now(timezone.utc).isoformat()
        self._save()


def _model_process_command(command, environment_bounds):
    """Make the admitted CPU allowance visible to native thread-pool sizing.

    A cgroup CPU quota limits consumed CPU time but leaves all host CPUs in
    sched_getaffinity. Native startup can otherwise create enough threads to
    exhaust this workflow's task allowance before any model turn begins.
    This is a process resource bound, not a research stopping rule.
    """
    allowed = sorted(os.sched_getaffinity(0))
    count = max(1, environment_bounds["cpu_percent"] // 100)
    # Spread separate coordinators over their permitted CPUs; never select
    # a CPU outside an inherited affinity constraint.
    start = os.getpid() % len(allowed)
    selected = (allowed[start:] + allowed[:start])[:count]
    taskset = shutil.which("taskset")
    if taskset is None:
        raise ModelCallError("model_cpu_affinity_tool_unavailable")
    return [taskset, "--cpu-list", ",".join(map(str, selected)), *command], selected


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
        self.authentication_policy = authentication_policy(config['connection'])
        self.authentication = None
        self.roles = {name: ModelRole(**config[name]) for name in ("FAST", "REASONING")}
        self.routing = config["routing"]
        self.directory, self.cwd = directory, cwd.resolve()
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "configuration.json").write_text(json.dumps(config, indent=2))
        self.process = None
        self.stderr = None
        self.stderr_reader = None
        self.stderr_failure = None
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
        self.admission = None

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
        # Catch duplicate transports inside a coordinator, then join the fair
        # run-wide queue. ModelConnection retires this transport after its call,
        # before the runtime can await or commission further scientific work.
        leases=Path(budget['run_directory'])/'provider-locks'
        leases.mkdir(exist_ok=True)
        self.provider_lease=(leases/(str(os.getpid())+'.lock')).open('a')
        try:
            fcntl.flock(self.provider_lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.provider_lease.close();self.provider_lease=None
            raise ModelCallError('single_provider_process_already_active')
        try:
            self.admission = _ProviderAdmission(leases, self.directory)
            await self.admission.acquire()
            self.stderr = (self.directory / "transport-stderr.log").open("wb")
            command = list(self.command)
            environment = dict(os.environ)
            command, environment = authentication_transport(
                command, environment, self.authentication_policy)
            cpu_affinity = None
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
                command, cpu_affinity = _model_process_command(command, budget['environment_bounds'])
            (self.directory/'transport-launch.json').write_text(json.dumps({
                'command':command,'cwd':str(self.cwd),'cpu_affinity':cpu_affinity,
                'provider_admission':dict(self.admission.record),
                'resources_before_start':_resource_snapshot(budget)},indent=2)+'\n')
            self.process = await asyncio.create_subprocess_exec(
                *command, cwd=self.cwd,env=environment,stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=16 * 1024 * 1024,
                start_new_session=True,
                # Preserve resource ownership if the coordinator dies before
                # its provider. The ticket becomes reclaimable on actual exit.
                pass_fds=(self.admission.ticket.fileno(),),
            )
            (self.directory/'transport-started.json').write_text(json.dumps({
                'provider_pid':self.process.pid,
                'resources_after_start':_resource_snapshot(budget)},indent=2)+'\n')
            self.stderr_failure = asyncio.get_running_loop().create_future()
            self.stderr_reader = asyncio.create_task(self._capture_stderr())
            await self._rpc("initialize", {"clientInfo": {
                "name": "gene_annotation_episode", "version": "0.1.0",
            }})
            await self._send({"method": "initialized", "params": {}})
            self.authentication = await verify_authentication(self._rpc, self.authentication_policy)
            if self.authentication is not None:
                (self.directory/'authentication.json').write_text(
                    json.dumps(self.authentication, indent=2)+'\n')
        except BaseException as error:
            failure_resources = _resource_snapshot(budget)
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
                'resources_at_failure':failure_resources,
                'resources_after_cleanup':_resource_snapshot(budget),
            },indent=2)+'\n')
            if isinstance(error, ProviderAuthenticationError):
                raise ModelCallError(str(error), diagnostic={'cause_code': str(error)}) from None
            raise
        return self

    async def __aexit__(self, *exception):
        # A cancellation must not release admission while the owned provider
        # is still alive. Finish transport teardown before propagating it.
        cleanup = asyncio.create_task(self._close_transport())
        cancelled = False
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                cancelled = True
        cleanup.result()
        if cancelled:
            raise asyncio.CancelledError

    async def _close_transport(self):
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
        try:
            if self.stderr_reader is not None:
                await self.stderr_reader
        finally:
            if self.stderr_failure is not None and not self.stderr_failure.done():
                self.stderr_failure.cancel()
            if self.stderr is not None:
                self.stderr.close()
            if self.provider_lease is not None:
                self.provider_lease.close()
                self.provider_lease=None
            if self.admission is not None:
                self.admission.release()
                self.admission=None

    async def _send(self, message):
        self.process.stdin.write((json.dumps(message, allow_nan=False) + "\n").encode())
        await self.process.stdin.drain()

    async def _capture_stderr(self):
        """Preserve native diagnostics and surface the observed startup panic.

        A panicked worker can leave the app-server alive with an unanswered RPC.
        Its explicit thread-creation failure is an execution error. Silence or
        elapsed time does not trigger this path.
        """
        tail = b""
        try:
            while chunk := await self.process.stderr.read(8192):
                self.stderr.write(chunk)
                self.stderr.flush()
                tail = (tail + chunk)[-16384:]
                if _THREAD_CREATION_PANIC.search(tail) and not self.stderr_failure.done():
                    self.stderr_failure.set_result(
                        "model_provider_thread_creation_failed; see transport-stderr.log")
        except (OSError, ValueError) as error:
            if not self.stderr_failure.done():
                self.stderr_failure.set_result("model_provider_stderr_capture_failed: " + str(error))

    async def _read(self):
        if self.stderr_failure is None:
            line = await self.process.stdout.readline()
        else:
            reading = asyncio.create_task(self.process.stdout.readline())
            try:
                await asyncio.wait((reading, self.stderr_failure), return_when=asyncio.FIRST_COMPLETED)
                if self.stderr_failure.done():
                    raise ModelCallError(self.stderr_failure.result())
                line = reading.result()
            finally:
                if not reading.done():
                    reading.cancel()
                await asyncio.gather(reading, return_exceptions=True)
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
                    error = message['error']
                    data = error.get('data') if isinstance(error, Mapping) else None
                    diagnostic = None
                    if isinstance(data, Mapping) and data.get('input_error_code') == 'input_too_large':
                        diagnostic = {'cause_code': 'input_too_large'}
                        for reported, shown in (('actual_chars', 'input_chars'),
                                                ('max_chars', 'provider_max_chars')):
                            if type(data.get(reported)) is int and data[reported] >= 0:
                                diagnostic[shown] = data[reported]
                    raise ModelCallError(f"{method}: {error}", diagnostic=diagnostic)
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
                        error = turn.get('error')
                        diagnostic = ({'cause_code': 'provider_output_incomplete'}
                            if isinstance(error, Mapping) and error.get('message') ==
                                'Incomplete response returned, reason: max_output_tokens'
                            else None)
                        raise ModelCallError(f"Model turn {turn['status']}: {error}",
                            diagnostic=diagnostic)
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
                        "schema. Include every property named in each object's required list. "
                        "A required property whose schema permits null still needs a value: use "
                        "explicit JSON null when that field is unused. Optional tool operands can "
                        "therefore appear as required nullable properties in this response schema. "
                        "Complete the remaining required properties and all closing delimiters, "
                        "then finish the turn. Choose the action and report values from the supplied "
                        "scientific context; this is a response-format repair."}]
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
        from .monitor_prompt import is_monitor_context, render_monitor_prompt
        from .literature_experimental_prompt import (
            is_literature_experimental_context)
        from .component_axis_literature_prompt import (
            render_component_axis_literature_prompt, with_fact_contract_instructions)
        from .rna_structure_comparison_presentation import is_rna_comparison_results_context
        from .rna_structure_presentation import (
            has_rna_structure_receiver_context, is_rna_structure_results_context)
        from .scientific_process_prompt import (
            has_molecular_receiver_context, is_selected_execution_context, render_selected_execution_prompt)

        def has_text_task(value):
            return (is_hpc_context(value) or is_published_scientific_context(value)
                    or is_monitor_context(value)
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
                renderer = render_component_axis_literature_prompt
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
            elif (is_monitor_context(state)
                    and not has_rna_structure_receiver_context(state)
                    and not _rna_comparison_receiver_context(state)
                    and not has_molecular_receiver_context(state)):
                renderer = render_monitor_prompt
            else:
                from .rna_structure_comparison_receiver_prompt import render_rna_comparison_receiver_prompt
                renderer = render_rna_comparison_receiver_prompt
            rendered = renderer(state, instructions, lookup_results=lookups)
            rendered = with_fact_contract_instructions(rendered, state)
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
    """One admitted provider call, retired before scientific execution resumes.

    Native unsubscribe does not unload ephemeral threads. A process per call
    frees the workflow's model slot for another coordinator, including a child.
    The runtime reconstructs authoritative state/history for each fresh native
    conversation; model settings and scientific records remain unchanged.
    """
    session_type = _SessionConnection

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
        for previous in tuple(dict.fromkeys(k[0] for k in self.workers)):
            await self.release(previous)
        self.session_index += 1
        worker = self.session_type(self.config,
            self.directory / f"session-{self.session_index:04}", self.cwd,
            image_resolver=self.image_resolver)
        await worker.__aenter__()
        self.workers[key] = worker
        self.maximum_active_workers = max(self.maximum_active_workers, len(self.workers))
        try:
            return await worker.complete(episode_id, role, instructions, context, output_schema)
        finally:
            await self.release(episode_id)

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
