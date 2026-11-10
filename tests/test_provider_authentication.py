"""Account selection cannot silently fall back to another billing identity."""
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.provider_authentication import (
    ProviderAuthenticationError, authentication_policy,
    authentication_transport, verify_authentication)


ACCOUNT = 'intended-oauth-workspace'
POLICY = {'mode': 'chatgpt_oauth', 'account_sha256': hashlib.sha256(ACCOUNT.encode()).hexdigest(),
          'workspace_label': 'Intended workspace'}


def token(account=ACCOUNT):
    payload = {'https://api.openai.com/auth': {'chatgpt_account_id': account}}
    return 'header.'+base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')+'.signature'


class Server:
    def __init__(self):
        self.calls = []
        self.responses = {
            'config/read': {'config': {'model_provider': 'openai'}},
            'account/read': {'account': {'type': 'chatgpt', 'planType': 'business',
                'email': 'private@example.invalid', 'workspaceName': 'Intended workspace'}},
            'getAuthStatus': {'authMethod': 'chatgpt', 'authToken': token()},
        }

    async def rpc(self, method, arguments):
        self.calls.append((method, arguments))
        return deepcopy(self.responses[method])


def test_correct_account_verified_without_retaining_credentials():
    server = Server()
    report = asyncio.run(verify_authentication(server.rpc, POLICY))
    assert report['account_sha256'] == POLICY['account_sha256']
    assert report['verified_before_inference'] is True
    assert report['reported_workspace_name'] == 'Intended workspace'
    assert token() not in json.dumps(report) and 'private@example.invalid' not in json.dumps(report)
    assert [name for name, _ in server.calls] == ['config/read', 'account/read', 'getAuthStatus']


def test_other_oauth_workspace_rejected_before_inference():
    server = Server()
    server.responses['getAuthStatus']['authToken'] = token('AmSC-other-workspace')
    with pytest.raises(ProviderAuthenticationError, match='model_oauth_account_mismatch'):
        asyncio.run(verify_authentication(server.rpc, POLICY))
    assert all(name not in {'turn/start', 'thread/start'} for name, _ in server.calls)


def test_api_key_login_rejected_without_requesting_its_secret():
    server = Server()
    server.responses['account/read'] = {'account': {'type': 'apiKey'}}
    with pytest.raises(ProviderAuthenticationError, match='model_oauth_login_required'):
        asyncio.run(verify_authentication(server.rpc, POLICY))
    assert [name for name, _ in server.calls] == ['config/read', 'account/read']


@pytest.mark.parametrize('configuration', [
    {'model_provider': 'AmSC'},
    {'model_provider': 'openai', 'model_providers': {'openai': {'base_url': 'https://gateway.invalid/v1'}}},
    {'chatgpt_base_url': 'https://gateway.invalid/backend-api'},
    {'model_providers': {'openai': {'env_key': 'OTHER_BILLING_KEY'}}},
    {'model_providers': {'openai': {'http_headers': {'Authorization': 'Bearer fixture-secret'}}}},
])
def test_gateway_and_credential_overrides_rejected(configuration):
    server = Server()
    server.responses['config/read'] = {'config': configuration}
    with pytest.raises(ProviderAuthenticationError, match='model_oauth_provider_route_mismatch'):
        asyncio.run(verify_authentication(server.rpc, POLICY))
    assert len(server.calls) == 1


def test_unidentifiable_token_rejected_without_exposing_it():
    server = Server()
    server.responses['getAuthStatus']['authToken'] = 'not-a-jwt-secret'
    with pytest.raises(ProviderAuthenticationError, match='model_oauth_account_identity_unavailable') as error:
        asyncio.run(verify_authentication(server.rpc, POLICY))
    assert 'not-a-jwt-secret' not in str(error.value)


def test_oauth_transport_clears_api_credentials_only_in_child():
    environment = {'OPENAI_API_KEY': 'private', 'CODEX_API_KEY': 'private',
        'OPENAI_BASE_URL': 'https://gateway.invalid', 'OPENAI_PROJECT_ID': 'other', 'KEEP': 'yes'}
    original = deepcopy(environment)
    command, child = authentication_transport(['codex', 'app-server', '--stdio'], environment, POLICY)
    assert child == {'KEEP': 'yes'} and environment == original
    assert command == ['codex', '-c', 'model_provider="openai"', 'app-server', '--stdio']


def test_invalid_policy_and_unverifiable_transport_rejected():
    with pytest.raises(ProviderAuthenticationError, match='invalid_model_oauth_account_policy'):
        authentication_policy({'authentication': {'mode': 'chatgpt_oauth'}})
    with pytest.raises(ProviderAuthenticationError, match='model_oauth_requires_codex_app_server'):
        authentication_transport(['unverified-provider'], {}, POLICY)


def test_existing_unconfigured_transports_keep_their_original_behavior():
    assert authentication_policy({}) is None
    command, environment = ['original-provider'], {'KEEP': 'yes'}
    assert authentication_transport(command, environment, None) == (command, environment)
    assert asyncio.run(verify_authentication(Server().rpc, None)) is None


def test_wrong_account_stops_owned_provider_through_existing_source_failure_type(tmp_path, monkeypatch):
    from gene_annotation_episode.providers import ModelCallError, _SessionConnection, load_config
    executable = tmp_path/'codex'
    executable.write_bytes(Path(__file__).with_name('provider_wrong_oauth_fixture.py').read_bytes())
    executable.chmod(0o700)
    requests = tmp_path/'request-methods.txt'
    monkeypatch.setenv('AUTH_FIXTURE_REQUEST_LOG', str(requests))
    monkeypatch.setattr('gene_annotation_episode.providers._seed_codex_index', lambda _: [])
    config = load_config()
    config['connection'] = {'command': [str(executable), 'app-server'], 'authentication': POLICY}
    provider = _SessionConnection(config, tmp_path/'provider', tmp_path)
    with pytest.raises(ModelCallError, match='model_oauth_account_mismatch') as error:
        asyncio.run(provider.__aenter__())
    assert error.value.diagnostic['cause_code'] == 'model_oauth_account_mismatch'
    assert provider.process.returncode is not None
    assert 'thread/start' not in requests.read_text() and 'turn/start' not in requests.read_text()
    assert not (tmp_path/'provider'/'authentication.json').exists()
