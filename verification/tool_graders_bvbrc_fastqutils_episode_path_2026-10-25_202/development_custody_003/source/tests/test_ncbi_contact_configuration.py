"""Persistent NCBI contact reaches real client ports; no external requests."""
import asyncio
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import time

import pytest
import requests

from gene_annotation_episode import acquisition
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.api_blast import NCBIBlastService
from gene_annotation_episode.public_configuration import (
    configured_tools, ncbi_contact, public_config_path, save_ncbi_contact)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools


EMAIL = "synthetic-contact@example.invalid"


@pytest.fixture(autouse=True)
def isolated_contact(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path/"user-config"))
    monkeypatch.delenv("NCBI_EMAIL", raising=False)


def test_persistent_contact_survives_a_new_process_and_obeys_precedence(tmp_path, monkeypatch):
    assert ncbi_contact() is None
    path = save_ncbi_contact(EMAIL)
    assert path == public_config_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    code = "from gene_annotation_episode.acquisition import PublicClients; import json; print(json.dumps(PublicClients().ncbi_email))"
    assert json.loads(subprocess.check_output([sys.executable, "-c", code], text=True)) == EMAIL
    monkeypatch.setenv("NCBI_EMAIL", "environment@example.invalid")
    assert PublicClients().ncbi_email == "environment@example.invalid"
    assert PublicClients(ncbi_email="caller@example.invalid").ncbi_email == "caller@example.invalid"
    assert PublicClients(ncbi_email=None).ncbi_email is None


def test_fresh_registry_freezes_contact_for_both_api_ports_and_worker_reopening(tmp_path, monkeypatch):
    save_ncbi_contact(EMAIL)
    configuration = {"public": {"provider_access_dir": str(tmp_path/"access")}}
    original = deepcopy(configuration)
    with Store(tmp_path/"workspace") as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        tools = build_tools(store, configuration)
        saved = json.loads(json.dumps(tools.reconstruction_configuration))
        assert configuration == original
        assert tools.clients.ncbi_email == EMAIL
        assert NCBIBlastService(tools).client is tools.clients
        assert saved["public"]["ncbi_email"] == EMAIL
    # A separately reconstructed worker receives the saved operand, not a new
    # environment/default lookup. The same saved null also remains absent.
    save_ncbi_contact("new-default@example.invalid")
    monkeypatch.setenv("NCBI_EMAIL", "different-worker@example.invalid")
    with Store(tmp_path/"workspace") as store:
        reopened = build_tools(store, saved)
        assert reopened.clients.ncbi_email == EMAIL
        service = NCBIBlastService(reopened)
        assert service.client.ncbi_email == EMAIL
        assert all(row["configuration"]["ncbi_contact_configured"]
                   for row in service.capabilities())
        absent = build_tools(store, {"public": {"ncbi_email": None}})
        assert absent.clients.ncbi_email is None
        assert absent.reconstruction_configuration["public"]["ncbi_email"] is None


def test_fixed_case_preparation_freezes_contact_without_changing_supplied_configuration(tmp_path):
    from gene_annotation_episode.case_execution import prepare_case_run
    from test_case_execution import prepared
    save_ncbi_contact(EMAIL)
    case, configuration, _ = prepared(tmp_path)
    original = deepcopy(configuration)
    manifest = prepare_case_run(case, tmp_path/"run", configuration)
    assert manifest["configuration"]["public"]["ncbi_email"] == EMAIL
    assert configuration == original
    with Store(manifest["configuration"]["workspace"]) as store:
        tools = build_tools(store, manifest["configuration"])
        assert tools.reconstruction_configuration == manifest["configuration"]


