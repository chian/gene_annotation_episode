"""Retain original BAM SAM-header bytes without synthesizing dictionary rows."""
from __future__ import annotations

import gzip
import os
from pathlib import Path
import struct
import zlib

from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_atac_differential_contracts import POLICY, failure, require, path_value, validate_atac_record


def extract_atac_bam_header(*, input_path: Path, input_file: dict, input_key: str,
        callpeak_run_key: str, input_ordinal: int, output_path: Path,
        output_relative_path: str, policy: LocalJobPolicy) -> dict:
    """Stream the BAM header text verbatim, then check its binary dictionary.

    No alignment records are decoded and no @SQ is reconstructed. Complete raw
    text survives a subsequent binary-dictionary inconsistency as failed evidence.
    """
    from .native_atac_differential_driver import _regular, _writing, declaration, stream_identity
    require(type(policy) is LocalJobPolicy and policy.to_dict() == POLICY, "resource_allocation")
    output_path = Path(path_value(str(output_path), absolute=True))
    relative = path_value(output_relative_path, absolute=False)
    # The producer checks this relationship against its selected plan. Derive
    # the supplied root by removing the full explicit relative suffix only.
    require(tuple(output_path.parts[-len(relative.parts):]) == relative.parts, "invalid_output_path")
    root = output_path
    for _ in relative.parts:
        root = root.parent
    spec = dict(relative_path=output_relative_path, format="sam_header_text")
    failures, extent, outcome, text_written = [], "unknown", "failed", False
    try:
        with _regular(input_path) as source:
            before = os.fstat(source.fileno())
            expected = {k: input_file[k] for k in ("sha256", "size_bytes")}
            require(stream_identity(source) == expected, "artifact_digest_mismatch")
            with gzip.GzipFile(fileobj=source, mode="rb") as bam:
                def exact(size):
                    value = bam.read(size)
                    require(len(value) == size, "input_unavailable")
                    return value
                def integer():
                    return struct.unpack("<i", exact(4))[0]
                require(exact(4) == b"BAM\x01", "input_unavailable")
                length = integer()
                require(length >= 0, "input_unavailable")
                check_scratch_budget(root.parent, policy, additional_bytes=length)
                left, text_error = length, None
                with _writing(output_path) as target:
                    try:
                        while left:
                            block = bam.read(min(left, 65536))
                            if not block:
                                raise ValueError("input_unavailable")
                            target.write(block)
                            left -= len(block)
                    except (OSError, EOFError, ValueError, zlib.error) as error:
                        text_error = error
                text_written = True
                extent = "partial" if left else "complete"
                if text_error is not None:
                    raise text_error
                # Compare exact text observations with BAM's binary dictionary.
                text_rows = []
                with _regular(output_path) as text:
                    for raw in text:
                        if raw.startswith(b"@SQ\t"):
                            fields = raw.rstrip(b"\n").removesuffix(b"\r").split(b"\t")
                            names = [x[3:] for x in fields if x.startswith(b"SN:")]
                            lengths = [x[3:] for x in fields if x.startswith(b"LN:")]
                            require(len(names) == len(lengths) == 1 and names[0] and lengths[0].isdigit(), "reference_conflict")
                            text_rows.append((names[0], int(lengths[0])))
                count = integer()
                require(count >= 0 and count == len(text_rows), "reference_conflict")
                seen = set()
                for ordinal in range(count):
                    name_length = integer()
                    require(name_length > 1 and name_length <= length + 1, "reference_conflict")
                    name = exact(name_length)
                    require(name[-1:] == b"\0" and b"\0" not in name[:-1], "reference_conflict")
                    contig_length = integer()
                    row = (name[:-1], contig_length)
                    require(contig_length > 0 and row == text_rows[ordinal] and row[0] not in seen, "reference_conflict")
                    seen.add(row[0])
            source.seek(0)
            require(stream_identity(source) == expected, "artifact_digest_mismatch")
            after = os.fstat(source.fileno())
            require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "artifact_digest_mismatch")
            outcome = "succeeded"
    except (OSError, EOFError, ValueError, zlib.error) as error:
        code = str(error) if str(error) in ("artifact_digest_mismatch", "reference_conflict") else "input_unavailable"
        failures.append(failure(code, "reference", step_key=callpeak_run_key, binding_key=input_key,
            artifact_ref=input_file["artifact_ref"], requirement="matching_reference_dictionary" if code == "reference_conflict"
                else "matching_file_identity" if code == "artifact_digest_mismatch" else "actual_bam_header"))
    except Exception as error:
        from .acquisition import AcquisitionError
        if not isinstance(error, AcquisitionError):
            raise
        failures.append(failure("resource_limit", "reference", step_key=callpeak_run_key, binding_key=input_key,
            artifact_ref=input_file["artifact_ref"], requirement="resource_allocation"))
    return validate_atac_record("HeaderExtraction", dict(version="atac_bam_header_extraction_v1",
        input_key=input_key, callpeak_run_key=callpeak_run_key, input_ordinal=input_ordinal,
        input_file=input_file, header=declaration(spec, root), producer_outcome=outcome,
        supplied_extent=extent if text_written else "unknown", failures=failures))
