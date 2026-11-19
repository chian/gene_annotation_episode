"""The run's one model provider: the standard ``model_provider`` collaborator.

``ModelProvider`` offers exactly the interface the generic runner checks
(``episode_runtime/collaborators.py``)::

    async complete(episode_id, role, instructions, context, output_schema) -> response

Each call sends ``instructions`` as the conversation's developer instructions,
``context`` as one JSON text input and ``output_schema`` as the strict output
schema, and returns the parsed structured response. It renders no episode
prompt: every binding builds its own instructions and context.

The model endpoint is the Codex app-server over stdio (JSON-RPC, one JSON
message per line). Its configuration is the ``[models]`` table of the packaged
``defaults.toml``, or an equivalent mapping supplied by the caller:

- ``connection.command``: the app-server argv, e.g. ``["codex", "app-server", "--stdio"]``;
- ``connection.authentication`` (optional): ``{mode = "chatgpt_oauth",
  account_sha256 = <64 hex>, workspace_label = <str>}``; when present the
  server's provider route and signed-in ChatGPT account are verified before
  any inference, and API-key variables are removed from its environment;
- one table per role (``FAST``, ``REASONING``): ``{model, reasoning_effort}``;
  the ``role`` argument of ``complete`` names one of them.

``models.routing`` maps a binding's route names to roles; it is binding
configuration and is not read here.

Every call starts its own app-server process inside the caller's workflow
budget (``tools/one_workflow.sh``), opens one ephemeral thread, runs one turn
and retires the process. Calls are serialized: one model process at a time.
Any failure raises ``ModelCallError``; nothing is retried or substituted.
"""
from __future__ import annotations

import asyncio
import base64
from collections.abc import Mapping
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import tomllib
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from gene_annotation_episode.boundary_validation import ModelOutputError, parse_json_value


class ModelCallError(RuntimeError):
    """A model call failed; ``diagnostic`` carries the provider's own cause record when it gave one."""

    def __init__(self, *args, diagnostic=None):
        super().__init__(*args)
        self.diagnostic = diagnostic


class ModelProviderConfigError(ValueError):
    """The supplied model configuration does not have the required form."""


# The model reasons only; the workflow executes every action.
_BASE_INSTRUCTIONS = ('You are a reasoning component. Return the requested structured data. Do not run commands, '
                      'read files, call tools, or delegate. The caller executes every action.')
_NATIVE_TOOLS_DISABLED = {
    'features.shell_tool': False, 'features.multi_agent': False, 'features.apps': False, 'features.plugins': False,
    'features.browser_use': False, 'features.computer_use': False, 'features.image_generation': False,
    'features.view_image': False, 'features.sleep_tool': False, 'features.skip_host_skill_discovery': True,
    'features.memories': False, 'features.external_agent_memory_import': False,
    'features.daemon_auto_start': False, 'web_search': 'disabled',
    'mcp_servers.openaiDeveloperDocs.enabled': False}
_CONVERSATION_ITEMS = frozenset({'userMessage', 'agentMessage', 'reasoning', 'contextCompaction'})
_CREDENTIAL_VARIABLES = ('OPENAI_API_KEY', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN', 'OPENAI_BASE_URL', 'OPENAI_ORG_ID',
                         'OPENAI_ORGANIZATION', 'OPENAI_PROJECT', 'OPENAI_PROJECT_ID')
_CREDENTIAL_HEADERS = frozenset({'authorization', 'chatgpt-account-id', 'openai-organization', 'openai-project',
                                 'x-api-key'})
_ROUTING_KEY = 'routing'


def default_config_path():
    """The packaged configuration file holding the ``[models]`` table."""
    return Path(__file__).with_name('defaults.toml')


def load_config(path=None):
    """The ``[models]`` table of ``path`` (the packaged ``defaults.toml`` when not given)."""
    return tomllib.loads(Path(default_config_path() if path is None else path).read_text())['models']


def _non_empty_text(value):
    return isinstance(value, str) and bool(value.strip())


