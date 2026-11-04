"""Engineered host custody controls, without alignment/native/model execution.

The imported admission fixture supplies literal ATGC/ATAC native carrier data
through the actual ToolRegistry publisher and first-insert Journal records.
These tests exercise real Store/action/receipt owners. They do not claim a
whole Workflow, a native aligner run, or a biological repair mechanism.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode import reference_edit_outcomes as core
from gene_annotation_episode import reference_edit_outcome_tools as host
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.molecular_measurement_tools import (
    _recorded_molecular_producer, _recorded_molecular_producer_details,
)
from gene_annotation_episode.molecular_sequence_input_bindings import MolecularSequenceInputBindings
from test_reference_edit_alignment_admission import admission, _tables


def _context(case, *, name="analysis", run_id=None, initial=None):
    run_id = case.producer.run_id if run_id is None else run_id
    journal, receipts = Journal(case.store, run_id), EpisodeReceipts(case.store, run_id)
    path = (("scientific_process", name),)
    episode = EpisodeRef(run_id, path).episode_id
    manifest = receipts.bind(episode)
    scope = case.store.validate_scope({"subject_refs": [case.query, case.reference, case.other]})
    request = dict(message=dict(scope=scope, episode_assignment={}, knowledge_inheritance=manifest))
    journal.save("runtime_episodes", dict(episode_id=episode, path=canonical(path), request=canonical(request),
        initial_credit=0., state="active"))
    context = BindingContext(run_id, episode, "scientific_process", path, scope, {}, request)
    receipts.receive(episode, [case.alignment, case.query, case.reference, case.other] if initial is None else initial, kind="initial")
    # Explicit engineering access port. The real input owner still authenticates
    # the saved root, exact scope, original manifest and actual known receipts.
    owner = SimpleNamespace(store=case.store, run_id=run_id, resolve_received_reference=lambda *_: None)
    inputs = MolecularSequenceInputBindings(owner)
    def reader(current, reference, namespace, **options):
        if namespace == "source":
            assert options == {"source_metadata_only": True}
            return inputs.read_received_source(current, reference)
        assert options == {"subject_metadata_only": True}
        return inputs.read_received_subject(current, reference, namespace)
    return SimpleNamespace(context=context, journal=journal, receipts=receipts, reader=reader)


def _arguments(case, *, copies=1, selected=True):
    return dict(mode="analyze", population=[dict(reference_ref=case.reference, edited_ref=case.query,
        alignment_ref=case.alignment if selected else None, group_label="declared") for _ in range(copies)],
        gap_bins=None, guide_comparisons=[], template_comparisons=[])


def _invoke(case, receiver, arguments, *, index=0, commit=True, existing=False):
    context = receiver.context
    key = f"{context.run_id}:{context.episode_id}:{index}"
    if not existing:
        receiver.journal.save("runtime_actions", dict(episode_id=context.episode_id, decision_index=index,
            action=canonical(dict(kind="tool", tool=host.TOOL, arguments=arguments)), result=None, credit=0.))
    with case.tools.current_invocation(context, read_received=receiver.reader, tool_name=host.TOOL,
            arguments=arguments, operation_key=key):
        result = host.execute_reference_edit_outcome(case.tools, arguments, scope=plain(context.scope),
            operation_key=key, authority=(context, receiver.reader))
    if commit:
        receiver.journal.save("runtime_actions", dict(episode_id=context.episode_id, decision_index=index,
            action=canonical(dict(kind="tool", tool=host.TOOL, arguments=arguments)), result=canonical(result)))
    return result, key


def _publication(case, *, receiver=None, arguments=None):
    receiver = _context(case) if receiver is None else receiver
    arguments = _arguments(case) if arguments is None else arguments
    result, key = _invoke(case, receiver, arguments)
    assert result["status"] in ("completed", "partial"), result
    source = case.store.get(result["result"]["source_ref"])
    return SimpleNamespace(receiver=receiver, arguments=arguments, result=result, key=key, source=source)


def _forbidden(*args, **kwargs):
    raise AssertionError("saved operation reopened original inputs or ran forbidden work")


def _private_refs(source):
    return {source["request_ref"], *source["auxiliary_artifact_refs"]}


def _read(case, publication, *, receiver=None, envelope=False):
    receiver = publication.receiver if receiver is None else receiver
    return host.read_reference_edit_outcome_publication(case.tools, receiver.context, receiver.reader,
        publication.source["id"], require_envelope=envelope, recovery_operation_key=(publication.key
            if receiver is publication.receiver else None))


def test_contract_and_exact_fact_schema_are_detached_source_only():
    contract = host.reference_edit_outcome_tool_contract()
    assert contract["invocation_route"] == {"kind": "direct"} and contract["resources"] == "local"
    assert [branch["properties"]["mode"]["const"] for branch in contract["input_schema"]["anyOf"]] == [
        "analyze", "read_stored", "calculate_saved"]
    facts = host.reference_edit_outcome_fact_sources()
    assert set(facts) == {"reference_edit_outcomes"}
    source = facts["reference_edit_outcomes"]
    assert source["type"] == "array" and source["meaning"]
    assert source["report_schema"] == dict(type="array", items=core.RETURN_SCHEMA, **{"x-source": "reference_edit_outcomes"})
    source["report_schema"]["items"].clear()
    assert host.reference_edit_outcome_fact_sources()["reference_edit_outcomes"]["report_schema"]["items"] == core.RETURN_SCHEMA


def test_public_primary_is_compact_and_original_captures_are_private(admission):
    case = admission()
    receiver = _context(case)
    receipts_before = list(case.store.db.execute("SELECT * FROM runtime_record_receipts"))
    publication = _publication(case, receiver=receiver, arguments=_arguments(case, copies=2))
    public, source = publication.result["result"], publication.source
    assert public["status"] == "complete"
    assert [pair["pair_ordinal"] for pair in public["pairs"]] == [0, 1]
    assert all(pair["whole_pair_type"] == "substitution_only" and pair["counts"]["substituted_positions"] == 1
        and pair["counts"]["query_gap_columns"] == pair["counts"]["reference_gap_columns"] == 0 for pair in public["pairs"])
    population = public["populations"]["overall"]
    assert population["declared_pair_count"] == population["classified_pair_count"] == 2
    packet = json.loads(case.store.get_artifact(source["artifact_ref"]))
    assert packet == dict(version=host.PACKET_VERSION, value={key: value for key, value in public.items()
        if key not in ("version", "source_ref")})
    assert "sheet" not in packet and "comparison_inputs" not in packet and "aligned_query" not in canonical(packet)
    private = _read(case, publication, envelope=True)
    assert private["stored"]["sheet"]["alignment_inputs"][0]["grading"]["sheet"]["traceback"]["query"] == "ATGC"
    assert private["control"]["native_call_state"] == "not_requested"
    alignment_source = case.store.get(case.store.get(case.alignment)["source_ref"])
    assert source["parent_source_refs"] == [alignment_source["id"]]
    assert _private_refs(source).isdisjoint({alignment_source["artifact_ref"], *alignment_source["auxiliary_artifact_refs"],
        case.store.get(case.query)["sequence_ref"], case.store.get(case.reference)["sequence_ref"]})
    # Adapter derivation itself records no delivery or scientific observation.
    after = list(case.store.db.execute("SELECT * FROM runtime_record_receipts"))
    assert after == receipts_before
    assert case.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


@pytest.mark.parametrize("shape", ["not_selected", "local", "legacy"])
def test_partial_unknown_and_unselected_are_not_observed_zero(admission, shape):
    case = admission(mode="local" if shape == "local" else "global",
        retention="legacy_companion" if shape == "legacy" else "modern")
    publication = _publication(case, arguments=_arguments(case, selected=shape != "not_selected"))
    public, = [publication.result["result"]]
    pair, = public["pairs"]
    assert publication.result["status"] == "partial"
    if shape == "legacy":
        assert pair["whole_pair_type"] == "substitution_only"
        assert pair["counts"]["substituted_positions"] == 1
        assert "saved_correspondence_unavailable" in pair["issue_codes"]
    elif shape == "local":
        assert pair["counts"]["substituted_positions"] == 1 and pair["counts"]["query_gap_columns"] == 0
    else:
        assert pair["counts"]["substituted_positions"] is None and pair["events"] is None
    if shape != "legacy":
        assert pair["whole_pair_type"] is None and public["populations"]["overall"]["classified_pair_count"] == 0
        assert all(row["fraction_of_classified"]["value"] is None for row in public["populations"]["overall"]["categories"])


def test_explicit_comparison_subject_admission_precedes_literal_shared_extraction(admission, monkeypatch):
    case = admission()
    receiver = _context(case)
    arguments = _arguments(case)
    arguments["guide_comparisons"] = [dict(pair_ordinal=0, guide_ref=case.reference, reference_interval=[0, 4],
        orientation="as_is", molecule="dna")]
    arguments["template_comparisons"] = [dict(pair_ordinal=0, template_ref=case.query, edited_interval=[0, 4],
        reference_interval=[0, 4], orientation="as_is", molecule="dna")]
    sequence = case.tools._sequence
    accessed = []
    def capture(reference, **kwargs):
        assert reference in set(receiver.receipts.known(receiver.context.episode_id))
        accessed.append(reference)
        return sequence(reference, **kwargs)
    monkeypatch.setattr(case.tools, "_sequence", capture)
    publication = _publication(case, receiver=receiver, arguments=arguments)
    assert accessed == [case.reference, case.query]
    stored = _read(case, publication, envelope=True)["stored"]
    assert stored["sheet"]["comparison_inputs"] == {"sequences": [
        {"subject_ref": case.reference, "sequence": "ATAC"}, {"subject_ref": case.query, "sequence": "ATGC"}]}
    assert publication.result["result"]["guide_comparisons"][0]["literal_comparison"]["state"] == "available"
    assert publication.result["result"]["template_comparisons"][0]["edited_comparison"]["state"] == "available"
    assert "ATAC" not in canonical(json.loads(case.store.get_artifact(publication.source["artifact_ref"])))


def test_read_stored_is_literal_no_math_private_bytes_or_input_file_grants(admission, monkeypatch):
    case = admission()
    original = _publication(case)
    receiver = _context(case, name="saved", run_id="reference-edit-saved-reader", initial=[original.source["id"]])
    known = set(receiver.receipts.known(receiver.context.episode_id))
    assert known == {original.source["id"]}
    actual = case.store.get_artifact
    opened = []
    def public_only(reference):
        assert reference == original.source["artifact_ref"]
        opened.append(reference)
        return actual(reference)
    monkeypatch.setattr(case.store, "get_artifact", public_only)
    monkeypatch.setattr(case.tools, "_sequence", _forbidden)
    for name in ("populate_reference_edit_outcome_sheet", "calculate_reference_edit_outcome_components", "project_reference_edit_outcome_return"):
        monkeypatch.setattr(core, name, _forbidden)
    result, key = _invoke(case, receiver, dict(mode="read_stored", result_ref=original.source["id"]))
    assert result["status"] == "completed" and result["result"] == original.result["result"]
    assert result["record_refs"] == [original.source["id"]] and result["changed_record_refs"] == []
    assert host.read_reference_edit_outcome_action_result(case.tools, receiver.context,
        dict(mode="read_stored", result_ref=original.source["id"]), key, reader=receiver.reader) == original.result["result"]
    assert opened and set(receiver.receipts.known(receiver.context.episode_id)) == known
    details = _recorded_molecular_producer_details(case.tools, original.source["id"], host.TOOL)
    assert details["invocation"]["operation_key"] == original.key != key
    assert _recorded_molecular_producer(case.tools, original.source["id"], host.TOOL) == (details["arguments"], details["invocation"])


def test_saved_rebin_has_distinct_source_original_observations_and_one_shared_calculation(admission, monkeypatch):
    case = admission()
    original = _publication(case)
    old_record = deepcopy(original.source)
    old_private = _read(case, original, envelope=True)
    receiver = _context(case, name="rebin", run_id="reference-edit-rebin", initial=[original.source["id"]])
    before = set(receiver.receipts.known(receiver.context.episode_id))
    actual, calculate = case.store.get_artifact, core.calculate_reference_edit_outcome_components
    forbidden = {case.store.get(case.query)["sequence_ref"], case.store.get(case.reference)["sequence_ref"]}
    alignment_source = case.store.get(case.store.get(case.alignment)["source_ref"])
    forbidden.update([alignment_source["artifact_ref"], *alignment_source["auxiliary_artifact_refs"]])
    opened, calls = [], []
    def retained(reference):
        assert reference not in forbidden
        opened.append(reference)
        return actual(reference)
    def calculator(sheet):
        calls.append(deepcopy(sheet))
        return calculate(sheet)
    monkeypatch.setattr(case.store, "get_artifact", retained)
    monkeypatch.setattr(case.tools, "_sequence", _forbidden)
    monkeypatch.setattr(core, "calculate_reference_edit_outcome_components", calculator)
    args = dict(mode="calculate_saved", result_ref=original.source["id"],
        gap_bins=dict(deletion_upper_bounds_nt=[1, 10], insertion_upper_bounds_nt=[2]))
    result, key = _invoke(case, receiver, args)
    assert result["status"] == "completed", result
    derived = case.store.get(result["result"]["source_ref"])
    assert derived["id"] != original.source["id"] and derived["parent_source_refs"] == [original.source["id"]]
    assert len(calls) == 1 and calls[0]["alignment_inputs"] == old_private["stored"]["sheet"]["alignment_inputs"]
    assert calls[0]["comparison_inputs"] == old_private["stored"]["sheet"]["comparison_inputs"]
    assert result["result"]["gap_bins"] == args["gap_bins"] and case.store.get(old_record["id"]) == old_record
    assert host.read_reference_edit_outcome_action_result(case.tools, receiver.context, args, key,
        reader=receiver.reader) == result["result"]
    assert set(receiver.receipts.known(receiver.context.episode_id)) == before
    assert _private_refs(derived).isdisjoint(_private_refs(original.source))


@pytest.mark.parametrize("timing", ["unreceived", "later"])
def test_saved_action_cannot_borrow_a_later_or_missing_source_receipt(admission, timing):
    case = admission()
    original = _publication(case)
    receiver = _context(case, name="unreceived", initial=[])
    args = dict(mode="read_stored", result_ref=original.source["id"])
    result, key = _invoke(case, receiver, args)
    assert result["status"] == "invalid" and result["record_refs"] == []
    if timing == "later":
        receiver.receipts.receive(receiver.context.episode_id, [original.source["id"]], kind="own_action", source_index=1)
    repeated, _ = _invoke(case, receiver, args, existing=True)
    assert repeated == result


def test_exact_pending_current_action_recovers_without_a_second_derivation(admission, monkeypatch):
    case = admission()
    receiver, args = _context(case), _arguments(case)
    result, key = _invoke(case, receiver, args, commit=False)
    assert result["status"] == "completed", result
    before = _tables(case.store), case.store.db.total_changes
    monkeypatch.setattr(core, "populate_reference_edit_outcome_sheet", _forbidden)
    monkeypatch.setattr(core, "calculate_reference_edit_outcome_components", _forbidden)
    repeated, _ = _invoke(case, receiver, args, commit=False, existing=True)
    assert repeated == result and (_tables(case.store), case.store.db.total_changes) == before
    with pytest.raises(ContractError, match="publication_conflict"):
        _recorded_molecular_producer_details(case.tools, result["result"]["source_ref"], host.TOOL)
    with pytest.raises(ContractError, match="publication_conflict|action_conflict|current_invocation_required"):
        _recorded_molecular_producer_details(case.tools, result["result"]["source_ref"], host.TOOL,
            recovery_context=receiver.context, recovery_operation_key=key)


@pytest.mark.parametrize("change", ["arguments", "scope", "runtime", "operation_ref"])
def test_real_action_operation_conflicts_deny_before_private_payloads(admission, monkeypatch, change):
    case = admission()
    original = _publication(case)
    if change in ("arguments", "scope"):
        value = {**original.arguments, "gap_bins": {"deletion_upper_bounds_nt": [], "insertion_upper_bounds_nt": []}} if change == "arguments" else {"subject_refs": []}
        case.store.db.execute("UPDATE tool_operations SET " + change + "=? WHERE operation_key=?", (canonical(value), original.key))
    else:
        saved = deepcopy(original.result)
        if change == "runtime": saved["result"]["pairs"][0]["counts"]["substituted_positions"] = True
        else: saved["operation_ref"] = "operation_" + "a"*24
        case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(saved), original.receiver.context.run_id, original.receiver.context.episode_id))
    monkeypatch.setattr(case.store, "get_artifact", _forbidden)
    with pytest.raises(ContractError, match="publication_conflict|action_conflict"):
        _read(case, original, envelope=True)


def test_source_shape_cannot_establish_a_selected_producer(admission, monkeypatch):
    case = admission()
    original = _publication(case)
    payload = {key: value for key, value in original.source.items() if key not in ("id", "origin", "record_type")}
    payload["accession"] = "engineered_unpublished"
    forged = case.store.put("source", payload, origin="tool")
    monkeypatch.setattr(case.store, "get_artifact", _forbidden)
    with pytest.raises(ContractError, match="publication_conflict"):
        host.read_reference_edit_outcome_publication(case.tools, original.receiver.context,
            original.receiver.reader, forged["id"])


def test_selected_argument_conflict_does_not_replace_an_occupied_operation(admission):
    case = admission()
    original = _publication(case)
    changed = {**original.arguments, "population": []}
    before = _tables(case.store), case.store.db.total_changes
    with case.tools.current_invocation(original.receiver.context, read_received=original.receiver.reader,
            tool_name=host.TOOL, arguments=changed, operation_key=original.key):
        with pytest.raises(ContractError, match="selected_action_conflict"):
            host.execute_reference_edit_outcome(case.tools, changed, scope=plain(original.receiver.context.scope),
                operation_key=original.key, authority=(original.receiver.context, original.receiver.reader))
    assert (_tables(case.store), case.store.db.total_changes) == before


def test_unreceived_comparison_is_rejected_before_any_sequence_bytes(admission, monkeypatch):
    case = admission()
    receiver = _context(case, initial=[case.alignment])
    # Alignment delivery carries its operands in legacy ordinary receipts;
    # remove this explicit comparison's actual receipt as a negative fixture.
    case.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
        (receiver.context.run_id, receiver.context.episode_id, case.other))
    args = _arguments(case)
    args["guide_comparisons"] = [dict(pair_ordinal=0, guide_ref=case.other, reference_interval=[0, 4], orientation="as_is", molecule="dna")]
    monkeypatch.setattr(case.tools, "_sequence", _forbidden)
    original_sources = case.store.count("source")
    result, _ = _invoke(case, receiver, args)
    assert result["status"] == "invalid" and result["record_refs"] == [] and case.store.count("source") == original_sources


def test_private_payload_tampering_keeps_literal_read_but_blocks_recalculation(admission):
    case = admission()
    original = _publication(case)
    metadata = case.store.get(original.source["auxiliary_artifact_refs"][0])
    path = case.store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
    path.write_bytes(path.read_bytes() + b" ")
    assert _read(case, original)["public"] == original.result["result"]
    with pytest.raises((ValueError, ContractError), match="digest_mismatch|retained_artifact_mismatch"):
        _read(case, original, envelope=True)


def test_failed_atomic_publication_rolls_back_source_and_caches_only_original_failure(admission, monkeypatch):
    case = admission()
    receiver, args = _context(case), _arguments(case)
    before = case.store.count("source"), list(case.store.db.execute("SELECT * FROM runtime_record_receipts"))
    save, calls = case.tools._save, []
    def fail_once(*values):
        calls.append(values)
        if len(calls) == 1: raise RuntimeError("engineered_save_failure")
        return save(*values)
    monkeypatch.setattr(case.tools, "_save", fail_once)
    result, _ = _invoke(case, receiver, args)
    assert result["status"] == "failed" and result["record_refs"] == []
    assert (case.store.count("source"), list(case.store.db.execute("SELECT * FROM runtime_record_receipts"))) == before
    monkeypatch.setattr(core, "calculate_reference_edit_outcome_components", _forbidden)
    repeated, _ = _invoke(case, receiver, args, existing=True)
    assert repeated == result and len(calls) == 2


def test_source_receipt_stops_at_public_source_and_private_controls_always_deny(admission, monkeypatch):
    from gene_annotation_episode.materials import artifact_path
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    case = admission()
    original = _publication(case)
    receiver = _context(case, name="source-receiver", initial=[original.source["id"]])
    known = set(receiver.receipts.known(receiver.context.episode_id))
    assert known == {original.source["id"]}
    before = _tables(case.store), case.store.db.total_changes
    monkeypatch.setattr(case.store, "get_artifact", _forbidden)
    assert molecular_reference_restriction(case.store, receiver.context, original.source["id"], "source") is True
    assert molecular_reference_restriction(case.store, receiver.context, original.source["artifact_ref"], "artifact") is False
    for reference in _private_refs(original.source):
        assert molecular_reference_restriction(case.store, receiver.context, reference, "artifact") is False
        assert molecular_reference_restriction(case.store, None, reference, "artifact", private_only=True) is False
        with pytest.raises(ContractError, match="molecular_private_artifact_not_readable"):
            artifact_path(case.store, reference)
    original_file = case.store.get(case.query)["sequence_ref"]
    assert original_file in set(original.receiver.receipts.known(original.receiver.context.episode_id))
    assert molecular_reference_restriction(case.store, original.receiver.context, original_file, "artifact") is None
    assert (_tables(case.store), case.store.db.total_changes) == before


def test_generic_own_facts_authenticate_producer_and_redisplay_then_freeze_literal_group(admission, monkeypatch):
    from gene_annotation_episode import molecular_result_facts as facts
    from gene_annotation_episode.communication import validate_form
    case = admission()
    original = _publication(case)
    receiver = original.receiver
    receiver.receipts.receive(receiver.context.episode_id, [original.source["id"]], kind="own_action", source_index=0)
    read_args = dict(mode="read_stored", result_ref=original.source["id"])
    read, _ = _invoke(case, receiver, read_args, index=1)
    assert read["result"] == original.result["result"]
    actual, opened = case.store.get_artifact, []
    def public_only(reference):
        assert reference == original.source["artifact_ref"]
        opened.append(reference)
        return actual(reference)
    monkeypatch.setattr(case.store, "get_artifact", public_only)
    for name in ("populate_reference_edit_outcome_sheet", "calculate_reference_edit_outcome_components", "project_reference_edit_outcome_return"):
        monkeypatch.setattr(core, name, _forbidden)
    group = facts.own_molecular_facts(case.tools, receiver.context, read_received=receiver.reader,
        fact_source="reference_edit_outcomes")
    assert group == [original.result["result"]] and opened
    schema = obj(dict(outcomes=host.reference_edit_outcome_fact_sources()["reference_edit_outcomes"]["report_schema"]))
    resolver_calls = []
    def resolver(reference, namespace):
        resolver_calls.append((reference, namespace))
        return reference == original.source["id"] and namespace == "source"
    assert validate_form(dict(outcomes=group), schema, resolver) == dict(outcomes=group)
    assert resolver_calls and set(resolver_calls) == {(original.source["id"], "source")}
    receiver.journal.save("runtime_forms", dict(episode_id=receiver.context.episode_id,
        facts=canonical({"reference_edit_outcomes": group}), form=canonical(dict(outcomes=group))))
    monkeypatch.setattr(case.store, "get_artifact", _forbidden)
    monkeypatch.setattr(host, "read_reference_edit_outcome_action_result", _forbidden)
    before = _tables(case.store), case.store.db.total_changes
    frozen = facts.frozen_molecular_facts(case.store, receiver.context.run_id, receiver.context,
        fact_source="reference_edit_outcomes")
    assert frozen == group
    facts.validate_frozen_molecular_return(dict(outcomes=group), schema, frozen, fact_source="reference_edit_outcomes")
    # Possession of a Source does not manufacture a returned child form.
    assert facts.received_molecular_facts(case.store, receiver.context.run_id, receiver.context,
        fact_source="reference_edit_outcomes") == []
    assert (_tables(case.store), case.store.db.total_changes) == before


@pytest.mark.parametrize("fault", ["nested", "counterfeit", "float_count", "bool_ordinal"])
def test_exact_registered_form_rejects_schema_or_scalar_forgery_before_resolution(admission, fault):
    from gene_annotation_episode.communication import ReportBoundaryError, validate_form
    case = admission()
    original = _publication(case)
    source_schema = host.reference_edit_outcome_fact_sources()["reference_edit_outcomes"]["report_schema"]
    schema, form = obj(dict(outcomes=source_schema)), dict(outcomes=[deepcopy(original.result["result"])])
    if fault == "nested":
        schema = obj(dict(wrapper=obj(dict(outcomes=source_schema))))
        form = dict(wrapper=form)
    elif fault == "counterfeit":
        schema["properties"]["outcomes"]["minItems"] = 1
    elif fault == "float_count":
        form["outcomes"][0]["populations"]["overall"]["declared_pair_count"] = 1.0
    else:
        form["outcomes"][0]["pairs"][0]["pair_ordinal"] = False
    with pytest.raises((ReportBoundaryError, ValueError)):
        validate_form(form, schema, _forbidden)


def test_source_group_merge_and_frozen_comparison_preserve_original_operand_identity(admission):
    from gene_annotation_episode import molecular_result_facts as facts
    from gene_annotation_episode.communication import ReportBoundaryError
    case = admission()
    original = _publication(case)
    group = [original.result["result"]]
    changed = deepcopy(group)
    changed[0]["pairs"][0]["reference_ref"] = case.other
    changed[0]["populations"]["by_reference"][0]["reference_ref"] = case.other
    core.validate_reference_edit_outcome_return(changed[0])
    assert facts.merge_molecular_facts(group, deepcopy(group), fact_source="reference_edit_outcomes") == group
    with pytest.raises(ContractError, match="facts_source_conflict"):
        facts.merge_molecular_facts(group, changed, fact_source="reference_edit_outcomes")
    schema = obj(dict(outcomes=host.reference_edit_outcome_fact_sources()["reference_edit_outcomes"]["report_schema"]))
    with pytest.raises(ReportBoundaryError) as failure:
        facts.validate_frozen_molecular_return(dict(outcomes=changed), schema, group, fact_source="reference_edit_outcomes")
    assert failure.value.diagnostic["code"] == "reference_edit_outcome_frozen_source_mismatch"


@pytest.mark.parametrize("received", [False, True])
def test_public_source_read_requires_source_receipt_without_granting_packet_file(admission, monkeypatch, received):
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    case = admission()
    original = _publication(case)
    receiver = _context(case, name="public-source-read", initial=[original.source["id"]] if received else [])
    args = dict(source_ref=original.source["id"], representation="original", offset=0, limit=100000)
    context = receiver.context
    key = f"{context.run_id}:{context.episode_id}:0"
    receiver.journal.save("runtime_actions", dict(episode_id=context.episode_id, decision_index=0,
        action=canonical(dict(kind="tool", tool="source.read", arguments=args)), result=None, credit=0.))
    if not received:
        monkeypatch.setattr("gene_annotation_episode.materials._verified_artifact_path", _forbidden)
        monkeypatch.setattr(case.store, "get_artifact", _forbidden)
    def execute():
        with case.tools.current_invocation(context, read_received=receiver.reader, tool_name="source.read",
                arguments=args, operation_key=key):
            return case.tools.execute("source.read", args, scope=plain(context.scope), operation_key=key)
    result = execute()
    receiver.journal.save("runtime_actions", dict(episode_id=context.episode_id, decision_index=0,
        action=canonical(dict(kind="tool", tool="source.read", arguments=args)), result=canonical(result)))
    assert result["record_refs"] == []
    if received:
        assert result["status"] == "completed", result
        packet = json.loads(result["result"]["text"])
        assert packet == host._packet(original.result["result"])
        assert result["result"]["next_offset"] is None
        assert set(receiver.receipts.known(context.episode_id)) == {original.source["id"]}
        assert molecular_reference_restriction(case.store, context, original.source["artifact_ref"], "artifact") is False
        case.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
            (context.run_id, context.episode_id, original.source["id"]))
        assert execute()["status"] == "invalid"
        saved = case.store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
        assert json.loads(saved[0]) == result
    else:
        assert result["status"] == "invalid" and result["result"] is None
        assert result["feedback"]["code"] == "reference_edit_outcome_source_primary_body_not_received"
    assert _private_refs(original.source).isdisjoint(receiver.receipts.known(context.episode_id))
