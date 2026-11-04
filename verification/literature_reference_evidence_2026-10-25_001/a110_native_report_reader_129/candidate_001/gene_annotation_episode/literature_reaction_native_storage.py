"""Independently requested native A110 observations over one saved sheet.

Native observations are source operands, not scoring components. Aggregate-only
forms never acquire them. Saved projection reads no scientific source bytes.
"""
from copy import deepcopy
import json

from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_reaction_storage import LiteratureReactionSemanticProjection, BINDINGS
from .literature_reaction_native_inputs import RATIO_BASES, COUNT_BASES, UNCERTAINTY_KINDS, TRACE_VERSION

NAMESPACE = "literature_reaction_native_observations"
POSITIONS_FIELD = "requested_reaction_native_positions"


def positions_schema():
    return {"type": "array", "uniqueItems": True, "items": {"anyOf": [
        {"type": "integer", "minimum": 0}, {"type": "string", "const": "all"}]}}


def native_observations_schema():
    def ref(kind, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference",
                "x-reference-namespace": kind}
    number = {"type": ["number", "null"]}
    return {"type": "array", "x-source": NAMESPACE, "items": obj({
        **{name: ref("source") for name in ("sheet_ref", "evidence_source_ref", "data_source_ref")},
        **{field: ref(kind, True) for field, (_, kind) in BINDINGS.items()},
        "observation_position": {"type": "integer", "minimum": 0},
        "measurement_ref": ref("reference"), "resource_ref": ref("reference", True),
        "source_number_refs": {"type": "array", "items": ref("reference")},
        "basis_refs": {"type": "array", "items": ref("reference")},
        "count_basis_refs": {"type": "array", "items": ref("reference")},
        "uncertainty_basis_refs": {"type": "array", "items": ref("reference")},
        "count_number_ref": ref("reference", True), "uncertainty_number_ref": ref("reference", True),
        "source_unit_ref": ref("reference", True),
        "operand_role": {"type": "string", "enum": ["ratio_summary", "ratio_observation",
            "resource_value", "resource_lower", "resource_upper"]},
        "value": dict(number), "reported_value": dict(number),
        "numerator_value": dict(number), "denominator_value": dict(number),
        "unit": {"type": "string", "enum": ["mol_per_mol", "signal_per_signal", "umol", "uM", "umol_per_min", "uM_per_min"]},
        "source_unit": {"type": ["string", "null"], "enum": [None, "pmol", "nmol", "umol", "mmol", "nM", "uM", "mM",
            *[u + "/" + t for u in ("pmol", "nmol", "umol", "mmol", "nM", "uM", "mM") for t in ("s", "min")]]},
        "ratio_kind": {"type": ["string", "null"], "enum": [None, "product_pair", "formed_per_consumed", "formed_per_supplied", "signal_ratio"]},
        "ratio_form": {"type": "string", "enum": ["reported_point", "normalized_reported_pair", "unreported", "not_ratio"]},
        "measurement_basis": {"type": ["string", "null"], "enum": [None, *RATIO_BASES]},
        "reported_count": {"type": ["integer", "null"], "minimum": 1},
        "count_basis": {"type": "string", "enum": list(COUNT_BASES)},
        "independent_n": {"type": ["integer", "null"], "minimum": 1},
        "uncertainty_kind": {"type": "string", "enum": list(UNCERTAINTY_KINDS)},
        "uncertainty_value": {**number, "minimum": 0},
        "transformation": {"type": "string", "enum": ["identity", "normalize_reported_pair", "unit_conversion", "unreported"]},
        "evaluation_scope": {"type": "string", "const": "native_reference_reaction_operands"},
        "measurement_corrections": {"type": "string", "const": "not_applied"},
        "origin": {"type": "string", "enum": ["reported", "synthetic"]}})}


