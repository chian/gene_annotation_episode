"""Synthetic selected optical persistence, saved integrity and exact typed subsets."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_optical_inputs import read_optical_rate_operands
from gene_annotation_episode.literature_optical_storage import LiteratureOpticalRepository, optical_cells_schema
from gene_annotation_episode.state import Store
from test_literature_optical_inputs import fixture, witness, SOURCE, TEXT, PRIMITIVE_ORDER


SUFFIX = " Molecule reference-R; construct reference-RC; preparation reference-RP; condition buffer-B; measured NADH."


def setup(path, *, covariance=True, status="known", text=TEXT + SUFFIX, change=None, operands=None):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    artifact = store.artifact(text, "text/plain")
    source = store.put("source", {"provider": "synthetic_optical_fixture", "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")["id"]
    args = fixture(text, **(operands or {}))[0]
    for field, quote in (("molecule", "reference-R"), ("construct", "reference-RC"), ("preparation", "reference-RP"),
                         ("condition", "buffer-B"), ("measured_entity", "NADH")):
        args[field] = witness(text, quote)
    if change:
        change(args)
    def replace_source(value):
        if isinstance(value, dict):
            return {key: replace_source(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace_source(child) for child in value]
        return source if value == SOURCE else value
    args = replace_source(args)
    refs = [source]
    def read(ref, representation):
        row = store.get(ref)
        key = row["artifact_ref"] if representation == "original" else row["text_ref"]
        return {"artifact_ref": key, "content": store.get_artifact(key)}
    if covariance:
        ex = read_optical_rate_operands(args, read_source=read)
        rows = [ex["signals"]["sample"], ex["signals"]["blank"], ex["calibration"]["epsilon"], ex["calibration"]["path_length"]]
        data = {"version": "a105_optical_covariance_v1", "primitive_order": list(PRIMITIVE_ORDER),
            "primitive_measurement_keys": [r["measurement_key"] for r in rows],
            "primitive_physical_observation_keys": [r["physical_observation_key"] for r in rows],
            "primitive_owner_keys": [r["owner_key"] for r in rows], "primitive_units": [r["unit"]["raw_unit"] for r in rows],
            "covariance": [[1e-8, 5e-9, 0, 0], [5e-9, 1e-8, 0, 0], [0, 0, 10000, 0], [0, 0, 0, .01]],
            "origin": "synthetic", "covariance_status": status}
        cov_artifact = store.artifact(canonical(data), "application/json")
        cov_source = store.put("source", {"provider": "synthetic_optical_covariance", "accession": None, "uri": None,
            "artifact_ref": cov_artifact, "text_ref": cov_artifact, "request_ref": None, "version": None,
            "retrieved_at": None, "parent_source_refs": [source]}, origin="caller")["id"]
        refs.append(cov_source)
        args["covariance_source_ref"] = cov_source
    context = BindingContext("optical-run", "optical-child", "literature", (("literature", "case"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": [source]}, {}, refs)
    return store, context, args


def projected(repo, outcome, components=None):
    return repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=components)


@pytest.mark.parametrize("status", ["known", "estimated", "unknown"])
def test_complete_original_calculation_and_closed_typed_meanings(tmp_path, status):
    store, context, args = setup(tmp_path, status=status)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["calculation"]["net_depletion_rate"]["value"] == pytest.approx(2)
        cells = projected(repo, outcome)
        assert [row["component"] for row in cells] == ["net_rate", "variance_net_rate"]
        assert cells[0]["value"] == pytest.approx(2)
        assert cells[1]["value"] == (None if status == "unknown" else pytest.approx(.0024))
        assert cells[1]["unit"] == "uM2/min2"
        assert cells[0]["covariance"]["status"] == status
        assert cells[0]["source_origin"] == "synthetic"
        assert all("value" not in operand for operand in cells[0]["operands"].values())
        assert cells[0]["operands"]["epsilon"]["canonical_unit"] == "mM_inverse_cm_inverse"
        assert cells[0]["operands"]["epsilon"]["measurement_source_ref"] == args["source_ref"]
        assert optical_cells_schema()["items"]["properties"]["operands"]["properties"]["epsilon"]["properties"]["measurement_source_ref"]["x-reference-namespace"] == "source"
        assert store.get(cells[0]["context"]["construct"]["ref"])["label"] == "reference-RC"
        validate_form({"numbers": cells}, obj({"numbers": optical_cells_schema()}),
            lambda ref, ns: store.reference_subset([ref], plain(context.scope)) and store.get(ref)["record_type"] == ns)
        assert saved["selection"] == args
        assert saved["extraction"]["calculation_inputs"] == saved["calculation"]["input_snapshot"]
        assert len(saved["cells"]) == 2
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


@pytest.mark.parametrize("change,reason,operand_reason", [
    (lambda a: a["signals"].update(sample=None), "missing_sample_slope", "source_measurement_unreported"),
    (lambda a: a["calibration"].update(path_length=None), "missing_path_length", None),
    (lambda a: a["calibration"]["epsilon"]["qualification"].update(value="unknown", witnesses=[]), "missing_epsilon", None),
    (lambda a: a["signal_kind"].update(value="static_absorbance"), "missing_sample_slope", "optical_signal_not_slope"),
    (lambda a: a["blank_role"].update(value="component_omission"), "blank_role_not_background", None),
    (lambda a: a["blank_role"].update(value="condition_reference"), "blank_role_not_background", None),
    (lambda a: a["rate_window"].update(value="interval_mean_only"), "rate_interval_unestablished", None),
])
def test_valid_partials_preserve_raw_source_and_explicit_dependent_unknowns(tmp_path, change, reason, operand_reason):
    store, context, args = setup(tmp_path, covariance=False, change=change)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        row, = projected(repo, outcome, ["net_rate"])
        assert row["value"] is None and row["unavailable_reason"] == reason
        if operand_reason:
            assert operand_reason in row["operands"]["sample_slope"]["input_unavailable_reasons"]
        assert repo.read(row["sheet_ref"])["extraction"]["calibration"]["wavelength"]["value"] == 340
        assert row["covariance"]["status"] == "unknown"
    finally:
        store.close()


def test_epsilon_only_no_default_blank_or_path(tmp_path):
    def change(args):
        args["signals"] = {"sample": None, "blank": None}
        args["calibration"].update(path_length=None, wavelength=None)
    store, context, args = setup(tmp_path, covariance=False, change=change)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        out = repo.populate(context, args, "epsilon-only")
        saved = repo.read(out["result"]["sheet_ref"])
        assert saved["extraction"]["calculation_inputs"]["epsilon"] == 5
        assert projected(repo, out)[0]["value"] is None
    finally:
        store.close()


@pytest.mark.parametrize("mutation", [lambda r: r.update(value=99), lambda r: r.update(unit="uM2/min2"),
    lambda r: r["interpretations"]["blank_role"].update(value="condition_reference"),
    lambda r: r["operands"]["epsilon"].update(measurement_ref=None),
    lambda r: r["covariance"].update(status="estimated"), lambda r: r["context"]["molecule"].update(ref=None)])
def test_changed_typed_value_or_meaning_rejected(tmp_path, mutation):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        rows = projected(repo, out, ["net_rate"])
        mutation(rows[0])
        with pytest.raises(ContractError, match="differs_from_saved_cells"):
            repo.validate_returned_values(rows, permitted_record_refs=out["record_refs"])
    finally:
        store.close()


def test_saved_reopen_original_subset_forwarding_and_replay_forbid_all_source_io(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    repo = LiteratureOpticalRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    ref = outcome["result"]["sheet_ref"]
    rows = projected(repo, outcome, ["variance_net_rate"])
    parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={})
    repo.receive_cells(parent, rows, "delivery")
    source_artifacts = {store.get(r)["artifact_ref"] for r in context.received_record_refs}
    store.close()
    def forbidden(*_a, **_kw):
        raise AssertionError("Saved output must not read/reparse/recalculate sources")
    monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.read_optical_rate_operands", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_optical_storage.calculate_nadh_optical_rate", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs._number", forbidden)
    with Store(tmp_path) as reopened:
        get = reopened.get_artifact
        def saved_only(reference):
            assert reference not in source_artifacts, "scientific artifact reopened"
            return get(reference)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        repo = LiteratureOpticalRepository(reopened, context.run_id)
        changes = reopened.db.total_changes
        assert repo.read(ref)["selection"] == args
        assert repo.populate(context, args, "selected") == outcome
        assert projected(repo, outcome, ["variance_net_rate"]) == rows
        assert repo.received_cells(parent) == rows
        assert reopened.db.total_changes == changes
        repo.receive_cells(parent, rows, "delivery")
        assert repo.received_cells(parent) == rows
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=()), args, "selected")
        with pytest.raises(ContractError, match="operation_key_reused"):
            repo.populate(replace(context, assignment={**plain(context.assignment), "requested_optical_components": ["net_rate"]}), args, "selected")


def test_receipts_and_actual_assigned_page_source_ancestry_authorized(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=()), args, "no-receipt")
        other = store.put("source", {"provider": "other", "artifact_ref": store.artifact("unrelated"),
            "text_ref": None, "request_ref": None, "accession": None, "uri": None, "version": None, "retrieved_at": None}, origin="caller")["id"]
        page = replace(context, role="literature_page", path=(("literature_page", "page"),), assignment={"source_ref": other})
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(page, args, "wrong-ancestry")
        # A descendant covariance source with the correct original source is authorized.
        page = replace(page, assignment={"source_ref": args["source_ref"]})
        assert repo.populate(page, args, "valid-descendant")["status"] == "completed"
        assert store.db.execute("SELECT count(*) FROM literature_optical_operations").fetchone()[0] == 1
    finally:
        store.close()


def test_atomic_interruption_rolls_back_records_and_retry_uses_original_key(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        before = store.db.execute("SELECT count(*) FROM records").fetchone()[0]
        put = store.put
        def interrupt(kind, value, **kwargs):
            if kind == "source" and value.get("provider") == repo.provider:
                raise OSError("synthetic interruption")
            return put(kind, value, **kwargs)
        monkeypatch.setattr(store, "put", interrupt)
        with pytest.raises(OSError, match="interruption"):
            repo.populate(context, args, "original-key")
        assert store.db.execute("SELECT count(*) FROM records").fetchone()[0] == before
        assert store.db.execute("SELECT count(*) FROM literature_optical_operations").fetchone()[0] == 0
        monkeypatch.setattr(store, "put", put)
        outcome = repo.populate(context, args, "original-key")
        assert repo.populate(context, args, "original-key") == outcome
    finally:
        store.close()


@pytest.mark.parametrize("which", ["key", "tool", "scope", "outcome", "cell", "binding"])
def test_provider_label_and_forged_original_bindings_are_insufficient(tmp_path, which):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        original = store.get(outcome["result"]["sheet_ref"])
        request = json.loads(store.get_artifact(original["request_ref"]))
        payload = json.loads(store.get_artifact(original["artifact_ref"]))
        if which in ("key", "tool", "scope"):
            request[{"key": "operation_key", "tool": "selected_tool", "scope": "scope"}[which]] = {"x": 1} if which == "scope" else "forged"
        if which == "cell":
            payload["cells"]["net_rate"]["value"] = 100
        if which == "binding":
            payload["operand_bindings"]["epsilon"]["measurement_ref"] = None
        fields = {name: original[name] for name in ("provider", "accession", "uri", "text_ref", "version", "retrieved_at", "parent_source_refs")}
        fields.update(request_ref=store.artifact(canonical(request), "application/json"), artifact_ref=store.artifact(canonical(payload), "application/json"))
        fields["text_ref"] = fields["artifact_ref"]
        fake = store.put("source", fields, origin="tool", scope=plain(context.scope))["id"]
        if which in ("cell", "binding", "outcome"):
            # Even a forged table association must pass remaining saved links.
            forged = deepcopy(outcome)
            forged["result"]["sheet_ref"] = fake
            if which == "outcome":
                forged["operation_ref"] = "operation_forged"
            store.db.execute("UPDATE literature_optical_operations SET outcome=?", (canonical(forged),))
        with pytest.raises((ContractError, ValueError)):
            repo.read(fake)
        with pytest.raises(ContractError, match="run_mismatch"):
            LiteratureOpticalRepository(store, "stranger-run").read(original["id"])
    finally:
        store.close()


def test_foreign_sheet_cannot_expand_admitted_subset_and_forged_receipt_rejects(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        q = projected(repo, outcome, ["net_rate"])
        v = projected(repo, outcome, ["variance_net_rate"])
        receiver = replace(context, episode_id="other-literature-parent", received_record_refs=tuple(outcome["record_refs"]))
        assert repo.fact_cells(receiver, [q[0]["sheet_ref"]], components=["net_rate", "variance_net_rate"]) == []
        repo.receive_cells(receiver, q, "admitted-original-q")
        assert repo.fact_cells(receiver, [q[0]["sheet_ref"]], components=["net_rate", "variance_net_rate"]) == q
        store.db.execute("UPDATE literature_optical_received SET cells=?", (canonical(v),))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            repo.received_cells(receiver)
    finally:
        store.close()


def test_representation_metadata_mismatch_and_unavailable_exact_text_are_rejected(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path, covariance=False)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        args["signals"]["sample"]["measurement"]["number"]["witness"]["representation"] = "text"
        outcome = repo.populate(context, args, "text-selected")
        get = store.get
        def metadata_changed(ref):
            record = get(ref)
            if ref == args["source_ref"]:
                record["text_ref"] = None
            return record
        monkeypatch.setattr(store, "get", metadata_changed)
        with pytest.raises(ContractError, match="source_mismatch"):
            repo.read(outcome["result"]["sheet_ref"])
        with pytest.raises(ContractError, match="representation_unavailable"):
            repo.populate(context, args, "new-text-attempt")
    finally:
        store.close()


def test_same_token_reuse_preserves_physical_measurement_and_distinct_owner_bindings(tmp_path):
    store, context, args = setup(tmp_path, covariance=False)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        args["signals"]["blank"] = deepcopy(args["signals"]["sample"])
        outcome = repo.populate(context, args, "same-token")
        row, = projected(repo, outcome, ["net_rate"])
        assert row["value"] == 0
        forged = deepcopy(row)
        forged["value"] = False
        with pytest.raises(ContractError, match="differs_from_saved_cells"):
            repo.validate_returned_values([forged], permitted_record_refs=outcome["record_refs"])
        assert row["operands"]["sample_slope"]["local_reuse_ref"] == row["operands"]["blank_slope"]["local_reuse_ref"]
        assert row["operands"]["sample_slope"]["semantic_owner_ref"] != row["operands"]["blank_slope"]["semantic_owner_ref"]
        saved = repo.read(row["sheet_ref"])
        assert saved["extraction"]["signals"]["sample"]["measurement_key"] == saved["extraction"]["signals"]["blank"]["measurement_key"]
    finally:
        store.close()


def rewrite_selected_payload(store, outcome, mutate):
    """Synthetic corruption reaches the detached validator past provider labels."""
    original = store.get(outcome["result"]["sheet_ref"])
    payload = json.loads(store.get_artifact(original["artifact_ref"]))
    mutate(payload)
    fields = {key: original[key] for key in ("provider", "accession", "uri", "request_ref", "version", "retrieved_at", "parent_source_refs")}
    artifact = store.artifact(json.dumps(payload), "application/json")
    fields.update(artifact_ref=artifact, text_ref=artifact)
    ref = store.put("source", fields, origin="tool")["id"]
    changed = deepcopy(outcome)
    changed["result"]["sheet_ref"] = ref
    changed["record_refs"] = [ref if old == original["id"] else old for old in changed["record_refs"]]
    store.db.execute("UPDATE literature_optical_operations SET outcome=?", (canonical(changed),))
    return ref


def test_zero_operand_snapshot_cannot_be_spoofed_with_boolean_false(tmp_path):
    text = (TEXT + SUFFIX).replace("-0.012 AU/min", "0.0 AU/min")
    store, context, args = setup(tmp_path, text=text, operands={"sample": ("0.0 AU/min", "0.0", "AU/min")})
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        out = repo.populate(context, args, "zero-sample")
        fake = rewrite_selected_payload(store, out, lambda p: p["calculation"]["input_snapshot"].update(sample_slope=False))
        with pytest.raises(ContractError, match="saved_calculation_mismatch"):
            repo.read(fake)
    finally:
        store.close()


@pytest.mark.parametrize("invalid", [10**400, float("nan"), float("inf"), True])
def test_adversarial_saved_cell_is_deliberate_structured_failure(tmp_path, invalid):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        def corrupt(payload):
            payload["calculation"]["net_depletion_rate"]["value"] = invalid
            payload["cells"]["net_rate"]["value"] = invalid
        fake = rewrite_selected_payload(store, out, corrupt)
        with pytest.raises(ContractError, match="saved_cell_mismatch"):
            repo.read(fake)
    finally:
        store.close()


@pytest.mark.parametrize("mutation", ["bool_offset", "wrong_id"])
def test_saved_binding_authenticates_exact_types_and_derived_record_identity(tmp_path, mutation):
    # This condition genuinely starts at byte0, so False would compare equal to
    # its valid zero offset under ordinary Python nested equality.
    def change(args):
        original = args["relation"]["witnesses"][0]
        args["condition"] = {**original, "start": 0, "end": len("Synthetic"), "quote": "Synthetic"}
    store, context, args = setup(tmp_path, change=change)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        out = repo.populate(context, args, "selected")
        saved = repo.read(out["result"]["sheet_ref"])
        ref = saved["context_bindings"]["condition"]
        record = store.get(ref)
        if mutation == "bool_offset":
            assert record["anchor"]["start"] == 0
            record["anchor"]["start"] = False
        else:
            record["id"] = "context_" + "a" * 64
        store.db.execute("UPDATE records SET data=? WHERE id=?", (json.dumps(record), ref))
        with pytest.raises(ContractError, match="binding_mismatch"):
            repo.read(out["result"]["sheet_ref"])
    finally:
        store.close()


def test_repository_honors_explicit_bound_scope_guard_before_source_access(tmp_path, monkeypatch):
    """Injected scope port guard; Store paper sources themselves are reusable.

    This covers the adapter's actual rejection branch, not a claim that source
    records currently have target roots in Store. Receipt/assigned-page tests
    above exercise the ordinary unmodified Store source authorization path.
    """
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        original = store.reference_subset
        def bound_guard(refs, scope=None):
            return [] if args["source_ref"] in refs else original(refs, scope)
        monkeypatch.setattr(store, "reference_subset", bound_guard)
        with pytest.raises(ContractError, match="source_outside_scope"):
            repo.populate(context, args, "scope-denied")
        assert store.db.execute("SELECT count(*) FROM literature_optical_operations").fetchone()[0] == 0
    finally:
        store.close()


def test_saved_qualified_operand_boolean_is_not_integer_one(tmp_path):
    def qualified(args):
        args["calibration"]["epsilon"]["qualification"]["value"] = "source_qualified_approximate"
    store, context, args = setup(tmp_path, change=qualified)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        out = repo.populate(context, args, "qualified")
        assert repo.read(out["result"]["sheet_ref"])["operand_bindings"]["epsilon"]["approximate"] is True
        fake = rewrite_selected_payload(store, out, lambda p: p["operand_bindings"]["epsilon"].update(approximate=1))
        with pytest.raises(ContractError, match="binding_mismatch"):
            repo.read(fake)
    finally:
        store.close()


def test_original_outcome_zero_cell_cannot_be_relabelled_false(tmp_path):
    store, context, args = setup(tmp_path, covariance=False)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        args["signals"]["blank"] = deepcopy(args["signals"]["sample"])
        out = repo.populate(context, args, "zero-rate")
        assert repo.read(out["result"]["sheet_ref"])["cells"]["net_rate"]["value"] == 0.0
        altered = deepcopy(out)
        altered["result"]["cells"]["net_rate"]["value"] = False
        store.db.execute("UPDATE literature_optical_operations SET outcome=?", (canonical(altered),))
        with pytest.raises(ContractError, match="outcome_mismatch"):
            repo.read(out["result"]["sheet_ref"])
    finally:
        store.close()
