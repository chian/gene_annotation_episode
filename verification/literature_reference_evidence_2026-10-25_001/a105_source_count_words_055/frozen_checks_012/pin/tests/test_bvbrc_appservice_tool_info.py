"""C4b tool-information checks; descriptions establish no deployed service."""
from copy import deepcopy

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.bvbrc_appservice_tool_info import (
    OPERATIONS, LAUNCH_OPERATIONS, RESULT_OPERATIONS,
    bvbrc_appservice_tool_contracts, bvbrc_appservice_tool_information,
    operation_catalog,
)


def test_exact_eleven_operations_and_responsible_owners():
    expected = {"enumerate_apps", "prepare", "workspace_metadata", "workspace_create",
                "upload", "submit", "status", "task_info", "list_outputs",
                "download_capability", "download"}
    assert {name.rsplit(".", 1)[1] for name in OPERATIONS} == expected
    assert set(LAUNCH_OPERATIONS) | set(RESULT_OPERATIONS) == set(OPERATIONS)
    assert len(LAUNCH_OPERATIONS) == 8 and len(RESULT_OPERATIONS) == 6
    assert "api.bvbrc_appservice.submit" not in RESULT_OPERATIONS
    assert "api.bvbrc_appservice.download" not in LAUNCH_OPERATIONS


def test_actual_four_field_information_and_separate_invocation_contract():
    infos = bvbrc_appservice_tool_information()
    contracts = bvbrc_appservice_tool_contracts(resource_id="selected-api")
    assert len(infos) == len(contracts) == 11
    for info, contract in zip(infos, contracts, strict=True):
        assert set(info) == {"name", "description", "resources", "instructions"}
        assert info == {key: contract[key] for key in info}
        assert info["resources"] == "api"
        assert all(isinstance(value, str) and value.strip() for value in info.values())
        Draft202012Validator.check_schema(contract["input_schema"])
        route = contract["invocation_route"]
        assert route["kind"] == "commission"
        assert all(row["resource_id"] == "selected-api" for row in route["routes"])
        for owner in route["routes"]:
            if owner["entry_role"] == "launch":
                assert owner["resource_role"] == "launch_api"
                assert info["name"] in LAUNCH_OPERATIONS
            else:
                assert owner["entry_role"] == owner["resource_role"] == "results"
                assert info["name"] in RESULT_OPERATIONS


def test_operation_catalogs_are_detached_and_closed():
    rows = operation_catalog("launch_api")
    original = deepcopy(rows)
    for row in rows:
        assert set(row) == {"name", "description", "input_schema"}
        Draft202012Validator.check_schema(row["input_schema"])
    rows[0]["input_schema"].clear()
    assert operation_catalog("launch_api") == original
    info = bvbrc_appservice_tool_information()
    info[0]["instructions"] = "altered"
    assert bvbrc_appservice_tool_information()[0]["instructions"] != "altered"


@pytest.mark.parametrize("role", ["root", "scientific", "launch", "monitor", "local", None])
def test_unsupported_roles_do_not_grant_an_operation(role):
    with pytest.raises(ValueError):
        operation_catalog(role)


@pytest.mark.parametrize("resource", [None, "", 1])
def test_configured_resource_identity_required_for_commission_contracts(resource):
    with pytest.raises(ValueError):
        bvbrc_appservice_tool_contracts(resource_id=resource)


def test_operation_specific_instructions_preserve_native_limits():
    infos = {row["name"].rsplit(".", 1)[1]: row for row in bvbrc_appservice_tool_information()}
    for operation, marker in {
        "enumerate_apps": "enumerate_apps",
        "prepare": "prepare_application",
        "workspace_metadata": "metadata_only=1",
        "workspace_create": "createUploadNodes",
        "upload": "multipart",
        "submit": "start_app2",
        "status": "query_tasks",
        "task_info": "job_result_id",
        "list_outputs": "fullHierachicalOutput",
        "download_capability": "get_download_url",
        "download": "Content-Range",
    }.items():
        assert marker in infos[operation]["instructions"]
    assert "scientific" in infos["submit"]["instructions"]
    assert "unknown" in infos["download_capability"]["instructions"]
