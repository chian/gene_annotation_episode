"""Persist selected reference reaction constraints and exact admitted subsets.

This adapter owns source custody and immutable selected-operation records. It
does not choose investigations, interpret experiments, add observations or
recompute a saved numerical sheet during replay.

Carried from ``root/a110/literature_reaction_storage.py``, ``root/a110/library/reaction_population.py`` and the
``populate_source`` of ``root/a110/library/reaction_source_selection.py`` at ``97308b94c`` onto the custody-scoped
store (``store``: ``ctx.store`` of the populating tool unit, or ``records`` for reads). What was the old Store's:

* the source an Episode may read was "received" (``context.received_record_refs``); it is now a source the
  Episode holds (``store.holds``), in the commission's scope and, for a reading below a page, derived from the
  page's source;
* the ``literature_reaction_operations`` ledger (re-entry on the same operation key, the signature check) is
  deleted: the system journals each unit's attempt. The sheets one Episode saved are the work table ``OPERATIONS``;
* ``literature_reaction_received``, ``literature_reaction_semantic_received``, the delivery bindings and every read
  of ``runtime_*`` are deleted: that is custody and old-runner machinery;
* the saved cells are rows of ``CELLS`` (``SheetCustody.publish_cells``); a sheet's two views (R9) are its cell
  rows: ``literature_reaction_cells`` for a ``literature_reaction_record_v2`` sheet and
  ``literature_reaction_semantic_cells`` (the same cells with their source-bound meanings, the comparison reduction
  and the nominal limiting resources) for a ``literature_reaction_record_v3`` sheet;
* the A110 ``literature_sheet_updates`` policy was ``None`` (no automatic main sheet, no dependent sheets), so a
  sheet's revision family is its provider and arguments and the latest sheet of a family is its current one
  (work table ``CURRENT``); an ``experiment_assessment`` revision must name the current head of its experiment and
  question and supersedes it.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from episode_runtime import TableDeclaration

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_native_observations import (
    native_row_references, publish_native_observations)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_population_contracts import (
    BINDINGS, COMPONENTS, EXPERIMENT_TYPES, FORMULA_CODES, LITERAL_REFERENCE_TYPES, MEANINGS_INPUT_VERSION,
    MEANINGS_RECORD_VERSION, PROVIDER, _direct_references, _metadata, assessments, binding_references,
    literal_reference_role, populate_reaction_constraints, publish_meanings, reaction_direct_references,
    reaction_population_schema, read_reaction_inputs, semantic_metadata, source_literal_label)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_report_contracts import (
    reaction_cells_schema, reaction_semantic_cells_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.biochemical_feasibility_evidence.literature_reaction_native_inputs import (
    TRACE_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.biochemical_feasibility_evidence.reaction_source_selection import (
    OPERATION as SOURCE_OPERATION, PROVIDER as SELECTION_PROVIDER, VERSION as SELECTION_VERSION,
    _source_references, reaction_source_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.partner_presence_evidence.literature_assay_inputs import (
    materialize_text_witness_inputs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_sheet_custody import (
    SheetCustody)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    ContractError, canonical, identity, source_location_inputs, validate_schema)

RECORD_VERSION = 'literature_reaction_record_v2'
OPERATIONS = TableDeclaration(name='biochemical_feasibility_literature_reaction_operations', columns=('sheet_ref',),
                              key=('sheet_ref',), record_refs=('sheet_ref',))
CELLS = TableDeclaration(name='biochemical_feasibility_literature_reaction_cells',
                         columns=('sheet_ref', 'component', 'cell'), key=('sheet_ref', 'component'),
                         record_refs=('sheet_ref',))
CURRENT = TableDeclaration(name='biochemical_feasibility_literature_reaction_current', columns=('family', 'sheet_ref'),
                           key=('family',), record_refs=('sheet_ref',))


def family(args):
    """The revision family of a sheet: its provider and its arguments, the assessment's revision fields left out."""
    use = {key: value for key, value in args.items() if key != 'experiment_assessment'}
    return identity('literature_scientific_sheet_use', {'provider': PROVIDER, 'use': use})


def _witnessed(value):
    if isinstance(value, dict):
        if set(value) == {'source_ref', 'representation', 'start', 'end', 'quote', 'artifact_ref'}:
            yield value
        else:
            for child in value.values():
                yield from _witnessed(child)
    elif isinstance(value, list):
        for child in value:
            yield from _witnessed(child)


