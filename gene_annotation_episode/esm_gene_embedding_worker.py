"""One offline, explicitly pinned ESM2 attempt over supplied protein evidence.

No Ensembl request, model download, device fallback, OOM retry, Source creation
or scientific-confidence calculation occurs here. ESM/PyTorch own inference,
the token mean, and the equal mean over successful isoform occurrences.
"""
from copy import deepcopy
import hashlib
import io
import math
from pathlib import Path

from . import esm_gene_embedding_contracts as contracts
from .execution_contracts import digest
from .native_atac_differential_driver import _immutable, _regular, decode_json, file_identity, verify_driver_runtime


RESULT_VERSION = contracts.WORKER_RESULT_VERSION


def _require(condition, code):
    if not condition:
        raise ValueError("esm_gene_embedding_" + code)


def _read_pin(pin):
    with _regular(Path(pin["path"])) as stream:
        raw = stream.read(pin["size_bytes"] + 1)
    _require(len(raw) == pin["size_bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"], "file_bytes_conflict")
    return raw


def _encoded(value):
    """Retain nonfinite native values as explicit literals in finite JSON."""
    if isinstance(value, list):
        return [_encoded(item) for item in value]
    if math.isnan(value): return "NaN"
    if math.isinf(value): return "Infinity" if value > 0 else "-Infinity"
    return value


def _nonfinite(vector):
    return any(type(item) is str for item in vector)


def _base(request, supplied):
    selected = {iso["record_ordinal"] for gene in request["genes"] for iso in gene["isoforms"]}
    proteins = []
    for row in supplied["records"]:
        status, issues = "failed", ["model_unavailable"]
        if row["record_ordinal"] not in selected:
            status, issues = "unrequested", list(row["issues"])
        elif row["status"] != "available":
            status, issues = "invalid", list(row["issues"])
        elif len(row["sequence"]) > request["parameters"]["max_sequence_length"]:
            status, issues = "length_filtered", ["maximum_sequence_length_exceeded"]
        proteins.append(dict(protein_ordinal=row["record_ordinal"], raw_header=row["raw_header"],
            sequence=row["sequence"], status=status, model_token_count=None, residue_vectors=None,
            mean_vector=None, issues=issues))
    return dict(version=contracts.DOCUMENT_VERSION, input=supplied, genes=deepcopy(request["genes"]),
        parameters=deepcopy(request["parameters"]), deployment=deepcopy(request["deployment"]),
        observed_model=None, proteins=proteins, isoforms=[], gene_rows=[], execution=dict(
            state="failed", model_load="failed", attempts=1, model_forward_calls=0,
            runtime_verified=False, failure=None))


def _isoforms(document):
    rows = []
    for gene_ordinal, gene in enumerate(document["genes"]):
        for ordinal_within_gene, assignment in enumerate(gene["isoforms"]):
            index = assignment["record_ordinal"]
            protein = document["proteins"][index] if index < len(document["proteins"]) else None
            state = protein["status"] if protein is not None and protein["status"] in ("available", "nonfinite") else "unavailable"
            rows.append(dict(isoform_ordinal=len(rows), gene_ordinal=gene_ordinal,
                ordinal_within_gene=ordinal_within_gene, **assignment, status=state,
                mean_vector=None if protein is None else protein["mean_vector"]))
    document["isoforms"] = rows


def _genes(document, tensors, torch=None):
    rows = []
    for gene_ordinal, gene in enumerate(document["genes"]):
        members = [r for r in document["isoforms"] if r["gene_ordinal"] == gene_ordinal]
        successful = [r for r in members if r["status"] in ("available", "nonfinite")]
        vector, status = None, "unavailable"
        if successful:
            # Repeated original assignments remain repeated contributors. The
            # source's second mean gives each successful isoform equal weight.
            try:
                mean = torch.stack([tensors["proteins"][r["record_ordinal"]]["protein_mean"]
                    for r in successful], dim=0).mean(dim=0)
                tensors["genes"][gene_ordinal] = mean
                vector = _encoded(mean.tolist())
                status = "nonfinite" if _nonfinite(vector) else "available"
            except Exception as error:
                status = "failed"
                document["execution"]["failure"] = dict(code="native_gene_pooling_failed", exception_type=type(error).__name__)
        rows.append(dict(gene_ordinal=gene_ordinal, gene_id=gene["gene_id"],
            isoform_ordinals=[r["isoform_ordinal"] for r in members],
            successful_isoform_ordinals=[r["isoform_ordinal"] for r in successful], mean_vector=vector, status=status))
    document["gene_rows"] = rows


