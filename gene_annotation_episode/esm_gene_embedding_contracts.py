"""Supplied-protein occurrences and literal ESM2 embedding result contracts.

This module performs no acquisition, model inference, vector arithmetic or
similarity scoring. The native worker alone delegates inference and the two
explicit means to ESM/PyTorch. Identifiers are caller/source labels, not inferred
gene correspondence or functional confidence.
"""
from copy import deepcopy
import hashlib
import json
import re

from .native_atac_differential_contracts import driver_runtime_schema, validate_driver_runtime
from .execution_contracts import digest


TOOL = "generate_gene_embeddings_with_ESM_models"
FACT_SOURCE = "esm_gene_embedding_outcomes"
MODEL = "esm2_t6_8M_UR50D"
INPUT_VERSION = "esm_supplied_proteins_v1"
REQUEST_VERSION = "esm_gene_embedding_request_v1"
DOCUMENT_VERSION = "esm_gene_embeddings_v1"
SELECTION_VERSION = "esm_gene_embedding_selection_v1"
VALUE_VERSION = "esm_gene_embedding_values_v1"
SOURCE_VERSION = "esm_gene_embedding_result_v1"
WORKER_RESULT_VERSION = "esm_gene_embedding_worker_result_v1"
PROTEIN_POOLING = "mean_model_tokens_excluding_bos_eos_padding"
GENE_POOLING = "equal_mean_successful_isoform_occurrences"
_SOURCE = r"^source_[0-9a-f]{24,64}$"
_NONFINITE = ("NaN", "Infinity", "-Infinity")


def _require(condition, code):
    if not condition:
        raise ValueError("esm_gene_embedding_" + code)


def _copy(value):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("esm_gene_embedding_finite_json_required") from error


