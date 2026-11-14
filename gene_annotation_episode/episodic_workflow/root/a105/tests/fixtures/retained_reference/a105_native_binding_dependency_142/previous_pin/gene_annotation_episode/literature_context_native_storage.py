"""Separately requested native observations from the one committed A108 sheet.

This is reader information, not another score or population operation. Original
source bytes and parsers are never consulted during saved delivery/replay.
"""
from copy import deepcopy
import json

from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_context_inputs import NATIVE_UNITS
from .literature_context_storage import LiteratureContextSemanticProjection
from .literature_context_native_inputs import VALUE_BASES, TRACE_VERSION

NAMESPACE = "literature_context_native_observations"
POSITIONS_FIELD = "requested_context_native_positions"


def positions_schema():
    return {"type":"array","uniqueItems":True,"items":{"anyOf":[
        {"type":"integer","minimum":0},{"type":"string","const":"all"}]}}


def native_observations_schema():
    def ref(kind,nullable=False):
        return {"type":["string","null"] if nullable else "string","format":"reference","x-reference-namespace":kind}
    number={"type":["number","null"]}
    return {"type":"array","x-source":NAMESPACE,"items":obj({
        **{name:ref("source") for name in ("sheet_ref","evidence_source_ref","data_source_ref")},
        "context_ref":ref("context"),"setting_ref":ref("context",True),"requirement_ref":ref("reference"),"measurement_ref":ref("reference"),
        "basis_ref":ref("reference",True),"sample_unit_ref":ref("reference",True),"cluster_ref":ref("reference",True),
        "observation_position":{"type":"integer","minimum":0},
        "unit":{"type":"string","enum":list(NATIVE_UNITS)},"lower":dict(number),"upper":dict(number),
        "lower_closed":{"type":"boolean"},"upper_closed":{"type":"boolean"},
        "reported_relation":{"type":"string","enum":["point","unknown","not_extracted"]},
        **{name:{**number,"minimum":0} for name in ("reported_sd","reported_sem","reported_plusminus")},
        "reported_count":{"type":["integer","null"],"minimum":0},
        "count_relation":{"type":"string","enum":["exact","unknown"]},
        "replicate_kind":{"type":"string","enum":["biological","technical","timepoint","unknown"]},
        "value_basis":{"type":"string","enum":list(VALUE_BASES)},
        "origin":{"type":"string","enum":["reported","synthetic"]},
        "scope_match":{"type":"string","enum":["matched","unresolved","conflicting"]},
        "pairing":{"type":"string","enum":["paired","unknown"]},
        "context_kind":{"type":"string","enum":["sample","environment","growth_condition","assay_condition","organism"]},
        "bound_kind":{"type":"string","const":"reported_point_not_operating_domain"}})}


def publish_native_observations(extraction, meanings, publish):
    """Bind retained point values to actual context/requirement/source identities."""
    trace=extraction["native_evidence"];inputs=extraction["calculation_inputs"]
    if inputs["origin"] not in ("reported","synthetic"):
        raise ContractError("context_native_origin_mismatch")
    req_refs={req["key"]:binding["requirement_ref"] for req,binding in zip(inputs["requirements"],meanings["requirements"])}
    core_contexts={context["key"]:context for context in inputs["contexts"]}
    data_ref=extraction["arguments"]["data_source_ref"]
    def reference(witness,role,fallback=None):
        if witness is None and fallback is None:return None
        anchor=None if witness is None else {k:witness[k] for k in ("source_ref","artifact_ref","start","end","quote")}
        return publish("reference",{"reference_type":"literature_result","source_ref":data_ref if witness is None else witness["source_ref"],
            "accession":identity("context_literal",{"native_role":role,"anchor":anchor,"fallback":fallback if anchor is None else None}),
            "label":"Unknown "+role if witness is None else witness["quote"],"sequence_ref":None,"molecule":None,"length":None,
            "term_refs":[],"context_refs":[],"anchor":anchor})
    rows=[];seen={}
    for selected in trace["contexts"]:
        core=core_contexts[selected["key"]]
        witness=selected["identity"] or selected["setting"]
        anchor=None if witness is None else {k:witness[k] for k in ("source_ref","artifact_ref","start","end","quote")}
        # Unknown settings are scoped by the actual context identity, not
        # silently merged into one biological state merely through equal labels.
        name=("Unknown biological setting (context "+str(list(core_contexts).index(selected["key"])+1)+")"
              if witness is None else witness["quote"])
        context_ref=publish("context",{"context_type":selected["setting_kind"],"source_ref":data_ref if witness is None else witness["source_ref"],
            "name":name,"attributes":[],"related_refs":[],"anchor":anchor})
        setting=selected["setting"]
        setting_ref=None if setting is None else publish("context",{"context_type":selected["setting_kind"],
            "source_ref":setting["source_ref"],"name":setting["quote"],"attributes":[],"related_refs":[],
            "anchor":{k:setting[k] for k in ("source_ref","artifact_ref","start","end","quote")}})
        sample_ref=reference(selected["sample_unit"],"sampling unit")
        cluster_ref=reference(selected["cluster"],"sampling cluster")
        observations={obs["requirement_key"]:obs for obs in core["observations"]}
        for native in selected["observations"]:
            obs=observations[native["requirement_key"]]
            reading=native["value"]
            witness=native["measurement_identity"]
            if witness is None and reading is not None:
                number=reading["number"];selector=number["selector"];selected_number=selector["witness"]
                # Numeric source identity survives a different surrounding quote
                # or recipe. A wider excerpt is not a second observation.
                start=selected_number["start"]+len(selected_number["quote"][:selector["number_start"]].encode("utf-8"))
                witness={**selected_number,"start":start,"end":start+len(number["raw_number"].encode("utf-8")),"quote":number["raw_number"]}
            measurement_ref=reference(witness,"native observation",native["measurement_key"])
            interval=obs["interval"]
            row={"evidence_source_ref":extraction["arguments"]["source_ref"],"data_source_ref":data_ref,
                "context_ref":context_ref,"setting_ref":setting_ref,"requirement_ref":req_refs[native["requirement_key"]],"measurement_ref":measurement_ref,
                "basis_ref":reference(native["basis_witness"],"reported observation basis"),"sample_unit_ref":sample_ref,"cluster_ref":cluster_ref,
                "unit":obs["unit"],"lower":None if interval is None else interval["lower"],"upper":None if interval is None else interval["upper"],
                "lower_closed":interval is not None,"upper_closed":interval is not None,
                "reported_relation":("not_extracted" if native["value_basis"]=="source_value_not_extracted" else "unknown") if interval is None else "point",
                **{name:obs[name] for name in ("reported_sd","reported_sem","reported_plusminus","reported_count","count_relation","replicate_kind")},
                "value_basis":native["value_basis"],"origin":inputs["origin"],"scope_match":core["scope_match"],"pairing":inputs["pairing"],"context_kind":selected["setting_kind"],
                "bound_kind":"reported_point_not_operating_domain"}
            key=selected["key"],native["requirement_key"]
            if key in seen:
                if seen[key]!=row:raise ContractError("context_native_alias_meaning_conflict")
                continue
            seen[key]=deepcopy(row);row["observation_position"]=len(rows);rows.append(row)
    return rows