def _infer(document, model, alphabet, torch, tensors, progress):
    """Fixed batches in original protein occurrence order; no retries."""
    allowed = set(alphabet.standard_toks)
    candidates = []
    for protein in document["proteins"]:
        if protein["status"] != "failed":
            continue
        sequence = protein["sequence"]
        if any(symbol not in allowed for symbol in sequence):
            protein.update(status="invalid", issues=["unsupported_model_token_preserved_without_normalization"])
        else:
            candidates.append(protein["protein_ordinal"])
    converter = alphabet.get_batch_converter()
    batch_size, layer = document["parameters"]["batch_size"], document["parameters"]["layer"]
    for start in range(0, len(candidates), batch_size):
        ordinals = candidates[start:start + batch_size]
        raw_batch = [("protein_occurrence:" + str(i), document["proteins"][i]["sequence"]) for i in ordinals]
        try:
            labels, strings, tokens = converter(raw_batch)
            _require(labels == [r[0] for r in raw_batch] and strings == [r[1] for r in raw_batch], "batch_identity_conflict")
            lengths = (tokens != alphabet.padding_idx).sum(1)
            _require(all(int(lengths[j].item()) == len(sequence) + 2 for j, (_, sequence) in enumerate(raw_batch)),
                "batch_token_population_conflict")
            document["execution"]["model_forward_calls"] += 1
            with torch.no_grad():
                result = model(tokens.to("cpu"), repr_layers=[layer], return_contacts=False)
            representations = result["representations"][layer]
            _require(representations.ndim == 3 and representations.shape[0] == len(ordinals)
                and representations.shape[2] == 320, "representation_shape_conflict")
            for j, index in enumerate(ordinals):
                length = len(raw_batch[j][1])
                # The two selected means are the actual native Torch means.
                # BOS, EOS and batch padding never enter the token population.
                residues = representations[j, 1:length + 1].detach().cpu().clone()
                mean = residues.mean(0)
                _require(tuple(residues.shape) == (length, 320) and tuple(mean.shape) == (320,),
                    "representation_shape_conflict")
                encoded_rows, encoded_mean = _encoded(residues.tolist()), _encoded(mean.tolist())
                status = "nonfinite" if _nonfinite(encoded_mean) or any(_nonfinite(r) for r in encoded_rows) else "available"
                tensors["proteins"][index] = dict(residue_representations=residues, protein_mean=mean)
                document["proteins"][index].update(status=status, model_token_count=length,
                    residue_vectors=encoded_rows, mean_vector=encoded_mean, issues=[])
        except Exception as error:
            for index in ordinals:
                # Completed per-protein tensors are retained if a later member
                # fails; a batch error never invents a vector or retries work.
                if document["proteins"][index]["mean_vector"] is None:
                    document["proteins"][index].update(status="failed", issues=["native_batch_failed"])
            document["execution"]["failure"] = dict(code="native_batch_failed", exception_type=type(error).__name__)
        progress(ordinals)


def _declaration(path, directory, file_format):
    return dict(path=path.relative_to(directory).as_posix(), format=file_format, **file_identity(path))