class LiteratureReactionRepository(SheetCustody):
    """Saved reference reaction-constraint sheets over the custody-scoped store (``store``) of the running unit."""
    experiment_types = EXPERIMENT_TYPES
    provider = PROVIDER
    components = COMPONENTS
    record_version = RECORD_VERSION
    operations = OPERATIONS
    cells_table = CELLS
    binding_fields = tuple(BINDINGS)

    def __init__(self, store):
        self.store = store

    def _provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('literature_source_outside_scope')
        row = self.store.get(reference)
        if row['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return row

    def _source(self, scope, page_source_ref, reference):
        """A direct input: a source this Episode holds, in scope, derived from the assigned page's source when the
        Episode reads below a page."""
        if not self.store.holds(reference):
            raise ContractError('literature_source_not_received')
        source = self._provenance(scope, reference)
        if page_source_ref is not None:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(scope, current)
                if current == page_source_ref:
                    break
                pending.extend(ancestor.get('parent_source_refs', ()))
            else:
                raise ContractError('literature_reading_outside_assigned_source')
        return source

    def _authorize_assessment(self, scope, page_source_ref, value):
        """The old ``authorize_assessment``: an explicitly held, sourced assay identity; never inferred. A subject or
        construct literal of an earlier sheet is not an experiment."""
        assessments.validate_assessment(value, self.experiment_types)
        ref = value['experiment_ref']
        if not self.store.holds(ref):
            raise ContractError('experimental_experiment_not_received')
        record = self.store.get(ref)
        if record['record_type'] != 'reference' or record.get('reference_type') != 'assay':
            raise ContractError('experimental_experiment_reference_required')
        if not self.store.reference_subset([ref], plain(scope)):
            raise ContractError('experimental_experiment_outside_scope')
        self._source(scope, page_source_ref, record['source_ref'])
        if value['revises_sheet_ref'] is not None:
            self._source(scope, None, value['revises_sheet_ref'])
        if literal_reference_role(record) in {'molecule', 'construct'}:
            raise ContractError('literature_reaction_experiment_identity_is_subject_or_construct_literal')

    def populate(self, scope, page_source_ref, arguments, operation_key):
        """Read the selected dataset or native selection and the literal witnesses, calculate the fifteen cells and
        save the sheet, its literal and meaning bindings, its native observations, its cells, its revision family
        and its assessment in one transaction. ``page_source_ref`` is the assigned page's source, or ``None``."""
        args = plain(arguments)
        validate_schema(args, reaction_population_schema(include_assessment=True))
        assessment = args.get('experiment_assessment')
        if assessment is not None:
            self._authorize_assessment(scope, page_source_ref, assessment)
        direct = _direct_references(args)
        for reference in direct:
            self._source(scope, page_source_ref, reference)
        source = self.store.get(args['source_ref'])

        def read_source(reference, representation):
            row = self._source(scope, page_source_ref, reference)
            if representation not in ('original', 'text'):
                raise ContractError('literature_source_representation_required')
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
        extraction = read_reaction_inputs(args, read_source=read_source)
        direct = reaction_direct_references(extraction, direct)
        if set(extraction['sources']) != set(direct):
            raise ContractError('literature_reaction_direct_source_mismatch')
        sheet = populate_reaction_constraints(extraction['calculation_inputs'])
        parents, seen = list(direct), set(direct)
        if assessment is not None:
            parents.append(self.store.get(assessment['experiment_ref'])['source_ref'])
            if assessment['revises_sheet_ref'] is not None:
                parents.append(assessment['revises_sheet_ref'])
            parents = list(dict.fromkeys(parents))
            seen = set(parents)
        cursor = 0
        while cursor < len(parents):
            reference = parents[cursor]
            cursor += 1
            for parent in self.store.get(reference).get('parent_source_refs', ()):
                self._provenance(scope, parent)
                if parent not in seen:
                    seen.add(parent)
                    parents.append(parent)
        record_version = (MEANINGS_RECORD_VERSION if extraction['version'] == MEANINGS_INPUT_VERSION
                          else self.record_version)
        payload = {'version': record_version, 'input_source_ref': source['id'],
                   'input_artifact_ref': source['artifact_ref'], 'input_source_refs': parents,
                   'direct_input_source_refs': direct, 'data_source_ref': args['data_source_ref'],
                   'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            if assessment is not None:
                assessments.check_revision(self, assessment)
            created = []

            def publish(kind, record):
                new = not self.store.holds(identity(kind, {'origin': 'tool', 'record': record}))
                row = self.store.put(kind, record, origin='tool', scope=plain(scope))
                if new:
                    created.append(row['id'])
                return row['id']
            bindings = {}
            for field, (literal, kind) in BINDINGS.items():
                if field == 'experiment_ref' and assessment is not None:
                    bindings[field] = assessment['experiment_ref']
                    continue
                entry = extraction['literals'][literal]
                if entry is None:
                    bindings[field] = None
                    continue
                witness = entry['witness']
                anchor = {name: witness[name] for name in ('source_ref', 'artifact_ref', 'start', 'end', 'quote')}
                common = {'source_ref': witness['source_ref'], 'anchor': anchor}
                accession = identity('reaction_literal', {'field': literal, **anchor})
                label = source_literal_label(entry['value'])
                if kind == 'reference':
                    record = {**common, 'reference_type': LITERAL_REFERENCE_TYPES[literal], 'accession': accession,
                              'label': label, 'sequence_ref': None, 'molecule': None, 'length': None,
                              'term_refs': [], 'context_refs': []}
                elif kind == 'term':
                    record = {**common, 'namespace': 'literature_reaction_' + literal, 'accession': accession,
                              'label': label, 'term_type': 'other'}
                else:
                    record = {**common, 'context_type': 'assay_condition', 'name': label, 'attributes': [],
                              'related_refs': []}
                bindings[field] = publish(kind, record)
            if assessment is not None:
                payload['experiment_assessment'] = deepcopy(assessment)
            payload['experimental_bindings'] = bindings
            semantic_bindings = (publish_meanings(extraction, publish) if record_version == MEANINGS_RECORD_VERSION
                                 else None)
            if semantic_bindings is not None:
                payload['semantic_bindings'] = semantic_bindings
            metadata = _metadata(extraction, sheet)
            if semantic_bindings is not None:
                metadata = semantic_metadata(metadata, semantic_bindings, extraction['calculation_inputs'], sheet)
            native_rows = None
            if 'native_evidence' in extraction:
                native_rows = publish_native_observations(extraction, bindings, semantic_bindings, publish)
                payload['native_observations'] = native_rows
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request = self.store.artifact(canonical({'operation_key': operation_key, 'arguments': args,
                                                     'scope': plain(scope)}), 'application/json')
            sheet_ref = publish('source', {'provider': self.provider, 'accession': None, 'uri': None,
                                           'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
                                           'version': record_version, 'retrieved_at': None,
                                           'parent_source_refs': parents})
            self.store.table(OPERATIONS).put({'sheet_ref': sheet_ref})
            self.store.table(CURRENT).put({'family': family(args), 'sheet_ref': sheet_ref})
            if assessment is not None:
                assessments.record_assessment(self.store, sheet_ref, assessment)
            self.publish_cells(sheet_ref)
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'key': operation_key}),
                       'record_refs': list(dict.fromkeys([
                           sheet_ref, *parents, *(reference for reference in bindings.values() if reference),
                           *(binding_references(semantic_bindings) if semantic_bindings is not None else []),
                           *(native_row_references(native_rows) if native_rows is not None else [])])),
                       'changed_record_refs': created,
                       'result': {'sheet_ref': sheet_ref, 'cells': sheet['cells'],
                                  'assay_interpretation': extraction['literals'], **metadata,
                                  **({'native_observations': native_rows} if native_rows is not None else {})},
                       'feedback': None}
            if assessment is not None:
                outcome['result']['experiment_assessment'] = deepcopy(assessment)
        return outcome

    def populate_source(self, scope, page_source_ref, arguments, operation_key):
        """``literature.reaction.source.populate`` (old ``reaction_source_selection.populate_source``): one action
        with a retained selector intermediate. Only the newly created selector source joins what the population
        reads; every evidence source must already be held and within the original scope, and the population
        independently checks every actually read witness."""
        args = plain(arguments)
        validate_schema(args, reaction_source_population_schema())
        sources = _source_references(args)
        for reference in sources:
            self._source(scope, page_source_ref, reference)
        assessment = args.get('experiment_assessment')
        if assessment is not None:
            self._authorize_assessment(scope, page_source_ref, assessment)
        with self.store.transaction():
            artifact = self.store.artifact(canonical(args['native_selection']), 'application/json')
            request = self.store.artifact(canonical({'operation': SOURCE_OPERATION, 'operation_key': operation_key,
                                                     'scope': plain(scope), 'arguments': args}), 'application/json')
            selected = self.store.put('source', {'provider': SELECTION_PROVIDER, 'accession': None, 'uri': None,
                                                 'artifact_ref': artifact, 'text_ref': artifact,
                                                 'request_ref': request, 'version': SELECTION_VERSION,
                                                 'retrieved_at': None, 'parent_source_refs': sources},
                                      origin='tool', scope=plain(scope))
            operands = {name: value for name, value in args.items() if name != 'native_selection'}
            operands['data_source_ref'] = selected['id']
            outcome = self.populate(scope, page_source_ref, operands, operation_key)
            return {**outcome, 'record_refs': list(dict.fromkeys([*outcome['record_refs'], selected['id']])),
                    'changed_record_refs': list(dict.fromkeys([*outcome['changed_record_refs'], selected['id']])),
                    'result': {**outcome['result'], 'selection_source_ref': selected['id']}}

    def read(self, sheet_ref):
        """The saved sheet, checked against the request it was saved for (and, for a sheet with source-bound
        meanings, against the meaning bindings its extraction publishes)."""
        source = self.store.get(sheet_ref)
        if source['record_type'] != 'source' or source['provider'] != self.provider or source['origin'] != 'tool':
            raise ContractError('literature_reaction_sheet_required')
        payload = self.store.get_artifact(source['artifact_ref'])
        saved = json.loads(payload)
        request = json.loads(self.store.get_artifact(source['request_ref']))
        args, extraction = request['arguments'], saved['extraction']
        if (saved['version'] != source['version']
                or source['version'] not in (RECORD_VERSION, MEANINGS_RECORD_VERSION)
                or source['parent_source_refs'] != saved['input_source_refs']
                or args['source_ref'] != saved['input_source_ref']
                or saved['direct_input_source_refs'] != reaction_direct_references(extraction, _direct_references(args))
                or set(extraction['sources']) != set(saved['direct_input_source_refs'])
                or self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']
                or saved['data_source_ref'] != args['data_source_ref'] or extraction['arguments'] != args
                or saved['sheet']['inputs'] != extraction['calculation_inputs']):
            raise ContractError('literature_reaction_sheet_source_mismatch')
        if 'native_evidence' in extraction:
            if extraction['native_evidence']['version'] != TRACE_VERSION:
                raise ContractError('literature_reaction_native_saved_mismatch')
            for witness in _witnessed(extraction['native_evidence']):
                row = self.store.get(witness['source_ref'])
                artifact = row['artifact_ref'] if witness['representation'] == 'original' else row.get('text_ref')
                if artifact != witness['artifact_ref'] or witness['source_ref'] not in saved['direct_input_source_refs']:
                    raise ContractError('literature_reaction_native_source_mismatch')
        if source['version'] == MEANINGS_RECORD_VERSION:
            if ('artifact_' + hashlib.sha256(payload).hexdigest() != source['artifact_ref']
                    or extraction['version'] != MEANINGS_INPUT_VERSION):
                raise ContractError('literature_reaction_semantic_saved_mismatch')

            def validate_published(kind, record):
                expected = identity(kind, {'origin': 'tool', 'record': record})
                if self.store.get(expected) != {'id': expected, 'record_type': kind, 'origin': 'tool', **record}:
                    raise ContractError('literature_reaction_semantic_binding_mismatch')
                return expected
            if publish_meanings(extraction, validate_published) != saved['semantic_bindings']:
                raise ContractError('literature_reaction_semantic_binding_mismatch')
        assessments.validate_saved_assessment(self, saved, request, sheet_ref)
        return saved

    def row_metadata(self, saved):
        metadata = _metadata(saved['extraction'], saved['sheet'])
        if saved['version'] == MEANINGS_RECORD_VERSION:
            return semantic_metadata(metadata, saved['semantic_bindings'], saved['extraction']['calculation_inputs'],
                                     saved['sheet'])
        return metadata

    def project_cells(self, sheet_refs, components=None):
        """The selected cells of saved sheets in the view the sheet supports (R9): the numerical cells of a
        ``literature_reaction_record_v2`` sheet (``literature_reaction_cells``), or the numerical cells with their
        source-bound meanings of a ``literature_reaction_record_v3`` sheet (``literature_reaction_semantic_cells``).
        The cell formulas stay in the sheet; each row names its fixed formula code."""
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError('literature_reaction_component_selection_invalid')
        rows, versions = [], set()
        for reference in dict.fromkeys(sheet_refs):
            saved = self.read(reference)
            versions.add(saved['version'])
            for name in components:
                cell = {key: deepcopy(value) for key, value in saved['sheet']['cells'][name].items() if key != 'formula'}
                rows.append({'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'],
                             'data_source_ref': saved['data_source_ref'], **saved['experimental_bindings'],
                             'component': name, **cell, 'formula_code': FORMULA_CODES[name],
                             **self.row_metadata(saved)})
        if len(versions) > 1:
            raise ContractError('literature_reaction_projection_version_mismatch')
        validate_schema(rows, reaction_semantic_cells_schema() if versions == {MEANINGS_RECORD_VERSION}
                        else reaction_cells_schema())
        return rows

    def current_sheet_refs(self):
        """The current sheets of this Episode: the latest sheet of each revision family, less every sheet an
        assessment revision superseded. Earlier versions are retained, not current."""
        heads = {row['family']: row['sheet_ref'] for row in self.store.table(CURRENT).select()}
        superseded = {row['assessment']['revises_sheet_ref']
                      for row in self.store.table(assessments.ASSESSMENTS).select()}
        return [ref for ref in heads.values() if ref not in superseded]

    def current_assessments(self):
        return assessments.current_assessments(self)

    def assessment_history(self, sheet_ref):
        return assessments.assessment_history(self, sheet_ref)


