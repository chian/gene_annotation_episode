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
from gene_annotation_episode.episodic_workflow.root.a101.library.read_mapping_values import PRESETS, PARAMETERS, NATIVE_INT_MAX, PARAMETER_RANGES, _COMPLEMENT, native_integer, parameter_schema, parameter_schema_failure, settings, _paf_error, cigar_operations, cs_operations, parse_paf_line, compare_paf_sites

# Pinned minimap2 2.31: sketch.c requires w<256 and k<=28; exposed
# main.c atoi operands use the verified build's signed32-bit C int. These
# bounds describe the native interface, never scientific result quality.





def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()











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



