"""Original provider session/RPC ownership without research stopping gates."""
import asyncio
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
from .boundary_validation import parse_json_object, parse_json_value
from .provider_errors import ModelCallError
from .provider_authentication import (ProviderAuthenticationError,
    authentication_policy, authentication_transport, verify_authentication)
from .model_presentation import ModelPresentation
from .model_transport_resources import (_resource_snapshot, _model_process_command,
    _seed_codex_index, wait_owned_process_group_exit)

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


@dataclass(frozen=True)
class ModelRole:
    model: str
    reasoning_effort: str


class _SessionConnection(ModelPresentation):
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

    def has_session(self, episode_id, role):
        return (episode_id, role) in self.sessions

    def conversation_key(self, episode_id, role):
        """Identify the live conversation and observed context maintenance."""
        key = (episode_id, role)
        session = self.sessions.get(key)
        return None if session is None else (session[0], self.compaction_epochs.get(key, 0))


    async def _start_transport(self, *command, **options):
        """Retain the actual spawn result even when its caller is cancelled."""
        startup = asyncio.create_task(asyncio.create_subprocess_exec(*command, **options))
        interrupted = None
        while not startup.done():
            try:
                await asyncio.shield(startup)
            except (KeyboardInterrupt, asyncio.CancelledError) as error:
                interrupted = error
            except Exception:
                break
        try:
            self.process = startup.result()
        except BaseException as error:
            if interrupted is not None:
                raise interrupted from error
            raise
        if interrupted is not None:
            raise interrupted
        return self.process

    async def __aenter__(self):
        from gene_annotation_episode.workflow_budget import active_budget
        budget=active_budget()
        try:
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
                'resources_before_start':_resource_snapshot(budget)},indent=2)+'\n')
            self.process = await self._start_transport(
                *command, cwd=self.cwd,env=environment,stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=16 * 1024 * 1024,
                start_new_session=True,
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
            natural_returncode = self.process.returncode if self.process is not None else None
            await self.__aexit__(type(error), error, error.__traceback__)
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
        # Complete cleanup before propagating explicit caller cancellation.
        force = bool(exception and exception[0] is not None and
            issubclass(exception[0], (KeyboardInterrupt, asyncio.CancelledError)))
        cleanup = asyncio.create_task(self._close_transport(force=force))
        cancelled = False
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                cancelled = True
                if self.process is not None:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        cleanup.result()
        if cancelled:
            raise asyncio.CancelledError

    async def _close_transport(self, *, force=False):
        if self.process is not None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL if force else signal.SIGTERM)
            except ProcessLookupError:
                pass
            if self.process.returncode is None:
                await self.process.wait()
            await wait_owned_process_group_exit(self.process.pid)
        try:
            if self.stderr_reader is not None:
                await self.stderr_reader
        finally:
            if self.stderr_failure is not None and not self.stderr_failure.done():
                self.stderr_failure.cancel()
            if self.stderr is not None:
                self.stderr.close()

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
        """Collect one actual turn without a usage cutoff or automatic retry."""
        final_text, phases = [], {}
        with (directory / "events.jsonl").open("a") as events:
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
                if method == "turn/completed" and params["turn"]["id"] == turn_id:
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
                       context: dict, output_schema: dict, *,
                       prompt_renderer=None, declared_presenter=None):
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
            if prompt_renderer is None:
                model_text, model_instructions = self._presentation(
                    episode_id, role, instructions, context)
            else:
                presentation = {"module": prompt_renderer.__module__,
                    "qualname": prompt_renderer.__qualname__}
                full_context = (getattr(prompt_renderer, "presentation_protocol", None)
                    == "episode_context_presentation_v1")
                if full_context:
                    presentation["protocol"] = "episode_context_presentation_v1"
                else:
                    presentation["declared_presenter"] = {
                        "module": declared_presenter.__module__,
                        "qualname": declared_presenter.__qualname__}
                request["presentation"] = presentation
                (directory / "request.json").write_text(
                    json.dumps(request, indent=2, allow_nan=False))
                if full_context:
                    model_text, model_instructions = prompt_renderer(
                        self, episode_id, role, instructions, context)
                else:
                    model_text, model_instructions = declared_presenter(
                        self, episode_id, role, instructions, context, prompt_renderer)
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
            turn_request = {"threadId": thread, "model": selected.model,
                "effort": selected.reasoning_effort, "input": turn_input,
                "outputSchema": output_schema}
            prefix = directory / "turn-01"
            prefix.with_suffix(".request.json").write_text(json.dumps(turn_request,
                indent=2, allow_nan=False))
            response = await self._rpc("turn/start", turn_request)
            turn_id = response["turn"]["id"]
            text = await self._collect_turn(thread, turn_id, directory, episode_id, role)
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


_ORIGINAL_SESSION_COMPLETE = _SessionConnection.complete
_ORIGINAL_SESSION_PRESENTATION = _SessionConnection._presentation
