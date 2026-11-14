from __future__ import annotations
def is_native_hmmer_target(target):
    return target.get('resource_kind') in {'local', 'hpc'} and 'native_hmmer' in target.get('assignment', {}).get('requested_job', {})

def is_native_blast_target(target):
    return type(target) is dict and target.get('resource_kind') == 'local' and (type(target.get('assignment')) is dict) and (type(target['assignment'].get('requested_job')) is dict) and ('native_blast' in target.get('assignment', {}).get('requested_job', {}))

def is_native_blast_masking_target(target):
    return type(target) is dict and target.get('resource_kind') == 'local' and (type(target.get('assignment')) is dict) and (type(target['assignment'].get('requested_job')) is dict) and ('native_blast_masking' in target['assignment']['requested_job'])

def is_native_blast_utility_target(target):
    return type(target) is dict and target.get('resource_kind') == 'local' and (type(target.get('assignment')) is dict) and (type(target['assignment'].get('requested_job')) is dict) and ('native_blast_utility' in target['assignment']['requested_job'])

def is_native_blast_database_target(target):
    return type(target) is dict and target.get('resource_kind') == 'hpc' and ('native_blast_database' in target.get('assignment', {}).get('requested_job', {}))

def is_standard_blast_database_target(target):
    return type(target) is dict and target.get('resource_kind') == 'hpc' and ('native_blast_standard_database' in target.get('assignment', {}).get('requested_job', {}))

def is_native_infernal_target(target):
    """Recognize the explicit request branch, without claiming an HPC binding."""
    return isinstance(target, dict) and target.get('resource_kind') in ('local', 'hpc') and isinstance(target.get('assignment'), dict) and isinstance(target['assignment'].get('requested_job'), dict) and ('native_infernal' in target['assignment']['requested_job'])

def is_native_infernal_preparation_target(target):
    """Recognize the explicit branch; this does not establish an HPC binding."""
    return isinstance(target, dict) and target.get('resource_kind') in ('local', 'hpc') and isinstance(target.get('assignment'), dict) and isinstance(target['assignment'].get('requested_job'), dict) and ('native_infernal_preparation' in target['assignment']['requested_job'])

def is_native_hmmer_preparation_target(target):
    """Recognize the explicit branch; this does not establish an HPC binding."""
    return isinstance(target, dict) and target.get('resource_kind') in ('local', 'hpc') and isinstance(target.get('assignment'), dict) and isinstance(target['assignment'].get('requested_job'), dict) and ('native_hmmer_preparation' in target['assignment']['requested_job'])

def is_native_rna_structure_target(target):
    return isinstance(target, dict) and target.get('resource_kind') == 'local' and isinstance(target.get('assignment'), dict) and isinstance(target['assignment'].get('requested_job'), dict) and ('native_rna_structure' in target['assignment']['requested_job'])

def is_native_protein_structure_target(target: dict) -> bool:
    return (type(target) is dict and target.get("resource_kind") == "local"
        and type(target.get("assignment")) is dict
        and type(target["assignment"].get("requested_job")) is dict
        and "native_protein_structure" in target["assignment"]["requested_job"])
