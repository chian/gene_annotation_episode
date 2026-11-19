"""Persist selected assay grading and deliver exact requested A105 components.

Only population reads scientific inputs and calculates. Reconstruction validates
committed identities and typed cells; it does not rerun a reader or grader.

The A104 copy of the A105 assay grader (the literature subtree of A104 grades each applicable experiment into an A105
assay-grading sheet), carried onto
the custody-scoped store (``store``: ``ctx.store`` of the grading tool unit, or ``records`` for reads). What was the
old Store's:

* a record an Episode may read was "received" (``context.received_record_refs``); it is now a record the Episode
  holds (``store.holds``), in the commission's scope, and a source read below an assigned page is derived from the
  page's source;
* the ``literature_assay_grading_operations`` ledger (re-entry on the same operation key, the sheet's owner) is
  deleted: the system journals each unit's attempt and the owner of a sheet is its ``produced`` receipt. The sheets
  one Episode saved are the work table ``SHEETS``;
* ``literature_assay_grading_received`` is deleted: that is custody;
* the saved cells are rows of ``CELLS``, read by the Episode that saved them;
* the revision family of ``literature_sheet_updates.py`` (the owner's ``literature_sheet_policy.family_use``: the
  experiment, the assertion, the assay type, the quantity kind and the identity of the measured effect) is the work
  table ``CURRENT``: the latest sheet of a family is its current sheet; earlier sheets are retained, not current.
"""
from copy import deepcopy
from hashlib import sha256
import json

from episode_runtime import TableDeclaration

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.evolutionary_history_evidence.literature_assay_grading import (
    COMPONENTS, CRITERIA_BY_TYPE, assay_grading_cell_schema, assay_grading_input_schema, assay_grading_sheet_schema,
    grade_assay)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.evolutionary_history_evidence.literature_sheet_policy import (
    GRADING_PROVIDER, family_use)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_assay_grading_inputs import (
    assay_grading_population_schema as grading_population_schema, read_assay_grading_inputs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.evolutionary_history_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_OPERATION_DESCRIPTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_sheet_updates import (
    _measurement_keys, _replace_refs)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    canonical, identity, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.communication import plain

PROVIDER = GRADING_PROVIDER
VERSION = 'literature_assay_grading_record_v2'
NAMESPACE = 'literature_assay_grading_cells'
REQUESTED = 'requested_assay_grading_components'
SCOPE = 'assay_type_experimental_evidence'
OPERATION_DESCRIPTION = ASSAY_GRADING_OPERATION_DESCRIPTION
SAVED_KEYS = {'version', 'selection', 'extraction', 'sheet', 'direct_record_refs', 'input_source_refs',
              'record_bindings', 'artifact_bindings', 'input_component_rows'}

SHEETS = TableDeclaration(name='a104_literature_assay_grading_sheets', columns=('sheet_ref', 'family'), key=('sheet_ref',),
                          record_refs=('sheet_ref',))
CELLS = TableDeclaration(name='a104_literature_assay_grading_cells', columns=('sheet_ref', 'component', 'cell'),
                         key=('sheet_ref', 'component'), record_refs=('sheet_ref',))
CURRENT = TableDeclaration(name='a104_literature_assay_grading_current', columns=('family', 'sheet_ref'), key=('family',),
                           record_refs=('sheet_ref',))


def assay_grading_cells_schema():
    cell_schema = assay_grading_cell_schema()
    fields = deepcopy(cell_schema['properties'])
    sheet = assay_grading_sheet_schema()['properties']
    fields.update({'sheet_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}, 'evidence_source_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}, **{name: deepcopy(sheet[name]) for name in ('evaluation_scope', 'assay_type', 'assertion_ref', 'quantity_kind', 'interpretations', 'prediction_model', 'annotation_credit')}})
    fields['experiment_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'reference'}
    fields['assertion_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis'}
    fields['source_refs']['items'] = {'type': 'string', 'format': 'reference'}
    for criterion in fields['interpretations']['properties'].values():
        criterion['properties']['support_refs']['items'] = {'type': 'string', 'format': 'reference'}
    fields['prediction_model']['anyOf'][0]['properties']['support_refs']['items'] = {'type': 'string', 'format': 'reference'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields, required=[*cell_schema['required'], 'sheet_ref', 'evidence_source_ref', 'evaluation_scope', 'assay_type', 'assertion_ref', 'quantity_kind', 'interpretations', 'prediction_model', 'annotation_credit'])}


