# hmmsim pure numerical component — 263 / frozen 261/S1

This implements only the supplied-data reader and offline calculators. Root
still owns selected-tool dispatch, resource instructions, artifact capture,
requested typed projection and parent/child returns. No runtime, library,
accounting, other grader, execution or credit files are changed here.

The implementation was derived from the complete installed HMMER 3.4
`src/hmmsim.c`, Easel `lawless416`, `FitComplete`, `FitCompleteLoc`, exponential
`FitComplete`/survival, histogram `GetRank`, `GetTailByMass`, plot writers, and
integer mean/variance functions. Those are methods and format evidence; the
immutable objective and all 16 principles were read before implementation and
again after source study. Frozen S1 is authoritative for this component.

## Ports and exact storage shapes

`populate_hmmsim_sheet(*, operation, inputs, outputs, model_extraction,
native_abi=None)` returns exactly `schema, operation, artifact_occurrences,
input_records, native_rows, associations, native_abi, issues` with schema
`hmmer_simulation_sheet_v1`. It imports no execution, storage, network or model
service module. No files are opened.

`operation` has exactly `program, mode, engine_version, settings`, with program
`hmmsim`, version `3.4`, and mode `viterbi|msv|forward|hybrid`. Settings are copied
unchanged, including actual CLI spellings. Supply explicit positive integer
`-N` and `-L`, integer `--seed` (or resolved `seed`), style `fs|sw|ls|s` (or
the matching `--style` flag), and boolean `fast` (or `--fast`). The native default
seed is not guessed. `-a`, `-v`, the original output flags, `--pthresh` and all
other supplied settings remain recorded. Conflicting flags/resolved settings,
fast+Hybrid, fast+traceback and MPI order have explicit issues and unresolved
model associations. No alternative algorithm/resource is substituted.

Inputs are `{"models": [{"occurrence": ..., "content": bytes}, ...]}`.
Outputs use the same role-to-list shape for `summary, scores, alignments,
filter, survival, expected_counts, stdout, stderr`. Each occurrence is the exact
M1 eight-field object: `occurrence_id, direction, role, ordinal, artifact_ref,
sha256, size_bytes, completeness`. Ordinals are zero-based within each supplied
role list. Identity, digest, size, direction and ordering are validated without
opening the reference. An empty artifact retains its occurrence; an absent
artifact has no occurrence. Neither means a measured zero.

`model_extraction` is one exact `hmmer_model_extraction_v1` envelope, or an
ordered list of envelopes for multiple model input occurrences. Original M1
records are copied unchanged to `input_records`, including complete bodies.
NAME is read from the ordered `{tag,value,tokens,line}` headers, alphabet from
`{kind,symbols}`, and identity/byte bounds from its original locator. No name or
content digest becomes a replacement identity. Mixed alphabets, missing bodies,
invalid locators and mismatched extraction/occurrence references are explicit.

Every native row has exactly `kind, record_key, locator, model_keys, payload`.
`record_key` is `occurrence_id#kind/ordinal`. Locator has `artifact_ref,
occurrence_id, record_ordinal, byte_start, byte_end, line_start, line_end`.
Byte intervals are zero-based half-open; line intervals one-based inclusive
(null for binary). `model_keys` is the validated single model occurrence key,
or `[]` if unresolved. Association rows are `{record_key,model_keys,state,
method}` with state `resolved|unresolved`. Ordered serial model position is the
join; names validate that position. Input lists are never independently sorted.

Closed payload keys are exported as ordinary Python `ROW_FIELDS`:

| Kind | Payload fields and numerical meaning |
| --- | --- |
| summary | `name,tokens,values,states,raw_text`. Tokens/values/states share the closed algorithm-specific fields below. Original text is retained. |
| scores | `values,states,declared_population,observed_count,original_bytes_hex,completeness,representation,tokens`. Entire ordered arrays are retained. Binary scores are bits, `representation=native_binary64`, and `tokens=null`. Verbose stdout has `representation=printed_3_decimal` and every original token; it cannot supply an independent fit. Nonfinite values become null at their original indices, with explicit states and original binary bytes retained. |
| alignments | `sample_ordinal,trace_state_count,score,tokens,states,raw_text`. Zero-based sample position within model; count is the actual M+D+I trace-state sum; score is the native three-decimal bit score. Separate M/D/I counts are not emitted by hmmsim and are not invented. |
| filter | `name,count,denominator,fraction,tokens,states,raw_text`. Count is passing generated sequence occurrences, denominator is supplied `-N`, and fraction is the native four-decimal dimensionless value. |
| xy_series | `series_kind,series_ordinal,meaning,points,tokens,legends,delimiter,raw_text,complete`. Every point and token, original series order, legend and `&` is retained. Final missing delimiters are explicit partial series. |

