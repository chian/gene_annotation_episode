"""Selected immutable partner sheets and exact typed receipt projection.

Custody validates retained source records; it does not establish the truth of
supplied experimental interpretations. Saved reads never reopen source bytes or
repeat calculation. Ordinary episode accounting belongs to the caller.

Over the custody-scoped store (``store``: ``ctx.store`` of the populating tool unit, or ``records`` for reads).
What was the old Store's: a source an Episode may read was "received" (``context.received_record_refs``); it is now a
source the Episode holds (``store.holds``), in the commission's scope and, below an assigned page, derived from the
page's source. The saved cells are rows of ``CELLS`` (``SheetCustody.publish_cells``), the sheets one Episode saved
rows of ``OPERATIONS``, the current sheet of each revision family a row of ``CURRENT``.
"""
from __future__ import annotations
from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_sheet_custody import SheetCustody
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import BINDINGS, COMPONENTS, ContractError, EXPERIMENT_TYPES, FORMULA_CODES, PROVIDER, _metadata, assessments, canonical, deepcopy, json, literal_reference_role, partner_cells_schema, partner_population_schema, partner_source_population_schema, plain, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_partner_sheet_population import populate as _populate_partner_sheet
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.partner_presence_evidence.literature_assay_inputs import materialize_text_witness_inputs
from gene_annotation_episode.episodic_workflow.episode_support.literature.validation.literature_partner_saved_validation import _validate_native_saved as _science_validate_native_saved, _validate_saved as _science_validate_saved, _validate_scientific_saved as _science_validate_scientific_saved

OPERATIONS = TableDeclaration(name='partner_presence_literature_partner_operations', columns=('sheet_ref',), key=('sheet_ref',), record_refs=('sheet_ref',))
CELLS = TableDeclaration(name='partner_presence_literature_partner_cells', columns=('sheet_ref', 'component', 'cell'), key=('sheet_ref', 'component'), record_refs=('sheet_ref',))
CURRENT = TableDeclaration(name='partner_presence_literature_partner_current', columns=('family', 'sheet_ref'), key=('family',), record_refs=('sheet_ref',))


