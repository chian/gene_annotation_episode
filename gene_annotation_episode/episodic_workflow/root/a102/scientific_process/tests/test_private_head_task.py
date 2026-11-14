"""Original A102 scientific head task/build/credit/presentation boundaries."""
import pytest
from .head_checks import actual, identity, action, presentation, instructions, saved_model, saved_state, monitor_exchange, incoming_rejection, revision, next_context, ready_child, cold_import
from .head_checks import instruction_service

@pytest.mark.parametrize('scenario,standalone', [('original_instruction', False), ('original_instruction', True), ('merged_default', False), ('merged_default', True), ('model_inventory', False), ('model_inventory', True), ('target_model_correspondence', False), ('target_model_correspondence', True), ('synthesis', False), ('synthesis', True), ('structural_discovery', False), ('structural_discovery', True), ('native_comparison', False), ('native_comparison', True), ('functional_feature_geometry', False), ('functional_feature_geometry', True), ('functional_contrast', False), ('functional_contrast', True), ('reference_attribution', False), ('reference_attribution', True), ('local_trait_attribution', False), ('local_trait_attribution', True), ('interface_constraints', False), ('interface_constraints', True), ('experimental_source_discovery', False), ('experimental_source_discovery', True), ('experimental_model_identity', False), ('experimental_model_identity', True), ('experimental_feature_geometry', False), ('experimental_feature_geometry', True), ('experimental_local_validation', False), ('experimental_local_validation', True), ('experimental_assessment', False), ('experimental_assessment', True)], ids=['original_instruction;standalone=false', 'original_instruction;standalone=true', 'merged_default;standalone=false', 'merged_default;standalone=true', 'model_inventory;standalone=false', 'model_inventory;standalone=true', 'target_model_correspondence;standalone=false', 'target_model_correspondence;standalone=true', 'synthesis;standalone=false', 'synthesis;standalone=true', 'structural_discovery;standalone=false', 'structural_discovery;standalone=true', 'native_comparison;standalone=false', 'native_comparison;standalone=true', 'functional_feature_geometry;standalone=false', 'functional_feature_geometry;standalone=true', 'functional_contrast;standalone=false', 'functional_contrast;standalone=true', 'reference_attribution;standalone=false', 'reference_attribution;standalone=true', 'local_trait_attribution;standalone=false', 'local_trait_attribution;standalone=true', 'interface_constraints;standalone=false', 'interface_constraints;standalone=true', 'experimental_source_discovery;standalone=false', 'experimental_source_discovery;standalone=true', 'experimental_model_identity;standalone=false', 'experimental_model_identity;standalone=true', 'experimental_feature_geometry;standalone=false', 'experimental_feature_geometry;standalone=true', 'experimental_local_validation;standalone=false', 'experimental_local_validation;standalone=true', 'experimental_assessment;standalone=false', 'experimental_assessment;standalone=true'])
def test_original_projector_descriptor_yield_and_build(tmp_path, scenario, standalone):
    with actual(tmp_path / 'actual', scenario, standalone) as value:
        identity(value)