Summary numeric columns for Viterbi/MSV/Hybrid are exactly `tailp,mu,lambda,E10,
mufix,E10fix,mufix2,E10fix2,pmu,plambda,E10p`. Forward omits `mufix2,E10fix2`.
Only selected `-a` adds `almean,alsd`. Units are exported in `SUMMARY_UNITS`:
locations and x10 in bits; slopes in inverse bits; E10 in expected sequence
counts; tailp dimensionless; alignment means/SDs in trace states. Summary
negative/invalid slopes or counts retain the token/value but carry invalid
state. Hybrid pmu retains token `0.0000`, value 0 and state `undetermined`.

Binary parsing requires exactly `native_abi={byte_order:little|big,
float_format:ieee754_binary64,bytes_per_float:8}`. It never uses host byte order.
N contiguous doubles per input model establish serial segments. Earlier complete
segments survive trailing truncation. Entire original byte segments are hex;
leftover partial-double bytes are retained. Without ABI, values and decoded
count are null, not zero. `observed_count` never replaces requested N.

Survival emits three series/model: empirical binned survival; fitted Gumbel
survival; fixed-lambda Gumbel survival. Forward's last two curves are **unscaled
conditional** exponential survival for the last selected tail, not multiplied
by tail mass. Expected-count series is rank versus N times native calibrated
survival, at up to the native 1000 ranks. Hybrid's expected-count series uses
native experimental Gumbel pmu0; this is retained, not validated calibration.
Model boundaries for complete auxiliary outputs use N rows (alignments), one
named row (filter), three series (survival), or one named series (expected
counts). Ambiguous multi-model XY segmentation leaves models/meaning unresolved.

## Offline calculations

`calculate_hmmsim_components(sheet, *, parameters=None)` returns exactly
`schema,operation,parameters,rows,checks,issues`, with schema
`hmmer_simulation_components_v1`. Every component has exactly
`{value,state,unit,inputs}`; states are `present,missing,incomplete,incompatible,
nonfinite,failed`, and unavailable values are null. Each input is
`{record_key,field}`; operation/parameter operands use null record_key and an
explicit path. Every calculation row has `kind,record_key,source_record_keys,
model_keys,components,details`. Its own key is `calculation/ordinal` within that
result, while source keys retain the original occurrence identities.

Rows separate `native_summary`, `score_statistics`, `fit`,
`native_rounding_residuals`, `alignment_statistics`, `native_filter`,
`filter_recalculation`, and `native_experimental_filter_replay`. No quantities
are folded into a universal score. No uncertainty estimate is manufactured.

| Calculation | Exact definition and denominator |
| --- | --- |
| Count/mean/min/max | Count original score occurrences; mean is sum/N on a complete vector. |
| Sample variance | sum((score-mean)^2)/(N-1); N<2 is unavailable. |
| x10 | Tenth highest score occurrence, retaining ties; N<10 is unavailable. |
| Gumbel complete fit | Solve 1/lambda - mean(x) + sum(x exp(-lambda x))/sum(exp(-lambda x)) = 0; mu = -log(mean(exp(-lambda x)))/lambda. Implementation shifts by min(x) for stability. |
| Fixed slope | Same location formula with explicit fixed lambda; native-lambda variant uses separately retained printed plambda. |
| Gumbel E10 | N * (1-exp(-exp(-lambda*(x10-mu)))); stable exponential arithmetic. |
| Forward tail | Largest floor(N*tail_mass) score occurrences; mu=min(tail); lambda=1/mean(tail-mu). Every requested tail remains separate. |
| Forward E10 | N*tail_mass*exp_survival(x10); exp_survival=1 below mu, otherwise exp(-lambda*(x10-mu)). Native calibration E10 uses mass 1, as its origin is full-population. |
| Alignment | Mean and sample SD of original individual M+D+I counts, with SD denominator N-1. Rounded score-to-sample correspondence is checked at three-decimal precision. |
| Filter | Count under the declared numerical criterion, divided by N. Native counts/fractions remain separate from selected-criterion recalculation. |
| Residual | Recalculated quantity minus its original printed native quantity; neither is overwritten. |