def _obj(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _array(item, **extra):
    return dict(type="array", items=item, **extra)


def _nullable(schema):
    return dict(anyOf=[schema, dict(type="null")])


_INDEX = dict(type="integer", minimum=0)
_TEXT = dict(type="string", minLength=1)
_SOURCE_REF = dict(type="string", pattern=_SOURCE)
_FILE = _obj(dict(artifact_ref=dict(type="string", pattern=r"^artifact_[0-9a-f]{64}$"),
    sha256=dict(type="string", pattern=r"^[0-9a-f]{64}$"), size_bytes=_INDEX, format=dict(const="fasta")))
_PIN = _obj(dict(path=_TEXT, sha256=dict(type="string", pattern=r"^[0-9a-f]{64}$"), size_bytes=_INDEX))
_ASSIGNMENT = _obj(dict(record_ordinal=_INDEX, protein_id=_TEXT, isoform_id=_TEXT))
_GENE = _obj(dict(gene_id=_TEXT, isoforms=_array(_ASSIGNMENT)))
_PARAMETERS = _obj(dict(layer=dict(const=6), batch_size=dict(type="integer", minimum=1),
    max_sequence_length=dict(type="integer", minimum=1), protein_pooling=dict(const=PROTEIN_POOLING),
    gene_pooling=dict(const=GENE_POOLING)))
_DEPLOYMENT = _obj(dict(version=dict(const="esm_gene_embedding_deployment_v1"), model_name=dict(const=MODEL),
    layer_count=dict(const=6), embedding_dimension=dict(const=320), device=dict(const="cpu"), torch_threads=dict(const=1),
    checkpoint=_PIN, regression_checkpoint=_PIN, driver=driver_runtime_schema()))
_GROUP_SELECTION = _obj(dict(row_ordinals=_nullable(_array(_INDEX, uniqueItems=True)),
    component_indices=_nullable(_array(_INDEX, uniqueItems=True)), offset=_INDEX, limit=_INDEX))
_SELECTION = _obj(dict(version=dict(const=SELECTION_VERSION),
    residues=_GROUP_SELECTION, proteins=_GROUP_SELECTION, isoforms=_GROUP_SELECTION, genes=_GROUP_SELECTION))
_SEGMENT = _obj(dict(byte_start=_INDEX, byte_end=_INDEX, text=dict(type="string")))
_INPUT_ROW = _obj(dict(record_ordinal=_INDEX, raw_header=dict(type="string"), sequence=dict(type="string"),
    header_byte_start=_INDEX, header_byte_end=_INDEX, sequence_segments=_array(_SEGMENT),
    status=dict(enum=["available", "malformed"]), issues=_array(_TEXT, uniqueItems=True)))
_INPUT = _obj(dict(version=dict(const=INPUT_VERSION), file=_FILE, source_ref=_nullable(_SOURCE_REF),
    raw_hex=dict(type="string", pattern=r"^(?:[0-9a-f]{2})*$"), catalog_complete=dict(type="boolean"),
    record_count=_nullable(_INDEX), records=_array(_INPUT_ROW), issues=_array(_TEXT, uniqueItems=True)))
_NUMBER = dict(anyOf=[dict(type="number"), dict(enum=list(_NONFINITE))])
_VECTOR = _array(_NUMBER, minItems=320, maxItems=320)
_PROTEIN = _obj(dict(protein_ordinal=_INDEX, raw_header=dict(type="string"), sequence=dict(type="string"),
    status=dict(enum=["unrequested", "length_filtered", "invalid", "failed", "available", "nonfinite"]),
    model_token_count=_nullable(_INDEX), residue_vectors=_nullable(_array(_VECTOR)),
    mean_vector=_nullable(_VECTOR), issues=_array(_TEXT, uniqueItems=True)))
_ISOFORM = _obj(dict(isoform_ordinal=_INDEX, gene_ordinal=_INDEX, ordinal_within_gene=_INDEX,
    record_ordinal=_INDEX, protein_id=_TEXT, isoform_id=_TEXT,
    status=dict(enum=["unavailable", "available", "nonfinite"]), mean_vector=_nullable(_VECTOR)))
_GENE_ROW = _obj(dict(gene_ordinal=_INDEX, gene_id=_TEXT, isoform_ordinals=_array(_INDEX),
    successful_isoform_ordinals=_array(_INDEX), mean_vector=_nullable(_VECTOR),
    status=dict(enum=["unavailable", "failed", "available", "nonfinite"])))
_OBSERVED = _obj(dict(model_name=dict(const=MODEL), layer_count=dict(const=6), embedding_dimension=dict(const=320),
    torch_version=_TEXT, esm_version=_TEXT, parameter_dtype=_TEXT, device=dict(const="cpu"), torch_threads=dict(const=1),
    alphabet_tokens=_array(_TEXT, uniqueItems=True), prepend_bos=dict(const=True), append_eos=dict(const=True)))
_EXECUTION = _obj(dict(state=dict(enum=["completed", "partial", "failed"]),
    model_load=dict(enum=["completed", "failed"]), attempts=dict(const=1), model_forward_calls=_INDEX,
    runtime_verified=dict(type="boolean"), failure=_nullable(_obj(dict(code=_TEXT, exception_type=_TEXT)))))
_DOCUMENT = _obj(dict(version=dict(const=DOCUMENT_VERSION), input=_INPUT, genes=_array(_GENE),
    parameters=_PARAMETERS, deployment=_DEPLOYMENT, observed_model=_nullable(_OBSERVED),
    proteins=_array(_PROTEIN), isoforms=_array(_ISOFORM), gene_rows=_array(_GENE_ROW), execution=_EXECUTION))
_REQUEST = _obj(dict(version=dict(const=REQUEST_VERSION),
    input=_obj(dict(path=_TEXT, file=_FILE, source_ref=_nullable(_SOURCE_REF))),
    genes=_array(_GENE), parameters=_PARAMETERS, deployment=_DEPLOYMENT))


def _output_file(name, file_format):
    return _obj(dict(path=dict(const="esm-gene-embeddings/"+name), format=dict(const=file_format),
        sha256=dict(type="string", pattern=r"^[0-9a-f]{64}$"), size_bytes=_INDEX))


_WORKER_RESULT = _obj(dict(version=dict(const=WORKER_RESULT_VERSION),
    request_sha256=dict(type="string",pattern=r"^[0-9a-f]{64}$"),
    input_document_file=_output_file("input.json","json"), result_document_file=_output_file("embeddings.json","json"),
    vector_file=_nullable(_output_file("vectors.pt","pt")), execution=_EXECUTION))
_ARGUMENTS = dict(oneOf=[
    _obj(dict(mode=dict(const="embed"), input=_obj(dict(reference=_TEXT, namespace=dict(enum=["source", "artifact"]))),
        genes=_array(_GENE), model_name=dict(const=MODEL), parameters=_PARAMETERS, selection=_SELECTION)),
    _obj(dict(mode=dict(const="read_stored"), result_ref=_SOURCE_REF, selection=_SELECTION)),
])
_COMPONENTS = _array(_INDEX, uniqueItems=True)
_CELLS = _nullable(_array(_NUMBER, maxItems=320))
_PUBLIC_RESIDUE = _obj(dict(row_ordinal=_INDEX, protein_ordinal=_INDEX, token_ordinal_0based=_INDEX,
    symbol=dict(type="string", minLength=1, maxLength=1), status=dict(enum=["available", "nonfinite"]),
    component_indices=_COMPONENTS, values=_CELLS))
_PUBLIC_PROTEIN = _obj(dict(row_ordinal=_INDEX, protein_ordinal=_INDEX, raw_header=dict(type="string"),
    sequence=dict(type="string"), status=_PROTEIN["properties"]["status"], model_token_count=_nullable(_INDEX),
    issues=_array(_TEXT, uniqueItems=True), component_indices=_COMPONENTS, values=_CELLS))
_PUBLIC_ISOFORM = _obj(dict(row_ordinal=_INDEX, **{k:v for k,v in _ISOFORM["properties"].items() if k != "mean_vector"},
    component_indices=_COMPONENTS, values=_CELLS))
_PUBLIC_GENE = _obj(dict(row_ordinal=_INDEX, **{k:v for k,v in _GENE_ROW["properties"].items() if k != "mean_vector"},
    component_indices=_COMPONENTS, values=_CELLS))
_GENE_POPULATION = _obj(dict(gene_ordinal=_INDEX, gene_id=_TEXT, supplied_isoform_count=_INDEX,
    successful_isoform_ordinals=_array(_INDEX), status=_GENE_ROW["properties"]["status"]))
_CONTEXT = _obj(dict(model_name=dict(const=MODEL),
    selected_checkpoint_sha256=dict(type="string", pattern=r"^[0-9a-f]{64}$"),
    selected_regression_checkpoint_sha256=dict(type="string", pattern=r"^[0-9a-f]{64}$"),
    parameters=_PARAMETERS, observed_model=_nullable(_OBSERVED),
    execution=_EXECUTION, input_file=_FILE, input_source_ref=_nullable(_SOURCE_REF), input_catalog_complete=dict(type="boolean"),
    input_record_count=_nullable(_INDEX), input_issues=_array(_TEXT, uniqueItems=True), supplied_gene_occurrence_count=_INDEX,
    supplied_isoform_occurrence_count=_INDEX, requested_protein_ordinals=_array(_INDEX, uniqueItems=True),
    successful_protein_ordinals=_array(_INDEX, uniqueItems=True), length_filtered_protein_ordinals=_array(_INDEX, uniqueItems=True),
    failed_protein_ordinals=_array(_INDEX, uniqueItems=True), unavailable_requested_protein_ordinals=_array(_INDEX, uniqueItems=True),
    gene_populations=_array(_GENE_POPULATION),
    quantity_meaning=dict(const="dimensionless_model_representation_not_function_probability"),
    protein_denominator=dict(const="actual_model_tokens_excluding_bos_eos_padding"),
    gene_denominator=dict(const="successful_isoform_occurrences_only_equal_weight"),
    biological_isoform_population_completeness=dict(const="unknown")))


def _public_group(row):
    return _obj(dict(population_count=_INDEX, selected_count=_INDEX, returned_count=_INDEX, rows=_array(row)))


_VALUE = _obj(dict(version=dict(const=VALUE_VERSION), selection=_SELECTION, context=_CONTEXT,
    residues=_public_group(_PUBLIC_RESIDUE), proteins=_public_group(_PUBLIC_PROTEIN),
    isoforms=_public_group(_PUBLIC_ISOFORM), genes=_public_group(_PUBLIC_GENE)))
_RETURN = _obj(dict(source_ref={**_SOURCE_REF, "format":"reference", "x-reference-namespace":"source"},
    **_VALUE["properties"]))


def _check(value, schema):
    from jsonschema import Draft202012Validator, ValidationError, validators
    value = _copy(value)
    strict = validators.extend(Draft202012Validator, type_checker=
        Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _checker, item: type(item) is int))
    try:
        strict(schema).validate(value)
    except ValidationError as error:
        raise ValueError("esm_gene_embedding_schema_invalid") from error
    return value


