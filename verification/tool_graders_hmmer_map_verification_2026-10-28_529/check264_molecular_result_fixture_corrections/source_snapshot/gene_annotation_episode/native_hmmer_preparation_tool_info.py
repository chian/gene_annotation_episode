"""Information and exact request schemas for explicitly bound HMMER preparation.

Construction is pure: supplied software identities describe configured operations;
they do not prove installation or cause discovery, execution, parsing or grading.
The existing launch/local and results episodes own their selected operations.
"""
from copy import deepcopy

from .native_infernal_contracts import finite_json_copy
from .native_hmmer_preparation_contracts import (
    PROGRAM_MODES, _path, _sha, _text, operand_contract, output_contract,
)
from .native_hmmer_preparation_job_schema import preparation_requested_job_schema


_DESCRIPTIONS = {
    "alimask": {
        "mask_alignment": "Mask selected source-alignment columns in a supplied multiple alignment.",
        "mask_model": "Mask source-alignment spans selected in profile-model coordinates.",
        "model_to_alignment": "Map selected model-position intervals to source-alignment columns.",
        "alignment_to_model": "Map selected source-alignment intervals to model positions.",
    },
    "hmmbuild": {
        "build_alignment": "Build profile HMMs from supplied multiple sequence alignments.",
        "build_single_sequence_matrix": "Use matrix estimation for single-sequence alignments when building profile HMMs.",
    },
    "hmmconvert": {
        "ascii": "Convert supplied profile HMMs to an explicitly selected HMMER3 ASCII revision.",
        "binary": "Convert supplied profile HMMs to native HMMER binary format.",
        "legacy_hmmer2": "Convert supplied profile HMMs to legacy HMMER2 text format.",
    },
    "hmmemit": {
        "sample_core_unaligned": "Generate unaligned sequence samples from supplied core profile HMMs.",
        "sample_core_aligned": "Generate aligned sequence samples from supplied core profile HMMs.",
        "consensus_simple": "Generate simple maximum-probability consensus sequences from supplied profile HMMs.",
        "consensus_thresholded": "Generate consensus sequences with selected probability and case thresholds.",
        "sample_profile": "Generate sequence samples from profiles with selected alignment-style and expected-length settings.",
    },
    "hmmfetch": {
        "single_key": "Retrieve a profile HMM for one supplied native name or accession key.",
        "key_file": "Retrieve profile HMMs for the key occurrences in a supplied file.",
        "index": "Create an SSI lookup index for a private copy of supplied profile HMMs.",
    },
    "hmmpress": {"index": "Prepare the four native profile-database files used by hmmscan and nhmmscan."},
    "hmmsim": {
        "viterbi": "Generate random-sequence Viterbi score distributions for supplied profile HMMs.",
        "msv": "Generate random-sequence MSV score distributions for supplied profile HMMs.",
        "forward": "Generate random-sequence Forward scores and native exponential-tail fits.",
        "hybrid": "Generate experimental Hybrid score distributions for supplied profile HMMs.",
    },
    "hmmstat": {"summary": "Inspect every supplied profile HMM's training counts, size and native model statistics."},
    "makehmmerdb": {"build": "Build an FM-index representation of a supplied sequence collection."},
    "hmmerfm-exactmatch": {
        "locations": "Enumerate native literal-query locations in an explicitly supplied DNA FM index.",
        "count_only": "Count native raw FM intervals for supplied literal queries without reporting locations.",
    },
}

