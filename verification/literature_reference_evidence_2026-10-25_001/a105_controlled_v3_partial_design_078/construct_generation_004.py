"""Additive native original-boundary correction, preserving003."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'build_declarations_003.py').read_text().replace("_003.json'","_004.json'")
s=s.replace("'population_ref':T", "'sheet_ref':dict(type='string',format='reference',**{'x-reference-namespace':'source'})")
start=s.index("    'native_api':[")
end=s.index("    'source_calls_sheet'",start)
s=s[:start]+"""    'native_api':['LiteratureControlledResponseRepository.populate_v3(context, arguments, operation_key) -> ToolOutcome',
        'LiteratureControlledResponseRepository.read(sheet_ref) -> OriginalPopulationPayload',
        'LiteratureControlledResponseRepository.project_cells(sheet_refs, *, permitted_record_refs, components) -> NativeFactV3[]',
        'LiteratureControlledResponseRepository.fact_cells(context, sheet_refs, *, components) -> NativeFactV3[]',
        'LiteratureControlledResponseRepository.validate_fact_values(context, cells) -> None',
        'LiteratureControlledResponseRepository.receive_cells(context, cells, operation_key) -> None',
        'LiteratureControlledResponseRepository.received_cells(context) -> NativeFactV3[]'],
    'native_host_context':{'fields':['run_id','episode_id','role','assignment','scope','received_record_refs'],
        'authority':'Actual ordinary episode/tool context supplied by Workflow, never model-selected owner IDs or caller-composed proof'},
    'native_form_source':'literature_controlled_response_component_cells',
    'native_tables':{'operations':'literature_controlled_response_operations','received':'literature_controlled_response_component_received',
        'delivery':'literature_controlled_response_component_delivery_bindings'},
    'native_component_identity':['sheet_ref','component_key'],
    'native_runtime_proof':'Inherited _runtime_delivery_cells reads successful runtime_report_attempts at run:parent:decision:typed_form; exact child runtime_episodes.request.report_contract (or authenticated selected repair), original form and child_episode_id/delivery_ref must match. No proof argument is accepted.',
"""+s[end:]
with (HERE/'build_declarations_004.py').open('x') as f:f.write(s)
exec(compile(s,str(HERE/'build_declarations_004.py'),'exec'),{'__file__':str(HERE/'build_declarations_004.py'),'__name__':'__main__'})
