# Proposed ownership, integration and verification

Status: boundary proposal only. No worker has authorization from this document
to begin implementation. Root reviews/accepts the scientific formulas and
freezes exact serialized interfaces before assigning code. The original
checklist rows remain unchanged; neither application is marked complete.

## Schema owner and what is ready

Root is the single **schema freeze and shared integration owner**. Native
measurements/formulas, their actual source distinctions, host adapter signature
and the proposed concrete values are separable decisions. `PROPOSED_CONTRACT.md`
records scientific meanings; `INTERFACE_VALUES.md` proposes serialized parser,
association, count, statistical and adapter records. Neither document claims
root has accepted every choice merely because a source uses it.

Before coding across boundaries, root records exact accepted record keys/types,
enum values, method IDs and version constants in one additive freeze record.
The following still need that decision and must not be independently invented:

1. Final top-level sheet collections and how untouched shared calculator output
   is embedded beside tool-owned numeric cells. `NumericCell` and existing
   phylogeny `quantity` differ intentionally; workers must not silently convert.
2. Exact literal calculation-request record variants and `ReaderSpec` union
   schema. `INTERFACE_VALUES.md` supplies the underlying records and signatures;
   root or the assigned bundle-contract owner expands those into one exact
   closed parameter schema, with no generic expression evaluation.
3. Requested projection selector schema, each emitted array-row shape, source
   names, reference namespaces and identifier encoding. The proposed families
   are in section 8, but they are not an accepted prompt/return template.
4. Final host conversion of tool-owned requirements/diagnostics, including a
   source-failed/no-usable-fact case. Preserve host `failed` and existing phases;
   don't change `bvbrc_appservice_schemas.json` for these tools.
5. How `GroupColumnBinding` records actual R group-token order, metadata ordinals
   and erroneous exporter labels after root's separate native-R examination.
6. Numerical chi-square-tail dependency, version identity, stable log-tail and
   underflow behavior, plus explicit source-compatible vs standard-pair df
   method IDs. Root's controlled native execution can supply evidence, not
   silently choose a scientific policy for the caller.
7. XMFA coordinate record conversion after exact native examples/specification
   are acquired. Lexical token retention can proceed independently; coordinate
   math and complete multi-block claims cannot be guessed.

The proposed `BoundInvocation`, input occurrence, group expansion/header,
transformation, segment, group-column and parser/count/result records are
concrete in `INTERFACE_VALUES.md`; any root revision must be propagated to both
producer and consumer workload assignments. Pure source research for unresolved
formats, or obtaining exact native examples, does not need to wait for this
serialization freeze. It must stay within separately assigned output directories.

## Exclusive future file ownership

All paths below are proposals under `gene_annotation_episode/`; no files at
these paths were created or edited by this boundary task. Root should grant
each named file to one workload and avoid concurrent edits to shared consumers.

| Workload | Exclusive new files | Inputs and outputs crossing ownership |
| --- | --- | --- |
| A: MSA native readers, associations and calculations | `bvbrc_msa_contracts.py`, `bvbrc_msa_formats.py`, `bvbrc_msa_metadata.py`, `bvbrc_msa_calculators.py`, `bvbrc_msa_sheet.py`; later `xmfa_formats.py` only after explicit format freeze | Input: Artifact, exact supplied bytes, existing AlignmentDocument/Population, frozen InputMember/TransformationMap/ReferenceBinding/SegmentJoin. Output: MSAFrequencyTable, MSAInputAssociations, MSASheet, MSAEntropyComponents, MSAReferenceComponents. Calls existing shared pure readers/math for proven equal meanings; never edits them casually. |
| B: MetaCATS native readers, associations and calculations | `bvbrc_metacats_contracts.py`, `bvbrc_metacats_formats.py`, `bvbrc_metacats_metadata.py`, `bvbrc_metacats_calculators.py`, `bvbrc_metacats_sheet.py` | Input: Artifact/bytes, AlignmentDocument/Population, frozen group/member/column bindings, category/test-family parameters and explicit numerical kernel. Output: current/legacy parsed tables, GroupMetadataDocument, MetaCATSInputAssociations, GroupCountComponents, MetaCATSStatistics/Effects/Multiplicity and populated sheet. Does not own MSA calculations or alter native observations to match a preferred formula. |
| C: exact bundle binding and projection | `bvbrc_alignment_bundle_contracts.py`, `bvbrc_alignment_bundle_projection.py`, `bvbrc_msa_bundle_adapter.py`, `bvbrc_metacats_bundle_adapter.py` | Input: existing acquired bundle, exact `artifact_bytes`, host `supplied_values` list, original requested form/parameters, frozen A/B values. Output: existing eight-field pure AdapterResult; saved full sheet/components plus requested facts. Owns adapters' implementation digests and provider-specific closed selector validation; no network or custody implementation. |
| D: root-owned installed host/library/return integration | New `bvbrc_alignment_returns.py`, `bvbrc_alignment_tool_info.py`; edits only to the exact existing consumers listed below, after ongoing phylogeny integration finishes | Input: bound adapter IDs/version/digests, saved publications, accepted finite return schema and source meanings. Output: selectable existing commission routes and authenticated own/received facts with original requested relationships. Does not recalculate in parent readers or add model calls/actions. |