def _rows(saved, sheet_ref, components):
    sheet = saved['sheet']
    shared = {name: deepcopy(sheet[name]) for name in ('evaluation_scope', 'assay_type', 'assertion_ref', 'quantity_kind', 'annotation_credit')}
    if 'experiment_ref' in saved['selection']:
        shared['experiment_ref'] = saved['selection']['experiment_ref']
    by_component = {'measured_effect': (), 'effect_variance': ('variance_correspondence',), 'effect_precision': ('variance_correspondence',), 'recovery_deviation': ('calibration_applicability',), 'attributed_fraction': ('measurement_identity', 'attribution_supported'), 'condition_response': ('measurement_identity', 'condition_scope'), 'source_log_evidence_ratio': CRITERIA_BY_TYPE[sheet['assay_type']]}
    predictive = tuple((name for name in CRITERIA_BY_TYPE[sheet['assay_type']] if name not in ('variance_correspondence', 'sampling_basis')))
    rows = []
    for component in components:
        selected = by_component.get(component, predictive)
        rows.append({'sheet_ref': sheet_ref, 'evidence_source_ref': saved['selection']['source_ref'], **deepcopy(sheet['cells'][component]), **deepcopy(shared), 'interpretations': {name: deepcopy(sheet['interpretations'][name]) for name in selected if name in sheet['interpretations']}, 'prediction_model': deepcopy(sheet['prediction_model']) if component == 'source_log_evidence_ratio' else None})
    return rows


def family(arguments, saved):
    """The revision family of a grading sheet: the owner's ``family_use`` of the grading provider (experiment,
    assertion, assay type, quantity kind and the physical identity of the measured effect)."""
    return identity('literature_scientific_sheet_use', {
        'provider': PROVIDER, 'use': family_use(PROVIDER, arguments, saved, {}, _measurement_keys, _replace_refs)})


