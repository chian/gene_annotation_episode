"""Finite fact groups over real Store/commission/receipt metadata.

Liftover publications and decisions are explicitly engineered saved records;
these cases perform no native conversion, configured Workflow or model call.
Existing retained ITC tests separately cover its original scientific histories.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode import liftover_contracts as core
from gene_annotation_episode import molecular_result_facts as facts
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from test_molecular_publication_custody import (
    all_rows, forbidden, guard_work, publication_case, save_operation, scientific_value,
)


LIFE = "liftover_point_mappings"
ITC = "itc_binding_parameters"
CD = "circular_dichroism_summaries"
ORF = "orf_measurements"
EDIT = "reference_edit_outcomes"
SOURCE = "source_" + "7" * 24


def life_value():
    """A pure DTO fixture, not an authenticated native observation."""
    request = dict(version=core.REQUEST_VERSION,
        chain=dict(file=dict(artifact_ref="artifact_" + "1" * 64, sha256="1" * 64,
            size_bytes=0, format="ucsc_chain"), source_ref=None),
        point=dict(chromosome="literal contig", position_0based=0, strand="-"))
    return core.project_liftover_return(scientific_value(request, "mapping")["components"], source_ref=SOURCE)


def itc_value():
    """An unavailable-cell DTO; no fit or new parameter evidence is implied."""
    return dict(version="itc_parameter_return_v1", source_ref=SOURCE, parameter_source="selected_parameters",
        **{name: dict(state="unavailable", value=None, unit=unit, reason="missing_value")
            for name, unit in dict(kd="mol_per_litre", n="sites_per_macromolecule", delta_h="joule_per_mole").items()},
        cell_scope="retained_components_parameter_vector", fit_call_state=None, fit_call_count=None,
        fit_diagnostics_scope=None, weighting=None, independent_error_assumption=None, absolute_sigma=None,
        fit_qualification_codes=None, prediction_qualification_codes=None, calibration_authority="supplied_assertion",
        n_meaning="effective_sites_per_declared_macromolecule", identifiability="not_assessed",
        statistical_covariance_validity="not_assessed", warning_locations=[], failure_location=None)


def form_schema():
    return obj(dict(mappings=core.liftover_fact_sources()[LIFE]["report_schema"]))


def recorded_scientific(case, *, index=2, schema=None):
    """Record an actual scientific-role commission, not a relabelled results context."""
    value, parent = case.value, case.value.parent
    schema = obj({}) if schema is None else schema
    contract = AppServiceCustody._report_contract("Return the selected saved mapping facts.", schema)
    path = (*parent.path, ("scientific_process", "child_" + str(index)))
    episode_id = EpisodeRef(parent.run_id, path).episode_id
    selected = dict(kind="episode_child", role="scientific_process", scope=plain(parent.scope), assignment={},
        purpose=contract["decision"], schema_json=canonical(schema), goal="Inspect retained point mappings", initial_report_json="{}")
    value.store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)",
        (parent.run_id, parent.episode_id, index, canonical(selected)))
    manifest = value.receipts.bind(episode_id, parent.episode_id)
    request = dict(goal={"engineering_fixture": True}, message=dict(scope=plain(parent.scope),
        episode_assignment={}, initial_report={}, knowledge_inheritance=manifest), report_contract=contract)
    context = BindingContext(parent.run_id, episode_id, "scientific_process", path, plain(parent.scope), {}, request)
    value.store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)",
        (parent.run_id, episode_id, canonical(path), canonical(request)))
    return context


def saved_action(case, context, *, mode="read_stored", index=0, result_ref=None):
    arguments = dict(mode=mode, result_ref=result_ref or case.source["id"], mapping_ordinals=[])
    view = SimpleNamespace(**{**vars(case), "producer": context})
    key = save_operation(view, index=index, arguments=arguments, source_ref=case.source["id"])
    # Its selected empty view is deliberately distinct from the full Source.
    selected = core.calculate_liftover_components(case.stored["sheet"], mapping_ordinals=[])
    projection = core.project_liftover_return(selected, source_ref=case.source["id"])
    store = case.value.store
    row = store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
    outcome = json.loads(row[0]); outcome["result"] = projection
    store.db.execute("UPDATE tool_operations SET result=? WHERE operation_key=?", (canonical(outcome), key))
    recorded = {**outcome, "pending_work_after_action": dict(version="pending_work_v1", items=[],
        captured_at="2026-10-30T00:00:00+00:00")}
    store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
        (canonical(recorded), context.run_id, context.episode_id, index))
    return key, projection


def return_tables(store):
    store.db.execute("CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT,PRIMARY KEY(run_id,episode_id))")
    store.db.execute("CREATE TABLE runtime_report_attempts(run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,"
        "delivery_ref TEXT,child_episode_id TEXT,contract TEXT,form TEXT,failure TEXT,"
        "PRIMARY KEY(run_id,parent_episode_id,decision_index))")


def saved_return(case):
    """Actual frozen form/attempt rows and receipts, with no Workflow execution."""
    store, parent = case.value.store, case.value.parent
    return_tables(store)
    child = recorded_scientific(case, schema=form_schema())
    group = [core.project_liftover_return(case.stored["components"], source_ref=case.source["id"])]
    store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?)", (child.run_id, child.episode_id, canonical({LIFE: group})))
    store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,NULL)",
        (parent.run_id, parent.episode_id, 2, "controlled-mapping-delivery", child.episode_id,
            canonical(plain(child.request)["report_contract"]), canonical(dict(mappings=group))))
    case.value.receipts.receive(parent.episode_id, [case.source["id"]], kind="child_form", source_index=2)
    onward = recorded_scientific(case, index=3)
    return child, onward, group


def forbid_frozen_work(case, monkeypatch):
    from gene_annotation_episode import molecular_measurement_tools as ordinary
    monkeypatch.setattr(case.value.store, "get_artifact", forbidden)
    monkeypatch.setattr(ordinary, "read_retained_molecular_publication", forbidden)
    monkeypatch.setattr(ordinary, "project_itc_parameter_return", forbidden)
    for name in ("populate_liftover_sheet", "calculate_liftover_components", "project_liftover_return",
            "validate_liftover_sheet", "validate_liftover_components", "validate_liftover_return"):
        monkeypatch.setattr(core, name, forbidden)


@pytest.mark.parametrize("mutation", ["output_file", "source", "chain_source", "point_float", "point_bool",
    "population_float", "score_float", "score_bool", "ordinal_float", "native_count_bool", "call_count_float",
    "nonfinite", "meaning", "failure_occurrence"])
def test_liftover_dto_has_exact_closed_types_without_reconstructing_science(monkeypatch, mutation):
    value = life_value()
    if mutation == "output_file": value["grading_artifact_ref"] = "artifact_" + "0" * 64
    elif mutation == "source": value["source_ref"] = "source_not_a_real_identity"
    elif mutation == "chain_source": value["chain"]["source_ref"] = "source_invalid"
    elif mutation == "point_float": value["point"]["position_0based"] = 0.0
    elif mutation == "point_bool": value["point"]["position_0based"] = False
    elif mutation == "population_float": value["population"]["requested_point_count"] = 1.0
    elif mutation == "score_float": value["rows"][0]["native_chain_score"] = 91.0
    elif mutation == "score_bool": value["rows"][0]["native_chain_score"] = True
    elif mutation == "ordinal_float": value["selected_mapping_ordinals"] = [0.0]
    elif mutation == "native_count_bool": value["population"]["native_row_count"] = True
    elif mutation == "call_count_float": value["population"]["conversion_call_count"] = 1.0
    elif mutation == "nonfinite": value["rows"][0]["native_chain_score"] = float("nan")
    elif mutation == "meaning": value["population"]["mapping_count_scope"] = "selected_rows"
    else: value["failure"] = dict(stage="execution", code="execution_unconfirmed", location_code="native_failure", occurrence=0.0)
    for name in ("populate_liftover_sheet", "calculate_liftover_components", "project_liftover_return"):
        monkeypatch.setattr(core, name, forbidden)
    with pytest.raises(ValueError): facts.validate_molecular_fact(value, fact_source=LIFE)


@pytest.mark.parametrize("fact_source", [ITC, LIFE])
def test_source_group_copies_and_canonical_dedup_preserve_existing_meaning(fact_source):
    value = itc_value() if fact_source == ITC else life_value()
    merged = facts.merge_molecular_facts([value], [deepcopy(value)], fact_source=fact_source)
    assert canonical(merged) == canonical([value]) and merged[0] is not value
    conflict = deepcopy(value)
    if fact_source == ITC: conflict["kd"] = dict(state="present", value=0.0, unit="mol_per_litre", reason=None)
    else: conflict["rows"][0]["native_chain_score"] = -1
    with pytest.raises(ValueError, match="facts_source_conflict"):
        facts.merge_molecular_facts([value], [conflict], fact_source=fact_source)
    with pytest.raises(ValueError, match="facts_array_required"):
        facts.merge_molecular_facts(tuple([value]), fact_source=fact_source)


def test_unrelated_forms_never_enter_full_validation_or_source_declarations(monkeypatch):
    from gene_annotation_episode import communication
    monkeypatch.setattr(communication, "validate_closed_schema", forbidden)
    monkeypatch.setattr(facts, "_sources", forbidden)
    schema = obj(dict(sources={"type": "array", "items": {"type": "string"}, "x-source": "changed_record_refs"}))
    assert facts.requested_molecular_fact_sources(schema) == ()
    for name in (ITC, LIFE):
        assert facts.requested_molecular_fact_fields(schema, fact_source=name) == []


def test_requested_groups_are_finite_and_exact_registered_contracts():
    from gene_annotation_episode.arsenic_speciation_result_contracts import ordinary_arsenic_fact_sources
    from gene_annotation_episode.circular_dichroism_contracts import circular_dichroism_fact_sources
    from gene_annotation_episode.homer_motif_result_contracts import homer_motif_fact_sources
    from gene_annotation_episode.liftover_contracts import liftover_fact_sources
    from gene_annotation_episode.macs2_peak_result_contracts import macs2_peak_fact_sources
    from gene_annotation_episode.molecular_measurement_tools import itc_parameter_fact_sources
    from gene_annotation_episode.molecular_sequence_result_contracts import (
        ordinary_molecular_sequence_fact_sources, ordinary_orf_fact_sources,
    )
    from gene_annotation_episode.protein_disorder_result_contracts import ordinary_disorder_fact_sources
    from gene_annotation_episode.primer_placement_result_contracts import ordinary_primer_placement_fact_sources
    from gene_annotation_episode.protease_kinetics_result_contracts import ordinary_protease_kinetics_fact_sources
    from gene_annotation_episode.reference_edit_outcome_tools import reference_edit_outcome_fact_sources
    from gene_annotation_episode.tf_binding_result_contracts import tf_binding_fact_sources
    from gene_annotation_episode.vcf_result_tools import vcf_result_fact_sources

    expected = {
        "vcf_result_outcomes": vcf_result_fact_sources()["vcf_result_outcomes"],
        ITC: itc_parameter_fact_sources()[ITC],
        LIFE: liftover_fact_sources()[LIFE],
        CD: circular_dichroism_fact_sources()[CD],
        ORF: ordinary_orf_fact_sources()[ORF],
        "n_glycosylation_motif_outcomes": ordinary_molecular_sequence_fact_sources(
            "find_n_glycosylation_motifs")["n_glycosylation_motif_outcomes"],
        "o_glycosylation_hotspot_outcomes": ordinary_molecular_sequence_fact_sources(
            "predict_o_glycosylation_hotspots")["o_glycosylation_hotspot_outcomes"],
        EDIT: reference_edit_outcome_fact_sources()[EDIT],
        "macs2_peak_outcomes": macs2_peak_fact_sources()["macs2_peak_outcomes"],
        "homer_motif_outcomes": homer_motif_fact_sources()["homer_motif_outcomes"],
        "tf_binding_outcomes": tf_binding_fact_sources()["tf_binding_outcomes"],
        "protease_kinetics_outcomes": ordinary_protease_kinetics_fact_sources()["protease_kinetics_outcomes"],
        "arsenic_speciation_outcomes": ordinary_arsenic_fact_sources()["arsenic_speciation_outcomes"],
        "protein_disorder_outcomes": ordinary_disorder_fact_sources()["protein_disorder_outcomes"],
        "primer_placement_outcomes": ordinary_primer_placement_fact_sources()["primer_placement_outcomes"],
    }
    sources = facts.molecular_fact_sources()
    assert sources == expected and tuple(sources) == tuple(expected)
    schema = obj({name: sources[name]["report_schema"] for name in sources})
    assert facts.requested_molecular_fact_sources(schema) == tuple(expected)
    labels = {"vcf_result_outcomes": "VCF result", LIFE: "liftover", CD: "CD", ORF: "ORF",
        "n_glycosylation_motif_outcomes": "N-glycosylation", "o_glycosylation_hotspot_outcomes": "O-glycosylation",
        EDIT: "reference editing outcome", "macs2_peak_outcomes": "MACS2 peak",
        "homer_motif_outcomes": "HOMER motif", "tf_binding_outcomes": "TF binding",
        "protease_kinetics_outcomes": "protease kinetics", "arsenic_speciation_outcomes": "arsenic speciation",
        "protein_disorder_outcomes": "protein disorder", "primer_placement_outcomes": "primer placement"}
    for name in sources:
        assert facts.requested_molecular_fact_fields(schema, fact_source=name) == [name]
        changed = deepcopy(schema); changed["properties"][name]["minItems"] = 1
        if name != ITC:
            with pytest.raises(ReportBoundaryError, match=labels[name] + " fact schema must match") as failure:
                facts.requested_molecular_fact_fields(changed, fact_source=name)
            assert failure.value.diagnostic["code"] == "invalid_schema"
        else:
            with pytest.raises(ValueError, match="itc_parameter_requested_schema_conflict"):
                facts.requested_molecular_fact_fields(changed, fact_source=name)
    with pytest.raises(ValueError, match="molecular_fact_source_invalid"):
        facts.validate_molecular_fact({}, fact_source="another_provider")


@pytest.mark.parametrize("state", ["mapping", "unknown", "not_started", "empty"])
@pytest.mark.parametrize("mode", ["read_stored", "calculate_saved"])
def test_own_saved_views_keep_full_original_source_group_and_no_file_grants(tmp_path, monkeypatch, state, mode):
    with publication_case(tmp_path, state=state) as case:
        context = recorded_scientific(case)
        _, projection = saved_action(case, context, mode=mode)
        saved_action(case, context, mode="read_stored", index=1)
        expected = core.project_liftover_return(case.stored["components"], source_ref=case.source["id"])
        assert projection["rows"] == []
        if state == "mapping": assert len(expected["rows"]) == 1
        guard_work(case, monkeypatch)
        before, changes = all_rows(case.value.store), case.value.store.db.total_changes
        actual = facts.own_molecular_facts(case.registry, context,
            read_received=case.services.read_received_molecular_input, fact_source=LIFE)
        assert canonical(actual) == canonical([expected])
        assert not case.private_refs.intersection(case.value.receipts.known(context.episode_id))
        assert all_rows(case.value.store) == before and case.value.store.db.total_changes == changes


@pytest.mark.parametrize("change", ["operation_name", "arguments", "scope", "operation_ref", "runtime_result", "selected_source", "false_producer"])
def test_own_group_authenticates_current_action_separately_from_original_publication(tmp_path, monkeypatch, change):
    with publication_case(tmp_path) as case:
        context = recorded_scientific(case)
        key, _ = saved_action(case, context,
            mode="convert" if change == "false_producer" else "read_stored",
            result_ref=case.value.source_ref if change == "selected_source" else None)
        store = case.value.store
        if change == "operation_name": store.db.execute("UPDATE tool_operations SET name='state.query' WHERE operation_key=?", (key,))
        elif change == "arguments": store.db.execute("UPDATE tool_operations SET arguments='{}' WHERE operation_key=?", (key,))
        elif change == "scope": store.db.execute("UPDATE tool_operations SET scope='{}' WHERE operation_key=?", (key,))
        elif change in {"operation_ref", "runtime_result"}:
            row = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
                (context.run_id, context.episode_id)).fetchone()
            result = json.loads(row[0])
            if change == "operation_ref": result["operation_ref"] = "operation_" + "0" * 24
            else: result["record_refs"] = []
            store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
                (canonical(result), context.run_id, context.episode_id))
        guard_work(case, monkeypatch)
        expected_error = "ordinary_liftover_publication_conflict" if change == "false_producer" else "liftover_point_action_"
        with pytest.raises(ValueError, match=expected_error):
            facts.own_molecular_facts(case.registry, context,
                read_received=case.services.read_received_molecular_input, fact_source=LIFE)


def test_non_scientific_own_context_is_not_relabelled_as_a_scientific_owner(tmp_path, monkeypatch):
    with publication_case(tmp_path) as case:
        monkeypatch.setattr(case.value.store, "get_artifact", forbidden)
        with pytest.raises(ValueError, match="liftover_point_scientific_owner_required"):
            facts.own_molecular_facts(case.registry, case.producer,
                read_received=case.services.read_received_molecular_input, fact_source=LIFE)


@pytest.mark.parametrize("state", ["absent", "unrelated", "empty", "group", "malformed"])
def test_frozen_absence_empty_and_saved_group_remain_distinct_without_private_reads(tmp_path, monkeypatch, state):
    with publication_case(tmp_path) as case:
        return_tables(case.value.store)
        context = recorded_scientific(case)
        group = [core.project_liftover_return(case.stored["components"], source_ref=case.source["id"])]
        if state != "absent":
            saved = {} if state == "unrelated" else {LIFE: [] if state == "empty" else None if state == "malformed" else group}
            case.value.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?)",
                (context.run_id, context.episode_id, canonical(saved)))
        forbid_frozen_work(case, monkeypatch)
        before = all_rows(case.value.store)
        if state == "malformed":
            with pytest.raises(ValueError, match="frozen_source_invalid"):
                facts.frozen_molecular_facts(case.value.store, context.run_id, context, fact_source=LIFE)
        else:
            result = facts.frozen_molecular_facts(case.value.store, context.run_id, context, fact_source=LIFE)
            assert canonical(result) == canonical(None if state in {"absent", "unrelated"} else [] if state == "empty" else group)
        assert all_rows(case.value.store) == before


@pytest.mark.parametrize("change", ["literal", "value", "missing", "float_alias"])
def test_frozen_return_compares_original_literal_values_and_types(tmp_path, monkeypatch, change):
    with publication_case(tmp_path) as case:
        _, _, group = saved_return(case)
        form = dict(mappings=deepcopy(group))
        if change == "value": form["mappings"][0]["rows"][0]["native_chain_score"] += 1
        elif change == "missing": form = {}
        elif change == "float_alias": form["mappings"][0]["rows"][0]["native_chain_score"] = 91.0
        forbid_frozen_work(case, monkeypatch)
        if change == "literal":
            facts.validate_frozen_molecular_return(form, form_schema(), group, fact_source=LIFE)
        else:
            with pytest.raises(ReportBoundaryError) as failure:
                facts.validate_frozen_molecular_return(form, form_schema(), group, fact_source=LIFE)
            assert failure.value.diagnostic["field"] == "mappings"


def test_received_and_onward_groups_use_original_form_prefix_without_private_bytes(tmp_path, monkeypatch):
    with publication_case(tmp_path) as case:
        _, onward, group = saved_return(case)
        forbid_frozen_work(case, monkeypatch)
        store, parent = case.value.store, case.value.parent
        before, changes = all_rows(store), store.db.total_changes
        for context in (parent, onward):
            actual = facts.received_molecular_facts(store, context.run_id, context, fact_source=LIFE)
            assert canonical(actual) == canonical(group)
            assert not case.private_refs.intersection(case.value.receipts.known(context.episode_id))
        assert all_rows(store) == before and store.db.total_changes == changes


@pytest.mark.parametrize("change", ["returned_value", "frozen_value", "prefix_hash", "ungranted_source", "context"])
def test_received_groups_reject_forged_values_receipts_prefixes_and_context(tmp_path, monkeypatch, change):
    with publication_case(tmp_path) as case:
        child, onward, group = saved_return(case)
        store, parent = case.value.store, case.value.parent
        context = parent
        if change in {"returned_value", "frozen_value"}:
            altered = deepcopy(group); altered[0]["rows"][0]["native_chain_score"] += 1
            if change == "returned_value":
                store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=2",
                    (canonical(dict(mappings=altered)), parent.run_id, parent.episode_id))
            else: store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
                (canonical({LIFE: altered}), child.run_id, child.episode_id))
        elif change == "prefix_hash":
            row = store.db.execute("SELECT received_report_prefix FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?",
                (onward.run_id, onward.episode_id)).fetchone()
            prefix = json.loads(row[0]); prefix["attempts"][0]["form_sha256"] = "0" * 64
            store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE run_id=? AND episode_id=?",
                (canonical(prefix), onward.run_id, onward.episode_id)); context = onward
        elif change == "ungranted_source":
            store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
                (parent.run_id, parent.episode_id, case.source["id"]))
        else: context = replace(parent, scope={"subject_refs": []})
        forbid_frozen_work(case, monkeypatch)
        with pytest.raises(ValueError):
            facts.received_molecular_facts(store, context.run_id, context, fact_source=LIFE)


def test_onward_does_not_import_a_later_return_outside_its_frozen_prefix(tmp_path, monkeypatch):
    with publication_case(tmp_path) as case:
        child, onward, group = saved_return(case)
        store, parent = case.value.store, case.value.parent
        corrupted = deepcopy(group); corrupted[0]["rows"][0]["native_chain_score"] += 1
        store.db.execute("INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,NULL)",
            (parent.run_id, parent.episode_id, 4, "later-unreceived-delivery", child.episode_id,
                canonical(plain(child.request)["report_contract"]), canonical(dict(mappings=corrupted))))
        forbid_frozen_work(case, monkeypatch)
        assert canonical(facts.received_molecular_facts(store, onward.run_id, onward, fact_source=LIFE)) == canonical(group)
        with pytest.raises(ValueError):
            facts.received_molecular_facts(store, parent.run_id, parent, fact_source=LIFE)