def _file(value):
    _require(value["artifact_ref"] == "artifact_" + value["sha256"], "file_identity_conflict")


def validate_esm_deployment(value):
    value = _check(value, _DEPLOYMENT)
    validate_driver_runtime(value["driver"], required_modules=("gene_annotation_episode.esm_gene_embedding_worker",
        "gene_annotation_episode.esm_gene_embedding_contracts"),
        required_dependencies=("torch", "fair-esm"))
    for pin in (value["checkpoint"], value["regression_checkpoint"]):
        _require(pin["path"].startswith("/") and "/../" not in pin["path"], "checkpoint_path_conflict")
    expected = value["checkpoint"]["path"]
    _require(expected.endswith("/" + MODEL + ".pt") and value["regression_checkpoint"]["path"]
        == expected[:-3] + "-contact-regression.pt", "checkpoint_pair_conflict")
    return value


def validate_esm_selection(value):
    return _check(value, _SELECTION)


def validate_esm_embedding_arguments(value):
    value = _check(value, _ARGUMENTS)
    if value["mode"] == "embed":
        ref, namespace = value["input"]["reference"], value["input"]["namespace"]
        _require(re.fullmatch(_SOURCE if namespace == "source" else r"artifact_[0-9a-f]{64}", ref) is not None,
            "input_reference_conflict")
    return value


