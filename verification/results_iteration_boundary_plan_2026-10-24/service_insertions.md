# Filled service insertions for the common results draft

These are **planning examples**, not newly dispatched model prompts. The common
TASK/STEERING template supplies the shared iterative instructions; each insertion
below supplies actual acquisition/format semantics and concrete values. Existing
successful endpoints would close before another model call. Their post-acquisition
values are printed here for review, not evidence of an extra completion turn.
No new network request, native execution or grader calculation was run.

## A. Sealed native HMMER: actual retained hmmscan fixture

Opening task:

> Obtain the requested protein-domain rows from the original hmmscan search of
> the supplied protein sequence against its supplied pressed profile database.
> Acquire the complete original sealed bundle and its selected input/output
> files. Return the requested numerical rows and validated acquisition completion.

| Assigned item | Filled value and meaning |
| --- | --- |
| Program/mode | hmmscan / search |
| Acquisition | complete_bound_bundle |
| Projection family | protein_domain |
| Rows | Native order, offset 0, limit 50; no ranking or E-value filter |
| Requested metrics | paired_positions; paired_model_coverage; native_domain_score_bits; native_independent_evalue; sequence_identity_fraction |
| Actual result operations | `execution.results.status({})`; `execution.results.collect({})` |
| Raw retention | Original manifest, all selected original inputs, stdout/stderr, tblout/domtblout and any other explicitly selected output; each whole file matched to its original manifest |
| Return | `rows`: the existing `execution_hmmer_domain_rows` closed array; `completed`: existing boolean `execution_completed` |

Full acquisition insertion:

> `execution.results.collect` observes the original handed-off attempt once,
> captures its sealed original bundle and complete files, populates retained
> numerical sheets with deterministic readers, and publishes exactly the rows
> and metrics selected above. It takes no new query, database, threshold, file
> choice or retry argument. `execution.results.status` observes only the original
> attempt; it does not acquire numerical results. Select either only when useful.
>
> The host checks the original attempt, requested job, executable/input identity,
> declared artifact roles and each complete file. Captured mismatched bytes remain
> retained with failed custody and cannot be relabelled original output. Missing
> or unsealed artifacts remain unavailable. This path is not a current-filesystem
> preview and does not use `execution.results.read`.
>
> In hmmscan, the model axis is the hit profile and the sequence axis is the
> query protein. Native sequence and domain scores, E-values, bias, alignment
> coordinates, reporting/inclusion state and posterior bins retain their own
> meanings. Model-span coverage differs from paired-model coverage when gaps
> occur. A profile consensus is not an observed reference-protein sequence;
> missing actual sequence operands leave sequence identity unavailable. Preserve
> query/target occurrences and native iteration relationships. A complete valid
> no-hit search is distinct from a missing or malformed table.
>
> Completion requires complete original capture, successful original native
> outcome and valid requested numerical processing. An unavailable metric with
> an allowed missing-input qualification is not an invented zero. A mismatched
> biological binding makes that row invalid while valid siblings remain usable.
> Acquisition does not repair a frozen input binding or rerun a search. Preserve
> the affected row and exact failure if no permitted repair operation exists.

Requested metric meanings, filled:

| Field | Meaning/source | Unit / denominator | Missingness |
| --- | --- | --- | --- |
| paired_positions | Alignment columns containing both a model position and sequence residue, from retained display | paired positions; count | Unavailable if corresponding display/axis cannot be established |
| paired_model_coverage | Paired positions divided by actual full model length | fraction; model length | Missing denominator stays missing |
| native_domain_score_bits | Native domain bit score | bits; no invented confidence denominator | Native missing/invalid stays qualified |
| native_independent_evalue | Native independent domain E-value | expected-count statistic under native search conditions | Printed zero remains zero |
| sequence_identity_fraction | Identity using actual supplied sequence operands, as defined by the existing calculator | fraction; corresponding paired sequence positions | Profile consensus alone cannot establish it |

Actual retained selected row, from the existing successful integration receipt:

| Original locator | Field | Value | Qualification |
| --- | --- | --- | --- |
| domains.tbl line 4; query occurrence 0; target occurrence 0; iteration 1 | paired_positions | 20 | published |
| Same domain | paired_model_coverage | 1.0 | model denominator 20 positions in the retained input/score |
| Same domain | native_domain_score_bits | 72.1 bits | native domain score |
| Same domain | native_independent_evalue | 1.1e-24 | native independent E-value |
| Same domain | sequence_identity_fraction | unavailable | missing_input; not zero |

