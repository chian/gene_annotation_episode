"""Source-bound A111 coordinate/validation reader for one deposited assignment.

Only selected original bytes and literal witnesses are read. Coordinate occupancy
is a deposited atom parameter, never a population measurement. The validation
join is entry/revision metadata, not a coordinate digest or map recomputation.
Native geometry records hold endpoint selectors and selected atom rows; native
local records hold residue selectors, coordinate rows and raw report attributes.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import io
import re
import xml.etree.ElementTree as ET

from Bio.PDB.MMCIF2Dict import MMCIF2Dict

from .domain import REF, obj
from .literature_assay_inputs import (
    SOURCE_KINDS, _Sources, _fail, _finite, _keys, _nullable, _numeric,
    _text, _witness_schema,
)
from .literature_experimental_contracts import ExperimentalContractError

VERSION = "a111_structure_inputs_v1"
SCOPE = "conditional_deposited_model_geometry"
LITERAL_FIELDS = ("molecule", "construct", "experimental_system", "condition", "partner", "experiment")
_ARGS = ("source_ref", "coordinate_source_ref", "validation_source_ref", "source_kind",
         "model_number", "literals", "geometry_panel", "local_panel", "evaluation_scope")
_RESIDUE = ("auth_chain", "auth_seq_id", "insertion_code", "comp_id", "alt_id")
_ENDPOINT = (*_RESIDUE, "atom_names")
_GEOMETRY = ("endpoint_a", "endpoint_b", "positive_max_A", "incompatible_min_A")
_REQUIRED_ATOM = ("group_PDB", "id", "auth_atom_id", "auth_comp_id", "auth_asym_id", "auth_seq_id",
                  "label_alt_id", "pdbx_PDB_ins_code", "Cartn_x", "Cartn_y", "Cartn_z",
                  "occupancy", "B_iso_or_equiv", "pdbx_PDB_model_num")
_SCHEMA_ATTR = "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"


def structure_population_schema():
    """Closed operation arguments; proposed cutoffs are the only numeric points."""
    text = {"type": "string", "format": "structure_identifier"}
    residue = {field: deepcopy(text) for field in _RESIDUE}
    residue["auth_seq_id"] = {"type": "string", "format": "structure_residue_number"}
    residue["insertion_code"] = {"type": "string", "format": "structure_insertion_code"}
    endpoint = obj({**deepcopy(residue), "atom_names": {"type": "array", "minItems": 1,
        "uniqueItems": True, "items": deepcopy(text)}})
    schema = obj({"source_ref": deepcopy(REF), "coordinate_source_ref": deepcopy(REF),
        "validation_source_ref": _nullable(deepcopy(REF)), "source_kind": {"enum": list(SOURCE_KINDS)},
        "model_number": {"type": "integer", "minimum": 1},
        "literals": obj({field: _nullable(_witness_schema()) for field in LITERAL_FIELDS}),
        "geometry_panel": {"type": "array", "items": obj({"endpoint_a": deepcopy(endpoint),
            "endpoint_b": deepcopy(endpoint), "positive_max_A": {"type": "number", "minimum": 0},
            "incompatible_min_A": {"type": "number", "exclusiveMinimum": 0}})},
        "local_panel": {"type": "array", "items": obj(residue)},
        "evaluation_scope": {"enum": [SCOPE]}})
    from .literature_experiment_assessments import assessment_schema
    from .literature_structure_types import EXPERIMENT_TYPES
    schema["properties"]["experiment_assessment"] = assessment_schema(EXPERIMENT_TYPES)
    return schema


def _selector(value, field, *, atoms=False):
    _keys(value, _ENDPOINT if atoms else _RESIDUE, field)
    for name in _RESIDUE:
        if name == "insertion_code":
            if not isinstance(value[name], str) or value[name] in (".", "?") or not re.fullmatch(r"[!-~]*", value[name]):
                _fail("explicit_insertion_code_required", field + "." + name)
        else:
            _text(value[name], field + "." + name)
            shape = r"-?[0-9]+" if name == "auth_seq_id" else r"[!-~]+"
            if not re.fullmatch(shape, value[name]) or value[name] == "?":
                _fail("explicit_identity_required", field + "." + name)
    if atoms:
        names = value["atom_names"]
        if not isinstance(names, list) or not names:
            _fail("nonempty_atom_group_required", field)
        for name in names:
            _text(name, field + ".atom_names")
            if not re.fullmatch(r"[!-~]+", name) or name in (".", "?"):
                _fail("explicit_identity_required", field + ".atom_names")
        if len(set(names)) != len(names):
            _fail("duplicate_atom_selection", field)
    return tuple(value[name] for name in _RESIDUE) + ((tuple(sorted(value["atom_names"])),) if atoms else ())


def _arguments(arguments):
    extra = ("experiment_assessment",) if "experiment_assessment" in arguments else ()
    _keys(arguments, (*_ARGS, *extra), "arguments")
    if extra:
        from .literature_experiment_assessments import validate_assessment
        from .literature_structure_types import EXPERIMENT_TYPES
        validate_assessment(arguments["experiment_assessment"], EXPERIMENT_TYPES)
    if arguments["source_kind"] not in SOURCE_KINDS:
        _fail("unknown_source_kind", "source_kind")
    if arguments["evaluation_scope"] != SCOPE:
        _fail("unsupported_evaluation_scope", "evaluation_scope")
    if type(arguments["model_number"]) is not int or arguments["model_number"] < 1:
        _fail("positive_integer_model_required", "model_number")
    _keys(arguments["literals"], LITERAL_FIELDS, "literals")
    for panel in ("geometry_panel", "local_panel"):
        if not isinstance(arguments[panel], list):
            _fail("panel_list_required", panel)
    seen = set()
    for i, item in enumerate(arguments["geometry_panel"]):
        field = f"geometry_panel[{i}]"
        _keys(item, _GEOMETRY, field)
        a = _selector(item["endpoint_a"], field + ".endpoint_a", atoms=True)
        b = _selector(item["endpoint_b"], field + ".endpoint_b", atoms=True)
        physical = tuple(sorted((a, b)))
        if physical in seen:
            _fail("duplicate_geometry_selection", field)
        seen.add(physical)
        for cutoff in ("positive_max_A", "incompatible_min_A"):
            _finite(item[cutoff], field + "." + cutoff)
        if item["positive_max_A"] < 0 or item["incompatible_min_A"] <= item["positive_max_A"]:
            _fail("disjoint_geometry_cutoffs_required", field)
    seen = set()
    for i, item in enumerate(arguments["local_panel"]):
        key = _selector(item, f"local_panel[{i}]")
        if key in seen:
            _fail("duplicate_local_selection", f"local_panel[{i}]")
        seen.add(key)


def _positive_integer(token, field):
    if not isinstance(token, str) or not re.fullmatch(r"[1-9][0-9]*", token):
        _fail("positive_integer_source_field_required", field)
    return int(token)


def _date(token, field):
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", token):
            raise ValueError()
        date.fromisoformat(token)
    except (TypeError, ValueError):
        _fail("iso_date_required", field)
    return token


def _entry(token, field):
    if not isinstance(token, str) or not re.fullmatch(r"[0-9][A-Za-z0-9]{3}", token):
        _fail("pdb_accession_required", field)
    return token.lower()


def _point(token, field, *, minimum=None, maximum=None):
    if token in (".", "?"):
        return None
    value = _numeric(token, field)
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        _fail("native_value_out_of_range", field)
    return value


class _QuotedToken(str):
    """A literal token must not activate MMCIF2Dict's syntax comparisons."""

    def startswith(self, *_args, **_kwargs):
        return False

    def lower(self):
        # Only parser/control comparisons use this while the token is wrapped.
        # Parsed keys/values are converted back to ordinary strings below.
        return "\0quoted:" + str.lower(self)


