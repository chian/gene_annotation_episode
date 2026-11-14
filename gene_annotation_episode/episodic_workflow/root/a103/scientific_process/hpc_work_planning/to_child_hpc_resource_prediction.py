"""Prepare this parent's selected prediction question and original commission operands."""
from gene_annotation_episode.episodic_workflow.root.a103.communication import plain
from gene_annotation_episode.episodic_workflow.root.a103.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.a103.execution_contracts import obj
TEXT = {'type': 'string', 'minLength': 1}

def assignment_schema(commissions):
    fields = {'commission_source_ref': {'type': 'string', 'format': 'reference'}}
    if commissions:
        fields['commission_id'] = {'type': 'string', 'enum': list(commissions)}
    required = []
    fields['owner_episode_id'] = TEXT
    required.append('owner_episode_id')
    schema = obj(fields, required=required)
    if commissions:
        schema['oneOf'] = [{'required': ['commission_id']}, {'required': ['commission_source_ref']}]
    else:
        schema['required'].append('commission_source_ref')
    return schema

def commission_identity(assignment):
    return {key: assignment[key] for key in ('commission_id', 'commission_source_ref') if key in assignment}

def prepare_request(parent, selection, commissions):
    selected = plain(selection)
    validate_schema(selected, assignment_schema(commissions))
    if parent.role != 'hpc' or selected['owner_episode_id'] != parent.episode_id or commission_identity(selected) != commission_identity(parent.assignment):
        raise ValueError('prediction_or_execution_must_belong_to_its_original_hpc_parent')
    return selected
