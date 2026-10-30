"""Only already-inspected engineering tests that do not open primary packets."""
import json
from pathlib import Path
import subprocess
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
nodes = ['tests/test_literature_partner_native_inputs.py']
for case in ('paired','marginal','capability'):
    for name in ('test_actual_selected_return_and_saved_only_reconstruction', 'test_ordinary_child_parent_delivery_has_one_own_observation_per_action'):
        nodes.append(f'tests/test_literature_context_integration.py::{name}[{case}]')
nodes += ['tests/test_literature_context_integration.py::test_context_task_repeats_after_lookup_and_reconstruction_at_provider_boundary',
 'tests/test_literature_context_integration.py::test_parent_receives_exact_definitions_once_with_only_requested_cells']
for case in ('False-False','False-True'):
    nodes.append(f'tests/test_literature_reaction_integration.py::test_selected_typed_values_and_reconstruction_without_source_bytes[{case}]')
nodes += ['tests/test_literature_reaction_integration.py::test_selected_in_ordinary_child_and_received_once[False]',
 'tests/test_literature_reaction_integration.py::test_recurring_reaction_task_and_material_qualifications_at_provider',
 'tests/test_literature_reaction_integration.py::test_parent_steering_groups_only_admitted_reaction_cells_and_keeps_own_task']
for case in ('matched','censored','baseline_reused'):
    for name in ('test_selected_components_saved_only_reconstruction_and_exact_typed_subset','test_ordinary_partner_child_parent_delivery_preserves_scientific_meanings'):
        nodes.append(f'tests/test_literature_partner_integration.py::{name}[{case}]')
nodes += ['tests/test_literature_partner_integration.py::test_partner_task_repeats_after_lookup_delta_and_reconstruction']
command = [sys.executable,'-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(HERE/'constructed_pytest_state'),*nodes]
proc = subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
receipt = {'kind':'constructed_engineering_checks_not_primary_validation','command':command,'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
(HERE/'CONSTRUCTED_CHECKS_001.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(proc.stdout, end='')
print(proc.stderr, end='')
sys.exit(proc.returncode)
