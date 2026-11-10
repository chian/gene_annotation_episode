"""Pure current/legacy contract controls; no native search or episode evidence."""
from copy import deepcopy
import hashlib

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.domain import ContractError, identity
from gene_annotation_episode import restriction_mapping_native as native
from gene_annotation_episode import restriction_mapping_readers as readers
from gene_annotation_episode import restriction_mapping_worker as worker
from gene_annotation_episode.restriction_mapping_bound_contracts import (
    restriction_bound_schema, restriction_native_request,
    validate_restriction_alias_arguments, validate_restriction_bound_record,
)
from gene_annotation_episode.restriction_mapping_contracts import (
    restriction_canonical, restriction_schema,
)
from gene_annotation_episode.restriction_mapping_tool_info import TOOL, restriction_tool_contract


SEQUENCE = "AAAAGAATTCTTTT"


def binding():
    """Engineering identity for pure validation; not a received Source or grant."""
    return dict(version="restriction_selected_sequence_v1", namespace="subject",
        sequence_ref="subject_restriction_public", source_ref="source_" + "1" * 24,
        sequence_version=1, content_sha256=hashlib.sha256(SEQUENCE.encode()).hexdigest(),
        length_nt=len(SEQUENCE), origin_mapping_ref=None)


def canonical_arguments(selection=None, topology="linear"):
    return dict(mode="native", sequence_ref=binding()["sequence_ref"],
        enzyme_selection=deepcopy(selection if selection is not None else
            {"kind": "explicit", "names": ["BamHI", "EcoRI"]}), topology=topology)


def reservation(tool_name=TOOL, arguments=None):
    """Unexecuted engineering metadata in the original closed record shape."""
    arguments = deepcopy(arguments if arguments is not None else dict(mode="native",
        sequence_ref=binding()["sequence_ref"], enzyme_names=["EcoRI"]))
    key = "engineering-restriction-public-contract"
    directory = "/engineering/state/native-restriction/" + hashlib.sha256(key.encode()).hexdigest()
    pin = lambda path: dict(path=path, sha256="0" * 64, size_bytes=0)
    request = (restriction_native_request(tool_name, arguments, sequence=SEQUENCE, sequence_binding=binding())
        if arguments["mode"] == "native" else dict(version="restriction_worker_request_v1", mode="saved",
            native_file=pin("/engineering/retained/native.json"), catalog_file=None,
            selected_sequence=binding()))
    return dict(version="restriction_operation_reservation_v1", operation_key=key,
        operation_ref=identity("operation", dict(key=key, name=tool_name, arguments=arguments)),
        tool_name=tool_name, arguments=arguments, scope=dict(subject_refs=[binding()["sequence_ref"]]),
        work_mode=arguments["mode"], input_source_ref=binding()["source_ref"],
        prior_result_source_ref=arguments.get("result_source_ref"), sequence_binding=binding(),
        worker_request=request, software=dict(python=pin("/engineering/runtime/bin/python"),
            implementation_files=[pin("/engineering/source/restriction_mapping_worker.py")],
            biopython_version="1.88", native_source_file=pin("/engineering/Bio/Restriction/Restriction.py"),
            dictionary_file=pin("/engineering/Bio/Restriction/Restriction_Dictionary.py"), environment={}),
        policy=dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3),
        directory=directory, request_file=pin(directory + "/request.json"),
        output_directory=directory + "/output", handle_path=directory + "/handle.json",
        stdout_path=directory + "/stdout.txt", stderr_path=directory + "/stderr.txt")


@pytest.fixture(autouse=True)
def no_scientific_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure restriction contract performed scientific work")
    monkeypatch.setattr(native, "run_restriction_mapping", forbidden)
    monkeypatch.setattr(readers, "read_restriction_mapping", forbidden)
    monkeypatch.setattr(worker, "read_restriction_mapping", forbidden)
    monkeypatch.setattr(worker, "run_restriction_worker", forbidden)