@pytest.mark.parametrize('kind,status,saved,standalone', [('tool', 'completed', 'fresh', False), ('tool', 'completed', 'fresh', True), ('tool', 'partial', 'fresh', False), ('tool', 'partial', 'fresh', True), ('tool', 'invalid', 'fresh', False), ('tool', 'invalid', 'fresh', True), ('tool', 'failed', 'fresh', False), ('tool', 'failed', 'fresh', True), ('tool', 'unavailable', 'fresh', False), ('tool', 'unavailable', 'fresh', True), ('tool', 'invalid', 'unfinished', False), ('tool', 'invalid', 'unfinished', True), ('tool', 'failed', 'result', False), ('tool', 'failed', 'result', True), ('reason', 'completed', 'fresh', False), ('reason', 'completed', 'fresh', True), ('reason', 'completed', 'unfinished', False), ('reason', 'completed', 'unfinished', True), ('reason', 'completed', 'result', False), ('reason', 'completed', 'result', True), ('reason', 'partial', 'result', False), ('reason', 'partial', 'result', True), ('reason', 'invalid', 'result', False), ('reason', 'invalid', 'result', True), ('reason', 'failed', 'result', False), ('reason', 'failed', 'result', True), ('reason', 'unavailable', 'result', False), ('reason', 'unavailable', 'result', True), ('wait', 'completed', 'unfinished', False), ('wait', 'completed', 'unfinished', True), ('wait', 'failed', 'result', False), ('wait', 'failed', 'result', True)], ids=['tool;outcome=completed;saved=fresh;standalone=false', 'tool;outcome=completed;saved=fresh;standalone=true', 'tool;outcome=partial;saved=fresh;standalone=false', 'tool;outcome=partial;saved=fresh;standalone=true', 'tool;outcome=invalid;saved=fresh;standalone=false', 'tool;outcome=invalid;saved=fresh;standalone=true', 'tool;outcome=failed;saved=fresh;standalone=false', 'tool;outcome=failed;saved=fresh;standalone=true', 'tool;outcome=unavailable;saved=fresh;standalone=false', 'tool;outcome=unavailable;saved=fresh;standalone=true', 'tool;outcome=invalid;saved=unfinished;standalone=false', 'tool;outcome=invalid;saved=unfinished;standalone=true', 'tool;outcome=failed;saved=result;standalone=false', 'tool;outcome=failed;saved=result;standalone=true', 'reason;outcome=completed;saved=fresh;standalone=false', 'reason;outcome=completed;saved=fresh;standalone=true', 'reason;outcome=completed;saved=unfinished;standalone=false', 'reason;outcome=completed;saved=unfinished;standalone=true', 'reason;outcome=completed;saved=result;standalone=false', 'reason;outcome=completed;saved=result;standalone=true', 'reason;outcome=partial;saved=result;standalone=false', 'reason;outcome=partial;saved=result;standalone=true', 'reason;outcome=invalid;saved=result;standalone=false', 'reason;outcome=invalid;saved=result;standalone=true', 'reason;outcome=failed;saved=result;standalone=false', 'reason;outcome=failed;saved=result;standalone=true', 'reason;outcome=unavailable;saved=result;standalone=false', 'reason;outcome=unavailable;saved=result;standalone=true', 'wait;outcome=completed;saved=unfinished;standalone=false', 'wait;outcome=completed;saved=unfinished;standalone=true', 'wait;outcome=failed;saved=result;standalone=false', 'wait;outcome=failed;saved=result;standalone=true'])
def test_original_executed_outcomes_and_replay(tmp_path, kind, status, saved, standalone):
    with actual(tmp_path / 'actual', standalone=standalone) as value:
        action(value, status, kind, saved)

@pytest.mark.parametrize('case,standalone', [('unrecognized', False), ('unrecognized', True), ('bootstrap_unrecognized', False), ('bootstrap_unrecognized', True), ('scientific', False), ('scientific', True), ('scientific_bootstrap', False), ('scientific_bootstrap', True), ('scientific_update', False), ('scientific_update', True), ('scientific_lookup', False), ('scientific_lookup', True), ('lost_scientific_task', False), ('lost_scientific_task', True), ('hpc_priority', False), ('hpc_priority', True), ('missing_base', False), ('missing_base', True)], ids=['unrecognized;standalone=false', 'unrecognized;standalone=true', 'bootstrap_unrecognized;standalone=false', 'bootstrap_unrecognized;standalone=true', 'scientific;standalone=false', 'scientific;standalone=true', 'scientific_bootstrap;standalone=false', 'scientific_bootstrap;standalone=true', 'scientific_update;standalone=false', 'scientific_update;standalone=true', 'scientific_lookup;standalone=false', 'scientific_lookup;standalone=true', 'lost_scientific_task;standalone=false', 'lost_scientific_task;standalone=true', 'hpc_priority;standalone=false', 'hpc_priority;standalone=true', 'missing_base;standalone=false', 'missing_base;standalone=true'])
def test_original_provider_priority_and_fallback(tmp_path, case, standalone):
    with actual(tmp_path / 'actual', standalone=standalone) as value:
        presentation(value, case)

