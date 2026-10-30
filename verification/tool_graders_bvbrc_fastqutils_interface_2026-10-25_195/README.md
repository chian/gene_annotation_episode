# Additive FastqUtils interface packet195

Contract-only work for **C-L209-FastqUtils::api**. The complete193 source packet
and its67 manifested files remain unchanged. No runtime/candidate/accounting or
authority file was written. All five recipe steps and all62 measurements/17
components remain in scope. This is not completed FastqUtils implementation.

Start with CONTRACT_002.md and SCHEMA_INVARIANTS_002.md. **SCHEMAS_004.json** is
the current complete schema. Frozen002 is preserved; SCHEMA_CORRECTIONS_003.md
documents the three native representation corrections, and
PROVIDER_CORRECTION_004.md documents required host return identity fields.
FROZEN_ASSETS_002.json records exact copied implementation-boundary hashes.

The immutable common, parser, calculator, provider and return signatures are
in PORTS_002.md. Exclusive A/B/C/root implementation ownership is in
WORKLOADS_002.md. METRIC_SPECS_002.json and COMPONENT_SPECS_002.json retain all
original numerical quantities; apply the small explicit
NUMERICAL_CORRECTIONS_003.json overrides without rewriting the originals.

Concrete fixtures and consumers:

| Asset | What it fixes |
|---|---|
| RESULT_SELECTOR_PRE_DOWNLOAD_002.json | Actual generic ResultSelector known before output hashes/record IDs exist |
| ARTIFACT_BUNDLE_AFTER_DOWNLOAD_002.json | Exact later requirement-to-acquired-byte binding, with current-version qualifications |
| POSSESSED_PARAMETERS_002.json | Exact already-possessed ContentBinding selection |
| ORIGINAL_TASK_002.json / SUPPLIED_VALUES_002.json | Existing submitted operands and source-pointer-materialized metadata ABI |
| EXPECTED_NATIVE_DOCUMENTS_002.json / EXPECTED_METADATA_002.json | Independent A/B native handoffs and C metadata handoff |
| EXPECTED_SHEET_002.json / EXPECTED_COMPONENTS_002.json | Separate retained measurements and explicit calculated components |
| EXPECTED_FACTS_002.json / EXPECTED_PROVIDER_RESULT_002.json | Exact requested numbers/absence, generic host failure fields and saved wrapper |
| UNAVAILABLE_SHEET_002.json / UNAVAILABLE_COMPONENTS_002.json | Unknown encoding leaves2 reads/10 bases and GC5/9; quality numbers unavailable |
| PARTIAL_NATIVE_DOCUMENT_002.json | One complete FASTQ prefix record with partial scope; no guessed second record |
| UNAVAILABLE_AND_PARTIAL_002.json |10 missing/value/cardinality/partial cases, including exact0 missing versus observed empty |
| ASSUMED_LINEAGE_*_002.json |8→6=.75 under the exact source-bound assumption, every stage execution still unknown |
| SOURCE_CUSTODY_AND_LINEAGE_002.json | Requested/asserted/native-observed distinctions and actual host versus pure responsibilities |
| IDENTITY_VECTORS_002.json / ERROR_SHAPES_002.json | Shared identity and concrete native/host error shapes |

All fixture files are explicitly handcrafted contract oracles. Numeric Hostile
semantics are grounded in193 source-executed synthetic receipts; these195 files
are not genuine service outputs, an authenticated runtime run or implemented
scientific parsers/calculators.

Run the contract checks without importing any runtime implementation:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 verification/tool_graders_bvbrc_fastqutils_interface_2026-10-25_195/check_contract_002.py
```

CONFORMANCE_RECEIPT_002.json records71 passing checks. Builders create schema/
oracle data only; frozen003/004 are explicit additive corrections to002, not
silently regenerated alternatives. The authority/reset, inspected sources,
terminal/preservation and complete artifact manifest receipts distinguish
reviewed evidence from execution. Native parser/calculator accuracy, original-
custody runtime tests, full episode communication and live-resource verification
remain the implementation workloads. Cutadapt, SAMstat, p3-sra metadata and
deployed native versions remain explicit unfinished source/format/resource work.