class _UniqueCIF(MMCIF2Dict):
    """Installed dictionary parser with quote-aware lexical token provenance.

    Bio.PDB's dictionary algorithm compares token spellings with control words
    and underscores. Its stock tokenizer discards whether they were quoted.
    These tokenizer adaptations preserve that single distinction, including
    semicolon text fields; the installed parser still parses the original text.
    """

    def __setitem__(self, key, value):
        if key in self:
            _fail("duplicate_cif_field", key)
        super().__setitem__(key, value)

    def _splitline(self, line):
        in_token, quote = False, None
        start = 0
        for i, char in enumerate(line):
            if char in self.whitespace_chars:
                if in_token and quote is None:
                    in_token = False
                    yield line[start:i]
            elif char in self.quote_chars:
                if quote is None and not in_token:
                    quote, in_token, start = char, True, i + 1
                elif char == quote and (i + 1 == len(line) or line[i + 1] in self.whitespace_chars):
                    quote, in_token = None, False
                    yield _QuotedToken(line[start:i])
            elif char == "#" and not in_token:
                return
            elif not in_token:
                in_token, start = True, i
        if quote is not None:
            raise ValueError("Line ended with quote open")
        if in_token:
            yield line[start:]

    def _tokenize(self, handle):
        for line in handle:
            if line.startswith("#"):
                continue
            if line.startswith(";"):
                buffer = [line[1:].rstrip()]
                for line in handle:
                    line = line.rstrip()
                    if line.startswith(";"):
                        yield _QuotedToken("\n".join(buffer))
                        line = line[1:]
                        if line and line[0] not in self.whitespace_chars:
                            raise ValueError("Missing whitespace after semicolon")
                        break
                    buffer.append(line)
                else:
                    raise ValueError("Missing closing semicolon")
            yield from self._splitline(line.strip())