@pytest.mark.parametrize("selection", [
    {"kind": "explicit", "names": ["BamHI", "EcoRI"]},
    {"kind": "explicit", "names": []},
    {"kind": "commercial_native_batch", "names": None},
])
@pytest.mark.parametrize("topology", ["linear", "circular"])
def test_canonical_native_request_keeps_exact_selected_population_and_binding(selection, topology):
    arguments = canonical_arguments(selection, topology)
    before = restriction_canonical(arguments)
    value = restriction_native_request(TOOL, arguments, sequence=SEQUENCE, sequence_binding=binding())
    assert value == dict(version="restriction_worker_request_v1", mode="native", sequence=SEQUENCE,
        selected_sequence=binding(), enzyme_selection=selection, topology=topology)
    assert worker.validate_restriction_worker_request(value) == value
    assert restriction_canonical(arguments) == before
    if selection["kind"] == "explicit":
        value["enzyme_selection"]["names"].append("HindIII")
        assert restriction_canonical(arguments) == before


def test_explicit_names_are_not_resolved_or_remapped_by_the_host_contract():
    selection = {"kind": "explicit", "names": ["literal_unresolved_enzyme", "ecori"]}
    value = restriction_native_request(TOOL, canonical_arguments(selection),
        sequence=SEQUENCE, sequence_binding=binding())
    assert value["enzyme_selection"] == selection


@pytest.mark.parametrize("tool_name", [TOOL, "find_restriction_enzymes"])
@pytest.mark.parametrize("topology", [None, "linear", "circular"])
def test_legacy_native_arguments_and_original_topology_defaults_are_literal(tool_name, topology):
    arguments = dict(mode="native", sequence_ref=binding()["sequence_ref"])
    if tool_name == TOOL:
        arguments["enzyme_names"] = ["EcoRI", "BamHI"]
    if topology is not None:
        arguments["topology"] = topology
    before = restriction_canonical(arguments)
    checked = validate_restriction_alias_arguments(tool_name, arguments)
    request = restriction_native_request(tool_name, arguments, sequence=SEQUENCE, sequence_binding=binding())
    expected = ({"kind": "explicit", "names": ["EcoRI", "BamHI"]} if tool_name == TOOL else
        {"kind": "commercial_native_batch", "names": None})
    assert request["enzyme_selection"] == expected
    assert request["topology"] == (topology or ("circular" if tool_name == TOOL else "linear"))
    assert restriction_canonical(checked) == restriction_canonical(arguments) == before
    assert identity("operation", dict(key="old-key", name=tool_name, arguments=checked)) == identity(
        "operation", dict(key="old-key", name=tool_name, arguments=arguments))
    checked["sequence_ref"] = "another_engineering_identity"
    assert restriction_canonical(arguments) == before


@pytest.mark.parametrize("tool_name", [TOOL, "find_restriction_enzymes"])
def test_old_saved_arguments_and_reservations_stay_readable_without_selection_defaults(tool_name):
    arguments = dict(mode="saved", result_source_ref="source_" + "2" * 24)
    value = reservation(tool_name, arguments)
    before = restriction_canonical(value)
    assert validate_restriction_alias_arguments(tool_name, arguments) == arguments
    assert validate_restriction_bound_record("Reservation", value) == value
    assert restriction_canonical(value) == before
    with pytest.raises((ContractError, ValueError)):
        restriction_native_request(tool_name, arguments, sequence=SEQUENCE, sequence_binding=binding())


@pytest.mark.parametrize("tool_name", [TOOL, "find_restriction_enzymes"])
def test_old_native_reservation_authenticates_original_arguments_without_rewriting(tool_name):
    arguments = dict(mode="native", sequence_ref=binding()["sequence_ref"])
    if tool_name == TOOL:
        arguments["enzyme_names"] = ["EcoRI"]
    value = reservation(tool_name, arguments)
    before = restriction_canonical(value)
    assert validate_restriction_bound_record("Reservation", value) == value
    assert restriction_canonical(value) == before


