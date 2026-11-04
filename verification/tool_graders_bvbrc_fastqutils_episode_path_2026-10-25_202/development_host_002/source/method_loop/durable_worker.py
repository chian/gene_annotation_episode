"""Bootstrap exactly one commissioned ordinary Episode in a fresh process.

The C1 factory is ``factory_module:factory_name(spec)`` returning an async
context manager. Its value can be a mapping with keys ``episode``, ``context``,
``pack_result`` or an object exposing those attributes. No parent closure is
serialized. The binding owns revalidation of saved inputs/code/configuration,
the scientific ClosedRecord projection, and release of its own resources.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import importlib
import inspect
import os
import secrets
import signal
import sys
import traceback

from .archive import JsonArchive
from .durable import (DurableExecutionError, DurableExecutionStore, canonical,
                      content_digest, process_identity, utc_now, validate_commission, validate_return,
                      _archive_descriptor, _references)
from .episode import Context, Episode, EpisodeCompletion, _require_closed_record


def _member(runtime, name):
    return runtime[name] if isinstance(runtime, Mapping) else getattr(runtime, name)


def _diagnostic(store, error):
    record = JsonArchive(store.archive_directory).store({
        "version": "episode_execution_diagnostic_v1", "observed_at": utc_now(),
        "exception_type": type(error).__name__, "traceback": traceback.format_exc()})
    return str(record.path)


async def execute_commission(store, handle, execution_token):
    """Run one already-claimed execution; never launch a root or retry work."""
    with store._connect() as db:
        reservation = store._row(db, handle)
    identity, live = process_identity()
    if (live != "live" or reservation["execution_identity"] != canonical(identity)
            or not secrets.compare_digest(reservation["execution_token"], execution_token)
            or reservation["return_id"] is not None):
        raise DurableExecutionError("identity_conflict", affected_refs=[handle])
    spec = validate_commission(store.load_commission(handle))
    digest = content_digest(spec)
    record = result = None
    closed = {"completion": None, "episode_archive": None, "result_archive": None,
              "form": None, "facts_archive": None, "pending_handles": []}
    outcome, failure, stage = "execution_failed", None, "factory"
    try:
        binding = spec["runtime_binding"]
        try:
            factory = importlib.import_module(binding["factory_module"])
            for name in binding["factory_name"].split("."):
                factory = getattr(factory, name)
        except (ImportError, AttributeError) as error:
            raise DurableExecutionError("unavailable_binding", affected_refs=[handle]) from error
        if not callable(factory):
            raise DurableExecutionError("unavailable_binding", affected_refs=[handle])
        try:
            manager = factory(spec)
        except TypeError as error:
            raise DurableExecutionError("unavailable_binding", affected_refs=[handle]) from error
        if inspect.isawaitable(manager):
            manager = await manager
        if not hasattr(manager, "__aenter__") or not hasattr(manager, "__aexit__"):
            raise DurableExecutionError("unavailable_binding", affected_refs=[handle])
        async with manager as runtime:
            try:
                episode, context, pack_result = (_member(runtime, name)
                    for name in ("episode", "context", "pack_result"))
            except (AttributeError, KeyError, TypeError) as error:
                raise DurableExecutionError("unavailable_binding", affected_refs=[handle]) from error
            if not isinstance(episode, Episode) or not isinstance(context, Context) or not callable(pack_result):
                raise DurableExecutionError("unavailable_binding", affected_refs=[handle])
            if (canonical(episode.request.as_record()) != canonical(spec["child"]["request"])
                    or context.require_run_id() != spec["run_id"]
                    or [list(part) for part in context.path] != spec["parent"]["path"]
                    or episode.grain.name != spec["child"]["role"]
                    or episode.key != spec["child"]["key"]):
                raise DurableExecutionError("identity_conflict", affected_refs=[handle])
            stage = "episode"
            record = await episode.run_async(context)
            # Close histories before packing, retaining only archive descriptors
            # in any infrastructure failure. Domain archives remain domain-owned.
            archive = episode.archive_record or JsonArchive(store.archive_directory).store
            stage = "archive_trace"
            closed["episode_archive"] = (record.archived_record or archive(record)).descriptor()
            stage = "result"
            result = episode.build_result(record)
            if inspect.isawaitable(result):
                result = await result
            result = _require_closed_record(result, "Episode.build_result()")
            stage = "archive_result"
            closed["result_archive"] = archive(result).descriptor()
            closed["completion"] = EpisodeCompletion.from_record(record).as_record()
            outcome, stage = "closed", "pack"
            packed = pack_result(record, result)
            if inspect.isawaitable(packed):
                packed = await packed
            if not isinstance(packed, Mapping) or set(packed) != set(closed):
                raise DurableExecutionError("invalid_return", affected_refs=[handle])
            if canonical(packed["completion"]) != canonical(closed["completion"]):
                raise DurableExecutionError("invalid_return", affected_refs=[handle])
            # Valid facts and surviving descendants remain usable even when a
            # separately supplied form cannot be represented or admitted.
            try:
                _archive_descriptor(packed["facts_archive"])
                closed["facts_archive"] = packed["facts_archive"]
            except (TypeError, ValueError):
                pass
            try:
                _references(packed["pending_handles"], "pending_handles")
                closed["pending_handles"] = list(packed["pending_handles"])
            except (TypeError, ValueError):
                pass
            # Check the complete immutable envelope before adopting descriptors
            # or form data supplied by a reconstruction binding.
            trial = {"version": "returned_episode_v1", "handle": handle,
                "commission_sha256": digest, "returned_at": utc_now(), "outcome": "closed",
                **packed, "failure": None}
            trial["return_id"] = content_digest(trial)
            validate_return(trial, spec=spec, commission_sha256=digest)
            closed = dict(packed)
            stage = "cleanup"
    except BaseException as error:
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            code = "interrupted_execution"
            if outcome != "closed":
                outcome = "interrupted"
        elif isinstance(error, DurableExecutionError):
            code = error.failure["code"]
            if code == "interrupted_execution" and outcome != "closed":
                outcome = "interrupted"
        else:
            code = ("invalid_return" if stage == "pack" else
                    "storage_failure" if stage in ("archive_trace", "archive_result") else "execution_failed")
        failure = (dict(error.failure) if isinstance(error, DurableExecutionError) else
            {"code": code, "affected_refs": [handle], "diagnostic_ref": None, "partial_record_refs": []})
        try:
            if failure["diagnostic_ref"] is None:
                failure["diagnostic_ref"] = _diagnostic(store, error)
        except (OSError, ValueError):
            # Failure to save a diagnostic must not erase preserved work.
            pass
        if outcome == "closed":
            # A failed representation does not erase completed child work and
            # cannot expose an invalid form for application admission.
            closed["form"] = None
        else:
            closed["completion"] = None
    payload = {"version": "returned_episode_v1", "handle": handle,
        "commission_sha256": digest, "returned_at": utc_now(), "outcome": outcome,
        **closed, "failure": failure}
    payload["return_id"] = content_digest(payload)
    return store.publish_return(handle, execution_token, payload)


def main(argv=None):
    directory, handle, token, readiness = sys.argv[1:] if argv is None else argv
    ready_fd = int(readiness)
    store = DurableExecutionStore(directory)
    readiness_byte = b"0"
    try:
        claimed = store._claim(handle, token)
        readiness_byte = b"1"
    finally:
        try:
            os.write(ready_fd, readiness_byte)
        except BrokenPipeError:
            pass  # The selected execution survives its starter's death.
        finally:
            os.close(ready_fd)
    if not claimed:
        return
    def interrupted(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    asyncio.run(execute_commission(store, handle, token))


if __name__ == "__main__":
    main()
