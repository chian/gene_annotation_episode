"""Fresh scientific child native-return custody admission."""
from gene_annotation_episode.domain import ContractError
def validate_native_return_channels(selection, schema):
    """Require result custody when admitting a new native-capable child.

    Preparation-only work may return empty components and its real execution
    findings. This does not choose an investigation, run a job or widen a
    receipt. Historical closed commissions retain their original contracts.
    """
    from ..library.component_native_profiles import OPERATIONS
    from ..library.component_native_received_records import FACT_SOURCE, EXECUTION_SOURCE
    axis = selection.get('evidence_axis', {}).get('option_id')
    if axis not in OPERATIONS:
        return
    native = {OPERATIONS[axis]}
    if axis == 'A107':
        native.add('partner.request_detection_hpc')
    if axis == 'A110':
        native.add('chemistry.request_flux_balance_hpc')
    if not native.intersection(item['name'] for item in selection.get('child_tool_info', ())):
        return
    present = {node.get('x-source') for node in schema.get('properties', {}).values()}
    missing = sorted({FACT_SOURCE, EXECUTION_SOURCE} - present)
    if missing:
        raise ContractError('component_native_return_channels_required', detail={
            'field': 'report_schema', 'missing_fact_sources': missing,
            'repair': 'Use episode.return_contract for scientific_process and include both '
                + FACT_SOURCE + ' and ' + EXECUTION_SOURCE + ' as saved-fact return fields. '
                'scientific_process_results contains process metadata, not these numerical results.'})