def native_row_references(rows):
    return list(dict.fromkeys(value for row in rows for key,value in row.items() if key.endswith("_ref") and value is not None))


class LiteratureContextNativeObservations(LiteratureContextSemanticProjection):
    received_table="literature_context_native_observations_received"

    def read(self,sheet_ref):
        saved=super().read(sheet_ref)
        if saved["extraction"].get("native_evidence",{}).get("version")!=TRACE_VERSION or "native_observations" not in saved:
            raise ContractError("literature_context_native_observations_unavailable")
        source=self.store.get(sheet_ref);request=json.loads(self.store.get_artifact(source["request_ref"]))
        operation=self.store.db.execute(f"SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id,request["episode_id"],request["operation_key"])).fetchone()
        outcome=json.loads(operation["outcome"])
        if outcome["result"].get("native_observations")!=saved["native_observations"]:
            raise ContractError("literature_context_native_saved_mismatch")
        return saved

    def _positions(self,positions):
        if not isinstance(positions,(list,tuple)) or any(type(p) not in (str,int) for p in positions):
            raise ContractError("context_native_positions_invalid")
        if len(set(positions))!=len(positions):
            raise ContractError("context_native_positions_invalid")
        if "all" in positions and tuple(positions)!=("all",):
            raise ContractError("context_native_positions_invalid")
        if any(p!="all" and (type(p) is not int or p<0) for p in positions):
            raise ContractError("context_native_positions_invalid")
        return tuple(positions)

    def project_rows(self,sheet_refs,*,permitted_record_refs,positions=("all",)):
        positions=self._positions(positions);result=[]
        for sheet_ref in dict.fromkeys(sheet_refs):
            if sheet_ref not in permitted_record_refs:raise ContractError("literature_sheet_not_received")
            saved=self.read(sheet_ref)
            rows=saved["native_observations"]
            if positions!=("all",) and any(p>=len(rows) for p in positions):
                raise ContractError("context_native_position_unavailable")
            result.extend({"sheet_ref":sheet_ref,**deepcopy(row)} for row in rows
                if positions==("all",) or row["observation_position"] in positions)
        validate_schema(result,native_observations_schema())
        return result

    def validate_returned_values(self,rows,*,permitted_record_refs):
        validate_schema(rows,native_observations_schema());seen=set()
        for row in rows:
            key=row["sheet_ref"],row["observation_position"]
            if key in seen:raise ContractError("duplicate_context_native_observation")
            seen.add(key)
            expected=self.project_rows([key[0]],permitted_record_refs=permitted_record_refs,positions=[key[1]])
            if len(expected)!=1 or canonical(row)!=canonical(expected[0]):
                raise ContractError("context_native_return_differs_from_saved")

    def fact_rows(self,context,sheet_refs,*,positions=("all",)):
        if context.run_id!=self.run_id:raise ContractError("literature_run_mismatch")
        positions=self._positions(positions);received=None;result=[]
        for sheet_ref in dict.fromkeys(sheet_refs):
            if sheet_ref not in context.received_record_refs:raise ContractError("literature_sheet_not_received")
            self.project_rows([sheet_ref],permitted_record_refs=context.received_record_refs,positions=[])
            if self._sheet_owner(sheet_ref)==context.episode_id:
                result.extend(self.project_rows([sheet_ref],permitted_record_refs=context.received_record_refs,positions=positions))
            else:
                if received is None:received=self.received_rows(context)
                result.extend(deepcopy(row) for row in received if row["sheet_ref"]==sheet_ref and
                    (positions==("all",) or row["observation_position"] in positions))
        return result

    def validate_fact_rows(self,context,rows):
        self.validate_returned_values(rows,permitted_record_refs=context.received_record_refs)
        expected={(r["sheet_ref"],r["observation_position"]):r for r in self.fact_rows(context,
            list(dict.fromkeys(r["sheet_ref"] for r in rows)),positions=list(dict.fromkeys(r["observation_position"] for r in rows)))}
        if any(canonical(r)!=canonical(expected.get((r["sheet_ref"],r["observation_position"]))) for r in rows):
            raise ContractError("context_native_observation_not_received")


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
