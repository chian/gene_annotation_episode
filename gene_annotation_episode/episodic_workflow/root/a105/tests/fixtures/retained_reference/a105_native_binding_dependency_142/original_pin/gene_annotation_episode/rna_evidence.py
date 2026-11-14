"""Native Infernal evidence, without an RNA classification or acceptance rule.

cmsearch's query is a model and its target is physical sequence. Model consensus
coordinates are deliberately kept separate from physical operand intervals.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re
import tempfile
import tomllib

from .acquisition import AcquisitionError
from .domain import ContractError
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job

VERSION = "infernal_cmsearch_fmt3_v1"
RFAM_ACCESSION = re.compile(r"^RF[0-9]{5}$")


def model_header(content: bytes) -> dict:
    """Read one ASCII CM's header; do not interpret CLEN as sequence length."""
    try:
        text = content.decode("ascii")
    except UnicodeDecodeError as error:
        raise ContractError("covariance_model_not_ascii") from error
    if not text.startswith("INFERNAL1/") or text.count("\nINFERNAL1/"):
        raise ContractError("single_infernal_covariance_model_required")
    header = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "CM":
            break
        fields = line.split(maxsplit=1)
        if len(fields) == 2:
            header[fields[0]] = fields[1].strip()
    else:
        raise ContractError("covariance_model_header_incomplete")
    try:
        length = int(header["CLEN"])
        if length < 1 or header["ALPH"] != "RNA" or not header["NAME"]:
            raise ValueError
    except (KeyError, ValueError) as error:
        raise ContractError("invalid_covariance_model_header") from error
    return {"format_header": text.splitlines()[0], "name": header["NAME"],
        "accession": header.get("ACC"), "description": header.get("DESC"),
        "consensus_length": length, "alphabet": header["ALPH"],
        "native_header": header}


def local_configuration(*, executable=None, cpu=None, job_limits=None) -> dict:
    defaults = tomllib.loads(Path(__file__).with_name("defaults.toml").read_text())["local_tools"]
    cpu = defaults["cmsearch_cpu"] if cpu is None else cpu
    if type(cpu) is not int or cpu < 0:
        raise ValueError("cmsearch_cpu_must_be_nonnegative_integer")
    path = Path(executable).expanduser().resolve() if executable is not None else None
    return {"executable": str(path) if path else None, "cpu": cpu,
        "job_limits": LocalJobPolicy.from_config(job_limits).to_dict(),
        "executable_sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None,
        "adapter_version": VERSION}


def search_settings(parameters=None) -> dict:
    given = dict(parameters or {})
    settings = {"report_evalue": 10.0, "inclusion_evalue": .01,
        "alignment_mode": "local", "strand": "both", "truncation": "default",
        "acceleration": "default", "force_cm": False, "cyk": False,
        "matrix_mb": 128.0, "sequence_matrix_mb": 128.0, "alignment_output": True}
    if "report_bitscore" in given or "model_cutoff" in given:
        settings.pop("report_evalue")
    if "inclusion_bitscore" in given or "model_cutoff" in given:
        settings.pop("inclusion_evalue")
    if "report_bitscore" in given and "report_evalue" in given:
        raise ContractError("conflicting_native_reporting_thresholds")
    if "inclusion_bitscore" in given and "inclusion_evalue" in given:
        raise ContractError("conflicting_native_inclusion_thresholds")
    if "model_cutoff" in given and any(key in given for key in
        ("report_bitscore", "report_evalue", "inclusion_bitscore", "inclusion_evalue")):
        raise ContractError("model_cutoff_sets_reporting_and_inclusion")
    settings.update(given)
    # These are native option incompatibilities, not a judgment of the result.
    if settings["truncation"] == "any" and settings["acceleration"] in {"max", "nohmm"}:
        raise ContractError("native_acceleration_disables_truncated_search")
    return settings


