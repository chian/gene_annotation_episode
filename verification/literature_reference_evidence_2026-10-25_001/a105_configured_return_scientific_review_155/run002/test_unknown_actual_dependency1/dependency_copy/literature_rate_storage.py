"""Persist source-level rate sheets without reacquisition or target scoring.

The repository is an adapter for a selected operation, not an episode or a
workflow. Ordinary runtime action/receipt accounting remains with its caller.
"""
from __future__ import annotations

import json
import hashlib
from copy import deepcopy

from .communication import plain
from .domain import ContractError, canonical, identity
from .literature_experimental_contracts import RATE_UNITS
from .literature_rate_reader import read_rate_table
from .literature_rate_calculations import populate_rate_contrast
from .literature_rate_native_inputs import NATIVE_BINDINGS, NATIVE_REASONS


PROVIDER = "literature.a105.rate_population"
COMPONENTS = ("reference_rate", "test_rate", "rate_difference", "retained_fraction",
              "fractional_decrease", "reference_mean_se", "test_mean_se", "difference_se",
              "signed_profile_log_ratio", "source_signed_index")
UNAVAILABLE_REASONS = ("nonfinite_calculation", "missing_reference_arm", "missing_test_arm",
    "conflicting_source_identity", "ambiguous_reference_arm", "ambiguous_test_arm",
    "source_measurement_unavailable", "censored_measurement", "conflicting_measurement",
    "mean_uncertainty_unreported", "observation_model_unspecified", "measurement_count_unreported",
    "insufficient_measurement_count", "positive_sd_required", "zero_reference_rate",
    "dependence_unknown", "profile_requires_sample_sd", "numerical_model_range")
NATIVE_RECORD_VERSION = "literature_rate_population_record_v2"