@pytest.mark.parametrize("tool_name,arguments", [
    (TOOL, dict(mode="native", sequence_ref="subject_engineering", enzyme_names=["EcoRI"],
        enzyme_selection={"kind": "explicit", "names": ["EcoRI"]}, topology="linear")),
    (TOOL, dict(mode="native", sequence_ref="subject_engineering")),
    (TOOL, dict(mode="native", sequence_ref="subject_engineering",
        enzyme_selection={"kind": "explicit", "names": ["EcoRI"]})),
    (TOOL, canonical_arguments(True)),
    (TOOL, canonical_arguments({"kind": "explicit", "names": True})),
    (TOOL, canonical_arguments({"kind": "explicit", "names": [True]})),
    (TOOL, canonical_arguments({"kind": "explicit", "names": ["EcoRI", "EcoRI"]})),
    (TOOL, canonical_arguments({"kind": "explicit", "names": [""]})),
    (TOOL, canonical_arguments({"kind": "commercial_native_batch", "names": []})),
    (TOOL, canonical_arguments({"kind": "commercial", "names": None})),
    (TOOL, canonical_arguments({"kind": "explicit", "names": [], "extra": False})),
    (TOOL, canonical_arguments(topology=True)),
    (TOOL, {**canonical_arguments(), "sequence_ref": False}),
    (TOOL, {**canonical_arguments(), "mode": True}),
    (TOOL, {**canonical_arguments(), "extra": "undeclared"}),
    (TOOL, dict(mode="saved", result_source_ref="source_engineering", topology="linear")),
    ("find_restriction_enzymes", canonical_arguments()),
    ("another_restriction_alias", canonical_arguments()),
])
def test_closed_argument_boundary_rejects_ambiguous_or_wrongly_typed_selections(tool_name, arguments):
    with pytest.raises((ContractError, ValueError)):
        validate_restriction_alias_arguments(tool_name, arguments)


def test_single_advertised_local_direct_contract_requires_current_explicit_native_operands():
    contract = restriction_tool_contract()
    assert contract["name"] == TOOL == "find_restriction_sites"
    assert contract["resources"] == "local" and contract["invocation_route"] == {"kind": "direct"}
    schema = contract["input_schema"]
    Draft202012Validator.check_schema(schema)
    native_schema, saved_schema = schema["anyOf"]
    assert set(native_schema["required"]) == {"mode", "sequence_ref", "enzyme_selection", "topology"}
    assert set(saved_schema["required"]) == {"mode", "result_source_ref"}
    assert native_schema["properties"]["enzyme_selection"] == restriction_schema("EnzymeSelection")
    validator = Draft202012Validator(schema)
    for selection in ({"kind": "explicit", "names": []},
            {"kind": "explicit", "names": ["EcoRI", "BamHI"]},
            {"kind": "commercial_native_batch", "names": None}):
        assert validator.is_valid(canonical_arguments(selection))
    assert validator.is_valid(dict(mode="saved", result_source_ref="source_engineering"))
    legacy = dict(mode="native", sequence_ref="subject_engineering", enzyme_names=["EcoRI"])
    assert validate_restriction_alias_arguments(TOOL, legacy) == legacy
    assert not validator.is_valid(legacy)
    for field in ("mode", "sequence_ref", "enzyme_selection", "topology"):
        candidate = canonical_arguments()
        candidate.pop(field)
        assert not validator.is_valid(candidate)
    assert not validator.is_valid({**canonical_arguments(), "enzyme_names": ["EcoRI"]})
    assert not validator.is_valid(canonical_arguments(topology=False))
    assert not validator.is_valid(canonical_arguments({"kind": "explicit", "names": [False]}))
    assert not validator.is_valid(dict(mode="saved", result_source_ref="source_engineering", enzyme_names=[]))


def test_public_contract_is_detached_and_keeps_existing_coordinate_and_population_meanings():
    contract = restriction_tool_contract()
    text = contract["instructions"]
    for meaning in ("first_base_after_cut_1based", "recognition_start_1based", "not_recorded",
            "zero-based half-open", "complete empty", "unknown counts remain null"):
        assert meaning in text
    contract["input_schema"]["anyOf"][0]["properties"]["enzyme_selection"].clear()
    assert restriction_tool_contract()["input_schema"]["anyOf"][0]["properties"]["enzyme_selection"] == (
        restriction_schema("EnzymeSelection"))
    schema = restriction_bound_schema("Reservation")
    schema["properties"]["policy"].clear()
    assert restriction_bound_schema("Reservation")["properties"]["policy"]["properties"]


@pytest.mark.parametrize("field,value", [
    ("memory_bytes", True), ("memory_bytes", 20.0),
    ("scratch_bytes", False), ("scratch_bytes", 4.0),
    ("wall_seconds", True), ("wall_seconds", 0),
])
def test_existing_resource_policy_rejects_boolean_counts_and_invalid_limits(field, value):
    record = reservation()
    record["policy"][field] = value
    with pytest.raises((ContractError, ValueError)):
        validate_restriction_bound_record("Reservation", record)


