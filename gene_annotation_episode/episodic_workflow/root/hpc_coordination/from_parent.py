"""HPC parent and prediction specializations of the ordinary Episode loop.

Launch remains the existing launch -> launch_hpc iteration. Known monitoring
and result parsing are single tools of the HPC parent. This binding never calls
a model, polls in a loop, or decides to commission children itself.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import asyncio
import shlex
import subprocess
import time

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library.hpc_campaign import (YIELD_ROLES, accepts, bind_progress, build_plan,
    incorporate_progress, telemetry, timestamp, validate_commission)
from gene_annotation_episode.episodic_workflow.root.library.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.root.library import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.root.library import hpc_queue
from gene_annotation_episode.episodic_workflow.root.library.hpc_resource_prediction import forecast_metric, pbs_resource_metrics, physical_attempt_key


TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


def assignment_schema(self, role):
    self.credit_kind(role)
    fields = {'commission_source_ref': {'type': 'string', 'format': 'reference'}}
    if self.commissions:
        fields['commission_id'] = {'type': 'string', 'enum': list(self.commissions)}
    required = []
    fields['tool_request'] = obj({'name': TEXT, 'resources': {'enum': ['api', 'local', 'hpc']},
        'arguments_json': TEXT, 'result_reader': TEXT, 'objective': TEXT})
    schema = obj(fields, required=required)
    if self.commissions:
        schema['oneOf'] = [{'required': ['commission_id']}, {'required': ['commission_source_ref']}]
    else:
        schema['required'].append('commission_source_ref')
    return schema

def commission_identity(assignment):
    return {key: assignment[key] for key in ('commission_id', 'commission_source_ref') if key in assignment}

def _commission(self, assignment, scope):
    if 'commission_source_ref' in assignment:
        from gene_annotation_episode.hpc_commission_sources import read
        return read(self.store, assignment['commission_source_ref'], scope=plain(scope), resources=self.resources)
    return self.commissions[assignment['commission_id']]

def prepare_assignment(self, parent, role, selection, scope, operation_key):
    selection = plain(selection)
    validate_schema(selection, self.assignment_schema(role))
    if 'commission_source_ref' in selection:
        if selection['commission_source_ref'] not in parent.received_record_refs:
            raise ValueError('hpc_commission_source_not_received_by_parent')
        self._commission(selection, scope)
    if 'tool_request' in selection:
        self._tool_request(selection['tool_request'], scope)
    if self.private_yield_binding and 'yield_bindings' not in self._commission(selection, scope):
        raise ValueError('hpc_commission_yield_binding_required:' + role)
    return selection

def _tool_request(self, request, scope):
    """Resolve the parent's request from its real frozen tool library."""
    workflow = getattr(self.services, 'workflow', None)
    binding = getattr(workflow, 'scientific_process_binding', None)
    if binding is None:
        raise ValueError('scientific_tool_library_required_for_hpc_tool_request')
    contract = binding.tool_library.resolve_invocations([
        {key: request[key] for key in ('name', 'resources')}], binding._information_catalog(scope))[0]
    readers = [row for row in binding.tool_library.parent_tool_info(binding._information_catalog(scope))
               if row['name'] == request['result_reader']]
    if not readers:
        raise ValueError('actual_result_reader_required_for_hpc_tool_request')
    arguments = json.loads(request['arguments_json'])
    validate_schema(arguments, contract['input_schema'])
    return {'objective': request['objective'], 'tool_contract': contract,
        'arguments': arguments, 'result_reader': request['result_reader'], 'result_reader_options': readers,
        'execution_rule': 'Implement this exact requested computation through the HPC template. '
            'The declared resources describe the original callable; they do not grant a remote adapter. '
            'Establish the software, staged operands and owning result reader before launch. '
            'Return complete original artifacts for that reader; do not replace scientific grading '
            'with the allocation acceptance score.'}

