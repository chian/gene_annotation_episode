"""Native genomic read placements, separate from correction and interpretation.

PAF coordinates are operand-local, never an exact extraction/assembly ancestry
map. The adapter requests base alignment and preserves every reported row. The
reference index is a disposable operational cache bound to actual input bytes,
index options and executable bytes, not an independent scientific result.
"""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import shutil
import sqlite3
import tempfile
import tomllib

from .acquisition import AcquisitionError
from .domain import ContractError, canonical
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job_async

VERSION = "minimap2_paf_source_placements_v1"
PRESETS = ["map-ont", "map-pb", "map-hifi", "lr:hq", "map-iclr", "sr"]
PARAMETERS = {"kmer": "-k", "window": "-w", "max_secondary": "-N", "seed": "--seed"}
# Pinned minimap2 2.31: sketch.c requires w<256 and k<=28; exposed
# main.c atoi operands use the verified build's signed32-bit C int. These
# bounds describe the native interface, never scientific result quality.
NATIVE_INT_MAX = 2147483647
PARAMETER_RANGES = {"kmer": (1,28), "window": (1,255),
    "max_secondary": (0,NATIVE_INT_MAX), "seed": (0,NATIVE_INT_MAX)}
_COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVNacgtryswkmbdhvn", "TGCAYRSWMKVHDBNtgcayrswmkvhdbn")


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def native_integer(value, *, field_path, minimum, maximum):
    detail = {"field_path": list(field_path), "minimum": minimum, "maximum": maximum,
        "native_representation": "minimap2_2_31_supported_integer_interface"}
    if type(value) is not int:
        raise ContractError("native_mapping_integer_required", detail={**detail, "actual_type": type(value).__name__})
    if not minimum <= value <= maximum:
        raise ContractError("native_mapping_integer_out_of_range", detail={**detail, "value": value})
    return value


def parameter_schema(name):
    low, high = PARAMETER_RANGES[name]
    field = {"type":"integer", "minimum":low, "maximum":high}
    if name == "max_secondary":
        field["description"] = ("Native -N0 is a supported alias: it disables secondary output and retains "
            "the prior preset's internal best_n, even with secondary=true. Selected flags are preserved.")
    return field


def parameter_schema_failure(error, *, path_prefix=()):
    """Project an existing field validation failure; do not validate again.

    The caller selects the actual reads.map schema branch. Other fields and
    schema failures keep their normal feedback rather than being guessed here.
    """
    path = list(getattr(error, "absolute_path", ()))
    prefix = list(path_prefix)
    relative = path[len(prefix):] if path[:len(prefix)] == prefix else []
    if (len(relative) != 2 or relative[0] != "parameters"
            or relative[1] not in PARAMETER_RANGES
            or error.validator not in ("minimum", "maximum", "type")
            or error.schema.get("type") != "integer"):
        return None
    detail = {"field_path": relative, "minimum": error.schema["minimum"],
        "maximum": error.schema["maximum"], "schema_keyword": error.validator,
        "native_representation": "minimap2_2_31_supported_integer_interface"}
    if error.validator == "type":
        detail["actual_type"] = type(error.instance).__name__
        code = "native_mapping_integer_required"
    else:
        detail["value"] = error.instance
        code = "native_mapping_integer_out_of_range"
    return {"code": code, "detail": detail}


def local_configuration(*, executable=None, cpu=None, cache_dir=None, job_limits=None):
    defaults = tomllib.loads(Path(__file__).with_name("defaults.toml").read_text())["local_tools"]
    cpu = defaults["minimap2_cpu"] if cpu is None else cpu
    native_integer(cpu, field_path=["local_tools","minimap2_cpu"], minimum=1, maximum=NATIVE_INT_MAX)
    path = Path(executable).expanduser().resolve() if executable is not None else None
    return {"executable": str(path) if path else None, "cpu": cpu,
        "job_limits": LocalJobPolicy.from_config(job_limits).to_dict(),
        "cache_dir": str(Path(cache_dir).expanduser().resolve()) if cache_dir is not None else None,
        "executable_sha256": file_digest(path) if path and path.is_file() else None,
        "adapter_version": VERSION}