def _physical_fasta_lines(content):
    offset, result = 0, []
    for raw in content.splitlines(keepends=True):
        body = raw.rstrip(b"\r\n")
        result.append((offset, offset + len(body), body.decode("utf-8")))
        offset += len(raw)
    return result


def read_esm_protein_fasta(content, *, file, source_ref=None):
    """Read literal supplied occurrences; preserve raw bytes, case and headers.

    Sequence-line edge whitespace follows FAIR's FastaBatchedDataset reader.
    No uppercase conversion, ID extraction, duplicate-label collapse or network
    lookup occurs. Invalid header catalogs remain explicitly incomplete.
    """
    _require(type(content) is bytes, "input_bytes_required")
    file = _check(file, _FILE); _file(file)
    _require(len(content) == file["size_bytes"] and hashlib.sha256(content).hexdigest() == file["sha256"],
        "input_bytes_identity_conflict")
    result = dict(version=INPUT_VERSION, file=file, source_ref=source_ref, raw_hex=content.hex(),
        catalog_complete=True, record_count=0, records=[], issues=[])
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        result.update(catalog_complete=False, record_count=None, issues=["invalid_utf8"])
        return validate_esm_input_document(result)
    current = None
    for offset, end, text in _physical_fasta_lines(content):
        if text.startswith(">"):
            current = dict(record_ordinal=len(result["records"]), raw_header=text[1:], sequence="",
                header_byte_start=offset, header_byte_end=end, sequence_segments=[],
                status="available", issues=[])
            result["records"].append(current)
        elif current is None:
            if text.strip():
                result["issues"].append("sequence_before_header")
        else:
            current["sequence_segments"].append(dict(byte_start=offset, byte_end=end, text=text))
            current["sequence"] += text.strip()
    for row in result["records"]:
        if not row["raw_header"].strip(): row["issues"].append("empty_header")
        if not row["sequence"]: row["issues"].append("empty_sequence")
        if row["issues"]: row["status"] = "malformed"
    result["issues"] = list(dict.fromkeys(result["issues"]))
    result["record_count"] = len(result["records"])
    return validate_esm_input_document(result)