def publish_native_observations(extraction, scientific_bindings, semantic_bindings, publish):
    """Publish exact source anchors and declared operand roles, without inference."""
    trace = extraction["native_evidence"]
    inputs = extraction["calculation_inputs"]
    data_ref = extraction["arguments"]["data_source_ref"]
    rows = []
    def reference(witness, role, fallback=None):
        if witness is None and fallback is None:
            return None
        anchor = None if witness is None else {key: witness[key] for key in ("source_ref", "artifact_ref", "start", "end", "quote")}
        return publish("reference", {"reference_type": "literature_result", "source_ref": data_ref if witness is None else witness["source_ref"],
            "accession": identity("reaction_literal", {"native_role": role, "anchor": anchor, "fallback": fallback}),
            "label": "Unreported " + role if witness is None else witness["quote"], "sequence_ref": None,
            "molecule": None, "length": None, "term_refs": [], "context_refs": [], "anchor": anchor})
    def number_ref(number, role):
        if number is None:
            return None
        selector = number["selector"]
        witness = selector["witness"]
        start = witness["start"] + len(witness["quote"][:selector["number_start"]].encode())
        exact = {**witness, "start": start, "end": start + len(number["raw_number"].encode()), "quote": number["raw_number"]}
        return reference(exact, role)
    def witnesses(values, role):
        return list(dict.fromkeys(reference(value, role) for value in values))
    def base(role, measurement, value, unit):
        return {"evidence_source_ref": extraction["arguments"]["source_ref"], "data_source_ref": data_ref,
            **deepcopy(scientific_bindings), "observation_position": len(rows), "measurement_ref": measurement,
            "resource_ref": None, "source_number_refs": [], "basis_refs": [], "count_basis_refs": [],
            "uncertainty_basis_refs": [], "count_number_ref": None, "uncertainty_number_ref": None,
            "source_unit_ref": None, "operand_role": role, "value": value, "reported_value": None,
            "numerator_value": None, "denominator_value": None, "unit": unit, "source_unit": None,
            "ratio_kind": None, "ratio_form": "not_ratio", "measurement_basis": None,
            "reported_count": None, "count_basis": "unknown", "independent_n": None,
            "uncertainty_kind": "unreported", "uncertainty_value": None, "transformation": "unreported",
            "evaluation_scope": "native_reference_reaction_operands", "measurement_corrections": "not_applied",
            "origin": inputs["ratio"]["origin"] if role.startswith("ratio") else inputs["budget"]["origin"]}
    ratio = trace["ratio"]
    if ratio is not None:
        items = ([("ratio_summary", ratio["summary"]["ratio"], ratio["summary"], [])] if ratio["summary"] is not None else
            [("ratio_observation", item["ratio"], None, item["basis_witnesses"]) for item in ratio["observations"]])
        for role, expression, summary, design in items:
            numbers = ([] if expression is None else [expression["number"]] if expression["number"] is not None else [expression["numerator"], expression["denominator"]])
            witness = numbers[0]["selector"]["witness"] if numbers else None
            row = base(role, reference(witness, "reported reaction measurement", len(rows)),
                None if expression is None else expression["value"], inputs["ratio"]["unit"])
            row.update(ratio_kind=inputs["ratio"]["ratio_kind"], measurement_basis=ratio["measurement_basis"],
                basis_refs=witnesses([*ratio["basis_witnesses"], *design], "ratio interpretation basis"),
                source_number_refs=[number_ref(number, "reported ratio operand") for number in numbers],
                ratio_form="unreported" if expression is None else expression["form"])
            if expression is not None:
                paired = expression["form"] == "normalized_reported_pair"
                row.update(reported_value=None if paired else expression["number"]["value"],
                    numerator_value=expression["numerator"]["value"] if paired else None,
                    denominator_value=expression["denominator"]["value"] if paired else None,
                    transformation="normalize_reported_pair" if paired else "identity")
            if summary is not None:
                spread, count = summary["uncertainty"], summary["count"]
                row.update(reported_count=count["reported_n"], count_basis=count["basis"],
                    independent_n=inputs["ratio"]["independent_n"], uncertainty_kind=spread["kind"],
                    uncertainty_value=None if spread["number"] is None else spread["number"]["value"],
                    count_number_ref=number_ref(count["number"], "reported repetition count"),
                    uncertainty_number_ref=number_ref(spread["number"], "reported ratio uncertainty"),
                    count_basis_refs=witnesses(count["basis_witnesses"], "repetition interpretation basis"),
                    uncertainty_basis_refs=witnesses(spread["basis_witnesses"], "uncertainty interpretation basis"))
            rows.append(row)
    if trace["budget"] is not None:
        resource_refs = {raw["resource_key"]: meaning["resource_ref"] for raw, meaning in
            zip(extraction["observations"]["budget"]["resources"], semantic_bindings["resources"])}
        for resource in trace["budget"]["resources"]:
            for role in ("value", "lower", "upper"):
                quantity = resource[role]
                if quantity is None:
                    continue
                number, unit = quantity["number"], quantity["unit"]
                row = base("resource_" + role, reference(number["selector"]["witness"], "reported resource measurement"),
                    quantity["value"], unit["canonical_unit"])
                raw_unit = unit["native_unit"]
                row.update(resource_ref=resource_refs[resource["resource_key"]], reported_value=number["value"],
                    source_number_refs=[number_ref(number, "reported resource operand")], source_unit_ref=reference(unit["witness"], "reported resource unit"),
                    source_unit=raw_unit, transformation="identity" if unit["multiplier"] == 1 else "unit_conversion")
                rows.append(row)
    return rows


def native_row_references(rows):
    result = []
    for row in rows:
        for key, value in row.items():
            if key.endswith("_ref") and value is not None:
                result.append(value)
            elif key.endswith("_refs"):
                result.extend(value)
    return list(dict.fromkeys(result))