Resolved parameters always retain `tail_masses,fixed_lambda,fit_tolerance,
solver_iteration_limit,rounding_tolerance,filter_criterion`. Defaults for the
**calculator** are fixed_lambda 0.693147, fit_tolerance 1e-10, numerical solver
limit 200 and absolute rounding tolerance 0.000051. None is an episode limit or
continuation rule. Forward tails may come only from supplied `tail_masses` or
the complete recorded `--tmin,--tmax,--tpoints,--tlinear` selection. Gumbel is a
complete-population fit, so non-full tail parameters are rejected. Missing tail
selection is explicit; no native default is guessed by either component.

Filter criterion is exactly `{threshold,meaning,comparison,fit_variant}`.
Meaning is `score|survival_probability`; comparison `<|<=|>|>=`; variants are
`independent|fixed_lambda|native_lambda|native_calibration`. Forward independent
survival is scaled by its selected tail mass. A numerical score threshold does
not require a fitted distribution. The actual native Viterbi/MSV criterion is
calibrated Gumbel survival `<=` recorded `--pthresh`; no threshold is guessed.
Forward native filtering is unavailable. Hybrid independently usable calibrated
location remains null/incompatible. Its actual native exponential filter can
be replayed separately using pmu0, explicitly labeled experimental/undetermined;
this never makes `native_calibration` an available selected fit variant.

Native calibration was computed by the original run, not copied from HMM
STATS. The full-precision pmu/plambda were not exported. Therefore reconstructed
calibration and native-lambda diagnostics explicitly use printed rounded
parameters. Their residual checks are unknown; native filter count agreement
can pass, while disagreement cannot prove an erroneous native run from rounded
parameters alone. Missing or ambiguous calibration is never replaced by a
refit of rounded summary values.

Easel's original Lawless stopping tolerance is 1e-5. Using the tighter default
1e-10 changes some E10s beyond four-decimal printing error, so those residuals
remain numeric with an unknown check and an explicit solver-tolerance
qualification. A second verification with fit_tolerance=1e-5 checks all 19
native fitted summaries at native precision. Changed fixed lambda likewise
does not claim to reproduce the original native setting.

## Verification and limits

The retained examples are the original workload259 bytes for 4 algorithms ×
4 styles plus 3 optimized local runs. They retain original receipts and exit
codes; no new simulation was run. Native ABI is explicitly declared little
endian IEEE754 binary64 from the retained build evidence, then checked against
textual scores and original fitted summaries. No host-endian inference occurs
in the parsers. Final M1 model records are decoded by the actual262 implementation.

The local_jobs verification receipts enforce 21474836480 bytes RAM,
4294967296 bytes scratch and no wall limit. They hash the two implementations,
tests, final M1 decoder, installed C sources, immutable objective/contracts,
retained native files and original native receipts before and after each run.
`check001` and `check002` retain failed development checks; their corrections
preserve native values and explicitly distinguish numerical tolerances.

Tests cover the original 19 cases, explicit ABI including synthetic big endian,
multi-model/duplicate-name identity, real mixed alphabets, unsupported settings,
wrong metadata, nonfinite/partial/missing/empty data, quantity domains, XY
segmentation, verbose scores, insufficient/constant/empty populations, failed
convergence, sample variance, tied x10, changed tails/slope/filter/tolerance,
JSON save/recalculation and forbidden file/subprocess/socket/Store sentinels.
The module import boundary excludes acquisition, execution and LLM services.

Multi-model, big-endian, malformed and Forward XY examples are synthetic
verification, not new native runs. No MPI ordering, unsupported fast+Hybrid or
fast+traceback behavior is claimed. Model formats unsupported by M1 remain
unresolved; there is no implicit model conversion. Input models with shared
seeds/backgrounds do not acquire an independence claim. No annotation score,
biological observation, execution receipt or local yield observation is created
by the parser/calculator. Complete child-owned execution and typed episode
communication remain unverified by this pure component.
