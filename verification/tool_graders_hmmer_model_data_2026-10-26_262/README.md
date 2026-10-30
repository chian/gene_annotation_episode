# Workload 262: shared HMMER model data, frozen 261/M1 handoff

This component implements the two pure ports assigned by
`verification/tool_graders_hmmer_preparation_2026-10-26_261/MODEL_DATA_CONTRACT_001.md`.
It supplies model data to separate hmmbuild, hmmconvert, hmmemit, hmmfetch,
hmmpress, hmmsim and hmmstat sheets. It does not declare any whole tool,
production binding, episode communication or fixed inventory row complete.
No execution, registry, Infernal, annotation-credit or accounting source changed.

## Ports and concrete shapes

```python
from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_model_calculations import calculate_hmmer_model_components

extraction = extract_hmmer_models(content, occurrence=occurrence, format="hmmer3_ascii")
components = calculate_hmmer_model_components(
    extraction, background=explicit_symbol_probability_map, probability_tolerance=1e-4)
```

`content` is supplied bytes. The caller acquires and retains them; neither port
reads a file, consults a Store, uses the network, launches native work or an LLM.
`format` is explicitly `hmmer3_ascii`, `hmmer2_ascii` or `hmmer_binary`.

The occurrence has exactly these fields:

```text
{
  occurrence_id: nonempty string, direction: "input" | "output",
  role: nonempty string, ordinal: nonnegative integer,
  artifact_ref: nonempty string, sha256: 64 hexadecimal characters,
  size_bytes: nonnegative integer, completeness: "complete" | "partial" | "unknown"
}
```

It is copied unchanged. Digest and size are checked against supplied bytes.
Mismatch preserves decoded data but makes the population invalid. Identical
bytes supplied as different occurrences retain distinct record keys.

The extraction envelope has exactly `schema`, `occurrence`, `format`, `records`,
`population`, `issues`; schema is `hmmer_model_extraction_v1`.

```text
population = {decoded_count: integer | null, complete: boolean,
              state: "decoded" | "partial" | "unsupported" | "invalid"}

record = {
  record_key: occurrence_id + "#model/" + zero_based_record_ordinal,
  locator: {artifact_ref, record_ordinal, byte_start, byte_end, line_start, line_end},
  format_tag: actual "HMMER3/a" ... "HMMER3/f",
  engine_text: complete native remainder of signature line, including brackets, or null,
  headers: [{tag: string, value: string, tokens: [string, ...], line: integer}, ...],
  alphabet: {kind: "amino" | "DNA" | "RNA" | invalid native string | null,
             symbols: [actual HMM header symbols in original order]},
  length: integer | null,
  sequence_count: integer | null,
  effective_sequence_count: number | null,
  maximum_length: integer | null,
  checksum: integer | null,
  flags: {declared RF/MM/CONS/CS/MAP: boolean | null},
  cutoffs: {declared GA/TC/NC: {
    tokens: [string, ...], values: [number | null, ...],
    sequence: number | null, domain: number | null, domain_supplied: boolean,
    line: integer, unit: "bit"}},
  calibration: [{mode: native string | null, statistic: native string | null,
    tokens: [all STATS value tokens], parameters: [
      {name: "mu" | "tau" | "lambda" | null, token: string,
       value: number | null, unit: "bit" | "inverse_bit" | null}], line: integer}],
  composition: distribution | null,
  initial: {insert: distribution | null, transitions: distribution | null},
  positions: [{position: positive native integer | null, position_token: string,
    line: integer, match: distribution, insert: distribution | null,
    transitions: distribution | null,
    annotations: {revision-present MAP/CONS/RF/MM/CS: {token: string, value: integer | string | null}},
    extra_tokens: [unrecognized trailing annotation tokens]}],
  terminated: boolean, issues: [issue, ...]
}

distribution = {symbols: [string, ...], cells: [cell, ...], line: integer}
cell = {token: string, negative_log_probability: number | null,
        probability: number | null,
        state: "finite" | "structural_zero" | "underflow" | "invalid"}
```

Byte intervals are zero-based and half-open; line intervals are one-based and
inclusive. Model positions and MAP coordinates retain native one-based values.
No NAME, ACC or DESC convenience identity is synthesized: consumers use the
ordered corresponding header records and preserve duplicate-header ambiguity.
An invalid or duplicate numeric header gives a null canonical scalar plus an
explicit issue and its original header tokens. Optional missing headers remain
missing. Unknown headers and repeated COM lines are retained in order.

