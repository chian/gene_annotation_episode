"""Pure BLAST maskinfo syntax reading and existing masking-sheet population.

Bytes, physical spans, original member ordinals and complete native trees are
retained separately from input association. No native process or numerical
extent calculator is called here. Authentication is supplied by the host.
"""
from __future__ import annotations

from copy import deepcopy
import re

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.gene_context_evidence.sequence_masking_contracts import _mask_runs, sequence_masking_molecule, validate_sequence_masking_record as core
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.gene_context_evidence.sequence_masking_inputs import _check, _failure



def _span(data, start, end):
    return {"byte_start": start, "byte_end": end,
            "line_start": data.count(b"\n", 0, start) + 1,
            "line_end": data.count(b"\n", 0, max(start, end - 1)) + 1}


def _children(node, name):
    return [r for r in node["children"] if r["name"] == name] if node else []


def _one(node, name):
    found = _children(node, name)
    return found[0] if len(found) == 1 else None


def _path(node, *names):
    for name in names:
        node = _one(node, name)
    return node


def _value(node):
    if node is None:
        return None
    return node["children"][0] if node["kind"] in ("field", "choice") and len(node["children"]) == 1 else node


def _scalar(node, kind=None):
    node = _value(node)
    if node is None or kind and node["kind"] != kind:
        return None
    return node["scalar"]


def _integer_value(node, xml):
    value = _scalar(node)
    if xml:
        return int(value.strip()) if type(value) is str and re.fullmatch(r"-?[0-9]+", value.strip()) else None
    return value if type(value) is int else None


def _signature(seq_id):
    """Compare supported IDs without dropping local integer/string distinctions."""
    if seq_id is None:
        return None
    node, choice = seq_id["native_tree"], seq_id["choice"]
    xml = node["kind"] == "xml_element"
    if choice == "local":
        obj = _path(node, "Seq-id_local", "Object-id") if xml else _value(node)
        if xml:
            string, integer = _one(obj, "Object-id_str"), _one(obj, "Object-id_id")
            if string is not None and integer is None and len(obj["children"]) == 1:
                return ("local", "string", string["scalar"])
            if integer is not None and string is None and len(obj["children"]) == 1:
                n = _integer_value(integer, True)
                return ("local", "integer", n) if n is not None else None
        elif obj and obj["name"] in ("str", "id"):
            raw = _scalar(obj)
            if type(raw) is (str if obj["name"] == "str" else int):
                return ("local", "string" if obj["name"] == "str" else "integer", raw)
    elif choice == "other":
        obj = _path(node, "Seq-id_other", "Textseq-id") if xml else _value(node)
        if obj:
            fields = {}
            for item in obj["children"]:
                name = item["name"].removeprefix("Textseq-id_") if item["name"] else None
                if name not in ("accession", "version", "name", "release") or name in fields:
                    return None
                fields[name] = _integer_value(item, xml) if name == "version" else _scalar(item)
            if isinstance(fields.get("accession"), str) and all(v is not None for v in fields.values()):
                return ("other", tuple(sorted(fields.items())))
    elif choice == "general":
        obj = _path(node, "Seq-id_general", "Dbtag") if xml else _value(node)
        if obj and len(obj["children"]) == 2:
            db = _scalar(_one(obj, "Dbtag_db" if xml else "db"))
            tag = _path(obj, "Dbtag_tag", "Object-id") if xml else _value(_one(obj, "tag"))
            if xml:
                string, integer = _one(tag, "Object-id_str"), _one(tag, "Object-id_id")
                item = string or integer
                raw = _scalar(item) if string else _integer_value(item, True)
                kind = "string" if string else "integer"
            else:
                raw = _scalar(tag)
                kind = "string" if tag and tag["name"] == "str" else "integer" if tag and tag["name"] == "id" else None
            if isinstance(db, str) and kind and type(raw) is (str if kind == "string" else int):
                return ("general", db, kind, raw)
    return None


