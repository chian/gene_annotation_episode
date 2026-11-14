"""Current private resource identities and fingerprints of their actual bodies."""
import hashlib
from pathlib import Path

HOMES=('resource_job_submission',
       'resource_job_submission/api_resource_execution',
       'resource_job_submission/local_resource_execution',
       'resource_job_submission/hpc_resource_execution',
       'resource_result_acquisition',
       'legacy_annotation/resource_job_submission',
       'legacy_annotation/resource_job_submission/api_resource_execution',
       'legacy_annotation/resource_job_submission/local_resource_execution',
       'legacy_annotation/resource_job_submission/hpc_resource_execution',
       'legacy_annotation/resource_result_acquisition',
       'scientific_process/resource_job_submission',
       'scientific_process/resource_job_submission/api_resource_execution',
       'scientific_process/resource_job_submission/local_resource_execution',
       'scientific_process/resource_job_submission/hpc_resource_execution',
       'scientific_process/resource_result_acquisition',
       'hpc_coordination/resource_job_submission',
       'hpc_coordination/resource_job_submission/api_resource_execution',
       'hpc_coordination/resource_job_submission/local_resource_execution',
       'hpc_coordination/resource_job_submission/hpc_resource_execution',
       'hpc_coordination/resource_result_acquisition',
       'hpc_coordination/hpc_allocation_execution/resource_job_submission',
       'hpc_coordination/hpc_allocation_execution/resource_job_submission/api_resource_execution',
       'hpc_coordination/hpc_allocation_execution/resource_job_submission/local_resource_execution',
       'hpc_coordination/hpc_allocation_execution/resource_job_submission/hpc_resource_execution',
       'hpc_coordination/hpc_allocation_execution/resource_result_acquisition',
       'legacy_annotation/hpc_coordination/resource_job_submission',
       'legacy_annotation/hpc_coordination/resource_job_submission/api_resource_execution',
       'legacy_annotation/hpc_coordination/resource_job_submission/local_resource_execution',
       'legacy_annotation/hpc_coordination/resource_job_submission/hpc_resource_execution',
       'legacy_annotation/hpc_coordination/resource_result_acquisition',
       'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission',
       'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/api_resource_execution',
       'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/local_resource_execution',
       'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/hpc_resource_execution',
       'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_result_acquisition',
       'scientific_process/hpc_coordination/resource_job_submission',
       'scientific_process/hpc_coordination/resource_job_submission/api_resource_execution',
       'scientific_process/hpc_coordination/resource_job_submission/local_resource_execution',
       'scientific_process/hpc_coordination/resource_job_submission/hpc_resource_execution',
       'scientific_process/hpc_coordination/resource_result_acquisition',
       'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission',
       'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/api_resource_execution',
       'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/local_resource_execution',
       'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/hpc_resource_execution',
       'scientific_process/hpc_coordination/hpc_allocation_execution/resource_result_acquisition')
PRIVATE_FILES=('from_parent','child_commissioning','action_policy','resource_selection','internal_summary','goal','operations','report_fields','report_delivery','reference_access','to_parent','credit','episode',
               'task','decision_context','task_state','task_protocol','task_decision','decision_exchange','task_instructions','task_actions','task_report')