def validate_esm_input_document(value):
    value = _check(value, _INPUT); _file(value["file"])
    raw = bytes.fromhex(value["raw_hex"])
    _require(len(raw) == value["file"]["size_bytes"] and hashlib.sha256(raw).hexdigest() == value["file"]["sha256"],
        "input_bytes_identity_conflict")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        _require(value["catalog_complete"] is False and value["records"] == [] and value["issues"] == ["invalid_utf8"],
            "input_decode_state_conflict")
    else:
        _require(value["catalog_complete"] is True and set(value["issues"]) <= {"sequence_before_header"},
            "input_decode_state_conflict")
        lines = _physical_fasta_lines(raw)
        starts = [start for start, end, text in lines if text.startswith(">")]
        _require(starts == [r["header_byte_start"] for r in value["records"]], "input_header_population_conflict")
        prefix = any(text.strip() for start, end, text in lines if not starts or start < starts[0])
        _require(value["issues"] == (["sequence_before_header"] if prefix else []), "input_prefix_state_conflict")
        for ordinal, row in enumerate(value["records"]):
            bound = starts[ordinal+1] if ordinal+1 < len(starts) else len(raw)+1
            expected = [dict(byte_start=start, byte_end=end, text=text) for start,end,text in lines
                if row["header_byte_start"] < start < bound]
            _require(row["sequence_segments"] == expected, "input_sequence_extent_conflict")
    _require(value["record_count"] == (len(value["records"]) if value["catalog_complete"] else None),
        "input_population_conflict")
    previous = -1
    for ordinal, row in enumerate(value["records"]):
        start, end = row["header_byte_start"], row["header_byte_end"]
        _require(row["record_ordinal"] == ordinal and previous < start < end <= len(raw)
            and raw[start:end] == (">" + row["raw_header"]).encode("utf-8"), "header_locator_conflict")
        previous = end
        for segment in row["sequence_segments"]:
            start, end = segment["byte_start"], segment["byte_end"]
            _require(previous <= start <= end <= len(raw) and raw[start:end] == segment["text"].encode("utf-8"),
                "sequence_locator_conflict")
            previous = end
        _require(row["sequence"] == "".join(s["text"].strip() for s in row["sequence_segments"]), "sequence_join_conflict")
        expected = ([] if row["raw_header"].strip() else ["empty_header"]) + ([] if row["sequence"] else ["empty_sequence"])
        _require(row["issues"] == expected and row["status"] == ("malformed" if expected else "available"),
            "input_status_conflict")
    return value


def validate_esm_worker_request(value):
    value = _check(value, _REQUEST); _file(value["input"]["file"])
    validate_esm_deployment(value["deployment"])
    _require(value["input"]["path"].startswith("/") and "/../" not in value["input"]["path"], "input_path_conflict")
    return value


def validate_esm_worker_result(value, *, request=None, document=None):
    """Metadata joins only; the host authenticates actual declared File bytes."""
    value = _check(value, _WORKER_RESULT)
    if request is not None:
        request = validate_esm_worker_request(request)
        _require(value["request_sha256"] == digest(request), "worker_request_digest_conflict")
    if document is not None:
        document = validate_esm_embedding_document(document)
        _require(value["execution"] == document["execution"], "worker_execution_conflict")
        if request is not None:
            _require(all(document[k] == request[k] for k in ("genes","parameters","deployment"))
                and all(document["input"][k] == request["input"][k] for k in ("file","source_ref")), "worker_input_conflict")
        successful = any(p["mean_vector"] is not None for p in document["proteins"])
        expected_vector = successful and (document["execution"]["failure"] or {}).get("code") != "native_vector_artifact_write_failed"
        _require((value["vector_file"] is not None) == expected_vector, "worker_vector_capture_conflict")
    return value


def _nonfinite(vector):
    return vector is not None and any(type(v) is str for v in vector)