def _expected_id(source, operation):
    if not operation["parse_seqids"]:
        return ("local", "integer", source["record_ordinal"] + 1)
    token = source["native_header"].split()[0] if source["native_header"].split() else ""
    if token.startswith("lcl|"):
        return ("local", "string", token[4:])
    if token.startswith("ref|"):
        accession = token.split("|")[1]
        match = re.fullmatch(r"(.+)\.([0-9]+)", accession)
        return ("other", tuple(sorted({"accession": match[1], "version": int(match[2])}.items()))) if match else ("other", (("accession", accession),))
    if token.startswith("gnl|"):
        parts = token.split("|")
        if len(parts) == 3:
            return ("general", parts[1], "string", parts[2])
        return None
    return ("local", "string", token) if "|" not in token else None


def _record_from_node(node, *, data, xml, ordinal, root_ordinal, list_ordinal, member_ordinal, oid, closed):
    failures, intervals = [], []
    def fail(code, at=node, stage="parse"):
        item = _failure(stage, code, oid, line_number=at["native_locator"]["line_start"])
        if item not in failures:
            failures.append(item)
    if xml:
        choice = node["children"][0] if node["name"] == "Seq-loc" and len(node["children"]) == 1 else None
        kind = {"Seq-loc_int": "int", "Seq-loc_packed-int": "packed_int"}.get(choice["name"] if choice else None, "unsupported")
        holder = _one(choice, "Packed-seqint") if kind == "packed_int" else choice
        members = holder["children"] if holder else []
    else:
        kind = {"int": "int", "packed-int": "packed_int"}.get(node["name"], "unsupported")
        holder = _value(node)
        members = holder["children"] if kind == "packed_int" else [holder] if kind == "int" else []
    if kind == "unsupported" or not members or kind == "int" and len(members) != 1:
        fail("maskinfo_location_unsupported")
    for number, item in enumerate(members):
        if xml and item["name"] != "Seq-interval" or not xml and item["kind"] not in ("object", "array"):
            fail("maskinfo_location_unsupported", item)
        start = _integer_value(_one(item, "Seq-interval_from" if xml else "from"), xml)
        end = _integer_value(_one(item, "Seq-interval_to" if xml else "to"), xml)
        if start is None or end is None or start < 0 or end < start:
            fail("maskinfo_interval_invalid", item)
        if xml:
            ident = _path(item, "Seq-interval_id", "Seq-id")
            idchoice = ident["children"][0]["name"].removeprefix("Seq-id_") if ident and len(ident["children"]) == 1 else "unsupported"
        else:
            ident = _value(_one(item, "id"))
            idchoice = ident["name"] if ident and ident["name"] else "unsupported"
        seq_id = {"choice": idchoice, "native_locator": ident["native_locator"], "native_tree": ident} if ident else None
        if _signature(seq_id) is None:
            fail("maskinfo_location_unsupported", item)
        allowed = {"Seq-interval_from", "Seq-interval_to", "Seq-interval_id"} if xml else {"from", "to", "id"}
        if len(item["children"]) != 3 or any(r["name"] not in allowed for r in item["children"]):
            fail("maskinfo_location_unsupported", item)
        intervals.append({"interval_ordinal": number, "native_locator": item["native_locator"],
                          "start": start, "end_inclusive": end, "seq_id": seq_id})
    ids = [_signature(r["seq_id"]) for r in intervals]
    if ids and any(identity != ids[0] for identity in ids):
        fail("maskinfo_seq_id_conflict", stage="association")
    if id(node) not in closed:
        fail("maskinfo_syntax_invalid")
    return {"record_ref": oid + "#/native_mask_records/" + str(ordinal), "native_record_ordinal": ordinal,
            "root_ordinal": root_ordinal, "mask_list_ordinal": list_ordinal, "member_ordinal": member_ordinal,
            "native_location_kind": kind, "native_locator": node["native_locator"], "native_tree": node,
            "intervals": intervals, "completeness": "partial" if failures else "complete", "failures": failures}


