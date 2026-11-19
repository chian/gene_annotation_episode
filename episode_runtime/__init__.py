"""The generic episode runner and the Episode type: link, record and resume a subtree of episodes.

This package belongs to no episode tree. It knows no role, episode or evidence axis. Every episode binding
inherits directly from ``EpisodeBinding`` (``episode_type.py``), which carries the system behaviour on top of the
generic method loop (``method_loop``). The runner links a registry of binding instances below any entry
(grains -> declared tree -> Context -> entry Episode with child builders), gives each Episode its recording
services (``recording.py``: model calls, record custody, unit attempts; ``store_scope.py``,
``work_tables.py`` and ``store_ledger.py``: the run's Store under custody, its work tables and the receipts of
what units produced; ``progress.py``: clock points; ``services.py``), writes every
commission, unit attempt, outcome, controller step, model call, service read of a decision, receipt, return,
setting, service and result to the run journal, and resumes a recorded run from it
(docs/axis_restructure_20261117/BINDING_CONTRACT.md).

``EPISODE_API`` names what an episode's files and the support library may import from this package. Everything
else (``Custody``, ``UnitAttempts``, ``UnitPosition``, ``RecordedModel``, ``ServiceReads``, ``BoundEpisode``,
``ChildBuilder``, ``WorkRows``, ``StoreLedger``, the pass functions of ``recording.py``) belongs to the runner.
"""
from .bindings import BindingRegistry, MissingBinding
from .collaborators import STANDARD_COLLABORATORS, interface_failures
from .episode_type import (ChildCall, ChildMessage, EpisodeBinding, ModelRequest, Rejected, SIGNATURES,
                           SUPPLIED_BY_FILE, ToolCall)
from .journal import JournalError, RunJournal
from .progress import DecisionClock, ProgressClock
from .recording import CustodyError, DecisionContext, UnitContext
from .runner import BoundEpisode, ChildBuilder, EpisodeRun, LinkError, link, resume
from .services import DecisionServices, EpisodeServices, RunServices, ServiceReader
from .store_scope import RecordReader, ScopedStore
from .work_tables import ScopedTable, TableDeclaration, TableReader, WorkTableError

# What episode files and the support library may import from ``episode_runtime``.
EPISODE_API = ('ChildCall', 'ChildMessage', 'CustodyError', 'DecisionClock', 'DecisionContext', 'EpisodeBinding',
               'ModelRequest', 'RecordReader', 'Rejected', 'ScopedStore', 'ScopedTable', 'ServiceReader',
               'TableDeclaration', 'TableReader', 'ToolCall', 'UnitContext', 'WorkTableError')

__all__ = ['BindingRegistry', 'BoundEpisode', 'ChildBuilder', 'ChildCall', 'ChildMessage', 'CustodyError',
           'DecisionClock', 'DecisionContext', 'DecisionServices', 'EPISODE_API', 'EpisodeBinding', 'EpisodeRun',
           'EpisodeServices', 'JournalError', 'LinkError', 'MissingBinding', 'ModelRequest', 'ProgressClock',
           'RecordReader', 'Rejected', 'RunJournal', 'RunServices', 'SIGNATURES', 'STANDARD_COLLABORATORS',
           'SUPPLIED_BY_FILE', 'ScopedStore', 'ScopedTable', 'ServiceReader', 'TableDeclaration', 'TableReader',
           'ToolCall',
           'UnitContext', 'WorkTableError', 'interface_failures', 'link', 'resume']
