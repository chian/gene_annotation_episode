"""Immutable A106 final results on the existing numerical-cell custody path."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json

from .communication import plain
from .domain import ContractError, canonical, identity, validate_schema
from .literature_assay_grading_storage import LiteratureAssayGradingRepository
from .literature_assay_inputs import _Sources
from .literature_intervention_storage import LiteratureInterventionRepository, intervention_cells_schema
from .literature_a106_subscore import (
    COMPONENTS, REQUESTED, NAMESPACE, SCORE_COMPONENT, population_schema,
    cell_schema, cells_schema, finalize_a106, TASK,
)

PROVIDER = "literature.a106.subscore"
VERSION = "literature_a106_subscore_record_v1"
OPERATION_DESCRIPTION = TASK
QUESTION_FIELDS = ("subject_ref", "assertion_ref", "comparison_ref", "scope_statement")


def _rows(saved, sheet_ref, components):
    return [{"sheet_ref": sheet_ref, **deepcopy(saved["sheet"]["cells"][name])} for name in components]


class LiteratureA106SubscoreRepository(LiteratureAssayGradingRepository):
    judgment_table = 'literature_a106_score_judgments'

    def _install_judgments(self):
        self.store.db.execute(f'''CREATE TABLE IF NOT EXISTS {self.judgment_table}(
            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, judgment_ref TEXT NOT NULL,
            request TEXT NOT NULL, possessed TEXT NOT NULL, state TEXT NOT NULL,
            response TEXT, provenance TEXT, outcome TEXT,
            PRIMARY KEY(run_id,episode_id,judgment_ref))''')

    def prepare_judgments(self, context):
        """Save one compact judgment request for this original A106 commission.

        The caller invokes the model after this method returns and outside any
        transaction. A judgment is an ordinary calculation, not an episode.
        """
        if self.store.db.in_transaction:
            raise ContractError('a106_judgment_requires_committed_inputs')
        assignment = plain(context.assignment)
        commission = assignment if context.role == 'scientific_process' else None
        if commission is None:
            from method_loop.identities import EpisodeRef
            for length in range(len(context.path) - 1, 0, -1):
                path = context.path[:length]
                if path[-1][0] != 'scientific_process':
                    continue
                owner = EpisodeRef(context.run_id, path).episode_id
                saved = self.store.db.execute('SELECT request FROM runtime_episodes '
                    'WHERE run_id=? AND episode_id=?', (context.run_id, owner)).fetchone()
                if saved is not None:
                    original = json.loads(saved['request'])['message']
                    if not self.store.scope_contains(original['scope'], plain(context.scope)):
                        raise ContractError('a106_judgment_scope_outside_original_commission')
                    commission = original.get('episode_assignment', {})
                break
        axis = (commission or {}).get('selection', {}).get('evidence_axis', {}).get('option_id')
        proposal = (commission or {}).get('proposed_annotation_ref')
        known = set(context.received_record_refs)
        if axis != 'A106' or proposal not in known:
            return []
        if assignment.get('proposed_annotation_ref') != proposal:
            raise ContractError('a106_judgment_original_annotation_required')
        annotation = self.store.get(proposal)
        if annotation['record_type'] != 'hypothesis':
            raise ContractError('a106_judgment_proposed_annotation_required')
        from .literature_sheet_updates import _rows, _heads
        heads = list(_heads(_rows(self.store, context)).values())
        native = LiteratureInterventionRepository(self.store, self.run_id)
        refs = {row['sheet_ref'] for row in heads}
        view = replace(context, received_record_refs=tuple(sorted(known | refs)))
        grouped = {}
        for row in heads:
            if row['provider'] != native.provider or row['current_status'] != 'current':
                continue
            for cell in native.fact_cells(view, [row['sheet_ref']], components=[SCORE_COMPONENT]):
                if cell['assertion_ref'] == proposal:
                    grouped.setdefault(cell['comparison_ref'], []).append(cell)
        requests = []
        for comparison, cells in sorted(grouped.items()):
            cells = sorted(cells, key=lambda cell: (cell['experiment_ref'], cell['sheet_ref']))
            finals = [row for row in heads if row['provider'] == self.provider
                and json.loads(row['arguments'])['assertion_ref'] == proposal
                and json.loads(row['arguments'])['comparison_ref'] == comparison]
            # An admitted final belongs to its original producer. Its reader
            # waits for authentic replacement delivery, not private inputs.
            if any(json.loads(row['receipt'])['custody'] != 'owned' for row in finals):
                continue
            available = known | set(native.cell_record_refs(cells)) | refs
            if comparison not in available:
                continue
            previous = [dict(sheet_ref=row['sheet_ref'], selection=json.loads(row['arguments'])) for row in finals]
            key = identity('a106_score_judgment', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'scope': plain(context.scope),
                'proposed_annotation_ref': proposal, 'comparison_ref': comparison,
                'assessment_versions': [cell['sheet_ref'] for cell in cells]})
            witnesses = {}
            def collect(value):
                if isinstance(value, dict):
                    if {'source_ref', 'representation', 'start', 'end', 'quote'} <= set(value):
                        witnesses[canonical(value)] = deepcopy(value)
                    else:
                        for child in value.values():
                            collect(child)
                elif isinstance(value, list):
                    for child in value:
                        collect(child)
            for cell in cells:
                collect(cell['experimental_design'])
                collect(cell['sample_bindings'])
            for old in previous:
                collect(old['selection']['dependence']['witnesses'])
            packet = {'proposed_annotation': annotation, 'comparison': self.store.get(comparison),
                'assigned_scope': plain(context.scope), 'current_assessments': cells,
                'experiments': [self.store.get(ref) for ref in sorted({cell['experiment_ref'] for cell in cells})],
                'declared_contexts': [self.store.get(ref) for ref in annotation['context_refs'] if ref in available],
                'available_witnesses': list(witnesses.values()), 'previous_final_bindings': previous}
            from .domain import obj
            schema = obj({'selection': {'anyOf': [population_schema(), {'type': 'null'}]},
                'unresolved_reasons': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}})
            instructions = (
                'Make one source-bound A106 evidence judgment from the supplied current assessments. '
                'Return the existing final selection or null with unresolved_reasons. This is a calculation, '
                'not a decision about next actions. Preserve the proposed annotation, explicit comparison, '
                'actual subject and original assigned region. Supply a biological scope_statement only '
                'when these inputs establish it. Keep every relevant original experiment, including '
                'opposition and unavailable scores; never choose by score magnitude. Do not infer '
                'independence from different papers or identifiers. Declare unknown/shared dependence '
                'when its original biological units, controls and sampling are unresolved. For independence '
                'use only exact supplied available_witnesses. An existing final binding keeps its '
                'subject_ref, assertion_ref, comparison_ref and scope_statement; revise its exact sheet. '
                'Multiple conflicting existing bindings or competing assessments require unresolved '
                'judgment. Do not invent source quotations, witnesses, experiments or biological facts.')
            request = {'judgment_ref': key, 'instructions': instructions,
                'context': packet, 'output_schema': schema}
            with self.store.transaction():
                self._install_judgments()
                self.store.db.execute(f'INSERT OR IGNORE INTO {self.judgment_table} '
                    '(run_id,episode_id,judgment_ref,request,possessed,state) VALUES(?,?,?,?,?,?)',
                    (self.run_id, context.episode_id, key, canonical(request), canonical(sorted(available)), 'pending'))
                saved = self.store.db.execute(f'SELECT request,state,outcome,provenance FROM {self.judgment_table} '
                    'WHERE run_id=? AND episode_id=? AND judgment_ref=?',
                    (self.run_id, context.episode_id, key)).fetchone()
                if saved['state'] == 'pending':
                    self.store.db.execute(f'UPDATE {self.judgment_table} SET state=? '
                        'WHERE run_id=? AND episode_id=? AND judgment_ref=?',
                        ('dispatched', self.run_id, context.episode_id, key))
            if saved['state'] == 'pending':
                requests.append(json.loads(saved['request']))
            elif saved['state'] == 'dispatched':
                outcome = self.complete_judgment(context, key, provenance={'recovery': 'interrupted_dispatch'},
                    failure={'code': 'a106_judgment_dispatch_interrupted',
                        'requirement': 'new_scientific_input_required_for_another_judgment'})
                requests.append({**json.loads(saved['request']), 'completed_outcome': outcome,
                    'completed_provenance': {'recovery': 'interrupted_dispatch'}})
            else:
                requests.append({**json.loads(saved['request']),
                    'completed_outcome': json.loads(saved['outcome']),
                    'completed_provenance': json.loads(saved['provenance'])})
        return requests

    def complete_judgment(self, context, judgment_ref, response=None, *, provenance, failure=None):
        """Validate and retain one response; failures stay unresolved without a retry loop."""
        if self.store.db.in_transaction:
            raise ContractError('a106_judgment_requires_committed_inputs')
        row = self.store.db.execute(f'SELECT * FROM {self.judgment_table} '
            'WHERE run_id=? AND episode_id=? AND judgment_ref=?',
            (self.run_id, context.episode_id, judgment_ref)).fetchone()
        if row is None:
            raise ContractError('a106_judgment_request_not_found')
        if row['state'] not in {'pending', 'dispatched'}:
            return json.loads(row['outcome'])
        request = json.loads(row['request'])
        packet = request['context']
        diagnostic = failure
        outcome = None
        try:
            if diagnostic is None:
                validate_schema(response, request['output_schema'])
                selection = response['selection']
                if selection is None:
                    diagnostic = {'code': 'a106_judgment_unresolved',
                        'reasons': response['unresolved_reasons'] or ['scientific_binding_unresolved']}
                else:
                    expected = {(cell['experiment_ref'], cell['sheet_ref']) for cell in packet['current_assessments']}
                    actual = {(item['experiment_ref'], item['sheet_ref']) for item in selection['experiments']}
                    if (selection['assertion_ref'] != packet['proposed_annotation']['id']
                            or selection['comparison_ref'] != packet['comparison']['id']
                            or selection['subject_ref'] not in packet['proposed_annotation']['subject_refs']
                            or actual != expected or len(actual) != len(selection['experiments'])):
                        raise ContractError('a106_judgment_scientific_binding_mismatch')
                    previous = packet['previous_final_bindings']
                    if len(previous) > 1:
                        raise ContractError('a106_judgment_existing_question_ambiguous')
                    if previous:
                        prior = previous[0]
                        if (selection['revises_subscore_ref'] != prior['sheet_ref']
                                or any(selection[name] != prior['selection'][name] for name in QUESTION_FIELDS)):
                            raise ContractError('a106_judgment_revision_question_mismatch')
                    elif selection['revises_subscore_ref'] is not None:
                        raise ContractError('a106_judgment_unreceived_predecessor')
                    permitted = {canonical(witness) for witness in packet['available_witnesses']}
                    if any(canonical(witness) not in permitted for witness in selection['dependence']['witnesses']):
                        raise ContractError('a106_judgment_witness_not_supplied')
                    possessed = json.loads(row['possessed'])
                    applying = replace(context, received_record_refs=tuple(possessed),
                        assignment={**plain(context.assignment), REQUESTED: list(COMPONENTS)})
                    with self.store.transaction():
                        outcome = self.populate(applying, selection, judgment_ref)
                        outcome = {**outcome, 'judgment_ref': judgment_ref}
                        self.store.db.execute(f'UPDATE {self.judgment_table} '
                            'SET state=?,response=?,provenance=?,outcome=? '
                            'WHERE run_id=? AND episode_id=? AND judgment_ref=?',
                            ('complete', canonical(response), canonical(provenance), canonical(outcome),
                             self.run_id, context.episode_id, judgment_ref))
                    return outcome
        except ContractError as error:
            diagnostic = {'code': str(error), 'detail': getattr(error, 'detail', None)}
        if outcome is None:
            outcome = {'status': 'unavailable', 'record_refs': [], 'changed_record_refs': [],
                'result': {'judgment_ref': judgment_ref, 'score': None}, 'feedback': diagnostic}
        outcome = {**outcome, 'judgment_ref': judgment_ref}
        with self.store.transaction():
            if diagnostic is not None:
                from .literature_sheet_updates import _rows, _heads, CURRENT
                for final in _heads(_rows(self.store, context)).values():
                    if final['provider'] != self.provider or json.loads(final['receipt'])['custody'] != 'owned':
                        continue
                    selected = json.loads(final['arguments'])
                    if (selected['assertion_ref'], selected['comparison_ref']) == (
                            packet['proposed_annotation']['id'], packet['comparison']['id']):
                        self.store.db.execute(f'UPDATE {CURRENT} SET status=?,detail=? '
                            'WHERE run_id=? AND episode_id=? AND family=?',
                            ('unavailable', canonical({'judgment_ref': judgment_ref, 'diagnostic': diagnostic}),
                             self.run_id, context.episode_id, final['family']))
            self.store.db.execute(f'UPDATE {self.judgment_table} SET state=?,response=?,provenance=?,outcome=? '
                'WHERE run_id=? AND episode_id=? AND judgment_ref=?',
                ('complete' if diagnostic is None else 'unresolved',
                 canonical(response) if response is not None else None, canonical(provenance), canonical(outcome),
                 self.run_id, context.episode_id, judgment_ref))
        return outcome

    def current_annotation_cells(self, context):
        """Resolve this owner's admitted current final cells without granting private inputs."""
        rows = ([row for row in self.received_cells(context) if row['component'] == 'experimental_subscore']
            if self._installed(self.received_table) else [])
        from .literature_sheet_updates import current_scoring_sheets
        current = [row for row in current_scoring_sheets(self.store, context) if row['axis'] == 'A106']
        if current:
            rows = [cell for row in current if row['status'] == 'current'
                for cell in row['cells'] if cell['component'] == 'experimental_subscore']
        superseded = {row['revises_subscore_ref'] for row in rows if row.get('revises_subscore_ref')}
        native = LiteratureInterventionRepository(self.store, context.run_id)
        revised = set()
        if native._installed(native.received_table):
            revised = {cell['experiment_assessment']['revises_sheet_ref'] for cell in native.received_cells(context)
                if (cell.get('experiment_assessment') or {}).get('revises_sheet_ref')}
        return [row for row in rows if row['sheet_ref'] not in superseded and not any(
            cell['sheet_ref'] in revised for cell in row['selected_components'])]

    def annotation_contribution(self, store, context, *, target, annotation, scope,
                                comparison_ref=None, selection=None, details_limit=0, details_offset=0):
        from .communication import plain
        from .root_axis_scalars import _result, require_attribution, bind_contribution
        from .literature_a106_subscore import annotation_scalar
        import json
        rows = [row for row in self.current_annotation_cells(context) if row['assertion_ref'] == annotation['id']
            and (comparison_ref is None or row.get('comparison_ref') == comparison_ref)
            and (selection is None or row['sheet_ref'] == selection)]
        refs, details = [], []
        if len(rows) != 1:
            reason = ('no_received_current_final_cell_for_this_question' if not rows else
                'multiple_current_axis_questions_require_explicit_sheet_selection')
            scalar = _result('A106', None, formula='received_current_axis_result_required',
                inputs={'sheet_refs': [row['sheet_ref'] for row in rows]}, reasons=[reason])
            transfer = {'status': 'unresolved', 'missing_inputs': [reason],
                'needed_refs': [], 'link_refs': [row['sheet_ref'] for row in rows]}
            if self._installed(self.judgment_table):
                judgments = self.store.db.execute(f'SELECT judgment_ref,state,outcome FROM {self.judgment_table} '
                    "WHERE run_id=? AND episode_id=? AND json_extract(request,'$.context.proposed_annotation.id')=? "
                    "AND (? IS NULL OR json_extract(request,'$.context.comparison.id')=?) ORDER BY rowid DESC LIMIT 1",
                    (self.run_id, context.episode_id, annotation['id'], comparison_ref, comparison_ref)).fetchall()
                if judgments:
                    judgment = judgments[0]
                    feedback = (json.loads(judgment['outcome']).get('feedback') if judgment['outcome'] else
                        {'code': 'a106_automatic_judgment_pending'})
                    if feedback is not None:
                        code = feedback.get('code', 'a106_judgment_failed') if isinstance(feedback, dict) else 'a106_judgment_failed'
                        scalar['missing_inputs'].append(code)
                        transfer['missing_inputs'].append(code)
                        if isinstance(feedback, dict):
                            reasons = [reason for reason in feedback.get('reasons', []) if isinstance(reason, str)]
                            scalar['missing_inputs'].extend(reasons)
                            transfer['missing_inputs'].extend(reasons)
                        transfer['link_refs'].append(judgment['judgment_ref'])
                        scalar['judgment_diagnostic'] = feedback
        else:
            cell = rows[0]
            refs = [cell['sheet_ref']]
            scalar = annotation_scalar(cell)
            missing = [] if cell['subject_ref'] == target else ['a106_source_subject_not_this_target']
            transfer = {'status': 'established' if not missing else 'invalid', 'missing_inputs': missing,
                'needed_refs': [], 'link_refs': [cell['sheet_ref']]}
            source = store.get(cell['sheet_ref'])
            request = json.loads(store.get_artifact(source['request_ref']))
            if not store.scope_contains(request['scope'], plain(scope)):
                transfer = {**transfer, 'status': 'unresolved',
                    'missing_inputs': [*transfer['missing_inputs'], 'received_axis_result_does_not_cover_requested_scope']}
            scalar = require_attribution(scalar, missing=transfer['missing_inputs'])
            details = [{'source_ref': cell['sheet_ref'], 'target_ref': target,
                'proposed_annotation_ref': annotation['id'], 'scope': plain(scope), 'transfer': transfer}]
        scalar.update(question={'assertion_ref': annotation['id'], 'comparison_ref': comparison_ref},
            source_contribution_count=len(refs))
        return bind_contribution(scalar, annotation=annotation, subject=target, scope=scope,
            transfer=transfer, source_refs=refs), details[details_offset:details_offset + details_limit]


    # Reuse only immutable persistence, projection and receipt helpers. Final
    # publication reads possessed assessment cells; it never reruns a grader.
    provider = PROVIDER
    record_version = legacy_version = VERSION
    requested = REQUESTED
    components = COMPONENTS
    operations_table = "literature_a106_subscore_operations"
    received_table = "literature_a106_subscore_received"
    rows = staticmethod(_rows)
    cells_schema = staticmethod(cells_schema)

    def _question_key(self, args):
        return identity("a106_question", {key: args[key] for key in QUESTION_FIELDS})

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, population_schema())
        requested = list(context.assignment.get(REQUESTED, ()))
        if len(requested) != len(set(requested)) or any(name not in COMPONENTS for name in requested):
            raise ContractError("a106_component_selection_invalid")
        request = dict(run_id=self.run_id, episode_id=context.episode_id, operation_key=operation_key,
            arguments=args, scope=plain(context.scope), requested_components=requested)
        signature = canonical(request)
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?", (self.run_id, context.episode_id, operation_key)
        ).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            for ref in self.read(outcome["result"]["sheet_ref"])["direct_record_refs"]:
                self._record(context, ref)
            return outcome
        direct, bindings = [], {}
        def retain(ref, kind=None, possessed=True):
            record = self._record(context, ref) if possessed else self._native_provenance(context.scope, ref)
            if kind is not None and record["record_type"] != kind:
                raise ContractError("a106_record_type_mismatch")
            bindings[ref] = identity("a106_subscore_input", record)
            if possessed and ref not in direct:
                direct.append(ref)
            return record
        retain(args["subject_ref"])
        for key in ("assertion_ref", "comparison_ref"):
            claim = retain(args[key], "hypothesis")
            if args["subject_ref"] not in claim["subject_refs"]:
                raise ContractError("a106_subject_assertion_mismatch")
        def read_source(ref, representation):
            source = retain(ref, "source")
            field = "artifact_ref" if representation == "original" else "text_ref"
            artifact = source.get(field)
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            raw = self.store.get_artifact(artifact)
            if artifact != "artifact_" + sha256(raw).hexdigest():
                raise ContractError("a106_subscore_input_hash_mismatch")
            return {"artifact_ref": artifact, "content": raw}
        sources = _Sources(read_source)
        for witness in args["dependence"]["witnesses"]:
            sources.witness(witness, "between_experiment_dependence")
        native = LiteratureInterventionRepository(self.store, self.run_id)
        source_rows = []
        for index, experiment in enumerate(args["experiments"]):
            record = retain(experiment["experiment_ref"], "reference")
            if record.get("reference_type") != "assay":
                raise ContractError("a106_experiment_reference_required")
            ref = experiment["sheet_ref"]
            if ref is not None:
                source = retain(ref, "source")
                try:
                    rows = native.fact_cells(context, [ref], components=[SCORE_COMPONENT])
                except ContractError as error:
                    if str(error) != "assay_grading_sheet_required":
                        raise
                    raise ContractError(str(error), detail={
                        "field": f"experiments.{index}.sheet_ref",
                        "sheet_ref": ref, "experiment_ref": experiment["experiment_ref"],
                        "expected_provider": native.provider,
                        "actual_provider": source.get("provider"),
                        "requirement": "Select the received A106 intervention-grading worksheet for this experiment, "
                            "created by literature.intervention_grading.populate. A publication, file listing, "
                            "raw measurement source or final subscore is not that assessment worksheet."}) from error
                if len(rows) != 1:
                    raise ContractError("a106_assessment_component_not_received")
                source_rows.extend(rows)
        prior = args["revises_subscore_ref"]
        question = self._question_key(args)
        if prior is not None:
            retain(prior, "source")
            predecessor = self.read(prior)
            if predecessor["question_key"] != question:
                previous = {key: predecessor["selection"][key] for key in QUESTION_FIELDS}
                proposed = {key: args[key] for key in QUESTION_FIELDS}
                raise ContractError("a106_revision_question_mismatch", detail={
                    "revises_subscore_ref": prior,
                    "different_fields": [key for key in QUESTION_FIELDS if previous[key] != proposed[key]],
                    "previous_question": previous, "proposed_question": proposed,
                    "requirement": "A revision must retain its predecessor's exact question binding. For a different biological scope, create a separate question without a predecessor."})
        cell = finalize_a106(args, source_rows)
        input_sources = [ref for ref in bindings if self.store.get(ref)["record_type"] == "source"]
        input_sources.extend(record["source_ref"] for ref in list(bindings)
            if (record := self.store.get(ref)).get("source_ref"))
        input_sources = list(dict.fromkeys(input_sources))
        for ref in input_sources:
            source = retain(ref, "source", possessed=False)
            for ancestor in source.get("parent_source_refs", ()):
                if ancestor not in input_sources:
                    input_sources.append(ancestor)
        payload = dict(version=VERSION, selection=args, question_key=question, source_cells=source_rows,
            direct_record_refs=direct, record_bindings=bindings, input_source_refs=input_sources,
            sheet={"cells": {COMPONENTS[0]: cell}})
        with self.store.transaction():
            self._install()
            assessment_heads = native.current_assessments()
            current_assessments = {row["sheet_ref"] for row in assessment_heads}
            stale = []
            for row in source_rows:
                if row["sheet_ref"] in current_assessments:
                    continue
                index = next(i for i, item in enumerate(args["experiments"])
                    if item["sheet_ref"] == row["sheet_ref"])
                assessment = row["experiment_assessment"]
                item = {"field": f"experiments.{index}.sheet_ref", "sheet_ref": row["sheet_ref"],
                    "experiment_ref": row["experiment_ref"], "assessment_key": assessment["assessment_key"]}
                head = next((head for head in assessment_heads
                    if (head["experiment_ref"], head["assessment_key"])
                    == (row["experiment_ref"], assessment["assessment_key"])), None)
                if (head is not None and head["sheet_ref"] in context.received_record_refs
                        and self.store.reference_subset([head["sheet_ref"]], plain(context.scope))):
                    item["latest_sheet_ref"] = head["sheet_ref"]
                stale.append(item)
            if stale:
                raise ContractError("a106_current_assessment_required", detail={
                    "stale_assessments": stale,
                    "requirement": "Select the current revision of each experiment assessment. "
                        "Read any listed latest_sheet_ref and obtain its requested cells before finalizing; "
                        "the finalizer does not replace selections automatically."})
            heads, superseded = [], set()
            for row in self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=?", (self.run_id,)):
                ref = json.loads(row["outcome"])["result"]["sheet_ref"]
                saved = self.read(ref)
                if saved["question_key"] == question:
                    heads.append(ref)
                    superseded.add(saved["selection"]["revises_subscore_ref"])
            current_subscores = [ref for ref in heads if ref not in superseded]
            if current_subscores != ([] if prior is None else [prior]):
                detail = {"field": "revises_subscore_ref", "requested_predecessor": prior,
                    "requirement": "A correction must revise the current final worksheet for this exact question."}
                visible = [ref for ref in current_subscores if ref in context.received_record_refs
                    and self.store.reference_subset([ref], plain(context.scope))]
                if visible:
                    detail["latest_subscore_refs"] = visible
                raise ContractError("a106_latest_subscore_revision_required", detail=detail)
            artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(signature, "application/json")
            record = self.store.put("source", dict(provider=PROVIDER, accession=None, uri=None,
                artifact_ref=artifact, text_ref=artifact, request_ref=request_ref, version=VERSION,
                retrieved_at=None, parent_source_refs=input_sources), origin="tool", scope=plain(context.scope))
            outcome = dict(status="completed", operation_ref=identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                record_refs=[record["id"]], changed_record_refs=[record["id"]], feedback=None,
                result={"sheet_ref": record["id"], "cells": _rows(payload, record["id"], requested)})
            validate_schema(outcome["result"]["cells"], cells_schema())
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get("record_type") != "source" or source.get("origin") != "tool"
                or source.get("provider") != PROVIDER or source.get("version") != VERSION):
            raise ContractError("a106_subscore_sheet_required")
        value = {key: val for key, val in source.items() if key not in {"id", "record_type", "origin"}}
        if identity("source", {"origin": "tool", "record": value}) != sheet_ref:
            raise ContractError("a106_subscore_identity_mismatch")
        request = self._artifact_json(source["request_ref"])
        if request.get("run_id") != self.run_id:
            raise ContractError("a106_subscore_run_mismatch")
        scope = self.store.validate_scope(request["scope"])
        self._native_provenance(scope, sheet_ref)
        operation = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])
        ).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation["signature"] != canonical(request):
            raise ContractError("a106_subscore_operation_mismatch")
        saved = self._artifact_json(source["artifact_ref"])
        outcome = json.loads(operation["outcome"])
        if (saved.get("version") != VERSION or saved.get("selection") != request["arguments"]
                or saved.get("question_key") != self._question_key(request["arguments"])
                or saved.get("input_source_refs") != source["parent_source_refs"]
                or outcome.get("status") != "completed" or outcome.get("record_refs") != [sheet_ref]
                or outcome.get("result", {}).get("sheet_ref") != sheet_ref
                or outcome.get("operation_ref") != identity("operation", {
                    "run_id": self.run_id, "episode_id": request["episode_id"], "key": request["operation_key"]})):
            raise ContractError("a106_subscore_saved_mismatch")
        validate_schema(saved["selection"], population_schema())
        validate_schema(saved["source_cells"], intervention_cells_schema())
        validate_schema(saved["sheet"]["cells"][COMPONENTS[0]], cell_schema())
        for ref, digest in saved["record_bindings"].items():
            if (not self.store.reference_subset([ref], plain(scope))
                    or identity("a106_subscore_input", self.store.get(ref)) != digest):
                raise ContractError("a106_subscore_input_mismatch")
        if not set(saved["direct_record_refs"]) <= set(saved["record_bindings"]):
            raise ContractError("a106_subscore_input_mismatch")
        native = LiteratureInterventionRepository(self.store, self.run_id)
        for row in saved["source_cells"]:
            expected = native.project_cells([row["sheet_ref"]], permitted_record_refs=[row["sheet_ref"]],
                components=[SCORE_COMPONENT])
            if canonical(expected) != canonical([row]):
                raise ContractError("a106_subscore_input_mismatch")
        rows = _rows(saved, sheet_ref, request["requested_components"])
        if canonical(rows) != canonical(outcome["result"]["cells"]):
            raise ContractError("a106_subscore_saved_cells_mismatch")
        return saved

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        for row in cells:
            refs.extend(row[key] for key in ("sheet_ref", "subject_ref", "assertion_ref", "comparison_ref", "revises_subscore_ref"))
            refs.extend(row["source_refs"])
            refs.extend(item["experiment_ref"] for item in row["experiments"])
            refs.extend(LiteratureInterventionRepository.cell_record_refs(row["selected_components"]))
        return list(dict.fromkeys(ref for ref in refs if ref is not None))