The receipt has `complete=true` and no failures. This is a small synthetic
sequence fixture executed by native HMMER, not biological annotation evidence
about the user's target. It illustrates that a legitimate missing identity
measurement does not automatically invalidate every numerical result.

The existing invalid-binding fixture instead retains a domain with 72.1 bits and
4.3e-24 independent E-value as **invalid** because its supplied biological subject
fails sequence matching; a sibling with 70.8 bits and 1.1e-23 remains published.
Its acquisition endpoint is false. The displayed measurement must retain that
invalid-binding qualification rather than treating all parsed numbers as
qualified target observations.

Other sealed HMMER families fill the same template from their actual descriptor:

* `hmmsearch`: model is query profile, sequence is database target.
* `jackhmmer`: all stdout rounds remain retained; final tables and checkpoints
  keep their distinct round roles. Convergence is not an episode stopping rule.
* `nhmmer`: sequence/profile/alignment query mode stays explicit. Native table
  length means target-sequence length; minus-strand coordinate direction remains.
* `nhmmscan`: table length means hit-model length; query length is the separate
  sequence-coverage denominator. The retained fixture has plus and minus loci,
  both with 100 paired positions, paired-model coverage 1.0, sequence-span
  coverage 0.8333333333333334, score 120.9 bits and E-value 2e-39.
* `hmmalign`: Stockholm/RF/PP and original annotations remain complete. The
  retained second sequence has original length 25, model length 20, 18 match-state
  residues, zero trimmed residues, model occupancy 0.9 and sequence-match
  coverage 0.72. `--trim`/`--mapali` keep their actual separate meanings.

These are descriptor differences, not six separately written episodes. The
current sealed producer binding is local. `is_native_hmmer_target` recognizing
an HPC label does not establish an implemented HPC capture route.

## B. HMMER API: original retained phmmer result page

Opening task:

> Obtain page 1, page size 2, from the original phmmer search against PDB. Retain
> the complete returned native JSON page, its hit/domain associations, alignments,
> search statistics and page metadata. Return the parent's original acquired
> result fields; the scientific parent interprets these measurements.

| Assigned item | Filled value and meaning |
| --- | --- |
| API service/program | ebi_hmmer / phmmer |
| Database | pdb, as recorded in the original request |
| Selector | page 1; effective page size 2 from the original assignment |
| Actual result operation | `api.hmmer.result({})` only |
| Complete artifact | The complete native JSON response for this requested page |
| Return currently bound | `execution_result_refs` and `execution_completed`; HMMER API numerical observations already exist behind qualified refs |
| Numerical model-view gap | An explicit requested-value projection needs the proposed deterministic materializer; native-HMMER row x-sources must not be mislabelled as current API facts |

Full acquisition insertion:

> `api.hmmer.result` obtains exactly the assigned original page with domains.
> It cannot submit another job, change the database or request the next page.
> Another page requires another explicit results assignment. The response must
> match the original search, algorithm, database and supplied input where those
> identities are reported. A not-ready response, remote failure, malformed result
> or identity conflict remains a distinct acquisition outcome. Recovery of this
> selected action uses its retained response; it does not make a replacement
> submission. A new explicit permitted acquisition may request this same page.
>
> Retain the entire page, including every supplied hit/domain, native array
> position, reporting/inclusion flag, alignment display and statistic. Preserve
> valid sibling domains when another domain fails publication. A completed page
> can still be one of several pages. Reported native target names, linked UniProt
> accessions and biological source labels are different fields, not interchangeable
> identifiers. A no-hit page does not establish biological absence.
>
> For phmmer the model axis describes the query and the sequence axis the matched
> reference protein. For hmmscan the model is the hit profile and the sequence is
> the query. Retain native one-based inclusive coordinates; derived intervals use
> the existing zero-based half-open interpretation. Domain/full-sequence scores,
> conditional/independent E-values, bias and coverage remain separate quantities.
> Domain bias from this API is in nats; its separately named bits quantity divides
> by ln(2). Native local tables already report bits.
>
> `api_identity_fraction`, consensus identity, alignment identity and actual
> sequence identity have separate denominators and operand requirements. PP
> displays supply bounded posterior probabilities, not exact identity or gene
> function confidence. Preserve negative native scores and printed zero E-values.
> Missing displays or operand metadata leave dependent measurements unavailable.
> Deterministic grading adds no HTTP request, model judgment or observation.
>
> The practical endpoint is completed acquisition/publication of this requested
> page. Partial numeric publication preserves valid rows and does not create a
> completed-page receipt. Byte retention is separately reported. Full numeric
> sheets remain saved data; only requested values and qualifications are shown.

