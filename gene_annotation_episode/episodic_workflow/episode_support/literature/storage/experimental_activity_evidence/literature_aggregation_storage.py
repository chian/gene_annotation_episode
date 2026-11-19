"""Persist selected A105 aggregation over the parent's possessed grade rows.

Carried from ``scoring/literature_a105_aggregation_storage.py`` of ``source_evidence_examination`` at ``97308b94c``
onto the custody-scoped store (``store``: ``ctx.store`` of the aggregating tool unit, or ``records`` for reads):
the ``literature_a105_aggregation_operations`` and ``_received`` ledgers are deleted (the system journals each unit's
attempt; what an Episode received is custody); a grading sheet the aggregation reads must be held, and its cells are
projected from the held sheet's saved record; the aggregation sheets one Episode saved are the work table
``SHEETS``, and the current sheet of each question (the owner's ``family_use``: assertion and comparison) is
``CURRENT``. The owner's reducers are ``literature_aggregation.REDUCERS``: reliability SUM, validity SUM, relevance
MAXIMUM, attribution MAXIMUM, overall SUM."""
from copy import deepcopy
from hashlib import sha256
import json

from episode_runtime import TableDeclaration

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sheet_policy import (
    SCORING_PROVIDER, family_use)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_aggregation import (
    COMPONENTS, SCOPE, aggregate_a105, aggregation_cell_schema, aggregation_population_schema, aggregation_sheet_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository, assay_grading_cells_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_sheet_updates import (
    _measurement_keys, _replace_refs)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical, identity, obj, plain, validate_schema)

PROVIDER = SCORING_PROVIDER
VERSION = 'literature_a105_aggregation_record_v1'
NAMESPACE = 'literature_a105_aggregation_cells'
REQUESTED = 'requested_a105_aggregation_components'
OPERATION_DESCRIPTION = 'Combine the retained experimental A105 components selected by the parent. Use one actual possessed numerical component per experiment and metric: reliability SUM, validity SUM, relevance MAX, attribution MAX, overall SUM. Preserve the selected native values, units and meanings, with no weighting, rescaling or orthogonality correction. Select one assessment of each experiment so duplicate reports or revisions do not become additional experiments. Keep missing values explicit and report available partial totals separately. The comparison reference is a parent declaration; no alternative hypothesis identity is inferred from the native prediction numbers. Return exactly the requested saved metrics. This is A105 evidence aggregation, not W05 annotation credit.'
SAVED_KEYS = {'version', 'selection', 'source_cells', 'sheet', 'direct_record_refs', 'input_source_refs',
              'record_bindings'}

SHEETS = TableDeclaration(name='a105_aggregation_sheets', columns=('sheet_ref', 'family'), key=('sheet_ref',),
                          record_refs=('sheet_ref',))
CURRENT = TableDeclaration(name='a105_aggregation_current', columns=('family', 'sheet_ref'), key=('family',),
                           record_refs=('sheet_ref',))