@pytest.mark.parametrize("path", ["root_tool", "api_episode_port"])
def test_persisted_contact_and_tool_identity_reach_actual_installed_http_requests(tmp_path, monkeypatch, path):
    """Run installed BLAST primitives with captured, synthetic HTTP responses."""
    save_ncbi_contact(EMAIL)
    calls = []
    clock = [1000.]
    def advancing_clock():
        clock[0] += 61.
        return clock[0]
    monkeypatch.setattr(time, "time", advancing_clock)

    def http(session, method, url, **kwargs):
        calls.append((method, kwargs))
        data = kwargs.get("data") or kwargs.get("params")
        assert data["email"] == EMAIL
        assert data["tool"] == "gene-annotation-episode"
        response = requests.Response()
        response.status_code = 200
        if data["CMD"] == "Put":
            body = b"RID = SYNTHETIC_CONTACT_RID\nRTOE = 0\n"
        elif data.get("FORMAT_OBJECT") == "SearchInfo":
            body = b"Status=READY\nThereAreHits=no\n"
        else:
            body = json.dumps({"BlastOutput2": [{"report": {"program": "blastp",
                "results": {"search": {"query_len": 8, "hits": []}}}}]}).encode()
        response._content = body
        response.url = url
        response.headers["Content-Type"] = "text/plain"
        response.request = requests.Request(method, url, data=kwargs.get("data"), params=kwargs.get("params")).prepare()
        return response
    monkeypatch.setattr(requests.Session, "request", http)

    def in_process_worker(command, *, input, text, capture_output, timeout):
        old_arguments, old_input = sys.argv, sys.stdin
        output = io.StringIO()
        try:
            sys.argv = ["-c", *command[3:]]
            sys.stdin = io.StringIO(input)
            with contextlib.redirect_stdout(output):
                exec(compile(command[2], "<controlled-blast-worker>", "exec"), {"__name__": "__main__"})
        finally:
            sys.argv, sys.stdin = old_arguments, old_input
            monkeypatch.setattr(requests.Session, "request", http)
        return subprocess.CompletedProcess(command, 0, output.getvalue(), "")
    monkeypatch.setattr(acquisition.subprocess, "run", in_process_worker)
    with Store(tmp_path/"workspace") as store:
        subject = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"][0]
        tools = build_tools(store, {"public": {"provider_access_dir": str(tmp_path/"access")}})
        request = {"subject_ref": subject, "program": "blastp", "database": "swissprot"}
        if path == "root_tool":
            result = asyncio.run(tools.execute_async("public.blast.search", request))
            assert result["status"] == "completed", result
            assert len(calls) == 3
        else:
            service = NCBIBlastService(tools)
            prepared = service.prepare("api.blast.submit", request, {},
                scope=store.validate_scope(None), previous_events=[])
            result = service.decode(prepared, service.invoke(prepared))
            assert result["native_handle"]["rid"] == "SYNTHETIC_CONTACT_RID"
            assert len(calls) == 1


def test_saved_missing_contact_does_not_adopt_a_later_default(tmp_path):
    saved = configured_tools()
    assert saved["public"]["ncbi_email"] is None
    save_ncbi_contact(EMAIL)
    assert configured_tools(saved) == saved
    assert configured_tools()["public"]["ncbi_email"] == EMAIL


def test_independent_worker_restores_original_contact_before_provider_entry(tmp_path, monkeypatch):
    from gene_annotation_episode import tool_configuration
    from gene_annotation_episode.independent_execution import open_commission
    from gene_annotation_episode.providers import ModelConnection
    from test_episode_reconstruction import fixture_commission
    save_ncbi_contact(EMAIL)
    spec, run, _, turns = fixture_commission(tmp_path)
    saved = spec['runtime_binding']['arguments']['tool_configuration']
    assert saved['public']['ncbi_email'] == EMAIL
    frozen_manifest = (run/'case-launch.json').read_bytes()
    save_ncbi_contact('changed-user-default@example.invalid')
    monkeypatch.setenv('NCBI_EMAIL', 'changed-worker-environment@example.invalid')
    observed = []
    original_build = tool_configuration.build_tools

    def build(store, configuration):
        tools = original_build(store, configuration)
        observed.append(tools.clients.ncbi_email)
        assert NCBIBlastService(tools).client.ncbi_email == EMAIL
        return tools

    class BeforeProviderTransport(Exception):
        pass

    async def before_transport(provider):
        raise BeforeProviderTransport

    monkeypatch.setattr(tool_configuration, 'build_tools', build)
    monkeypatch.setattr(ModelConnection, '__aenter__', before_transport)
    async def reopen():
        async with open_commission(spec):
            pytest.fail('No model or episode execution belongs to this check')
    with pytest.raises(BeforeProviderTransport):
        asyncio.run(reopen())
    assert observed == [EMAIL]
    assert (run/'case-launch.json').read_bytes() == frozen_manifest
    assert not turns.exists()