class LiteratureRateRepository:
    """Use one application's existing Store and explicit run/episode identities."""

    provider = PROVIDER
    components = COMPONENTS
    record_version = "literature_rate_population_record_v1"
    operations_table = "literature_rate_operations"
    received_table = "literature_rate_received"
    binding_fields = ("assayed_subject_ref", "experiment_ref", "reference_condition_ref",
                      "test_condition_ref", "endpoint_ref", "normalization_ref")

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id
        store.db.execute(f"""CREATE TABLE IF NOT EXISTS {self.operations_table}(
            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
            signature TEXT NOT NULL, outcome TEXT NOT NULL,
            PRIMARY KEY(run_id,episode_id,operation_key))""")
        store.db.execute(f"""CREATE TABLE IF NOT EXISTS {self.received_table}(
            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
            cells TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))""")
    @property
    def _delivery_table(self):
        return self.received_table.removesuffix("_received") + "_delivery_bindings"

    def _delivery_binding(self, context, operation_key):
        installed = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (self._delivery_table,)).fetchone()
        return self.store.db.execute(f"SELECT cells_digest FROM {self._delivery_table} WHERE "
            "run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone() if installed else None

    def _install_delivery_bindings(self):
        # New receipt state is created only inside the actual incoming receive
        # transaction. Old authentic runtime state can remain fully read-only.
        # Optical004 already uses this exact per-view table/digest naming.
        self.store.db.execute(f"""CREATE TABLE IF NOT EXISTS {self._delivery_table}(
            run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
            cells_digest TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))""")

    def _delivery_digest(self, cells):
        kind = self.received_table.removeprefix("literature_").removesuffix("_received")
        return identity(kind + "_admitted_cells", cells)

    def _runtime_delivery_cells(self, context, operation_key):
        """Authenticate runtime admission; other keys are a trusted manual API.

        A saved digest is not proof that runtime admitted the subset. Its actual
        successful form and original child contract supply that proof. Reading
        an old authentic runtime receipt needs no backfilled binding or history.
        """
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        prefix = self.run_id + ":" + context.episode_id + ":"
        if not operation_key.startswith(prefix) and not operation_key.endswith(":typed_form"):
            return None
        suffix = operation_key[len(prefix):].split(":") if operation_key.startswith(prefix) else []
        if (len(suffix) != 2 or not suffix[0].isascii() or not suffix[0].isdigit()
                or suffix[1] != "typed_form"):
            raise ContractError("literature_delivery_binding_mismatch")
        try:
            index = int(suffix[0])
        except ValueError as error:
            raise ContractError("literature_delivery_binding_mismatch") from error
        if index > 2**63 - 1 or str(index) != suffix[0]:
            raise ContractError("literature_delivery_binding_mismatch")
        installed = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_report_attempts'").fetchone()
        attempt = self.store.db.execute("SELECT form,contract,failure,child_episode_id,delivery_ref FROM runtime_report_attempts "
            "WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (self.run_id, context.episode_id, index)).fetchone() if installed else None
        if attempt is None or attempt["form"] is None or attempt["failure"] is not None:
            raise ContractError("literature_delivery_binding_mismatch")
        try:
            form, contract = json.loads(attempt["form"]), json.loads(attempt["contract"])
            if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_episodes'").fetchone() is None:
                raise ContractError("literature_delivery_binding_mismatch")
            child = self.store.db.execute("SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.run_id, attempt["child_episode_id"])).fetchone()
            if child is None:
                raise ContractError("literature_delivery_binding_mismatch")
            original_contract = json.loads(child["request"])["report_contract"]
            if canonical(original_contract) != canonical(contract):
                # A selected report repair can legitimately revise the form.
                # Authenticate that actual decision and its original delivery,
                # rather than pretending it was the child's initial contract.
                installed_action = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone()
                action = self.store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                    (self.run_id, context.episode_id, index)).fetchone() if installed_action else None
                installed_decision = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_model_calls'").fetchone()
                # Report repair runs before ActionLeaf/action publication. Read
                # only its public selected choice, never provider history,
                # request text, complete responses or private reasoning.
                decision = self.store.db.execute("SELECT CASE WHEN json_valid(response) THEN response -> '$.selection' END AS selected "
                    "FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=? AND purpose='decision'",
                    (self.run_id, context.episode_id, index)).fetchone() if installed_decision else None
                selected = json.loads(action["action"]) if action else None
                chosen = json.loads(decision["selected"]) if decision and decision["selected"] is not None else None
                if selected is not None and chosen is not None and canonical(selected) != canonical(chosen):
                    raise ContractError("literature_delivery_binding_mismatch")
                selected = selected if selected is not None else chosen
                if not isinstance(selected, dict):
                    raise ContractError("literature_delivery_binding_mismatch")
                prior = self.store.db.execute("SELECT child_episode_id,contract FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? "
                    "AND delivery_ref=? AND decision_index<? ORDER BY decision_index LIMIT 1",
                    (self.run_id, context.episode_id, selected.get("delivery_ref"), index)).fetchone()
                if (selected.get("kind") != "redeliver_report" or prior is None
                        or attempt["delivery_ref"] != selected.get("delivery_ref")
                        or prior["child_episode_id"] != attempt["child_episode_id"]
                        or canonical(json.loads(prior["contract"])) != canonical(original_contract)
                        or selected.get("purpose") != contract["decision"]
                        or canonical(json.loads(selected["schema_json"])) != canonical(contract["measurements"]["schema"])):
                    raise ContractError("literature_delivery_binding_mismatch")
            namespace = self.received_table.removesuffix("_received") + "_cells"
            fields = [name for name, node in contract["measurements"]["schema"]["properties"].items()
                if node.get("x-source") == namespace]
            if not fields:
                raise ContractError("literature_delivery_binding_mismatch")
            return [row for name in fields for row in form[name]]
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError("literature_delivery_binding_mismatch") from error

    def populate(self, context, arguments, operation_key):
        """Parse the exact selected retained table and save this action atomically.

        The source must have been received by this episode, not merely exist
        somewhere in shared state. This operation performs no network call,
        scientific interpretation, receipt admission or controller observation.
        """
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        keys = {"source_ref", "source_representation", "table_kind", "delimiter", "subject",
                "experiment", "reference_arm", "test_arm", "reference_condition",
                "test_condition", "dependence", "observation_model"}
        if not isinstance(args, dict) or set(args) != keys:
            raise ContractError("literature_rate_arguments_required")
        if any(not isinstance(value, str) or not value for value in args.values()):
            raise ContractError("literature_rate_arguments_required")
        source_ref = args["source_ref"]
        if source_ref not in context.received_record_refs:
            raise ContractError("literature_source_not_received")
        if not self.store.reference_subset([source_ref], plain(context.scope)):
            raise ContractError("literature_source_outside_scope")
        signature = canonical({"arguments": args, "scope": plain(context.scope)})
        saved = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if saved is not None:
            if saved["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            return json.loads(saved["outcome"])
        source = self.store.get(source_ref)
        if source["record_type"] != "source":
            raise ContractError("literature_source_required")
        if args["source_representation"] not in ("original", "text"):
            raise ContractError("literature_table_representation_required")
        artifact = (source["artifact_ref"] if args["source_representation"] == "original"
                    else source.get("text_ref"))
        if artifact is None:
            raise ContractError("literature_table_representation_unavailable")
        try:
            text = self.store.get_artifact(artifact).decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContractError("literature_utf8_table_required") from error
        extraction = read_rate_table({"source_ref": source_ref, "artifact_ref": artifact,
            "text": text, "representation": args["table_kind"], "delimiter": args["delimiter"]},
            expected_subject=args["subject"], expected_experiment=args["experiment"])
        sheet = populate_rate_contrast(extraction, **{key: args[key] for key in (
            "reference_arm", "test_arm", "reference_condition", "test_condition",
            "dependence", "observation_model")})
        payload = {"version": "literature_rate_population_record_v1",
                   "input_source_ref": source_ref, "input_artifact_ref": artifact, "sheet": sheet}
        with self.store.transaction():
            newly_created = []

            def publish(kind, value):
                # These are immutable source/reference/context/term records,
                # with Store's ordinary content identity, not revisioned claims.
                candidate = identity(kind, {"origin": "tool", "record": value})
                existed = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (candidate,)).fetchone()
                row = self.store.put(kind, value, origin="tool", scope=plain(context.scope))
                if existed is None:
                    newly_created.append(row["id"])
                return row

            # These references identify source assertions and experimental
            # conditions. They do not assert target identity or activity.
            subject = publish("reference", {"reference_type": "assay", "source_ref": source_ref,
                "accession": identity("source_assay", {"source_ref": source_ref, "subject": args["subject"]}),
                "label": args["subject"], "sequence_ref": None, "molecule": None, "length": None,
                "term_refs": [], "context_refs": []}) if extraction["rows"] else None
            experiment = publish("reference", {"reference_type": "assay", "source_ref": source_ref,
                "accession": identity("source_experiment", {"source_ref": source_ref, "experiment": args["experiment"]}),
                "label": args["experiment"], "sequence_ref": None, "molecule": None, "length": None,
                "term_refs": [], "context_refs": []}) if extraction["rows"] else None
            bindings = {"assayed_subject_ref": subject["id"] if subject else None,
                        "experiment_ref": experiment["id"] if experiment else None}
            for side in ("reference", "test"):
                row = next((row for row in extraction["rows"]
                    if row["arm"] == args[side + "_arm"]
                    and row["condition"] == args[side + "_condition"]), None)
                bindings[side + "_condition_ref"] = (publish("context", {
                    "context_type": "assay_condition", "name": row["condition"], "source_ref": source_ref,
                    "attributes": [], "related_refs": [subject["id"], experiment["id"]]})["id"] if row else None)
            for field in ("endpoint", "normalization"):
                label = sheet["comparison"][field]
                bindings[field + "_ref"] = (publish("term", {
                    "namespace": "literature_" + field, "accession": identity(field, {"source_ref": source_ref, "label": label}),
                    "label": label, "term_type": "other", "source_ref": source_ref, "anchor": None})["id"] if label else None)
            payload["experimental_bindings"] = bindings
            sheet_artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(canonical({"run_id": self.run_id,
                "episode_id": context.episode_id, "operation_key": operation_key,
                "arguments": args}), "application/json")
            record = publish("source", {"provider": PROVIDER, "accession": None,
                "uri": None, "artifact_ref": sheet_artifact, "text_ref": sheet_artifact,
                "request_ref": request_ref, "version": payload["version"],
                "retrieved_at": None, "parent_source_refs": [source_ref]})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": [record["id"], *dict.fromkeys(ref for ref in bindings.values() if ref)],
                "changed_record_refs": newly_created,
                "result": {"sheet_ref": record["id"], "cells": sheet["cells"]}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _native_provenance(self, scope, reference):
        if not self.store.reference_subset([reference], plain(scope)):
            raise ContractError("literature_source_outside_scope")
        source = self.store.get(reference)
        if source["record_type"] != "source":
            raise ContractError("literature_source_required")
        return source

    def _native_source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError("literature_source_not_received")
        source = self._native_provenance(context.scope, reference)
        page = context.assignment if context.role == "literature_page" else context.assignment.get("page")
        if page:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                row = self._native_provenance(context.scope, current)
                if current == page["source_ref"]:
                    break
                pending.extend(row.get("parent_source_refs", ()))
            else:
                raise ContractError("literature_reading_outside_assigned_source")
        return source

    def populate_native(self, context, arguments, operation_key):
        """Populate the same cells from original selected, source-bound operands."""
        from .domain import validate_schema
        from .literature_rate_native_inputs import read_rate_source_inputs, rate_source_population_schema
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        args = plain(arguments)
        validate_schema(args, rate_source_population_schema())
        signature = canonical({"input_mode": "native_source_spans", "arguments": args, "scope": plain(context.scope)})
        old = self.store.db.execute(f"SELECT signature,outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old["signature"] != signature:
                raise ContractError("operation_key_reused_for_different_work")
            outcome = json.loads(old["outcome"])
            saved = self.read(outcome["result"]["sheet_ref"])
            for reference in saved["direct_input_source_refs"]:
                self._native_source(context, reference)
            for reference in saved["input_source_refs"]:
                self._native_provenance(context.scope, reference)
            return outcome

        def read_source(reference, representation):
            source = self._native_source(context, reference)
            artifact = source["artifact_ref"] if representation == "original" else source.get("text_ref")
            if artifact is None:
                raise ContractError("literature_source_representation_unavailable")
            return {"artifact_ref": artifact, "content": self.store.get_artifact(artifact)}

        extraction = read_rate_source_inputs(args, read_source=read_source)
        from .literature_rate_domains import VERSION as DOMAIN_VERSION
        rows = {row["arm"]: row for row in extraction["rows"]}
        sheet = populate_rate_contrast(extraction, reference_arm="reference", test_arm="test",
            reference_condition=rows.get("reference", {}).get("condition"),
            test_condition=rows.get("test", {}).get("condition"),
            dependence=args["dependence"]["value"], observation_model=args["observation_model"]["value"],
            native_bound_version=DOMAIN_VERSION)
        direct = extraction["native_context"]["source_refs"]
        parents, seen = list(direct), set(direct)
        cursor = 0
        while cursor < len(parents):
            source = self._native_provenance(context.scope, parents[cursor])
            cursor += 1
            for reference in source.get("parent_source_refs", ()):
                self._native_provenance(context.scope, reference)
                if reference not in seen:
                    seen.add(reference)
                    parents.append(reference)
        root = self._native_source(context, args["source_ref"])
        payload = {"version": NATIVE_RECORD_VERSION, "input_source_ref": args["source_ref"],
            "input_artifact_ref": root["artifact_ref"], "direct_input_source_refs": direct,
            "input_source_refs": parents, "native_selection": args, "sheet": sheet}
        with self.store.transaction():
            created = []
            def publish(kind, value):
                key = identity(kind, {"origin": "tool", "record": value})
                exists = self.store.db.execute("SELECT 1 FROM records WHERE id=?", (key,)).fetchone()
                record = self.store.put(kind, value, origin="tool", scope=plain(context.scope))
                if exists is None:
                    created.append(record["id"])
                return record
            def reference(witness, kind):
                if witness is None:
                    return None
                return publish("reference", {"reference_type": "assay", "source_ref": witness["source_ref"],
                    "accession": identity("native_rate_" + kind, witness), "label": witness["quote"],
                    "sequence_ref": None, "molecule": None, "length": None,
                    "term_refs": [], "context_refs": []})["id"]
            native_bindings = {}
            for role in ("reference", "test"):
                meanings = rows.get(role, {}).get("source", {}).get("meanings", {})
                for name in ("subject", "construct", "preparation"):
                    native_bindings[role + "_" + name + "_ref"] = reference(meanings.get(name), name)
            shared = extraction["native_context"]["comparison"]["subject_relation"]["value"] == "same"
            bindings = {"assayed_subject_ref": (native_bindings["reference_subject_ref"] or native_bindings["test_subject_ref"]) if shared else None,
                "experiment_ref": reference(extraction["native_context"]["experiment"], "experiment")}
            for role in ("reference", "test"):
                meanings = rows.get(role, {}).get("source", {}).get("meanings", {})
                condition = meanings.get("condition")
                bindings[role + "_condition_ref"] = (publish("context", {
                    "context_type": "assay_condition", "name": condition["quote"],
                    "source_ref": condition["source_ref"], "attributes": [],
                    "related_refs": list(dict.fromkeys(ref for ref in (
                        native_bindings[role + "_subject_ref"], native_bindings[role + "_construct_ref"],
                        native_bindings[role + "_preparation_ref"], bindings["experiment_ref"]) if ref))})["id"] if condition else None)
            for field in ("endpoint", "normalization"):
                relation = extraction["native_context"]["comparison"][field + "_relation"]["value"]
                witness = next((row["source"]["meanings"][field] for row in rows.values()
                                if row["source"]["meanings"][field]), None) if relation == "same" else None
                bindings[field + "_ref"] = (publish("term", {"namespace": "literature_" + field,
                    "accession": identity("native_rate_" + field, witness), "label": witness["quote"],
                    "term_type": "other", "source_ref": witness["source_ref"], "anchor": None})["id"] if witness else None)
            payload["experimental_bindings"] = bindings
            payload["native_bindings"] = native_bindings
            sheet_artifact = self.store.artifact(canonical(payload), "application/json")
            request_ref = self.store.artifact(canonical({"run_id": self.run_id,
                "episode_id": context.episode_id, "operation_key": operation_key,
                "arguments": args}), "application/json")
            record = publish("source", {"provider": PROVIDER, "accession": None, "uri": None,
                "artifact_ref": sheet_artifact, "text_ref": sheet_artifact, "request_ref": request_ref,
                "version": NATIVE_RECORD_VERSION, "retrieved_at": None, "parent_source_refs": parents})
            outcome = {"status": "completed", "operation_ref": identity("operation", {
                "run_id": self.run_id, "episode_id": context.episode_id, "key": operation_key}),
                "record_refs": [record["id"], *dict.fromkeys(ref for ref in (
                    *bindings.values(), *native_bindings.values()) if ref)], "changed_record_refs": created,
                "result": {"sheet_ref": record["id"], "cells": sheet["cells"]}, "feedback": None}
            self.store.db.execute(f"INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        """Read original saved cells without scientific source IO or fitting.

        The rate writer can reopen its v1/v2 payloads. Return views separately
        enforce their exact projection version; subclass providers keep their
        original independent version contracts.
        """
        source = self.store.get(sheet_ref)
        if (source["record_type"] != "source" or source["provider"] != self.provider
                or source["origin"] != "tool" or source["request_ref"] is None):
            raise ContractError("literature_rate_sheet_required")
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        if request.get("run_id") != self.run_id:
            raise ContractError("literature_rate_sheet_run_mismatch")
        operation = self.store.db.execute(f"SELECT outcome FROM {self.operations_table} "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request.get("episode_id"), request.get("operation_key"))).fetchone()
        if (operation is None or json.loads(operation["outcome"]).get("result", {}).get("sheet_ref") != sheet_ref):
            raise ContractError("literature_sheet_not_selected_output")
        payload = json.loads(self.store.get_artifact(source["artifact_ref"]))
        native = self.provider == PROVIDER and payload.get("version") == NATIVE_RECORD_VERSION
        # An adapter can explicitly retain exact old payloads while publishing
        # a newer version. Reading never upgrades or recalculates those cells.
        readable_versions = getattr(self, "readable_record_versions", (self.record_version,))
        if not native and payload.get("version") not in readable_versions:
            raise ContractError("literature_rate_sheet_version_mismatch")
        if (hasattr(self, "readable_record_versions")
                and source.get("version") != payload.get("version")):
            raise ContractError("literature_rate_sheet_version_mismatch")
        if source.get("parent_source_refs") != payload.get("input_source_refs", [payload["input_source_ref"]]):
            raise ContractError("literature_rate_sheet_source_mismatch")
        if request.get("arguments", {}).get("source_ref") != payload["input_source_ref"]:
            raise ContractError("literature_rate_sheet_source_mismatch")
        if native:
            self._validate_native_saved(payload, request, json.loads(operation["outcome"]))
        return payload

    def _validate_native_saved(self, payload, request, outcome):
        """Check original saved associations without rereading scientific sources."""
        from .literature_rate_native_inputs import validate_native_extraction, validate_native_selection
        if (payload.get("native_selection") != request.get("arguments")
                or outcome.get("result", {}).get("cells") != payload["sheet"]["cells"]):
            raise ContractError("literature_native_rate_saved_mismatch")
        extraction = validate_native_extraction(payload["sheet"]["extraction"])
        validate_native_selection(request["arguments"], extraction)
        trace = payload["sheet"].get("native_bound_arithmetic")
        if "native_bound_arithmetic" in payload["sheet"]:
            from .literature_rate_domains import VERSION as DOMAIN_VERSION, native_domain_trace, apply_native_domains
            if not isinstance(trace, dict) or trace.get("version") != DOMAIN_VERSION:
                raise ContractError("literature_native_rate_bound_version_unsupported")
            import math
            for cell in payload["sheet"]["cells"].values():
                for field in ("value", "threshold"):
                    value = cell.get(field)
                    try:
                        valid = value is None or type(value) in (int, float) and math.isfinite(value)
                    except (OverflowError, ValueError):
                        valid = False
                    if not valid:
                        raise ContractError("literature_native_rate_saved_numeric_type_mismatch")
            expected_trace = native_domain_trace(extraction, payload["sheet"]["cells"])
            if canonical(trace) != canonical(expected_trace):
                raise ContractError("literature_native_rate_saved_domain_mismatch")
        rows = {row["arm"]: row for row in extraction["rows"]}
        for component in self.components:
            row = rows.get("reference" if component == "reference_rate" else
                           "test" if component == "test_rate" else None)
            number = row["source"]["number"] if row else None
            relation = number["relation"] if number else "point"
            censored = relation != "point"
            expected = {"threshold": row["value"] if censored else None,
                        "bound": relation if censored else "none"}
            cell = payload["sheet"]["cells"][component]
            if trace is not None and component in ("rate_difference", "retained_fraction", "fractional_decrease"):
                original = {name: deepcopy(value) for name, value in payload["sheet"]["cells"].items()}
                for value in original.values():
                    value.update(threshold=None, bound="none")
                apply_native_domains(original, trace)
                expected = {key: original[component][key] for key in ("threshold", "bound")}
                domain = trace["components"][component]["reported_domain"]
                if cell["input_rows"] != trace["components"][component]["input_rows"]:
                    raise ContractError("literature_native_rate_saved_domain_mismatch")
                image = trace["components"][component]["image"]
                exact_point = image is not None and image["lower"] is not None and image["lower"] == image["upper"]
                if domain["failure"] is not None:
                    if (cell["value"] is not None or cell["status"] != "unavailable"
                            or cell["unavailable_reason"] != domain["failure"]):
                        raise ContractError("literature_native_rate_saved_domain_mismatch")
                elif not exact_point:
                    if cell["value"] is not None or cell["status"] != "unavailable":
                        raise ContractError("literature_native_rate_saved_domain_mismatch")
                    if cell["unavailable_reason"] != "censored_measurement":
                        raise ContractError("literature_native_rate_saved_domain_mismatch")
                else:
                    from fractions import Fraction
                    exact = image["lower"]
                    identified = float(Fraction(int(exact["numerator"]), int(exact["denominator"])))
                    if cell["value"] != identified or cell["status"] != "populated" or cell["unavailable_reason"] is not None:
                        raise ContractError("literature_native_rate_saved_domain_mismatch")
            if (not set(expected).issubset(cell)
                    or canonical({key: cell[key] for key in expected}) != canonical(expected)):
                raise ContractError("literature_native_rate_saved_bounds_mismatch")
        context = extraction["native_context"]
        if context["source_refs"] != payload["direct_input_source_refs"]:
            raise ContractError("literature_native_rate_saved_mismatch")
        root = self.store.get(payload["input_source_ref"])
        if payload["input_artifact_ref"] != root["artifact_ref"]:
            raise ContractError("literature_native_rate_source_mismatch")
        def witnesses(value):
            if isinstance(value, dict):
                if set(("source_ref", "representation", "start", "end", "quote", "artifact_ref")) == set(value):
                    yield value
                else:
                    for child in value.values():
                        yield from witnesses(child)
            elif isinstance(value, list):
                for child in value:
                    yield from witnesses(child)
        for witness in witnesses(extraction):
            source = self.store.get(witness["source_ref"])
            artifact = source["artifact_ref"] if witness["representation"] == "original" else source.get("text_ref")
            if artifact != witness["artifact_ref"] or witness["source_ref"] not in payload["direct_input_source_refs"]:
                raise ContractError("literature_native_rate_source_mismatch")
        rows = {row["arm"]: row for row in extraction["rows"]}
        bindings = payload["native_bindings"]
        if set(bindings) != set(NATIVE_BINDINGS):
            raise ContractError("literature_native_rate_bindings_mismatch")
        def expected_reference(witness, kind):
            if witness is None:
                return None
            value = {"reference_type": "assay", "source_ref": witness["source_ref"],
                "accession": identity("native_rate_" + kind, witness), "label": witness["quote"],
                "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": []}
            reference = identity("reference", {"origin": "tool", "record": value})
            actual = self.store.get(reference)
            if (actual.get("record_type") != "reference" or actual.get("origin") != "tool"
                    or any(actual.get(key) != child for key, child in value.items())):
                raise ContractError("literature_native_rate_bindings_mismatch")
            return reference
        for role in ("reference", "test"):
            meanings = rows.get(role, {}).get("source", {}).get("meanings", {})
            for name in ("subject", "construct", "preparation"):
                ref = bindings[role + "_" + name + "_ref"]
                if ref != expected_reference(meanings.get(name), name):
                    raise ContractError("literature_native_rate_bindings_mismatch")
                if ref is not None:
                    self.store.get(ref)
        common = payload["experimental_bindings"]
        shared = context["comparison"]["subject_relation"]["value"] == "same"
        expected_subject = (bindings["reference_subject_ref"] or bindings["test_subject_ref"]) if shared else None
        if (common["assayed_subject_ref"] != expected_subject
                or common["experiment_ref"] != expected_reference(context["experiment"], "experiment")):
            raise ContractError("literature_native_rate_bindings_mismatch")
        if set(common) != set(self.binding_fields):
            raise ContractError("literature_native_rate_bindings_mismatch")
        def expected_record(kind, value):
            reference = identity(kind, {"origin": "tool", "record": value})
            actual = self.store.get(reference)
            if (actual.get("record_type") != kind or actual.get("origin") != "tool"
                    or any(actual.get(key) != child for key, child in value.items())):
                raise ContractError("literature_native_rate_bindings_mismatch")
            return reference
        for role in ("reference", "test"):
            meanings = rows.get(role, {}).get("source", {}).get("meanings", {})
            condition = meanings.get("condition")
            expected = (expected_record("context", {"context_type": "assay_condition",
                "name": condition["quote"], "source_ref": condition["source_ref"], "attributes": [],
                "related_refs": list(dict.fromkeys(ref for ref in (
                    bindings[role + "_subject_ref"], bindings[role + "_construct_ref"],
                    bindings[role + "_preparation_ref"], common["experiment_ref"]) if ref))}) if condition else None)
            if common[role + "_condition_ref"] != expected:
                raise ContractError("literature_native_rate_bindings_mismatch")
        for field in ("endpoint", "normalization"):
            relation = context["comparison"][field + "_relation"]["value"]
            witness = next((row["source"]["meanings"][field] for row in rows.values()
                            if row["source"]["meanings"][field]), None) if relation == "same" else None
            expected = (expected_record("term", {"namespace": "literature_" + field,
                "accession": identity("native_rate_" + field, witness), "label": witness["quote"],
                "term_type": "other", "source_ref": witness["source_ref"], "anchor": None}) if witness else None)
            if common[field + "_ref"] != expected:
                raise ContractError("literature_native_rate_bindings_mismatch")

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        """Copy requested saved cells, never compose prose or recompute a score."""
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple)) or len(set(components)) != len(components)
                or any(name not in self.components for name in components)):
            raise ContractError("literature_rate_component_selection_invalid")
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            metadata = self.store.get(reference)
            if (self.provider == PROVIDER and metadata.get("provider") == PROVIDER
                    and metadata.get("version") != self.record_version):
                raise ContractError("literature_rate_projection_version_mismatch")
            saved = self.read(reference)
            if self.provider == PROVIDER and saved["version"] != self.record_version:
                raise ContractError("literature_rate_projection_version_mismatch")
            for name in components:
                cell = saved["sheet"]["cells"][name]
                result.append({"sheet_ref": reference, "evidence_source_ref": saved["input_source_ref"],
                    **{key: saved.get("experimental_bindings", {}).get(key) for key in self.binding_fields},
                    "component": name, "value": cell["value"], "unit": cell["unit"],
                    "status": cell["status"], "origin": cell["origin"],
                    "unavailable_reason": cell["unavailable_reason"],
                    "conditional_on": list(cell["conditional_on"])})
                if self.provider == PROVIDER and saved.get("version") == NATIVE_RECORD_VERSION:
                    result[-1].update(saved["native_bindings"], approximate=cell["approximate"],
                                     threshold=cell["threshold"], bound=cell["bound"])
        return result

    def source_projection(self):
        """A closed native return view over the same saved numerical operations."""
        if self.provider != PROVIDER or self.operations_table != "literature_rate_operations":
            raise ContractError("native_rate_return_view_requires_rate_repository")
        if not hasattr(self, "_source_projection"):
            self._source_projection = LiteratureRateSourceProjection(self.store, self.run_id)
        return self._source_projection

    def source_domain_projection(self):
        """Versioned domain return over the same original numerical operations."""
        if self.provider != PROVIDER or self.operations_table != "literature_rate_operations":
            raise ContractError("native_rate_return_view_requires_rate_repository")
        if not hasattr(self, "_source_domain_projection"):
            self._source_domain_projection = LiteratureRateSourceDomainProjection(self.store, self.run_id)
        return self._source_domain_projection

    def validate_empty_return_family(self, context):
        """At typed admission, distinguish unavailable work from the wrong view.

        Only this episode's saved operations inform this validation. It never
        runs before population, removes work or creates an observation.
        """
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        versions = set()
        for saved in self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=?",
                (self.run_id, context.episode_id)):
            outcome = json.loads(saved["outcome"])
            if outcome.get("status") != "completed":
                continue
            sheet = self.store.get(outcome["result"]["sheet_ref"])
            if sheet.get("provider") == PROVIDER:
                versions.add(sheet.get("version"))
        supported = {"literature_rate_population_record_v1", NATIVE_RECORD_VERSION}
        if self.record_version not in versions and versions & supported:
            raise ContractError("literature_rate_projection_version_mismatch")

    def validate_cells(self, cells, *, sheet_refs, permitted_record_refs, components=None):
        """Validate actual values and requested membership, beyond JSON syntax."""
        expected = self.project_cells(sheet_refs, permitted_record_refs=permitted_record_refs,
                                      components=components)
        if canonical(cells) != canonical(expected):
            raise ContractError("literature_rate_return_differs_from_saved_cells")

    def validate_returned_values(self, cells, *, permitted_record_refs):
        """Check each actual returned cell without exposing unrequested cells."""
        seen = set()
        for row in cells:
            key = (row["sheet_ref"], row["component"])
            if key in seen:
                raise ContractError("duplicate_literature_rate_return_cell")
            seen.add(key)
            expected = self.project_cells([row["sheet_ref"]],
                permitted_record_refs=permitted_record_refs, components=(row["component"],))
            if canonical(row) != canonical(expected[0]):
                raise ContractError("literature_rate_return_differs_from_saved_cells")

    def _sheet_owner(self, reference):
        """Check the original selected owner, without reading scientific bytes."""
        self.read(reference)
        source = self.store.get(reference)
        record = {key: value for key, value in source.items() if key not in ("id", "record_type", "origin")}
        if identity("source", {"origin": "tool", "record": record}) != reference:
            raise ContractError("literature_sheet_owner_mismatch")
        request_bytes = self.store.get_artifact(source["request_ref"])
        if "artifact_" + hashlib.sha256(request_bytes).hexdigest() != source["request_ref"]:
            raise ContractError("literature_sheet_owner_mismatch")
        request = json.loads(request_bytes)
        if (request.get("run_id") != self.run_id or type(request.get("episode_id")) is not str
                or not request["episode_id"] or type(request.get("operation_key")) is not str
                or not request["operation_key"]):
            raise ContractError("literature_sheet_owner_mismatch")
        operation = self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE "
            "run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        outcome = json.loads(operation["outcome"]) if operation else {}
        if (outcome.get("status") != "completed" or outcome.get("result", {}).get("sheet_ref") != reference
                or reference not in outcome.get("record_refs", ())
                or outcome.get("operation_ref") != identity("operation", {"run_id": self.run_id,
                    "episode_id": request["episode_id"], "key": request["operation_key"]})):
            raise ContractError("literature_sheet_owner_mismatch")
        return request["episode_id"]

    def fact_cells(self, context, sheet_refs, *, components):
        """Project owned cells or copy this receiver's exact admitted subset."""
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        # Use each view's existing complete component-selection validation.
        self.project_cells([], permitted_record_refs=(), components=components)
        received = None
        result = []
        for reference in dict.fromkeys(sheet_refs):
            if reference not in context.received_record_refs:
                raise ContractError("literature_sheet_not_received")
            # Empty projection still validates exact v1/v2 view and saved sheet.
            self.project_cells([reference], permitted_record_refs=context.received_record_refs, components=[])
            if self._sheet_owner(reference) == context.episode_id:
                result.extend(self.project_cells([reference], permitted_record_refs=context.received_record_refs,
                    components=components))
            else:
                if received is None:
                    received = {(row["sheet_ref"], row["component"]): row for row in self.received_cells(context)}
                result.extend(deepcopy(received[(reference, name)]) for name in components
                    if (reference, name) in received)
        return result

    def validate_fact_values(self, context, cells):
        """A valid saved row must also be possessed by the reporting episode."""
        self.validate_returned_values(cells, permitted_record_refs=context.received_record_refs)
        if not cells:
            return
        expected = {(row["sheet_ref"], row["component"]): row for row in self.fact_cells(context,
            list(dict.fromkeys(row["sheet_ref"] for row in cells)),
            components=list(dict.fromkeys(row["component"] for row in cells)))}
        if any(canonical(row) != canonical(expected.get((row["sheet_ref"], row["component"]))) for row in cells):
            raise ContractError("literature_cell_not_received")

    def receive_cells(self, context, cells, operation_key):
        """Record exactly the already admitted subset, adding no observation."""
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        with self.store.transaction():
            original = self._runtime_delivery_cells(context, operation_key)
            if original is not None and canonical(original) != canonical(cells):
                raise ContractError("literature_delivery_binding_mismatch")
            self.validate_returned_values(cells,
                permitted_record_refs=[row["sheet_ref"] for row in cells])
            data = canonical(cells)
            old = self.store.db.execute(f"SELECT cells FROM {self.received_table} WHERE "
                "run_id=? AND episode_id=? AND operation_key=?",
                (self.run_id, context.episode_id, operation_key)).fetchone()
            if old is not None and old["cells"] != data:
                raise ContractError("literature_rate_delivery_identity_conflict")
            digest = self._delivery_digest(cells)
            bound = self._delivery_binding(context, operation_key)
            if bound is not None and bound[0] != digest:
                raise ContractError("literature_delivery_binding_mismatch")
            if old is not None and bound is None and original is None:
                raise ContractError("literature_delivery_binding_unavailable")
            if old is not None and bound is None:
                # The original runtime form is sufficient proof. Preserve old
                # state rather than backfilling a newly invented admission.
                return
            self._install_delivery_bindings()
            self.store.db.execute(f"INSERT OR IGNORE INTO {self.received_table} VALUES(?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, data))
            self.store.db.execute(f"INSERT OR IGNORE INTO {self._delivery_table} VALUES(?,?,?,?)",
                (self.run_id, context.episode_id, operation_key, digest))

    def received_cells(self, context):
        """Forward copied admitted cells, not the complete private child sheet."""
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        result, seen = [], set()
        rows = self.store.db.execute(f"SELECT operation_key,cells FROM {self.received_table} WHERE "
            "run_id=? AND episode_id=? ORDER BY rowid", (self.run_id, context.episode_id))
        for saved in rows:
            cells = json.loads(saved["cells"])
            original = self._runtime_delivery_cells(context, saved["operation_key"])
            bound = self._delivery_binding(context, saved["operation_key"])
            if bound is None and original is None:
                raise ContractError("literature_delivery_binding_unavailable")
            if (bound is not None and bound[0] != self._delivery_digest(cells)
                    or original is not None and canonical(original) != canonical(cells)):
                raise ContractError("literature_delivery_binding_mismatch")
            self.validate_returned_values(cells, permitted_record_refs=[row["sheet_ref"] for row in cells])
            for row in cells:
                key = (row["sheet_ref"], row["component"])
                if key not in seen:
                    seen.add(key)
                    result.append(deepcopy(row))
        return result


def rate_cells_schema():
    """Closed numerical parent form fragment; native units use declared codes."""
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {"sheet_ref": dict(reference), "evidence_source_ref": dict(reference),
        "component": {"type": "string", "enum": list(COMPONENTS)},
        "value": {"type": ["number", "null"]},
        "unit": {"type": ["string", "null"],
                 "enum": [*RATE_UNITS, "fraction", "dimensionless", None]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "origin": {"type": "string", "enum": ["reported", "graph_derived", "synthetic", "derived", "proposed"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [*UNAVAILABLE_REASONS, None]},
        "conditional_on": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "enum": ["independent_normal_groups", "independent_groups"]}}}
    for field, namespace in (("assayed_subject_ref", "reference"), ("experiment_ref", "reference"),
            ("reference_condition_ref", "context"), ("test_condition_ref", "context"),
            ("endpoint_ref", "term"), ("normalization_ref", "term")):
        properties[field] = {"type": ["string", "null"], "format": "reference",
                             "x-reference-namespace": namespace}
    return {"type": "array", "items": {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}, "x-source": "literature_rate_cells"}


class LiteratureRateSourceProjection(LiteratureRateRepository):
    """Native typed-return view; shares the single numerical sheet/operation table."""

    record_version = NATIVE_RECORD_VERSION
    received_table = "literature_rate_source_received"

    def populate(self, context, arguments, operation_key):
        raise ContractError("native_rate_return_view_cannot_publish_legacy_table")


class LiteratureRateSourceDomainProjection(LiteratureRateSourceProjection):
    """Independent typed custody for constraints, without a second sheet."""
    received_table = "literature_rate_source_domain_received"

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("explicit_literature_run_required")
        self.store, self.run_id = store, run_id

    def _installed(self):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (self.received_table,)).fetchone() is not None

    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        return super().received_cells(context) if self._installed() else []

    def receive_cells(self, context, cells, operation_key):
        with self.store.transaction():
            self.store.db.execute(f"""CREATE TABLE IF NOT EXISTS {self.received_table}(
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                cells TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))""")
            return super().receive_cells(context, cells, operation_key)

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        from .literature_rate_domains import _project, _point
        from fractions import Fraction
        rows = super().project_cells(sheet_refs, permitted_record_refs=permitted_record_refs, components=components)
        saved = {}
        for row in rows:
            reference = row["sheet_ref"]
            if reference not in saved:
                saved[reference] = self.read(reference)
            trace = saved[reference]["sheet"].get("native_bound_arithmetic")
            if trace is not None:
                domain = trace["components"][row["component"]]["reported_domain"]
            else:
                # Historical cells supply only their actually saved point or
                # raw threshold. Never infer a previously unsaved contrast.
                q = row["value"] if row["value"] is not None else row["threshold"]
                interval = None if q is None else _point(Fraction(q))
                if q is not None and row["bound"] != "none":
                    q = Fraction(q)
                    interval = {"lt": (-float("inf"), False, q, False), "le": (-float("inf"), False, q, True),
                        "gt": (q, False, float("inf"), False), "ge": (q, True, float("inf"), False)}[row["bound"]]
                domain = _project(interval, basis="legacy_stored_cell", conditioning="stored_source_cell",
                    failure=row["unavailable_reason"] if interval is None else None)
            row["reported_domain"] = deepcopy(domain)
        return rows


def rate_source_cells_schema():
    """Closed native return contract, distinct from the unchanged v1 projection."""
    schema = rate_cells_schema()
    properties = schema["items"]["properties"]
    properties["unavailable_reason"]["enum"] = [*UNAVAILABLE_REASONS, *NATIVE_REASONS, None]
    for field in NATIVE_BINDINGS:
        properties[field] = {"type": ["string", "null"], "format": "reference",
                             "x-reference-namespace": "reference"}
    properties["approximate"] = {"type": "boolean"}
    properties["threshold"] = {"type": ["number", "null"]}
    properties["bound"] = {"type": "string", "enum": ["none", "lt", "le", "gt", "ge"]}
    schema["items"]["required"] = list(properties)
    schema["x-source"] = "literature_rate_source_cells"
    return schema


def rate_population_schema():
    """Operands for one explicitly selected source-table population operation."""
    from .domain import REF, obj
    text = {"type": "string", "minLength": 1}
    return obj({"source_ref": REF,
        "source_representation": {"enum": ["original", "text"]},
        "table_kind": {"enum": ["primary_table", "retained_extraction", "synthetic_fixture"]},
        "delimiter": {"enum": ["\t", ","]},
        **{field: dict(text) for field in ("subject", "experiment", "reference_arm", "test_arm",
                                          "reference_condition", "test_condition")},
        "dependence": {"enum": ["unknown", "independent"]},
        "observation_model": {"enum": ["none", "independent_normal_groups"]}})


__all__ = ["LiteratureRateRepository", "COMPONENTS", "PROVIDER", "rate_cells_schema", "rate_population_schema",
           "rate_source_cells_schema"]