POPULATE_DESCRIPTION = (
    'Populate reported reference reaction-ratio residuals, named-prediction comparisons and simple resource-budget '
    'components from an explicitly retained received dataset or native source-selection recipe. Read exact report '
    'ratio points or author a:b expressions, summary uncertainty/counts and simple resource quantities with source '
    'units. Preserve unknown replication, missing alternatives, calibration basis and incomplete resource '
    'constraints. Product-pair ratios, instrument signals, supplied reagent budgets and usable capacity have '
    'distinct meanings. This route does not parse NMR spectra, establish measured oxygen coupling, apply missing '
    'corrections or calculate target transfer/annotation credit.')
SOURCE_POPULATE_DESCRIPTION = (
    'Populate the original experimental reaction components directly from exact received source spans, without a '
    'prepared measurement dataset. Select reported ratio points or author a:b expressions, actual uncertainty/count '
    'witnesses and source-unit resource quantities. Explicit predictions, coefficients and demand retain their '
    'interpreted basis. The host saves the source-selection recipe and invokes the existing native readers, '
    'numerical calculator, publication and exact selected-cell returns. Unknown sampling, calibration, alternatives '
    'and resource completeness remain unknown; no spectrum digitization, biological activity, target transfer or new '
    'score is inferred.')


def population_input_schema():
    """What the model supplies to ``literature.reaction.populate`` (the old catalog entry's schema)."""
    return source_location_inputs(reaction_population_schema(include_assessment=True))


