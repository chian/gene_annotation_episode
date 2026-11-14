"""Original macs2_peak assignment identity and output-role declarations."""
ASSIGNMENT_VERSION = 'macs2_peak_scientific_assignment_v1'
LAUNCH_VERSION = 'macs2_peak_scientific_launch_v1'
OUTPUT_ROLES = ('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal')
def is_compact_assignment(value):
    return isinstance(value, dict) and value.get('version') == ASSIGNMENT_VERSION


def is_compact_launch(value):
    return isinstance(value, dict) and value.get('version') == LAUNCH_VERSION