def iter_fmt3(content: bytes):
    """Parse every reported row, including native '?' rows. Fail visibly."""
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split(maxsplit=19)
        if len(fields) < 19:
            raise ContractError("invalid_cmsearch_fmt3_row", detail={"line": line_number})
        try:
            row = {"native_target_name": fields[0], "native_target_accession": None if fields[1] == "-" else fields[1],
                "native_query_name": fields[2], "native_query_accession": None if fields[3] == "-" else fields[3],
                "algorithm": fields[4], "model_from": int(fields[5]), "model_to": int(fields[6]),
                "target_from": int(fields[7]), "target_to": int(fields[8]), "strand": fields[9],
                "truncation": fields[10], "pass": int(fields[11]), "gc_fraction": float(fields[12]),
                "bias_bits": float(fields[13]), "bitscore": float(fields[14]), "evalue": float(fields[15]),
                "inclusion": fields[16], "model_length": int(fields[17]), "target_length": int(fields[18]),
                "description": fields[19] if len(fields) == 20 else ""}
            valid = (row["algorithm"] in {"cm", "hmm"} and row["strand"] in {"+", "-"}
                and row["truncation"] in {"no", "5'", "3'", "5'&3'", "-"} and row["inclusion"] in {"!", "?"}
                and 1 <= row["model_from"] <= row["model_to"] <= row["model_length"]
                and 1 <= min(row["target_from"], row["target_to"]) <= max(row["target_from"], row["target_to"]) <= row["target_length"]
                and ((row["target_from"] <= row["target_to"]) if row["strand"] == "+" else (row["target_from"] >= row["target_to"]))
                and all(math.isfinite(row[key]) for key in ("gc_fraction", "bias_bits", "bitscore", "evalue"))
                and 0 <= row["gc_fraction"] <= 1 and row["evalue"] >= 0 and row["pass"] >= 1)
            if not valid:
                raise ValueError
        except ValueError as error:
            raise ContractError("invalid_cmsearch_fmt3_values", detail={"line": line_number}) from error
        row["target_interval"] = [min(row["target_from"], row["target_to"]) - 1,
                                  max(row["target_from"], row["target_to"])]
        row["model_consensus_interval"] = [row["model_from"] - 1, row["model_to"]]
        yield row


def parse_fmt3(content: bytes) -> list[dict]:
    return list(iter_fmt3(content))


@dataclass(frozen=True)
class NativeSearch:
    metadata: dict
    stdout: bytes
    stderr: bytes
    table: bytes
    input_fasta: bytes
    help_output: bytes