def source_population_input_schema():
    """What the model supplies to ``literature.reaction.source.populate``."""
    return source_location_inputs(reaction_source_population_schema())


def _materialized(repository, scope, page_source_ref, arguments):
    """The old ``_materialize_text_arguments``: each selected literal witness's quotation read from the held
    source bytes."""
    store = repository.store

    def read_source(reference, representation):
        source = repository._source(scope, page_source_ref, reference)
        artifact = source['artifact_ref'] if representation == 'original' else source.get('text_ref')
        if artifact is None:
            raise ContractError('literature_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    return materialize_text_witness_inputs(plain(arguments), read_source=read_source)


def populate_reaction_sheet(store, scope, page_source_ref, arguments, operation_key):
    """The ``literature.reaction.populate`` operation over ``ctx.store``."""
    repository = LiteratureReactionRepository(store)
    return repository.populate(scope, page_source_ref, _materialized(repository, scope, page_source_ref, arguments),
                               operation_key)


def populate_reaction_source_sheet(store, scope, page_source_ref, arguments, operation_key):
    """The ``literature.reaction.source.populate`` operation over ``ctx.store``."""
    repository = LiteratureReactionRepository(store)
    return repository.populate_source(scope, page_source_ref,
                                      _materialized(repository, scope, page_source_ref, arguments), operation_key)


__all__ = ['LiteratureReactionRepository', 'COMPONENTS', 'PROVIDER', 'OPERATIONS', 'CELLS', 'CURRENT',
           'POPULATE_DESCRIPTION', 'SOURCE_POPULATE_DESCRIPTION', 'population_input_schema',
           'source_population_input_schema', 'populate_reaction_sheet', 'populate_reaction_source_sheet']