Actual retained page values that an explicitly requested materialization would
show (not all automatically selected by the existing ref-only form):

| Original native locator | Field | Exact value | Qualification |
| --- | --- | --- | --- |
| Requested page 1 | page_count | 2 | Page is not complete population |
| Page 1 | hits returned | 2 | Native page array count |
| Hit-array position 0 | native sequence score | 19.809377670288086 bits | Full-hit score |
| Hit-array position 0 / domain-array position 0 | domain score | -0.9096836447715759 bits | Negative native value retained |
| Same domain | independent E-value | 11354.052312028885 | Native statistic, no confidence interpretation |
| Hit-array position 0 / domain-array position 1 | domain score | 16.722900390625 bits | Separate domain |
| Same domain | independent E-value | 0.047277148370955285 | Native statistic |

Do not automatically print all these values when the parent asked for only
completion/refs. An actually requested source-cell row must be joined by the
original hit-array and domain-array positions, not provider hit index or a newly
sorted list. The whole retained page remains available for later requested work.

## C. Generic native byte windows: illustrative assignment, not measured run

Opening task:

> Obtain bytes [0, 4096) of `/project/run/output.tsv` from the original handed-off
> native job. Preserve the exact acquired windows and their qualifications. Return
> acquired-result references, acquisition origin and the original completion field.

This example's path and byte values are deliberately illustrative. They test
the real generic-window contract; they are not measurements from a newly run job.

| Assigned item | Filled value and meaning |
| --- | --- |
| Original program | `/project/software/analyzer`; actual original argv would be printed |
| Selector | path `/project/run/output.tsv`; offset 0; limit 4096 |
| Native format | Unknown; `.tsv` alone does not bind a scientific parser |
| Available operations | `execution.results.status({})`; `execution.results.collect({})`; `execution.results.read(path, offset, limit)` |
| Read operands | Exact assigned path; offset ≥ 0; positive limit ≤ 1,048,576; chosen interval remains within [0,4096) |
| Raw retention | Exact returned byte windows; generic path does not seal a whole producing-attempt artifact |

Full acquisition insertion:

> `execution.results.collect` observes the original attempt and reads a bounded
> first window for each requested path using the configured window bound.
> `execution.results.read` observes the original attempt and obtains one selected
> window within the assigned path and interval. `execution.results.status`
> observes the original attempt without acquiring file bytes. Select each only
> when useful; there is no mandatory status-before-read sequence.
>
> These reads observe the current resource filesystem. The original attempt's
> successful observation does not prove that current bytes were produced by that
> attempt. Separate reads are not an atomic file snapshot. Keep each offset,
> returned length, observed file size and original observation time. A changed
> file between reads does not become an invented common version.
>
> This assignment asks for a byte interval, not a complete scientific output or
> numerical interpretation. Retain those bytes; report their scope precisely.
> Successful requested acquisition plus an independently observed successful
> original attempt can establish this limited endpoint. It does not establish
> producing-attempt identity, complete larger-file custody or valid numerical
> content. An assignment requiring complete original scientific artifacts needs
> an appropriate bound acquisition contract; do not silently broaden this one.

Illustrative STEERING rows after one selected read:

| Object | Acquired selection | Missing selection | Qualification |
| --- | --- | --- | --- |
| `/project/run/output.tsv` | [0,2048); 2048 bytes | [2048,4096) | Observed file size 12288; current-filesystem window |
| Original attempt | completed, returncode 0 | none for this observation | Does not verify producing attempt for file bytes |
| Numerical result | not requested / no format reader bound | no numeric claim | Bytes are retained without interpreting TSV cells |

`execution.results.read` can select the remaining interval using the exact path,
offset 2048 and limit 2048. This is an available choice, not an automatically
chosen next action. When [0,4096) is acquired, only the requested interval is
complete; the 12288-byte file remains only partially retained.