def run_cmsearch(*, sequence: str, subject_ref: str, model: bytes,
                 model_ref: str, configuration: dict, parameters=None,
                 job_limits=None, cancel_event=None) -> NativeSearch:
    """Pure external work: no Store, transaction, loop or scientific retry."""
    executable = configuration["executable"]
    if executable is None:
        raise AcquisitionError("cmsearch_not_configured", phase="local_preflight")
    path = Path(executable)
    if not path.is_file():
        raise AcquisitionError("cmsearch_executable_missing", phase="local_preflight")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    # A caller may change operational resources between measurements. Keep the
    # actual invocation's identity; do not invalidate earlier committed work.
    policy = LocalJobPolicy.from_config(job_limits if job_limits is not None else configuration.get("job_limits"))
    configuration = {**configuration, "executable_sha256": digest, "job_limits": policy.to_dict()}
    settings = search_settings(parameters)
    header = model_header(model)
    # A declared processing model does not reclassify caller material.
    if not sequence or not set(sequence.upper()) <= set("ACGTURYSWKMBDHVN"):
        raise ContractError("cmsearch_requires_nucleotide_processing_alphabet")
    fasta = f">{subject_ref}\n{sequence}\n".encode("ascii")
    started = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix="annotation-cmsearch-") as directory:
        directory = Path(directory)
        model_path, target_path, table_path = directory / "query.cm", directory / "target.fa", directory / "matches.tbl"
        check_scratch_budget(directory, policy, additional_bytes=len(model)+len(fasta))
        model_path.write_bytes(model)
        target_path.write_bytes(fasta)
        check_scratch_budget(directory, policy)
        help_result = run_local_job([executable, "-h"], cwd=directory, policy=policy,
            stdout_path=directory/"help.stdout", stderr_path=directory/"help.stderr", cancel_event=cancel_event)
        help_stdout, help_stderr = help_result.stdout_path.read_bytes(), help_result.stderr_path.read_bytes()
        help_text = help_stdout.decode("utf-8", errors="replace")
        match = re.search(r"# INFERNAL ([^;\s]+)", help_text)
        native_version = match.group(1) if match else None
        command = [executable, "--cpu", str(configuration["cpu"]), "--tformat", "fasta", "--fmt", "3",
            "--tblout", str(table_path), "--notextw", "--verbose"]
        for key, flag in {"report_evalue": "-E", "report_bitscore": "-T", "inclusion_evalue": "--incE",
            "inclusion_bitscore": "--incT", "search_space_mb": "-Z", "matrix_mb": "--mxsize",
            "sequence_matrix_mb": "--smxsize"}.items():
            if key in settings:
                command += [flag, str(settings[key])]
        if "model_cutoff" in settings:
            command += ["--cut_" + settings["model_cutoff"]]
        if settings["alignment_mode"] == "glocal":
            command += ["-g"]
        if settings["strand"] != "both":
            command += ["--toponly" if settings["strand"] == "top" else "--bottomonly"]
        if settings["truncation"] != "default":
            command += ["--anytrunc" if settings["truncation"] == "any" else "--notrunc"]
        if settings["acceleration"] != "default":
            command += ["--" + settings["acceleration"]]
        for key, flag in (("force_cm", "--nohmmonly"), ("cyk", "--cyk")):
            if settings[key]:
                command += [flag]
        if not settings["alignment_output"]:
            command += ["--noali"]
        command += [str(model_path), str(target_path)]
        completed = run_local_job(command, cwd=directory, policy=policy,
            stdout_path=directory/"native.stdout", stderr_path=directory/"native.stderr", cancel_event=cancel_event)
        stdout, stderr = completed.stdout_path.read_bytes(), completed.stderr_path.read_bytes()
        table = table_path.read_bytes() if table_path.exists() else b""
    native_limitations = []
    report_mode = "bitscore" if "report_bitscore" in settings else "evalue"
    inclusion_mode = "bitscore" if "inclusion_bitscore" in settings else "evalue"
    if native_version == "1.1.5" and "model_cutoff" not in settings and report_mode != inclusion_mode:
        native_limitations.append("infernal_1_1_5_inclusion_uses_reporting_threshold_mode")
    if settings["truncation"] == "any":
        native_limitations.append("native_anytrunc_evalues_not_calibrated_for_truncated_search")
    if settings["acceleration"] in {"max", "nohmm"}:
        native_limitations.append("native_selected_acceleration_disables_truncation_detection")
    return NativeSearch({"adapter_version": VERSION, "native_version": native_version,
        "configuration": configuration, "settings": settings, "command": command,
        "local_jobs": {"help": help_result.metadata, "work": completed.metadata},
        "native_limitations": native_limitations,
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "returncode": completed.returncode, "model_ref": model_ref, "subject_ref": subject_ref,
        "native_roles": {"query": "covariance_model", "target": "submitted_sequence"},
        "model_sha256": hashlib.sha256(model).hexdigest(), "model_header": header,
        "target_sequence_sha256": hashlib.sha256(sequence.encode("ascii")).hexdigest(),
        "target_length": len(sequence), "molecule_model": "nucleotide", "molecule_assignment": "not_performed",
        "table_format": 3, "coordinate_system": "native_one_based_inclusive",
        "model_coordinate_unit": "model_consensus_position", "framework_operand_role": "query",
        "framework_operand_role_meaning": "investigated sequence, native cmsearch target",
        "no_hit_meaning": "no_reported_match_under_recorded_search_settings_not_organism_absence"},
        stdout, stderr, table, fasta, help_stdout + help_stderr)
