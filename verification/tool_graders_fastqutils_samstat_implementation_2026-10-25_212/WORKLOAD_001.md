# SAMstat shared contracts and current-format parser

Fresh coding workload. Read the COMPLETE original authoritative goal at
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`
before work. Read AGENTS.md, the relevant current inventory row and the complete
207 revision002 contracts. Reread the objective and ALL 16 design principles
verbatim after substantial external/native examination and before translating
it into code, and before finishing. Do not substitute a paraphrase or upstream
design. The exact source/native contracts are sealed in 207.

## Work and ownership

Root explicitly designates this worker as the shared SAMstat integration owner
ONLY within `212/candidate`. Create that candidate by copying the exact 1101-file
208 source_before.json manifest and verifying every hash first. Root's separate
211 candidate handles SRA metadata; no other owner's files may be edited.

Implement 207 workloads A (shared finite schema/spec/dispatch/compatibility)
and C (2.5.0 HTML and the source-produced caller error HTML). Do not implement
the legacy parser or the mapping calculator in this assignment. Those modules
have the independent public ports in 207 and will receive fresh owners. Do not
claim their unavailable implementation works. No changes to method_loop,
execution decisions, scientific credit, root tools or production files.

Owned files inside this candidate:
- new bvbrc_fastqutils_samstat_specs.py: all59 precise native metrics and two
  component definitions from the reviewed field/enum contracts; ordinary
  description dictionaries only, no executable rule language;
- new bvbrc_fastqutils_samstat_native.py: version-aware dispatch and typed
  unsupported-version preservation; public parse_samstat_html(raw:bytes, *,
  context:dict)->dict;
- new bvbrc_fastqutils_samstat_svg.py: exact public parse_samstat_html_2_5_0 and
  parse_samstat_bvbrc_error_html signatures from207;
- existing schemas, metric_specs, contracts, native dispatcher, adapter dependency
  list and package-data configuration only for their necessary additions;
- new bvbrc_fastqutils_legacy_cutadapt_schemas.json is an EXACT byte copy of
  208's bvbrc_fastqutils_schemas.json. Preserve old198 legacy file unchanged;
- dedicated tests/fixtures and receipts under212, plus test files for current
  parser and shared SAMstat contract.

Do not modify resolution/calculator control flow yet: deliver the agreed new
CalculationRequest schema and component specs for their future owner. Preserve
existing public signatures and closed shapes; mirror finite enums faithfully.
Do not introduce a new NativeDocument/Cell format or permissive objects. Preserve
both exact earlier requested-form generations, rejecting mixed/weakened forms.
The SRA and SAMstat finite additions will later be merged by root from their
common exact208 baseline; send a file-level patch and explicit enum/spec manifest.

## Exact handoffs

Inputs and outputs are ParseContext and NativeDocument; all content bytes are
caller-supplied and bound. Use original207 NATIVE_FIELDS_002.json,
PARSER_CALCULATOR_PORTS_002.md including its final caller-error section,
ENUM_ADDITIONS_001.json and WORKLOADS_002.md without redefining populations.
Publish the precise completed shared-file manifest promptly so fresh legacy and
calculator owners can develop against it. Do not make them wait for current
parser completion if the common interfaces already work. Existing _Report can
be reused if its state semantics match; do not quietly invent a helper that
other owners must discover. If a new shared construction helper is necessary,
document its exact signature, mutations and return before handoff.

Report counts describe contributing records; no FASTQ/molecule/pair inference.
Original input scope remains unknown from closed HTML. MAPQ255 stays inside the
native high bin. Static SVG has no exact arrays: never reverse engineer geometry
or substitute optional JSON that the caller did not acquire. Preserve actual
native precision, missing values, errors and independent valid sections.

## Verification and boundaries

Implement the full current-format case list in207 workloadC, with genuine37
native HTML artifacts available read-only there. Copy only required fixtures
into212 and retain provenance/hashes. Add malformed/conflicting/truncated and
caller-failure cases, exact source-byte locations, compact selected numerical
outputs, old/current requested-form compatibility. Do not run a duplicate full
359-case suite now; scoped current/parser/contract checks suffice before root
composition. Run no live BV-BRC or Aurora operation. No global dependencies,
20 GiB RAM/4 GiB scratch, no wall-time cap. No parser I/O, network, subprocess,
LLM, HTML/JavaScript evaluation or extra episode observations.

Consumer chain remains native dispatcher -> metadata/sheet -> selected
calculation -> projection -> saved codec -> existing typed return. Code presence
and native parser tests are not a whole-tool or full episode-path pass. Send
exact completed/unimplemented files and native numerical examples in the final
handoff. Preserve every failed verification receipt and correct additively.