def _cif(raw):
    try:
        text = raw.decode("utf-8")
        # MMCIF2Dict is intentionally permissive about dangling scalar fields,
        # repeated blocks and incomplete loops. Audit its own tokenizer's stream
        # before consuming its parsed dictionary; no alternate parser is used.
        parser = _UniqueCIF(io.StringIO(text))
        tokens = list(parser._tokenize(io.StringIO(text)))
        if not tokens or not tokens[0].startswith("data_") or len(tokens[0]) <= 5:
            _fail("malformed_structure_source", "coordinate_source_ref")
        i = 1
        while i < len(tokens):
            token = tokens[i]
            if token.lower() == "loop_":
                i += 1
                start = i
                while i < len(tokens) and tokens[i].startswith("_"):
                    i += 1
                columns = i - start
                values = i
                while i < len(tokens) and not (tokens[i].startswith("_") or tokens[i].lower() in ("loop_", "stop_", "global_") or tokens[i].lower().startswith(("data_", "save_"))):
                    i += 1
                if columns == 0 or i == values or (i - values) % columns:
                    _fail("malformed_structure_source", "coordinate_source_ref")
            elif token.startswith("_") and i + 1 < len(tokens):
                value = tokens[i + 1]
                if value.startswith("_") or value.lower() in ("loop_", "stop_", "global_") or value.lower().startswith(("data_", "save_")):
                    _fail("malformed_structure_source", "coordinate_source_ref")
                i += 2
            else:
                _fail("malformed_structure_source", "coordinate_source_ref")
        return {str(key): [str(item) for item in value] if isinstance(value, list) else str(value)
                for key, value in parser.items()}
    except ExperimentalContractError:
        raise
    except (UnicodeDecodeError, ValueError, IndexError, ZeroDivisionError, RecursionError) as error:
        raise ExperimentalContractError("malformed_structure_source", "coordinate_source_ref") from error


def _scalar(cif, name, *, optional=False):
    values = cif.get(name)
    if values is None and optional:
        return None
    if not isinstance(values, list) or len(values) != 1:
        _fail("scalar_structure_field_required", name)
    return values[0]