_MODE_DETAILS = {
    "alimask": {
        "mask_alignment": "Keep --alirange and its selected range string in options. These are source-alignment columns; write the MM mask to masked_alignment.",
        "mask_model": "Keep --modelrange and its selected range string in options. Map each model interval's endpoints to the source alignment and mask every intervening column, including inserts.",
        "model_to_alignment": "Keep --model2ali and its selected range string in options. Mapping rows remain on stdout even when -o redirects the descriptive header. This mode produces no masked_alignment.",
        "alignment_to_model": "Keep --ali2model and its selected range string in options. Native rows report the first and last mapped alignment columns within the requested interval as well as model endpoints; preserve both requested and returned coordinates. The producer rejects intervals wholly after the last match column. Its established preflight covers hand/RF and fast unweighted, given-weight or PB maps with explicit alphabet; GSC/BLOSUM maps and PB subsampling above 50,000 sequences remain unsupported. It does not substitute a different map or weighting choice.",
    },
    "hmmbuild": {
        "build_alignment": "Use the selected --fast occupancy or --hand RF architecture, alphabet, weights, priors, effective-count and calibration settings. --cpu and HMMER_NCPU retain the caller's values; an unresolved native CPU default is not a measured core count.",
        "build_single_sequence_matrix": "The compiler adds --singlemx. It selects matrix estimation for one-sequence MSAs; multi-sequence MSAs still use native alignment estimation. Select a supported --mx name or the explicit matrix operand, which becomes --mxfile. --popen and --pextend configure matrix-mode gap probabilities. The one-sequence model NAME can be the sequence name while the summary keeps the MSA name. Matrix probabilities are model-derived, not observed residue frequencies. A selected -O resaved_alignment can be empty because native SingleBuilder emits no postmsa.",
    },
    "hmmconvert": {
        "ascii": "The compiler adds -a. Optional --outfmt selects 3/a through 3/f; the recorded default is 3/f. Preserve the actual revision: older revisions omit newer annotations or represent calibration differently.",
        "binary": "The compiler adds -b. Optional --outfmt selects the native revision. stdout is binary model data and must never be decoded or monitored as an ordinary text log. Signature recognition does not establish decoded model count or probability equivalence.",
        "legacy_hmmer2": "The compiler adds -2; --outfmt is incompatible. Legacy HMMER2 uses quantized log-odds and different model semantics, not HMMER3 negative-log probabilities. Its unsupported decoder leaves numerical content validation unknown.",
    },
    "hmmemit": {
        "sample_core_unaligned": "Default core sampling writes FASTA. -N is the requested sample count per model. FASTA has no native trace or model alignment, so exact model coverage and domain counts are unmeasured.",
        "sample_core_aligned": "The compiler adds -a and writes Stockholm. -N is the requested sample count per model. Retain every generated row and RF column; gap counts and occupancy use actual alignment width and sample populations.",
        "consensus_simple": "The compiler adds -c. Native consensus selects the first maximum in alphabet order; a masked model state emits unknown X/N. -N is not a consensus operand. Validate the generated sequence against saved model probabilities while preserving near-tie uncertainty from rounding.",
        "consensus_thresholded": "The compiler adds -C. --minl marks low maximum probabilities with lowercase unknown symbols; --minu controls uppercase versus lowercase maximum-probability symbols. Masked states remain lowercase unknown. Preserve actual thresholds and case; -N is not allowed. Saved rounded probabilities can leave threshold/tie agreement ambiguous.",
        "sample_profile": "The compiler adds -p. Select one of --local, --unilocal, --glocal or --uniglocal; -L configures expected length, not observed sample length. -N is samples per model. Profiles may emit flanks and multiple domains; unaligned FASTA supplies neither observed domain count nor exact model coverage.",
    },
    "hmmfetch": {
        "single_key": "Supply the positional key through key, with no whitespace or leading '-'. The compiler directs fetched_models with -o. An unindexed single-key scan returns the first name/accession match; that does not prove uniqueness.",
        "key_file": "The compiler adds -f and directs fetched_models with -o. Native key-file parsing uses the first token and # comments. With an explicitly supplied SSI, output follows key order, one model per key; without it, models appear once in source order when name or accession matches. Preserve name/accession aliases and repeated requests. Repeated identical keys are native errors. Unindexed missing keys may be omitted with exit zero; indexed failure can retain a valid earlier model prefix.",
        "index": "The compiler adds --index and creates the .ssi beside an immutable private model copy. Retain model, primary-name and accession-key counts separately. Index bytes and native counts alone do not decode every SSI entry or establish a later retrieval's success.",
    },
    "hmmpress": {
        "index": "Retain binary_models=.h3m, ssi_index=.h3i, msv_profiles=.h3f and remaining_profiles=.h3p with one common selected stem. All four belong to the exact source model occurrence and attempt. Native refusal cleanup can delete sidecars, so the producer uses private staging; optional -f applies only there. The source's target-length 400 profile configuration is a preparation parameter, not an observed sequence length. Binary framing is separate from full internal profile validation, which remains unavailable for opaque members.",
    },
    "hmmsim": {
        "viterbi": "The compiler adds --vit. Optional -a supplies native M+D+I traceback lengths; selected alignments uses --afile and requires -a. --fast cannot be combined with traceback. Preserve native and independently fitted Gumbel quantities separately.",
        "msv": "The compiler adds --msv. --nu is available only for generic MSV, not --fast. Native outputs can coincide across the four styles; preserve the style identity without claiming independent measurements.",
        "forward": "The compiler adds --fwd. Preserve every selected tail in --tmin/--tmax/--tpoints with --tlinear or geometric spacing, including its actual tail population and independent exponential fit. Forward --ffile can be empty after exit zero because of a native defect; that is missing output, not a measured zero passing count.",
        "hybrid": "The compiler adds --hyb. --fast is undefined for this native algorithm and is rejected. Native pmu=0 is explicitly undetermined calibration; its experimental filter diagnostic must retain that qualification, separately from Gumbel summary fits.",
    },
    "hmmstat": {
        "summary": "Native stdout supplies the complete summary; no second summary operation is needed. Preserve idx, name, accession, nseq, eff_nseq, M, relent, info, p_relE and compKL with their original tokens. Source sequence counts are not model counts. Missing header counts, native -1 sentinels and nonfinite statistics remain explicit states. Independent calculations require explicitly supplied background and length_probability (p1); the versioned HMMER 3.4 helper is available only for an explicit caller selection. Absence remains unknown and is never filled automatically. Native two-decimal statistics remain separate from recalculated full precision.",
    },
    "makehmmerdb": {
        "build": "Select alphabet and format explicitly. --bin_length is a power of two in 32..4096; --sa_freq is a positive power of two; --block_size is a positive decimal-Mbase integer no greater than 2147 under the implemented native signed-int multiplication. --fwd_only changes index traversal storage, not source population. Retain original RNA U separately from indexed T and ambiguous symbols separately from generated replacements. Amino writer output is retained, but the native downstream FM reader is DNA-only. Stored segments are not necessarily distinct original sequences. The format has no magic: build ABI and source associations come from the original sealed producer record, not filename or current host inference. FASTA source extraction is established; other execution formats can retain bytes with unavailable source decoding.",
    },
    "hmmerfm-exactmatch": {
        "locations": "The compiler selects an explicit --out hits destination. Retain all native anchors and f/r directions. Coordinates are one-based inclusive: f is a left endpoint and r a right endpoint; r means string reversal, not reverse complement or a biological minus strand. Native reverse-boundary defects can admit invalid intervals and omit valid matches. Independent checks preserve these rows and count valid, invalid and unresolved locations separately. Matching aggregate totals or exit zero does not establish complete literal matching.",
        "count_only": "The compiler adds --count_only and an explicit --out destination. An existing empty hits file is expected; locations are unmeasured. Native H counts raw FM intervals, including possible ambiguity replacements, cross-sequence matches and overlap duplicates. Q counts queries with raw intervals; no per-query count is emitted. Keep these aggregate populations distinct from validated source matches.",
    },
}