def settings(preset, parameters=None):
    if preset not in PRESETS:
        raise ContractError("unsupported_genomic_mapping_preset")
    given = dict(parameters or {})
    if set(given) - (set(PARAMETERS) | {"secondary", "homopolymer_compression"}):
        raise ContractError("unknown_mapping_parameter")
    for key,(low,high) in PARAMETER_RANGES.items():
        if key in given:
            native_integer(given[key], field_path=["parameters",key], minimum=low, maximum=high)
    for key in ("secondary", "homopolymer_compression"):
        if key in given and type(given[key]) is not bool:
            raise ContractError("invalid_native_mapping_parameter", detail={"field_path": ["parameters", key]})
    # -H is enable-only. A false override must not silently leave a preset's
    # enabled HPC unchanged; the initial interface exposes an explicit true.
    if given.get("homopolymer_compression") is False:
        raise ContractError("native_homopolymer_flag_is_enable_only",
            detail={"field_path": ["parameters", "homopolymer_compression"], "allowed_value": True})
    effects = ([{"option":"max_secondary", "requested":0,
        "native_effect":"secondary_output_disabled_prior_preset_internal_best_n_retained",
        "secondary_yes_does_not_override_zero_alias":True}]
        if given.get("max_secondary") == 0 else [])
    return {"preset": preset, "overrides": given, "native_option_effects":effects,
        "base_alignment": "PAF_cg_and_cs_long",
        "fragment_mode": "unpaired", "quality_used_for_mapping": False,
        "native_unset_options": "installed_version_preset_defaults_not_host_overrides"}


@dataclass
class NativeMapping:
    directory: Path
    metadata: dict

    def path(self, name):
        return self.directory / name

    def close(self):
        shutil.rmtree(self.directory)