def _authentication_policy(connection):
    if 'authentication' not in connection:
        return None
    value = connection['authentication']
    if (not isinstance(value, Mapping) or set(value) - {'mode', 'account_sha256', 'workspace_label'}
            or value.get('mode') != 'chatgpt_oauth'
            or not isinstance(value.get('account_sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', value['account_sha256'])
            or not isinstance(value.get('workspace_label', ''), str)):
        raise ModelProviderConfigError('invalid_model_oauth_account_policy')
    return dict(value)


def _is_codex_app_server(command):
    return Path(command[0]).name in {'codex', 'codex.exe'} and 'app-server' in command


def _parse_config(config):
    if not isinstance(config, Mapping):
        raise ModelProviderConfigError('model_config_must_be_a_mapping')
    connection = config.get('connection')
    if not isinstance(connection, Mapping) or set(connection) - {'command', 'authentication'}:
        raise ModelProviderConfigError('model_config_connection_invalid')
    command = connection.get('command')
    if (not isinstance(command, (list, tuple)) or not command
            or not all(_non_empty_text(part) for part in command)):
        raise ModelProviderConfigError('model_config_connection_command_invalid')
    command = tuple(command)
    if not _is_codex_app_server(command):
        raise ModelProviderConfigError('model_config_connection_must_be_codex_app_server')
    authentication = _authentication_policy(connection)
    roles = {}
    for name, table in config.items():
        if name in ('connection', _ROUTING_KEY):
            continue
        if (not isinstance(table, Mapping) or set(table) != {'model', 'reasoning_effort'}
                or not _non_empty_text(table['model']) or not _non_empty_text(table['reasoning_effort'])):
            raise ModelProviderConfigError('model_config_role_invalid:' + str(name))
        roles[name] = (table['model'], table['reasoning_effort'])
    if not roles:
        raise ModelProviderConfigError('model_config_has_no_roles')
    return command, authentication, roles


def _official_endpoint(value, hosts):
    if value is None:
        return True
    try:
        url = urlsplit(value)
        return (url.scheme == 'https' and url.hostname in hosts and url.port in (None, 443)
                and url.username is None and url.password is None and not url.query and not url.fragment)
    except (TypeError, ValueError):
        return False


class ModelProvider:
    """The standard ``model_provider`` collaborator over the Codex app-server.

    ``directory`` is created (it must not exist) and receives one subdirectory
    per call with its request, transport events, stderr and response or error.
    ``cwd`` is the working directory the model process is started in.
    """

    def __init__(self, config, directory, cwd):
        self._command, self._authentication, self._roles = _parse_config(config)
        self._config = json.loads(json.dumps(dict(config), allow_nan=False))
        self._directory = Path(directory)
        self._cwd = Path(cwd).resolve()
        if not self._cwd.is_dir():
            raise ModelProviderConfigError('model_provider_cwd_not_a_directory')
        self._directory.mkdir(parents=True, exist_ok=False)
        (self._directory / 'configuration.json').write_text(json.dumps(self._config, indent=2) + '\n')
        self._calls = 0
        self._serial = asyncio.Lock()

    @property
    def roles(self):
        """Role name -> ``{'model', 'reasoning_effort'}`` as configured."""
        return {name: {'model': model, 'reasoning_effort': effort} for name, (model, effort) in self._roles.items()}

    def _check_arguments(self, episode_id, role, instructions, context, output_schema):
        if not _non_empty_text(episode_id):
            raise ValueError('model_call_episode_id_required')
        if role not in self._roles:
            raise ValueError('model_call_unknown_role:' + str(role))
        if not _non_empty_text(instructions):
            raise ValueError('model_call_instructions_required')
        if not isinstance(context, Mapping):
            raise TypeError('model_call_context_must_be_a_mapping')
        if not isinstance(output_schema, Mapping) or output_schema.get('type') != 'object':
            raise ValueError('model_call_output_schema_must_describe_an_object')
        try:
            Draft202012Validator.check_schema(output_schema)
        except SchemaError as error:
            raise ValueError('model_call_output_schema_invalid: ' + error.message) from None
        try:
            context_text = json.dumps(context, allow_nan=False)
            schema = json.loads(json.dumps(output_schema, allow_nan=False))
        except (TypeError, ValueError) as error:
            raise ValueError('model_call_arguments_not_json: ' + str(error)) from None
        return context_text, schema

    async def complete(self, episode_id, role, instructions, context, output_schema):
        """Send ``instructions``, ``context`` and the strict ``output_schema``; return the parsed response."""
        context_text, schema = self._check_arguments(episode_id, role, instructions, context, output_schema)
        async with self._serial:
            self._calls += 1
            directory = self._directory / f'call-{self._calls:05}'
            directory.mkdir()
            model, effort = self._roles[role]
            request = {'episode_id': episode_id, 'role': role, 'model': model, 'reasoning_effort': effort,
                       'instructions': instructions, 'context': json.loads(context_text), 'output_schema': schema,
                       'started_at': datetime.now(timezone.utc).isoformat()}
            (directory / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
            try:
                async with _AppServer(self._command, self._authentication, directory, self._cwd) as server:
                    text = await server.structured_turn(model, effort, instructions, context_text, schema)
                (directory / 'response.txt').write_text(text)
                try:
                    response = parse_json_value(text)
                except ModelOutputError as error:
                    raise ModelCallError('model_response_not_json: ' + str(error),
                                         diagnostic={'cause_code': error.category}) from None
                if not isinstance(response, dict):
                    raise ModelCallError('model_response_not_an_object')
                (directory / 'response.json').write_text(json.dumps(response, indent=2) + '\n')
                return response
            except BaseException as error:
                (directory / 'error.json').write_text(json.dumps(
                    {'error': type(error).__name__, 'message': str(error),
                     'diagnostic': getattr(error, 'diagnostic', None)}, indent=2) + '\n')
                raise


class _AppServer:
    """One Codex app-server process for one call, inside the caller's workflow budget."""

    def __init__(self, command, authentication, directory, cwd):
        self._command, self._authentication = command, authentication
        self._directory, self._cwd = directory, cwd
        self._process = self._stderr = self._stderr_reader = self._events = None
        self._pending = []
        self._request_id = 0

    def _launch_command(self):
        from gene_annotation_episode.workflow_budget import active_budget
        budget = active_budget()
        sqlite_home = (self._directory / 'sqlite').resolve()
        log_dir = (self._directory / 'logs').resolve()
        sqlite_home.mkdir(mode=0o700)
        log_dir.mkdir(mode=0o700)
        environment = dict(os.environ)
        environment['CODEX_SQLITE_HOME'] = str(sqlite_home)
        source = Path(os.environ.get('CODEX_SQLITE_HOME') or os.environ.get('CODEX_HOME')
                      or Path.home() / '.codex').expanduser().resolve()
        # A consistent read-only copy of the existing index, so the server does not rescan every rollout.
        for index in sorted(source.glob('state_*.sqlite')):
            with closing(sqlite3.connect(index.as_uri() + '?mode=ro', uri=True)) as reader:
                with closing(sqlite3.connect(sqlite_home / index.name)) as writer:
                    reader.backup(writer)
        options = ['-c', 'sqlite_home=' + json.dumps(str(sqlite_home)), '-c', 'log_dir=' + json.dumps(str(log_dir))]
        options += [part for key, value in _NATIVE_TOOLS_DISABLED.items() for part in ('-c', key + '=' + json.dumps(value))]
        if self._authentication is not None:
            for name in _CREDENTIAL_VARIABLES:
                environment.pop(name, None)
            options += ['-c', 'model_provider="openai"']
        command = [self._command[0], *options, *self._command[1:]]
        # The CPU quota leaves every host CPU in the affinity mask; native thread pools size from that mask.
        taskset = shutil.which('taskset')
        if taskset is None:
            raise ModelCallError('model_cpu_affinity_tool_unavailable')
        allowed = sorted(os.sched_getaffinity(0))
        count = max(1, budget['environment_bounds']['cpu_percent'] // 100)
        start = os.getpid() % len(allowed)
        cpus = (allowed[start:] + allowed[:start])[:count]
        return [taskset, '--cpu-list', ','.join(map(str, cpus)), *command], environment

    async def __aenter__(self):
        try:
            command, environment = self._launch_command()
            (self._directory / 'transport-launch.json').write_text(
                json.dumps({'command': command, 'cwd': str(self._cwd)}, indent=2) + '\n')
            self._stderr = (self._directory / 'transport-stderr.log').open('wb')
            self._events = (self._directory / 'events.jsonl').open('a')
            self._process = await asyncio.create_subprocess_exec(
                *command, cwd=self._cwd, env=environment, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=16 * 1024 * 1024,
                start_new_session=True)
            self._stderr_reader = asyncio.create_task(self._capture_stderr())
            await self._rpc('initialize', {'clientInfo': {'name': 'gene_annotation_episode', 'version': '0.1.0'}})
            await self._send({'method': 'initialized', 'params': {}})
            if self._authentication is not None:
                verified = await self._verify_authentication()
                (self._directory / 'authentication.json').write_text(json.dumps(verified, indent=2) + '\n')
        except BaseException:
            await self._close()
            raise
        return self

    async def __aexit__(self, *exception):
        await self._close()

    async def _close(self):
        closing_task = asyncio.ensure_future(self._shutdown())
        cancelled = False
        while not closing_task.done():
            try:
                await asyncio.shield(closing_task)
            except asyncio.CancelledError:
                cancelled = True
        closing_task.result()
        if cancelled:
            raise asyncio.CancelledError

    async def _shutdown(self):
        if self._process is not None:
            if self._process.stdin is not None and not self._process.stdin.is_closing():
                self._process.stdin.close()
            try:
                os.killpg(self._process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            await self._process.wait()
            try:
                os.killpg(self._process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if self._stderr_reader is not None:
            await self._stderr_reader
        for handle in (self._stderr, self._events):
            if handle is not None:
                handle.close()

    async def _capture_stderr(self):
        while chunk := await self._process.stderr.read(8192):
            self._stderr.write(chunk)
            self._stderr.flush()

    async def _send(self, message):
        self._process.stdin.write((json.dumps(message, allow_nan=False) + '\n').encode())
        await self._process.stdin.drain()

    async def _read(self):
        line = await self._process.stdout.readline()
        if not line:
            raise ModelCallError('model_transport_closed; see transport-stderr.log')
        message = json.loads(line)
        self._events.write(json.dumps(message) + '\n')
        self._events.flush()
        return message

    async def _rpc(self, method, params):
        self._request_id += 1
        identity = self._request_id
        await self._send({'id': identity, 'method': method, 'params': params})
        while True:
            message = await self._read()
            if message.get('id') == identity and 'method' not in message:
                if 'error' in message:
                    error = message['error']
                    data = error.get('data') if isinstance(error, Mapping) else None
                    diagnostic = None
                    if isinstance(data, Mapping) and data.get('input_error_code') == 'input_too_large':
                        diagnostic = {'cause_code': 'input_too_large'}
                        for reported, shown in (('actual_chars', 'input_chars'), ('max_chars', 'provider_max_chars')):
                            if type(data.get(reported)) is int and data[reported] >= 0:
                                diagnostic[shown] = data[reported]
                    raise ModelCallError(f'{method}: {error}', diagnostic=diagnostic)
                return message['result']
            self._pending.append(message)

    async def _verify_authentication(self):
        """Read the server's provider route and signed-in account; never retain its token."""
        config = (await self._rpc('config/read', {'includeLayers': False})).get('config') or {}
        provider = config.get('model_provider', config.get('modelProvider')) or 'openai'
        selected = (config.get('model_providers', config.get('modelProviders')) or {}).get('openai') or {}
        header_override = any(str(key).lower() in _CREDENTIAL_HEADERS for field in ('http_headers', 'env_http_headers')
                              for key in (selected.get(field) or {}))
        if (provider != 'openai' or header_override
                or not _official_endpoint(selected.get('base_url'), {'api.openai.com'})
                or not _official_endpoint(config.get('chatgpt_base_url'), {'chatgpt.com', 'chat.openai.com'})
                or any(selected.get(key) for key in ('env_key', 'experimental_bearer_token', 'auth', 'gateway_oauth'))):
            raise ModelCallError('model_oauth_provider_route_mismatch')
        account = (await self._rpc('account/read', {'refreshToken': False})).get('account') or {}
        if account.get('type') != 'chatgpt':
            raise ModelCallError('model_oauth_login_required')
        status = await self._rpc('getAuthStatus', {'includeToken': True, 'refreshToken': False})
        if status.get('authMethod') not in {'chatgpt', 'chatgptAuthTokens'}:
            raise ModelCallError('model_oauth_login_required')
        try:
            encoded = status['authToken'].split('.')[1]
            claims = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
            account_id = claims['https://api.openai.com/auth']['chatgpt_account_id']
            if not isinstance(account_id, str) or not account_id:
                raise ValueError
        except (KeyError, IndexError, TypeError, ValueError):
            raise ModelCallError('model_oauth_account_identity_unavailable') from None
        actual = hashlib.sha256(account_id.encode()).hexdigest()
        if not hmac.compare_digest(actual, self._authentication['account_sha256']):
            raise ModelCallError('model_oauth_account_mismatch')
        return {'auth_mode': 'chatgpt_oauth', 'model_provider': provider, 'account_sha256': actual,
                'workspace_label': self._authentication.get('workspace_label'),
                'reported_workspace_name': account.get('workspaceName'), 'plan_type': account.get('planType'),
                'verified_before_inference': True}

    async def structured_turn(self, model, effort, instructions, context_text, schema):
        """One ephemeral thread, one turn under ``schema``; the final agent message text."""
        started = await self._rpc('thread/start', {
            'model': model, 'cwd': str(self._cwd), 'ephemeral': True, 'approvalPolicy': 'never',
            'sandbox': 'read-only', 'config': {'model_reasoning_effort': effort, **_NATIVE_TOOLS_DISABLED},
            'baseInstructions': _BASE_INSTRUCTIONS, 'developerInstructions': instructions})
        if started.get('model') != model:
            raise ModelCallError(f"model_mismatch: requested {model}; server selected {started.get('model')}")
        if started.get('reasoningEffort') != effort:
            raise ModelCallError(f"reasoning_effort_mismatch: requested {effort}; "
                                 f"server selected {started.get('reasoningEffort')}")
        thread = started['thread']['id']
        turn = await self._rpc('turn/start', {'threadId': thread, 'model': model, 'effort': effort,
                                              'input': [{'type': 'text', 'text': context_text}],
                                              'outputSchema': schema})
        turn_id = turn['turn']['id']
        final_text = []
        while True:
            event = self._pending.pop(0) if self._pending else await self._read()
            params = event.get('params') or {}
            if params.get('threadId') != thread:
                continue
            if 'id' in event and 'method' in event:
                await self._send({'id': event['id'], 'error': {'code': -32601,
                                                               'message': 'Only structured reasoning is bound here'}})
                raise ModelCallError('model_side_request: ' + str(event['method']))
            if params.get('turnId', turn_id) != turn_id:
                continue
            method = event.get('method')
            if method in ('item/started', 'item/completed'):
                item = params.get('item') or {}
                kind = item.get('type')
                if kind not in _CONVERSATION_ITEMS:
                    await self._rpc('turn/interrupt', {'threadId': thread, 'turnId': turn_id})
                    raise ModelCallError('model_attempted_action: ' + str(kind))
                if kind == 'agentMessage' and method == 'item/completed' and item.get('phase') != 'commentary':
                    final_text.append(item.get('text', ''))
            elif method == 'turn/completed' and params['turn']['id'] == turn_id:
                completed = params['turn']
                if completed['status'] != 'completed':
                    error = completed.get('error')
                    diagnostic = ({'cause_code': 'provider_output_incomplete'} if isinstance(error, Mapping)
                                  and error.get('message') == 'Incomplete response returned, reason: max_output_tokens'
                                  else None)
                    raise ModelCallError(f"model_turn_{completed['status']}: {error}", diagnostic=diagnostic)
                if not final_text:
                    raise ModelCallError('model_turn_returned_no_final_message')
                return '\n'.join(final_text)


__all__ = ['ModelCallError', 'ModelProvider', 'ModelProviderConfigError', 'default_config_path', 'load_config']
