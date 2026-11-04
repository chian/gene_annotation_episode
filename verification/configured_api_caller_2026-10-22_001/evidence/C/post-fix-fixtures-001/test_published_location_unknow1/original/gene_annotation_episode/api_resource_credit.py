"""Explicit API qualification with the existing operational contribution units.

Native projection remains untouched. Dispatch chooses one caller-bound
projection from the original assignment, including an unselected Launch's
initial zero-proof context; it never adds channel scores or selects execution.
"""
from __future__ import annotations

from copy import deepcopy
import math

from .communication import plain
from .episode_bindings import BindingContext
from .hmmer_resource_information import json_value


class ApiSearchOperationalCredit:
    requires_episode_receipts = True

    def __init__(self, reader, *, handoff_unit: float, acquired_record_unit: float):
        for value in (handoff_unit, acquired_record_unit):
            try:
                valid = type(value) in {int, float} and math.isfinite(value) and value > 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError('explicit_positive_operational_credit_units_required')
        if any(not callable(getattr(reader, name, None)) for name in
                ('as_record', 'qualify_launch', 'read_handoff_source', 'qualify_handoff', 'own_result_rows')):
            raise TypeError('explicit_api_information_reader_required')
        self.reader = reader
        self.handoff_unit, self.acquired_record_unit = handoff_unit, acquired_record_unit
        self._reader_record = json_value(reader.as_record())
        if not self._reader_record.get('registry_ref') or not self._reader_record.get('run_id'):
            raise ValueError('explicit_api_information_identity_required')

    def as_record(self):
        return {'version': 'received_api_search_operational_credit_v1',
            'reader': deepcopy(self._reader_record), 'handoff_unit': self.handoff_unit,
            'acquired_record_unit': self.acquired_record_unit,
            'launch_contribution': 'distinct_received_usable_physical_handoff_identities',
            'results_contribution': 'distinct_received_canonical_records_in_own_extraction_publication_rows',
            'baseline': 'frozen_initial_record_and_physical_handoff_identities',
            'qualification': 'original_assigned_job_inputs_selection_constraints_and_requested_selector',
            'scientific_credit': False, 'monitoring_credit': False,
            'controller_effect': 'operational_information_only_without_channel_summing'}

    @staticmethod
    def _references(value):
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise ValueError('resource_credit_requires_explicit_record_references')
        return value

    def __call__(self, context: BindingContext, receiver_selection: dict):
        if not isinstance(context, BindingContext) or context.role not in {'launch', 'launch_api', 'results'}:
            raise ValueError('resource_credit_requires_supported_resource_role')
        selected = json_value(receiver_selection)
        if (selected.get('run_id') != context.run_id or selected.get('episode_id') != context.episode_id
                or context.run_id != self._reader_record['run_id']):
            raise ValueError('resource_credit_receiver_identity_mismatch')
        known = self._references(selected.get('known_record_refs'))
        initial = set(self._references(selected.get('initial_known_record_refs')))
        if not initial <= set(known):
            raise ValueError('resource_credit_initial_references_must_be_known')
        handoff_count = acquired_count = 0
        if context.role == 'results':
            seen = set(initial)
            for row in self.reader.own_result_rows(context):
                if row['registry_ref'] != self._reader_record['registry_ref']:
                    raise ValueError('api_information_publication_conflict')
                reference = row['record_ref']
                if reference in known and reference not in seen:
                    seen.add(reference)
                    acquired_count += 1
        else:
            # Validate the original API request even before any order/proof.
            qualified = self.reader.qualify_launch(context)
            proofs = {reference: self.reader.read_handoff_source(reference, scope=plain(context.scope))
                for reference in dict.fromkeys(known)}
            def identity(proof):
                if (proof['run_id'] != context.run_id or proof['registry_ref'] != self._reader_record['registry_ref']
                        or proof['execution_handoff']['state'] != 'usable'
                        or proof['execution_handoff']['failure'] is not None):
                    raise ValueError('api_information_proof_identity_conflict')
                return proof['registry_ref'], proof['job_ref']
            seen = {identity(proofs[reference]) for reference in initial if proofs[reference] is not None}
            for proof in proofs.values():
                if proof is None:
                    continue
                key = identity(proof)
                if key in seen:
                    continue
                self.reader.qualify_handoff(context, qualified, proof)
                seen.add(key)
                handoff_count += 1
        credit = self.handoff_unit * handoff_count + self.acquired_record_unit * acquired_count
        if not math.isfinite(credit):
            raise ValueError('finite_operational_credit_required')
        return {'credit': credit, 'operational_credit': credit, 'operational_credit_binding': self.as_record(),
            'new_handoff_count': handoff_count, 'new_acquired_record_count': acquired_count}


class ResourceCreditDispatch:
    requires_episode_receipts = True

    def __init__(self, *, native_projector, api_projector,
                 native_resource_id: str, api_resource_id: str):
        if (not callable(native_projector) or not callable(api_projector)
                or not callable(getattr(native_projector, 'as_record', None))
                or not callable(getattr(api_projector, 'as_record', None))
                or not isinstance(native_resource_id, str) or not native_resource_id
                or not isinstance(api_resource_id, str) or not api_resource_id
                or native_resource_id == api_resource_id):
            raise ValueError('explicit_resource_credit_routes_required')
        self.native_projector, self.api_projector = native_projector, api_projector
        self.native_resource_id, self.api_resource_id = native_resource_id, api_resource_id

    def as_record(self):
        return {'version': 'explicit_resource_credit_dispatch_v1', 'routes': [
            {'job_request_contract': 'native_homology', 'resource_id': self.native_resource_id,
                'projection': json_value(self.native_projector.as_record())},
            {'job_request_contract': 'public_hmmer', 'resource_id': self.api_resource_id,
                'projection': json_value(self.api_projector.as_record())}]}

    def __call__(self, context, receiver_selection):
        if not isinstance(context, BindingContext):
            raise TypeError('resource_credit_binding_context_required')
        assignment = plain(context.assignment)
        selected = (assignment.get('handoff', {}).get('resource_selection') if context.role == 'results'
            else assignment.get('resource_selection'))
        job = assignment.get('job_request', {})
        if context.role == 'launch' and selected is None:
            if job.get('provider') == 'hmmer':
                projector = self.api_projector
            elif (job and set(job) <= {'query_ref', 'cpu', 'search_mode', 'existing_job_ref'}
                    and ('existing_job_ref' in job or {'query_ref', 'cpu'} <= set(job))):
                projector = self.native_projector
            else:
                raise ValueError('unsupported_resource_credit_job_request')
        else:
            resource = None if selected is None else selected.get('resource_id')
            if resource == self.native_resource_id:
                projector = self.native_projector
            elif resource == self.api_resource_id:
                projector = self.api_projector
            else:
                raise ValueError('resource_credit_selection_mismatch')
        return projector(context, receiver_selection)


__all__ = ['ApiSearchOperationalCredit', 'ResourceCreditDispatch']
