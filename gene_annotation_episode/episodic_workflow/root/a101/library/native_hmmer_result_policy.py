"""HMMER result facts, credit and completion policy on authenticated host ports."""
from __future__ import annotations
from copy import deepcopy
from ..communication import plain
from ..domain import ContractError
from ..execution_contracts import digest
from ..native_hmmer_acquisition import ORIGIN
from .hmmer_native_result_views import FAMILY_SOURCES, family_for_program

VERSION = 'native_hmmer_acquired_result_v1'


class NativeHMMERResultPolicy:
    def facts(self, context):
        bodies = list(self._own_bodies(context))
        result = {'execution_handoff_refs': [], 'execution_blast_hsps': [],
            'execution_result_refs': sorted({ref for body in bodies for ref in body['record_refs']}),
            'execution_result_origin': deepcopy(ORIGIN) if any(body['capture'] is not None
                and body['capture']['complete'] for body in bodies) else None,
            'execution_completed': any(body['complete'] for body in bodies),
            **{source: [] for source in FAMILY_SOURCES.values()}}
        fields = context.request.get('report_contract', {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested = {field.get('x-source') for field in fields.values()}
        seen = set()
        for body in bodies:
            family = family_for_program(body['target']['assignment']['requested_job']['native_hmmer']['program'])
            source = FAMILY_SOURCES[family]
            if source not in requested:
                continue
            for row in body['rows']:
                key = row['source_ref'], row['record_key']
                if key not in seen:
                    result[source].append(row)
                    seen.add(key)
        return result

    def credit_view(self, context, receiver_selection):
        selection = plain(receiver_selection)
        known, initial = set(selection['known_record_refs']), set(selection['initial_known_record_refs'])
        if not initial <= known:
            raise ContractError('native_hmmer_initial_references_must_be_known')
        # A stable observation/source identity survives page and metric choices.
        # This retains the existing acquisition-unit scheme, not a new scientific score.
        acquired = {self.result_identity(ref, context.scope)
            for ref in set(self.facts(context)['execution_result_refs']) & known}
        inherited = set()
        for reference in initial:
            try:
                inherited.add(self.result_identity(reference, context.scope))
            except (ValueError, KeyError, OSError):
                pass
        count = len(acquired-inherited)
        value = self.owner.acquired_record_unit*count
        return {'credit': value, 'operational_credit': value, 'new_handoff_count': 0,
            'new_acquired_record_count': count, 'operational_credit_binding': {
                'version': VERSION, 'handoff_unit': self.owner.handoff_unit,
                'acquired_record_unit': self.owner.acquired_record_unit,
                'scientific_credit': False, 'monitoring_credit': False}}

    def completion(self, context):
        for body in self._own_bodies(context):
            if not body['complete']:
                continue
            # Runtime must have completed the actual selected own action first.
            row = self.owner._selected_result_action(context.episode_id, body['operation_key'],
                body['tool_name'], body['arguments'])
            if row['result'] is None:
                continue
            return {'version': 'practical_completion_v1', 'run_id': context.run_id,
                'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                'endpoint': 'usable_handoff', 'operation_key': body['operation_key'],
                'receipt_sha256': digest(body), 'validation_keys': ['original_native_attempt',
                    'complete_sealed_bundle_acquisition', 'requested_native_numerical_projection']}
        return None
