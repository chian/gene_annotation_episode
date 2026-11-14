"""Original lumpy assignment identity and output-role declarations."""
ASSIGNMENT_VERSION = 'lumpy_scientific_assignment_v1'
LAUNCH_VERSION = 'lumpy_scientific_launch_v1'
OUTPUT_ROLES = ('vcf', 'stderr', 'seal', 'bam_headers')
def is_compact_assignment(value):
    return isinstance(value, dict) and value.get('version') == ASSIGNMENT_VERSION


def is_compact_launch(value):
    return isinstance(value, dict) and value.get('version') == LAUNCH_VERSION


