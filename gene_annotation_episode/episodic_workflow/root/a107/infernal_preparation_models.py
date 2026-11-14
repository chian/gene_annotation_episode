"""Pure header and framing readers for retained Infernal preparation artifacts.

The current and legacy CM readers check native state/node framing; the HMM
reader checks HMMER3/f nucleotide framing. State tables stay in the retained
artifact. Binary formats deliberately expose no decoded model population.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re

from .infernal_preparation_schema import (
    field_input, issue, locator, record_key, validate_artifact, value,
)

MODEL_FORMATS = frozenset({"infernal_cm_ascii", "infernal_cm_legacy_ascii",
    "hmmer_hmm_ascii", "infernal_cm_binary", "infernal_ssi", "infernal_i1f", "infernal_i1p"})
# Only these actual byte signatures were observed on the retained deployment.
OPAQUE_SIGNATURES = {
    "infernal_cm_binary": bytes.fromhex("b2b0ede3"),
    "infernal_ssi": bytes.fromhex("d3d3c9b3"),
    "infernal_i1f": bytes.fromhex("f3e6e1b1"),
    "infernal_i1p": bytes.fromhex("f3f0e6b3"),
}
ISSUE_CODES = frozenset({"model_artifact_digest_mismatch", "model_artifact_size_mismatch",
    "model_capture_incomplete", "model_opaque_content", "model_binary_signature_invalid",
    "model_binary_header_truncated", "model_text_decode_failed", "model_empty_population",
    "model_signature_invalid", "model_version_unsupported", "model_record_unterminated",
    "model_required_header_missing", "model_header_duplicate", "model_number_invalid",
    "model_header_invalid", "model_body_missing", "model_body_invalid",
    "model_topology_mismatch", "model_filter_missing", "model_filter_mismatch",
    "model_calibration_incomplete", "model_legacy_calibration_unsupported",
    "model_duplicate_name", "model_duplicate_accession", "model_alphabet_mismatch"})
CHECK_NAMES = frozenset()
COMPONENT_NAMES = frozenset()
ROW_FIELDS = {"model": frozenset({"kind", "record_key", "locator", "format",
    "writer_version", "model_type", "name", "accession", "description", "alphabet",
    "content_validation", "fields", "flags", "null_background", "calibration",
    "efp7gf", "filter_hmm", "topology", "source_fields"})}
FIELD_UNITS = {"CLEN": "nt", "W": "nt", "NSEQ": "count", "EFFN": "count",
    "STATES": "count", "NODES": "count", "CKSUM": "dimensionless",
    "GA": "bit", "TC": "bit", "NC": "bit"}
HMM_UNITS = {"LENG": "nt", "MAXL": "nt", "NSEQ": "count", "EFFN": "count", "CKSUM": "dimensionless"}
CALIBRATION_ALGORITHMS = {"ECMLC": "cm_local_cyk", "ECMGC": "cm_glocal_cyk",
    "ECMLI": "cm_local_inside", "ECMGI": "cm_glocal_inside"}
TOPOLOGY_FIELDS = ("base_pair_nodes", "bifurcation_nodes", "total_nodes", "total_states")
_INTEGER = re.compile(r"[+-]?\d+\Z")
_NODE = re.compile(r"\[\s*(ROOT|MATP|MATL|MATR|BIF|BEGL|BEGR|END)\s+(\d+)\s*\](.*)\Z")
_SIGNATURE = re.compile(r"(?:INFERNAL\S*|HMMER\S*)(?:\s|$)")


def _content_bytes(content):
    if isinstance(content, bytes):
        return content
    if isinstance(content, str):
        return content.encode("utf-8")
    try:
        chunks = list(content)
    except TypeError as exc:
        raise TypeError("content must be bytes, text or an iterable of text") from exc
    if any(not isinstance(chunk, str) for chunk in chunks):
        raise TypeError("content iterable must contain text")
    return "".join(chunks).encode("utf-8")


class _Reader:
    def __init__(self, data, artifact):
        self.artifact = artifact
        self.ref = artifact["artifact_ref"]
        self.lines = data.decode("utf-8").splitlines(keepends=True)
        self.offsets = [0]
        for line in self.lines:
            self.offsets.append(self.offsets[-1] + len(line.encode("utf-8")))
        self.issues = []

    def loc(self, ordinal, start, end=None):
        end = start + 1 if end is None else end
        if end <= start:
            return locator(self.ref, ordinal)
        return locator(self.ref, ordinal, line_start=start+1, line_end=end,
                       byte_start=self.offsets[start], byte_end=self.offsets[end])

    def problem(self, code, ordinal=None, field=None, *, severity="error", stage="format"):
        self.issues.append(issue(code, stage=stage, severity=severity, artifact_ref=self.ref,
            record_key=record_key(self.ref, "model", ordinal) if ordinal is not None else None,
            field=field))

    def number(self, token, unit, ordinal, line, field, *, integer=False, minimum=None,
               positive=False, maximum=None):
        source = [field_input(self.loc(ordinal, line), field)]
        try:
            if token is None or (integer and not _INTEGER.fullmatch(token)):
                raise ValueError
            number = int(token) if integer else float(token)
            if not math.isfinite(number) or (minimum is not None and number < minimum):
                raise ValueError
            if (positive and number <= 0) or (maximum is not None and number > maximum):
                raise ValueError
        except (ValueError, OverflowError):
            self.problem("model_number_invalid", ordinal, field, stage="extraction")
            return value(state="invalid", basis="model_header", unit=unit, inputs=source, native_token=token)
        return value(number, basis="model_header", unit=unit, inputs=source, native_token=token)

    def block_end(self, start):
        for index in range(start + 1, len(self.lines)):
            token = self.lines[index].strip()
            if token == "//":
                return index + 1, True
            if _SIGNATURE.match(token):
                return index, False
        return len(self.lines), False

    def headers(self, start, end, marker, ordinal):
        result, source, body = {}, {"date": [], "commands": [], "other_headers": []}, None
        for index in range(start + 1, end):
            line = self.lines[index].strip()
            if not line or line == "//":
                continue
            parts = line.split(None, 1)
            tag, rest = parts[0], parts[1] if len(parts) > 1 else ""
            if tag == marker:
                body = index
                break
            if tag in {"DATE", "BDATE", "CDATE"}:
                source["date"].append(rest)
            elif tag in {"COM", "BCOM", "CCOM"}:
                source["commands"].append(rest)
            elif tag == "STATS":
                result.setdefault(tag, []).append((rest.split(), index))
            elif tag in result:
                self.problem("model_header_duplicate", ordinal, tag)
                # Retain both native lines; never silently replace the first.
                source["other_headers"].append({"tag": tag, "tokens": rest.split()})
                result[tag + "__duplicate"] = True
            else:
                result[tag] = (rest.split(), index)
                result[tag + "__text"] = rest
        if body is None:
            self.problem("model_body_missing", ordinal, marker)
        return result, source, body

    def scalar(self, headers, tag, ordinal, unit):
        if tag not in headers:
            return value(basis="model_header", unit=unit)
        tokens, line = headers[tag]
        if len(tokens) != 1 or headers.get(tag + "__duplicate"):
            self.problem("model_header_invalid", ordinal, tag)
            return value(state="invalid", basis="model_header", unit=unit,
                native_token=" ".join(tokens), inputs=[field_input(self.loc(ordinal, line), tag)])
        integer = tag in {"CLEN", "W", "STATES", "NODES", "NSEQ", "CKSUM", "LENG", "MAXL"}
        return self.number(tokens[0], unit, ordinal, line, tag, integer=integer,
            minimum=0 if tag not in {"GA", "TC", "NC"} else None,
            positive=tag in {"CLEN", "W", "STATES", "NODES", "LENG", "MAXL"},
            maximum=4294967295 if tag == "CKSUM" else None)

    def required(self, headers, tags, ordinal):
        for tag in tags:
            if tag not in headers or not headers[tag][0]:
                self.problem("model_required_header_missing", ordinal, tag)

    def text(self, headers, tag, ordinal):
        if tag not in headers:
            return None
        tokens, _ = headers[tag]
        if not tokens or (tag != "DESC" and len(tokens) != 1) or headers.get(tag + "__duplicate"):
            self.problem("model_header_invalid", ordinal, tag)
            return None
        return headers[tag + "__text"]

    def cm_body(self, body, end, terminated, headers, ordinal, legacy):
        missing = {key: value(basis="model_header") for key in TOPOLOGY_FIELDS}
        if body is None:
            return missing
        nodes, node_indices, states, valid = [], [], [], True
        for index in range(body + 1, end - int(terminated)):
            line = self.lines[index].strip()
            if not line:
                continue
            node = _NODE.fullmatch(line)
            if node:
                node_type, node_index, annotation = node.groups()
                if int(node_index) in node_indices or (not legacy and len(annotation.split()) != 6):
                    valid = False
                if legacy and annotation.strip():
                    valid = False
                nodes.append(node_type)
                node_indices.append(int(node_index))
                continue
            fields = line.split()
            nfixed = 6 if legacy else 10
            if len(fields) < nfixed or fields[0] not in {"S", "IL", "IR", "MP", "ML", "MR", "D", "B", "E"}:
                valid = False
                continue
            if not nodes or any(not _INTEGER.fullmatch(x) for x in fields[1:nfixed]):
                valid = False
                continue
            if int(fields[1]) != len(states):
                valid = False
            state = fields[0]
            ntransitions = 0 if state == "B" else int(fields[5])
            nemissions = 16 if state == "MP" else 4 if state in {"ML", "MR", "IL", "IR"} else 0
            if not 0 <= ntransitions <= 6 or len(fields) != nfixed + ntransitions + nemissions:
                valid = False
            if any(not _finite_score(x) for x in fields[nfixed:]):
                valid = False
            states.append(state)
        if not valid or not nodes or not states:
            self.problem("model_body_invalid", ordinal, "MODEL:" if legacy else "CM")
        expected_nodes = self.scalar(headers, "NODES", ordinal, "count")["value"]
        expected_states = self.scalar(headers, "STATES", ordinal, "count")["value"]
        expected_clen = self.scalar(headers, "CLEN", ordinal, "nt")["value"]
        actual_clen = 2 * nodes.count("MATP") + nodes.count("MATL") + nodes.count("MATR")
        if (expected_nodes != len(nodes) or set(node_indices) != set(range(len(nodes)))
                or expected_states != len(states) or expected_clen != actual_clen):
            self.problem("model_topology_mismatch", ordinal, "CM")
            valid = False
        if not terminated or not valid:
            return {key: value(state="truncated" if not terminated else "invalid", basis="model_header")
                    for key in TOPOLOGY_FIELDS}
        counts = [nodes.count("MATP"), nodes.count("BIF"), len(nodes), len(states)]
        return {key: value(count, basis="model_header", inputs=[field_input(self.loc(ordinal, body+1, end-1), key)])
                for key, count in zip(TOPOLOGY_FIELDS, counts)}

    def hmm(self, start, end, terminated, ordinal):
        headers, source, body = self.headers(start, end, "HMM", ordinal)
        self.required(headers, ("NAME", "LENG", "ALPH"), ordinal)
        signature = self.lines[start].strip()
        if signature.split()[0] != "HMMER3/f":
            self.problem("model_version_unsupported", ordinal, "HMMER3")
        fields = {tag: self.scalar(headers, tag, ordinal, unit) for tag, unit in HMM_UNITS.items()}
        alphabet = self.text(headers, "ALPH", ordinal)
        if alphabet not in {"RNA", "DNA"}:
            self.problem("model_header_invalid", ordinal, "ALPH")
        stats, seen = [], set()
        for tokens, line in headers.get("STATS", []):
            if len(tokens) != 4:
                self.problem("model_header_invalid", ordinal, "STATS")
                continue
            mode, algorithm, location_token, scale_token = tokens
            if mode != "LOCAL" or algorithm not in {"MSV", "VITERBI", "FORWARD"} or (mode, algorithm) in seen:
                self.problem("model_header_invalid", ordinal, "STATS")
            seen.add((mode, algorithm))
            stats.append({"locator": self.loc(ordinal, line), "mode": mode, "algorithm": algorithm,
                "location": self.number(location_token, "bit", ordinal, line, "STATS."+algorithm+".location"),
                "scale": self.number(scale_token, "inverse_bit", ordinal, line, "STATS."+algorithm+".scale", positive=True)})
        if seen and seen != {("LOCAL", a) for a in ("MSV", "VITERBI", "FORWARD")}:
            self.problem("model_calibration_incomplete", ordinal, "STATS")
        if body is not None:
            lines = [self.lines[i].strip().split() for i in range(body, end-int(terminated)) if self.lines[i].strip()]
            valid = len(lines) >= 4 and lines[0] == ["HMM", "A", "C", "G", "U" if alphabet == "RNA" else "T"]
            valid = valid and lines[1] == ["m->m", "m->i", "m->d", "i->m", "i->i", "d->m", "d->d"]
            rows = lines[2:]
            if rows and rows[0][0] == "COMPO":
                valid = valid and _score_row(rows[0][1:], 4)
                rows = rows[1:]
            valid = valid and len(rows) >= 2 and _score_row(rows[0], 4) and _score_row(rows[1], 7)
            matches = rows[2:]
            length = fields["LENG"]["value"]
            valid = valid and length is not None and len(matches) == length * 3
            for k in range(0, len(matches)-2, 3):
                match, insert, transitions = matches[k:k+3]
                valid = valid and len(match) == 10 and match[0] == str(k//3+1)
                valid = valid and _score_row(match[1:5], 4) and _score_row(insert, 4) and _score_row(transitions, 7)
            if not valid:
                self.problem("model_body_invalid", ordinal, "HMM")
        header = {"locator": self.loc(ordinal, start, end), "writer_version": _writer(signature),
            "name": self.text(headers, "NAME", ordinal), "accession": self.text(headers, "ACC", ordinal),
            "description": self.text(headers, "DESC", ordinal), "alphabet": alphabet, "fields": fields, "stats": stats}
        return header, headers, source

    def model(self, start, end, terminated, ordinal, fmt):
        before = len(self.issues)
        signature = self.lines[start].strip()
        result = {"kind": "model", "record_key": record_key(self.ref, "model", ordinal),
            "locator": self.loc(ordinal, start, end), "format": fmt, "writer_version": _writer(signature),
            "model_type": "hmm" if fmt == "hmmer_hmm_ascii" else "cm",
            "name": None, "accession": None, "description": None, "alphabet": None,
            "content_validation": "parsed_headers_and_boundaries",
            "fields": {tag: value(basis="model_header", unit=unit) for tag, unit in FIELD_UNITS.items()},
            "flags": {tag: None for tag in ("RF", "CONS", "MAP")}, "null_background": [],
            "calibration": {tag: None for tag in CALIBRATION_ALGORITHMS}, "efp7gf": None,
            "filter_hmm": None, "topology": {tag: value(basis="model_header") for tag in TOPOLOGY_FIELDS},
            "source_fields": {"date": [], "commands": [], "other_headers": []}}
        if fmt == "hmmer_hmm_ascii":
            hmm, headers, source = self.hmm(start, end, terminated, ordinal)
            result["filter_hmm"] = hmm
            for tag in ("name", "accession", "description", "alphabet"):
                result[tag] = hmm[tag]
            consumed = set(HMM_UNITS) | {"NAME", "ACC", "DESC", "ALPH", "STATS", "RF", "CONS", "MAP"}
        else:
            legacy = fmt == "infernal_cm_legacy_ascii"
            headers, source, body = self.headers(start, end, "MODEL:" if legacy else "CM", ordinal)
            required = ("NAME", "STATES", "NODES", "CLEN", "ALPHABET") if legacy else (
                "NAME", "STATES", "NODES", "CLEN", "W", "ALPH", "NULL", "EFP7GF", "ELSELF")
            self.required(headers, required, ordinal)
            for tag, attr in (("NAME", "name"), ("ACC", "accession"), ("DESC", "description")):
                result[attr] = self.text(headers, tag, ordinal)
            alphabet_tag = "ALPHABET" if legacy else "ALPH"
            result["alphabet"] = self.text(headers, alphabet_tag, ordinal)
            # Legacy ALPHABET is an integer native string. Preserve it verbatim;
            # its explicitly supported nucleotide meanings are checked here.
            if result["alphabet"] not in ({"1", "2"} if legacy else {"RNA", "DNA"}):
                self.problem("model_header_invalid", ordinal, alphabet_tag)
            for tag, unit in FIELD_UNITS.items():
                result["fields"][tag] = self.scalar(headers, "EFFNSEQ" if legacy and tag == "EFFN" else tag, ordinal, unit)
            if "NULL" in headers:
                tokens, line = headers["NULL"]
                if len(tokens) != 4:
                    self.problem("model_header_invalid", ordinal, "NULL")
                result["null_background"] = [self.number(token, "log2_odds", ordinal, line, "NULL."+str(i))
                                              for i, token in enumerate(tokens)]
            for tag, algorithm in CALIBRATION_ALGORITHMS.items():
                if tag not in headers:
                    continue
                tokens, line = headers[tag]
                if len(tokens) != 6:
                    self.problem("model_header_invalid", ordinal, tag)
                tokens = tokens + [None] * max(0, 6-len(tokens))
                names = ("lambda", "mu_extrap", "mu_orig", "calibration_dbsize_nt", "random_hit_count", "tail_probability_mass")
                units = ("inverse_bit", "bit", "bit", "nt", "count", "fraction")
                fit = {"algorithm": algorithm, "locator": self.loc(ordinal, line)}
                for i, (name, unit) in enumerate(zip(names, units)):
                    fit[name] = self.number(tokens[i], unit, ordinal, line, tag+"."+name,
                        integer=i in {3, 4}, positive=i in {0, 3, 5}, minimum=0 if i == 4 else None,
                        maximum=1 if i == 5 else None)
                result["calibration"][tag] = fit
            nfits = sum(item is not None for item in result["calibration"].values())
            if nfits not in {0, 4}:
                self.problem("model_calibration_incomplete", ordinal, "ECM")
            if legacy and any(tag.startswith(("E-", "FT-")) or tag == "PART" for tag in headers):
                self.problem("model_legacy_calibration_unsupported", ordinal, "PART", severity="warning")
            if "EFP7GF" in headers:
                tokens, line = headers["EFP7GF"]
                if len(tokens) != 2:
                    self.problem("model_header_invalid", ordinal, "EFP7GF")
                tokens = tokens + [None] * max(0, 2-len(tokens))
                result["efp7gf"] = {"locator": self.loc(ordinal, line),
                    "location": self.number(tokens[0], "bit", ordinal, line, "EFP7GF.location"),
                    "scale": self.number(tokens[1], "inverse_bit", ordinal, line, "EFP7GF.scale", positive=True)}
            result["topology"] = self.cm_body(body, end, terminated, headers, ordinal, legacy)
            consumed = set(FIELD_UNITS) | set(CALIBRATION_ALGORITHMS) | {
                "NAME", "ACC", "DESC", "ALPH", "ALPHABET", "NULL", "EFP7GF", "EFFNSEQ", "RF", "CONS", "MAP"}
        for tag in result["flags"]:
            result["flags"][tag] = self.text(headers, tag, ordinal)
            if result["flags"][tag] is not None and result["flags"][tag].lower() not in {"yes", "no"}:
                self.problem("model_header_invalid", ordinal, tag)
        for tag, item in headers.items():
            if "__" not in tag and tag not in consumed:
                source["other_headers"].append({"tag": tag, "tokens": item[0]})
        result["source_fields"] = source
        if not terminated:
            self.problem("model_record_unterminated", ordinal)
            result["content_validation"] = "partial"
        elif any(i["severity"] == "error" for i in self.issues[before:]):
            result["content_validation"] = "invalid"
        return result


def _writer(signature):
    match = re.search(r"\[(.*)\]", signature)
    return match.group(1) if match else None


def _finite_score(token):
    if token == "*":
        return True
    try:
        return math.isfinite(float(token))
    except (ValueError, OverflowError):
        return False


def _score_row(tokens, count):
    return len(tokens) == count and all(_finite_score(token) for token in tokens)


def extract_infernal_models(content, *, artifact, format, engine_version=None):
    """Extract exact ordered model/header records; never acquire or convert data.

    ``population_complete`` describes decoded framing plus acquisition
    completeness, not a claim of scientific integrity or binary decoding.
    ``engine_version`` never overrides the actual native writer-version string.
    """
    validate_artifact(artifact)
    if format not in MODEL_FORMATS or artifact["format"] != format:
        raise ValueError("unsupported or inconsistent declared model format")
    if engine_version is not None and not isinstance(engine_version, str):
        raise TypeError("engine_version must be text or None")
    data = _content_bytes(content)
    result = {"artifact": deepcopy(artifact), "format": format, "records": [], "issues": [], "population_complete": False}
    def artifact_issue(code, severity="error"):
        result["issues"].append(issue(code, stage="format", severity=severity, artifact_ref=artifact["artifact_ref"]))
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        artifact_issue("model_artifact_digest_mismatch")
    if len(data) != artifact["size_bytes"]:
        artifact_issue("model_artifact_size_mismatch")
    if artifact["completeness"] != "complete":
        artifact_issue("model_capture_incomplete", "warning")
    if format in OPAQUE_SIGNATURES:
        if len(data) <= 4:
            artifact_issue("model_binary_header_truncated")
        if not data.startswith(OPAQUE_SIGNATURES[format]):
            artifact_issue("model_binary_signature_invalid")
        artifact_issue("model_opaque_content", "information")
        return result
    try:
        reader = _Reader(data, artifact)
    except UnicodeDecodeError:
        artifact_issue("model_text_decode_failed")
        return result
    expected = {"infernal_cm_ascii": "INFERNAL1/a", "infernal_cm_legacy_ascii": "INFERNAL-1",
                "hmmer_hmm_ascii": "HMMER3/f"}[format]
    index = 0
    while index < len(reader.lines):
        line = reader.lines[index].strip()
        if not line or line.startswith("#"):
            index += 1
            continue
        if line.split()[0] != expected:
            reader.problem("model_signature_invalid")
            index += 1
            continue
        ordinal = len(result["records"])
        end, terminated = reader.block_end(index)
        record = reader.model(index, end, terminated, ordinal, format)
        if format == "infernal_cm_ascii" and terminated:
            following = end
            while following < len(reader.lines) and not reader.lines[following].strip():
                following += 1
            if following < len(reader.lines) and reader.lines[following].strip().startswith("HMMER3/"):
                hmm_end, hmm_terminated = reader.block_end(following)
                before = len(reader.issues)
                hmm, _, _ = reader.hmm(following, hmm_end, hmm_terminated, ordinal)
                record["filter_hmm"] = hmm
                record["locator"] = reader.loc(ordinal, index, hmm_end)
                equal = all(record[key] == hmm[key] for key in ("name", "accession", "alphabet"))
                equal = equal and record["fields"]["CLEN"]["value"] == hmm["fields"]["LENG"]["value"]
                if not equal:
                    reader.problem("model_filter_mismatch", ordinal, "filter_hmm")
                if not hmm_terminated:
                    reader.problem("model_record_unterminated", ordinal, "filter_hmm")
                    record["content_validation"] = "partial"
                elif any(item["severity"] == "error" for item in reader.issues[before:]):
                    record["content_validation"] = "invalid"
                end = hmm_end
            else:
                reader.problem("model_filter_missing", ordinal, "filter_hmm")
                record["content_validation"] = "partial"
        result["records"].append(record)
        index = end
    if not result["records"]:
        reader.problem("model_empty_population")
    for attr, code in (("name", "model_duplicate_name"), ("accession", "model_duplicate_accession")):
        seen = set()
        for record in result["records"]:
            native = record[attr]
            if native is not None and native in seen:
                reader.problem(code, record["locator"]["record_ordinal"], attr, severity="warning", stage="association")
            seen.add(native)
    if len({r["alphabet"] for r in result["records"] if r["alphabet"] is not None}) > 1:
        reader.problem("model_alphabet_mismatch")
    result["issues"].extend(reader.issues)
    result["population_complete"] = (artifact["completeness"] == "complete" and bool(result["records"])
        and not any(item["severity"] == "error" for item in result["issues"])
        and all(r["content_validation"] == "parsed_headers_and_boundaries" for r in result["records"]))
    return result
