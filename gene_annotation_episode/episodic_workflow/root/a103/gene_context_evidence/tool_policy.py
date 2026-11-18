"""Original own-A103 Scientific validate_tool_name."""
from ..domain import ContractError


def validate_tool_name(tool_name):
    if tool_name == 'sequence.align':
        raise ContractError('a103_new_sequence_comparison_requires_shared_parent')