def _coordinate(source, reference, model):
    cif = _cif(source["content"])
    entry_id = _entry(_scalar(cif, "_entry.id"), "_entry.id")
    revision_names = ("_pdbx_audit_revision_history.ordinal", "_pdbx_audit_revision_history.revision_date")
    revisions = [cif.get(name) for name in revision_names]
    revision_number = revision_date = None
    if any(item is not None for item in revisions):
        if any(not isinstance(item, list) or not item for item in revisions) or len(revisions[0]) != len(revisions[1]):
            _fail("revision_columns_required", "coordinate_source_ref")
        pairs = [(_positive_integer(n, revision_names[0]), _date(d, revision_names[1]))
                 for n, d in zip(*revisions)]
        if len({n for n, _ in pairs}) != len(pairs):
            _fail("duplicate_source_revision", revision_names[0])
        revision_number, revision_date = max(pairs)
    columns = {key[11:]: value for key, value in cif.items() if key.startswith("_atom_site.")}
    if any(name not in columns for name in _REQUIRED_ATOM):
        _fail("required_atom_columns_missing", "coordinate_source_ref")
    lengths = {len(value) for value in columns.values()}
    if len(lengths) != 1 or not next(iter(lengths)):
        _fail("unequal_or_empty_atom_columns", "coordinate_source_ref")
    rows = []
    for index in range(next(iter(lengths))):
        raw = {key: value[index] for key, value in columns.items()}
        path = f"atom_site[{index}]"
        number = _positive_integer(raw["pdbx_PDB_model_num"], path + ".pdbx_PDB_model_num")
        for field in ("id", "auth_atom_id", "auth_comp_id", "auth_asym_id", "auth_seq_id", "label_alt_id"):
            _text(raw[field], path + "." + field)
            if raw[field].strip() != raw[field] or raw[field] in (".", "?") and field != "label_alt_id":
                _fail("invalid_atom_identity", path + "." + field)
        if not re.fullmatch(r"-?[0-9]+", raw["auth_seq_id"]):
            _fail("invalid_residue_number", path + ".auth_seq_id")
        if raw["group_PDB"] not in ("ATOM", "HETATM"):
            _fail("invalid_atom_group", path + ".group_PDB")
        xyz = [_point(raw[axis], path + "." + axis) for axis in ("Cartn_x", "Cartn_y", "Cartn_z")]
        rows.append({"row_index": index, "raw_attributes": raw, "model_number": number,
            "auth_chain": raw["auth_asym_id"], "auth_seq_id": raw["auth_seq_id"],
            "insertion_code": "" if raw["pdbx_PDB_ins_code"] in (".", "?") else raw["pdbx_PDB_ins_code"],
            "comp_id": raw["auth_comp_id"], "alt_id": raw["label_alt_id"], "atom_name": raw["auth_atom_id"],
            "coordinates_A": xyz, "occupancy_parameter": _point(raw["occupancy"], path + ".occupancy", minimum=0, maximum=1),
            "B_iso_or_equiv_A2": _point(raw["B_iso_or_equiv"], path + ".B_iso_or_equiv", minimum=0),
            "source_ref": reference, "artifact_ref": source["artifact_ref"]})
    models = sorted({row["model_number"] for row in rows})
    if model not in models:
        _fail("selected_model_unavailable", "model_number")
    metadata = {"entry_id": entry_id, "revision_number": revision_number, "revision_date": revision_date,
        "method": deepcopy(cif.get("_exptl.method")), "model_numbers": models,
        "coordinate_unit": "angstrom", "source_ref": reference, "artifact_ref": source["artifact_ref"],
        "raw_fields": {key: deepcopy(value) for key, value in cif.items()
            if key.startswith(("_entry.", "_pdbx_audit_revision_history.", "_exptl."))}}
    return metadata, rows