@pytest.mark.parametrize('exchange', [False, True], ids=['exchange=false', 'exchange=true'])
def test_original_instructions_and_summary(tmp_path, exchange):
    with actual(tmp_path / 'actual') as value:
        instructions(value, exchange)

@pytest.mark.parametrize('declared,answered', [(False, False), (False, True), (True, False), (True, True)], ids=['declared=false;answered=false', 'declared=false;answered=true', 'declared=true;answered=false', 'declared=true;answered=true'])
def test_saved_model_context(tmp_path, declared, answered):
    with actual(tmp_path / 'actual') as value:
        saved_model(value, declared, answered)

@pytest.mark.parametrize('standalone', [False, True], ids=['standalone=false', 'standalone=true'])
def test_saved_state_and_report(tmp_path, standalone):
    with actual(tmp_path / 'actual', standalone=standalone) as value:
        saved_state(value)

@pytest.mark.parametrize('role', ['monitor', 'unrelated'], ids=['monitor', 'unrelated'])
def test_existing_monitor_exchange(tmp_path, role):
    with actual(tmp_path / 'actual') as value:
        monitor_exchange(value, role)

@pytest.mark.parametrize('operand', ['assignment', 'purpose', 'path'], ids=['assignment', 'purpose', 'path'])
def test_original_incoming_rejection(tmp_path, operand):
    with actual(tmp_path / 'actual') as value:
        incoming_rejection(value, operand)

@pytest.mark.parametrize('standalone', [False, True], ids=['standalone=false', 'standalone=true'])
def test_original_revision_prepares_separate_child(tmp_path, standalone):
    with actual(tmp_path / 'actual', standalone=standalone) as value:
        revision(value)

@pytest.mark.parametrize('standalone', [False, True], ids=['standalone=false', 'standalone=true'])
def test_actual_next_context(tmp_path, standalone):
    with actual(tmp_path / 'actual', standalone=standalone) as value:
        next_context(value)

@pytest.mark.parametrize('standalone', [False, True], ids=['standalone=false', 'standalone=true'])
def test_ready_child_precedes_decision(tmp_path, standalone):
    with actual(tmp_path / 'actual', standalone=standalone) as value:
        ready_child(value)

@pytest.mark.parametrize('order', ['head_first', 'runtime_first'], ids=['head_first', 'runtime_first'])
def test_cold_import_order(tmp_path, order):
    cold_import(tmp_path / 'imports', order)

@pytest.mark.parametrize('case,exchange', [('default', False), ('default', True), ('instance_shadow', False), ('instance_shadow', True), ('nonparticipant', False), ('nonparticipant', True), ('nonparticipant_shadow', False), ('nonparticipant_shadow', True), ('custom_return', False), ('custom_return', True), ('custom_raise', False), ('custom_raise', True), ('subclass_return', False), ('subclass_return', True), ('subclass_raise', False), ('subclass_raise', True), ('custom_delegates', False), ('custom_delegates', True)], ids=['default;exchange=false', 'default;exchange=true', 'instance_shadow;exchange=false', 'instance_shadow;exchange=true', 'nonparticipant;exchange=false', 'nonparticipant;exchange=true', 'nonparticipant_shadow;exchange=false', 'nonparticipant_shadow;exchange=true', 'custom_return;exchange=false', 'custom_return;exchange=true', 'custom_raise;exchange=false', 'custom_raise;exchange=true', 'subclass_return;exchange=false', 'subclass_return;exchange=true', 'subclass_raise;exchange=false', 'subclass_raise;exchange=true', 'custom_delegates;exchange=false', 'custom_delegates;exchange=true'])
def test_instruction_service_override_and_private_composer(tmp_path, case, exchange):
    with actual(tmp_path / 'actual') as value:
        instruction_service(value, case, exchange)