def _source_relationship(source, record, operation, oid):
    """Check a selected association against original symbols and native facts."""
    key, failures = source["record_key"], []
    line = record["native_locator"]["line_start"]
    def fail(code, stage="association"):
        item = _failure(stage, code, source["occurrence"]["occurrence_id"] if stage == "input" else oid,
                        key, None if stage == "input" else line)
        if item not in failures:
            failures.append(item)
    if source["molecule"] != sequence_masking_molecule(operation):
        fail("incompatible_input_molecule", "input")
    if source["length"] is None or source["length"] == 0 or source["failures"]:
        fail("input_substrate_unavailable", "input")
    valid = []
    for interval in record["intervals"]:
        a, b = interval["start"], interval["end_inclusive"]
        if a is not None and b is not None and 0 <= a <= b:
            if source["length"] is not None and b >= source["length"]:
                fail("maskinfo_interval_out_of_bounds", "parse")
            else:
                valid.append([a, b + 1])
    if valid != _mask_runs([c.islower() for c in source["original_sequence"]]):
        fail("maskinfo_source_mask_conflict")
    if operation["output_format"] != "interval":
        expected = _expected_id(source, operation)
        # An unsupported header mapping is unavailable, never a guessed join.
        for interval in record["intervals"]:
            signature = _signature(interval["seq_id"])
            if signature is None or expected is None:
                fail("maskinfo_location_unsupported", "parse")
            elif signature != expected:
                fail("maskinfo_seq_id_conflict")
    return failures


