"""Explicit native failure reaches the caller without a research deadline."""
import asyncio
import json
from pathlib import Path
import sys

import pytest

from gene_annotation_episode.providers import ModelCallError, _SessionConnection, load_config


def connection(path, mode):
    config = load_config()
    config["connection"]["command"] = [sys.executable, "-B",
        str(Path(__file__).with_name("provider_thread_failure_fixture.py")), mode]
    return _SessionConnection(config, path, path.parent)


def test_thread_creation_panic_interrupts_pending_rpc_and_preserves_diagnostic(tmp_path):
    provider = connection(tmp_path / "thread-failure", "thread")
    async def exercise():
        async with provider:
            with pytest.raises(ModelCallError, match="model_provider_thread_creation_failed"):
                await provider._rpc("thread/start", {})
            # The reported panic, not process exit or a timeout, broke the wait.
            assert provider.process.returncode is None
    asyncio.run(exercise())
    assert provider.process.returncode is not None
    assert provider.stderr_reader.done() and provider.stderr.closed
    assert b"failed to spawn thread:" in (provider.directory / "transport-stderr.log").read_bytes()


def test_initialization_panic_is_archived_and_owned_process_is_closed(tmp_path):
    provider = connection(tmp_path / "initialization-failure", "initialize")
    async def exercise():
        with pytest.raises(ModelCallError, match="model_provider_thread_creation_failed"):
            await provider.__aenter__()
    asyncio.run(exercise())
    assert provider.process.returncode is not None
    assert provider.stderr_reader.done() and provider.stderr.closed
    failure = json.loads((provider.directory / "startup-failure.json").read_text())
    assert "model_provider_thread_creation_failed" in failure["error"]
    assert failure["returncode_before_cleanup"] is None
    assert failure["returncode_after_cleanup"] is not None


def test_nonpanic_stderr_does_not_discard_successful_rpc(tmp_path):
    provider = connection(tmp_path / "ordinary-diagnostic", "ordinary")
    async def exercise():
        async with provider:
            assert await provider._rpc("fixture/request", {}) == {"ok": True}
            assert not provider.stderr_failure.done()
    asyncio.run(exercise())
    assert provider.process.returncode is not None
    assert (provider.directory / "transport-stderr.log").read_text() == (
        ("worker warning: failed to spawn thread: retry scheduled\n"
         'worker note: prior "panicked at ... failed to spawn thread:" report was handled\n') * 2)