_PROGRAM_DETAILS = {
    "alimask": "Ranges are one-based inclusive, comma-separated occurrences, with at most 100 ranges. Overlapping requests remain distinct; --appendmask unions with existing MM, while the default replaces it. Native processes only the first MSA; retain all supplied bytes and report unprocessed records. Model and alignment coordinates differ. Current preflight reads Stockholm/Pfam only; other declared native input formats remain unsupported preflight cases. Independently reconstructed fast maps require the actual weighting/fragment semantics; unsupported maps stay unknown.",
    "hmmbuild": "The models output is HMMER3 ASCII. Optional summary uses -o and resaved_alignment uses -O. Retain every input MSA, model, full probability body and native summary. Original/source and resaved alignment coordinates are separate: Plan7 resaving can change columns. Check actual MSA/summary/model membership and MAP before relating coordinates; equal labels alone are insufficient. Stockholm decoding is established; accepting other native alignment formats for execution does not establish their decoder. Missing background leaves independent relative entropy unavailable.",
    "hmmconvert": "stdout and converted_models intentionally alias the same output path and native format, with two retained role occurrences but one model population. Retain original models, complete converted bytes and any valid prefix after a later-record failure. Compare body probabilities only when both formats are decoded. HMMER3 ASCII revisions a-f have explicit readers; HMMER2 and binary model bodies remain unsupported by the current numerical decoder. Missing fields or unknown model counts are not zero and conversion does not prove identical search behavior.",
    "hmmemit": "Samples and consensus are generated model data, not biological observations. Retain every model and generated occurrence in native order, preserving repeated labels, full sequence case, alphabet and sample identity. A name suffix alone cannot prove source association. --seed=0 requests an arbitrary native seed and does not establish reproducibility. HMMER2/binary inputs can execute natively while independent model-probability decoding remains unavailable. Missing model/trace information stays unknown.",
    "hmmfetch": "Input models and optional explicitly selected ssi retain their original association; no ambient sidecar is discovered. The producer stages models and SSI with matching private stems. NAME and ACC are native keys; repeated labels/bytes remain distinct model occurrences. Retrieval emits HMMER3 ASCII even from older formats. Preserve valid partial outputs and compare requested, resolved, missing and actually returned populations separately. Current HMMER2/binary/SSI internal decoding limits remain explicit.",
    "hmmpress": "Use complete ordinary model-file bytes with native names and a consistent alphabet. Preserve model occurrences, source hashes and original private-copy relationships outside model-facing text. Native model/name/accession counts, captured member sizes, source custody and format compatibility are separate checks. No search starts as part of preparation or validation; pressing success is not biological evidence.",
    "hmmsim": "Supply a same-alphabet model collection and retain full ordered scores, summary and every selected auxiliary output. -N is generated sequences per model (at least 10); -L is their fixed length. Keep seed, background policy, calibration options, algorithm and --fs/--sw/--ls/--s style (multihit local/unihit local/multihit glocal/unihit glocal). The producer explicitly records --fast=false and --tlinear=false when unselected; historical omissions remain unknown. --seed=0 is arbitrary. Scores are headerless native double vectors requiring the original recorded byte order and IEEE754 binary64 width, not the reading host's ABI. -v writes rounded scores to stdout; these cannot replace full vectors. Keep all XY datasets, tail schedules and native versus independent fits; missing vectors prevent refitting. Shared seeds do not establish independent model populations.",
    "hmmstat": "Retain the entire model population and native stdout/stderr. Match summary index to original model occurrence, checking native labels and counts without merging duplicates. The deterministic statistics reader/calculator preserves entropy, occupancy, composition and their units, with explicit supplied parameters. Native model-derived statistics are not annotation probabilities. HMMER2/binary source bodies remain undecoded even when native summary rows are available.",
    "makehmmerdb": "Retain the full FM database, original sequences, stdout and stderr. Temporary fmtmp files and all output writes belong to the private attempt. Full FM parsing preserves segments, ambiguity ranges, block arrays and sentinels; source custody and independently compared symbols have different meanings. Build/index success does not establish biological function or authorize a downstream search.",
    "hmmerfm-exactmatch": "queries is one nonempty literal canonical A/C/G/T sequence per LF-terminated line, at most 254 symbols; it is not FASTA. Current binding rejects U, CR, whitespace and unsupported characters rather than normalizing or splitting them. Preserve duplicate query occurrences. source_sequences supplies original FASTA for validation and is not an extra native argument. input_metadata.producer_contract must explicitly describe the imported HMMER 3.4 FM ABI; current-process ABI cannot replace it. Optional source_binding retains original source order/digests/producer association. Compatible DNA FM framing and arrays are checked before the unsafe native reader. Native miss R counts only zero raw intervals, so location Q+R need not equal query count. Retain stdout/stderr; the native post-free occ/sec diagnostic is not reliable productive throughput. Exhaustive literal checking is a separate explicitly selected calculation over retained source bytes, never a native rerun.",
}