class LiteraturePartnerRepository(SheetCustody):
    experiment_types = EXPERIMENT_TYPES
    provider = PROVIDER
    components = COMPONENTS
    record_version = 'literature_partner_record_v1'
    operations = OPERATIONS
    cells_table = CELLS
    current_table = CURRENT
    binding_fields = tuple(BINDINGS)

    def __init__(self, store):
        self.store = store

    def _read_sheet(self, sheet_ref):
        """Read an A107 partner sheet from its original selected operation."""
        source = self.store.get(sheet_ref)
        if source['record_type'] != 'source' or source['provider'] != self.provider or source['origin'] != 'tool' or (source['request_ref'] is None):
            raise ContractError('literature_partner_sheet_required')
        request = json.loads(self.store.get_artifact(source['request_ref']))
        payload = json.loads(self.store.get_artifact(source['artifact_ref']))
        if payload.get('version') != self.record_version or source.get('version') != self.record_version or source.get('parent_source_refs') != payload.get('input_source_refs', [payload['input_source_ref']]) or (request.get('arguments', {}).get('source_ref') != payload['input_source_ref']):
            raise ContractError('literature_partner_sheet_source_mismatch')
        return payload

    def _authorize_assessment(self, scope, page_source_ref, value):
        """The old ``authorize_assessment``: an explicitly held, sourced assay identity; never inferred. A subject,
        partner or condition literal is not experiment identity."""
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
        role = literal_reference_role(record)
        if role in {'subject', 'partner'}:
            raise ContractError('literature_partner_experiment_identity_is_subject_or_partner_literal')
        if role is not None and role != 'experiment':
            raise ContractError('literature_partner_experiment_identity_is_condition_literal')

    def cells_schema(self):
        return partner_cells_schema()

    def _provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('literature_source_outside_scope')
        source = self.store.get(reference)
        if source['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return source

    def _source(self, scope, page_source_ref, reference):
        """A direct input: a source this Episode holds, in scope, derived from the assigned page's source when the
        Episode reads below a page."""
        if not self.store.holds(reference):
            raise ContractError('literature_source_not_received')
        source = self._provenance(scope, reference)
        if page_source_ref is not None:
            pending, seen = ([reference], set())
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

    def _parents(self, scope, direct):
        parents, seen = (list(direct), set(direct))
        cursor = 0
        while cursor < len(parents):
            source = self._provenance(scope, parents[cursor])
            cursor += 1
            for reference in source.get('parent_source_refs', ()):
                self._provenance(scope, reference)
                if reference not in seen:
                    seen.add(reference)
                    parents.append(reference)
        return parents

    populate = _populate_partner_sheet

    def _assessment_sources(self, assessment):
        if assessment is None:
            return []
        return [self.store.get(assessment['experiment_ref'])['source_ref'], *([assessment['revises_sheet_ref']] if assessment['revises_sheet_ref'] is not None else [])]

    def current_sheet_refs(self):
        """The current sheets of this Episode: the latest sheet of each revision family, less every sheet an
        assessment revision superseded. Earlier versions are retained, not current."""
        heads = {row['family']: row['sheet_ref'] for row in self.store.table(CURRENT).select()}
        superseded = {row['assessment']['revises_sheet_ref'] for row in self.store.table(assessments.ASSESSMENTS).select()}
        return [ref for ref in heads.values() if ref not in superseded]

    def current_assessments(self):
        return assessments.current_assessments(self)

    def assessment_history(self, sheet_ref):
        return assessments.assessment_history(self, sheet_ref)

    def read(self, sheet_ref):
        """Validate saved authority and copy cells, without source-byte reads."""
        saved = self._read_sheet(sheet_ref)
        try:
            self._validate_saved(sheet_ref, saved)
        except ContractError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError('literature_partner_sheet_source_mismatch') from error
        return saved
    _validate_saved = _science_validate_saved
    _validate_native_saved = _science_validate_native_saved
    _validate_scientific_saved = _science_validate_scientific_saved

    def project_cells(self, sheet_refs, *, components=None):
        components = self.components if components is None else components
        if not isinstance(components, (list, tuple)) or any((not isinstance(name, str) or name not in self.components for name in components)) or len(set(components)) != len(components):
            raise ContractError('literature_partner_component_selection_invalid')
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            saved = self.read(reference)
            for name in components:
                bindings = deepcopy(saved['experimental_bindings'])
                if 'native_operand_bindings' in saved:
                    bindings.update(saved['native_operand_bindings']['component_bindings'][name])
                rows.append({'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'], 'data_source_ref': saved['data_source_ref'], **bindings, 'component': name, **deepcopy(saved['sheet']['cells'][name]), 'formula_code': FORMULA_CODES[name], **_metadata(saved['extraction'], saved['factor_bindings'])})
        validate_schema(rows, partner_cells_schema())
        return rows

    def validate_returned_values(self, cells):
        validate_schema(cells, partner_cells_schema())


def populate_partner_sheet(store, scope, page_source_ref, arguments, operation_key):
    """The ``literature.partner.populate`` and ``literature.partner.source.populate`` operations (old ``execute`` and
    ``_materialize_text_arguments``): fill each selected text witness's quotation from the held source bytes, then
    populate and save the sheet."""
    repository = LiteraturePartnerRepository(store)

    def read_source(reference, representation):
        source = repository._source(scope, page_source_ref, reference)
        artifact = source['artifact_ref'] if representation == 'original' else source.get('text_ref')
        if artifact is None:
            raise ContractError('literature_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    materialized = materialize_text_witness_inputs(plain(arguments), read_source=read_source)
    return repository.populate(scope, page_source_ref, materialized, operation_key)


__all__ = ['LiteraturePartnerRepository', 'COMPONENTS', 'PROVIDER', 'BINDINGS', 'FORMULA_CODES', 'OPERATIONS', 'CELLS', 'CURRENT', 'partner_population_schema', 'partner_source_population_schema', 'partner_cells_schema', 'populate_partner_sheet']