A and B can proceed independently after their shared read-only input contracts
are frozen. C can first implement closed schemas/projection selection against
the accepted values without waiting for every native format to become available;
it must preserve missing requirements for unfinished modes. D owns all shared
host edits and should wait for the active phylogeny work to settle. Do not split
one shared bundle-contract file between parallel workers. No work removes a
fixed-scope mode merely because its artifact, version or resource is missing.

Suggested future test ownership mirrors A/B/C/D with separate test files;
no test files were created in this boundary-only assignment. Native examples
and arithmetic receipts here are reusable evidence with their stated limits,
not proof that future tests already passed.

## Complete actual consuming path inspected

The following traces name current concrete consumers, not an invented new
workflow. Relevant complete function bodies and their producer/consumer
contracts were inspected; source identities are in `READ_IDENTITIES.json`
and `ADDITIONAL_READ_IDENTITIES.json`. Concurrent root work can change them,
so D must recheck current files before editing. No episode prompt is changed by
this proposal; concrete tool information needs the TASK/STEERING review and
user feedback required by the repository instructions.

1. **Selection and tool information.**
   `BVBRCAppServiceService.__init__` in `api_bvbrc_appservice.py` calls
   `bvbrc_appservice_adapters.bind_adapters`. The registry currently installs
   homology/GeneTree/CodonTree modules and checks each configured implementation
   digest. Add only explicitly configured `(bvbrc_msa,'1')` and
   `(bvbrc_metacats,'1')` after their adapters exist. An uninstalled source
   description does not become callable.

   `ExecutionEpisodes.resource_tool_contracts` currently adds separate homology
   and phylogeny scientific operation information only when their adapters are
   bound. D adds the two analogous limited provider entries through
   `alignment_tool_contracts(resource_id, assignment_schema, provider)` in the
   new tool-info file. Each entry has name, description, resources, substantive
   instructions, actual input schema and existing commission routes:
   launch → `launch_api`; results → `results`.

   The actual consumers are
   `resource_tool_information.bound_resource_tool_contracts`,
   `resource_tool_information.tool_information_contracts`,
   `WorkflowServices.tool_information_catalog` in `episode_services.py`, and
   `ExecutionServiceFactory.__call__` in `execution_service_setup.py`.
   These already expose bound resource operations without a root direct
   scientific tool. No new layer, role, prescribed child order or direct tool
   registration is needed. Information must describe actual supported formats,
   group/input requirements and API-only deployment evidence without implying
   local scientific deployment or live service verification.

2. **Original request and selected execution.**
   `bvbrc_application_definitions._check_application_inputs` and the existing
   preparation function validate the original packaged application definitions.
   Their MSA aligned-type mismatch is not repaired by inventing a parameter.
   `BVBRCAppServiceService.result_catalog` calls the selected adapter's
   `validate_parameters` and `validate_requested_form`. Keep their actual
   signatures: the second receives only the form, with cross-parameter
   relationship checking at consumption as needed.

   `APIServiceExecution.execute` / `_execute_locked` delegate AppService work
   to `BVBRCAppServiceHost.execute_locked`. That complete function binds original
   inputs, calls `service.prepare`, validates selected acquisition dependencies,
   retains the immutable intent, executes exactly the selected call, retains
   snapshot/effect receipts and decodes it. AppService native submission remains
   `start_app2`; preparation, upload, status, metadata, capabilities and download
   remain separately selected existing operations. No automatic service job,
   group refresh, aligner rerun or retry is introduced by parsing requirements.