def aggregation_cells_schema():
    fields = deepcopy(aggregation_cell_schema()['properties'])
    fields['sheet_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}


def _rows(saved, sheet_ref, components):
    return [dict(sheet_ref=sheet_ref, **deepcopy(saved['sheet']['cells'][name])) for name in components]


def family(arguments):
    """The question an aggregation sheet answers (the owner's ``family_use`` of the scoring provider)."""
    return identity('literature_scientific_sheet_use', {
        'provider': PROVIDER, 'use': family_use(PROVIDER, arguments, None, {}, _measurement_keys, _replace_refs)})


class LiteratureA105AggregationRepository:
    """Saved A105 across-experiment aggregation sheets over the custody-scoped store (``store``)."""
    provider = PROVIDER
    components = COMPONENTS
    record_version = VERSION

    def __init__(self, store):
        self.store = store

    def _record(self, scope, reference, kind=None):
        if not self.store.holds(reference):
            raise ContractError('a105_aggregation_record_not_received')
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('a105_aggregation_record_outside_scope')
        record = self.store.get(reference)
        if kind is not None and record['record_type'] != kind:
            raise ContractError('a105_aggregation_record_type_mismatch')
        return record

    def _provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError('literature_source_outside_scope')
        source = self.store.get(reference)
        if source['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return source

    def populate(self, scope, arguments, operation_key, requested=()):
        """Aggregate the selected grading-sheet components of held sheets and save the sheet in one transaction."""
        args = plain(arguments)
        validate_schema(args, aggregation_population_schema())
        requested = list(requested)
        if len(set(requested)) != len(requested) or any((name not in COMPONENTS for name in requested)):
            raise ContractError('a105_aggregation_component_selection_invalid')
        direct, bindings = ([], {})

        def retain(reference, kind=None, possessed=True):
            record = self._record(scope, reference, kind) if possessed else self._provenance(scope, reference)
            bindings[reference] = identity('a105_aggregation_input_record', record)
            if possessed and reference not in direct:
                direct.append(reference)
            return record
        retain(args['assertion_ref'], 'hypothesis')
        if args['comparison_ref'] is not None:
            retain(args['comparison_ref'], 'hypothesis')
        grouped = {}
        for experiment in args['experiments']:
            retain(experiment['experiment_ref'], 'reference')
            for selected in experiment['metrics'].values():
                if selected is not None and selected['component'] not in grouped.setdefault(selected['sheet_ref'], []):
                    grouped[selected['sheet_ref']].append(selected['component'])
        grades = LiteratureAssayGradingRepository(self.store)
        input_rows, sources = ([], [])
        for sheet_ref, components in grouped.items():
            retain(sheet_ref, 'source')
            rows = grades.project_cells(sheet_ref, components)
            validate_schema(rows, assay_grading_cells_schema())
            input_rows.extend(rows)
            sources.append(sheet_ref)
        sheet = aggregate_a105(args, input_rows)
        for reference in list(sources):
            source = retain(reference, possessed=False)
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        payload = {'version': VERSION, 'selection': args, 'source_cells': input_rows, 'sheet': sheet, 'direct_record_refs': direct, 'input_source_refs': sources, 'record_bindings': bindings}
        request = {'operation_key': operation_key, 'arguments': args, 'scope': plain(scope), 'requested_components': requested}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(canonical(request), 'application/json')
            record = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref, 'version': VERSION, 'retrieved_at': None, 'parent_source_refs': sources}
            sheet_ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.holds(sheet_ref)
            self.store.put('source', record, origin='tool', scope=plain(scope))
            question = family(args)
            self.store.table(SHEETS).put({'sheet_ref': sheet_ref, 'family': question})
            self.store.table(CURRENT).put({'family': question, 'sheet_ref': sheet_ref})
            rows = _rows(payload, sheet_ref, requested)
            validate_schema(rows, aggregation_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'key': operation_key}), 'record_refs': [sheet_ref], 'changed_record_refs': [] if exists else [sheet_ref], 'result': {'sheet_ref': sheet_ref, 'cells': rows}, 'feedback': None}
        return outcome

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != 'artifact_' + sha256(raw).hexdigest():
            raise ContractError('a105_aggregation_saved_hash_mismatch')
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as cause:
            raise ContractError('a105_aggregation_saved_json_required') from cause
        if not isinstance(result, dict):
            raise ContractError('a105_aggregation_saved_object_required')
        return result

    def read(self, sheet_ref):
        """The saved aggregation record of a held sheet, checked against its request and its schemas."""
        source = self.store.get(sheet_ref)
        if source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER or (source.get('version') != VERSION):
            raise ContractError('a105_aggregation_sheet_required')
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != sheet_ref:
            raise ContractError('a105_aggregation_saved_identity_mismatch')
        request = self._artifact_json(source['request_ref'])
        saved = self._artifact_json(source['artifact_ref'])
        if set(request) != {'operation_key', 'arguments', 'scope', 'requested_components'} or set(saved) != SAVED_KEYS or saved['version'] != VERSION or saved['selection'] != request['arguments'] or saved['input_source_refs'] != source['parent_source_refs']:
            raise ContractError('a105_aggregation_saved_selection_mismatch')
        validate_schema(saved['selection'], aggregation_population_schema())
        validate_schema(saved['source_cells'], assay_grading_cells_schema())
        validate_schema(saved['sheet'], aggregation_sheet_schema())
        if not set(saved['direct_record_refs']) <= set(saved['record_bindings']):
            raise ContractError('a105_aggregation_saved_input_mismatch')
        return saved

    def sheet_refs(self):
        return [row['sheet_ref'] for row in self.store.table(SHEETS).select()]

    def current_sheet_refs(self):
        return [row['sheet_ref'] for row in self.store.table(CURRENT).select()]

    def project_cells(self, sheet_ref, components=None):
        selected = COMPONENTS if components is None else components
        if not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected) or any((component not in COMPONENTS for component in selected)):
            raise ContractError('a105_aggregation_component_selection_invalid')
        return _rows(self.read(sheet_ref), sheet_ref, list(selected))


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'SCOPE', 'COMPONENTS', 'OPERATION_DESCRIPTION', 'SHEETS',
           'CURRENT', 'aggregation_cells_schema', 'LiteratureA105AggregationRepository', 'direct_target_application']


