"""The run's shared Store under custody: the only way an episode, or a library function called by one, reaches it.

There is one operation set under one set of names. ``RecordReader`` is its read-only part, given to the pure
functions (``view.records`` and the ``records`` argument of ``credit``, ``action`` and ``read_from_child``).
``ScopedStore`` is the whole set, given only to tools (``ctx.store``). No episode and no library function receives
the Store itself, its SQLite connection or its directory.

What ``RecordReader`` offers (every read; it writes nothing):

- **custody questions**: ``holds``, ``refs``, ``receipt``;
- **reads of one named record** (``get``, ``get_artifact``, ``open_artifact``, ``require``, ``get_input``,
  ``roots``, the ``subject_*`` questions, ``coverage``, ``record_coverage``, ``sequence_mapping``,
  ``has_exact_mapping``, ``map_segments``, ``material_members``, ``material_errors``, ``material_read``,
  ``material_member``, ``material_annotations``, ``is_current``): the record must be one the Episode holds, else
  ``CustodyError``. Holding a record does not hold the records it names: where the Store's operation reads
  further records on the way (a feature's parent subject, a product's sequence artifact, an assessment's
  hypothesis, a material's source: ``FOLLOWED`` below), each of those must be held too. The exception is a
  collection: a member is read by an Episode that holds it or its collection;
- **inventories, limited to what the Episode holds** (``list``, ``count``, ``subjects``, ``references``,
  ``targets``, ``problem``, ``current_assessments``, ``current_annotations``, ``iter_current_annotations``,
  ``iter_current_accounts``, ``current_assessment_subset``, ``reference_subset``, ``in_scope``,
  ``query_records``, ``reasoning_view``): each returns only held records. ``list`` returns all of them unless a
  ``limit`` is given; the paged ones (``query_records``, ``reasoning_view``, ``material_members``) report their
  totals and next offsets. A page is cut after the custody limit;
- **scope arithmetic** (``validate_scope``, ``scope_contains``, ``scope_covers``, ``scope_coverage``,
  ``scope_dimension_segments``): every subject and read selection a scope names must be held; the same holds for
  the subjects and read selections of a context mask, the target of a span and the subjects of a mapping's path
  (``normalize_context_mask``, ``context_mask_identity``, ``context_mask_subset``, ``context_mask_overlap``,
  ``footprint_dimension``, ``footprint_from_mapping``, ``assessment_key``). ``reasoning_schema`` reads no record;
- **the measures of a scope and of a context mask** (``scope_measure``, ``iter_scope_coverage``,
  ``read_subject_ref``, ``context_mask_measure``, ``context_mask_target_full``,
  ``context_mask_dimension_segments``, ``context_mask_positions``): under the same rule, every subject and read
  selection the scope or mask names must be held. ``context_mask_positions`` returns the positions the Store's
  ``context_mask_target_query`` describes; the SQL of that query is not handed out;
- **the Store's ownership rules, over held records** (``assessment_write_extent(ref)``,
  ``assert_library_write_scope(ref, scope)``, ``named_references(ref)``; ``roots(ref)`` is the Store's
  ``_record_roots`` of a stored record): the Store's own private functions, run for one held record with
  ``HeldStore`` in the place of the Store, so that every record they read on the way must be held too;
- **the original reads of a read library** (``library_members(library_ref, ...)``, a page of the reads of a held
  library, and ``selection_members(selection_ref)``, the references of the reads a held read selection froze):
  the Store's own ``library_targets.member_page`` and the rows of its ``library_selection_members``. The library,
  every collection it binds (the reads are rows of those collections), the scope's subjects and read selections
  and a named selection must be held. The references they return are names: reading a read subject by its
  reference still needs that reference held;
- **the diagnostics of the Episode's tool outcomes** (``is_diagnostic_ref(ref)``): whether the outcome of one of
  this Episode's tool units names the held record ``ref`` under a key ``diagnostic_ref`` (``recording.py``);
- **work tables** (``table(declaration)``): the held rows of a declared table (``work_tables.py``).

What ``ScopedStore`` adds, for the tool unit that is running:

- **writes** (``put``, ``artifact``, ``artifact_file``, ``artifact_stream``, ``caller_source``,
  ``commit_reasoning``, ``register_material``, ``create_problem``, ``parse_material``, ``material_header``,
  ``material_reference``, ``select_library_members``, ``reclaim``, and ``table(declaration).put`` and
  ``.withdraw``).
  A write requires every record it names to be readable by the unit, else ``CustodyError``. The Episode holds
  what the write created or changed as produced at this unit. Each write runs in a Store transaction and its
  receipt is written in the same transaction (``store_ledger.py``);
- **transactions** (``transaction()``, ``read_snapshot()``, ``in_transaction()``): the writes of a transaction
  are receipted when it commits; a rolled-back transaction leaves no receipt and the Episode does not hold what
  it wrote. There is no ``commit``: a library function never ends a transaction it did not open;
- **a scratch directory** (``scratch(name)``, ``scratch.py``): files of the unit's own on disk, outside custody,
  with ``copy_artifact`` to bring a held artifact in and ``compute`` to run a worker thread on them;
- **a section** (``section(name)``): whether a call is the outermost one of a named piece of the unit's work
  (what a library function used to mark with an attribute it set on the Store object);
- **what an abandoned attempt of this unit produced** is readable through these reads while the rerun's tool
  runs (``ctx.abandoned`` names it), and through nothing else.

Not offered, in any form: the Store's SQLite connection (``db``), its directory (``path``), the path of an
artifact, a commit, and the SQL text of ``context_mask_target_query``. The Store's helpers that read nothing
(``_unit``, ``_merge_segments``, ``_covered_by``) are not Store operations: a library function that needs one
keeps it as a pure function of its own.

What the system itself uses of the Store beyond its public methods: ``_require`` (for ``require``), ``path`` (to
open the file of an artifact and to place the scratch directories), the connection ``db`` (whether a transaction
is open, which revision is current, the positions of a context mask, the reads of a read selection, the system
tables of ``work_tables.py`` and ``store_ledger.py``), the private rules ``_caller_source``, ``_refs``,
``_record_roots``, ``_assessment_write_extent``, ``_ownership_reach``, ``_assert_read_member_reach`` and
``_assert_library_write_scope`` (run over held records, ``HeldStore``), and the Store's own module functions
``materials.artifact_file`` (to capture a file as an artifact) and ``library_targets.member_page`` and
``library_targets.select`` (the page of a read library's reads and the freezing of a selection of them, run on
the Store once custody has admitted everything they read). ``named_references`` below repeats the rule of the
Store's ``_refs`` for which values of a record are references.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
import json
import os
from types import MethodType

# The Store's own implementation of its read libraries: the page of a library's reads and the freezing of a
# selection of them (module functions over the Store; the Store class has no method for either).
from gene_annotation_episode import library_targets as libraries
# The Store's own implementation of capturing a file as an artifact (the Store class has no method for it).
from gene_annotation_episode.materials import artifact_file as capture_artifact_file

from .recording import CustodyError
from .scratch import SCRATCH, ScratchDirectory, ScratchRoot
from .work_tables import ScopedTable, TableReader, is_row_ref

REVISIONED_KINDS = ('assessment', 'annotation', 'interpretation_account')


def named_references(value):
    """Every reference a record or payload names: the text under a key ``ref`` or ``..._ref``, and the texts of a
    list under a key ``..._refs`` or ``dependencies`` (the Store's own rule, ``Store._refs``). A value that is not
    text in such a place names nothing; the Store's validation refuses the record that carries it."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if type(key) is str and (key == 'ref' or key.endswith('_ref')):
                if type(child) is str:
                    yield child
            elif type(key) is str and (key == 'dependencies' or key.endswith('_refs')):
                if isinstance(child, (list, tuple)):
                    yield from (ref for ref in child if type(ref) is str)
            else:
                yield from named_references(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from named_references(child)


# -- the records a Store read follows (PROVISIONAL: owner decision T5, "name every record") -----------------------
# Holding a record does not hold the records it names. The Store's own read operations below read further records
# on the way (a feature's parent subject, a product's sequence artifact, an assessment's hypothesis, a material's
# source); ``FOLLOWED`` names, per operation, the records the Store reads beyond the one it is asked for, and
# ``RecordReader`` requires each of them to be held before it asks the Store. This table, ``followed`` and
# ``RecordReader._follow`` are the whole of the rule: an operation that is not in the table is not guarded by it.
# The exceptions and their reasons are listed in ``BINDING_CONTRACT.md`` ("What a read reaches"). The main one is a
# collection: its members, and the packed bytes of their titles and sequences, are rows and storage of the
# collection, not records with receipts of their own, so they are read through the held collection
# (``material_members``, ``material_member``, ``material_header``, ``material_reference``).
SUBJECT_KINDS = ('input', 'read_subject', 'feature', 'product')


def _subject_chain(store, row):
    """A feature is resolved through its parent subject, and that one through its own: ``(refs, last)`` are the
    parent references the Store reads, nearest first, and the record of the first subject that is not a feature."""
    refs = []
    while row['record_type'] == 'feature':
        refs.append(row['subject_ref'])
        row = store.get(row['subject_ref'])
    return refs, row


def _sequence(row):
    """The sequence artifact whose size is the length of a product or a reference."""
    return [row['sequence_ref']] if row['record_type'] in ('product', 'reference') and row.get('sequence_ref') else []


def _mapping(store, row):
    """``sequence_mapping`` and ``has_exact_mapping``: the parents of a feature, and the sequence artifact of the
    reference the chain ends in (its size is the length of the mapping)."""
    refs, last = _subject_chain(store, row)
    return refs + (_sequence(last) if last['record_type'] == 'reference' else [])


def _segments(store, row):
    """``map_segments``: what the mapping follows, the subject's own sequence artifact (its length), and the
    subjects a product's stored mapping runs over (the Store reads each to build the footprint)."""
    refs, last = _subject_chain(store, row)
    path = last.get('mapping') if last['record_type'] == 'product' else None
    return (_sequence(row) + _mapping(store, row)
            + [step['subject_ref'] for step in (path or {}).get('path', ()) if type(step.get('subject_ref')) is str])


def _coverage(store, row):
    """``coverage``: a feature's coverage maps its segments through its parent subject."""
    if row['record_type'] != 'feature':
        return []
    return [row['subject_ref']] + _segments(store, store.get(row['subject_ref']))


def _record_coverage(store, row):
    """``record_coverage``: an assessment's coverage is its hypothesis's; a hypothesis's or an observation's is that
    of the subjects it names."""
    kind = row['record_type']
    if kind in SUBJECT_KINDS:
        return _coverage(store, row)
    if kind == 'assessment':
        return [row['hypothesis_ref']] + _record_coverage(store, store.get(row['hypothesis_ref']))
    if kind in ('hypothesis', 'observation'):
        refs = []
        for ref in row['subject_refs']:
            refs.append(ref)
            subject = store.get(ref)
            if subject['record_type'] in SUBJECT_KINDS:
                refs += _coverage(store, subject)
        return refs
    return []


def _material_read(store, row):
    """``material_read``: the bytes are those of the artifact of the material's source."""
    return [row['source_ref'], store.get(row['source_ref'])['artifact_ref']]


def _material_annotations(store, row):
    """``material_annotations``: the parse's material (its source is named in the page) and the source of the
    native annotations, when the parse made one."""
    return [row['material_ref']] + ([row['native_source_ref']] if row.get('native_source_ref') else [])


FOLLOWED = {
    'subject_length': lambda store, row: _sequence(row),
    'subject_unit': lambda store, row: _subject_chain(store, row)[0],
    'subject_molecule': lambda store, row: _subject_chain(store, row)[0],
    'sequence_mapping': _mapping,
    'has_exact_mapping': _mapping,
    'map_segments': _segments,
    'coverage': _coverage,
    'record_coverage': _record_coverage,
    'material_read': _material_read,
    'material_annotations': _material_annotations,
}


def followed(store, operation, ref, readable):
    """Require (``readable(ref)`` raises ``CustodyError``) every record the Store's ``operation`` on the held
    record ``ref`` reads beyond ``ref``. Each record is required before the Store is asked for the next, so the
    walk itself reads only what is held."""
    class Held:
        """The Store's ``get`` over held records only."""
        @staticmethod
        def get(reference):
            readable(reference)
            return store.get(reference)
    for reference in FOLLOWED[operation](Held, store.get(ref)):
        readable(reference)


def is_problem_ref(ref):
    """Whether ``ref`` is the reference of a Store's problem (``problem_...``, the identity the Store's
    ``create_problem`` gives the record of its ``problem`` table)."""
    return type(ref) is str and ref.startswith('problem_')


def require_in_store(store, rows, ref):
    """Raise ``CustodyError`` unless ``ref`` names something in the Store (a record, input, artifact or work-table
    row); the Store's own error for a reference it does not know is the cause."""
    if is_row_ref(ref):
        if not rows.exists(ref):
            raise CustodyError('entry_record_not_in_store:' + ref)
        return
    try:
        store.get(ref)
    except Exception as error:
        raise CustodyError('entry_record_not_in_store:' + ref) from error


class _SelectionMembers:
    """The one thing the Store's ownership rules ask its connection: which original reads a held read selection
    has (``library_selection_members``). The rows are the selection's own storage, like the members of a
    collection; nothing else can be asked here."""

    def __init__(self, db):
        self.__db = db

    def execute(self, sql, parameters=()):
        if not sql.startswith('SELECT read_ref FROM library_selection_members WHERE selection_ref=?'):
            raise CustodyError('store_rule_asked_the_connection_for_something_else_than_selection_members')
        return self.__db.execute(sql, parameters)


class HeldStore:
    """The Store as its own ownership rules see it when the system runs them for an Episode.

    ``RULES`` are the Store's own private functions. They are run with this object in the place of the Store, so
    every read they make (``READS``) is the custody-limited read of the Episode's reader: a record a rule follows
    (an assessment's hypothesis and observation, their subjects, a feature's parents, a read selection) must be
    held, else ``CustodyError``, and the rule is the Store's, not a copy of it. ``PURE`` read nothing. A rule that
    asks for anything else fails with ``AttributeError``: nothing here falls through to the Store."""

    READS = ('get', 'get_input', 'roots', 'coverage', 'record_coverage', 'has_exact_mapping', 'sequence_mapping',
             'map_segments', 'footprint_dimension', 'validate_scope', 'scope_covers', 'scope_contains',
             'scope_measure', 'scope_dimension_segments', 'read_subject_ref', 'context_mask_subset')
    RULES = ('_record_roots', '_assessment_write_extent', '_ownership_reach', '_assert_read_member_reach',
             '_assert_library_write_scope')
    PURE = ('_merge_segments', '_covered_by')

    def __init__(self, store, reader):
        for name in self.READS:
            setattr(self, name, getattr(reader, name))
        for name in self.RULES:
            setattr(self, name, MethodType(getattr(type(store), name), self))
        for name in self.PURE:
            setattr(self, name, getattr(type(store), name))
        self._db = _SelectionMembers(store._db)


class RecordReader:
    """The read-only view of what an Episode holds (see the module docstring)."""

    def __init__(self, store, custody, rows, *, unit=False):
        self.__store, self.__custody, self.__rows = store, custody, rows
        # A running tool (``unit``) may also read what an abandoned attempt of its unit produced.
        self.__readable = custody.require_unit_readable if unit else custody.require_readable

    def __rules(self):
        """The Store's ownership rules over what this reader may read (``HeldStore``)."""
        return HeldStore(self.__store, self)

    def _readable(self, ref):
        """Raise ``CustodyError`` unless ``ref`` may be read here."""
        self.__readable(ref)

    def _follow(self, operation, ref):
        """``ref`` must be held, and so must every record the Store's ``operation`` reads beyond it
        (``FOLLOWED``): holding a record does not hold the records it names."""
        self.__readable(ref)
        followed(self.__store, operation, ref, self.__readable)

    def _hold_mask(self, mask):
        """Every subject and read selection a context mask names must be held (the Store reads each)."""
        self._hold_scope(mask)

    def _member(self, ref):
        """A collection member is read by an Episode that holds it or its collection."""
        try:
            self.__readable(ref)
            return
        except CustodyError as refused:
            try:
                row = self.__store.get(ref)
            except Exception:
                raise refused from None
            if not isinstance(row, dict) or row.get('record_type') != 'collection_member':
                raise
            self.__readable(row['collection_ref'])

    def _hold_scope(self, scope):
        """Every subject and read selection ``scope`` names must be held (checked before the Store reads any)."""
        if isinstance(scope, Mapping):
            for key in ('subject_refs', 'read_selection_refs'):
                for ref in scope[key] if isinstance(scope.get(key), (list, tuple)) else ():
                    if type(ref) is str:
                        self.__readable(ref)

    def _scope(self, scope, parent_scope=None):
        """The Store's normalized scope; it names only held subjects."""
        self._hold_scope(scope)
        self._hold_scope(parent_scope)
        return self.__store.validate_scope(scope, parent_scope)

    def _held_records(self):
        """The held references that are records the Store's ``get`` answers and its inventories list by kind. Two
        kinds of held reference are not: a work-table row (read with ``table``) and the problem (the Episode
        whose unit called ``create_problem`` holds its reference as produced). The problem is the Store's one
        record of its own table, of no kind an inventory lists; it is read with ``problem()``."""
        return [ref for ref in self.__custody.refs() if not is_row_ref(ref) and not is_problem_ref(ref)]

    # -- custody questions ------------------------------------------------------------------
    def holds(self, ref):
        return self.__custody.holds(ref)

    def refs(self):
        return self.__custody.refs()

    def receipt(self, ref):
        return self.__custody.receipt(ref)

    # -- reads of one named record ----------------------------------------------------------
    def get(self, ref):
        """The held Store record (or work-table row) ``ref``."""
        if is_row_ref(ref):
            self.__custody.require_readable(ref)
            row = self.__rows.row(ref)
            if row is None:
                raise CustodyError('held_work_row_is_not_in_the_store:' + str(ref))
            return row
        self.__readable(ref)
        return self.__store.get(ref)

    def get_artifact(self, ref):
        """The bytes of the held Store artifact ``ref``."""
        self.__readable(ref)
        return self.__store.get_artifact(ref)

    def open_artifact(self, ref):
        """The bytes of the held artifact ``ref`` as a read-only binary file object, for content too large to
        load. It is opened by descriptor and carries no path: the Store's directory is not handed out."""
        self.__readable(ref)
        row = self.__store.get(ref)
        if row['record_type'] != 'artifact':
            raise ValueError('artifact_reference_required:' + str(ref))
        return os.fdopen(os.open(self.__store.path / 'artifacts' / row['sha256'][:2] / row['sha256'],
                                 os.O_RDONLY), 'rb')

    def require(self, ref, kinds=None, *, field_path=None):
        """The held record ``ref``; the Store's ``wrong_reference_type`` error when its kind is not in ``kinds``."""
        self.__readable(ref)
        return self.__store._require(ref, kinds, field_path=field_path)

    def is_current(self, ref):
        """Whether the held assessment, annotation or interpretation account ``ref`` is the current revision of
        its lineage."""
        self.__readable(ref)
        kind = self.__store.get(ref)['record_type']
        if kind not in REVISIONED_KINDS:
            raise ValueError('revisioned_record_required:' + str(ref))
        return self.__store._db.execute('SELECT 1 FROM current_revisions WHERE record_type=? AND record_ref=?',
                                       (kind, ref)).fetchone() is not None

    def get_input(self, ref):
        self.__readable(ref)
        return self.__store.get_input(ref)

    def roots(self, ref):
        self.__readable(ref)
        return self.__store.roots(ref)

    def subject_length(self, subject_ref):
        """The length of the held subject. For a product or a reference it is the size of its sequence artifact,
        which must be held too."""
        self._follow('subject_length', subject_ref)
        return self.__store.subject_length(subject_ref)

    def subject_unit(self, subject_ref):
        """The unit of the held subject; a feature's is that of its parent subject, which must be held too."""
        self._follow('subject_unit', subject_ref)
        return self.__store.subject_unit(subject_ref)

    def subject_molecule(self, subject_ref):
        """The molecule of the held subject; a feature's is that of its parent subject, which must be held too."""
        self._follow('subject_molecule', subject_ref)
        return self.__store.subject_molecule(subject_ref)

    def coverage(self, subject_ref):
        """The coverage of the held subject; a feature's is mapped through its parent subject, which must be held
        too (with what ``map_segments`` of that parent follows)."""
        self._follow('coverage', subject_ref)
        return self.__store.coverage(subject_ref)

    def record_coverage(self, row):
        """The coverage of the held record ``row['id']``, computed from the stored record (nothing else of the
        ``row`` the caller hands in is used). An assessment's coverage is its hypothesis's and a hypothesis's or an
        observation's is that of the subjects it names: each of those records must be held too."""
        self._follow('record_coverage', row['id'])
        return self.__store.record_coverage(self.__store.get(row['id']))

    def sequence_mapping(self, subject_ref):
        """The sequence mapping of the held subject. A feature's parent subjects and a reference's sequence
        artifact must be held too."""
        self._follow('sequence_mapping', subject_ref)
        return self.__store.sequence_mapping(subject_ref)

    def has_exact_mapping(self, subject_ref):
        self._follow('has_exact_mapping', subject_ref)
        return self.__store.has_exact_mapping(subject_ref)

    def map_segments(self, subject_ref, segments):
        """Map segments of the held subject. What its mapping follows, its own sequence artifact and the subjects
        a product's stored mapping runs over must be held too."""
        self._follow('map_segments', subject_ref)
        return self.__store.map_segments(subject_ref, segments)

    def material_members(self, collection_ref, *, offset=0, limit=50):
        self.__readable(collection_ref)
        return self.__store.material_members(collection_ref, offset=offset, limit=limit)

    def material_errors(self, parse_ref, *, offset=0, limit=50):
        self.__readable(parse_ref)
        return self.__store.material_errors(parse_ref, offset=offset, limit=limit)

    def material_read(self, material_ref, *, offset=0, limit=12000):
        """A window of the bytes of the held material: those of the artifact of its source. The source and the
        artifact must be held too."""
        self._follow('material_read', material_ref)
        return self.__store.material_read(material_ref, offset=offset, limit=limit)

    def material_member(self, member_ref, *, offset=0, limit=12000):
        self._member(member_ref)
        return self.__store.material_member(member_ref, offset=offset, limit=limit)

    def material_annotations(self, parse_ref, **kwargs):
        """A page of the native annotations of the held parse attempt. Its material and the source of those
        annotations must be held too."""
        self._follow('material_annotations', parse_ref)
        return self.__store.material_annotations(parse_ref, **kwargs)

    # -- inventories, limited to what the Episode holds ----------------------------------
    def _selection(self):
        return 'SELECT value FROM json_each(?)', [json.dumps(self._held_records())]

    @staticmethod
    def __page(rows, limit, offset):
        if type(offset) is not int or offset < 0 or (limit is not None and (type(limit) is not int or limit < 0)):
            raise ValueError('invalid_page')
        return rows[offset:] if limit is None else rows[offset:offset + limit]

    def __held_rows(self, kind, scope):
        """The held records of ``kind`` (within ``scope``), ordered by reference."""
        self.__store.list(kind, None, 0, 0)        # the Store's own check that the kind exists
        refs = self._held_records()
        if scope is not None:
            refs = self.__store.reference_subset(refs, self._scope(scope))
        rows = [row for row in map(self.__store.get, refs) if row['record_type'] == kind]
        return sorted(rows, key=lambda row: row['id'])

    def __current(self, kind, scope):
        """The current revisions of ``kind`` (within ``scope``) that the Episode holds, in the Store's order."""
        if scope is not None:
            scope = self._scope(scope)
        if kind == 'assessment':
            rows = self.__store.current_assessments(scope)
        elif kind == 'annotation':
            rows = self.__store.current_annotations(scope)
        else:
            rows = list(self.__store.iter_current_accounts(kind, scope))
        return [row for row in rows if self.__custody.holds(row['id'])]

    def list(self, kind, scope=None, limit=None, offset=0):
        """The held records of ``kind`` (within ``scope``), ordered by reference: all of them, or the page
        ``limit`` and ``offset`` cut after the custody limit."""
        return self.__page(self.__held_rows(kind, scope), limit, offset)

    def count(self, kind, scope=None, *, current=False):
        """How many records of ``kind`` (within ``scope``; current revisions only with ``current``) are held."""
        return len(self.__current(kind, scope) if current else self.__held_rows(kind, scope))

    def subjects(self, scope):
        """The scope's subjects (all held) and the held features and products within it."""
        normalized = self._scope(scope)
        return ([self.__store.get_input(ref) for ref in normalized['subject_refs']]
                + self.__held_rows('feature', normalized) + self.__held_rows('product', normalized))

    def references(self, scope):
        """The Store's references of ``scope`` by kind, each list limited to what the Episode holds."""
        found = self.__store.references(self._scope(scope))
        return {kind: [ref for ref in refs if self.__custody.holds(ref)] for kind, refs in found.items()}

    def problem(self):
        """The run's problem record, its ``subject_refs`` limited to the subjects the Episode holds."""
        problem = self.__store.problem()
        return {**problem, 'subject_refs': [ref for ref in problem['subject_refs'] if self.__custody.holds(ref)]}

    def targets(self):
        """The problem subjects the Episode holds."""
        return [self.__store.get_input(ref) for ref in self.problem()['subject_refs']]

    def current_assessments(self, scope=None, limit=None, offset=0):
        return self.__page(self.__current('assessment', scope), limit, offset)

    def current_annotations(self, scope=None, limit=None, offset=0):
        return self.__page(self.__current('annotation', scope), limit, offset)

    def iter_current_annotations(self, scope=None, page_size=100):
        yield from self.iter_current_accounts('annotation', scope, page_size)

    def iter_current_accounts(self, kind, scope=None, page_size=100):
        if scope is not None:
            scope = self._scope(scope)
        for row in self.__store.iter_current_accounts(kind, scope, page_size):
            if self.__custody.holds(row['id']):
                yield row

    def current_assessment_subset(self, refs):
        return self.__store.current_assessment_subset([ref for ref in refs if self.__custody.holds(ref)])

    def reference_subset(self, candidates, scope):
        return self.__store.reference_subset([ref for ref in candidates if self.__custody.holds(ref)],
                                             self._scope(scope))

    def in_scope(self, ref, scope):
        """Whether the held record ``ref`` lies within ``scope``."""
        self.__readable(ref)
        return ref in self.__store.reference_subset([ref], self._scope(scope))

    def query_records(self, kind, scope, limit=100, offset=0, *, current_only=False, references=None):
        """One page of the held records of ``kind`` in ``scope`` (the result carries ``total`` and
        ``next_offset``). Every reference named in ``references`` must be held."""
        for ref in references if isinstance(references, (list, tuple)) else ():
            if type(ref) is str:
                self.__readable(ref)
        return self.__store.query_records(kind, self._scope(scope), limit, offset, current_only=current_only,
                                          references=references, record_selection=self._selection())

    def reasoning_view(self, scope, limit=100):
        return self.__store.reasoning_view(self._scope(scope), limit, record_selection=self._selection())

    # -- scope arithmetic ------------------------------------------------------------------
    def validate_scope(self, scope, parent_scope=None):
        return self._scope(scope, parent_scope)

    def scope_contains(self, parent_scope, child_scope):
        self._hold_scope(parent_scope)
        self._hold_scope(child_scope)
        return self.__store.scope_contains(parent_scope, child_scope)

    def scope_covers(self, segments, scope):
        return self.__store.scope_covers(segments, self._scope(scope))

    def scope_coverage(self, scope):
        return self.__store.scope_coverage(self._scope(scope))

    def scope_dimension_segments(self, scope, dimension_ref):
        return self.__store.scope_dimension_segments(self._scope(scope), dimension_ref)

    def normalize_context_mask(self, mask):
        self._hold_mask(mask)
        return self.__store.normalize_context_mask(mask)

    def context_mask_identity(self, mask):
        self._hold_mask(mask)
        return self.__store.context_mask_identity(mask)

    def context_mask_subset(self, left, right):
        self._hold_mask(left)
        self._hold_mask(right)
        return self.__store.context_mask_subset(left, right)

    def context_mask_overlap(self, left, right):
        self._hold_mask(left)
        self._hold_mask(right)
        return self.__store.context_mask_overlap(left, right)

    def footprint_dimension(self, span):
        """The dimension of a span; the target the span names must be held (the Store reads it)."""
        if isinstance(span, Mapping) and type(span.get('target_ref')) is str:
            self.__readable(span['target_ref'])
        return self.__store.footprint_dimension(span)

    def footprint_from_mapping(self, mapping):
        """The footprint of a mapping; every subject its path names must be held (the Store reads each)."""
        path = mapping.get('path') if isinstance(mapping, Mapping) else None
        for step in path if isinstance(path, (list, tuple)) else ():
            if isinstance(step, Mapping) and type(step.get('subject_ref')) is str:
                self.__readable(step['subject_ref'])
        return self.__store.footprint_from_mapping(mapping)

    def assessment_key(self, record):
        """The lineage key of an assessment record; a ``context_account_scope`` it carries is a context mask."""
        if isinstance(record, Mapping) and 'context_account_scope' in record:
            self._hold_mask(record['context_account_scope'])
        return self.__store.assessment_key(record)

    def reasoning_schema(self):
        """The JSON schema of a reasoning payload (the envelope ``commit_reasoning`` takes)."""
        return self.__store.reasoning_schema()

    # -- the measures of a scope and of a context mask ---------------------------------------
    def scope_measure(self, scope, target_ref):
        """The position mass of ``target_ref`` within ``scope`` (the Store's ``scope_measure``). The scope's
        subjects and read selections must be held; a target that is not one of them is the Store's
        ``target_outside_scope``."""
        return self.__store.scope_measure(self._scope(scope), target_ref)

    def iter_scope_coverage(self, scope, target_ref=None):
        """The spans of ``scope`` (of ``target_ref`` only, when given), streamed. The scope's subjects and read
        selections must be held; of a held read library the spans name its members (their identities and
        lengths are the library's fixed geometry)."""
        return self.__store.iter_scope_coverage(self._scope(scope), target_ref)

    def read_subject_ref(self, library_ref, member_ref):
        """The reference of the read subject of ``member_ref`` in the held read library ``library_ref``. It is a
        name only: reading the read subject needs that reference held."""
        self.__readable(library_ref)
        return self.__store.read_subject_ref(library_ref, member_ref)

    def context_mask_measure(self, mask, target_ref):
        """The position mass of ``target_ref`` within the context mask (zero when the mask does not name it)."""
        self._hold_mask(mask)
        return self.__store.context_mask_measure(mask, target_ref)

    def context_mask_target_full(self, mask, target_ref):
        """Whether the context mask covers the whole of ``target_ref``."""
        self._hold_mask(mask)
        return self.__store.context_mask_target_full(mask, target_ref)

    def context_mask_dimension_segments(self, mask, dimension_ref):
        """The segments of the context mask on one dimension (an input, or a read subject of a held library). As
        for ``scope_dimension_segments`` the record of ``dimension_ref`` is read to find its target; the answer
        is empty unless that target is one of the mask's subjects, which must be held."""
        self._hold_mask(mask)
        return self.__store.context_mask_dimension_segments(mask, dimension_ref)

    def context_mask_positions(self, mask, target_ref, limit=None, offset=0):
        """The disjoint position intervals of the context mask on ``target_ref``: ``{'target_ref', 'member_ref',
        'dimension_ref', 'read_ref', 'length', 'unit', 'start', 'end'}``, ordered by member, unit, start and end
        (all of them, or the page ``limit`` and ``offset``). These are the rows the Store's
        ``context_mask_target_query`` describes; the query itself is run here and its SQL is not handed out."""
        if type(offset) is not int or offset < 0 or (limit is not None and (type(limit) is not int or limit < 0)):
            raise ValueError('invalid_page')
        self._hold_mask(mask)
        sql, parameters = self.__store.context_mask_target_query(mask, target_ref)
        query = ('SELECT target_ref,member_ref,dimension_ref,read_ref,length,unit,start,end FROM (' + sql + ') '
                 "ORDER BY coalesce(member_ref,''),unit,start,end LIMIT ? OFFSET ?")
        return [dict(row) for row in self.__store._db.execute(
            query, (*parameters, -1 if limit is None else limit, offset))]

    # -- the Store's ownership rules, over held records ---------------------------------------
    def assessment_write_extent(self, ref):
        """The attributed extent of the held assessment ``ref`` (the Store's ``_assessment_write_extent`` of the
        stored record): its merged original-unit segments, ``[]`` for an unlocalized inferred extent, ``None``
        when the geometry is unknown. Every record the rule reads must be held too: the assessment's hypothesis
        and observation, the subjects those name and what the coverage and mapping of each subject follow."""
        self.__readable(ref)
        record = self.__store.get(ref)
        if record['record_type'] != 'assessment':
            raise ValueError('assessment_reference_required:' + str(ref))
        return self.__rules()._assessment_write_extent(record)

    def assert_library_write_scope(self, ref, scope):
        """Raise the Store's ``ContractError`` unless the held record ``ref`` is owned within ``scope`` (the
        Store's ``_assert_library_write_scope`` of the stored record; a revisioned record is checked as proposed
        and as the current revision). It checks ownership of original members, never truth. The scope's subjects
        and every record the rule reads must be held; the members of a held read selection are read with it."""
        self.__readable(ref)
        record = self.__store.get(ref)
        kind = record['record_type']
        normalized = self._scope(scope)
        self.__rules()._assert_library_write_scope(
            'annotation' if kind == 'interpretation_account' else kind, record, normalized,
            current=record if kind in REVISIONED_KINDS else None)

    def named_references(self, ref):
        """Every reference the held Store record ``ref`` names, in the Store's own order (its ``_refs`` rule): what
        a ``msg_to_child`` or a ``final_to_parent`` must name beside ``ref`` for a receiver that will follow
        them. Naming is not holding: each is read only when it is held."""
        if is_row_ref(ref):
            raise ValueError('store_record_reference_required:' + str(ref))
        self.__readable(ref)
        return list(self.__store._refs(self.__store.get(ref)))

    # -- the original reads of a read library ---------------------------------------------------
    def _library(self, library_ref, scope):
        """Custody of a read of the reads of ``library_ref`` within ``scope``: the library must be held, and so
        must every collection it binds (its reads are rows of those collections, read through them like any
        collection member) and every subject and read selection the scope names. The Store's normalized scope;
        no ``scope`` is the whole library."""
        self.__readable(library_ref)
        target = self.__store.get_input(library_ref)
        for ref in target['collection_refs'] if libraries.is_library(target) else ():
            self.__readable(ref)
        return self._scope({'subject_refs': [library_ref]} if scope is None else scope)

    def library_members(self, library_ref, *, selection_ref=None, offset=0, limit=50, scope=None):
        """One page of the original reads of the held read library ``library_ref`` within ``scope`` (the whole
        library when none is given), in the library's order; only the reads of the read selection
        ``selection_ref`` (or of the scope's selection of this library) when there is one. The Store's own page
        (``library_targets.member_page``): ``{'library_ref', 'selection_ref', 'members', 'total', 'offset',
        'limit', 'next_offset', 'next_query'}``, each member the read subject in its model view (its name and
        description as previews). The library, every collection it binds, the scope's subjects and read
        selections and ``selection_ref`` must be held. A member's ``id`` is a name: reading that read subject by
        its reference needs the reference held; its sequence is read through its held collection
        (``material_member(member['member_ref'])``)."""
        normalized = self._library(library_ref, scope)
        if selection_ref is not None:
            self.__readable(selection_ref)
        return libraries.member_page(self.__store, library_ref, scope=normalized, selection_ref=selection_ref,
                                     offset=offset, limit=limit)

    def selection_members(self, selection_ref, limit=None, offset=0):
        """The references of the reads the held read selection ``selection_ref`` froze, ordered by reference (all
        of them, or the page ``limit`` and ``offset``). They are the selection's own rows, like the members of a
        collection, and they are names: reading a read subject needs its reference held, or is done through the
        held library (``library_members(library_ref, selection_ref=...)``)."""
        if type(offset) is not int or offset < 0 or (limit is not None and (type(limit) is not int or limit < 0)):
            raise ValueError('invalid_page')
        self.__readable(selection_ref)
        self.__store._require(selection_ref, {'read_selection'})
        return [row[0] for row in self.__store._db.execute(
            'SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref '
            'LIMIT ? OFFSET ?', (selection_ref, -1 if limit is None else limit, offset))]

    # -- the diagnostics of the Episode's tool outcomes -------------------------------------------
    def is_diagnostic_ref(self, ref):
        """Whether the held record ``ref`` is the diagnostic of a tool outcome of this Episode: the value one of
        its tool units returned names it under a key ``diagnostic_ref`` (at any depth). The units are the
        recorded ones and, once its tool has returned, the unit being completed; the unit whose tool is still
        running has no outcome yet. Another Episode's diagnostic is not one of this Episode's, whoever holds
        it."""
        self.__readable(ref)
        return self.__custody.is_diagnostic(ref)

    # -- work tables --------------------------------------------------------------------------
    def table(self, declaration):
        """The held rows of the declared work table (read-only)."""
        return TableReader(self.__rows, self.__custody, declaration)


class ScopedStore(RecordReader):
    """The custody-scoped Store one Episode's tools use (see the module docstring)."""

    def __init__(self, store, custody, rows, owner):
        super().__init__(store, custody, rows, unit=True)
        self.__store, self.__custody, self.__rows, self.__owner = store, custody, rows, tuple(owner)
        self.__scratch = ScratchRoot(store)
        self.__sections = set()     # the named sections the running tool is inside

    def __guard(self):
        """A custody write may run inside a transaction only when the scoped store opened it (so that its
        receipts follow the commit or the rollback)."""
        if self.__store._db.in_transaction and not self.__custody.in_transaction():
            raise CustodyError('store_write_inside_a_transaction_the_scoped_store_did_not_open')

    def __named(self, value, *, aliases=False):
        """Every record a write names must be readable by the writing unit. ``aliases``: a reference ``@name``
        names a row of the same payload, not a record."""
        for ref in named_references(value):
            if not (aliases and ref.startswith('@')):
                self._readable(ref)

    def __produce_named(self, row):
        """Hold what a creating call returned and, transitively, the records it names that the Episode does not
        hold yet (the call wrote them, or wrote the same content)."""
        frontier = [row]
        if 'id' in row:
            self.__custody.produced(row['id'])
        while frontier:
            for ref in named_references(frontier.pop()):
                if not self.__custody.holds(ref):
                    self.__custody.produced(ref)
                    frontier.append(self.__store.get(ref))

    # -- writes, receipted as produced by this unit --------------------------------------
    def put(self, kind, record, *, origin, scope=None):
        """Write a Store record; the Episode then holds it as produced at this unit. Every record ``record`` names,
        and every subject of ``scope``, must be readable."""
        self.__named(record)
        self._hold_scope(scope)
        with self.transaction():
            stored = self.__store.put(kind, record, origin=origin, scope=scope)
            self.__custody.produced(stored['id'])
        return stored

    def artifact(self, data, media_type='application/octet-stream'):
        """Write a Store artifact; the Episode then holds it as produced at this unit."""
        with self.transaction():
            ref = self.__store.artifact(data, media_type)
            self.__custody.produced(ref)
        return ref

    def artifact_file(self, path, media_type='application/octet-stream'):
        """Write the bytes of the file ``path`` as a Store artifact without loading them (the Store's own
        capture: hashed while it is copied); the Episode then holds the artifact as produced at this unit. The
        file is one the unit can read: a file of its scratch directory, or one a service handed it."""
        self.__custody.require_unit('record_written')      # before the file is copied
        with self.transaction():
            ref = capture_artifact_file(self.__store, path, media_type)
            self.__custody.produced(ref)
        return ref

    def artifact_stream(self, stream, media_type='application/octet-stream'):
        """Write a stream as a Store artifact without holding it in memory: ``stream`` is a binary file object
        (``read``) or an iterable of ``bytes`` (a download in chunks). The Episode then holds the artifact as
        produced at this unit. The bytes are gathered in a file of the system's own, which is removed."""
        self.__custody.require_unit('artifact_stream')
        read = getattr(stream, 'read', None)
        chunks = iter(lambda: read(1024 * 1024), b'') if callable(read) else iter(stream)
        directory = self.__scratch.create(self.__owner, self.__custody.unit, 'stream')
        try:
            gathered = directory / 'stream'
            with gathered.open('xb') as output:
                for chunk in chunks:
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        raise TypeError('artifact_stream_requires_bytes')
                    output.write(chunk)
            return self.artifact_file(gathered, media_type)
        finally:
            self.__scratch.remove(directory)

    def caller_source(self, value, provider):
        """Write a value the caller supplied (closed JSON) as a source record of ``provider`` over its canonical
        bytes (the Store's ``_caller_source``); the Episode holds the source and its artifact as produced."""
        with self.transaction():
            source = self.__store._caller_source(value, provider)
            self.__produce_named(source)
        return source

    def commit_reasoning(self, payload, scope, operation_key):
        """Commit a reasoning payload. Every record the payload names must be readable. The account owner the
        Store is given is this Episode (run id, episode id); every record the commit created or changed is held
        as produced. The Store's commit is idempotent on ``operation_key`` (pass ``ctx.operation_key``):
        committing the same payload again returns the first result."""
        self.__named(payload, aliases=True)
        scope = self._scope(scope)
        with self.transaction():
            result = self.__store.commit_reasoning(payload, scope, operation_key, account_owner=self.__owner)
            for ref in (*result['record_refs'], *result['changed_record_refs']):
                self.__custody.produced(ref)
        return result

    def register_material(self, input_path=None, *, source_ref=None, **options):
        """Register material (the Store's ``register_material``); a ``source_ref`` must be readable. The Episode
        holds the material record and the records it names that the call created (its source, the source's
        artifact, its contexts)."""
        if source_ref is not None:
            self._readable(source_ref)
        with self.transaction():
            material = self.__store.register_material(input_path, source_ref=source_ref, **options)
            self.__produce_named(material)
        return material

    def create_problem(self, input_path=None, **options):
        """Create the Store's problem (the Store's ``create_problem``). The Episode holds the problem's subjects
        and, transitively, the records they name. It also holds the problem's own reference (``problem_...``) as
        produced; that reference is of no kind an inventory lists and the problem is read with ``problem()``."""
        with self.transaction():
            problem = self.__store.create_problem(input_path, **options)
            self.__produce_named(problem)
        return problem

    def parse_material(self, material_ref, *, format=None):
        """Parse the held material (the Store's ``parse_material``). The material and every record it names (its
        source, its sample, library and context records) must be readable. The Episode holds the parse attempt,
        the collection and the sources the parse created; it reads the collection's members through the
        collection."""
        self._readable(material_ref)
        self.__named(self.__store.get(material_ref))
        with self.transaction():
            parsed = self.__store.parse_material(material_ref, format=format)
            self.__produce_named(parsed)
        return parsed

    def material_header(self, member_ref, *, offset=0, limit=12000):
        """A window of a member's title. The title's artifact (written here when the member is stored packed) is
        held as produced."""
        self._member(member_ref)
        with self.transaction():
            header = self.__store.material_header(member_ref, offset=offset, limit=limit)
            self.__custody.produced(header['artifact_ref'])
        return header

    def material_reference(self, member_ref):
        """Make the member a reusable reference record (the Store's ``material_reference``). The member's
        collection and every record the collection names must be readable. The Episode holds the reference, its
        context record, the member and the member's component artifacts."""
        self._member(member_ref)
        collection = self.__store.get(self.__store.get(member_ref)['collection_ref'])
        self._readable(collection['id'])
        self.__named(collection)
        with self.transaction():
            reference = self.__store.material_reference(member_ref)
            self.__produce_named(reference)
        return reference

    def select_library_members(self, library_ref, *, member_refs=None, ordinal_ranges=None, scope=None):
        """Freeze an explicit selection of the original reads of the held read library ``library_ref`` (the
        Store's ``library_targets.select``): the reads of the collection members ``member_refs``, or those at
        the library ordinals ``ordinal_ranges`` (``[{'start', 'end'}, ...]``), within ``scope`` (the whole
        library when none is given). The ``read_selection`` record the Store wrote, with the selection's rows;
        the Episode holds it as produced at this unit. The library, every collection it binds, the scope's
        subjects and read selections and every member named must be held (a member through its collection)."""
        normalized = self._library(library_ref, scope)
        for ref in member_refs if isinstance(member_refs, (list, tuple)) else ():
            if type(ref) is str:
                self._member(ref)
        with self.transaction():
            selected = libraries.select(self.__store, library_ref, scope=normalized, member_refs=member_refs,
                                        ordinal_ranges=ordinal_ranges)
            self.__custody.produced(selected['id'])
        return selected

    def reclaim(self, ref):
        """Take over a record the abandoned attempt of this unit produced (``ctx.abandoned``) as produced by the
        attempt now running; an abandoned work-table row is written again as that attempt left it."""
        with self.transaction():
            self.__custody.reclaim(ref)

    def table(self, declaration):
        """The declared work table: the held rows, and this Episode's own rows to write."""
        return ScopedTable(self.__rows, self.__custody, declaration, self.__owner, self.transaction,
                           self._readable)

    # -- files of the unit's own, and its sections ----------------------------------------------
    @contextmanager
    def scratch(self, name='work'):
        """A scratch directory of the running unit (``scratch.ScratchDirectory``: ``path``, ``copy_artifact(ref,
        name)``, ``await compute(function, ...)``), removed with everything in it when the block is left. Nothing
        in it is a record: a result leaves it as a write of this store (``artifact_file``). ``name`` labels the
        directory (lowercase letters, digits, underscore and hyphen)."""
        if type(name) is not str or not name or not all(char.isascii() and (char.isalnum() or char in '_-')
                                                         for char in name) or name != name.lower():
            raise ValueError('scratch_directory_name_must_be_a_lowercase_label:' + repr(name))
        self.__custody.opened(SCRATCH)
        path = None
        try:
            path = self.__scratch.create(self.__owner, self.__custody.unit, name)
            directory = ScratchDirectory(path, self, self.__custody)
            try:
                yield directory
            finally:
                directory._close()
        finally:
            if path is not None:
                self.__scratch.remove(path)
            self.__custody.closed(SCRATCH)

    @contextmanager
    def section(self, name):
        """Enter the named section of this unit's work; the value is whether this is the outermost entry (``True``)
        or the section is already entered further up the call (``False``). A library function whose work calls
        itself again (a sheet update that refreshes its dependents, each refreshed by the same function) does its
        once-per-update part only when it is the outermost. The state is this Episode's and lasts for the call."""
        if type(name) is not str or not name:
            raise ValueError('section_name_must_be_non_empty_text')
        self.__custody.require_unit('section')
        outer = name not in self.__sections
        if outer:
            self.__sections.add(name)
        try:
            yield outer
        finally:
            if outer:
                self.__sections.discard(name)

    # -- transactions ------------------------------------------------------------------------
    def in_transaction(self):
        return self.__store._db.in_transaction

    @contextmanager
    def __receipted(self, scope):
        self.__guard()
        self.__custody.begin_transaction()
        try:
            with scope():
                yield self
                self.__custody.seal_transaction()
        except BaseException:
            self.__custody.rollback_transaction()
            raise
        self.__custody.commit_transaction()

    def transaction(self):
        """A Store transaction; what is written inside is receipted when it commits and not at all when it
        rolls back."""
        return self.__receipted(self.__store.transaction)

    def read_snapshot(self):
        return self.__receipted(self.__store.read_snapshot)