`decoded_count` counts returned model records, including explicitly partial
records. It is not a count of valid or complete models. A complete prefix model
remains available when a later record fails. Missing rows are null, short rows
retain only present cells, and missing positions are never padded. A fully
decoded record containing an underflow token has complete native data but an
unavailable numerical probability, so underflow alone does not change population
completeness. HMMER2/binary yield `decoded_count=null`, state `unsupported`, and
`decoder_unavailable`; explicitly empty HMMER3 ASCII yields zero decoded records.

Revision rules follow the native writer/reader:

| Revision | Position annotations | Calibration | MAXL |
| --- | --- | --- | --- |
| 3/a | MAP, RF, CS | VLAMBDA, VMU, FTAU; one supplied value each | absent |
| 3/b | MAP, RF, CS | MSV, VITERBI, FORWARD location/scale pairs | absent |
| 3/c, 3/d | MAP, RF, CS | modern pairs | optional |
| 3/e | MAP, CONS, RF, CS | modern pairs | optional |
| 3/f | MAP, CONS, RF, MM, CS | modern pairs | optional |

Legacy 3/a VMU remains VMU; no modern statistic is invented. In the annotated
fixture it is -5.908600, the source MSV location; modern VITERBI is -6.1309.
Protein cutoffs contain sequence/domain values; the retained RNA GA has only
sequence value 10.10 and `domain_supplied=false`. Missing domain values are not
copied from sequence values. MAXL is a native target-window upper bound in
alphabet residues/nucleotides, not annotation support. Checksum is the native
unsigned 32-bit quantity, not an identity key or confidence value.

The calculator envelope has exactly `schema`, `parameters`, `rows`, `checks`,
`issues`; schema is `hmmer_model_components_v1`. Parameters retain the exact
supplied background and tolerance without inserting a native default.

```text
component = {value: number | null,
             state: "present" | "missing" | "incomplete" | "incompatible" | "nonfinite",
             unit: string, inputs: [specific operand dictionaries]}
mass_components = {mass: component, mass_residual: component}
transition_components = {M: mass_components, I: mass_components, D: mass_components}

row = {
  record_key, alphabet,
  composition: mass_components,
  initial: {insert: mass_components, transitions: transition_components},
  positions: [{position, position_ordinal, match: mass_components,
    insert: mass_components, transitions: transition_components,
    entropy: component, relative_entropy: component}],
  sequence_count: component, effective_sequence_count: component,
  effective_sequence_ratio: component,
  declared_length: component, match_state_count: component,
  mean_match_entropy: component, mean_match_relative_entropy: component
}
```

The count named `match_state_count` is explicitly the number of decoded match
rows, with unit `decoded_match_row_count`. `declared_length` preserves native
LENG independently. Thus a four-position prefix of a declared 12-position model
retains counts 4 and 12, and no partial mean masquerades as a whole-model mean.
Complete prefix models retain their numerical means even if artifact acquisition
was partial. Saved record keys, artifact references and locator bounds are
validated. An incompatible identity or alphabet produces an explicit
`record_invalid` issue instead of a fabricated calculable row.

Every numerical operand identifies record key, native position, zero-based
position-array ordinal, distribution field, cell indices and symbols where
relevant. Count ratios identify numerator and denominator. Background and
tolerance references are explicit parameter operands. Missing, invalid native
counts and zero denominators remain different states.

## Numerical meaning

| Component | Formula and population | Unit / missing behavior |
| --- | --- | --- |
| Cell probability | exp(-native token), no normalization | Probability; `*` is native zero, finite-log underflow is unavailable |
| Emission mass | Sum all alphabet cells of that one composition/insert/match distribution | Probability mass; any missing/invalid operand stays unavailable |
| Transition mass | Sum MM/MI/MD for M, IM/II for I, DM/DD for D, separately at each native node | Probability mass; a complete outgoing group can survive another truncated group |
| Residual | Mass minus 1 | Probability mass, preserving native rounding residual |
| Entropy | -sum p log2(p), all symbols at one match position | Bits; zero terms contribute 0 |
| Relative entropy | sum p log2(p/q), same position against explicit compatible q | Bits; missing q stays missing; positive p with q=0 is nonfinite |
| Mean match quantities | Sum the per-position quantity / native LENG, requiring every declared match position in a terminated record | Bits per match position; incomplete populations give no partial mean |
| Sequence counts | Native NSEQ/EFFN header values | Input sequence count / effective sequence count |
| Effective/input ratio | EFFN / NSEQ, with NSEQ explicitly the denominator | Effective sequences per input sequence; absent/invalid/zero denominator distinguished |

Background values must be finite probabilities matching the exact alphabet and
sum to 1 within the supplied tolerance. Tolerance changes pass/fail checks and
background compatibility; it never normalizes either native probabilities or
background. No uncertainty is invented; these formulas operate on the precision
of the retained rounded native tokens. Underflow and malformed cells never
contribute artificial zero. There is no combined confidence score.

