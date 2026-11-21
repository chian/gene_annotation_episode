"""The generic episode runner: link, record and resume a subtree of episodes.

This package belongs to no episode tree. It knows no role, episode or evidence axis. Every episode binding
inherits directly from ``EpisodeBinding`` (``method_loop/episode_type.py``), which carries the system behaviour on
top of the generic method loop (``method_loop``). The runner links a registry of binding instances below any entry
(grains -> declared tree -> Context -> entry Episode with child builders), gives each Episode its recording
services (``recording.py``: model calls, record custody, unit attempts; ``store_scope.py``,
``work_tables.py`` and ``store_ledger.py``: the run's Store under custody, its work tables and the receipts of
what units produced; ``scratch.py``: the scratch directories of tool units; ``progress.py``: clock points;
``services.py``, with ``work_cache.py``: the cache a run may give its episodes as a service), writes every
commission, unit attempt, outcome, controller step, model call, service read of a decision, receipt, return,
setting, service and result to the run journal, and resumes a recorded run from it
(docs/axis_restructure_20261117/BINDING_CONTRACT.md). A run's caller may step the entry Episode in place of
running it: ``EpisodeRun.next_decision()`` (what its ``decide`` returns first, no model call) and
``EpisodeRun.run_unit(tool_call)`` (one journaled tool unit), with ``EpisodeRun.view`` for the Episode's view.

``EPISODE_API`` names what an episode's files and the support library may import from this package. Everything
else (``Custody``, ``UnitAttempts``, ``UnitPosition``, ``RecordedModel``, ``ServiceReads``, ``InitialCredit``,
``BoundEpisode``, ``ChildBuilder``, ``WorkRows``, ``StoreLedger``, the pass functions of ``recording.py``) belongs
to the runner.
"""
from .bindings import BindingRegistry, MissingBinding
from .collaborators import STANDARD_COLLABORATORS, interface_failures
# The episode contract is defined in method_loop (the owner's decision of 2026-11-20); episodes still import it from
# here until their imports are moved (step 2).
from method_loop import (ChildCall, ChildMessage, EpisodeBinding, ModelRequest, Rejected, SIGNATURES,
                         SUPPLIED_BY_FILE, ToolCall)
from .journal import JournalError, RunJournal
from .progress import DecisionClock, ProgressClock
from .recording import CustodyError, DecisionContext, UnitContext
from .runner import BoundEpisode, ChildBuilder, EpisodeRun, LinkError, link, resume
from .scratch import ScratchDirectory
from .services import DecisionServices, EpisodeServices, RunServices, ServiceReader
from .store_scope import RecordReader, ScopedStore
from .work_cache import WorkCache
from .work_tables import ScopedTable, TableDeclaration, TableReader, WorkTableError

# What episode files and the support library may import from ``episode_runtime``.
EPISODE_API = ('ChildCall', 'ChildMessage', 'CustodyError', 'DecisionClock', 'DecisionContext', 'EpisodeBinding',
               'ModelRequest', 'RecordReader', 'Rejected', 'ScopedStore', 'ScopedTable', 'ScratchDirectory',
               'ServiceReader', 'TableDeclaration', 'TableReader', 'ToolCall', 'UnitContext', 'WorkTableError')

__all__ = ['BindingRegistry', 'BoundEpisode', 'ChildBuilder', 'ChildCall', 'ChildMessage', 'CustodyError',
           'DecisionClock', 'DecisionContext', 'DecisionServices', 'EPISODE_API', 'EpisodeBinding', 'EpisodeRun',
           'EpisodeServices', 'JournalError', 'LinkError', 'MissingBinding', 'ModelRequest', 'ProgressClock',
           'RecordReader', 'Rejected', 'RunJournal', 'RunServices', 'SIGNATURES', 'STANDARD_COLLABORATORS',
           'SUPPLIED_BY_FILE', 'ScopedStore', 'ScopedTable', 'ScratchDirectory', 'ServiceReader',
           'TableDeclaration', 'TableReader', 'ToolCall',
           'UnitContext', 'WorkCache', 'WorkTableError', 'interface_failures', 'link', 'resume']
