"""Only the changed installed-Root policy ownership interfaces."""
import pytest
from root_policy_checks import paired_facts, paired_schema, paired_commissioning, paired_private, cold_entry


@pytest.mark.parametrize('scenario', ('saved', 'annotation', 'late_job', 'late_scientific', 'received_conflict'))
def test_root_report_policy(tmp_path, scenario):
    paired_facts(tmp_path, scenario)


@pytest.mark.parametrize('scenario', ('ordinary', 'late_job', 'root_no_receipt'))
def test_root_schema_policy(tmp_path, scenario):
    paired_schema(tmp_path, scenario)


@pytest.mark.parametrize('scenario', (
    'wait', 'receipt', 'declarations', 'declaration_none', 'late_filter',
    'fresh_arm', 'replay_arm', 'wrong_arm', 'wrong_role', 'catalog_none', 'catalog_wait',
    'execute_rejection', 'execute_lookup', 'selected_fresh', 'selected_replay', 'return_form'))
def test_root_commissioning_policy(tmp_path, scenario):
    paired_commissioning(tmp_path, scenario)


@pytest.mark.parametrize('kind', ('finish', 'summary'))
@pytest.mark.parametrize('placement', ('instance', 'class'))
def test_root_private_dynamic_override(tmp_path, kind, placement):
    paired_private(tmp_path, kind, placement)


@pytest.mark.parametrize('name', (
    'library.action_contracts', 'library.report_fact_assembly', 'commissioning_policy', 'task'))
def test_root_policy_cold_entry(tmp_path, name):
    cold_entry(tmp_path, name)
