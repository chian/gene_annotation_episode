"""Original flux_balance assignment identity and output-role declarations."""
ASSIGNMENT_VERSION = 'flux_balance_scientific_assignment_v1'
LAUNCH_VERSION = 'flux_balance_scientific_launch_v1'
OUTPUT_ROLES = ('original_model', 'selected_request', 'effective_model', 'effective_problem',
                'solution', 'flux_csv', 'native_log', 'manifest')
def is_compact_assignment(value):
    return value.get('version') == ASSIGNMENT_VERSION


def is_compact_launch(value):
    return value.get('version') == LAUNCH_VERSION