3. **Acquisition and pure adapter invocation.**
   `bvbrc_appservice_bundle_values.build_acquisition_value` validates actual
   output metadata/body records, original request/task and selection evidence.
   `build_artifact_bundle` associates selected requirement IDs with actual
   acquisition receipts and explicit original input bindings. Preserve task,
   Workspace UUID/path, body digests, native representations and partial states.
   Supplemental original alignment/metadata must use authenticated
   `supplied_contents`; nested source-ID claims do not authenticate bytes.

   `AppServicePublications.validate_selected_inputs`, `publication_inputs`,
   `_validate_inputs`, `_bundle` and `_grade` in `bvbrc_appservice_publication.py`
   already provide the custody-to-pure boundary. `_grade` supplies
   `artifact_bytes={raw_artifact_ref:bytes,...}` and
   `supplied_values=[{evidence,value},...]`, plus the original selector's
   `requested_schema` and adapter parameters. C dispatches only declared format
   readers and selected calculators; it never guesses the newest matching file.

4. **Durable publication and recovery.**
   `_grade` stores the actual whole sheet/components and selected fact values.
   `_requested_status` validates those facts against the original requested
   schema. `AppServicePublications.publish` runs inside that same completed
   download action, saving the scientific adapter result. `read` and
   `read_content_source` authenticate retained dependencies/content. Recovery
   uses saved scientific results instead of recalculating from mutable metadata.
   C must preserve failed/partial distinctions accepted by the existing schema.
   Missing input is not scientific absence; byte acquisition can remain valid
   even when a dependent statistic cannot be interpreted.

5. **Own results and both directions of handoff.**
   `BVBRCAppServiceHost.facts` currently merges support receipts, homology facts
   and phylogeny facts; D adds the new return owner. `APIServiceExecution.__init__`
   constructs it and `APIServiceExecution.resolve` dispatches its namespaces.
   The new owner follows the actual responsibility of `BVBRCPhylogenyReturns`:
   `facts`, `_latest`, `_attempt`, `_validate_values`, `received_context`,
   `received_facts`, `validate_received_report`, `record_admission`,
   `resolve_own`, `resolve_received`. Its identity checks mirror the necessary
   relationships examined in `_SavedIdentities` and `_saved_facts`, but operate
   on the new sheet schema. They validate saved selections, member/group/test
   identities and denominators; they do not recalculate scientific values.

   The complete integration sites in `ExecutionEpisodes` are
   `_appservice_sources`, `fact_sources`, `received_report_sources`,
   `received_report_facts`, `resolve_received_reference`,
   `validate_received_report`, `received_form_references` and `resolve`.
   Its `facts` and `validate_report` already enforce actual recorded own results;
   confirm the new owner is reached through the API facts path. Each nested
   parent sees only the originally requested typed values, validated against
   the received child form and saved publication, not a re-created wider sheet.

6. **Credit and continuation.**
   The existing selected acquisition/publication remains one completed own
   action. Pure parsing/calculation, return construction, replay and admission
   do not create synthetic observations. This task changes no W05 annotation
   aggregation, practical completion policy, estimator/controller, monitoring
   cadence, prompt construction or inherited-credit accounting. Integration
   verification must inspect the original selected action through its actual
   persisted return; tests of a standalone parser do not establish that path.

## Meaningful future verification cases

These are proposed checks, not a claim of current test execution.