def validate_esm_embedding_document(value):
    """Validate shape/membership, never re-infer or recompute a vector mean."""
    value = _check(value, _DOCUMENT)
    validate_esm_input_document(value["input"]); validate_esm_deployment(value["deployment"])
    records, proteins = value["input"]["records"], value["proteins"]
    _require(len(records) == len(proteins), "protein_population_conflict")
    requested = {iso["record_ordinal"] for gene in value["genes"] for iso in gene["isoforms"]}
    for ordinal, (record, protein) in enumerate(zip(records, proteins)):
        _require(protein["protein_ordinal"] == ordinal and all(protein[k] == record[k] for k in ("raw_header", "sequence")),
            "protein_identity_conflict")
        status, vector, residues = protein["status"], protein["mean_vector"], protein["residue_vectors"]
        if status in ("available", "nonfinite"):
            _require(ordinal in requested and residues is not None and vector is not None and type(protein["model_token_count"]) is int
                and protein["model_token_count"] == len(residues) == len(record["sequence"]) > 0
                and not protein["issues"] and record["status"] == "available", "protein_values_conflict")
            nonfinite = _nonfinite(vector) or any(_nonfinite(v) for v in residues)
            _require((status == "nonfinite") == nonfinite, "nonfinite_state_conflict")
        else:
            _require(vector is None and residues is None and protein["model_token_count"] is None, "unavailable_vector_conflict")
            _require((status == "unrequested") == (ordinal not in requested), "requested_population_conflict")
            if status == "length_filtered":
                _require(len(record["sequence"]) > value["parameters"]["max_sequence_length"], "length_filter_conflict")
    expected_isoforms = []
    for gene_ordinal, gene in enumerate(value["genes"]):
        for within, supplied in enumerate(gene["isoforms"]):
            record_index = supplied["record_ordinal"]
            protein = proteins[record_index] if record_index < len(proteins) else None
            status = protein["status"] if protein is not None and protein["status"] in ("available", "nonfinite") else "unavailable"
            expected_isoforms.append(dict(isoform_ordinal=len(expected_isoforms), gene_ordinal=gene_ordinal,
                ordinal_within_gene=within, **supplied, status=status,
                mean_vector=protein["mean_vector"] if protein is not None else None))
    _require(value["isoforms"] == expected_isoforms, "isoform_membership_conflict")
    _require(len(value["gene_rows"]) == len(value["genes"]), "gene_population_conflict")
    for ordinal, (supplied, row) in enumerate(zip(value["genes"], value["gene_rows"])):
        members = [i["isoform_ordinal"] for i in expected_isoforms if i["gene_ordinal"] == ordinal]
        successful = [i for i in members if expected_isoforms[i]["status"] in ("available", "nonfinite")]
        _require(row["gene_ordinal"] == ordinal and row["gene_id"] == supplied["gene_id"]
            and row["isoform_ordinals"] == members and row["successful_isoform_ordinals"] == successful,
            "gene_membership_conflict")
        if row["status"] == "failed":
            _require(successful and row["mean_vector"] is None and value["execution"]["failure"] is not None,
                "gene_status_conflict")
        else:
            _require((row["mean_vector"] is None) == (not successful) and row["status"] ==
                ("unavailable" if not successful else "nonfinite" if _nonfinite(row["mean_vector"]) else "available"),
                "gene_status_conflict")
    execution = value["execution"]
    _require((value["observed_model"] is None) == (execution["model_load"] == "failed"), "model_observation_conflict")
    if execution["model_load"] == "failed":
        _require(execution["model_forward_calls"] == 0 and execution["state"] == "failed", "model_failure_conflict")
    if execution["state"] == "completed":
        _require(execution["runtime_verified"] is True and execution["failure"] is None
            and all(p["status"] in ("available", "nonfinite", "unrequested", "length_filtered") for p in proteins),
            "execution_state_conflict")
    return value


def _select(rows, selection):
    ordinals = list(range(len(rows))) if selection["row_ordinals"] is None else selection["row_ordinals"]
    _require(all(i < len(rows) for i in ordinals), "selected_row_unavailable")
    selected = ordinals[selection["offset"]:selection["offset"] + selection["limit"]]
    components = list(range(320)) if selection["component_indices"] is None else selection["component_indices"]
    _require(all(i < 320 for i in components), "selected_component_unavailable")
    result = []
    for ordinal in selected:
        row = deepcopy(rows[ordinal]); vector = row.pop("vector")
        result.append(dict(row_ordinal=ordinal, **row, component_indices=components,
            values=None if vector is None else [vector[i] for i in components]))
    return dict(population_count=len(rows), selected_count=len(ordinals), returned_count=len(result), rows=result)


