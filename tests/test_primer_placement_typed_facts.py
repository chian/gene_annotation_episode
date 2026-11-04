"""Typed and receipt boundaries over the retained234 placement values.

Pure DTO Source strings establish no custody. The real Store metadata cases
below use explicitly engineered publication candidates, not native producers,
scientific action outcomes, model deliveries or execution evidence.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_result_contracts as shared
from gene_annotation_episode import primer_placement_measurements as science
from gene_annotation_episode import primer_placement_result_contracts as contracts
from gene_annotation_episode import scientific_process_prompt as presentation
from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, plain, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
from gene_annotation_episode.molecular_result_facts import (
    merge_molecular_facts, molecular_fact_sources, requested_molecular_fact_fields,
    requested_molecular_fact_sources, validate_frozen_molecular_return, validate_molecular_fact,
)
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from test_molecular_sequence_input_bindings import actual_received_input_owner
from test_primer_placement_ordinary import SOURCE, _inspection, _inspection_rows, _retained, _rows


FACT = contracts.FACT_SOURCE


def _forbidden(*args, **kwargs):
    raise AssertionError("typed placement boundary attempted scientific work or private bytes")


@pytest.fixture(autouse=True)
def no_scientific_work(monkeypatch):
    for name in ("build_primer_placement_sheet", "calculate_primer_placement_components", "_populate",
            "count_literal_alignment_columns"):
        monkeypatch.setattr(science, name, _forbidden)
    monkeypatch.setattr(native, "execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)


def _schema():
    return dict(type="object", additionalProperties=False, properties={
        "placements": contracts.ordinary_primer_placement_fact_sources()[FACT]["report_schema"]},
        required=["placements"])


def _view(rows=None):
    _values, _custody, packet = _retained(rows)
    return contracts.validate_ordinary_primer_placement_return(dict(source_ref=SOURCE, **packet))


def _file(raw):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format="ascii_sequence")


def test_exact_registered_whole_field_inserts_retained_cells_and_only_resolves_top_source():
    schema, value = _schema(), _view()
    assert validate_closed_schema(schema) == schema
    assert molecular_fact_sources()[FACT] == contracts.ordinary_primer_placement_fact_sources()[FACT]
    assert requested_molecular_fact_sources(schema) == (FACT,)
    assert requested_molecular_fact_fields(schema, fact_source=FACT) == ["placements"]
    form = form_with_facts({}, schema, {FACT: [value]})
    seen = []
    assert validate_form(form, schema,
        lambda reference, namespace: seen.append((reference, namespace)) or reference == SOURCE) == form
    assert seen == [(SOURCE, "source")]
    assert [row["value"] for row in value["values"]["rows"]] == [4, 2, 4, 9, 18, [1, 5], .25, 3, 3, 4]
    assert value["values"]["original_attempt_association"] == "unavailable"
    assert value["context"]["input"]["primers"] == "AAAA"


@pytest.mark.parametrize("change", [
    lambda node: node.update(minItems=1),
    lambda node: node["items"]["properties"]["source_ref"].update(**{"x-reference-namespace": "artifact"}),
    lambda node: node["$defs"].update(unselected={"type": "string"}),
])
def test_registered_schema_requires_the_exact_complete_local_definitions(change):
    schema = _schema()
    change(schema["properties"]["placements"])
    with pytest.raises(ReportBoundaryError) as caught:
        validate_closed_schema(schema)
    assert caught.value.diagnostic["code"] == "invalid_schema"


def test_registered_fact_cannot_be_nested_below_another_field():
    schema = _schema()
    schema["properties"]["placements"] = dict(type="object", additionalProperties=False,
        properties={"nested": schema["properties"]["placements"]}, required=["nested"])
    with pytest.raises(ReportBoundaryError, match="whole top-level fields"):
        validate_closed_schema(schema)


@pytest.mark.parametrize("change", [
    lambda value: value["context"]["population"].update(mismatch_count_sum=True),
    lambda value: value["context"]["population"].update(mismatch_count_denominator_hits=4.0),
    lambda value: value["values"]["rows"][0].update(value=True),
    lambda value: value["values"]["rows"][0].update(unit="confidence"),
    lambda value: value["selection"]["rows"][0]["fields"].reverse(),
    lambda value: value["context"].update(source_assumptions="PCR success"),
    lambda value: value["context"].update(native_handle={}),
])
def test_strict_dto_rejects_type_meaning_selection_and_control_tampering_before_resolving(change):
    value, seen = _view(), []
    change(value)
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"placements": [value]}, _schema(), lambda *args: seen.append(args) or True)
    assert caught.value.diagnostic["field"] == "placements" and seen == []
    with pytest.raises(ContractError, match="primer_placement_return_invalid"):
        validate_molecular_fact(value, fact_source=FACT)


@pytest.mark.parametrize("wrong", [None, {}, "not an array"])
def test_complete_source_groups_require_an_array(wrong):
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form({"placements": wrong}, _schema(), lambda *args: True)
    assert caught.value.diagnostic["code"] == "primer_placement_return_array_required"


def test_schema_cache_never_supplies_a_source_receipt():
    schema, form = _schema(), {"placements": [_view()]}
    validate_form(form, schema, lambda reference, namespace: reference == SOURCE and namespace == "source")
    seen = []
    with pytest.raises(ReportBoundaryError) as caught:
        validate_form(form, schema, lambda reference, namespace: seen.append((reference, namespace)) or False)
    assert caught.value.diagnostic["code"] == "unknown_reference" and seen == [(SOURCE, "source")]


def test_empty_selection_preserves_full_operand_files_mappings_populations_and_qualifications():
    value = _view([])
    context = value["context"]
    nested_source, nested_artifact = "source_" + "c" * 24, "artifact_" + "d" * 64
    literal = {"subject_ref": nested_source, "artifact_ref": nested_artifact, "thought_pattern": "native label",
        "library": {"entries": [], "workspace": "supplied opaque value"}, "invalid_mapping": True}
    context["input"]["target_ref"] = nested_source
    context["input"]["primer_refs"] = [nested_artifact]
    context["input"]["target_mapping"] = deepcopy(literal)
    context["input"]["primer_mappings"] = [deepcopy(literal)]
    context["original_operand_files"] = dict(target=_file(context["input"]["target_sequence"].encode("ascii")),
        primers=_file(context["input"]["primers"].encode("ascii")))
    original, seen = deepcopy(value), []
    validate_form({"placements": [value]}, _schema(),
        lambda reference, namespace: seen.append((reference, namespace)) or reference == SOURCE)
    assert value == original and seen == [(SOURCE, "source")]
    assert value["values"]["rows"] == [] and value["selection"]["rows"] == []
    assert context["population"]["mismatch_count_denominator_hits"] == 4
    assert len(context["issues"]) == 10 and context["definitions"]
    # This actual pure projection hook claims no runtime delivery or grant.
    projected = ScientificProcessEpisodes.received_form_references(
        object(), None, {"placements": [value]}, _schema(), "pure-projection")
    assert projected == [SOURCE]


def test_dedup_uses_source_and_exact_ordered_selection_and_returns_detached_full_groups():
    first, second = _view(), _view(list(reversed(_rows())))
    original = deepcopy((first, second))
    actual = merge_molecular_facts([first], [deepcopy(first), second], fact_source=FACT)
    assert actual == [first, second] and (first, second) == original
    assert first["source_ref"] == second["source_ref"] and first["selection"] != second["selection"]
    actual[0]["context"]["input"]["target_mapping"] = {"changed": True}
    assert (first, second) == original


def test_conflicting_context_for_the_same_source_and_selection_is_not_silently_deduplicated():
    first = _view([])
    changed = deepcopy(first)
    changed["context"]["input"]["target_mapping"] = {"supplied_unknown_mapping": True}
    assert validate_molecular_fact(changed, fact_source=FACT) == changed
    with pytest.raises(ContractError, match="primer_placement_facts_source_conflict"):
        merge_molecular_facts([first], [changed], fact_source=FACT)


@pytest.mark.parametrize("change", ["literal", "missing", "mapping", "population_type"])
def test_frozen_comparison_keeps_exact_cells_context_types_and_absence(change):
    value, schema = _view(), _schema()
    frozen, form = [deepcopy(value)], {"placements": [deepcopy(value)]}
    if change == "missing": form = {}
    elif change == "mapping": form["placements"][0]["context"]["input"]["target_mapping"] = {"changed": True}
    elif change == "population_type": form["placements"][0]["context"]["population"]["mismatch_count_sum"] = 2.0
    if change == "literal":
        validate_frozen_molecular_return(form, schema, frozen, fact_source=FACT)
    else:
        with pytest.raises(ReportBoundaryError) as caught:
            validate_frozen_molecular_return(form, schema, frozen, fact_source=FACT)
        assert caught.value.diagnostic["field"] == "placements"
    assert frozen == [value]


@pytest.mark.parametrize("available", [True, False])
def test_scientific_report_hook_uses_the_same_frozen_group_and_finite_missing_code(available):
    value, schema = _view([]), _schema()
    frozen = [deepcopy(value)] if available else None
    owner = SimpleNamespace(services=SimpleNamespace(molecular_frozen_facts=lambda context, *, fact_source: frozen))
    if available:
        ScientificProcessEpisodes._validate_molecular_report(owner, None, {"placements": [value]}, schema)
        assert frozen == [value]
    else:
        with pytest.raises(ReportBoundaryError) as caught:
            ScientificProcessEpisodes._validate_molecular_report(owner, None, {"placements": [value]}, schema)
        assert caught.value.diagnostic["code"] == "primer_placement_facts_not_frozen"
        assert caught.value.diagnostic["field"] == "placements"


@pytest.mark.parametrize("empty", [False, True])
def test_current_presentation_preserves_retained_full_context_and_private_addresses_stay_roles(monkeypatch, empty):
    value = _view([] if empty else None)
    original = deepcopy(value)
    monkeypatch.setattr("gene_annotation_episode.state.Store.get_artifact", _forbidden)
    monkeypatch.setattr(Path, "open", _forbidden)
    assert presentation._information(value) == original
    shown, packets = presentation._selected_molecular_view(dict(result=value, again=deepcopy(value)))
    assert shown == dict(result="Selected molecular result 1", again="Selected molecular result 1")
    assert packets == [original]
    text = presentation._selected_molecular_text(packets[0], 1)
    assert value == original and packets == [original]
    assert "Retained primer-placement operands and populations" in text
    assert "primer input form" in text and "scalar" in text and '"AAAA"' in text
    assert "population.mismatch_count_denominator_hits" in text and "| 4 |" in text
    assert "group_populations[0]" in text and "source_assumptions" in text
    assert "definitions." in text and "issues[0]" in text
    assert "Original attempt association" in text and "unavailable" in text
    for role in ("sheet", "components"):
        assert value["values"]["source_" + role + "_ref"] not in text
    if empty:
        assert '"rows":[]' in text and "mismatch_fraction.value" not in text
    else:
        assert "mismatch_fraction.value" in text and "0.25" in text


def test_long_sequence_display_summarizes_only_text_and_preserves_unknown_context_and_file_identity(monkeypatch):
    """Engineered unavailable-output context, not a new native observation."""
    sequence = "aCgT" * 40
    source_files = {role: shared.empty_file_state("producer_unavailable") for role in shared.FILE_ROLES}
    literal = {"slot": "thought_pattern", "evidence": {"unknown_mapping": True}, "entries": [], "library": "supplied"}
    inputs = dict(target_sequence=sequence, primers=["AAAA", "AAAA"], target_ref="literal-target",
        primer_refs=["literal-primer", "literal-primer"], target_mapping=deepcopy(literal), primer_mappings=[None, None])
    files = dict(target=_file(sequence.encode("ascii")), primers=[_file(b"AAAA"), _file(b"AAAA")])
    context = contracts.context(sheet=None, components=None, source_files=source_files,
        original_files=files, frozen_input=inputs)
    projection = shared.select_stored_molecular_sequence_values(operation=contracts.TOOL, sheet=None, components=None,
        selection=contracts.selector(dict(rows=[])), source_files=source_files)
    packet = contracts.packet(dict(intent=dict(arguments=dict(rows=[])), projection=projection,
        source_files=source_files, failures=projection["public"]["failures"], context=context))
    value = contracts.validate_return(dict(source_ref=SOURCE, **packet))
    original = deepcopy(value)
    monkeypatch.setattr("gene_annotation_episode.state.Store.get_artifact", _forbidden)
    monkeypatch.setattr(Path, "open", _forbidden)
    assert presentation._information(value) == original
    text = presentation._selected_molecular_text(value, 1)
    assert value == original and value["context"]["input"]["target_sequence"] == sequence
    assert "160 symbols retained in the result context" in text and sequence not in text
    assert "ordered list" in text and "primers[0]" in text and "primers[1]" in text
    assert "thought_pattern" in text and "unknown_mapping" in text and '"library":"supplied"' in text
    assert value["context"]["original_operand_files"] == files
    assert "size_bytes" not in text
    for file in [files["target"], *files["primers"]]:
        assert file["artifact_ref"] not in text and file["sha256"] not in text
    assert value["context"]["population"] is None and value["context"]["native_outcome"] is None


@contextmanager
def _metadata_publication(tmp_path, *, status="completed", deliver=True, explicit_files=()):
    """Actual metadata/receipts with no producing action or scientific custody."""
    with actual_received_input_owner(tmp_path, deliver=False) as value:
        store = value.store
        store.db.execute("CREATE TABLE tool_operations(operation_key TEXT PRIMARY KEY,id TEXT,name TEXT,arguments TEXT,scope TEXT,result TEXT)")
        _values, _custody, packet = _retained([])
        primary = store.artifact(canonical(packet), "application/json")
        private = {role: store.artifact(("engineering private " + role).encode(), "application/octet-stream")
            for role in ("capture", "sheet", "components", "control", "diagnostic")}
        original_file = store.artifact(b"separately admitted original operand", "application/octet-stream")
        original = store.put("source", dict(provider="engineering_original_operand", accession=None, uri=None,
            artifact_ref=original_file, text_ref=None, request_ref=None, version=None, retrieved_at=None), origin="tool")
        source = store.put("source", dict(provider=contracts.TOOL, accession=None, uri=None, artifact_ref=primary,
            text_ref=None, request_ref=private["control"], auxiliary_artifact_refs=[private[role]
                for role in ("capture", "sheet", "components")], parent_source_refs=[original["id"]],
            version=contracts.SOURCE_VERSION, retrieved_at=None), origin="tool")
        public = contracts.validate_return(dict(source_ref=source["id"], **packet))
        arguments = dict(mode="read_stored", result_ref=source["id"], rows=[])
        key = "engineering-placement-metadata-candidate"
        operation = identity("operation", dict(key=key, name=contracts.TOOL, arguments=arguments))
        outcome = dict(status=status, operation_ref=operation, record_refs=[source["id"]], result=public, feedback=None)
        store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)",
            (key, operation, contracts.TOOL, canonical(arguments), canonical(value.scope), canonical(outcome)))
        failed = dict(status="failed", record_refs=[], result=None, feedback=dict(diagnostic_ref=private["diagnostic"]))
        store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)",
            (key + ":failed", "engineering-failure", contracts.TOOL, "{}", canonical(value.scope), canonical(failed)))
        value.refs = dict(source=source["id"], packet=primary, original_source=original["id"], original_file=original_file, **private)
        value.public, value.source = public, source
        if deliver: value.receipts.receive(value.parent.episode_id, [source["id"]], kind="initial")
        if explicit_files:
            value.receipts.receive(value.parent.episode_id, [value.refs[role] for role in explicit_files], kind="initial")
        value.context = value.child(1)
        yield value


def _verdict(value, role, *, context=None, providers=None):
    return molecular_reference_restriction(value.store, value.context if context is None else context,
        value.refs[role], "source" if role.endswith("source") else "artifact", providers=providers)


@pytest.mark.parametrize("status", ["completed", "partial"])
def test_source_receipt_forwards_no_private_packet_controls_or_nested_operand_refs(tmp_path, status):
    with _metadata_publication(tmp_path, status=status) as value:
        assert value.source["version"] == "ordinary_primer_placement_result_v1"
        assert value.public["version"] == "ordinary_primer_placement_values_v1"
        assert value.receipts.forward_references(value.source) == []
        assert set(value.receipts.known(value.context.episode_id)) == {value.refs["source"]}
        assert _verdict(value, "source") is True and _verdict(value, "packet") is False
        for role in ("capture", "sheet", "components", "control", "diagnostic"):
            assert _verdict(value, role) is False
        assert _verdict(value, "original_source") is None and _verdict(value, "original_file") is None


def test_explicit_private_receipts_still_deny_controls_and_original_file_is_not_recategorized(tmp_path):
    roles = ("packet", "capture", "sheet", "components", "control", "diagnostic", "original_file")
    with _metadata_publication(tmp_path, explicit_files=roles) as value:
        assert all(value.refs[role] in set(value.receipts.known(value.context.episode_id)) for role in roles)
        assert _verdict(value, "packet") is True
        for role in ("capture", "sheet", "components", "control", "diagnostic"):
            assert _verdict(value, role) is False
        assert _verdict(value, "original_file") is None
        assert molecular_reference_restriction(value.store, value.context, value.refs["source"], "artifact") is False
        assert molecular_reference_restriction(value.store, value.context, value.refs["packet"], "source") is False


def test_unreceived_source_and_late_receipt_do_not_backfill_an_older_inherited_prefix(tmp_path):
    with _metadata_publication(tmp_path, deliver=False) as value:
        earlier = value.context
        assert _verdict(value, "source") is False and _verdict(value, "packet") is False
        value.receipts.receive(value.parent.episode_id, [value.refs["source"]], kind="initial")
        later = value.child(2)
        assert _verdict(value, "source", context=earlier) is False
        assert _verdict(value, "source", context=later) is True and _verdict(value, "packet", context=later) is False


@pytest.mark.parametrize("change", ["scope", "request", "run"])
def test_source_access_requires_the_actual_authenticated_receiving_context(tmp_path, change):
    with _metadata_publication(tmp_path) as value:
        context = value.context
        if change == "scope": context = replace(context, scope={"subject_refs": []})
        elif change == "request":
            request = plain(context.request)
            request["message"]["episode_assignment"] = {"changed": True}
            context = replace(context, request=request, assignment=request["message"]["episode_assignment"])
        else: context = replace(context, run_id="unreceived-run")
        assert _verdict(value, "source", context=context) is False


def test_privacy_classification_is_metadata_only_and_preserves_all_rows_and_receipts(tmp_path, monkeypatch):
    with _metadata_publication(tmp_path) as value:
        def rows():
            names = [row[0] for row in value.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name: sorted([tuple(row) for row in value.store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')], key=repr)
                for name in names}
        before, changes = rows(), value.store.db.total_changes
        known = set(value.receipts.known(value.context.episode_id))
        for name in ("get_artifact", "artifact", "_refs"):
            monkeypatch.setattr(value.store, name, _forbidden)
        monkeypatch.setattr(Path, "open", _forbidden)
        assert value.receipts.forward_references(value.source) == []
        for role in ("source", "packet", "capture", "sheet", "components", "control", "diagnostic"):
            _verdict(value, role)
        assert _verdict(value, "control", providers=("predict_protein_disorder_regions",)) is None
        assert rows() == before and value.store.db.total_changes == changes
        assert set(value.receipts.known(value.context.episode_id)) == known


def _native_view():
    _components, packet = _inspection()
    return contracts.validate_return(dict(source_ref=SOURCE, **packet))


def test_complete_native_literal_schema_uses_local_definitions_and_only_top_source_semantics():
    value = _native_view()
    schema = _schema()
    document = schema["properties"]["placements"]
    assert "PrimerLiteral" in document["$defs"] and "PrimerPlacementNativeJSON" in document["$defs"]
    assert len([key for key in document["$defs"] if key.startswith("PrimerPlacementNativeJSON")]) == 33
    for kind in ("Arguments", "Context", "Packet", "Return"):
        Draft202012Validator.check_schema(contracts.schema(kind))
    seen = []
    validate_form({"placements": [value]}, schema,
        lambda reference, namespace: seen.append((reference, namespace)) or reference == SOURCE)
    assert seen == [(SOURCE, "source")]


def test_callable_looking_native_keys_are_literal_data_without_nested_grants_or_stripping():
    components, _packet = _inspection()
    changed = deepcopy(components)
    nested_source, nested_file = "source_" + "d" * 24, "artifact_" + "e" * 64
    literal = {"source_ref": nested_source, "artifact_ref": nested_file, "library": {"entries": []},
        "slot": "thought_pattern", "evidence": [{"requested": False}], "unknown": None}
    changed["groups"][0]["native_group"] = deepcopy(literal)
    intervals = [dict(subject_ref=nested_source, start=0, end=2, unit="nt", strand="+"),
        dict(subject_ref=nested_file, start=4, end=6, unit="symbol", strand="-")]
    hit = changed["groups"][0]["hits"][1]
    hit["target_mapping"] = dict(state="available", intervals=deepcopy(intervals))
    hit["mismatches"][0]["target_source_intervals"] = [dict(subject_ref=nested_file, start=4, end=5,
        unit="symbol", strand="-")]
    _components, packet = _inspection(changed)
    value = contracts.validate_return(dict(source_ref=SOURCE, **packet))
    assert value["values"]["rows"][10]["value_state"] == "stored_value"
    assert value["values"]["rows"][7]["scientific_qualifiers"]["states"]["target_mapping_state"]["value"] == "available"
    original, seen = deepcopy(value), []
    validate_form({"placements": [value]}, _schema(),
        lambda reference, namespace: seen.append((reference, namespace)) or reference == SOURCE)
    assert value == original and seen == [(SOURCE, "source")]
    assert presentation._information(value) == original
    projected = ScientificProcessEpisodes.received_form_references(object(), None,
        {"placements": [value]}, _schema(), "pure-native-projection")
    assert projected == [SOURCE] and nested_source not in projected and nested_file not in projected


@pytest.mark.parametrize("containers", [0, 1, 31, 32, 33])
@pytest.mark.parametrize("kind", ["array", "object"])
def test_native_json_depth_bound_matches_the_schema_and_runtime_type(containers, kind):
    literal = False
    for _ in range(containers):
        literal = [literal] if kind == "array" else {"unchanged": literal}
    document = contracts.schema("Return")
    literal_schema = {"$defs": document["$defs"], "$ref": "#/$defs/PrimerPlacementNativeJSON"}
    valid = containers <= shared.PLACEMENT_MAX_NESTING
    assert shared.PLACEMENT_MAX_NESTING == 32
    assert shared.valid_type(literal, "placement_native_json") is valid
    assert Draft202012Validator(literal_schema).is_valid(literal) is valid
    value = _native_view();value["values"]["rows"][0]["value"] = literal
    if valid:
        assert contracts.validate_return(value) == value
        validate_form({"placements": [value]}, _schema(), lambda reference, namespace: reference == SOURCE)
    else:
        with pytest.raises(ValueError): contracts.validate_return(value)


@pytest.mark.parametrize("literal", [("tuple",), b"bytes", {1: "non-string key"}, {"set"}, float("nan"), float("inf")])
def test_non_json_or_nonfinite_native_literals_are_rejected_before_canonical_copy_coercion(literal):
    assert shared.valid_type(literal, "placement_native_json") is False
    value = _native_view();value["values"]["rows"][0]["value"] = literal
    with pytest.raises(ValueError): contracts.validate_return(value)
    with pytest.raises(ValueError):
        shared.validate_molecular_sequence_fact_values(shared.PROJECTION_SOURCE, [value["values"]])


@pytest.mark.parametrize("change", [
    lambda value: value["values"]["rows"][0].update(unit="probability"),
    lambda value: value["values"]["rows"][0].update(population_id="placement_native_hit_occurrence"),
    lambda value: value["values"]["rows"][0].update(source_pointer="/groups/1/native_group"),
    lambda value: value["values"]["rows"][0].update(value=None, value_state="stored_value"),
    lambda value: value["values"]["rows"][0].update(value={}, value_state="stored_null"),
    lambda value: value["selection"]["rows"][0]["fields"].reverse(),
    lambda value: value["values"]["rows"][7].update(value=dict(state="available", intervals=None)),
])
def test_native_field_declarations_selection_and_checked_state_tampering_deny_before_source_resolution(change):
    value, seen = _native_view(), []
    change(value)
    if value["values"]["rows"][0]["value"] is None or value["values"]["rows"][0]["value_state"] == "stored_null":
        assert Draft202012Validator(contracts.schema("Return")).is_valid(value) is False
    with pytest.raises(ReportBoundaryError):
        validate_form({"placements": [value]}, _schema(), lambda *args: seen.append(args) or True)
    assert seen == []


def test_shared_local_definition_collisions_are_rejected_instead_of_overwriting_literal_meanings(monkeypatch):
    original = shared.molecular_sequence_fact_sources
    def conflicting(*, profile=shared._LEGACY_PROFILE):
        definitions = original(profile=profile)
        if profile == shared._PLACEMENT_PROFILE:
            definitions[shared.PROJECTION_SOURCE]["report_schema"]["$defs"]["PrimerLiteral"] = {"type": "null"}
        return definitions
    monkeypatch.setattr(shared, "molecular_sequence_fact_sources", conflicting)
    with pytest.raises(ValueError, match="local_definition_collision"):
        contracts.schema("Return")


@pytest.mark.parametrize("ordinal,changed", [(0, True), (0, 1.0), (1, True), (1, 4.0)])
def test_full_primer_fraction_operands_are_strict_counts_not_boolean_or_float_aliases(ordinal, changed):
    value, seen = _view(), []
    value["values"]["rows"][6]["denominators"][ordinal]["value"] = changed
    with pytest.raises(ReportBoundaryError):
        validate_form({"placements": [value]}, _schema(), lambda *args: seen.append(args) or True)
    assert seen == []
    with pytest.raises(ValueError): contracts.validate_return(value)


@pytest.mark.parametrize("change", [
    lambda cell: cell.update(kind="calibration_response"),
    lambda cell: cell.update(unit="probability"),
    lambda cell: cell.update(source_ref="artifact_" + "f" * 64),
    lambda cell: cell.update(source_state="retained"),
    lambda cell: cell.update(unit_sources=[dict(value_state="stored_value", value="symbols", source_ref=cell["source_ref"],
        source_pointer="/unit", source_state=cell["source_state"])]),
])
def test_fraction_operand_original_kind_unit_source_and_state_joins_are_not_reassociated(change):
    value, seen = _view(), []
    change(value["values"]["rows"][6]["denominators"][1])
    with pytest.raises(ReportBoundaryError):
        validate_form({"placements": [value]}, _schema(), lambda *args: seen.append(args) or True)
    assert seen == []


def _association_view(field):
    identity = dict(kind="placement_hit", group_ordinal=0, native_hit_ordinal=1)
    if field.endswith("_source_intervals"):
        identity.update(kind="placement_mismatch", native_mismatch_ordinal=0)
    _components, packet = _inspection(rows=[dict(row_id=identity, fields=[field])])
    return contracts.validate_return(dict(source_ref=SOURCE, **packet))


def _assert_association_denied(value, *, schema_rejects=True):
    assert Draft202012Validator(contracts.schema("Return")).is_valid(value) is not schema_rejects
    with pytest.raises(ValueError):
        shared.validate_molecular_sequence_fact_values(shared.PROJECTION_SOURCE, [value["values"]])
    seen = []
    with pytest.raises(ReportBoundaryError):
        validate_form({"placements": [value]}, _schema(), lambda *args: seen.append(args) or True)
    assert seen == []


@pytest.mark.parametrize("side", ["target", "primer"])
@pytest.mark.parametrize("state", ["available", "unavailable", "incompatible"])
def test_selected_checked_mapping_state_must_equal_its_copied_qualifier_before_resolution(side, state):
    value = _association_view(side + "_mapping")
    row = value["values"]["rows"][0]
    if state == "unavailable":
        row["scientific_qualifiers"]["states"][side + "_mapping_state"]["value"] = "available"
    else:
        row["value"] = dict(state=state, intervals=[] if state == "available" else None)
    _assert_association_denied(value)


@pytest.mark.parametrize("side", ["target", "primer"])
@pytest.mark.parametrize("value_state", ["stored_null", "path_missing"])
def test_present_checked_mapping_requires_a_present_copied_state_not_null_or_missing(side, value_state):
    value = _association_view(side + "_mapping")
    value["values"]["rows"][0]["scientific_qualifiers"]["states"][side + "_mapping_state"].update(
        value_state=value_state, value=None)
    _assert_association_denied(value)


@pytest.mark.parametrize("side", ["target", "primer"])
@pytest.mark.parametrize("state", ["unavailable", "incompatible", "missing"])
def test_present_mismatch_source_path_requires_the_same_side_available_mapping_qualifier(side, state):
    value = _association_view(side + "_source_intervals")
    row = value["values"]["rows"][0]
    row.update(value_state="stored_value", value=[dict(subject_ref="literal-original-source", start=3, end=4,
        unit="nt", strand="+")])
    qualifier = row["scientific_qualifiers"]["states"][side + "_mapping_state"]
    if state == "missing":
        qualifier.update(value_state="path_missing", value=None)
    else:
        qualifier["value"] = state
    _assert_association_denied(value)


@pytest.mark.parametrize("side", ["target", "primer"])
@pytest.mark.parametrize("change", ["value", "missing"])
def test_same_component_source_and_mapping_pointer_cannot_carry_conflicting_qualifier_copies(side, change):
    value = _native_view()
    # native_hit remains opaque; only its explicitly declared host qualifier
    # disagrees with the same qualifier copied into the other selected rows.
    qualifier = value["values"]["rows"][4]["scientific_qualifiers"]["states"][side + "_mapping_state"]
    if change == "value":
        qualifier["value"] = "available"
    else:
        qualifier.update(value_state="path_missing", value=None)
    _assert_association_denied(value, schema_rejects=False)


@pytest.mark.parametrize("state", ["available_path", "available_empty", "unavailable", "incompatible"])
def test_projector_keeps_checked_mapping_and_mismatch_qualifications_consistent_without_recalculation(state):
    """Edited supplied Components test associations, not a native mapping claim."""
    components, _packet = _inspection()
    changed = deepcopy(components)
    hit = changed["groups"][0]["hits"][1]
    available = state.startswith("available")
    path = ([] if state == "available_empty" else
        [dict(subject_ref="literal-original-source", start=10, end=14, unit="nt", strand="+")]) if available else None
    mismatch = ([] if state == "available_empty" else
        [dict(subject_ref="literal-original-source", start=13, end=14, unit="nt", strand="+")]) if available else None
    for side in ("target", "primer"):
        hit[side + "_mapping"] = dict(state="available" if available else state, intervals=deepcopy(path))
        hit["mismatches"][0][side + "_source_intervals"] = deepcopy(mismatch)
    _components, packet = _inspection(changed)
    value = contracts.validate_return(dict(source_ref=SOURCE, **packet))
    original, seen = deepcopy(value), []
    validate_form({"placements": [value]}, _schema(),
        lambda reference, namespace: seen.append((reference, namespace)) or reference == SOURCE)
    assert value == original and seen == [(SOURCE, "source")]
    for ordinal, side in ((7, "target"), (8, "primer")):
        row = value["values"]["rows"][ordinal]
        assert row["value"]["state"] == row["scientific_qualifiers"]["states"][side + "_mapping_state"]["value"]
    for row in value["values"]["rows"][10:12]:
        assert row["value_state"] == ("stored_value" if available else "stored_null")
        assert row["value"] == mismatch
