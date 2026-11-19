"""Scratch directories: files of one tool unit's own, on disk, outside custody.

A tool that needs a file on disk (to give its name to an external program, to stream a download, to decode or
convert something too large for memory, to let a worker thread compute) asks its store for a scratch directory:

```python
with ctx.store.scratch('alignment') as scratch:
    query = scratch.copy_artifact(query_ref, 'query.fasta')          # a held artifact, as a file of the unit
    result = await scratch.compute(run_aligner, query, scratch.path / 'out.json')    # in a worker thread
    out_ref = ctx.store.artifact_file(scratch.path / 'out.json', 'application/json')  # a receipted write
```

Rules:

- **Nothing in a scratch directory is a record.** It is not held, passed, returned or receipted. A result leaves
  it only as a write through the scoped store (``artifact_file``, ``artifact_stream``, ``artifact``, ``put``),
  and an input enters it only through a custody read (``copy_artifact``, or bytes the tool read itself).
- **It belongs to the unit that opened it.** It can be opened only while a tool unit runs, and the unit must
  close it (leave the ``with`` block) before it returns: a unit that ends with one open raises ``CustodyError``.
  The directory and everything in it are removed when the block is left, also by an error.
- **A cut leaves nothing for the rerun.** The directories of an Episode live below one directory named by its
  episode id. When an Episode is built (at link and at resume) that directory is removed, so what a process that
  was cut left behind is gone before the unit runs again; the rerun gets a new, empty directory. A scratch file is
  therefore never a way to carry work across an interruption: what must survive is written as a record (and is
  then in ``ctx.abandoned`` for the rerun) or kept by a declared service.
- **A worker thread gets files, never the Store.** ``scratch.compute(function, ...)`` runs ``function`` in a
  worker thread and waits for it, also when the unit is cancelled (the directory is never removed under a
  running thread). The scoped store refuses every call from that thread (``recording.Custody``).

The directories are beside the Store's own files (``<store directory>/scratch/<episode id>/``), on the Store's
filesystem. The system chooses the place; a library function never names it and never builds a path to the Store
from it.
"""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import threading

from .recording import CustodyError

SCRATCH = 'scratch_directory'
_CHUNK = 1024 * 1024


class ScratchRoot:
    """Where the scratch directories of one Store's Episodes live. Built by the system; never given to episodes."""

    def __init__(self, store):
        self._root = Path(store.path) / 'scratch'

    def _episode(self, owner):
        return self._root / owner[1]

    def create(self, owner, unit, name):
        """A new, empty directory of ``owner`` (run id, episode id) for its unit ``unit``."""
        directory = self._episode(owner)
        directory.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=str(unit) + '-' + name + '-', dir=directory))

    @staticmethod
    def remove(path):
        shutil.rmtree(path)

    def clear(self, owner):
        """Remove every scratch directory of ``owner``: what a process that was cut left behind. Called when the
        Episode is built, when none of its units is running."""
        directory = self._episode(owner)
        if directory.exists():
            shutil.rmtree(directory)


class ScratchDirectory:
    """One scratch directory of a running tool unit (see the module docstring)."""

    def __init__(self, path, reader, custody):
        self.__path, self.__reader, self.__custody = Path(path), reader, custody
        self.__open = True

    def _close(self):
        self.__open = False

    def __require_open(self):
        self.__custody.require_unit(SCRATCH)
        if not self.__open:
            raise CustodyError('scratch_directory_is_closed:' + repr(self.__custody.path))

    @property
    def path(self):
        """The directory (a ``pathlib.Path``); the unit creates, reads and removes files below it freely."""
        self.__require_open()
        return self.__path

    def __inside(self, name):
        relative = PurePosixPath(name) if type(name) is str else None
        if relative is None or not relative.parts or relative.is_absolute() or '..' in relative.parts:
            raise ValueError('scratch_file_name_must_be_a_relative_path_inside_the_directory:' + repr(name))
        return self.__path / relative

    def copy_artifact(self, ref, name):
        """Copy the bytes of the held artifact ``ref`` into the new file ``name`` of this directory (a relative
        path; missing folders are made) and return its path. The copy is checked against the artifact's
        digest. ``CustodyError`` when the Episode does not hold ``ref``."""
        self.__require_open()
        destination = self.__inside(name)
        record = self.__reader.get(ref)
        if record['record_type'] != 'artifact':
            raise ValueError('artifact_reference_required:' + str(ref))
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with self.__reader.open_artifact(ref) as source, destination.open('xb') as output:
            for chunk in iter(lambda: source.read(_CHUNK), b''):
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != record['sha256']:
            destination.unlink()
            raise ValueError('artifact_digest_mismatch:' + str(ref))
        return destination

    async def compute(self, function, *args, **kwargs):
        """Run ``function(*args, cancel_event=<threading.Event>, **kwargs)`` in a worker thread and return what it
        returns (an error it raises is raised here). The thread works on files (paths below this directory) and
        plain values; it has no Store: the scoped store refuses every call from it. The unit waits for the thread
        even when it is cancelled: the event is set, ``function`` must stop its work and return, and only then
        does the cancellation continue, so the directory is never removed under a running thread."""
        self.__require_open()
        if 'cancel_event' in kwargs:
            raise ValueError('scratch_computation_is_given_its_cancel_event_by_the_system')
        cancellation = threading.Event()
        task = asyncio.create_task(asyncio.to_thread(function, *args, cancel_event=cancellation, **kwargs))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            cancellation.set()
            while not task.done():
                try:
                    await asyncio.wait({task})
                except asyncio.CancelledError:      # cancelled again while waiting: the thread is still running
                    continue
            task.exception()        # the thread's own error, if any, gives way to the cancellation
            raise


__all__ = ['SCRATCH', 'ScratchDirectory', 'ScratchRoot']