def select_esm_embedding_values(document, selection):
    """Copy selected native/derived cells; pagination never changes pooling."""
    document = validate_esm_embedding_document(document); selection = validate_esm_selection(selection)
    residues, proteins, isoforms, genes = [], [], [], []
    for p in document["proteins"]:
        proteins.append(dict(protein_ordinal=p["protein_ordinal"], raw_header=p["raw_header"], sequence=p["sequence"],
            status=p["status"], model_token_count=p["model_token_count"], issues=p["issues"], vector=p["mean_vector"]))
        for ordinal, vector in enumerate(p["residue_vectors"] or []):
            residues.append(dict(protein_ordinal=p["protein_ordinal"], token_ordinal_0based=ordinal,
                symbol=p["sequence"][ordinal], status="nonfinite" if _nonfinite(vector) else "available", vector=vector))
    for row in document["isoforms"]:
        isoforms.append({**{k:v for k,v in row.items() if k != "mean_vector"}, "vector":row["mean_vector"]})
    for row in document["gene_rows"]:
        genes.append({**{k:v for k,v in row.items() if k != "mean_vector"}, "vector":row["mean_vector"]})
    return dict(version=VALUE_VERSION, selection=selection, context=dict(model_name=MODEL,
        selected_checkpoint_sha256=document["deployment"]["checkpoint"]["sha256"],
        selected_regression_checkpoint_sha256=document["deployment"]["regression_checkpoint"]["sha256"],
        parameters=document["parameters"], observed_model=document["observed_model"], execution=document["execution"],
        input_file=document["input"]["file"], input_source_ref=document["input"]["source_ref"],
        input_catalog_complete=document["input"]["catalog_complete"], input_record_count=document["input"]["record_count"],
        input_issues=document["input"]["issues"], supplied_gene_occurrence_count=len(document["genes"]),
        supplied_isoform_occurrence_count=len(document["isoforms"]),
        requested_protein_ordinals=list(dict.fromkeys(i["record_ordinal"] for i in document["isoforms"])),
        successful_protein_ordinals=[p["protein_ordinal"] for p in document["proteins"] if p["status"] in ("available", "nonfinite")],
        length_filtered_protein_ordinals=[p["protein_ordinal"] for p in document["proteins"] if p["status"] == "length_filtered"],
        failed_protein_ordinals=[p["protein_ordinal"] for p in document["proteins"] if p["status"] in ("invalid", "failed")],
        unavailable_requested_protein_ordinals=list(dict.fromkeys(i["record_ordinal"] for i in document["isoforms"]
            if i["record_ordinal"] >= len(document["proteins"]))),
        gene_populations=[dict(gene_ordinal=r["gene_ordinal"], gene_id=r["gene_id"],
            supplied_isoform_count=len(r["isoform_ordinals"]), successful_isoform_ordinals=r["successful_isoform_ordinals"],
            status=r["status"]) for r in document["gene_rows"]],
        quantity_meaning="dimensionless_model_representation_not_function_probability",
        protein_denominator="actual_model_tokens_excluding_bos_eos_padding",
        gene_denominator="successful_isoform_occurrences_only_equal_weight",
        biological_isoform_population_completeness="unknown"),
        residues=_select(residues, selection["residues"]), proteins=_select(proteins, selection["proteins"]),
        isoforms=_select(isoforms, selection["isoforms"]), genes=_select(genes, selection["genes"]))


def project_esm_embedding_return(document, selection, source_ref):
    _check(source_ref, _SOURCE_REF)
    return validate_esm_embedding_return(dict(source_ref=source_ref, **select_esm_embedding_values(document, selection)))


