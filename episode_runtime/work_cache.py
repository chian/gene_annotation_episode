"""The work cache: a declared service for work that is worth keeping across Episodes and runs but is no record.

A cache is not under custody and is not part of the Store. Nothing in it is held, passed, returned or receipted;
it is shared by every Episode that declares it, and by a later run that is given the same directory; emptying it
changes no result, only what has to be done again. That is what a service is (``services.py``), so the cache is
one: the run's caller supplies it (``collaborators['services'] = {'work_cache': lambda: WorkCache(directory)}``),
an episode declares the name in its ``services``, and a tool reaches it as ``ctx.services['work_cache']``. It is
not an operation of the scoped store, because that store hands out only what custody covers and never a place
that outlives the unit.

It serves the two needs the library had of the Store's directory and of other Episodes' records:

- **a cache directory for an external program** (an aligner's index cache): ``directory(name)`` is a directory
  that persists, for the program to manage;
- **"was this already fetched or computed by anyone"**: ``get(namespace, key)`` returns the bytes kept under a key
  (``None`` when there are none) and ``put(namespace, key, data)`` keeps them. A tool that finds its bytes here
  writes them with ``ctx.store.artifact(data)``: the artifact is content-addressed, so it is the same reference
  another Episode got for the same bytes, and this Episode holds it as produced without having read anyone's
  record. A tool that does not find them does the work, writes the artifact and puts the bytes here.

A decision may ask ``ctx.services['work_cache'].read('has', namespace, key)``; like every decision read it is
recorded once per unit position and replayed. What a tool gets from the cache is not replayed: a completed unit
is not run again, and a unit that runs again finds the cache as it then is, which is the point of a cache.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile

from method_loop.jsonvalue import closed_copy, content_digest

_NAME = re.compile(r'^[a-z][a-z0-9_]*$')


class WorkCache:
    """A cache directory and keyed bytes below one directory the run's caller chooses (outside the Store)."""

    def __init__(self, root):
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _name(name, what):
        if type(name) is not str or not _NAME.fullmatch(name):
            raise ValueError('work_cache_' + what + '_must_be_a_lowercase_identifier:' + repr(name))
        return name

    def directory(self, name):
        """The persistent directory ``name`` (made on first use), as a ``pathlib.Path``, for an external program
        that keeps a cache of its own."""
        path = self._root / 'directories' / self._name(name, 'directory')
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _entry(self, namespace, key):
        key = closed_copy(key, 'work_cache_key', TypeError)
        return self._root / 'entries' / self._name(namespace, 'namespace') / content_digest(key)

    def has(self, namespace, key):
        """Whether bytes are kept under ``key`` (closed JSON) in ``namespace``."""
        return self._entry(namespace, key).is_file()

    def get(self, namespace, key):
        """The bytes kept under ``key`` in ``namespace``, or ``None``."""
        entry = self._entry(namespace, key)
        return entry.read_bytes() if entry.is_file() else None

    def put(self, namespace, key, data):
        """Keep ``data`` (bytes) under ``key`` in ``namespace``, replacing what was kept there. The entry appears
        whole or not at all."""
        if not isinstance(data, bytes):
            raise TypeError('work_cache_data_must_be_bytes')
        entry = self._entry(namespace, key)
        entry.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=entry.parent, prefix='.pending-')
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, entry)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


__all__ = ['WorkCache']
