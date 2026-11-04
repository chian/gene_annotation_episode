"""Addgene login and native page acquisition using private credential references.

Authentication responses and cookie values stay in memory. The scientific GET
retains its original response with credential-bearing headers omitted.
"""
from __future__ import annotations

import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request

from .acquisition import AcquisitionError, PublicClients, SourceSnapshot, _now
from .addgene_sequence_native import _Page
from .credentials import CredentialError, credential_reference, resolve_credential


ORIGIN = "https://www.addgene.org"
_PRIVATE_HEADERS = {"set-cookie", "set-cookie2", "authorization", "proxy-authorization"}


def configured_addgene_credential():
    """An absent configuration keeps the existing public-page operation."""
    try:
        return credential_reference("addgene", ORIGIN)
    except CredentialError as error:
        if str(error) == "credential_unavailable":
            return None
        raise AcquisitionError("addgene_credential_configuration_invalid", phase="http_request") from None


def _page(raw):
    parser = _Page()
    try:
        parser.feed(raw.decode("utf-8-sig"))
        parser.close()
    except (UnicodeError, ValueError, AssertionError):
        raise AcquisitionError("addgene_authentication_page_invalid", phase="http_response") from None
    return parser


class _ScopedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        parts = urllib.parse.urlsplit(url)
        if (parts.scheme != "https" or parts.hostname != "www.addgene.org"
                or parts.port not in (None, 443) or parts.username is not None
                or parts.password is not None):
            raise AcquisitionError("addgene_authentication_redirect_out_of_scope", phase="http_response")
        return super().redirect_request(request, response, code, message, headers, url)


def acquire_addgene_sequences(client, identifier, *, max_bytes, reference):
    """Authenticate privately, then perform the original selected scientific GET.

    There is one login attempt and no data retry, provider fallback or record
    selection. The existing native page reader remains the scientific parser.
    """
    try:
        credential = resolve_credential(reference, service="addgene", endpoint=ORIGIN)
        username, password = credential.field("username"), credential.field("password")
    except CredentialError:
        raise AcquisitionError("addgene_credentials_unavailable", phase="http_request") from None
    target = ORIGIN + "/" + identifier + "/sequences/"
    next_path = urllib.parse.urlsplit(target).path
    login = ORIGIN + "/users/login/?" + urllib.parse.urlencode({"next": next_path})
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), _ScopedRedirect())
    public_headers = {"User-Agent": "gene-annotation-episode/0.2", "Accept": "text/html"}

    def fetch(url, *, form=None, limit=1048576):
        headers = dict(public_headers)
        if form is not None:
            headers.update({"Content-Type": "application/x-www-form-urlencoded",
                "Origin": ORIGIN, "Referer": login})
        request = urllib.request.Request(url, headers=headers,
            data=None if form is None else urllib.parse.urlencode(form).encode())
        try:
            response = opener.open(request, timeout=client.timeout)
        except urllib.error.HTTPError as error:
            response = error
        except AcquisitionError:
            raise
        except Exception:
            raise AcquisitionError("addgene_connection_failed", phase="http_request") from None
        try:
            with response:
                body, capture, failure = PublicClients._read_bounded_response(response, limit)
                status, effective = response.code, response.geturl()
                headers = [(key, value) for key, value in response.headers.items()
                    if key.lower() not in _PRIVATE_HEADERS]
                redacted = sorted({key.lower() for key in response.headers
                    if key.lower() in _PRIVATE_HEADERS})
        except Exception:
            raise AcquisitionError("addgene_response_unavailable", phase="http_response") from None
        return body, status, effective, headers, redacted, capture, failure

    body, status, _, _, _, capture, failure = fetch(login)
    if status != 200 or failure is not None or not capture["body_complete"]:
        raise AcquisitionError("addgene_login_page_unavailable", phase="http_response")
    forms = [node for node in _page(body).nodes
        if node["tag"] == "form" and node["attrs"].get("id") == "login-form"]
    if len(forms) != 1 or (forms[0]["attrs"].get("method") or "").lower() != "post":
        raise AcquisitionError("addgene_login_form_unavailable", phase="http_response")
    action = urllib.parse.urljoin(login, forms[0]["attrs"].get("action") or login)
    action_parts = urllib.parse.urlsplit(action)
    if (action_parts.scheme != "https" or action_parts.hostname != "www.addgene.org"
            or action_parts.port not in (None, 443) or action_parts.username is not None
            or action_parts.password is not None):
        raise AcquisitionError("addgene_login_form_out_of_scope", phase="http_response")
    pending, fields, names = list(forms[0]["children"]), {}, set()
    while pending:
        node = pending.pop()
        pending.extend(node["children"])
        if node["tag"] == "input" and node["attrs"].get("name"):
            name = node["attrs"]["name"]
            names.add(name)
            if node["attrs"].get("type") == "hidden":
                fields[name] = node["attrs"].get("value", "")
    if not {"username", "password", "csrfmiddlewaretoken"} <= names:
        raise AcquisitionError("addgene_login_form_unavailable", phase="http_response")
    fields.update(username=username, password=password, next=next_path)
    if "cart_next" in fields:
        fields["cart_next"] = ""
    body, status, _, _, _, capture, failure = fetch(action, form=fields)
    if (status != 200 or failure is not None or not capture["body_complete"]
            or any(node["tag"] == "form" and node["attrs"].get("id") == "login-form"
                for node in _page(body).nodes)):
        raise AcquisitionError("addgene_authentication_failed", phase="http_response")

    body, status, effective, headers, redacted, capture, failure = fetch(target, limit=max_bytes)
    # CSRF nonces are form data, not authentication cookies. Passwords and
    # session-cookie values must never enter retained native bodies or headers.
    secrets = [password, *(cookie.value for cookie in jar
        if "csrf" not in cookie.name.lower() and len(cookie.value) >= 16)]
    retained_text = [effective, *(value for _, value in headers)]
    if any(secret.encode() in body or any(secret in value for value in retained_text)
            for secret in secrets):
        raise AcquisitionError("addgene_credential_echo_rejected", phase="http_response")
    metadata = {"status": status, "representation": "http_response_bytes",
        "headers": {key.lower(): value for key, value in headers if key.lower() in
            {"etag", "last-modified", "content-type", "retry-after", "link"}},
        "header_items": headers, "redacted_header_names": redacted,
        "effective_url": effective,
        "request": {"method": "GET", "url": target, "headers": public_headers},
        "authentication": {"scheme": "cookie_session", "credential_value_retained": False},
        "authentication_steps": ["login_form", "credential_submission"], **capture}
    snapshot = SourceSnapshot("addgene", target, {}, _now(), body, "text/html", metadata)
    if not 200 <= status < 300:
        raise AcquisitionError("provider_http_" + str(status), snapshot=snapshot, phase="http_response")
    if failure is not None:
        raise AcquisitionError(failure, snapshot=snapshot, phase="http_response")
    return snapshot