_RESULTS = {
    "alimask": "populate_hmmer_alignment_preparation_sheet and calculate_hmmer_alignment_preparation_components retain native endpoints, source geometry and exact mask changes. Requested calculations include components.input_column_count and components.native_mapping_row_count; mask modes additionally expose components.actual_masked_count, components.newly_masked_count and components.masked_fraction with the alignment-width denominator.",
    "hmmbuild": "extract_hmmer_models, populate_hmmer_alignment_preparation_sheet and calculate_hmmer_alignment_preparation_components retain complete models and both alignments. Requested calculations include components.input_sequence_count, components.input_column_count, components.resaved_column_count, components.model_length and components.model_alignment_fraction, plus effective counts and explicitly parameterized model entropy/KL.",
    "hmmconvert": "extract_hmmer_models, populate_hmmer_artifact_sheet and calculate_hmmer_artifact_components compare original and converted occurrences. Requested calculations include decoded_model_count, length_difference, compared_cell_count and max_absolute_probability_difference; undecoded populations and equivalence remain unknown.",
    "hmmemit": "populate_hmmemit_sheet and calculate_hmmemit_components retain full generated sequences/alignments and model associations. Requested calculations include captured_sample_count, total_length and mean_length; aligned output additionally provides alignment_width and rf_match_column_count, while consensus provides mismatch_count and ambiguous_position_count. These describe generated data with actual denominators.",
    "hmmfetch": "extract_hmmer_models, populate_hmmer_artifact_sheet and calculate_hmmer_artifact_components retain key/model/index associations. Retrieval calculations include requested_key_count, resolved_key_count, missing_key_count and returned_model_occurrence_count. Index calculations instead expose native_model_count, native_primary_name_count and native_accession_count alongside decoded source counts and retained byte sizes.",
    "hmmpress": "extract_hmmer_models, populate_hmmer_artifact_sheet and calculate_hmmer_artifact_components retain native index summaries and source/bundle associations. Requested calculations include native_model_count, native_primary_name_count, native_accession_count, member_count and bundle_byte_sum. Binary framing checks do not imply full internal-content validation.",
    "hmmsim": "populate_hmmsim_sheet and calculate_hmmsim_components preserve every score vector and native row. Requested calculations include components.observed_count, components.mean, components.sample_variance and components.x10, plus components.mu, components.lambda, components.E10, tail quantities and selected filter/traceback statistics on their corresponding rows. Native, fitted and derived rows retain their separate meanings.",
    "hmmstat": "parse_hmmstat_summary, populate_hmmstat_sheet and calculate_hmmstat_components retain native rows and complete model arrays. Requested calculations include components.mean_match_relative_entropy, components.mean_match_information, components.position_relative_entropy and components.composition_relative_entropy. Supply background and length_probability explicitly in grading_parameters when those calculations are required; missing parameters leave the dependent quantities unavailable.",
    "makehmmerdb": "extract_hmmer_fm_database, populate_hmmer_fm_sheet and calculate_hmmer_fm_components retain full database/source data. Requested calculations include components.source_occurrence_count, components.stored_segment_count, components.source_symbol_total, components.actual_database_bytes and components.ambiguity_fraction. Sequence count, segment count and index byte size have distinct denominators and meanings.",
    "hmmerfm-exactmatch": "populate_hmmer_fm_sheet and calculate_hmmer_fm_components retain every query and native hit. Requested calculations include components.query_occurrence_count, components.native_Q, components.native_H and components.native_R. Location mode additionally exposes components.valid_location_count, components.invalid_location_count and components.unresolved_location_count; count-only leaves location quantities unmeasured.",
}

