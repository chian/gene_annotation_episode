"""Bounded prerequisite facts and tiny upstream fixture acquisition, not a parser.

No production chromatin module is imported. Complete HIC population extraction
and scientific calculations are intentionally not implemented by this probe.
"""
from pathlib import Path
import ast
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import urllib.request
import zlib

PACKET = Path(sys.argv[1]).resolve()
REPO = PACKET.parents[1]
OUT = Path.cwd()

def pin(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": str(path), "resolved_path": str(path.resolve()),
            "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

dependencies = []
for name in ("hic-straw", "hictkpy", "cooler", "numpy", "h5py"):
    try:
        dist = importlib.metadata.distribution(name)
        dependencies.append({"distribution": name, "status": "metadata_present",
            "version": dist.version, "metadata_files": [pin(dist.locate_file(f))
                for f in dist.files or () if str(f).endswith(".dist-info/METADATA")]})
    except importlib.metadata.PackageNotFoundError:
        dependencies.append({"distribution": name, "status": "not_found_in_selected_environment"})
numpy = importlib.import_module("numpy")
write("DEPENDENCIES.json", {"interpreter": pin(sys.executable), "python": platform.python_version(),
    "prefix": sys.prefix, "dependencies": dependencies,
    "actual_imports": {"numpy": numpy.__version__, "zlib_compile": zlib.ZLIB_VERSION,
        "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION},
    "module_pins": [pin(numpy.__file__)] + ([pin(zlib.__file__)] if hasattr(zlib, "__file__") else []),
    "zlib_origin": zlib.__spec__.origin,
    "commands_found_on_path_not_invoked": {name: shutil.which(name) for name in ("hictk", "straw", "java")},
    "proc_maps": Path("/proc/self/maps").read_text()})

unit = os.environ.get("SYSTEMD_EXEC_PID")
write("CGROUP.json", {"cgroup": Path("/proc/self/cgroup").read_text(),
    "systemd_exec_pid": unit})

tree = json.loads((PACKET / "sources/igv-straw-tree.json").read_text())
revision = tree["sha"]
chosen = "test/data/testFiles/testBp.hic"
entry = next(row for row in tree["tree"] if row["path"] == chosen)
assert entry["size"] == 1908
url = f"https://raw.githubusercontent.com/aidenlab/hic-straw/{revision}/{chosen}"
receipt = {"url": url, "repository_commit": revision, "repository_entry": entry,
    "metadata_source": pin(PACKET / "sources/igv-straw-tree.json"),
    "maximum_bytes": entry["size"], "retry_count": 0}
write("FIXTURE_ACQUISITION_REQUEST.json", receipt)
try:
    with urllib.request.urlopen(url) as response:
        data = response.read(entry["size"] + 1)
        receipt.update(status=response.status, headers=dict(response.headers), final_url=response.url)
    assert len(data) == entry["size"]
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == entry["sha"]
    destination = OUT / "testBp.hic"
    destination.write_bytes(data)
    destination.chmod(0o444)
    receipt.update(file=pin(destination), magic_hex=data[:4].hex(),
        header_version=struct.unpack_from("<i", data, 4)[0],
        evidence_extent="full_original_bytes_acquired_header_magic_version_only_examined")
except Exception as error:
    receipt.update(error_type=type(error).__name__, error=str(error))
write("FIXTURE_ACQUISITION_RECEIPT.json", receipt)

source = REPO / "gene_annotation_episode/chromatin_interaction_contracts.py"
module = ast.parse(source.read_bytes())
literal = next(node.value.args[0] for node in module.body
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_DEFINITIONS" for t in node.targets))
definitions = json.loads(ast.literal_eval(literal))
names = ("ContactSpec", "ContactExtraction", "NativeMetadata", "Chromosome", "NativeVectorDescriptor",
    "PopulationExtraction", "PopulationReadEvidence", "RawCellPopulation", "NormalizationSummary",
    "TableDraft", "TableDescriptor", "Locator", "Failure", "Binding", "SoftwareBinding")
write("CURRENT_LITERAL_DEFINITIONS.json", {"source": pin(source),
    "definitions": {name: definitions[name] for name in names}})
worked_path = REPO / "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json"
worked = json.loads(worked_path.read_text())
write("WORKED_RECORD_INVENTORY.json", {"source": pin(worked_path),
    "record_type": worked["record_type"], "records": [{key: value for key, value in row.items() if key not in ("value", "record")} for row in worked["records"]]})
print(json.dumps({"dependencies": dependencies, "fixture_version": receipt.get("header_version"),
    "fixture_bytes": receipt.get("file", {}).get("size_bytes"), "fixture_error": receipt.get("error"),
    "contract_definitions": len(names), "production_imported": False}))