def validate_esm_embedding_value(value):
    value = _check(value, _VALUE); _file(value["context"]["input_file"])
    context = value["context"]
    _require(value["genes"]["population_count"] == context["supplied_gene_occurrence_count"]
        and value["isoforms"]["population_count"] == context["supplied_isoform_occurrence_count"]
        and (context["input_record_count"] is None or value["proteins"]["population_count"] == context["input_record_count"]),
        "public_group_population_conflict")
    _require(len(context["gene_populations"]) == context["supplied_gene_occurrence_count"], "public_gene_population_conflict")
    _require(sum(r["supplied_isoform_count"] for r in context["gene_populations"])
        == context["supplied_isoform_occurrence_count"], "public_isoform_population_conflict")
    for ordinal, row in enumerate(context["gene_populations"]):
        _require(row["gene_ordinal"] == ordinal and len(row["successful_isoform_ordinals"]) <= row["supplied_isoform_count"],
            "public_gene_population_conflict")
    for kind in ("residues", "proteins", "isoforms", "genes"):
        group, selection = value[kind], value["selection"][kind]
        ordinals = list(range(group["population_count"])) if selection["row_ordinals"] is None else selection["row_ordinals"]
        _require(all(i < group["population_count"] for i in ordinals) and group["selected_count"] == len(ordinals),
            "public_selection_population_conflict")
        returned = ordinals[selection["offset"]:selection["offset"] + selection["limit"]]
        components = list(range(320)) if selection["component_indices"] is None else selection["component_indices"]
        _require(all(i < 320 for i in components) and group["returned_count"] == len(group["rows"])
            and [r["row_ordinal"] for r in group["rows"]] == returned, "public_selection_order_conflict")
        for row in group["rows"]:
            _require(row["component_indices"] == components and
                (row["values"] is None or len(row["values"]) == len(components)), "public_vector_shape_conflict")
            _require((row["values"] is not None) == (row["status"] in ("available", "nonfinite")),
                "public_vector_state_conflict")
            if kind in ("proteins", "isoforms", "genes"):
                identity = {"proteins":"protein_ordinal", "isoforms":"isoform_ordinal", "genes":"gene_ordinal"}[kind]
                _require(row["row_ordinal"] == row[identity], "public_row_identity_conflict")
            if kind == "genes":
                population = context["gene_populations"][row["gene_ordinal"]]
                _require(all(row[k] == population[k] for k in ("gene_id", "successful_isoform_ordinals", "status"))
                    and len(row["isoform_ordinals"]) == population["supplied_isoform_count"], "public_gene_population_conflict")
    return value


def validate_esm_embedding_return(value):
    value = _check(value, _RETURN)
    validate_esm_embedding_value({k:v for k,v in value.items() if k != "source_ref"})
    return value


def esm_gene_embedding_fact_sources():
    return {FACT_SOURCE:dict(type="array", meaning="Selected literal ESM2 representations and explicit occurrence/pooling populations; not function probabilities.",
        report_schema={"type":"array", "items":esm_gene_embedding_schema("Return"), "x-source":FACT_SOURCE})}


def esm_gene_embedding_schema(kind="Arguments"):
    schemas = dict(Arguments=_ARGUMENTS, Selection=_SELECTION, Input=_INPUT, Deployment=_DEPLOYMENT,
        Request=_REQUEST, WorkerResult=_WORKER_RESULT, Document=_DOCUMENT, Value=_VALUE, Return=_RETURN)
    _require(kind in schemas, "schema_kind_required")
    return {"$schema":"https://json-schema.org/draft/2020-12/schema", **deepcopy(schemas[kind])}


__all__ = ["TOOL", "FACT_SOURCE", "MODEL", "INPUT_VERSION", "REQUEST_VERSION", "DOCUMENT_VERSION",
    "VALUE_VERSION", "SOURCE_VERSION", "WORKER_RESULT_VERSION", "SELECTION_VERSION", "PROTEIN_POOLING", "GENE_POOLING",
    "validate_esm_deployment", "validate_esm_selection", "validate_esm_embedding_arguments", "read_esm_protein_fasta",
    "validate_esm_input_document", "validate_esm_worker_request", "validate_esm_worker_result", "validate_esm_embedding_document",
    "select_esm_embedding_values", "project_esm_embedding_return", "validate_esm_embedding_value",
    "validate_esm_embedding_return", "esm_gene_embedding_fact_sources", "esm_gene_embedding_schema"]
