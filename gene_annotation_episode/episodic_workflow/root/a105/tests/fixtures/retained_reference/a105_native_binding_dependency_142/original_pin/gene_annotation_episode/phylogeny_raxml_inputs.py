"""Pure extraction of observed RAxML 8 log quantities from supplied bytes.

This module neither runs RAxML nor acquires a log. It preserves separate native
search/replicate events and original locations; provider extraction associates
them with the selected analysis. Requested settings cannot supply missing facts.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re
import shlex

from .phylogeny_format_contracts import _native_number


_VERSION = re.compile(r"^This is RAxML version (\S+) released\b")
_PARTITION = re.compile(r"^Partition:\s*(\d+)\s*$")
_FITTED = re.compile(
    r"^Model Parameters of Partition (\d+), Name: (.*), Type of Data: (\S+)\s*$")
_PARAMETER = re.compile(r"^(alpha|Tree-Length|rate [A-Z] <-> [A-Z]|freq pi\([A-Z]\)):\s*(\S+)\s*$")
_BOOTSTRAP = re.compile(
    r"^Bootstrap\[(\d+)\]:.*?bootstrap likelihood\s+(\S+?)(?:,|\s*$)")
_SLOW = re.compile(r"^Slow ML Search (\d+) Likelihood:\s*(\S+)\s*$")
_FINAL = re.compile(r"^Final ML Optimization Likelihood:\s*(\S+)\s*$")
_PATTERNS = re.compile(r"^Alignment has (\S+) distinct alignment patterns\s*$")
_GAPS = re.compile(r"^Proportion of gaps and completely undetermined characters in this alignment:\s*(\S+)%\s*$")
_OPTIMIZATION = re.compile(
    r"^Using \d+ distinct models/data partitions with (joint|separate) branch length optimization\s*$")
_END = re.compile(r"^Overall execution time for full ML analysis:\s+\S+ secs\b")
_ALPHABETS = {"DNA": "dna", "RNA": "rna", "AA": "protein"}


def _diagnostic(code, path="", *, refs=(), phase="native_decode", severity="error"):
    return {"code": code, "phase": phase, "path": path,
            "severity": severity, "evidence_refs": list(refs)}


def _invalid(code, artifact, *, phase="native_decode"):
    ref = artifact.get("source_ref") if type(artifact) is dict else None
    return {"status": "invalid", "value": None,
            "diagnostics": [_diagnostic(code, refs=[ref] if type(ref) is str else [], phase=phase)]}


def _option(argv, option):
    """Only read an actual command's tokens; never interpolate or execute."""
    values = [argv[i + 1] for i in range(len(argv) - 1) if argv[i] == option]
    return values[0] if len(values) == 1 else None