def _conversion_output(*, operation, input_records, parsed_maskinfo, custody, native_outcome):
    """The sole association constructor, reused when validating a saved sheet."""
    operation, parsed = core("Operation", operation), core("BlastMaskInfoParse", parsed_maskinfo)
    custody, outcome = core("Custody", custody), core("NativeOutcome", native_outcome)
    if operation["mode"] != "convert_mask" or operation["output_format"] != parsed["native_format"]:
        raise ContractError("sequence_masking_output_format")
    if type(input_records) is not list:
        raise ContractError("sequence_masking_list_required")
    sources = [core("InputRecord", r) for r in input_records]
    if len({r["record_key"] for r in sources}) != len(sources) or [r["record_key"] for r in sources] != custody["sequence_order"]:
        raise ContractError("sequence_masking_input_population")
    if outcome["returncode"] != custody["native_returncode"] or outcome["output_complete"] != custody["output_complete"]:
        raise ContractError("sequence_masking_outcome_custody_conflict")
    if custody["order_basis"] == "native_fasta_iteration" or any(r["basis"] == "native_fasta_iteration" for r in custody["record_bindings"]):
        raise ContractError("sequence_masking_conversion_order_basis")
    occurrence, oid = parsed["occurrence"], parsed["occurrence"]["occurrence_id"]
    failures, checks = deepcopy(parsed["failures"]), deepcopy(parsed["checks"])
    for root in parsed["roots"]:
        if root["algorithm_options"] != operation["requested_parameters"]["masking_options"]:
            failures.append(_failure("parse", "maskinfo_metadata_invalid", oid,
                                     line_number=root["native_locator"]["line_start"]))
    native = parsed["records"]
    by_key = {r["record_key"]: r for r in sources}
    masked = [r for r in sources if _mask_runs([c.islower() for c in r["original_sequence"]])]
    valid_sources = bool(sources) and all(r["length"] and not r["failures"] and
        r["molecule"] == sequence_masking_molecule(operation) and r["occurrence"]["completeness"] == "complete" for r in sources)
    # A caller cannot establish the complete population by dropping an input row.
    for oid_input in {r["occurrence"]["occurrence_id"] for r in sources}:
        group = [r for r in sources if r["occurrence"]["occurrence_id"] == oid_input]
        valid_sources = valid_sources and [r["record_ordinal"] for r in group] == list(range(len(group)))
    complete = (valid_sources and custody["producer_kind"] == "authenticated_native" and
        outcome == {"returncode": 0, "state": "succeeded", "output_complete": True} and
        occurrence["completeness"] == "complete" and parsed["parse_state"] == "complete" and not failures)
    structured = operation["output_format"] != "interval"
    relationships = (structured and len(native) == len(masked) and all(not _source_relationship(source, row, operation, oid)
                     for source, row in zip(masked, native)))
    automatic = complete and structured and custody["order_basis"] == "native_masked_input_iteration" and relationships
    if complete and structured and custody["order_basis"] == "native_masked_input_iteration" and not relationships:
        failures.append(_failure("association", "maskinfo_population_conflict", oid))
        for source, row in zip(masked, native):
            failures.extend(_source_relationship(source, row, operation, oid))
    bindings = {r["output_record_ordinal"]: r for r in custody["record_bindings"]}
    for ordinal, binding in bindings.items():
        if ordinal >= len(native):
            failures.append(_failure("association", "bound_output_record_absent", oid, binding["input_record_key"]))
    records, unassigned = [], []
    for row in native:
        ordinal, key, association = row["native_record_ordinal"], None, "unresolved"
        binding = bindings.get(ordinal)
        if binding is not None:
            if binding["basis"] == "native_single_input":
                if not structured and len(sources) == 1 and len(native) == 1:
                    key, association = binding["input_record_key"], "authenticated_single_input"
            elif binding["basis"] == "native_masked_input_iteration":
                if automatic and binding["input_record_key"] == masked[ordinal]["record_key"]:
                    key, association = binding["input_record_key"], "authenticated_native_masked_order"
            else:
                if structured or len(sources) == 1:
                    key, association = binding["input_record_key"], "caller_declared"
        elif automatic:
            key, association = masked[ordinal]["record_key"], "authenticated_native_masked_order"
        rf = [{**f, "record_key": key} for f in row["failures"]]
        if key is None:
            rf.append(_failure("association", "output_record_unassociated", oid, line_number=row["native_locator"]["line_start"]))
        else:
            rf.extend(_source_relationship(by_key[key], row, operation, oid))
        if not structured and len(sources) > 1:
            rf.append(_failure("association", "maskinfo_bare_interval_multirecord_unresolved", oid,
                               line_number=row["native_locator"]["line_start"]))
        completeness = row["completeness"]
        # Structured closed records survive a later failure; an interval stream
        # has no closing member and needs the complete output occurrence.
        if not structured and (not custody["output_complete"] or occurrence["completeness"] != "complete"):
            completeness = "partial"
            rf.append(_failure("parse", "output_record_incomplete", oid, key, row["native_locator"]["line_start"]))
        intervals = [[r["start"], r["end_inclusive"] + 1] for r in row["intervals"]
                     if r["start"] is not None and r["end_inclusive"] is not None and 0 <= r["start"] <= r["end_inclusive"]]
        record = {"output_record_ordinal": ordinal, "input_record_key": key, "native_header": "",
            "output_locator": {"byte_offset": row["native_locator"]["byte_start"],
                "line_start": row["native_locator"]["line_start"], "line_end": row["native_locator"]["line_end"]},
            "native_intervals": [{"start": r["start"], "end_inclusive": r["end_inclusive"],
                "line_number": r["native_locator"]["line_start"]} for r in row["intervals"]],
            "intervals_half_open": intervals, "output_sequence": None, "association": association,
            "completeness": completeness, "measurement": "exact_mask" if not rf and completeness == "complete" else "unavailable",
            "failures": rf, "native_record_ref": row["record_ref"]}
        (records if key is not None else unassigned).append(record)
        failures.extend(rf)
        checks.append(_check("mask_association_provenance", "unknown" if association in ("caller_declared", "unresolved") else "pass", key,
            "caller_declared_association" if association == "caller_declared" else "output_record_unassociated" if key is None else None))
        checks.append(_check("mask_measurement", "pass" if record["measurement"] == "exact_mask" else "unknown", key,
                             None if record["measurement"] == "exact_mask" else rf[0]["code"] if rf else "mask_measurement_unavailable"))
    # No invented native row for an omitted uppercase input. An unresolved or
    # conflicting emitted record prevents any inference from omission.
    zero_proof = complete and not failures and (automatic or not structured and len(sources) == 1 and not native and not masked
                                               and custody["order_basis"] == "native_single_input")
    zeros = [{"input_record_key": r["record_key"], "output_occurrence_id": oid,
              "evidence_kind": "authenticated_complete_conversion_omission"} for r in sources if zero_proof and r not in masked]
    present = {r["input_record_key"] for r in records + zeros}
    for source in sources:
        key = source["record_key"]
        if key not in present:
            failures.append(_failure("association", "input_mask_record_absent", oid, key))
        elif any(r["input_record_key"] == key for r in zeros):
            checks.append(_check("known_zero_mask", "pass", key, "authenticated_complete_conversion_omission"))
    checks.append(_check("mask_output_custody", "pass" if complete else "unknown", reason=None if complete else "output_not_successfully_closed"))
    unique = []
    for failure in failures:
        if failure not in unique:
            unique.append(failure)
    return {"version": "sequence_masking_parsed_output", "format": operation["output_format"],
        "occurrence": occurrence, "custody": custody, "records": records, "unassigned_records": unassigned,
        "checks": checks, "failures": unique, "native_maskinfo": parsed, "known_zero_records": zeros}