## D. Existing BV-BRC immediate Data API v1

Opening task:

> Obtain the original BV-BRC genome_feature page selected by the parent: gene
> equal to ybhP, offset 0, limit 2, with the originally requested fields and
> ordering. Preserve the complete native response and page limits. Return the
> original requested source-result fields without interpreting source product
> labels as measured target function.

The following native values come from the existing reserialized semantic fixture
in `tests/test_api_bvbrc.py`, documented there as captured on 2026-10-23. They are
not a new live request or original-byte-position claim.

| Assigned item | Filled value and meaning |
| --- | --- |
| Service / collection | bvbrc_data / genome_feature |
| Original filters | gene eq ybhP; no additional inferred filter |
| Fields | feature_id, genome_id, genome_name, gene, product, protein_id, refseq_locus_tag, pgfam_id, plfam_id, accession, start, end, strand |
| Sort | Omitted in original request; no invented stable ordering |
| Page | Original offset omitted, effective 0; original limit 2; empty results selector retains this page |
| Actual acquisition | `api.bvbrc.result({})` |
| Response kind | Immediate response; no remote job/status operation |
| Current return facts | execution_result_refs; execution_completed. Proposed BV-BRC v2 facts are not yet bound |

Full acquisition insertion:

> `api.bvbrc.result` acquires the explicitly selected page under the original
> collection, filters, fields and sort. The results selector permits only offset
> and limit. If its effective page matches the original request, the adapter
> publishes the actual retained response without another GET. An explicitly
> different selected page makes one new GET. It performs no automatic pagination
> or retry and creates no asynchronous job.
>
> Retain the complete native row array, raw response and request/response
> provenance. Preserve each actual feature/genome/accession relationship and
> requested source value. Do not collapse features that share a name or assume
> they describe the fixed annotation target. The original source reports start
> and end in its one-based inclusive coordinates and strand separately. Missing
> protein IDs, family IDs, conditions or units stay missing.
>
> Keep Content-Range verbatim. The observed header `items 0-2/88287` accompanies
> two rows. The next offset is 0 + 2 = 2; that header end is not an inclusive
> last-row index to advance to 3. Native reported total is 88287. If absent, total
> is unknown. A continuation indicates another available page; it does not
> authorize changing this assignment. Zero rows can be a completed empty page;
> an incomplete HTTP body cannot be a complete page.
>
> Source product strings are source assertions, not a calculated annotation
> probability. Page row counts are acquisition metadata. This v1 provider has
> no new function-confidence calculator, no additional v2 collection/filter
> semantics, and no AppService/Workspace operations. Errors preserve actual
> response and failure information. A monitor can describe this retained terminal
> response; there is no remote job to poll.

Native values if explicitly requested for materialization:

| Original page row | Field | Actual value | Qualification |
| --- | --- | --- | --- |
| 0 | genome_name | Escherichia coli strain THO-006 | Source organism label |
| 0 | product | Endonuclease/exonuclease/phosphatase family protein | Source assertion |
| 0 | start / end | 3368331 / 3369092 | Native one-based inclusive |
| 0 | pgfam_id | PGF_03781125 | Source family identifier |
| 0 | protein_id | missing | Not reported, not an empty protein or zero |
| 1 | genome_name | Escherichia coli O127:H27 str. C43/90 | Different actual genome |
| 1 | product | putative metal-dependent hydrolase | Source assertion |
| 1 | protein_id | EMS02283.1 | Source accession |
| 1 | start / end | 132605 / 133366 | Native one-based inclusive |
| 1 | pgfam_id | missing | Not reported |

The real feature IDs, genome IDs and accessions must accompany any requested
join; they are meaningful source identifiers, not host tracking hashes. This
table does not fabricate a gene-to-feature binding. A ref-only current return
does not establish that these values were delivered as typed facts. 070 owns
the proposed v2 `project_bvbrc_data_facts` schemas and their later numerical
admission path; this draft only defines how their already qualified values would
be rendered by the results boundary when actually bound.

## Separate operations, one common process

None of these insertions adds an LLM support judgment, hidden reacquisition,
timer cadence, retry policy or scientific score. Complete artifacts live on
disk. The model sees the original detailed task, the actual available operations,
its own signed yield information, relevant acquisition outcomes and the specific
requested native/numerical values with their qualifications.