_EXECUTION_INFORMATION = (
    "Use the exact selected operands, native options, output roles and explicit environment in "
    "the callable request schema. The pure requested_job_from_hmmer_preparation compiler builds "
    "argv; validate_native_hmmer_preparation_requested_job checks its exact relationship to the "
    "typed job. Mode/path flags are compiler-owned except alimask's selected range flag. "
    "Commission through launch and the configured local child; that child selects practical.job.start. "
    "The original attempt and caller-owned allocation remain bound, with local limits of 20 GiB RAM "
    "and 4 GiB scratch and no wall-time cap. API/HPC preparation bindings are unfinished and are not "
    "substitute routes. Monitoring uses the existing generic local-resource task instructions: "
    "observe the same execution identity, native state, available outputs and selected stdout/stderr "
    "windows, subject to the tool's binary-output restriction. Liveness and byte availability alone "
    "do not establish productive execution or completion; logs remain measured facts for the episode. "
    "Retain complete selected artifacts, missing/empty/partial distinctions and valid failed-run prefixes. "
)

_RESULT_INFORMATION = (
    "The selected execution.results.collect operation acquires the original bound bundle. Separate "
    "deterministic parsers populate numerical sheets; separate calculators consume those sheets and "
    "explicit grading_parameters. Saved-sheet recalculation acquires nothing and reruns no native tool. "
    "Choose requested typed numerical paths/checks from preparation_projection_catalog(program, mode), "
    "with an explicit row window or record keys, or select artifacts by direction/role/ordinal. "
    "The native_hmmer_preparation_result_selector_v1 uses acquisition=complete_bound_bundle; "
    "artifact-only selection remains possible when numerical grading is unavailable. Full arrays stay "
    "retained while only the requested typed rows/artifacts and population qualifications return. "
    "Unknown measurements remain unknown, distinct from measured zero. Preparation success, indexing "
    "and generated data receive no invented gene-function confidence."
)