async def run_mapping(directory, *, configuration, preset, parameters=None, input_metadata=None,
                      job_limits=None):
    """Run one native index/map operation over owner-staged immutable files."""
    directory = Path(directory).resolve()
    executable = configuration["executable"]
    if executable is None:
        raise AcquisitionError("minimap2_not_configured", phase="local_preflight")
    if not Path(executable).is_file():
        raise AcquisitionError("minimap2_executable_missing", phase="local_preflight")
    effective = settings(preset, parameters)
    native_integer(configuration["cpu"], field_path=["local_tools","minimap2_cpu"],
        minimum=1, maximum=NATIVE_INT_MAX)
    policy = LocalJobPolicy.from_config(job_limits if job_limits is not None else configuration.get("job_limits"))
    configuration = {**configuration, "executable_sha256": await asyncio.to_thread(file_digest, executable),
        "job_limits": policy.to_dict()}
    started = datetime.now(timezone.utc).isoformat()
    commands = {}
    local_jobs = {}
    async def process(phase, stdout, stderr):
        result = await run_local_job_async(commands[phase], cwd=directory, policy=policy,
            stdout_path=directory/stdout, stderr_path=directory/stderr)
        local_jobs[phase] = result.metadata
        return result.returncode
    commands["version"] = [executable, "--version"]
    rc = await process("version", "version.stdout", "version.stderr")
    if rc != 0:
        raise AcquisitionError("minimap2_version_unavailable", phase="local_preflight",
            diagnostic={"returncode": rc, "stderr": (directory/"version.stderr").read_text(errors="replace")})
    native_version = (directory/"version.stdout").read_text().strip()
    commands["help"] = [executable, "-h"]
    await process("help", "help.stdout", "help.stderr")
    target_digest = await asyncio.to_thread(file_digest, directory/"references.fasta")
    index_options = {key: value for key, value in effective["overrides"].items()
        if key in {"kmer", "window", "homopolymer_compression"}}
    key_basis = {"adapter_version": VERSION, "executable_sha256": configuration["executable_sha256"],
        "native_version": native_version, "target_fasta_sha256": target_digest,
        "preset": preset, "index_overrides": index_options}
    key = hashlib.sha256(canonical(key_basis).encode()).hexdigest()
    if configuration["cache_dir"] is None:
        raise ContractError("native_mapping_cache_directory_unbound")
    cache = Path(configuration["cache_dir"])
    cache.mkdir(parents=True, exist_ok=True)
    configuration = {**configuration, "effective_cache_dir": str(cache.resolve())}
    cache_index, cache_manifest = cache/(key+".mmi"), cache/(key+".json")
    index = directory/"references.mmi"
    cached, build = False, None
    if cache_index.is_file() and cache_manifest.is_file():
        try:
            candidate = json.loads(cache_manifest.read_text())
            if candidate["key_basis"] == key_basis:
                saved_stdout = base64.b64decode(candidate["stdout_base64"], validate=True)
                saved_stderr = base64.b64decode(candidate["stderr_base64"], validate=True)
                if not isinstance(candidate["command"], list) or not isinstance(candidate["created_at"], str):
                    raise ValueError("incomplete_cache_provenance")
                check_scratch_budget(directory, policy, additional_bytes=cache_index.stat().st_size)
                await asyncio.to_thread(shutil.copyfile, cache_index, index)
                check_scratch_budget(directory, policy)
                if await asyncio.to_thread(file_digest, index) == candidate["index_sha256"]:
                    build, cached = candidate, True
        except (OSError, ValueError, KeyError):
            # A torn/missing disposable cache does not invalidate evidence.
            pass
    index_flags = []
    for name in ("kmer", "window"):
        if name in index_options:
            index_flags += [PARAMETERS[name], str(index_options[name])]
    if index_options.get("homopolymer_compression"):
        index_flags.append("-H")
    if not cached:
        commands["index"] = [executable, "-x", preset, *index_flags, "-t", str(configuration["cpu"]),
            "-d", str(index), str(directory/"references.fasta")]
        rc = await process("index", "index.stdout", "index.stderr")
        if rc == 0 and index.is_file():
            build = {"key_basis": key_basis, "index_sha256": await asyncio.to_thread(file_digest, index),
                "command": commands["index"], "created_at": datetime.now(timezone.utc).isoformat(),
                "stdout_base64": base64.b64encode((directory/"index.stdout").read_bytes()).decode(),
                "stderr_base64": base64.b64encode((directory/"index.stderr").read_bytes()).decode()}
            # Publish complete cache members atomically. Concurrent builders may
            # do the same local derivation; copied bytes are digest-checked before
            # any later reuse, so a torn pair is simply an unused cache entry.
            with tempfile.NamedTemporaryFile(dir=cache, delete=False) as out:
                temporary = Path(out.name)
            await asyncio.to_thread(shutil.copyfile, index, temporary)
            temporary.replace(cache_index)
            with tempfile.NamedTemporaryFile(dir=cache, delete=False) as out:
                out.write(canonical(build).encode()); temporary = Path(out.name)
            temporary.replace(cache_manifest)
        else:
            return NativeMapping(directory, {"adapter_version": VERSION, "configuration": configuration,
                "settings": effective, "native_version": native_version, "commands": commands,
                "local_jobs": local_jobs,
                "phase": "native_index", "returncode": rc, "started_at": started,
                "finished_at": datetime.now(timezone.utc).isoformat(), "input_metadata": input_metadata})
    else:
        check_scratch_budget(directory, policy, additional_bytes=len(saved_stdout)+len(saved_stderr))
        (directory/"index.stdout").write_bytes(saved_stdout)
        (directory/"index.stderr").write_bytes(saved_stderr)
        check_scratch_budget(directory, policy)
    mapping_flags = []
    for name in ("max_secondary", "seed"):
        if name in effective["overrides"]:
            mapping_flags += [PARAMETERS[name], str(effective["overrides"][name])]
    if "secondary" in effective["overrides"]:
        mapping_flags += ["--secondary=" + ("yes" if effective["overrides"]["secondary"] else "no")]
    commands["map"] = [executable, "-x", preset, "-c", "--cs=long", "--frag=no", "-t", str(configuration["cpu"]),
        *mapping_flags, str(index), str(directory/"queries.fasta")]
    resource_failure = None
    try:
        rc = await process("map", "mappings.paf", "mapping.stderr")
    except AcquisitionError as error:
        if error.code != "local_job_resource_limit":
            raise
        # The job has been reaped. Its complete PAF rows remain independent
        # observations even when later native work exceeded a resource limit.
        resource_failure = {"code": error.code, "phase": error.phase,
            "operational": error.operational, "diagnostic": error.diagnostic}
        local_jobs["map"] = dict(error.operational or {})
        status = (error.operational or {}).get("service_exit", {})
        exit_kind, exit_status = status.get("EXIT_CODE"), status.get("EXIT_STATUS")
        if "native_returncode" in (error.operational or {}):
            # The v2 runner records wrapper and native outcomes separately. A
            # killed wrapper does not establish the native child's exit code.
            rc = error.operational["native_returncode"]
        elif exit_kind == "exited" and str(exit_status).isdigit():
            rc = int(exit_status)
        elif exit_kind in {"killed", "dumped"}:
            try:
                rc = -int(exit_status)
            except (TypeError, ValueError):
                signal_value = getattr(signal, "SIG" + str(exit_status), None)
                rc = -int(signal_value) if signal_value is not None else None
        else:
            rc = None  # An unknown exit must not be presented as a known signal.
    metadata = {"adapter_version": VERSION, "configuration": configuration, "settings": effective,
        "native_version": native_version, "commands": commands, "phase": "native_mapping", "returncode": rc,
        "local_jobs": local_jobs,
        "resource_failure": resource_failure,
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "index": {"cache_key": key, "reused": cached, **build},
        "input_metadata": input_metadata,
        "limitations": ["native_heuristic_placements_not_orthology_or_function",
            "no_reported_placement_is_not_biological_absence",
            "native_secondary_ranking_is_not_molecule_independence",
            "native_MAPQ_is_unreliable_for_multipart_indexes",
            "FASTA_staging_preserves_sequence_symbols_but_does_not_use_FASTQ_qualities",
            "native_preset_and_unset_defaults_are_version_dependent"]}
    if not (directory/"mappings.paf").is_file():
        return NativeMapping(directory, metadata)
    # Projection is disk-streamed in a host thread. Native cgroup limits do not
    # bound this Python projection worker; it is a distinct resource boundary.
    # A cancellation must not remove input/output files under a still-running
    # parser worker. Wait for its purely local projection before unwinding.
    projection = asyncio.create_task(asyncio.to_thread(project_output, directory))
    try:
        await asyncio.shield(projection)
    except asyncio.CancelledError:
        await projection
        raise
    return NativeMapping(directory, metadata)