| Boundary | Case and required observation |
| --- | --- |
| Shared vs native entropy | Use retained DNA four-row native example: column 2 native n=3, A=2, deletion=1, Score=92; literal H=0.9182958340544896 but canonical H=0 and whole-matrix gap fraction=2/4. Ensure subset selection preserves original terminal bounds. |
| Protein native table | Retained native protein column 4 has Del=2/Gly=2, n=4, Score=100, Xaa consensus. Preserve three-letter tokens, tie semantics and literal-vs-canonical entropy. Exercise an unknown protein letter without dropping it from actual alignment counts. |
| Native gaps and failures | Execute complete unchanged helper on all-gap rows, all-gap first columns, empty alignments and partially missing segments. Record actual emitted files/exit status; no infinite-loop assertion follows from the isolated Perl bound check. |
| Native precision and blanks | Blank globally absent symbol cells, literal ambiguity counts not represented in DNA table, NA/nonfinite/underflow numeric tokens and rounded Score boundaries. Preserve source token and independent recalculation. |
| Reference and member identity | Requested reference differs from first final row; duplicate original labels; duplicate generated-label mapping; missing original lengths; translated rows without codon map. Retain native columns but withhold unsupported original identity/coverage. |
| Genome/segment/Mauve populations | First-contig source record; lexical segment order; duplicates/suffixes; gap-padded missing locus; filtered row/report count difference; multi-block XMFA vs first-block `.afa`. No genome coverage or full XMFA correspondence from a projection alone. |
| MetaCATS complete population | Official 14×765 input joins 8/6 groups and yields 312 variable tests under inspected source arithmetic. At site 28 A8 vs C6, augmented X²=13.995751481999479, df=3, p=0.0029109414412902606; Bonferroni=0.9082137296825613 and BH=0.007397967443134484 over the declared 312-test family. Root's later R 4.3.3 native run confirms the unadjusted values within output precision and returns 143 omnibus/143 pair rows; corrections remain separately calculated. |
| Native current/legacy formats | Parse current exported headers and separate retained legacy example. Legacy `14*` is not silently accepted as a current native position/method. Do not infer its matching input by row count. |
| Selection filtering | Native cutoff uses strict `<`: equality must not be emitted. Complete zero-row TSV is not a zero-test population. Significant-only input cannot produce BH/Holm/BY; Bonferroni exception requires independently known m or explicit bound assumption. |
| Group join | Duplicate metadata IDs; metadata-only groups; missing metadata creating Unlabeled; basename collisions; commas in group labels; >=10 group ordinal formatting; R positional group labels that differ from original metadata ordinal. Root demonstrated metadata-only group mislabeling, but its 12-group case retained numeric order through padded character tokens. Preserve actual R tokens/column identity and any erroneous displayed label independently. |
| Statistical modes | NA ACGT zero-row padding; AA no alphabet padding; 2×2 omnibus R continuity; pair no continuity; >=3-group AA native df=(K-1)(R-1) versus explicitly selected standard pair df=R-1; no relabeling between results. |
| Pseudocount and adequacy | Raw counts remain integers; augmented counts add exactly selected epsilon per cell. Native Fewer_5 tests positive observed counts, independently of minimum/number of expected cells below 5/1. Preserve augmented sample total separately from true member count. |
| Empty/conserved sites | All `#` skip; one-symbol native placeholder and degenerate pair calls. Preserve tested, skipped and placeholder populations; do not count every alignment column as a fitted omnibus test. |
| Underflow | Tiny chi-square tails retain log tail and finite-decimal/native tokens; source's pair zero-to-one conversion never overwrites mathematical p. Native printed 1 is not automatically diagnosed as underflow without supporting calculation/runtime evidence. |
| Correction/dependence | Ties, missing p, explicit m bound, multiple categories, omnibus vs pair families, shared/identical sequences and overlapping locus/concat representations. No arbitrary deduplication/reweighting or count estimate from significant rows. |
| Offline purity | Deny network/subprocess/filesystem acquisition during parsers/calculators; same saved bytes/metadata/params reproduce components. Changed calculation params yield separately identified new results without overwriting old observations. |
| Real adapter/publication path | Original selected download receives task-bound bytes and exact supplied original input. Persisted full sheets/components and requested facts validate. Wrong task, metadata source, analysis/slot, group column, test family or member join fails specifically while independent partial rows survive. |
| Recursive return/recovery | Read saved facts through results → scientific child → scientific parent with exact original schemas and verified reference identities. Reopen/recover without recalculation or acquisition. Duplicate delivery yields no new observation; requested numerical facts are visible to the responsible episode. |
| Installed library | Preserve the three construction slots: evidence_axis, thought_pattern and child_tool_info. Bound child_tool_info has the four required fields name, description, resources and instructions, plus the actual callable contract/commission routes. An unbound adapter stays unavailable; root direct scientific tool catalog is unchanged. Confirm installed package module/data files, not only source-tree imports. |

## Work still required after this handoff

Known-byte readers, pure math and proposed source contracts can be implemented
after root review. Live authenticated service definitions, deployed versions,
original task receipts and actual service artifacts remain separate unfinished
requirements. Prealigned MSA invocation declaration, full XMFA coordinate
evidence, original transformation/member maps, resolved mutable group expansion
and native statistical runtime/order examples remain explicit dependencies.
Root's separate private R experiment is outside this directory/ownership; its
new receipts can extend evidence without rewriting the historical finding that
Rscript was absent from the PATH inspected during this review. Local native
execution would still not establish a deployed BV-BRC AppService capability.
