"""Verify an explicitly selected OAuth account before requesting inference.

Authentication failures are terminal transport failures, independent of the
scientific iterator. Credentials never enter the saved authentication report.
"""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


class ProviderAuthenticationError(RuntimeError):
    pass


def authentication_policy(connection):
    value = connection.get('authentication')
    if value is None:
        return None
    if (not isinstance(value, dict)
            or set(value) - {'mode', 'account_sha256', 'workspace_label'}
            or value.get('mode') != 'chatgpt_oauth'
            or not isinstance(value.get('account_sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', value['account_sha256'])
            or not isinstance(value.get('workspace_label', ''), str)):
        raise ProviderAuthenticationError('invalid_model_oauth_account_policy')
    return dict(value)


def authentication_transport(command, environment, policy):
    if policy is None:
        return command, environment
    if Path(command[0]).name not in {'codex', 'codex.exe'} or 'app-server' not in command:
        raise ProviderAuthenticationError('model_oauth_requires_codex_app_server')
    environment = dict(environment)
    for key in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN',
                'OPENAI_BASE_URL', 'OPENAI_ORG_ID', 'OPENAI_ORGANIZATION',
                'OPENAI_PROJECT', 'OPENAI_PROJECT_ID'):
        environment.pop(key, None)
    return [command[0], '-c', 'model_provider="openai"', *command[1:]], environment


def _official_endpoint(value, hosts):
    if value is None:
        return True
    try:
        url = urlsplit(value)
        return (url.scheme == 'https' and url.hostname in hosts
                and url.port in (None, 443) and url.username is None
                and url.password is None and not url.query and not url.fragment)
    except (TypeError, ValueError):
        return False


async def verify_authentication(rpc, policy):
    """Read the actual server identity; never log or retain its bearer token."""
    if policy is None:
        return None
    try:
        response = await rpc('config/read', {'includeLayers': False})
        config = response.get('config') or {}
        provider = config.get('model_provider', config.get('modelProvider')) or 'openai'
        providers = config.get('model_providers', config.get('modelProviders')) or {}
        selected = providers.get('openai') or {}
        credential_headers = {'authorization', 'chatgpt-account-id',
            'openai-organization', 'openai-project', 'x-api-key'}
        header_override = any(str(key).lower() in credential_headers
            for field in ('http_headers', 'env_http_headers')
            for key in (selected.get(field) or {}))
        if (provider != 'openai'
                or not _official_endpoint(selected.get('base_url'), {'api.openai.com'})
                or not _official_endpoint(config.get('chatgpt_base_url'),
                    {'chatgpt.com', 'chat.openai.com'})
                or header_override or any(selected.get(key) for key in (
                    'env_key', 'experimental_bearer_token', 'auth', 'gateway_oauth'))):
            raise ProviderAuthenticationError('model_oauth_provider_route_mismatch')
        response = await rpc('account/read', {'refreshToken': False})
        account = response.get('account') or {}
        if account.get('type') != 'chatgpt':
            raise ProviderAuthenticationError('model_oauth_login_required')
        status = await rpc('getAuthStatus', {'includeToken': True, 'refreshToken': False})
        if status.get('authMethod') not in {'chatgpt', 'chatgptAuthTokens'}:
            raise ProviderAuthenticationError('model_oauth_login_required')
        try:
            encoded = status['authToken'].split('.')[1]
            claims = json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
            account_id = claims['https://api.openai.com/auth']['chatgpt_account_id']
            if not isinstance(account_id, str) or not account_id:
                raise ValueError
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderAuthenticationError('model_oauth_account_identity_unavailable') from None
        actual = hashlib.sha256(account_id.encode()).hexdigest()
        if not hmac.compare_digest(actual, policy['account_sha256']):
            raise ProviderAuthenticationError('model_oauth_account_mismatch')
        return {'version': 'verified_model_oauth_account_v1',
            'auth_mode': 'chatgpt_oauth', 'model_provider': provider,
            'account_sha256': actual, 'workspace_label': policy.get('workspace_label'),
            'reported_workspace_name': account.get('workspaceName'),
            'plan_type': account.get('planType'), 'verified_before_inference': True}
    except ProviderAuthenticationError:
        raise
    except Exception:
        raise ProviderAuthenticationError('model_oauth_identity_verification_failed') from None