def _paf_error(error):
    code = str(error)
    # Preserve the established representation-failure category for ordinary
    # callers, with the new parser's precise tag diagnostic retained in detail.
    if code.startswith("native_paf_duplicate_tag:") or code in {
            "invalid_native_paf_tag", "invalid_native_paf_tag_value"}:
        return ContractError("invalid_native_paf_row", detail={"native_parser_code": code})
    return ContractError(code)


def cigar_operations(cigar):
    from .minimap2_grading_inputs import cigar_operations as parse_cigar
    try:
        return [(row["operation"], row["length"]) for row in parse_cigar(cigar)]
    except ValueError as error:
        raise _paf_error(error) from error


def cs_operations(cs):
    from .minimap2_grading_inputs import cs_operations as parse_cs
    try:
        return [(row["operation"], row["length"], row["value"]) for row in parse_cs(cs)]
    except ValueError as error:
        raise _paf_error(error) from error


def parse_paf_line(line):
    """Shared native parser for publication, admission and later site use.

    Raw lines remain in the original PAF artifact. Do not add a full raw row to
    the ordinary placement preview: it includes long alignment strings.
    """
    from .minimap2_grading_inputs import parse_minimap2_paf_row
    try:
        row = parse_minimap2_paf_row(line)
    except ValueError as error:
        raise _paf_error(error) from error
    return {key: value for key, value in row.items() if key not in {"native_line", "issues"}}


def project_output(directory):
    """Disk-stream independent native rows; one bad row never loses siblings."""
    directory = Path(directory)
    with sqlite3.connect(directory/"operands.sqlite") as operands, \
            (directory/"mappings.paf").open("rb") as native, \
            (directory/"placements.jsonl").open("w") as output, \
            (directory/"projection-errors.jsonl").open("w") as errors:
        line_number, offset = 0, 0
        for line in native:
            line_number += 1
            locator = {"line_number": line_number, "row_start": offset, "row_end": offset+len(line)}
            offset += len(line)
            try:
                row = parse_paf_line(line)
                for role, name, length in (("query", row["query_name"], row["query_length"]),
                        ("reference", row["reference_name"], row["reference_length"])):
                    actual = operands.execute("SELECT length FROM operands WHERE role=? AND subject_ref=?", (role,name)).fetchone()
                    if actual is None or actual[0] != length:
                        raise ContractError("native_paf_operand_identity_mismatch", detail={"role": role, "subject_ref": name})
                output.write(canonical({**locator, **row})+"\n")
            except ContractError as error:
                errors.write(canonical({**locator, "code": str(error), "detail": error.detail})+"\n")