def run_esm_gene_embedding_request(request, *, output_directory):
    """Create one fresh owned result directory and perform one offline attempt.

    The caller authenticates File custody before this Store-free boundary. The
    worker additionally verifies the actual input bytes and configured runtime,
    source, packages and checkpoint bytes. Model files are never downloaded.
    """
    request = contracts.validate_esm_worker_request(request)
    directory = Path(output_directory)
    _require(directory.is_absolute() and directory.is_dir(), "owned_parent_directory_required")
    work = directory / "esm-gene-embeddings"
    work.mkdir()
    _immutable(work / "request.json", request)
    input_file = request["input"]["file"]
    raw = _read_pin(dict(path=request["input"]["path"], sha256=input_file["sha256"], size_bytes=input_file["size_bytes"]))
    supplied = contracts.read_esm_protein_fasta(raw, file=input_file, source_ref=request["input"]["source_ref"])
    _immutable(work / "input.json", supplied)
    document = _base(request, supplied)
    tensors = dict(model_name=contracts.MODEL, layer=6, proteins={}, genes={})
    progress_index = 0

    def progress(ordinals=()):
        nonlocal progress_index
        # Each batch's native JSON cells are sealed once, rather than copying
        # the full growing residue matrix into every checkpoint.
        _immutable(work / ("progress-" + str(progress_index) + ".json"), dict(
            execution=document["execution"], observed_model=document["observed_model"],
            protein_states=[{k:p[k] for k in ("protein_ordinal","status","model_token_count","issues")}
                for p in document["proteins"]], completed_proteins=[document["proteins"][i] for i in ordinals]))
        progress_index += 1

    torch = None
    try:
        verify_driver_runtime(request["deployment"]["driver"])
        _require(Path(__file__) == Path(request["deployment"]["driver"]["module_root"])
            / "gene_annotation_episode" / "esm_gene_embedding_worker.py", "selected_worker_module_conflict")
        document["execution"]["runtime_verified"] = True
        import torch
        import esm
        deployment = request["deployment"]
        torch.set_num_threads(deployment["torch_threads"])
        model_bytes, regression_bytes = (_read_pin(deployment[key]) for key in ("checkpoint", "regression_checkpoint"))
        # Explicitly selected trusted physical checkpoints, never a hub lookup.
        model_data = torch.load(io.BytesIO(model_bytes), map_location="cpu", weights_only=False)
        regression_data = torch.load(io.BytesIO(regression_bytes), map_location="cpu", weights_only=False)
        model, alphabet = esm.pretrained.load_model_and_alphabet_core(contracts.MODEL, model_data, regression_data)
        _require(model.num_layers == 6 and model.embed_dim == 320 and alphabet.prepend_bos is True
            and alphabet.append_eos is True and not alphabet.use_msa, "observed_model_profile_conflict")
        model.eval(); model = model.to("cpu")
        document["observed_model"] = dict(model_name=contracts.MODEL, layer_count=model.num_layers,
            embedding_dimension=model.embed_dim, torch_version=str(torch.__version__), esm_version=str(esm.__version__),
            parameter_dtype=str(next(model.parameters()).dtype), device="cpu", torch_threads=torch.get_num_threads(),
            alphabet_tokens=list(alphabet.all_toks),
            prepend_bos=alphabet.prepend_bos, append_eos=alphabet.append_eos)
        document["execution"]["model_load"] = "completed"
        progress()
        _infer(document, model, alphabet, torch, tensors, progress)
    except Exception as error:
        document["execution"]["failure"] = dict(code="native_model_attempt_failed", exception_type=type(error).__name__)
    _isoforms(document)
    _genes(document, tensors, torch)
    if document["execution"]["model_load"] == "completed":
        document["execution"]["state"] = "partial" if document["execution"]["failure"] is not None or any(
            p["status"] in ("failed", "invalid") for p in document["proteins"]) else "completed"
        try:
            verify_driver_runtime(request["deployment"]["driver"])
            for key in ("checkpoint", "regression_checkpoint"):
                _require(file_identity(request["deployment"][key]["path"]) ==
                    {k:request["deployment"][key][k] for k in ("sha256", "size_bytes")}, "checkpoint_changed")
        except Exception as error:
            document["execution"].update(state="partial", runtime_verified=False,
                failure=dict(code="runtime_postcheck_failed", exception_type=type(error).__name__))
    document = contracts.validate_esm_embedding_document(document)
    vector_file = None
    if tensors["proteins"]:
        native = work / "vectors.pt"
        try:
            torch.save(tensors, native)
            vector_file = _declaration(native, directory, "pt")
        except Exception as error:
            document["execution"].update(state="partial",
                failure=dict(code="native_vector_artifact_write_failed", exception_type=type(error).__name__))
            document = contracts.validate_esm_embedding_document(document)
    result_path = work / "embeddings.json"
    _immutable(result_path, document)
    result = dict(version=RESULT_VERSION, request_sha256=digest(request),
        input_document_file=_declaration(work / "input.json", directory, "json"),
        result_document_file=_declaration(result_path, directory, "json"), vector_file=vector_file,
        execution=document["execution"])
    result = contracts.validate_esm_worker_result(result, request=request, document=document)
    _immutable(work / "result.json", result)
    return result


def main(argv=None):
    """Existing ordinary worker envelope: request file, result file."""
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    _require(len(argv) == 2, "worker_cli_arguments_required")
    request_path, result_path = map(Path, argv)
    _require(request_path.is_absolute() and result_path.is_absolute()
        and request_path.parent == result_path.parent, "worker_cli_directory_conflict")
    with _regular(request_path) as stream:
        envelope = decode_json(stream.read())
    _require(type(envelope) is dict and set(envelope) == {"operation", "arguments"}
        and envelope["operation"] == "esm_gene_embedding" and type(envelope["arguments"]) is dict
        and set(envelope["arguments"]) == {"request"}, "worker_envelope_conflict")
    result = run_esm_gene_embedding_request(envelope["arguments"]["request"], output_directory=result_path.parent)
    _immutable(result_path, result)
    return 0


__all__ = ["RESULT_VERSION", "run_esm_gene_embedding_request", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
