"""The named services a run gives its episodes (``ctx.services``).

The run's caller supplies a ``services`` collaborator: a mapping from a service name to a zero-argument factory.
An episode declares the names it needs (its ``services`` member); the runner checks at link time that every
declared name is supplied and journals the declaration. Each service is built once per run, on its first use,
and shared by every episode that declares it; the journal records each build (which Episode first used it, at
which unit; a resumed run builds its services again, which is recorded too). An episode sees only the names it
declared.

A tool is handed the services themselves (``ctx.services`` of the ``UnitContext``: ``EpisodeServices``) and may
act through them. ``decide`` and ``action`` are handed read handles (``ctx.services`` of the ``DecisionContext``:
``DecisionServices`` of ``ServiceReader``), never the service: ``ctx.services[name].read(member, *arguments)``
returns the service's value as closed JSON and records it in the run journal under the unit position being
decided. The same read at that position is then given the recorded value: after a rejected answer, on a rerun of
the unit and on resume, whatever the service says by then. A decision is therefore rebuilt from the values it was
first made on. (PROVISIONAL, owner decision T10: this module and ``RunJournal.service_read`` are the whole of it.)

A service is the run's access to something outside the Store (a job scheduler, a transport, a table of earlier
estimates). It is never a way to the Store: the Store is reached only through custody (``store_scope.py``).
"""
from __future__ import annotations

from collections.abc import Mapping

from method_loop.jsonvalue import closed_copy


class RunServices:
    """The services of one run: each factory is called at most once; ``on_build(name, user)`` records it."""

    def __init__(self, factories, on_build):
        self._factories, self._built, self._on_build = factories, {}, on_build

    def service(self, name, user):
        if name not in self._built:
            self._built[name] = self._factories[name]()
            self._on_build(name, user)
        return self._built[name]

    def view(self, names, user):
        return EpisodeServices(self, names, user)


class EpisodeServices(Mapping):
    """The services one episode declared, built when first read. The mapping cannot be changed."""

    def __init__(self, run_services, names, user):
        self._run, self._names, self._user = run_services, tuple(names), user

    def __getitem__(self, name):
        if name not in self._names:
            raise KeyError('service_not_declared_by_this_episode:' + str(name))
        return self._run.service(name, self._user)

    def __iter__(self):
        return iter(self._names)

    def __len__(self):
        return len(self._names)


class ServiceReader:
    """One declared service as ``decide`` and ``action`` see it: a handle that reads and cannot act.

    ``read(member, *arguments)`` is the service's public attribute ``member`` (called with ``arguments`` when it is
    callable), as closed JSON. The first read of a member with given arguments at a unit position asks the service
    and is recorded; every later one at that position returns the recorded value without asking the service."""

    def __init__(self, name, service, recorded):
        self.__name, self.__service, self.__recorded = name, service, recorded

    def read(self, member, *arguments):
        name = self.__name
        if type(member) is not str or not member.isidentifier() or member.startswith('_'):
            raise ValueError('service_read_member_must_be_a_public_name:' + name + ':' + repr(member))
        request = closed_copy({'service': name, 'member': member, 'arguments': list(arguments)},
                              'service_read_request', TypeError)

        def ask():
            value = getattr(self.__service(), member)
            if callable(value):
                value = value(*arguments)
            elif arguments:
                raise TypeError('service_read_member_takes_no_arguments:' + name + '.' + member)
            return closed_copy(value, 'service_read_value:' + name + '.' + member, TypeError)
        return self.__recorded(request, ask)


class DecisionServices(Mapping):
    """The read handles of the services one episode declared, for the decision of one unit position.

    ``recorded(request, ask)`` returns the value recorded for ``request`` at that position, or records and
    returns ``ask()``. The mapping cannot be changed; a name the episode did not declare raises ``KeyError``."""

    def __init__(self, services, recorded):
        # Only the names are taken here: a service is built when a read has to ask it, not before.
        self._services, self._names, self._recorded = services, tuple(services), recorded

    def __getitem__(self, name):
        if name not in self._names:
            raise KeyError('service_not_declared_by_this_episode:' + str(name))
        return ServiceReader(name, lambda: self._services[name], self._recorded)

    def __iter__(self):
        return iter(self._names)

    def __len__(self):
        return len(self._names)


__all__ = ['DecisionServices', 'EpisodeServices', 'RunServices', 'ServiceReader']