def validate_native_hmmer_preparation_bindings(value):
    """Validate only explicit binding data and return an independent JSON copy."""
    rows = finite_json_copy(value)
    if type(rows) is not list:
        raise ValueError("native_hmmer_preparation_explicit_binding_rows_required")
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != {"program", "mode", "software"}:
            raise ValueError("native_hmmer_preparation_invalid_binding")
        program, mode = row["program"], row["mode"]
        if (type(program) is not str or program not in PROGRAM_MODES or type(mode) is not str
                or mode not in PROGRAM_MODES[program] or (program, mode) in seen):
            raise ValueError("native_hmmer_preparation_invalid_or_duplicate_bound_mode")
        software = row["software"]
        if type(software) is not dict or set(software) != {"executable", "sha256", "engine_version"}:
            raise ValueError("native_hmmer_preparation_invalid_bound_software")
        _path(software["executable"], absolute=True)
        _sha(software["sha256"])
        if software["engine_version"] != "3.4":
            raise ValueError("native_hmmer_preparation_unverified_engine_version")
        seen.add((program, mode))
    return rows


def _roles_text(roles):
    return "; ".join(role + " (" + ", ".join(sorted(formats)) + ")" for role, formats in roles.items())


def native_hmmer_preparation_tool_contracts(bindings, *, resource_kind, resource_id):
    """Return exact configured mode schemas and child-owned commission routes."""
    if resource_kind != "local":
        raise ValueError("native_hmmer_preparation_resource_binding_unfinished:" + str(resource_kind))
    _text(resource_id, "resource_id")
    entries = []
    for binding in validate_native_hmmer_preparation_bindings(bindings):
        program, mode = binding["program"], binding["mode"]
        inputs, optional_inputs = operand_contract(program, mode)
        outputs, optional_outputs = output_contract(program, mode)
        instructions = " ".join((
            _DESCRIPTIONS[program][mode],
            "Required operands with declared native formats: " + _roles_text(inputs) + ".",
            "Optional operands: " + _roles_text(optional_inputs) + "." if optional_inputs else "",
            "Required retained outputs: " + _roles_text(outputs) + ".",
            "Optional selected outputs: " + _roles_text(optional_outputs) + "." if optional_outputs else "",
            _MODE_DETAILS[program][mode], _PROGRAM_DETAILS[program],
            _EXECUTION_INFORMATION, _RESULTS[program], _RESULT_INFORMATION,
        ))
        schema = preparation_requested_job_schema(program, mode)
        schema["properties"]["native_hmmer_preparation"]["properties"]["software"] = {
            "const": deepcopy(binding["software"])}
        entries.append({"name": "native." + program + "." + mode,
            "description": _DESCRIPTIONS[program][mode], "resources": "local",
            "instructions": instructions, "input_schema": schema,
            "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch",
                "resource_id": resource_id, "resource_role": "launch_local"}]}})
    return entries


def native_hmmer_preparation_tool_information(bindings, *, resource_kind, resource_id):
    """Return the corresponding name, description, resources and instructions."""
    return [{key: entry[key] for key in ("name", "description", "resources", "instructions")}
        for entry in native_hmmer_preparation_tool_contracts(bindings,
            resource_kind=resource_kind, resource_id=resource_id)]


__all__ = ["validate_native_hmmer_preparation_bindings", "native_hmmer_preparation_tool_contracts",
           "native_hmmer_preparation_tool_information"]