class LiteratureReactionNativeObservations(LiteratureReactionSemanticProjection):
    received_table = "literature_reaction_native_observations_received"

    def read(self, sheet_ref):
        saved = super().read(sheet_ref)
        if saved["extraction"].get("native_evidence", {}).get("version") != TRACE_VERSION or "native_observations" not in saved:
            raise ContractError("literature_reaction_native_observations_unavailable")
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source["request_ref"]))
        operation = self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, request["episode_id"], request["operation_key"])).fetchone()
        outcome = json.loads(operation["outcome"])
        if outcome["result"].get("native_observations") != saved["native_observations"]:
            raise ContractError("literature_reaction_native_saved_mismatch")
        return saved

    def _positions(self, positions):
        if not isinstance(positions, (tuple, list)) or any(type(p) not in (str, int) for p in positions):
            raise ContractError("reaction_native_positions_invalid")
        if len(set(positions)) != len(positions) or "all" in positions and tuple(positions) != ("all",):
            raise ContractError("reaction_native_positions_invalid")
        if any(p != "all" and (type(p) is not int or p < 0) for p in positions):
            raise ContractError("reaction_native_positions_invalid")
        return tuple(positions)

    def project_rows(self, sheet_refs, *, permitted_record_refs, positions=("all",)):
        positions = self._positions(positions)
        result = []
        for sheet_ref in dict.fromkeys(sheet_refs):
            if sheet_ref not in permitted_record_refs:
                raise ContractError("literature_sheet_not_received")
            rows = self.read(sheet_ref)["native_observations"]
            if positions != ("all",) and any(p >= len(rows) for p in positions):
                raise ContractError("reaction_native_position_unavailable")
            result.extend({"sheet_ref": sheet_ref, **deepcopy(row)} for row in rows
                if positions == ("all",) or row["observation_position"] in positions)
        validate_schema(result, native_observations_schema())
        return result

    def validate_returned_values(self, rows, *, permitted_record_refs):
        validate_schema(rows, native_observations_schema())
        seen = set()
        for row in rows:
            key = row["sheet_ref"], row["observation_position"]
            if key in seen:
                raise ContractError("duplicate_reaction_native_observation")
            seen.add(key)
            expected = self.project_rows([key[0]], permitted_record_refs=permitted_record_refs, positions=[key[1]])
            if len(expected) != 1 or canonical(row) != canonical(expected[0]):
                raise ContractError("reaction_native_return_differs_from_saved")

    def fact_rows(self, context, sheet_refs, *, positions=("all",)):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        positions = self._positions(positions)
        received, result = None, []
        for sheet_ref in dict.fromkeys(sheet_refs):
            if sheet_ref not in context.received_record_refs:
                raise ContractError("literature_sheet_not_received")
            self.project_rows([sheet_ref], permitted_record_refs=context.received_record_refs, positions=[])
            if self._sheet_owner(sheet_ref) == context.episode_id:
                result.extend(self.project_rows([sheet_ref], permitted_record_refs=context.received_record_refs, positions=positions))
            else:
                if received is None:
                    received = self.received_rows(context)
                result.extend(deepcopy(row) for row in received if row["sheet_ref"] == sheet_ref and
                    (positions == ("all",) or row["observation_position"] in positions))
        return result

    def validate_fact_rows(self, context, rows):
        self.validate_returned_values(rows, permitted_record_refs=context.received_record_refs)
        expected = {(row["sheet_ref"], row["observation_position"]): row for row in self.fact_rows(context,
            list(dict.fromkeys(row["sheet_ref"] for row in rows)),
            positions=list(dict.fromkeys(row["observation_position"] for row in rows)))}
        if any(canonical(row) != canonical(expected.get((row["sheet_ref"], row["observation_position"]))) for row in rows):
            raise ContractError("reaction_native_observation_not_received")

    # These three receipt methods retain the existing rate-receipt proof
    # structure exactly, with the native namespace and row-position identity.
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
            namespace = NAMESPACE
            fields = [name for name, node in contract["measurements"]["schema"]["properties"].items()
                if node.get("x-source") == namespace]
            if not fields:
                raise ContractError("literature_delivery_binding_mismatch")
            return [row for name in fields for row in form[name]]
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError("literature_delivery_binding_mismatch") from error


    def _receive_rows(self, context, cells, operation_key):
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


    def _received_rows(self, context):
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
                key = (row["sheet_ref"], row["observation_position"])
                if key not in seen:
                    seen.add(key)
                    result.append(deepcopy(row))
        return result


    def receive_rows(self,context,rows,operation_key):
        with self.store.transaction():
            self.store.db.execute(f"""CREATE TABLE IF NOT EXISTS {self.received_table}(
                run_id TEXT NOT NULL,episode_id TEXT NOT NULL,operation_key TEXT NOT NULL,
                cells TEXT NOT NULL,PRIMARY KEY(run_id,episode_id,operation_key))""")
            return self._receive_rows(context,rows,operation_key)

    def received_rows(self,context):
        if context.run_id!=self.run_id:raise ContractError("literature_run_mismatch")
        return self._received_rows(context) if self._installed() else []