def direct_target_application(store, context, cell, target, scope=None):
    """A105's current direct experiment-to-target links; no invented transfer kernel."""
    from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_and_context_sources.experimental_activity_evidence.component_assessment_dependencies import assessment_dependencies
    scope = plain(scope) if scope is not None else None
    experiments, linked, links, needed, states = (set(cell['selected_experiment_refs']), set(), set(), set(), set())
    known = set(context.received_record_refs)
    for reference in known:
        row = store.get(reference)
        if row['record_type'] != 'assessment' or row['hypothesis_ref'] != cell['assertion_ref']:
            continue
        finding = row.get('investigation_finding')
        if finding is None or target not in finding['source_claim']['subject_refs'] or row['observation_ref'] not in known:
            continue
        observation = store.get(row['observation_ref'])
        references = {*observation.get('subject_refs', ()), *observation.get('source_subject_refs', ()), *observation.get('dependencies', ())}
        matching = experiments.intersection(references)
        if not matching:
            continue
        links.add(reference)
        dependency = assessment_dependencies(store, reference, known)
        if finding['status'] == 'withdrawn':
            states.add('withdrawn')
            continue
        if row['applicability'] == 'incomparable':
            states.add('invalid')
            continue
        if dependency is not None and dependency['retired']:
            continue
        if dependency is None or row['extent_basis'] == 'context_allocation':
            states.add('unresolved')
            continue
        required = {observation['source_ref'], *observation.get('dependencies', ()), *row['condition_refs'], *row['assumption_refs'], *finding['qualification']['context_refs'], *finding['qualification']['assumption_refs']}
        missing = required - (known | set(store.problem()['subject_refs']))
        needed.update(missing)
        extent = store.assessment_write_extent(row['id'])
        if missing or (scope is not None and (not extent or not store.scope_contains({'subject_refs': sorted({span['target_ref'] for span in extent}), 'segments': extent}, scope))):
            states.add('unresolved')
            continue
        states.add('established')
        linked.update(matching)
    established = bool(experiments) and linked == experiments
    return {'status': 'established' if established else 'withdrawn' if states == {'withdrawn'} else 'invalid' if states == {'invalid'} else 'unresolved', 'missing_inputs': [] if established else ['a105_direct_target_experiment_application_unresolved'], 'needed_refs': sorted(needed), 'link_refs': sorted(links), 'owner_states': sorted(states)}
