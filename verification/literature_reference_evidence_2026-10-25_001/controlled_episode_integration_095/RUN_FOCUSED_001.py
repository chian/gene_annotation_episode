"""Run the bounded isolated engineering checks and retain actual provenance."""
from pathlib import Path
import hashlib
import json
import sys

import pytest
from literature_controlled_response_worker_fixture_095 import module_imports

BASE=Path(__file__).resolve().parent
PIN=BASE/'coherent_code_001'
arguments=['-q','--rootdir='+str(PIN),'-c',str(BASE/'pytest095.ini'),
    '--basetemp='+str(BASE/'focused_tests_001'),
    '-o','cache_dir='+str(BASE/'focused_tests_001/pytest_cache'),
    'tests/test_literature_controlled_response_prompt.py',
    'tests/test_literature_controlled_response_communication.py',
    'tests/test_literature_controlled_response_monitor_consumer.py',
    'tests/test_literature_controlled_response_episode_integration.py::test_opt_in_default_contracts_original_descriptor_and_exact_selectors',
    'tests/test_literature_controlled_response_episode_integration.py::test_original_saved_descriptor_replay_and_exact_parent_subset_without_readers',
    'tests/test_literature_controlled_response_episode_integration.py::test_unknown_and_conflicting_joint_assignments_cross_the_original_typed_boundary',
    'tests/test_literature_controlled_response_episode_integration.py::test_production_worker_restores_original_controlled_descriptor_before_transport',
    'tests/test_literature_controlled_response_consumer.py::test_actual_runtime_digest_and_complete_alternate_wrapper_cannot_replace_selected_output',
    'tests/test_local_return_history.py','tests/test_completion_evidence.py','tests/test_progress_receipt_order.py',
    'tests/test_recursive_monitoring.py::test_form_delivery_is_explicit_typed_idempotent_and_transactional',
    'tests/test_literature_ratio_source_episode_integration.py']
manifest=json.loads((BASE/'COHERENT_CODE_MANIFEST_001.json').read_text())
before={path:hashlib.sha256((PIN/path).read_bytes()).hexdigest() for path in manifest['files']}
assert before==manifest['files']
(BASE/'FOCUSED_COMMAND_001.json').write_text(json.dumps({'cwd':str(PIN),'python':sys.executable,'pytest_arguments':arguments,
    'evidence_class':'scripted engineering fixtures; no configured model or primary-source scientific claim'},indent=2)+'\n')
code=int(pytest.main(arguments))
imports=module_imports()
assert imports['runtime_implementation_sha256']==manifest['runtime_implementation_sha256']
assert all(Path(row['path']).is_relative_to(PIN) for name,row in imports['modules'].items()
    if name.startswith(('gene_annotation_episode','method_loop')))
(BASE/'FOCUSED_IMPORTS_001.json').write_text(json.dumps(imports,indent=2)+'\n')
after={path:hashlib.sha256((PIN/path).read_bytes()).hexdigest() for path in manifest['files']}
assert after==before
(BASE/'FOCUSED_RESULT_001.json').write_text(json.dumps({'exit_code':code,'pin_files_unchanged':True,
    'runtime_implementation_sha256':imports['runtime_implementation_sha256'],'actual_repository_imports':len(imports['modules']),
    'evidence_class':'scripted engineering fixtures; no scientific completion claim'},indent=2)+'\n')
raise SystemExit(code)