def _validate_native_relationships(parsed):
    """Check saved convenience fields against the retained syntax, without I/O."""
    def require(condition):
        if not condition:
            raise ContractError("sequence_masking_native_tree_relationship")
    xml = parsed["native_format"] == "maskinfo_xml"
    for root in parsed["roots"]:
        tree = root["native_tree"]
        require(tree["name"] == "Blast-db-mask-info")
        require(root["algorithm_id"] == _integer_value(_one(tree, "Blast-db-mask-info_algo-id" if xml else "algo-id"), xml))
        if xml:
            program = _path(tree, "Blast-db-mask-info_algo-program", "Blast-filter-program")
            name = next((r["value"] for r in program["attributes"] if r["name"] == "value"), None) if program else None
            code = _integer_value(program, True)
            options = _one(tree, "Blast-db-mask-info_algo-options")
            options = _scalar(options) if options and not options["children"] else None
            masks = _one(tree, "Blast-db-mask-info_masks")
            lists = masks["children"] if masks else []
        else:
            name, code = _scalar(_one(tree, "algo-program"), "identifier"), None
            options = _scalar(_one(tree, "algo-options"), "string")
            lists = [_value(r) for r in _children(tree, "masks")]
        require((root["algorithm_program_name"], root["algorithm_program_code"], root["algorithm_options"]) == (name, code, options))
        require(root["algorithm_program_code_presence"] == ("not_serialized" if not xml else "serialized" if code is not None else "unreadable"))
        require(len(lists) == len(root["mask_lists"]))
        for entry, native_list in zip(root["mask_lists"], lists):
            require(entry["native_locator"] == native_list["native_locator"])
            more_node = _one(native_list, "Blast-mask-list_more" if xml else "more")
            if xml:
                lexeme = next((r["value"] for r in more_node["attributes"] if r["name"] == "value"), None) if more_node else None
                more = {"true": True, "false": False}.get(lexeme)
                require(entry["more_lexeme"] == lexeme)
            else:
                more = _scalar(more_node, "boolean")
                if more is not None:
                    require(entry["more_lexeme"] == ("TRUE" if more else "FALSE"))
            require(entry["more"] is more)
            container = _one(native_list, "Blast-mask-list_masks" if xml else "masks")
            container = container if xml else _value(container)
            members = container["children"] if container else []
            require(len(members) == len(entry["record_ordinals"]))
            for mid, (member, ordinal) in enumerate(zip(members, entry["record_ordinals"])):
                record = parsed["records"][ordinal]
                require(record["native_tree"] == member)
                closed = set() if any(f["code"] == "maskinfo_syntax_invalid" for f in record["failures"]) else {id(member)}
                expected = _record_from_node(member, data=b"", xml=xml, ordinal=ordinal, root_ordinal=root["root_ordinal"],
                    list_ordinal=entry["mask_list_ordinal"], member_ordinal=mid, oid=parsed["occurrence"]["occurrence_id"], closed=closed)
                require(record == expected)