def test_current_native_reservation_keeps_canonical_request_and_operation_identity():
    record = reservation(arguments=canonical_arguments({"kind": "commercial_native_batch", "names": None}, "circular"))
    assert validate_restriction_bound_record("Reservation", record) == record
    changed = deepcopy(record)
    changed["worker_request"]["enzyme_selection"] = {"kind": "explicit", "names": []}
    with pytest.raises(ContractError, match="restriction_input_conflict"):
        validate_restriction_bound_record("Reservation", changed)


def test_actual_default_registry_advertises_only_the_canonical_current_contract(tmp_path):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    with Store(tmp_path / "canonical-restriction-catalog") as store:
        store.create_problem(raw_sequence=SEQUENCE, molecule="dna")
        registry = ToolRegistry(store)
        catalog = registry.catalog()
        assert TOOL in catalog and "find_restriction_enzymes" not in catalog
        entry = catalog[TOOL]
        expected = restriction_tool_contract()
        assert {field: entry[field] for field in expected} == expected
        assert entry["configuration"]["job_limits"] == registry.local_job_policy.to_dict()
        validator = Draft202012Validator(entry["input_schema"])
        subject = store.targets()[0]["id"]
        explicit = {**canonical_arguments(), "sequence_ref": subject}
        commercial = {**canonical_arguments({"kind": "commercial_native_batch", "names": None}),
            "sequence_ref": subject}
        assert validator.is_valid(explicit) and validator.is_valid(commercial)
        assert not validator.is_valid(dict(mode="native", sequence_ref=subject, enzyme_names=["EcoRI"]))
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0


def test_actual_dispatch_denies_unreceived_sequence_before_bytes_or_job_preparation(tmp_path, monkeypatch):
    import asyncio
    from gene_annotation_episode import restriction_mapping_inputs as inputs
    from gene_annotation_episode import restriction_mapping_jobs as jobs
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    with Store(tmp_path / "unreceived-restriction-input") as store:
        store.create_problem(raw_sequence=SEQUENCE, molecule="dna")
        registry = ToolRegistry(store)
        subject = store.targets()[0]["id"]
        arguments = {**canonical_arguments({"kind": "explicit", "names": ["EcoRI"]}),
            "sequence_ref": subject}
        scope = dict(subject_refs=[subject])
        operation_key = "engineering-unreceived-restriction-action"
        record_ids = list(store.db.execute("SELECT id FROM records ORDER BY id"))
        artifact_ids = list(store.db.execute("SELECT id FROM artifacts ORDER BY id"))
        calls = []

        def forbidden(port):
            def reject(*args, **kwargs):
                calls.append(port)
                raise AssertionError("unreceived sequence reached " + port)
            return reject

        monkeypatch.setattr(registry, "_sequence", forbidden("ToolRegistry._sequence"))
        monkeypatch.setattr(store, "get_artifact", forbidden("Store.get_artifact"))
        monkeypatch.setattr(inputs, "artifact_path", forbidden("restriction_inputs.artifact_path"))
        monkeypatch.setattr(jobs.RestrictionMappingJobs, "reserve", forbidden("RestrictionMappingJobs.reserve"))
        monkeypatch.setattr(jobs.native, "prepare_job", forbidden("native_lifecycle.prepare_job"))
        outcome = asyncio.run(registry.execute_async(TOOL, arguments, scope=scope,
            operation_key=operation_key, permitted_record_refs=[]))
        assert outcome["status"] == "invalid" and outcome["result"] is None
        assert outcome["record_refs"] == [] and outcome.get("changed_record_refs", []) == []
        assert outcome["feedback"] == dict(category="arguments_or_reference", code="restriction_operand_not_received")
        assert calls == []
        assert list(store.db.execute("SELECT id FROM records ORDER BY id")) == record_ids
        assert list(store.db.execute("SELECT id FROM artifacts ORDER BY id")) == artifact_ids
        assert store.db.execute("SELECT count(*) FROM restriction_mapping_operations").fetchone()[0] == 0
        assert not (store.path / "native-restriction").exists()
        saved = store.db.execute("SELECT name,arguments,result FROM tool_operations WHERE operation_key=?",
            (operation_key,)).fetchone()
        assert saved["name"] == TOOL and saved["arguments"] == restriction_canonical(arguments)
        assert saved["result"] == restriction_canonical(outcome)