class _Log:
    def __init__(self, data, artifact):
        self.artifact = deepcopy(artifact)
        self.identity = artifact["raw_artifact_ref"] + "#raxml_log"
        self.lines = []
        start = 0
        for number, raw in enumerate(data.splitlines(keepends=True), 1):
            location = {"artifact": deepcopy(artifact), "byte_start_0based": start,
                "byte_end_0based_exclusive": start + len(raw), "line_start_1based": number,
                "line_end_1based_inclusive": number, "xml_path": None}
            self.lines.append((number, raw.decode("utf-8").rstrip("\r\n"), location))
            start += len(raw)
        self.diagnostics = []
        self.observations = []
        self.commands = []
        self.models = []
        self.versions = []
        self.optimizations = []
        self.finished = False

    def diagnostic(self, code, number=None, *, severity="error"):
        self.diagnostics.append(_diagnostic(code,
            f"/lines/{number}" if number is not None else "",
            refs=[self.artifact["source_ref"]], severity=severity))

    def number(self, token, line, *, integer=False, minimum=None, maximum=None):
        try:
            if integer and re.fullmatch(r"[+-]?\d+", token) is None:
                raise ValueError
            value = int(token) if integer else _native_number(token)
            if value is None or not math.isfinite(value):
                raise ValueError
        except (ValueError, OverflowError):
            self.diagnostic("raxml_numeric_token_invalid", line)
            return None
        if minimum is not None and value < minimum or maximum is not None and value > maximum:
            self.diagnostic("raxml_numeric_range_invalid", line)
            return None
        return value

    def observation(self, token, line, location, *, field, method, unit,
                    population="alignment", subject=None, integer=False,
                    minimum=None, maximum=None):
        value = self.number(token, line, integer=integer, minimum=minimum, maximum=maximum)
        self.observations.append({
            "observation_id": f"{self.identity}/line/{line}/{field}",
            "field": field, "value": value, "raw_token": token,
            "state": "available" if value is not None else "failed",
            "unit": unit, "population_id": self.identity + "/population/" + population,
            "subject_id": self.identity + "/" + subject if subject is not None else None,
            "method": method, "location": deepcopy(location), "evidence": [],
            "uncertainty": None, "requirement_ids": []})

    def new_model(self, index, location, name=None, datatype="unknown"):
        value = {"native_run_label": None, "partition_index": index,
            "partition_name": name, "model_token": None, "datatype": datatype,
            "branch_optimization": "unknown", "parameters": [], "location": deepcopy(location)}
        self.models.append(value)
        return value

    def command(self, text, line, location):
        try:
            argv = shlex.split(text, posix=True)
            if not argv:
                raise ValueError
        except ValueError:
            argv = None
            self.diagnostic("raxml_command_tokens_invalid", line)
        mode = _option(argv, "-f") if argv else None
        role = {"a": "inference", "D": "inference", "b": "support_mapping", "I": "rooting"}.get(mode, "unknown")
        self.commands.append({"command_id": f"{self.identity}/command/{line}",
            "role": role, "argv": argv, "raw_text": text, "origin": "observed",
            "evidence": [], "location": deepcopy(location)})

    def parse(self):
        current = None
        current_is_fitted = False
        expecting_command = False
        for line, raw, location in self.lines:
            text = raw.strip()
            if not text:
                continue
            if expecting_command:
                # A missing command must not consume the next log section.
                if re.match(r"(?:\S*/)?raxml\S*(?:\s|$)", text, re.IGNORECASE):
                    self.command(raw, line, location)
                    expecting_command = False
                    current = None
                    continue
                self.diagnostic("raxml_command_missing", line)
                expecting_command = False
            match = _VERSION.match(text)
            if match:
                self.versions.append((match.group(1), deepcopy(location)))
                continue
            if text == "RAxML was called as follows:":
                expecting_command = True
                current = None
                continue
            match = _OPTIMIZATION.match(text)
            if match:
                self.optimizations.append(match.group(1))
                continue
            if _END.match(text):
                self.finished = True
                current = None
                continue
            match = _PARTITION.match(text)
            if match:
                index = int(match.group(1))
                if any(row["partition_index"] == index for row in self.models):
                    self.diagnostic("raxml_partition_repeated", line)
                current = self.new_model(index, location)
                current_is_fitted = False
                continue
            match = _FITTED.match(text)
            if match:
                index, name = int(match.group(1)), match.group(2)
                datatype = _ALPHABETS.get(match.group(3), "unknown")
                candidates = [row for row in self.models if row["partition_index"] == index]
                compatible = [row for row in candidates if row["partition_name"] == name
                    and row["datatype"] == datatype and not row["parameters"]]
                if len(candidates) == len(compatible) == 1:
                    current = compatible[0]
                else:
                    if candidates:
                        self.diagnostic("raxml_partition_association_conflict", line)
                    current = self.new_model(index, location, name, datatype)
                current_is_fitted = True
                if datatype == "unknown":
                    self.diagnostic("raxml_partition_datatype_unknown", line, severity="qualification")
                continue
            if text.startswith(("Partition:", "Model Parameters of Partition ")):
                self.diagnostic("raxml_partition_syntax_invalid", line)
                current = None
                current_is_fitted = False
                continue
            match = _PATTERNS.match(text)
            if match:
                self.observation(match.group(1), line, location, field="distinct_alignment_patterns",
                    method="raxml_8_alignment_patterns", unit="patterns", integer=True, minimum=0)
                continue
            match = _GAPS.match(text)
            if match:
                self.observation(match.group(1), line, location, field="gap_undetermined_percent_native",
                    method="raxml_8_gap_undetermined_percent", unit="percent", minimum=0, maximum=100)
                continue
            match = _BOOTSTRAP.match(text)
            if match:
                index, token = match.groups()
                self.observation(token, line, location, field="log_likelihood",
                    method="raxml_8_bootstrap_log_likelihood", unit="natural_log_likelihood",
                    population="bootstrap/" + index, subject="bootstrap/" + index)
                current = None
                continue
            match = _SLOW.match(text)
            if match:
                index, token = match.groups()
                self.observation(token, line, location, field="log_likelihood",
                    method="raxml_8_slow_search_log_likelihood", unit="natural_log_likelihood",
                    subject="slow_search/" + index)
                current = None
                continue
            match = _FINAL.match(text)
            if match:
                self.observation(match.group(1), line, location, field="log_likelihood",
                    method="raxml_8_final_ml_log_likelihood", unit="natural_log_likelihood", subject="final_ml")
                current = None
                continue
            if current is not None and not current_is_fitted:
                if text.startswith("Alignment Patterns:"):
                    self.observation(text.split(":", 1)[1].strip(), line, location,
                        field="distinct_alignment_patterns", method="raxml_8_partition_patterns",
                        unit="patterns", integer=True, minimum=0,
                        population=f"partition/{current['partition_index']}",
                        subject=f"partition/{current['partition_index']}")
                    continue
                field = next((key for prefix, key in (("Name:", "partition_name"),
                    ("DataType:", "datatype"), ("Substitution Matrix:", "model_token"))
                    if text.startswith(prefix)), None)
                if field:
                    value = text.split(":", 1)[1].strip()
                    value = _ALPHABETS.get(value, "unknown") if field == "datatype" else value or None
                    prior = current[field]
                    if prior not in (None, "unknown") and prior != value:
                        self.diagnostic("raxml_partition_association_conflict", line)
                        current = self.new_model(current["partition_index"], location)
                    current[field] = value
                    continue
            elif text.startswith(("Alignment Patterns:", "Name:", "DataType:", "Substitution Matrix:")):
                self.diagnostic("raxml_partition_header_unassociated", line)
                continue
            match = _PARAMETER.match(text)
            if match:
                if current is None or not current_is_fitted:
                    self.diagnostic("raxml_parameter_partition_missing", line)
                    continue
                name, token = match.groups()
                value = self.number(token, line)
                if value is not None:
                    if any(row["name"] == name for row in current["parameters"]):
                        self.diagnostic("raxml_parameter_repeated", line)
                    current["parameters"].append({"name": name, "value": value,
                        "native_location": deepcopy(location)})
                continue
            if text.startswith(("alpha:", "Tree-Length:", "rate ", "freq pi(")):
                self.diagnostic("raxml_parameter_syntax_invalid", line)
                continue
            if (text.startswith(("Bootstrap[", "Slow ML Search ", "Final ML Optimization Likelihood:",
                                 "Alignment has ", "Proportion of gaps and completely undetermined characters"))):
                self.diagnostic("raxml_measurement_syntax_invalid", line)
        if expecting_command:
            self.diagnostic("raxml_command_missing")
        versions = {value for value, _ in self.versions}
        if not versions:
            self.diagnostic("raxml_version_missing")
        elif len(versions) > 1:
            self.diagnostic("raxml_version_conflict")
        if any(not re.fullmatch(r"8(?:\.\d+)+(?:[-+][A-Za-z0-9._-]+)?", value) for value in versions):
            self.diagnostic("raxml_version_unsupported")
        if not self.commands:
            self.diagnostic("raxml_command_missing")
        elif len(self.commands) > 1:
            self.diagnostic("raxml_multiple_invocations_unassociated")
        if not self.finished:
            self.diagnostic("raxml_log_completion_unproven", severity="qualification")
        optimization = set(self.optimizations)
        if len(optimization) > 1:
            self.diagnostic("raxml_branch_optimization_conflict")
        labels = {_option(row["argv"], "-n") for row in self.commands if row["argv"] is not None}
        label = next(iter(labels)) if len(labels) == 1 and len(self.commands) == 1 else None
        for model in self.models:
            model["native_run_label"] = label
            model["branch_optimization"] = next(iter(optimization)) if len(optimization) == 1 else "unknown"
        version = self.versions[0][0] if len(versions) == 1 else None
        version_location = self.versions[0][1] if version is not None else None
        invalid = any(row["code"] in {"raxml_version_conflict", "raxml_version_unsupported"}
                      for row in self.diagnostics)
        complete = self.finished and not any(row["severity"] == "error" for row in self.diagnostics)
        value = {"artifact": self.artifact,
            "engine": {"name": "raxml", "version": version, "version_location": version_location,
                "version_evidence": [], "command_ids": [row["command_id"] for row in self.commands]},
            "commands": self.commands, "observations": self.observations, "models": self.models,
            "completeness": "complete" if complete else "partial" if self.lines else "unknown"}
        return {"status": "invalid" if invalid else "ok" if complete else "partial",
                "value": value, "diagnostics": self.diagnostics}


def parse_raxml_run_log(data: bytes, *, artifact: dict, dialect: str) -> dict:
    """Return the frozen ReadResult[RAxMLRunObservations] supplied-data shape."""
    if dialect != "raxml_8":
        return _invalid("raxml_dialect_unsupported", artifact)
    if (type(data) is not bytes or type(artifact) is not dict
            or set(artifact) != {"raw_artifact_ref", "source_ref", "sha256"}
            or any(type(artifact.get(key)) is not str or not artifact[key]
                   for key in ("raw_artifact_ref", "source_ref", "sha256"))
            or re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is None):
        return _invalid("raxml_artifact_invalid", artifact, phase="association")
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        return _invalid("raxml_artifact_hash_conflict", artifact, phase="association")
    try:
        return _Log(data, artifact).parse()
    except UnicodeDecodeError:
        return _invalid("raxml_encoding_invalid", artifact)


__all__ = ["parse_raxml_run_log"]