PARENT_MESSAGE_FILES=(
    'resource_job_submission/to_child_api_resource_execution.py',
    'resource_job_submission/from_child_api_resource_execution.py',
    'resource_job_submission/to_child_local_resource_execution.py',
    'resource_job_submission/from_child_local_resource_execution.py',
    'resource_job_submission/to_child_hpc_resource_execution.py',
    'resource_job_submission/from_child_hpc_resource_execution.py',
    'legacy_annotation/resource_job_submission/to_child_api_resource_execution.py',
    'legacy_annotation/resource_job_submission/from_child_api_resource_execution.py',
    'legacy_annotation/resource_job_submission/to_child_local_resource_execution.py',
    'legacy_annotation/resource_job_submission/from_child_local_resource_execution.py',
    'legacy_annotation/resource_job_submission/to_child_hpc_resource_execution.py',
    'legacy_annotation/resource_job_submission/from_child_hpc_resource_execution.py',
    'scientific_process/resource_job_submission/to_child_api_resource_execution.py',
    'scientific_process/resource_job_submission/from_child_api_resource_execution.py',
    'scientific_process/resource_job_submission/to_child_local_resource_execution.py',
    'scientific_process/resource_job_submission/from_child_local_resource_execution.py',
    'scientific_process/resource_job_submission/to_child_hpc_resource_execution.py',
    'scientific_process/resource_job_submission/from_child_hpc_resource_execution.py',
    'hpc_coordination/resource_job_submission/to_child_api_resource_execution.py',
    'hpc_coordination/resource_job_submission/from_child_api_resource_execution.py',
    'hpc_coordination/resource_job_submission/to_child_local_resource_execution.py',
    'hpc_coordination/resource_job_submission/from_child_local_resource_execution.py',
    'hpc_coordination/resource_job_submission/to_child_hpc_resource_execution.py',
    'hpc_coordination/resource_job_submission/from_child_hpc_resource_execution.py',
    'hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_api_resource_execution.py',
    'hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_api_resource_execution.py',
    'hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_local_resource_execution.py',
    'hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_local_resource_execution.py',
    'hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_hpc_resource_execution.py',
    'hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_hpc_resource_execution.py',
    'legacy_annotation/hpc_coordination/resource_job_submission/to_child_api_resource_execution.py',
    'legacy_annotation/hpc_coordination/resource_job_submission/from_child_api_resource_execution.py',
    'legacy_annotation/hpc_coordination/resource_job_submission/to_child_local_resource_execution.py',
    'legacy_annotation/hpc_coordination/resource_job_submission/from_child_local_resource_execution.py',
    'legacy_annotation/hpc_coordination/resource_job_submission/to_child_hpc_resource_execution.py',
    'legacy_annotation/hpc_coordination/resource_job_submission/from_child_hpc_resource_execution.py',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_api_resource_execution.py',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_api_resource_execution.py',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_local_resource_execution.py',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_local_resource_execution.py',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_hpc_resource_execution.py',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_hpc_resource_execution.py',
    'scientific_process/hpc_coordination/resource_job_submission/to_child_api_resource_execution.py',
    'scientific_process/hpc_coordination/resource_job_submission/from_child_api_resource_execution.py',
    'scientific_process/hpc_coordination/resource_job_submission/to_child_local_resource_execution.py',
    'scientific_process/hpc_coordination/resource_job_submission/from_child_local_resource_execution.py',
    'scientific_process/hpc_coordination/resource_job_submission/to_child_hpc_resource_execution.py',
    'scientific_process/hpc_coordination/resource_job_submission/from_child_hpc_resource_execution.py',
    'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_api_resource_execution.py',
    'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_api_resource_execution.py',
    'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_local_resource_execution.py',
    'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_local_resource_execution.py',
    'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/to_child_hpc_resource_execution.py',
    'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/from_child_hpc_resource_execution.py',
)
SHARED_FILES=('resource_episodes.py','homology_resource_adapter.py','resource_binding_catalogue.py',
 'resource_records.py','library/resource_binding_records.py','library/resource_custody.py',
 'library/resource_outcomes.py','library/resource_message.py','library/resource_information.py',
 'library/homology_resource_assignment.py','library/homology_resource_operations.py',
 'library/homology_resource_custody.py','library/homology_resource_returns.py',
 'library/homology_resource_progress.py')

def implementation_fingerprint(profile):
    root=Path(__file__).resolve().parents[1]
    paths=list(SHARED_FILES)+[home+'/'+name+'.py' for home in HOMES for name in PRIVATE_FILES]+list(PARENT_MESSAGE_FILES)
    if profile is not None:
        paths+=['composition_information.py','schema_information_text.py']
    digest=hashlib.sha256()
    for path in paths:
        digest.update(path.encode('utf-8'));digest.update(b'\0')
        source = root.parents[1] / path if path == 'schema_information_text.py' else root / path
        digest.update(source.read_bytes());digest.update(b'\0')
    return digest.hexdigest()

def binding_record(binding, identifier, path):
    if binding.binding_path != path or identifier != 'root_'+path.replace('/','_'):
        raise ValueError('resource_binding_identity_conflict')
    return {'binding_id':identifier,'version':identifier+'_v1',
            'implementation_sha256':implementation_fingerprint(binding._contract_information_profile),
            'configuration':binding.owner.configuration()}