def _validation(source, reference):
    try:
        text = source["content"].decode("utf-8")
        if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
            _fail("xml_declarations_forbidden", "validation_source_ref")
        root = ET.fromstring(text)
    except ExperimentalContractError:
        raise
    except (UnicodeDecodeError, ET.ParseError, ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_validation_source", "validation_source_ref") from error
    entries = list(root.iter("Entry"))
    if root.tag != "wwPDB-validation-information" or len(entries) != 1:
        _fail("single_validation_entry_required", "validation_source_ref")
    entry = entries[0].attrib
    raw_id = entry.get("pdbid")
    entry_id = _entry(raw_id, "Entry.pdbid") if raw_id not in (None, "", ".", "?") else None
    raw_n, raw_d = entry.get("PDB-revision-number"), entry.get("PDB-revision-date")
    number = _positive_integer(raw_n, "Entry.PDB-revision-number") if raw_n not in (None, "", ".", "?") else None
    day = _date(raw_d, "Entry.PDB-revision-date") if raw_d not in (None, "", ".", "?") else None
    metadata = {"entry_id": entry_id, "revision_number": number, "revision_date": day,
        "creation_date": entry.get("XMLcreationDate"), "schema_location": root.attrib.get(_SCHEMA_ATTR),
        "raw_entry_attributes": dict(entry), "raw_root_attributes": dict(root.attrib),
        "source_ref": reference, "artifact_ref": source["artifact_ref"]}
    rows = []
    for index, node in enumerate(root.iter("ModelledSubgroup")):
        raw = dict(node.attrib)
        for field in ("model", "chain", "resnum", "icode", "altcode", "resname"):
            if field not in raw:
                _fail("validation_identity_required", f"ModelledSubgroup[{index}].{field}")
        model = _positive_integer(raw["model"], "ModelledSubgroup.model")
        for field in ("chain", "resnum", "resname"):
            _text(raw[field], "ModelledSubgroup." + field)
        if not re.fullmatch(r"-?[0-9]+", raw["resnum"]):
            _fail("invalid_residue_number", "ModelledSubgroup.resnum")
        rows.append({"row_index": index, "model_number": model, "auth_chain": raw["chain"],
            "auth_seq_id": raw["resnum"], "insertion_code": "" if not raw["icode"].strip() else raw["icode"],
            "alt_id": "." if not raw["altcode"].strip() else raw["altcode"], "comp_id": raw["resname"],
            "rscc": _point(raw.get("rscc", "?"), "ModelledSubgroup.rscc", minimum=-1, maximum=1),
            "raw_attributes": raw, "source_ref": reference, "artifact_ref": source["artifact_ref"]})
    return metadata, rows


def _residue_rows(selector, rows, model):
    return [row for row in rows if row["model_number"] == model and all(
        row[name] == selector[name] for name in ("auth_chain", "auth_seq_id", "insertion_code"))]


def _selected_residue(selector, rows, model):
    at_site = _residue_rows(selector, rows, model)
    selected = [row for row in at_site if row["comp_id"] == selector["comp_id"] and row["alt_id"] == selector["alt_id"]]
    return at_site, selected


def _endpoint(selector, rows, model):
    at_site, residue = _selected_residue(selector, rows, model)
    selected, reason = [], None
    for atom in selector["atom_names"]:
        matches = [row for row in residue if row["atom_name"] == atom]
        selected.extend(matches)
        if len(matches) > 1:
            reason = "ambiguous_atom_selection"
        elif not matches and reason != "ambiguous_atom_selection":
            reason = "endpoint_identity_mismatch" if at_site and not residue else "endpoint_unmodeled"
        elif any(value is None for row in matches for value in row["coordinates_A"]) and reason is None:
            reason = "coordinate_unreported"
    points = None if reason else [deepcopy(row["coordinates_A"]) for row in selected]
    return {"selector": deepcopy(selector), "selected_atom_rows": deepcopy(selected),
            "coordinates_A": points, "unavailable_reason": reason}


def _local(selector, atom_rows, report_rows, model, *, supplied):
    at_site, coordinate = _selected_residue(selector, atom_rows, model)
    candidates = [row for row in report_rows if row["model_number"] == model and all(
        row[name] == selector[name] for name in ("auth_chain", "auth_seq_id", "insertion_code", "alt_id"))]
    reason = None
    if not coordinate:
        reason = "local_identity_mismatch" if at_site else "local_endpoint_unmodeled"
    elif len(candidates) > 1:
        reason = "ambiguous_local_selection"
    elif candidates and candidates[0]["comp_id"] != selector["comp_id"]:
        reason = "local_identity_mismatch"
    elif not supplied or not candidates or candidates[0]["rscc"] is None:
        reason = "local_rscc_unreported"
    value = None if reason else candidates[0]["rscc"]
    return {"selector": deepcopy(selector), "coordinate_atom_rows": deepcopy(coordinate),
        "validation_rows": deepcopy(candidates), "rscc": value, "unavailable_reason": reason}


def _binding(coordinate, validation):
    if validation is None:
        return "not_supplied"
    if validation["entry_id"] is not None and coordinate["entry_id"] != validation["entry_id"]:
        return "entry_mismatch"
    fields = ("entry_id", "revision_number", "revision_date")
    if any(record[field] is None for record in (coordinate, validation) for field in fields):
        return "binding_unreported"
    if any(coordinate[field] != validation[field] for field in ("revision_number", "revision_date")):
        return "revision_mismatch"
    return "matching_entry_revision"


def read_structure_inputs(arguments, *, read_source):
    """Read selected authoritative bytes, preserving incomplete scientific panels."""
    _arguments(arguments)
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    literals = {}
    for field, item in arguments["literals"].items():
        witness = sources.witness(item, "literals." + field) if item is not None else None
        literals[field] = {"value": witness["quote"], "witness": witness} if witness else None
    coordinate, atoms = _coordinate(sources.source(arguments["coordinate_source_ref"], "original"),
                                   arguments["coordinate_source_ref"], arguments["model_number"])
    validation, report = None, []
    if arguments["validation_source_ref"] is not None:
        validation, report = _validation(sources.source(arguments["validation_source_ref"], "original"),
                                         arguments["validation_source_ref"])
    native_geometry, members = [], []
    for index, item in enumerate(arguments["geometry_panel"]):
        endpoints = {name: _endpoint(item[name], atoms, arguments["model_number"])
                     for name in ("endpoint_a", "endpoint_b")}
        reason = next((endpoints[name]["unavailable_reason"] for name in endpoints
                       if endpoints[name]["unavailable_reason"] is not None), None)
        native_geometry.append({"member_index": index, **endpoints,
            "positive_max_A": item["positive_max_A"], "incompatible_min_A": item["incompatible_min_A"]})
        members.append({**{name: endpoints[name]["coordinates_A"] for name in endpoints},
            "positive_max_A": item["positive_max_A"], "incompatible_min_A": item["incompatible_min_A"],
            "unavailable_reason": reason})
    native_local = [_local(item, atoms, report, arguments["model_number"], supplied=validation is not None)
                    for item in arguments["local_panel"]]
    return {"version": VERSION, **{field: deepcopy(arguments[field]) for field in (
        "source_ref", "source_kind", "coordinate_source_ref", "validation_source_ref", "model_number", "evaluation_scope")},
        "literals": literals, "source_refs": list(sources.references), "coordinate_metadata": coordinate,
        "validation_metadata": validation, "native_geometry": native_geometry, "native_local": native_local,
        "calculation_inputs": {"geometry_members": members, "local_members": [
            {"rscc": item["rscc"], "unavailable_reason": item["unavailable_reason"]} for item in native_local],
            "validation_binding": _binding(coordinate, validation),
            "origin": "synthetic" if arguments["source_kind"] == "synthetic_fixture" else "reported",
            "evaluation_scope": SCOPE}}


__all__ = ["VERSION", "SCOPE", "LITERAL_FIELDS", "structure_population_schema", "read_structure_inputs"]