class LiteratureAssayGradingRepository:
    """Saved A105 assay grading sheets over the custody-scoped store (``store``) of the running unit.

    ``read_cells(namespace, sheet_ref, components)`` reads the cells of a reader sheet the grader takes a
    ``received_component`` from; without it such a route is refused (``assay_grading_reader_namespace_unbound``)."""
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION
    population_schema = staticmethod(grading_population_schema)

    def __init__(self, store, read_cells=None):
        self.store = store
        self._read_cells = read_cells

    def _provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('literature_source_outside_scope')
        source = self.store.get(reference)
        if source['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return source

    def source(self, scope, page_source_ref, reference):
        """A direct input source: held by this Episode, in scope and, below an assigned page, derived from the
        page's source (``page_source_ref`` ``None``: no assigned page)."""
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
                row = self._provenance(scope, current)
                if current == page_source_ref:
                    break
                pending.extend(row.get('parent_source_refs', ()))
            else:
                raise ContractError('literature_reading_outside_assigned_source')
        return source

    def _record(self, scope, reference):
        if not self.store.holds(reference):
            raise ContractError('assay_grading_record_not_received')
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('assay_grading_record_outside_scope')
        return self.store.get(reference)

    def populate(self, scope, page_source_ref, arguments, operation_key, requested=()):
        """Read the selected operands, grade the experiment and save the sheet, its cells and its revision family in
        one transaction."""
        args = plain(arguments)
        if 'experiment_ref' not in args:
            raise ContractError('assay_grading_experiment_reference_required')
        validate_schema(args, self.population_schema())
        requested = list(requested)
        if len(set(requested)) != len(requested) or any((name not in self.components for name in requested)):
            raise ContractError('assay_grading_component_selection_invalid')
        record_bindings, direct, artifact_bindings, input_component_rows = ({}, [], {}, [])

        def retain(record, *, possessed=False):
            reference = record['id']
            record_bindings[reference] = identity('assay_grading_input_record', record)
            if possessed and reference not in direct:
                direct.append(reference)
            return record

        def read_record(reference):
            return retain(self._record(scope, reference), possessed=True)

        def read_source(reference, representation):
            source = retain(self.source(scope, page_source_ref, reference), possessed=True)
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            raw = self.store.get_artifact(artifact)
            if artifact != 'artifact_' + sha256(raw).hexdigest():
                raise ContractError('assay_grading_input_artifact_hash_mismatch')
            artifact_bindings[reference, representation] = artifact
            return {'artifact_ref': artifact, 'content': raw}

        def read_cells(namespace, sheet_ref, components):
            retain(self.source(scope, page_source_ref, sheet_ref), possessed=True)
            if self._read_cells is None:
                raise ContractError('assay_grading_reader_namespace_unbound')
            rows = self._read_cells(namespace, sheet_ref, components)
            input_component_rows.append({'namespace': namespace, 'sheet_ref': sheet_ref, 'components': list(components), 'rows': deepcopy(rows)})
            return rows

        def read_database_request(reference):
            source = retain(self.source(scope, page_source_ref, reference), possessed=True)
            request_ref = source.get('request_ref')
            if request_ref is None:
                raise ContractError('database_measurement_request_unavailable')
            receipt = self._artifact_json(request_ref)
            artifact_bindings[reference, 'request'] = request_ref
            return receipt
        retain(self.source(scope, page_source_ref, args['source_ref']), possessed=True)
        extraction = read_assay_grading_inputs(args, read_source=read_source, read_cells=read_cells, read_record=read_record, read_database_request=read_database_request)
        validate_schema(extraction, assay_grading_input_schema())
        sheet = grade_assay(extraction)
        validate_schema(sheet, assay_grading_sheet_schema())
        sources = [args['source_ref']]
        for quantity in extraction['quantities'].values():
            if quantity is not None:
                sources.extend(quantity['source_refs'])
        for reference in list(record_bindings):
            record = self.store.get(reference)
            if record['record_type'] == 'source':
                sources.append(reference)
            elif record.get('source_ref'):
                sources.append(record['source_ref'])
        sources = list(dict.fromkeys(sources))
        for reference in sources:
            source = retain(self._provenance(scope, reference))
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        payload = {'version': self.record_version, 'selection': args, 'extraction': extraction, 'sheet': sheet, 'direct_record_refs': direct, 'input_source_refs': sources, 'record_bindings': record_bindings, 'input_component_rows': input_component_rows, 'artifact_bindings': [{'source_ref': ref, 'representation': rep, 'artifact_ref': artifact} for (ref, rep), artifact in artifact_bindings.items()]}
        request = {'operation_key': operation_key, 'arguments': args, 'scope': plain(scope), 'requested_components': requested}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(canonical(request), 'application/json')
            record = {'provider': self.provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref, 'version': self.record_version, 'retrieved_at': None, 'parent_source_refs': sources}
            sheet_ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.holds(sheet_ref)
            self.store.put('source', record, origin='tool', scope=plain(scope))
            sheet_family = family(args, payload)
            self.store.table(SHEETS).put({'sheet_ref': sheet_ref, 'family': sheet_family})
            self.store.table(CURRENT).put({'family': sheet_family, 'sheet_ref': sheet_ref})
            for row in _rows(payload, sheet_ref, self.components):
                self.store.table(CELLS).put({'sheet_ref': sheet_ref, 'component': row['component'], 'cell': row})
            rows = _rows(payload, sheet_ref, requested)
            validate_schema(rows, assay_grading_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'key': operation_key}), 'record_refs': [sheet_ref], 'changed_record_refs': [] if exists else [sheet_ref], 'result': {'sheet_ref': sheet_ref, 'cells': rows}, 'feedback': None}
        return outcome

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != 'artifact_' + sha256(raw).hexdigest():
            raise ContractError('assay_grading_saved_hash_mismatch')
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError('assay_grading_saved_json_required') from error
        if not isinstance(value, dict):
            raise ContractError('assay_grading_saved_object_required')
        return value

    def read(self, sheet_ref):
        """The saved grading record of a held sheet, checked against the request it was saved for and recomputed
        from nothing (the sheet's schema and its cells' projection)."""
        source = self.store.get(sheet_ref)
        if source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != self.provider or source.get('version') != self.record_version:
            raise ContractError('assay_grading_sheet_required')
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != sheet_ref:
            raise ContractError('assay_grading_saved_identity_mismatch')
        request = self._artifact_json(source['request_ref'])
        saved = self._artifact_json(source['artifact_ref'])
        if set(request) != {'operation_key', 'arguments', 'scope', 'requested_components'} or set(saved) != SAVED_KEYS or saved['version'] != source['version'] or saved['selection'] != request['arguments'] or saved['input_source_refs'] != source['parent_source_refs']:
            raise ContractError('assay_grading_saved_selection_mismatch')
        validate_schema(saved['selection'], self.population_schema())
        validate_schema(saved['extraction'], assay_grading_input_schema())
        validate_schema(saved['sheet'], assay_grading_sheet_schema())
        if not set(saved['direct_record_refs']) <= set(saved['record_bindings']):
            raise ContractError('assay_grading_saved_input_mismatch')
        validate_schema(_rows(saved, sheet_ref, self.components), assay_grading_cells_schema())
        return saved

    def sheet_refs(self):
        """The grading sheets this Episode saved, in the order first saved."""
        return [row['sheet_ref'] for row in self.store.table(SHEETS).select()]

    def current_sheet_refs(self):
        """The current sheet of each revision family this Episode saved, in the order the families began."""
        return [row['sheet_ref'] for row in self.store.table(CURRENT).select()]

    def held_sheet_refs(self):
        """The saved grading sheets the Episode holds (its own and the ones passed or returned to it), in reference
        order."""
        return [row['id'] for row in self.store.list('source') if row.get('provider') == self.provider
                and row.get('origin') == 'tool' and row.get('request_ref') is not None]

    def selected_sheet_refs(self, context):
        """Every held sheet, each read and authenticated."""
        refs = self.held_sheet_refs()
        for reference in refs:
            self.read(reference)
        return refs

    available_sheet_refs = selected_sheet_refs

    def cells(self, sheet_ref, components=None):
        """The saved cell rows of a sheet this Episode saved, in component order."""
        selected = self.components if components is None else components
        if not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected) or any((component not in self.components for component in selected)):
            raise ContractError('assay_grading_component_selection_invalid')
        rows = {row['component']: row['cell'] for row in self.store.table(CELLS).select({'sheet_ref': sheet_ref})}
        return [rows[name] for name in selected]

    def project_cells(self, sheet_ref, components=None):
        """The cell rows of any held sheet, projected from its saved record."""
        selected = self.components if components is None else components
        return _rows(self.read(sheet_ref), sheet_ref, list(selected))

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        for row in cells:
            refs.extend((row['sheet_ref'], row['evidence_source_ref'], row['assertion_ref']))
            if row.get('experiment_ref') is not None:
                refs.append(row['experiment_ref'])
            refs.extend(row.get('source_refs', ()))
            for interpretation in row['interpretations'].values():
                refs.extend(interpretation['support_refs'])
            if row['prediction_model']:
                refs.extend(row['prediction_model']['support_refs'])
        return list(dict.fromkeys((ref for ref in refs if ref is not None)))


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'SCOPE', 'COMPONENTS', 'OPERATION_DESCRIPTION', 'SHEETS',
           'CELLS', 'CURRENT', 'LiteratureAssayGradingRepository', 'assay_grading_cells_schema', 'family']
