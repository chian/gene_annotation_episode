"""Original supplied-record fixture functions and original worker validators.

Extracted with whole-span provenance; no native work is executed by these
helpers. Software pins are explicitly synthetic selected-record controls.
"""
from copy import deepcopy
import gzip
import hashlib
import os
from pathlib import Path
import struct
import sys

from gene_annotation_episode.native_atac_differential_contracts import (
    MODE, OPERATION, REQUIRED_MODULES, REQUIRED_DEPENDENCIES, digest,
    _dependency_roots, requested_job_from_atac,
)
from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_preparation_result_publication import PREFIX, _error


def identity(raw, format="bam"):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format=format)


def bam_bytes(*, text=b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrToy\tLN:12000\n", length=12000):
    raw = b"BAM\x01" + struct.pack("<i", len(text)) + text
    raw += struct.pack("<i", 1) + struct.pack("<i", 7) + b"chrToy\0" + struct.pack("<i", length)
    return gzip.compress(raw, mtime=0)


def fake_software():
    files = ["/fixture/native/macs2", "/fixture/site/MACS2/callpeak_cmd.py", "/fixture/site/MACS2/bdgdiff_cmd.py",
        "/fixture/site/MACS2/IO/Parser.cpython-311-x86_64-linux-gnu.so", "/fixture/site/numpy/__init__.py"]
    return {"driver_runtime": {"python_executable": "/fixture/python", "python_sha256": "0" * 64,
        "python_version": "3.12.0", "module_root": "/fixture/source",
        "implementation_files": [{"module": name, "sha256": digest(name)} for name in sorted(REQUIRED_MODULES)],
        "dependencies": [{"distribution": name, "version": "control-fixture", "package_root": "/fixture/deps/" + name,
            "files": [{"path": "/fixture/deps/" + name + "/__init__.py", "sha256": digest(name), "size_bytes": 1}]}
            for name in sorted(REQUIRED_DEPENDENCIES)]},
        "macs2_runtime": {"python_executable": "/fixture/native/python", "python_sha256": "0" * 64,
            "python_version": "3.11.13", "macs2_script": files[0], "macs2_sha256": "0" * 64,
            "macs2_version": "2.2.9.1", "import_roots": ["/fixture/site"],
            "files": [{"path": path, "sha256": "0" * 64, "size_bytes": 1} for path in files]}}


def job_fixture(directory, *, software=None, inputs=None):
    directory.mkdir(parents=True, exist_ok=True)
    inputs = [bam_bytes(), bam_bytes()] if inputs is None else inputs
    bindings, occurrences, samples, conditions = [], [], [], []
    for i, raw in enumerate(inputs, 1):
        path = directory / f"original{i}.bam"
        path.write_bytes(raw)
        file = identity(raw)
        bindings.append(dict(input_key=f"input{i}", file=file, path=str(path)))
        occurrences.append(dict(input_key=f"input{i}", condition_id=f"condition{i}", sample_id=f"sample{i}", reference_id="reference", file=file))
        samples.append(dict(sample_id=f"sample{i}", input_artifact_refs=[file["artifact_ref"]], reference_id="reference",
            biospecimen_id=None, replicate_id=None, origin="synthetic_engineering_fixture"))
        conditions.append(dict(condition_id=f"condition{i}", label=None, sample_ids=[f"sample{i}"]))
    request = dict(version="atac_differential_request_v1", operation=OPERATION, mode=MODE, comparison_key="comparison",
        reference=dict(reference_id="reference", assembly_accession_version=None, source_refs=[], aliases=[],
            contigs=[dict(chromosome="chrToy", length_bp=12000, sequence_accession_version=None, sequence_sha256=None, source_refs=[])]),
        samples=samples, conditions=conditions, inputs=occurrences,
        callpeak=dict(genome_size_argument="12000", qvalue_cutoff=0.05, keep_duplicates=1, nomodel=True, shift_bp=-100,
            extension_size_bp=200, store_bedgraph=True, spmr=False, broad=False, downsample=False),
        bdgdiff=dict(cutoff_log10_lr=3, minimum_length_bp=50, maximum_gap_bp=0), output_prefix="outputs")
    software = fake_software() if software is None else software
    return dict(request=request, software=software, input_bindings=bindings)


def requested(job, directory):
    driver = job["software"]["driver_runtime"]
    env = dict(PYTHONPATH=os.pathsep.join([driver["module_root"], *_dependency_roots(driver)]), PYTHONHOME=sys.base_prefix,
        PYTHONNOUSERSITE="1", PYTHONSAFEPATH="1", PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
        TMP=str(directory / "tmp"), TEMP=str(directory / "tmp"), TMPDIR=str(directory / "tmp"),
        XDG_CACHE_HOME=str(directory / "cache"), PIP_CACHE_DIR=str(directory / "cache/pip"))
    return requested_job_from_atac(job, environment=env)


_HISTORICAL_WORKER_MODULE = "gene_annotation_episode.native_hmmer_preparation_result_worker"
_WORKER_MODULE = "gene_annotation_episode.episodic_workflow.root.library.native_hmmer_preparation_result_worker"
_VERIFY_MODULE = "gene_annotation_episode.native_atac_differential_driver"
_WORKER_SELECTION = PREFIX + "worker_execution_v1"
_HISTORICAL_WORKER_PROGRAM = (
    "import json,sys\n"
    "from pathlib import Path\n"
    "from gene_annotation_episode.native_atac_differential_driver import verify_driver_runtime\n"
    "with open(sys.argv[1]) as stream:\n"
    "    selected=json.load(stream)\n"
    "with open(selected['runtime_path']) as stream:\n"
    "    runtime=json.load(stream)\n"
    "if runtime['data_files'] != []:\n"
    "    raise ValueError('original_worker_required_data_conflict')\n"
    "if sys.prefix != selected['python_home']:\n"
    "    raise ValueError('original_worker_python_home_conflict')\n"
    "verify_driver_runtime(selected['driver_runtime'])\n"
    "from gene_annotation_episode.native_infernal_contracts import native_infernal_digest\n"
    "root=Path(sys.argv[1]).parent\n"
    "with open(root/'original-handle.json') as stream:\n"
    "    binding=json.load(stream)\n"
    "with open(sys.argv[2]) as stream:\n"
    "    plan=json.load(stream)\n"
    "with open(root/'intent.json') as stream:\n"
    "    intent=json.load(stream)\n"
    "if (native_infernal_digest(selected) != binding['selection_sha256'] or "
    "native_infernal_digest(runtime) != selected['runtime_sha256'] or "
    "native_infernal_digest(plan) != selected['plan_sha256'] or "
    "native_infernal_digest(intent) != selected['intent_sha256']):\n"
    "    raise ValueError('original_worker_operands_conflict')\n"
    "from gene_annotation_episode.native_hmmer_preparation_result_worker import main\n"
    "raise SystemExit(main([sys.argv[2]]))\n"
)
_WORKER_PROGRAM = _HISTORICAL_WORKER_PROGRAM.replace(
    "from gene_annotation_episode.native_hmmer_preparation_result_worker import main\n",
    "from gene_annotation_episode.episodic_workflow.root.library.native_hmmer_preparation_result_worker import main\n")


def _worker_program(driver):
    modules = {row["module"] for row in driver["implementation_files"]}
    selected = modules & {_HISTORICAL_WORKER_MODULE, _WORKER_MODULE}
    if len(selected) != 1:
        _error("result_worker_original_source_identity_conflict")
    return (_WORKER_PROGRAM if _WORKER_MODULE in selected else _HISTORICAL_WORKER_PROGRAM)


def _runtime_files(driver):
    from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import validate_driver_runtime
    driver = validate_driver_runtime(driver, required_modules=(_VERIFY_MODULE,))
    _worker_program(driver)
    sources = [{"path": str(Path(driver["module_root"]) / (row["module"].replace(".", "/") + ".py")),
                "sha256": row["sha256"]} for row in driver["implementation_files"]]
    if {row["path"] for row in sources} != {
            str(path) for path in Path(driver["module_root"]).rglob("*") if path.is_file()}:
        _error("result_worker_original_source_inventory_conflict")
    files = [{"path": driver["python_executable"], "sha256": driver["python_sha256"]}, *sources]
    files.extend(file for dependency in driver["dependencies"] for file in dependency["files"])
    for file in files:
        path = Path(file["path"])
        if (not path.is_absolute() or hashlib.sha256(path.read_bytes()).hexdigest() != file["sha256"]
                or "size_bytes" in file and path.stat().st_size != file["size_bytes"]):
            _error("result_worker_original_software_changed")
    return driver


def _command(reservation):
    return [reservation["software"]["python"]["path"], "-B", "-m",
        "gene_annotation_episode.restriction_mapping_worker", reservation["request_file"]["path"],
        reservation["output_directory"]]


