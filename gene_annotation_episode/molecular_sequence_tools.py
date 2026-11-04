"""Explicit ordinary sequence selection and one existing-owner action lease.

No sequence interpretation, native implementation or scientific calculation
lives here. The received-input service authenticates the operand before the
existing sequence owner reads bytes; the existing molecular result owner
retains/projects/publishes and the selected native ports own the one unit.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import threading

from .acquisition import AcquisitionError
from .communication import plain
from .domain import ContractError, REF, identity
from .execution_contracts import canonical, digest
from .genomic_overlap_result_receipts import immutable, read_control, same
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import authenticate_molecular_invocation, MolecularOperationUnpublished
from .molecular_sequence_execution_contracts import absolute_path, _software
from .molecular_sequence_input_contracts import input_record_digest, validate_molecular_sequence_received_subject
from . import molecular_sequence_ordinary as ordinary
from . import molecular_sequence_result_contracts as contracts


ORF_TOOL = contracts.ORDINARY_ORF_TOOL
N_GLYCOSYLATION_TOOL = "find_n_glycosylation_motifs"
O_GLYCOSYLATION_TOOL = "predict_o_glycosylation_hotspots"
PLACEMENT_TOOL = "align_sequences"
BINDING_VERSION = "native_molecular_sequence_binding_v1"
CONFIGURATION_VERSION = "ordinary_molecular_sequence_configuration_v1"
HOST_BINDING_VERSION = "ordinary_orf_host_binding_v1"
HOST_BINDING_FILENAME = "ordinary-orf-host-binding.json"
SUBJECT_KINDS = ("input", "reference", "feature", "product", "read_subject")
_HOST_BINDINGS = {
    ORF_TOOL: (HOST_BINDING_VERSION, HOST_BINDING_FILENAME),
    N_GLYCOSYLATION_TOOL: ("ordinary_n_glycosylation_host_binding_v1",
        "ordinary-n-glycosylation-host-binding.json"),
    O_GLYCOSYLATION_TOOL: ("ordinary_o_glycosylation_host_binding_v1",
        "ordinary-o-glycosylation-host-binding.json"),
    PLACEMENT_TOOL: ("ordinary_primer_placement_host_binding_v1", "ordinary-primer-placement-host-binding.json"),
}


def _require(condition, code):
    if not condition:
        raise ContractError("ordinary_orf_" + code)


def _copy(value):
    return json.loads(canonical(value))


def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)


def _profile(operation):
    return contracts.ordinary_molecular_sequence_profile(operation)


def _code(operation, suffix):
    return _profile(operation)["operand_version"].removesuffix("_sequence_operand_v1") + "_" + suffix


def _configuration_selection(configuration, operation):
    _profile(operation)
    _require(configuration is not None, "configuration_required")
    rows = [row for row in configuration["bindings"] if row["operation"] == operation]
    _require(len(rows) == 1, "configuration_required")
    return rows[0]


def validate_native_molecular_sequence_bindings(bindings):
    """Pure deployment/adapter metadata checks; no installed-software claim."""
    bindings = _copy(bindings)
    _require(type(bindings) is list and bool(bindings), "bindings_required")
    for row in bindings:
        _closed(row, ("version", "operation", "deployment", "software"), "binding_fields_invalid")
        _require(row["version"] == BINDING_VERSION
            and row["operation"] in contracts.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS, "binding_operation_invalid")
        ordinary._deployment(row["operation"], row["deployment"])
        _software(row["software"])
        _require(row["deployment"]["runtime"]["executable"] == row["software"]["python"]
            and row["deployment"]["runtime"]["home"] == row["software"]["python_home"], "binding_runtime_conflict")
    return bindings


def _configuration_row(value):
    value = _copy(value)
    _closed(value, ("operation", "resource_id", "binding_ordinal_0based", "workspace", "binding", "environment"),
        "configuration_row_invalid")
    _require(value["operation"] in contracts.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS and type(value["resource_id"]) is str and value["resource_id"]
        and type(value["binding_ordinal_0based"]) is int and value["binding_ordinal_0based"] >= 0
        and same(value["environment"], ordinary.ENVIRONMENT_SELECTION), "configuration_selection_invalid")
    absolute_path(value["workspace"])
    validate_native_molecular_sequence_bindings([value["binding"]])
    _require(value["binding"]["operation"] == value["operation"], "configuration_selection_invalid")
    return value


def _configuration(value):
    if value is None:
        return None
    value = _copy(value)
    _closed(value, ("version", "policy", "bindings"), "configuration_fields_invalid")
    _require(value["version"] == CONFIGURATION_VERSION and same(value["policy"], ordinary.POLICY)
        and type(value["bindings"]) is list
        and 1 <= len(value["bindings"]) <= len(contracts.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS), "configuration_invalid")
    value["bindings"] = [_configuration_row(row) for row in value["bindings"]]
    _require(len({row["operation"] for row in value["bindings"]}) == len(value["bindings"]),
        "ambiguous_operation_selection")
    return value


def normalize_molecular_sequence_configuration(resources, environments, policy):
    """Compile only explicit setup rows; available bindings imply no selection."""
    _require(isinstance(environments, (list, tuple)), "environment_table_required")
    if not environments:
        return None
    resources, environments = _copy(resources), _copy(environments)
    _require(type(resources) is dict and type(policy) is LocalJobPolicy and policy.to_dict() == ordinary.POLICY,
        "allocation_or_resources_invalid")
    rows, operations = [], set()
    for entry in environments:
        _closed(entry, ("operation", "resource_id", "binding_ordinal_0based", "environment"), "environment_record_invalid")
        operation, name, ordinal = entry["operation"], entry["resource_id"], entry["binding_ordinal_0based"]
        _require(operation in contracts.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS and operation not in operations, "ambiguous_operation_selection")
        operations.add(operation)
        _require(type(name) is str and bool(name) and type(ordinal) is int and ordinal >= 0, "binding_selection_invalid")
        resource = resources.get(name)
        _require(type(resource) is dict and resource.get("kind") == "local"
            and same(resource.get("policy"), ordinary.POLICY), "local_resource_allocation_required")
        bindings = validate_native_molecular_sequence_bindings(resource.get("native_molecular_sequence"))
        _require(ordinal < len(bindings) and bindings[ordinal]["operation"] == operation, "binding_selection_invalid")
        rows.append(_configuration_row(dict(operation=operation, resource_id=name, binding_ordinal_0based=ordinal,
            workspace=resource["workspace"], binding=bindings[ordinal], environment=entry["environment"])))
    return _configuration(dict(version=CONFIGURATION_VERSION, policy=policy.to_dict(), bindings=rows))


def compile_ordinary_molecular_sequence_selection(configuration, *, operation):
    """Map one explicitly configured operation to the existing attempt port."""
    configuration = _configuration(configuration)
    row = _configuration_selection(configuration, operation)
    return dict(resource_id=row["resource_id"], workspace=row["workspace"],
        deployment=deepcopy(row["binding"]["deployment"]), software=deepcopy(row["binding"]["software"]),
        environment=deepcopy(row["environment"]))


def compile_ordinary_orf_selection(configuration):
    """Compatibility selection for the existing ORF operation."""
    return compile_ordinary_molecular_sequence_selection(configuration, operation=ORF_TOOL)


def molecular_sequence_tool_catalog(configuration, *, saved_modes=False):
    _require(type(saved_modes) is bool, "saved_modes_invalid")
    configuration = _configuration(configuration)
    if saved_modes:
        return {operation: _saved_mode_catalog(configuration, operation=operation)[operation]
            for operation in contracts.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS}
    if configuration is None:
        return {}
    result = {}
    for row in configuration["bindings"]:
        result.update(_native_operation_catalog(configuration, row))
    return result


def _native_operation_catalog(configuration, row):
    operation = row["operation"]
    profile = _profile(operation)
    if operation == PLACEMENT_TOOL:
        from .primer_placement_result_contracts import argument_schema
        return {operation: dict(resources="local", invocation_route={"kind": "direct"},
            input_schema=argument_schema(native=True, saved=False),
            description="Locate all retained complete ungapped short-sequence occurrences with at most one literal mismatch on both source orientations.",
            instructions=("Use the explicitly received target and scalar or ordered primer operands without host normalization. "
                "The source uppercases internally and checks forward starts then reverse-complement starts; only A/C/G/T are complemented. "
                "Preserve repeated primer occurrences, opposite palindrome orientations, native ordinals, mismatch triples and mappings. "
                "Mismatch fractions use the full primer width; candidate-window counts are structural populations, not execution attestations. "
                "Retain empty, missing, partial and unsupported noncanonical/empty-primer qualifications. This is not PCR, primer design or confidence. "
                "Return the requested stored fields with their full original operand and population context."),
            configuration=dict(job_limits=deepcopy(configuration["policy"]), bindings=[dict(operation=operation,
                resource_id=row["resource_id"], binding_ordinal_0based=row["binding_ordinal_0based"],
                binding_sha256=digest(row["binding"]), deployment_version=row["binding"]["deployment"]["version"],
                source_sha256=row["binding"]["deployment"]["module"]["sha256"],
                python_version=row["binding"]["software"]["python_version"], environment=deepcopy(row["environment"]))]))}
    rows = contracts.ordinary_molecular_sequence_fact_sources(operation)[profile["fact_source"]]["report_schema"]["items"]["properties"]["selection"]["properties"]["rows"]
    if operation == O_GLYCOSYLATION_TOOL:
        fields = dict(subject_ref=deepcopy(REF), window={"type": "integer"},
            min_st_fraction={"type": "number"}, disallow_proline_next={"type": "boolean"}, rows=deepcopy(rows))
        schema = dict(type="object", properties=fields, required=list(fields), additionalProperties=False)
        schema["$id"] = "urn:gene-annotation:ordinary-o-glycosylation-tool:" + digest(schema)
        return {operation: dict(resources="local", invocation_route={"kind": "direct"}, input_schema=schema,
            description="Find retained O-glycosylation candidate hotspots using the original local S/T-density heuristic on an explicitly received protein sequence.",
            instructions=("Answer the parent's assigned scientific question using its explicitly selected protein sequence, window, min_st_fraction and disallow_proline_next settings. "
                "The original routine uppercases internally and considers each S/T center independently; it has no N-sequon overlap setting. "
                "An integer window below 3 or even is supplied unchanged and the original source uses effective window 7. Preserve supplied, requested and effective parameters separately. "
                "Each window is clipped at the processed sequence ends. Retain the actual S/T numerator and complete clipped-segment symbol denominator, "
                "the native window and expected clipping, and the separate center and window source-coordinate mappings. "
                "Selection compares the full-precision S/T fraction >= min_st_fraction, then the native display rounds to three decimal places; do not threshold the displayed rounded number. "
                "When disallow_proline_next is true, an S/T immediately followed by P is excluded. Finite thresholds outside [0,1] are retained and qualified; the original source does not clamp or reject them. "
                "Native positions and printed window endpoints are one-based; retained processed intervals are zero-based half-open. Preserve original row ordinals, printed residues and fraction tokens. "
                "The native log prints at most its first 100 candidates; native total, printed rows, usable rows and unprinted remainder remain distinct. "
                "Missing, truncated, failed and unavailable data remain distinct from an observed zero. This density is a source heuristic, not measured glycosylation, occupancy, calibrated probability or confidence. "
                "Return only the requested controlled values; no host sequence normalization, alternative scan or inferred unprinted positions is selected. "
                "The configured resource and binding are fixed at setup; this call selects no alternative deployment. Saved reads and recalculation are not exposed here."),
            configuration=dict(job_limits=deepcopy(configuration["policy"]), bindings=[dict(operation=operation,
                resource_id=row["resource_id"], binding_ordinal_0based=row["binding_ordinal_0based"],
                binding_sha256=digest(row["binding"]), deployment_version=row["binding"]["deployment"]["version"],
                source_sha256=row["binding"]["deployment"]["module"]["sha256"],
                python_version=row["binding"]["software"]["python_version"], environment=deepcopy(row["environment"]))]))}
    if operation == N_GLYCOSYLATION_TOOL:
        fields = dict(subject_ref=deepcopy(REF), allow_overlap={"type": "boolean"}, rows=deepcopy(rows))
        schema = dict(type="object", properties=fields, required=list(fields), additionalProperties=False)
        schema["$id"] = "urn:gene-annotation:ordinary-n-glycosylation-tool:" + digest(schema)
        return {operation: dict(resources="local", invocation_route={"kind": "direct"}, input_schema=schema,
            description="Find literal N-glycosylation candidate motifs in an explicitly received protein sequence and return selected retained values.",
            instructions=("Answer the parent's assigned scientific question using its explicitly selected protein sequence and allow_overlap setting. "
                "The original routine uppercases internally and reports literal N-X-S/T candidates with X other than P; other middle symbols are not silently excluded. "
                "allow_overlap=false resumes after the three-symbol motif, while true permits overlapping candidates. Native positions are one-based in the processed sequence. "
                "Preserve the supplied sequence identity, literal stored motif, selected overlap setting, original row ordinals and available source-coordinate mapping. "
                "The native log prints at most its first 100 rows; native total, printed rows and unprinted remainder remain separate. "
                "Missing, truncated and unavailable data remain distinct from an observed zero. Candidate motifs do not establish measured glycosylation, occupancy or confidence. "
                "Return only the requested controlled values; no host sequence normalization, translation or alternative scan is selected. "
                "The configured resource and binding are fixed at setup; this call selects no alternative deployment. Saved reads and recalculation are not exposed here."),
            configuration=dict(job_limits=deepcopy(configuration["policy"]), bindings=[dict(operation=operation,
                resource_id=row["resource_id"], binding_ordinal_0based=row["binding_ordinal_0based"],
                binding_sha256=digest(row["binding"]), deployment_version=row["binding"]["deployment"]["version"],
                source_sha256=row["binding"]["deployment"]["module"]["sha256"],
                python_version=row["binding"]["software"]["python_version"], environment=deepcopy(row["environment"]))]))}
    fields = dict(subject_ref=deepcopy(REF), min_length={"type": "integer", "minimum": 0,
        "description": "Minimum retained ORF nucleotide-symbol length, including its literal terminal stop codon."},
        search_reverse={"type": "boolean"}, filter_subsets={"type": "boolean"}, rows=deepcopy(rows))
    schema = dict(type="object", properties=fields, required=list(fields), additionalProperties=False)
    schema["$id"] = "urn:gene-annotation:ordinary-orf-tool:" + digest(schema)
    return {operation: dict(resources="local", invocation_route={"kind": "direct"}, input_schema=schema,
        description="Run the original literal DNA ORF scan on an explicitly received sequence operand and return selected retained values.",
        instructions=("Answer the parent's assigned scientific question using its explicitly selected sequence and parameters. "
            "The original routine uppercases internally, scans all three forward frames for literal ATG through the next literal TAA, TAG or TGA, "
            "and optionally scans reverse complements. min_length counts nucleotide symbols including the terminal stop codon. "
            "filter_subsets removes same-strand contained intervals after longest-first ordering; final native rows are ordered by descending nucleotide length. "
            "Start/end are zero-based half-open coordinates in the selected input. Native translation uses Biopython translate(to_stop=True); "
            "retained translation/mapping qualifiers remain explicit. Source paths describe original nucleotide or symbol ancestry, including protein ancestry, "
            "rather than amino-acid coordinates. Preserve original row identities, units, empty populations, missing values and partial results. "
            "This scan does not establish genes or annotation confidence. Return only the requested controlled values. "
            "The configured resource and binding are fixed at setup; this call selects no alternative deployment. Saved reads and recalculation are not exposed here."),
        configuration=dict(job_limits=deepcopy(configuration["policy"]), bindings=[dict(operation=operation,
            resource_id=row["resource_id"], binding_ordinal_0based=row["binding_ordinal_0based"],
            binding_sha256=digest(row["binding"]), deployment_version=row["binding"]["deployment"]["version"],
            source_sha256=row["binding"]["deployment"]["module"]["sha256"],
            python_version=row["binding"]["software"]["python_version"], environment=deepcopy(row["environment"]))]))}


def _saved_mode_catalog(configuration, *, operation=ORF_TOOL):
    profile = _profile(operation)
    native = molecular_sequence_tool_catalog(configuration)
    if operation == PLACEMENT_TOOL:
        from .primer_placement_result_contracts import argument_schema
        entry = deepcopy(native.get(operation, dict(resources="local", invocation_route={"kind": "direct"},
            description="Read retained short-sequence placement values or calculate the authenticated saved placement Sheet.",
            instructions="Preserve full original operands, occurrence identities, source mappings and distinct retained populations.")))
        entry["input_schema"] = argument_schema(native=operation in native, saved=True)
        entry["instructions"] += (" read_stored selects stored values from the admitted Source without mathematics or a new Source. "
            "calculate_saved calls the existing placement calculator once on that Source's authenticated Sheet and publishes a derived Source; "
            "it never enumerates target windows or accepts replacement operands. Nested input/File provenance grants no references.")
        return {operation: entry}
    rows = contracts.ordinary_molecular_sequence_fact_sources(operation)[profile["fact_source"]]["report_schema"]["items"]["properties"]["selection"]["properties"]["rows"]
    variants = []
    if operation in native:
        entry = deepcopy(native[operation])
        variants.append({key: value for key, value in entry["input_schema"].items() if key != "$id"})
        entry["instructions"] = entry["instructions"].replace("Saved reads and recalculation are not exposed here.", "")
    else:
        entry = dict(resources="local", invocation_route={"kind": "direct"},
            description=("Read selected retained ORF values or calculate the authenticated saved sheet without native enumeration."
                if operation == ORF_TOOL else
                "Read retained O-glycosylation hotspot values or calculate the authenticated saved sheet without another scan."
                if operation == O_GLYCOSYLATION_TOOL else
                "Read retained N-glycosylation candidate values or calculate the authenticated saved sheet without another scan."),
            instructions="Preserve the parent's question, original native rows, source paths, units, populations and qualifications. ")
    for mode in ("read_stored", "calculate_saved"):
        variants.append(dict(type="object", additionalProperties=False, required=["mode", "result_ref", "rows"], properties=dict(
            mode={"const": mode, "type": "string"}, result_ref={"type": "string", "pattern": "^source_[0-9a-f]{24}$"}, rows=deepcopy(rows))))
    schema = dict(anyOf=variants)
    schema["$id"] = ("urn:gene-annotation:ordinary-orf-tool:" if operation == ORF_TOOL else
        "urn:gene-annotation:ordinary-o-glycosylation-tool:" if operation == O_GLYCOSYLATION_TOOL else
        "urn:gene-annotation:ordinary-n-glycosylation-tool:") + digest(schema)
    entry["input_schema"] = schema
    if operation == O_GLYCOSYLATION_TOOL:
        entry["instructions"] += ("read_stored selects literal retained values from an explicitly received original or derived Source and keeps its identity. "
            "calculate_saved calls the existing glycosylation calculator on the authenticated sheet and publishes a distinct derived Source without another native scan. "
            "Saved rows select retained printed sites only; the original window, threshold, next-proline rule, clipped-window operands and native total/printed/remainder meanings stay unchanged. "
            "The complete fraction and native rounded display remain separate. Saved modes accept no replacement sequence or scan parameters. "
            "Do not invent unprinted sites, rejected-window scores, occupancy or calibrated probabilities. Preserve zero, null, partial states and original source paths. "
            "Source provenance strings grant no Files.")
        return {operation: entry}
    if operation == N_GLYCOSYLATION_TOOL:
        entry["instructions"] += ("read_stored selects literal retained values from an explicitly received original or derived Source and keeps its identity. "
            "calculate_saved calls the existing glycosylation calculator on the authenticated sheet and publishes a distinct derived Source without a native rescan. "
            "Saved rows select retained logged cells only; the original overlap setting and native total/printed/remainder meanings stay unchanged. "
            "Do not invent unprinted positions or biological modification measurements. Preserve zero, null, partial states and original source paths. "
            "Source provenance strings grant no Files.")
        return {operation: entry}
    entry["instructions"] += ("read_stored selects literal values from an explicitly received original or derived Source and keeps that Source identity. "
        "calculate_saved calls the existing ORF calculator on its authenticated saved sheet and publishes a distinct derived Source; it never reruns the native scan. "
        "Historical observations and prior calculations remain unchanged even if current derived values differ. "
        "Saved modes accept rows only as a view; original scan parameters and frozen genetic-code/mapping evidence remain in the sheet. "
        "Retain zero, null, missing paths, original row ordinals and partial qualifications. Source provenance strings grant no Files.")
    return {operation: entry}


def _n_context_partial(operation, public):
    """Keep global retained glyco status when the selected cell view is empty."""
    if operation == PLACEMENT_TOOL:
        return public["context"]["component_status"] != "complete" or public["context"]["native_outcome"] != "completed"
    if operation not in (N_GLYCOSYLATION_TOOL, O_GLYCOSYLATION_TOOL):
        return False
    context = public["values"]["context"]
    return any(cell["value_state"] != "stored_value" or cell["value"] != complete
        for cell, complete in ((context["component_status"], "complete"),
            (context["input"]["native_outcome"], "completed")))


async def _observe_original(prepared):
    """Join the observer on cancellation; leave the original native unit intact."""
    stop_observation = threading.Event()
    operation = ordinary._prepared_profile(prepared)["operation"]
    observe = (ordinary.run_ordinary_orf_attempt if operation == ORF_TOOL else
        ordinary.run_ordinary_molecular_sequence_attempt)
    task = asyncio.create_task(asyncio.to_thread(observe, prepared, cancel_event=stop_observation))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        stop_observation.set()
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if task.done() and not task.cancelled():
            task.exception()
        raise


class OrdinaryMolecularSequenceTools:
    def __init__(self, registry, *, configuration, saved_modes=False):
        _require(type(saved_modes) is bool, "saved_modes_invalid")
        self.registry, self.store = registry, registry.store
        self.configuration = _configuration(configuration)
        self.saved_modes = saved_modes

    def _run_selection(self, owner, row):
        """Join new work to this run's actual resource record, without repricing recovery."""
        resources = getattr(owner.owner, "resources", None)
        _require(type(resources) is dict, "run_resource_selection_conflict")
        resource = resources.get(row["resource_id"])
        _require(type(resource) is dict and resource.get("kind") == "local"
            and same(resource.get("workspace"), row["workspace"])
            and same(resource.get("policy"), ordinary.POLICY), "run_resource_selection_conflict")
        bindings = resource.get("native_molecular_sequence")
        ordinal = row["binding_ordinal_0based"]
        _require(type(bindings) is list and ordinal < len(bindings) and same(bindings[ordinal], row["binding"]),
            "run_resource_selection_conflict")

    def _admitted_subject(self, context, reader, subject_ref):
        # Metadata selects the actual namespace only. No sequence helper or
        # artifact-byte reader runs until the real received-input owner agrees.
        record = self.store.get(subject_ref)
        namespace = record.get("record_type")
        _require(namespace in SUBJECT_KINDS, "sequence_operand_required")
        received = validate_molecular_sequence_received_subject(
            reader(context, subject_ref, namespace, subject_metadata_only=True))
        _require(type(received) is dict and received.get("failure") is None and type(received.get("input")) is dict,
            "subject_not_received")
        item = received["input"]
        witness, receiver = item.get("witness", {}), item.get("receiver", {})
        _require(received.get("selection") == dict(reference=subject_ref, namespace=namespace)
            and witness.get("reference") == subject_ref and witness.get("namespace") == namespace
            and same(witness.get("record"), record) and witness.get("record_sha256") == input_record_digest(record)
            and receiver == dict(run_id=context.run_id, episode_id=context.episode_id,
                request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
            and same(item.get("scope"), self.store.validate_scope(plain(context.scope))), "subject_admission_conflict")
        return _copy(received)

    def _placement_admissions(self, context, reader, arguments):
        target = self._admitted_subject(context, reader, arguments["target_ref"])
        refs = arguments["primer_refs"]
        primers = ([self._admitted_subject(context, reader, ref) for ref in refs] if type(refs) is list
            else self._admitted_subject(context, reader, refs))
        return dict(target=target, primers=primers)

    def _host_binding(self, owner, action, context, admitted):
        operation = action.intent["tool_name"]
        host_version, host_filename = _HOST_BINDINGS[operation]
        path = action.directory / host_filename
        saved = read_control(path)
        if saved is not None:
            _closed(saved, ("version", "intent_sha256", "configuration_selection", "policy", "subject_admission", "frozen_operand"),
                "host_binding_fields_invalid")
            _require(saved["version"] == host_version and saved["intent_sha256"] == digest(action.intent)
                and same(saved["policy"], ordinary.POLICY) and same(saved["subject_admission"], admitted), "original_host_binding_conflict")
            _configuration_row(saved["configuration_selection"])
            _require(saved["configuration_selection"]["operation"] == operation, "original_host_binding_conflict")
            ordinary._operand(saved["frozen_operand"], action.intent["arguments"] if operation == PLACEMENT_TOOL else action.intent["arguments"]["subject_ref"], operation=operation)
            if operation == PLACEMENT_TOOL:
                from .primer_placement_result_contracts import admission_matches
                _require(admission_matches(saved["frozen_operand"], admitted), "operand_subject_admission_conflict")
            else:
                _require(same(saved["frozen_operand"]["subject"], admitted["input"]["witness"]["record"]),
                    "operand_subject_admission_conflict")
            return saved
        _require(self.configuration is not None, "configuration_required")
        row = _configuration_selection(self.configuration, operation)
        self._run_selection(owner, row)
        if operation == PLACEMENT_TOOL:
            from .primer_placement_result_contracts import OPERANDS_VERSION, admission_matches
            arguments = action.intent["arguments"]
            freeze = lambda ref: self.registry._prepare_molecular_sequence_operand(operation, ref, scope=plain(context.scope))
            refs = arguments["primer_refs"]
            operand = dict(version=OPERANDS_VERSION, target=freeze(arguments["target_ref"]),
                primers=[freeze(ref) for ref in refs] if type(refs) is list else freeze(refs))
            _require(admission_matches(operand, admitted), "operand_subject_admission_conflict")
        else:
            operand = (self.registry._prepare_orf_sequence_operand(
                action.intent["arguments"]["subject_ref"], scope=plain(context.scope)) if operation == ORF_TOOL else
                self.registry._prepare_molecular_sequence_operand(operation,
                    action.intent["arguments"]["subject_ref"], scope=plain(context.scope)))
            _require(same(operand["subject"], admitted["input"]["witness"]["record"]), "operand_subject_admission_conflict")
        saved = dict(version=host_version, intent_sha256=digest(action.intent),
            configuration_selection=deepcopy(row), policy=deepcopy(ordinary.POLICY),
            subject_admission=admitted, frozen_operand=operand)
        immutable(path, saved)
        return saved

    def _saved(self, owner, action, context, arguments, scope, *, read_received=None):
        operation = action.intent["tool_name"]
        try:
            outcome = owner._ordinary_recorded_operation(action.intent)
        except ValueError as error:
            raise ContractError(_code(operation, "saved_operation_conflict")) from error
        if outcome is None:
            return None
        key = action.intent["operation_key"]
        if outcome.get("status") in ("completed", "partial"):
            public = (contracts.validate_ordinary_orf_return(outcome["result"]) if operation == ORF_TOOL else
                contracts.validate_ordinary_molecular_sequence_return(outcome["result"], operation=operation))
            _require(outcome.get("record_refs") == [public["source_ref"]], "saved_source_conflict")
            read = (owner.read_ordinary_orf_action_result if operation == ORF_TOOL else
                owner.read_ordinary_molecular_sequence_action_result)
            _require(same(read(context, arguments, key, read_received=read_received,
                **({} if operation == ORF_TOOL else {"operation": operation})), public), "saved_publication_conflict")
        else:
            _require(outcome.get("status") in ("invalid", "failed", "unavailable")
                and outcome.get("result") is None and outcome.get("record_refs") == [], "saved_failure_conflict")
        return outcome

    def _failure(self, action, arguments, scope, error):
        operation = action.intent["tool_name"]
        acquisition = isinstance(error, AcquisitionError)
        code = error.code if acquisition else str(error) if isinstance(error, ContractError) else _code(operation, "invalid_input")
        unavailable = code in ("ordinary_orf_configuration_required", _code(operation, "configuration_required"))
        outcome = dict(status="failed" if acquisition else "unavailable" if unavailable else "invalid", operation_ref=identity("operation", {
            "key": action.intent["operation_key"], "name": operation, "arguments": arguments}), record_refs=[], changed_record_refs=[],
            result=None, feedback=dict(category="execution" if acquisition else "arguments_or_reference", code=code))
        if acquisition and error.phase is not None:
            outcome["feedback"]["phase"] = error.phase
        with self.store.transaction():
            self.registry._save(action.intent["operation_key"], operation, arguments, scope, outcome)
        return outcome

    async def execute(self, arguments, *, scope, operation_key, authority, operation=ORF_TOOL):
        arguments = (contracts.validate_ordinary_orf_arguments(arguments) if operation == ORF_TOOL else
            contracts.validate_ordinary_molecular_sequence_arguments(operation, arguments))
        if "mode" not in arguments or operation == PLACEMENT_TOOL and arguments["mode"] == "run_native":
            return await self._execute_native(arguments, scope=scope, operation_key=operation_key, authority=authority, operation=operation)
        _require(self.saved_modes, "saved_modes_not_configured")
        return await self._execute_saved(arguments, scope=scope, operation_key=operation_key, authority=authority, operation=operation)

    async def _execute_saved(self, arguments, *, scope, operation_key, authority, operation=ORF_TOOL):
        scope = _copy(scope)
        context, reader = authenticate_molecular_invocation(self.registry, operation, arguments, scope, operation_key)
        _require(isinstance(authority, tuple) and len(authority) == 2 and authority[0] is context and authority[1] is reader,
            "invocation_authority_conflict")
        owner = self.registry.molecular_sequence_results_for(context.run_id)
        _require(owner.store is self.store and owner.owner.tool_registry is self.registry and owner.run_id == context.run_id,
            "result_owner_conflict")
        _require(not self.store.db.in_transaction, "native_work_requires_no_transaction")
        async with owner.locked_action(context, target=None, tool_name=operation, arguments=arguments, operation_key=operation_key) as action:
            saved = self._saved(owner, action, context, arguments, scope, read_received=reader)
            if saved is not None:
                return saved
            try:
                prepare = (owner.prepare_ordinary_orf_saved if operation == ORF_TOOL else
                    owner.prepare_ordinary_molecular_sequence_saved)
                prepared = prepare(action, read_received=reader)
                with self.store.transaction():
                    if arguments["mode"] == "read_stored":
                        public, references = prepared["public"], [arguments["result_ref"]]
                    else:
                        capture = (owner.capture_ordinary_orf_saved if operation == ORF_TOOL else
                            owner.capture_ordinary_molecular_sequence_saved)
                        publish = (owner.publish_ordinary_orf if operation == ORF_TOOL else
                            owner.publish_ordinary_molecular_sequence)
                        custody = capture(action, prepared=prepared)
                        public, references = publish(action, custody=custody)
                    partial = bool(public["failures"]) or _n_context_partial(operation, public) or any(
                        cell["value_state"] not in ("stored_value", "stored_null")
                        or any(name in ("component_status", "native_outcome") and qualifier["value_state"] == "stored_value"
                            and qualifier["value"] not in ("complete", "completed")
                            for name, qualifier in cell["scientific_qualifiers"]["states"].items())
                        for cell in public["values"]["rows"])
                    outcome = dict(status="partial" if partial else "completed", operation_ref=identity("operation", {
                        "key": operation_key, "name": operation, "arguments": arguments}), record_refs=references,
                        changed_record_refs=[] if arguments["mode"] == "read_stored" else list(references), result=public,
                        feedback=None if not partial else dict(category="representation", code=_code(operation, "selected_result_partial"),
                            source_ref=public["source_ref"]))
                    self.registry._save(operation_key, operation, arguments, scope, outcome)
                return outcome
            except (asyncio.CancelledError, MolecularOperationUnpublished):
                raise
            except (AcquisitionError, ValueError, KeyError) as error:
                if any((action.directory / name).exists() for name in
                        ("ordinary-calculation-started.json", "ordinary-calculation-result.json", "ordinary-read-receipt.json")):
                    raise MolecularOperationUnpublished(_code(operation, "saved_action_unpublished")) from error
                return self._failure(action, arguments, scope, error)
            except Exception as error:
                raise MolecularOperationUnpublished(_code(operation, "saved_action_unpublished")) from error

    async def _execute_native(self, arguments, *, scope, operation_key, authority, operation=ORF_TOOL):
        """Own the complete action through publication and ToolOperation save."""
        arguments, scope = _copy(arguments), _copy(scope)
        if operation == ORF_TOOL:
            contracts.ordinary_orf_selector(arguments)
        else:
            contracts.ordinary_molecular_sequence_selector(operation, arguments)
        context, reader = authenticate_molecular_invocation(self.registry, operation, arguments, scope, operation_key)
        _require(isinstance(authority, tuple) and len(authority) == 2 and authority[0] is context and authority[1] is reader,
            "invocation_authority_conflict")
        owner = self.registry.molecular_sequence_results_for(context.run_id)
        _require(owner.store is self.store and owner.owner.tool_registry is self.registry and owner.run_id == context.run_id,
            "result_owner_conflict")
        _require(not self.store.db.in_transaction, "native_work_requires_no_transaction")
        async with owner.locked_action(context, target=None, tool_name=operation, arguments=arguments, operation_key=operation_key) as action:
            # An occupied key belongs to its original recorded operation.
            # Authentication failures must never enter the fresh-failure INSERT.
            saved = self._saved(owner, action, context, arguments, scope)
            if saved is not None:
                return saved
            host_path = action.directory / _HOST_BINDINGS[operation][1]
            original_binding = host_path.exists() or host_path.is_symlink()
            prepared = None
            try:
                _require(self.configuration is not None or original_binding, "configuration_required")
                admitted = (self._placement_admissions(context, reader, arguments) if operation == PLACEMENT_TOOL else
                    self._admitted_subject(context, reader, arguments["subject_ref"]))
                if not original_binding:
                    _require(type(self.registry.local_job_policy) is LocalJobPolicy
                        and self.registry.local_job_policy.to_dict() == ordinary.POLICY, "registry_allocation_conflict")
                binding = self._host_binding(owner, action, context, admitted)
                original_binding = True
                row = binding["configuration_selection"]
                configuration = dict(version=CONFIGURATION_VERSION, policy=binding["policy"], bindings=[row])
                selected = (compile_ordinary_orf_selection(configuration) if operation == ORF_TOOL else
                    compile_ordinary_molecular_sequence_selection(configuration, operation=operation))
                prepare = (ordinary.prepare_ordinary_orf_attempt if operation == ORF_TOOL else
                    ordinary.prepare_ordinary_molecular_sequence_attempt)
                prepared = prepare(context=context, operation_key=operation_key,
                    arguments=arguments, frozen_operand=binding["frozen_operand"], selected=selected,
                    policy=LocalJobPolicy(**binding["policy"]),
                    **({} if operation == ORF_TOOL else {"operation": operation}))
                execution = await _observe_original(prepared)
                capture = (owner.capture_ordinary_orf if operation == ORF_TOOL else
                    owner.capture_ordinary_molecular_sequence)
                publish = (owner.publish_ordinary_orf if operation == ORF_TOOL else
                    owner.publish_ordinary_molecular_sequence)
                custody = capture(action, execution=execution)
                with self.store.transaction():
                    public, references = publish(action, custody=custody)
                    declaration = execution["declaration"]
                    partial = (execution["failure"] is not None or execution["returncode"] != 0 or bool(custody["failures"])
                        or any(state != "retained" for state in public["file_states"].values())
                        or declaration is None or declaration.get("native_call_state") != "returned"
                        or declaration.get("native_failure") is not None or declaration.get("driver_failure") is not None)
                    partial |= _n_context_partial(operation, public)
                    partial |= any(cell["value_state"] not in ("stored_value", "stored_null")
                        or any(name in ("component_status", "native_outcome") and qualifier["value_state"] == "stored_value"
                            and qualifier["value"] not in ("complete", "completed")
                            for name, qualifier in cell["scientific_qualifiers"]["states"].items())
                        for cell in public["values"]["rows"])
                    outcome = dict(status="partial" if partial else "completed", operation_ref=identity("operation", {
                        "key": operation_key, "name": operation, "arguments": arguments}), record_refs=references,
                        changed_record_refs=list(references), result=public, feedback=None if not partial else dict(
                            category="execution" if execution["failure"] is not None or execution["returncode"] != 0 else "representation",
                            code=_code(operation, "selected_result_partial"), source_ref=public["source_ref"]))
                    self.registry._save(operation_key, operation, arguments, scope, outcome)
                return outcome
            except (asyncio.CancelledError, MolecularOperationUnpublished):
                raise
            except (AcquisitionError, ValueError, KeyError) as error:
                if original_binding or prepared is not None:
                    raise MolecularOperationUnpublished(_code(operation, "original_action_unpublished")) from error
                return self._failure(action, arguments, scope, error)
            except Exception as error:
                # No exception can release the lease while an observer thread
                # remains active or convert its original attempt into a retry.
                raise MolecularOperationUnpublished(_code(operation, "original_action_unpublished")) from error


__all__ = ["ORF_TOOL", "N_GLYCOSYLATION_TOOL", "O_GLYCOSYLATION_TOOL", "PLACEMENT_TOOL", "BINDING_VERSION", "CONFIGURATION_VERSION", "HOST_BINDING_VERSION", "HOST_BINDING_FILENAME",
    "SUBJECT_KINDS", "validate_native_molecular_sequence_bindings", "normalize_molecular_sequence_configuration",
    "compile_ordinary_orf_selection", "compile_ordinary_molecular_sequence_selection", "molecular_sequence_tool_catalog", "OrdinaryMolecularSequenceTools"]
