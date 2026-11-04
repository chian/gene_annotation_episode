"""Lossless token/table readers for explicitly supplied PDB 3.x and CIF 1.x.

Original bytes are caller-retained. All rows, lexical spellings, byte spans,
models and alternatives survive; malformed content never becomes repaired atoms.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import math
import re

from .protein_structure_contracts import (
    FileIdentity, BlockSelection, ParsedStructure, NativeToken, NativeNumber,
    canonical, issue, same, validate_file_identity, validate_parsed_structure,
)


def absent_token() -> NativeToken:
    return {"lexeme": None, "text": None, "syntax": "absent", "lexical_state": "absent", "span": None}


def token_text(token):
    return token["text"] if token["lexical_state"] == "value" else None


def pdb_field(record, start, end) -> NativeToken:
    text = record["text"].rstrip("\r\n")
    if len(text) <= start:
        return absent_token()
    lexeme = text[start:end]
    offset = record["span"]["start_0based"]
    return {"lexeme": lexeme, "text": lexeme, "syntax": "pdb_field",
            "lexical_state": "value" if lexeme.strip() else "pdb_blank",
            "span": {"start_0based": offset + len(text[:start].encode("utf-8")),
                     "end_exclusive": offset + len(text[:min(end, len(text))].encode("utf-8"))}}


_NUMBER = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:\((\d+)\))?([eE][+-]?\d+)?$")
# A suffix after the exponent is also a conventional CIF uncertainty spelling.
_NUMBER_AFTER_EXP = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))([eE][+-]?\d+)\((\d+)\)$")


def native_number(token: NativeToken) -> NativeNumber:
    value = None
    uncertainty = None
    state = "missing" if token["lexical_state"] != "value" else "invalid"
    if state != "missing":
        text = token["text"].strip() if token["syntax"] == "pdb_field" else token["text"]
        match = _NUMBER.fullmatch(text)
        if match:
            mantissa, digits, exponent = match.groups()
        else:
            match = _NUMBER_AFTER_EXP.fullmatch(text)
            if match:
                mantissa, exponent, digits = match.groups()
        if match:
            try:
                exponent_number = int((exponent or "e0")[1:])
                value = float(Decimal(mantissa) * (Decimal(10) ** exponent_number))
                if digits is not None:
                    decimals = len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
                    uncertainty = float(Decimal(digits) * (Decimal(10) ** (exponent_number - decimals)))
                if math.isfinite(value) and (uncertainty is None or math.isfinite(uncertainty)):
                    state = "present"
                else:
                    value = uncertainty = None
            except (InvalidOperation, ValueError, OverflowError):
                value = uncertainty = None
    return {"token": deepcopy(token), "value": value, "state": state,
            "embedded_standard_uncertainty": uncertainty}


def native_integer(token, *, positive=False):
    text = token_text(token)
    if text is None or re.fullmatch(r"[+-]?\d+", text.strip()) is None:
        return None
    value = int(text)
    return value if not positive or value > 0 else None


def _input(data, file_identity, expected):
    identity = validate_file_identity(file_identity)
    if type(data) is not bytes:
        raise ValueError("invalid_schema")
    if identity["format"] != expected:
        raise ValueError("unsupported_format")
    if len(data) != identity["byte_length"] or hashlib.sha256(data).hexdigest() != identity["sha256"]:
        raise ValueError("input_digest_mismatch")
    return identity


def _empty(identity):
    return {"version": "protein_structure_parsed_v1", "file_identity": identity,
            "state": "complete", "pdb_records": [], "cif_blocks": [], "atoms": [],
            "models": [], "chains": [], "unparsed_spans": [], "issues": []}


def _undecodable(identity):
    parsed = _empty(identity)
    parsed.update(state="invalid", unparsed_spans=[{"start_0based": 0, "end_exclusive": identity["byte_length"]}],
                  issues=[issue("unsupported_format", field="file_identity")])
    return parsed


def _pdb_contexts(records):
    """Original model/TER context of every coordinate or uncertainty record."""
    current = None
    models, contexts, issues, segments = [], {}, [], {}
    explicit_seen = False
    serials = set()
    for record in records:
        name = record["record_name"]
        if name == "MODEL":
            if current is not None:
                issues.append(issue("malformed_record", field="model_key"))
            token = pdb_field(record, 10, 14)
            serial = native_integer(token)
            model = {"ordinal_0based": len(models), "native_serial_token": token,
                     "serial_state": "explicit" if token["lexical_state"] == "value" else "missing"}
            if serial is None or serial in serials:
                issues.append(issue("conflicting_identity" if serial in serials else "malformed_record", field="model_key"))
            if serial is not None:
                serials.add(serial)
            models.append(model)
            current, explicit_seen, segments = model, True, {}
        elif name == "ENDMDL":
            if current is None:
                issues.append(issue("malformed_record", field="model_key"))
            current, segments = None, {}
        elif name in ("ATOM", "HETATM", "TER", "ANISOU", "SIGUIJ", "SIGATM"):
            if current is None:
                current = {"ordinal_0based": len(models), "native_serial_token": absent_token(), "serial_state": "implicit"}
                models.append(current)
                if explicit_seen:
                    issues.append(issue("malformed_record", field="model_key"))
            chain = pdb_field(record, 21, 22)["text"]
            if chain is not None and len(chain) == 1:
                chain_key = {"namespace": "pdb", "chain_id": chain, "ter_segment_ordinal_0based": segments.get(chain, 0)}
                contexts[record["record_key"]] = (current, chain_key)
                if name == "TER":
                    segments[chain] = segments.get(chain, 0) + 1
    if explicit_seen and current is not None and current["serial_state"] != "implicit":
        issues.append(issue("malformed_record", field="model_key"))
    return models, contexts, issues


def pdb_residue_identity(record, file_sha256, context, *, record_class=None):
    number = native_integer(pdb_field(record, 22, 26))
    component = token_text(pdb_field(record, 17, 20))
    insertion = pdb_field(record, 26, 27)["text"]
    if context is None or number is None or component is None or insertion is None or len(insertion) != 1:
        return None
    model, chain = context
    return {"format": "pdb_3x_text", "position_key": {"namespace": "pdb", "file_sha256": file_sha256,
        "block_ordinal_0based": None, "model_key": deepcopy(model), "chain_key": deepcopy(chain),
        "residue_number": number, "insertion_code": insertion},
        "record_class": record_class or record["record_name"], "component_id": component.strip()}


def _atom_issues(atom):
    key = atom["identity"]["atom_row_key"]
    if atom["identity"]["residue"] is None:
        atom["issues"].append(issue("invalid_coordinate_identity", atom=key, field="atom_identity"))
    if any(x["state"] != "present" for x in atom["xyz_A"]):
        atom["issues"].append(issue("nonfinite_coordinate", atom=key, field="xyz"))
    occupancy = atom["occupancy"]
    if occupancy["state"] == "invalid" or occupancy["state"] == "present" and not 0 <= occupancy["value"] <= 1:
        atom["issues"].append(issue("invalid_occupancy", atom=key, field="occupancy"))
    atom["state"] = "invalid" if atom["issues"] else "partial" if occupancy["state"] != "present" or atom["b_iso"]["state"] != "present" else "valid"


def _add_inventory(parsed, model, block, atom, chain, auth=None, entity=None):
    key = atom["identity"]["atom_row_key"]
    for row in parsed["models"]:
        if row["block_ordinal_0based"] == block and same(row["model_key"], model):
            row["atom_row_keys"].append(key)
            break
    if chain is None:
        return
    row = next((r for r in parsed["chains"] if r["block_ordinal_0based"] == block and same(r["model_key"], model) and same(r["chain_key"], chain)), None)
    if row is None:
        row = {"block_ordinal_0based": block, "model_key": deepcopy(model), "chain_key": deepcopy(chain),
               "auth_chain_tokens": [], "entity_tokens": [], "atom_row_keys": []}
        parsed["chains"].append(row)
    row["atom_row_keys"].append(key)
    for field, value in (("auth_chain_tokens", auth), ("entity_tokens", entity)):
        if value is not None and not any(x["lexical_state"] == value["lexical_state"] and x["text"] == value["text"] for x in row[field]):
            row[field].append(deepcopy(value))


def _finish(parsed):
    # Duplicate physical atom sites remain separate rows, both disqualified.
    groups = {}
    for atom in parsed["atoms"]:
        identity = atom["identity"]
        if identity["residue"] is None:
            continue
        residue = identity["residue"]
        if residue["format"] == "pdbx_mmcif_text":
            # Token spans are provenance, not different physical identities.
            rkey = {k: (x["text"], x["lexical_state"]) if isinstance(x, dict) and "lexical_state" in x else x for k, x in residue.items()}
        else:
            rkey = residue
        signature = canonical([rkey, identity["atom_name"]["text"], identity["alt_id"]["text"], identity["alt_id"]["lexical_state"]])
        groups.setdefault(signature, []).append(atom)
    for group in groups.values():
        if len(group) > 1:
            for atom in group:
                atom["state"] = "invalid"
                atom["issues"].append(issue("conflicting_identity", atom=atom["identity"]["atom_row_key"], field="atom_identity"))
    if parsed["issues"] or any(a["state"] != "valid" for a in parsed["atoms"]) or any(b["state"] != "complete" for b in parsed["cif_blocks"]):
        parsed["state"] = "partial" if parsed["atoms"] or parsed["cif_blocks"] or parsed["pdb_records"] else "invalid"
    return validate_parsed_structure(parsed)


def parse_pdb_structure(data: bytes, *, file_identity: FileIdentity) -> ParsedStructure:
    identity = _input(data, file_identity, "pdb_3x_text")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        return _undecodable(identity)
    if "\0" in text or text.lstrip().startswith(("data_", "loop_", "{")):
        return _undecodable(identity)
    parsed = _empty(identity)
    offset = 0
    for line_number, line in enumerate(text.splitlines(keepends=True), 1):
        parsed["pdb_records"].append({"record_key": f"pdb_line_{line_number}", "line_1based": line_number,
            "span": {"start_0based": offset, "end_exclusive": offset + len(line)}, "text": line,
            "record_name": line[:6].strip()})
        offset += len(line)
    models, contexts, problems = _pdb_contexts(parsed["pdb_records"])
    parsed["issues"].extend(problems)
    parsed["models"] = [{"block_ordinal_0based": None, "model_key": m, "atom_row_keys": []} for m in models]
    for record in parsed["pdb_records"]:
        if record["record_name"] not in ("ATOM", "HETATM"):
            continue
        context = contexts.get(record["record_key"])
        residue = pdb_residue_identity(record, identity["sha256"], context)
        atom = {"identity": {"atom_row_key": record["record_key"], "residue": residue,
            "serial_or_atom_site_id": pdb_field(record, 6, 11), "atom_name": pdb_field(record, 12, 16),
            "auth_atom_name": absent_token(), "alt_id": pdb_field(record, 16, 17),
            "element": pdb_field(record, 76, 78), "formal_charge": pdb_field(record, 78, 80)},
            "xyz_A": [native_number(pdb_field(record, s, s + 8)) for s in (30, 38, 46)],
            "occupancy": native_number(pdb_field(record, 54, 60)),
            "b_iso": native_number(pdb_field(record, 60, 66)), "state": "valid", "issues": []}
        _atom_issues(atom)
        parsed["atoms"].append(atom)
        if context:
            _add_inventory(parsed, context[0], None, atom, context[1])
    if not parsed["pdb_records"] or not any(r["record_name"] in {"HEADER", "ATOM", "HETATM", "MODEL", "SEQRES", "END", "REMARK", "EXPDTA", "TITLE", "COMPND"} for r in parsed["pdb_records"]):
        parsed["issues"].append(issue("unsupported_format", field="file_identity"))
    return _finish(parsed)


def _cif_tokens(text):
    """CIF lexical tokens plus exact comment/invalid spans; no shell-style quoting."""
    byte_offsets = [0]
    for ch in text:
        byte_offsets.append(byte_offsets[-1] + len(ch.encode("utf-8")))
    tokens, ignored, problems, malformed_spans = [], [], [], []
    n, i = len(text), 0
    def span(a, b):
        return {"start_0based": byte_offsets[a], "end_exclusive": byte_offsets[b]}
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        start = i
        if text[i] == "#":
            i = text.find("\n", i)
            if i < 0:
                i = n
            ignored.append(span(start, i))
            continue
        syntax = "bare"
        if text[i] == ";" and (i == 0 or text[i - 1] == "\n"):
            syntax = "semicolon"
            end = re.search(r"\n;(?=[ \t\r\n]|$)", text[i + 1:])
            if end is None:
                ignored.append(span(i, n)); malformed_spans.append(span(i, n))
                problems.append(issue("malformed_record", field="native_metadata")); break
            closing = i + 1 + end.start() + 1
            i = closing + 1
            value = text[start + 1:closing]
            if value.endswith("\r\n"):
                value = value[:-2]
            elif value.endswith("\n"):
                value = value[:-1]
        elif text[i] in "'\"":
            quote = text[i]
            syntax = "single_quoted" if quote == "'" else "double_quoted"
            i += 1
            while i < n and not (text[i] == quote and (i + 1 == n or text[i + 1].isspace())):
                if text[i] in "\r\n":
                    break
                i += 1
            if i >= n or text[i] != quote:
                end = text.find("\n", i)
                i = n if end < 0 else end
                ignored.append(span(start, i)); malformed_spans.append(span(start, i))
                problems.append(issue("malformed_record", field="native_metadata")); continue
            value = text[start + 1:i]
            i += 1
        else:
            while i < n and not text[i].isspace():
                i += 1
            value = text[start:i]
        lexeme = text[start:i]
        state = "cif_unknown" if syntax == "bare" and value == "?" else "cif_not_applicable" if syntax == "bare" and value == "." else "value"
        tokens.append({"lexeme": lexeme, "text": value, "syntax": syntax, "lexical_state": state, "span": span(start, i)})
    return tokens, ignored, problems, malformed_spans


def _reserved(token):
    if token["syntax"] != "bare":
        return False
    value = token["text"].lower()
    return value.startswith(("_", "data_", "save_")) or value in ("loop_", "stop_", "global_")


def category_rows(parsed, block_ordinal, category):
    """All native rows for a category, with scalar fields joined only within a block."""
    if block_ordinal >= len(parsed["cif_blocks"]):
        return []
    category = category.lower().rstrip(".") + "."
    result, scalar, scalar_keys = [], {}, []
    for table in parsed["cif_blocks"][block_ordinal]["tables"]:
        tags = [t["text"].lower() for t in table["tags"]]
        columns = [(i, tag[len(category):]) for i, tag in enumerate(tags) if tag.startswith(category)]
        if not columns:
            continue
        for key, row in zip(table["row_keys"], table["rows"]):
            values = {name: row[i] for i, name in columns}
            if table["form"] == "scalar":
                scalar.update(values); scalar_keys.append(key)
            else:
                result.append((key, values))
    if scalar:
        result.insert(0, (scalar_keys[0], scalar))
    return result


def get_token(row, name):
    return row.get(name.lower(), absent_token())


def _cif_atoms(parsed):
    for block in parsed["cif_blocks"]:
        ordinal = block["ordinal_0based"]
        model_by_native = {}
        for key, row in category_rows(parsed, ordinal, "_atom_site"):
            mtoken = get_token(row, "pdbx_pdb_model_num")
            mkey = (mtoken["lexical_state"], mtoken["text"])
            if mkey not in model_by_native:
                model = {"ordinal_0based": len(model_by_native), "native_serial_token": deepcopy(mtoken),
                         "serial_state": "explicit" if mtoken["lexical_state"] == "value" else "missing"}
                model_by_native[mkey] = model
                parsed["models"].append({"block_ordinal_0based": ordinal, "model_key": model, "atom_row_keys": []})
            model = model_by_native[mkey]
            residue = {"format": "pdbx_mmcif_text", "file_sha256": parsed["file_identity"]["sha256"],
                       "block_ordinal_0based": ordinal, "model_key": deepcopy(model)}
            for field, tag in (("label_asym_id", "label_asym_id"), ("auth_asym_id", "auth_asym_id"), ("label_entity_id", "label_entity_id"), ("label_seq_id", "label_seq_id"), ("auth_seq_id", "auth_seq_id"), ("insertion_code", "pdbx_pdb_ins_code"), ("label_comp_id", "label_comp_id"), ("auth_comp_id", "auth_comp_id"), ("group_pdb", "group_pdb")):
                residue[field] = deepcopy(get_token(row, tag))
            chain_id = token_text(residue["label_asym_id"])
            if not chain_id or not token_text(residue["label_comp_id"]):
                residue = None
            atom = {"identity": {"atom_row_key": key, "residue": residue,
                "serial_or_atom_site_id": get_token(row, "id"), "atom_name": get_token(row, "label_atom_id"),
                "auth_atom_name": get_token(row, "auth_atom_id"), "alt_id": get_token(row, "label_alt_id"),
                "element": get_token(row, "type_symbol"), "formal_charge": get_token(row, "pdbx_formal_charge")},
                "xyz_A": [native_number(get_token(row, "cartn_" + axis)) for axis in "xyz"],
                "occupancy": native_number(get_token(row, "occupancy")), "b_iso": native_number(get_token(row, "b_iso_or_equiv")),
                "state": "valid", "issues": []}
            _atom_issues(atom)
            parsed["atoms"].append(atom)
            _add_inventory(parsed, model, ordinal, atom,
                {"namespace": "label_asym_id", "label_asym_id": chain_id} if chain_id else None,
                get_token(row, "auth_asym_id"), get_token(row, "label_entity_id"))


def parse_mmcif_structure(data: bytes, *, file_identity: FileIdentity,
                         data_block: BlockSelection | None) -> ParsedStructure:
    identity = _input(data, file_identity, "pdbx_mmcif_text")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _undecodable(identity)
    if "\0" in text or text.startswith("#\\#CIF_2"):
        return _undecodable(identity)
    parsed = _empty(identity)
    tokens, ignored, problems, malformed_spans = _cif_tokens(text)
    parsed["issues"].extend(problems)
    parsed["unparsed_spans"].extend(ignored)
    block, i, seen_tags = None, 0, set()
    while i < len(tokens):
        token = tokens[i]; lower = token["text"].lower()
        if token["syntax"] == "bare" and lower.startswith("data_"):
            if block is not None:
                block["span"]["end_exclusive"] = token["span"]["start_0based"]
            block = {"ordinal_0based": len(parsed["cif_blocks"]), "name": token["text"][5:],
                "span": {"start_0based": token["span"]["start_0based"], "end_exclusive": len(data)},
                "state": "complete", "tables": [], "unparsed_spans": []}
            if not block["name"] or any(b["name"].lower() == block["name"].lower() for b in parsed["cif_blocks"]):
                block["state"] = "invalid"; parsed["issues"].append(issue("conflicting_identity", field="data_block"))
            parsed["cif_blocks"].append(block); seen_tags = set(); i += 1; continue
        if block is None:
            parsed["unparsed_spans"].append(token["span"]); parsed["issues"].append(issue("malformed_record", field="data_block")); i += 1; continue
        if token["syntax"] == "bare" and (lower == "loop_" or lower.startswith("_")):
            loop = lower == "loop_"
            tags, values, begin = [], [], i
            if loop:
                i += 1
                while i < len(tokens) and tokens[i]["syntax"] == "bare" and tokens[i]["text"].startswith("_"):
                    tags.append(tokens[i]); i += 1
                while i < len(tokens) and not _reserved(tokens[i]):
                    values.append(tokens[i]); i += 1
            else:
                tags.append(token); i += 1
                if i < len(tokens) and not _reserved(tokens[i]):
                    values.append(tokens[i]); i += 1
            malformed = not tags or not values or len(values) % len(tags) != 0
            repeated = any(t["text"].lower() in seen_tags for t in tags) or len({t["text"].lower() for t in tags}) != len(tags)
            seen_tags.update(t["text"].lower() for t in tags)
            if malformed or repeated:
                block["state"] = "invalid"
                parsed["issues"].append(issue("malformed_cif_loop" if malformed and loop else "conflicting_identity" if repeated else "malformed_record", field="native_metadata"))
            count = len(values) // len(tags) if tags else 0
            table_key = f"cif_block_{block['ordinal_0based']}_table_{len(block['tables'])}"
            block["tables"].append({"table_key": table_key, "form": "loop" if loop else "scalar", "tags": tags,
                "rows": [values[j * len(tags):(j + 1) * len(tags)] for j in range(count)],
                "row_keys": [f"{table_key}_row_{j}" for j in range(count)]})
            if malformed:
                tail = values[count * len(tags):]
                start = tail[0]["span"]["start_0based"] if tail else tokens[begin]["span"]["start_0based"]
                end = tokens[max(begin, i - 1)]["span"]["end_exclusive"]
                block["unparsed_spans"].append({"start_0based": start, "end_exclusive": end})
            continue
        block["state"] = "invalid"; block["unparsed_spans"].append(token["span"])
        parsed["issues"].append(issue("malformed_record", field="native_metadata")); i += 1
    if not parsed["cif_blocks"]:
        parsed["issues"].append(issue("unsupported_format", field="file_identity"))
    # Comments are retained spans, not lexical failures. A malformed token
    # disqualifies its own block without tainting independent valid blocks.
    for span in malformed_spans:
        for b in parsed["cif_blocks"]:
            if b["span"]["start_0based"] <= span["start_0based"] < b["span"]["end_exclusive"]:
                b["state"] = "invalid"
    if data_block is not None:
        if type(data_block) is not dict or set(data_block) != {"ordinal_0based", "name"} or type(data_block["ordinal_0based"]) is not int or type(data_block["name"]) is not str:
            raise ValueError("invalid_schema")
        if not any(b["ordinal_0based"] == data_block["ordinal_0based"] and b["name"] == data_block["name"] for b in parsed["cif_blocks"]):
            parsed["issues"].append(issue("unselected_data_block", field="data_block"))
    _cif_atoms(parsed)
    return _finish(parsed)


__all__ = ["parse_pdb_structure", "parse_mmcif_structure"]