Checks have closed `code`, `state` (`pass/fail/unknown/not_applicable`), affected
record/position/field and inputs. Issues have a closed code set declared in each
module, stage `extraction` or `calculation`, record/position/field, and specific
details; extraction issues also give a line when available. Record-local
extraction issues are repeated in the envelope for inspection, not counted as
observations or credit.

## Concrete examples and verification

The full examples are in `examples002/examples/`; `provenance.json` includes
every fixture's exact bytes hash, native argv, executable hash, original receipt
hash, selected input hash and bounded native policy. Every full array is retained
in its extraction JSON. Calculation JSON files contain every per-position result.
`summary.json` includes independent 60-digit Decimal expectations, not merely
assertions based on the production calculator.

Protein example: LENG 12, NSEQ 3, EFFN 3, ratio 1. Position 5 preserves F token
0.40547 and Y token 1.09861. Their decoded probabilities are 0.6666634054134197 and
0.3333340962235762, mass 0.999997501636996, residual -0.000002498363004033166.
Entropy is 0.9182987398592106 bits and KL against explicit uniform amino background
is 3.4036185572828934 bits. Mean match entropy is 0.07652489498826755 bits/position;
mean KL is 4.24540230008699 bits/position. Initial transition masses are
M: 1, I: 0.9999971805639198, D: 0.9999971805639198.

Recalculation changes q(F)=q(Y)=0.1 and other symbols to 0.8/18: position 5 KL
becomes 2.403621055645897 bits while entropy and original probabilities remain
unchanged. Tightening tolerance from 1e-4 to 1e-8 changes failed mass checks from 0
to 40; the raw residuals remain unchanged. Both DNA and RNA examples have
mean match entropy 0.9925134248800135 and uniform-background KL 1.0074921672642938
bits/position, native MAXL 73. These are native outputs from synthetic supplied
alignments and illustrative cutoffs, not observed biological evidence.

The final owned test run `check004/receipt.json` passed 85 tests in 0.49s through
`local_jobs.run_local_job`: memory 21474836480 bytes, scratch 4294967296 bytes,
wall_seconds=null. Enforcement receipt confirms cgroup memory/swap limits,
no wall deadline and monitored scratch. `examples002/receipt.json` records the
bounded example-generation run. Earlier receipts remain historical facts.

Tests cover full protein/DNA/RNA bodies; native annotated conversions 3a--f;
native single-matrix COM/count headers; cutoff and calibration distinctions;
all probability arrays, transition groups and numerical values; missing optional
headers; identical bytes and duplicate names; multiple records; structural zeros;
underflow; malformed numbers; partial rows and trailing records; subsequent valid
records after a truncated one; alphabet mismatch; size/digest mismatch; explicit
unsupported HMMER2/binary; saved references and token/log consistency; changed
background/tolerance; and forbidden file/network/subprocess sentinels during
extraction and saved-sheet recalculation.

Authoritative format source inspected in full: `p7_hmmfile.c` WriteASCII and
read_asc30hmm paths, SHA256
`9f664f5878e7fd60aa1a5b028b2bb605327bf26df19fe2268ad60a963ef5d090`.
Native protein model SHA256
`f744b16d69df05ddf8239af3bc4a68d36a6e2764f31ad1b8274507e958056ea5`;
DNA `c75e9e7e1da3f9d609e768634493e0ee13ea48cd532025610c2aa7d2f6964cab`;
RNA `a8577c5ed8817b99e130f53e7098d8d921cb59d04cac701fa1f9e42ca2f87d56`.
Implementation and test hashes are in the final test receipt and example manifest.

## Limits and consumer handoff

HMMER2 and binary decoders remain unavailable in this component. Their required
tool modes remain in overall scope; a separately selected conversion may provide
an independently identified ASCII artifact, but this parser never invokes one.
This component does not provide hmmstat-specific occupancy/profile-relative
entropy or composition-divergence calculations, tool-specific preparation sheets,
execution binding, typed result return or episode-path verification. Root owns
those separate consumers. Workload 263 can join the exact model header/locator
shape for its hmmsim data; its integration receipt is its own responsibility.

All native executions were performed and retained by workload 259, then reused
here. Workload 262 ran pure parser/calculator verification and example generation
under the existing bounded local adapter; it launched no new native HMMER job,
database BLAST, installation, remote job or credential action. An initial direct
verification launcher invocation lacked the repository import path and failed
before testing; the runner now resolves its repository path explicitly. It
neither creates an episode nor manufactures execution/scientific/yield credit.

The complete immutable goal/all 16 principles were read verbatim before coding,
after substantial native/source examination and before handoff; the exact 261/M1
contract was reread. Those reads are implementation discipline, not deployed
runtime gates or actions.
