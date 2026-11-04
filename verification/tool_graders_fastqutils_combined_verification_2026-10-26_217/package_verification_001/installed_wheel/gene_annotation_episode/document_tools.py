"""Selected archive/PDF transformations over actual source artifacts.

Workers receive only already resolved source paths and caller-owned software.
They never touch Store or infer biological claims from the document.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import zipfile

from .acquisition import AcquisitionError
from .domain import ContractError
from .local_jobs import LocalJobPolicy, run_local_job

VERSION = "selected_archive_poppler_v1"


@dataclass(frozen=True)
class DocumentOutput:
    metadata: dict
    content: bytes | None = None
    media_type: str | None = None
    stdout: bytes = b""
    stderr: bytes = b""


def resource(path):
    resolved = Path(path).expanduser().resolve() if path is not None else None
    return {"executable": str(resolved) if resolved else None,
        "executable_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest() if resolved and resolved.is_file() else None}


def archive_inventory(path: Path, *, offset=0, limit=50) -> DocumentOutput:
    members = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            total = len(entries)
            for ordinal in range(offset, min(offset + limit, total)):
                entry = entries[ordinal]
                unix_type = (entry.external_attr >> 16) & 0o170000
                members.append({"ordinal": ordinal, "name": entry.filename, "size": entry.file_size,
                    "compressed_size": entry.compress_size, "crc32": entry.CRC,
                    "header_offset": entry.header_offset, "entry_type": "directory" if entry.is_dir() else "symlink" if unix_type == 0o120000 else "file"})
        archive_format = "zip"
    elif tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            entries = archive.getmembers()
            total = len(entries)
            for ordinal in range(offset, min(offset + limit, total)):
                entry = entries[ordinal]
                members.append({"ordinal": ordinal, "name": entry.name, "size": entry.size,
                    "compressed_size": None, "crc32": None, "header_offset": entry.offset,
                    "entry_type": "file" if entry.isfile() else "directory" if entry.isdir() else "symlink" if entry.issym() else "hardlink" if entry.islnk() else "other"})
        archive_format = "tar"
    else:
        raise ContractError("supported_zip_or_tar_source_required")
    return DocumentOutput({"operation": "archive_inventory", "adapter_version": VERSION,
        "python_version": sys.version, "archive_format": archive_format, "members": members,
        "offset": offset, "limit": limit, "total": total,
        "next_offset": offset+len(members) if offset+len(members)<total else None})


def archive_extract(path: Path, member: dict) -> DocumentOutput:
    # Reading a selected stream never follows source paths/symlinks or writes
    # a member-supplied name into the host filesystem.
    if member["entry_type"] != "file":
        raise ContractError("archive_member_not_regular_file")
    ordinal = member["ordinal"]
    if member["archive_format"] == "zip":
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if ordinal >= len(entries):
                raise ContractError("archive_member_identity_mismatch")
            entry = entries[ordinal]
            if (entry.filename, entry.file_size, entry.CRC, entry.header_offset) != (member["name"], member["size"], member["crc32"], member["header_offset"]):
                raise ContractError("archive_member_identity_mismatch")
            content = archive.read(entry)  # validates native ZIP CRC on read
    else:
        with tarfile.open(path, "r:*") as archive:
            entries = archive.getmembers()
            if ordinal >= len(entries):
                raise ContractError("archive_member_identity_mismatch")
            entry = entries[ordinal]
            if (entry.name, entry.size, entry.offset) != (member["name"], member["size"], member["header_offset"]) or not entry.isfile():
                raise ContractError("archive_member_identity_mismatch")
            content = archive.extractfile(entry).read()
    return DocumentOutput({"operation": "archive_extract", "adapter_version": VERSION,
        "python_version": sys.version, "member": member, "transformation": "selected_uncompressed_member_bytes",
        "output_sha256": hashlib.sha256(content).hexdigest()}, content, "application/octet-stream")


def pdf_native(path: Path, *, operation: str, executables: dict,
               first_page=None, last_page=None, page=None, layout="reading_order", dpi=150,
               job_limits=None, cancel_event=None) -> DocumentOutput:
    tool = {"info": "pdfinfo", "text": "pdftotext", "page": "pdftoppm"}[operation]
    selected = resource(executables.get(tool))
    executable = selected["executable"]
    if executable is None:
        raise AcquisitionError(tool + "_not_configured", phase="local_preflight")
    if not Path(executable).is_file():
        raise AcquisitionError(tool + "_executable_missing", phase="local_preflight")
    policy = LocalJobPolicy.from_config(job_limits)
    path = Path(path).resolve()
    started_at = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix="annotation-pdf-") as directory:
        directory = Path(directory)
        version_result = run_local_job([executable, "-v"], cwd=directory, policy=policy,
            stdout_path=directory/"version.stdout", stderr_path=directory/"version.stderr",
            cancel_event=cancel_event)
        version_bytes = version_result.stdout_path.read_bytes() + version_result.stderr_path.read_bytes()
        version_text = version_bytes.decode("utf-8", errors="replace")
        match = re.search(re.escape(tool) + r" version ([^\s]+)", version_text)
        output = directory / "selected"
        if operation == "info":
            command = [executable, "-enc", "UTF-8", "-isodates", str(path)]
        elif operation == "text":
            if first_page > last_page:
                raise ContractError("pdf_page_range_reversed")
            command = [executable, "-f", str(first_page), "-l", str(last_page), "-enc", "UTF-8", "-eol", "unix"]
            if layout != "reading_order":
                command.append("-layout" if layout == "layout" else "-raw")
            command += [str(path), "-"]
        else:
            command = [executable, "-f", str(page), "-l", str(page), "-r", str(dpi), "-png", "-singlefile", str(path), str(output)]
        completed = run_local_job(command, cwd=directory, policy=policy,
            stdout_path=directory/"native.stdout", stderr_path=directory/"native.stderr",
            cancel_event=cancel_event)
        stdout, stderr = completed.stdout_path.read_bytes(), completed.stderr_path.read_bytes()
        if operation == "page":
            content = output.with_suffix(".png").read_bytes() if output.with_suffix(".png").is_file() else None
            media_type = "image/png"
        else:
            content, media_type = stdout, "text/plain"
    selection = ({} if operation == "info" else
        {"first_page": first_page, "last_page": last_page, "layout": layout,
         "encoding": "UTF-8", "end_of_line": "unix", "page_breaks": True} if operation == "text" else
        {"page": page, "dpi": dpi, "image_format": "PNG", "page_box": "native_default_media_box"})
    metadata = {"operation": "pdf_" + operation, "adapter_version": VERSION,
        "software": tool, "software_version": match.group(1) if match else None,
        "resource": selected, "native_version_output": version_text, "command": command,
        "job_limits": policy.to_dict(),
        "local_jobs": {"version": version_result.metadata, "work": completed.metadata},
        "returncode": completed.returncode, "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(), "native_page_numbering": "one_based_physical_pdf_page",
        "selection": selection,
        "transformation": "native_pdf_information" if operation == "info" else "native_utf8_text_derivative_not_pdf_byte_coordinates" if operation == "text" else "native_rasterized_pdf_page_not_an_interpretation"}
    if operation == "info" and completed.returncode == 0:
        match = re.search(rb"^Pages:\s+([0-9]+)\s*$", stdout, re.MULTILINE)
        metadata["page_count"] = int(match.group(1)) if match else None
    return DocumentOutput(metadata, content, media_type, stdout, stderr)
