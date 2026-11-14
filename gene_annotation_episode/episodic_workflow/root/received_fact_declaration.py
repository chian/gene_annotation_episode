"""Authenticate saved report declarations using each child's private parser."""
from importlib import import_module
from .scientific_process_records import selection_fields


def validate_saved_fact_form(*, child, submitted_schema_json, expanded_schema, declaration):
    selection = child.assignment.get('selection', {})
    field = selection_fields(selection)[0]
    axis = selection[field]['option_id']
    parser = {
        'A101': '.a101.episode_contract_information',
        'A102': '.a102.episode_contract_information',
        'A103': '.a103.episode_contract_information',
        'A104': '.a104.episode_contract_information',
        'A105': '.a105.episode_contract_information',
        'A106': '.a106.episode_contract_information',
        'A107': '.a107.episode_contract_information',
        'A108': '.a108.episode_contract_information',
        'A110': '.a110.episode_contract_information',
    }[axis]
    return import_module(parser, __package__).validate_saved_fact_form(
        child_role=child.role, submitted_schema_json=submitted_schema_json,
        expanded_schema=expanded_schema, declaration=declaration)