def compare_paf_sites(row, reference_positions, *, query, reference, quality=None, quality_encoding="unspecified"):
    """Observe actual operand bases along a native CIGAR, never call variants.

    Query positions/quality indices always use its original strand. Returned
    query_residue is oriented to the reference; original symbols remain explicit.
    Insertions use a reference boundary, not a fabricated reference residue.
    """
    if len(query) != row["query_length"] or len(reference) != row["reference_length"]:
        raise ContractError("native_alignment_operand_length_changed")
    if not row.get("cigar"):
        raise ContractError("native_base_alignment_unavailable")
    if any(type(p) is not int or not 0 <= p < len(reference) for p in reference_positions):
        raise ContractError("invalid_reference_site")
    if quality is not None and len(quality) != len(query):
        raise ContractError("native_query_quality_length_mismatch")
    if quality_encoding not in {"unspecified", "phred33", "phred64", "solexa64"}:
        raise ContractError("unknown_quality_encoding")
    wanted, found, insertions = set(reference_positions), {}, []
    plus = row["strand"] == "+"
    q = row["query_interval"][0] if plus else row["query_interval"][1]-1
    r = row["reference_interval"][0]
    direction = 1 if plus else -1

    def query_data(position):
        original = query[position]
        char = quality[position] if quality is not None else None
        numeric = (ord(char) - (33 if quality_encoding == "phred33" else 64)
            if char is not None and quality_encoding != "unspecified" else None)
        return {"query_position": position, "query_original_residue": original,
            "query_residue": original if plus else original.translate(_COMPLEMENT),
            "query_quality_character": char, "query_quality_score": numeric,
            "quality_encoding": quality_encoding}

    for kind, size in cigar_operations(row["cigar"]):
        if kind in "M=X":
            for position in wanted:
                if r <= position < r+size:
                    data = query_data(q + direction*(position-r))
                    found[position] = {"reference_position": position, "reference_residue": reference[position],
                        **data, "relationship": "identical" if data["query_residue"].upper() == reference[position].upper() else "substituted",
                        "native_operation": kind, "query_strand": row["strand"]}
            q += direction*size; r += size
        elif kind in "DN":
            for position in wanted:
                if r <= position < r+size:
                    found[position] = {"reference_position": position, "reference_residue": reference[position],
                        "query_position": None, "query_original_residue": None, "query_residue": None,
                        "query_quality_character": None, "query_quality_score": None, "quality_encoding": quality_encoding,
                        "relationship": "gap" if kind == "D" else "reference_skip", "native_operation": kind,
                        "query_strand": row["strand"]}
            r += size
        else:  # I: query bases between reference positions, not a reference base.
            if r in wanted or r-1 in wanted:
                indices = range(q, q + direction*size, direction)
                original_positions = [min(q, q+direction*(size-1)), max(q, q+direction*(size-1))+1]
                insertions.append({"reference_boundary": r, "query_interval": original_positions,
                    "query_strand": row["strand"], "query_sequence": "".join(query_data(p)["query_residue"] for p in indices),
                    "query_quality_characters": ("".join(quality[p] for p in indices) if quality is not None else None),
                    "quality_encoding": quality_encoding, "native_operation": "I"})
            q += direction*size
    return {"sites": [found.get(p, {"reference_position": p, "reference_residue": None,
        "query_position": None, "query_residue": None, "relationship": "outside_alignment",
        "query_strand": row["strand"]}) for p in reference_positions], "insertions": insertions,
        "quality_encoding": quality_encoding, "mapping_quality": row["mapping_quality"],
        "mapping_quality_available": row["mapping_quality_available"],
        "native_alignment_type": row["native_alignment_type"]}
