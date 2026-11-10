# A108 source access, readers and information delivery plan

Source review: 2026-11-05 UTC. This is a design document, not an execution or
implementation claim. No network requests, Python commands, workflows or tests
were run for this review. The rejected A108 implementation is not a source for
the design below.

A108 asks how the other evidence fits the actual organism and sample. It needs
the qualified finding being considered, the biological requirements implied by
that finding, and observations about the relevant organism/sample that bear on
those requirements. It does not repeat A105's assessment of an activity assay,
or make successful database acquisition into biological evidence. A105 supplies
the useful hierarchy of source readers, purpose-specific subscoring sheets,
graders, aggregation and authenticated delivery. It does not determine A108's
tools, experiments, scientific criteria or number of sheets.

The numerical subscoring sheets and calculations are being specified in
[A108_NUMERICAL_SUBSCORING_PLAN.md](A108_NUMERICAL_SUBSCORING_PLAN.md), with their
main-sheet arithmetic and numerical delivery in
[A108_MAIN_EVIDENCE_SCORING_PLAN.md](A108_MAIN_EVIDENCE_SCORING_PLAN.md).
The earlier biological-question-only scoring plan was removed because it did
not define the required evidence scores. The source questions and reader needs
below are an inventory, not completed numerical subscoring sheets. The existing A105
communication hierarchy is documented separately in
[A105_EPISODE_COMMUNICATION.md](A105_EPISODE_COMMUNICATION.md). This document
specifies which actual sources can supply the operands, what each source can
mean, and which additional A108 reader and delivery work is required.

## 1. First input: evidence the parent has already received

The starting input is not necessarily another literature search. The shared
parent can already possess a qualified A105 activity finding, an A106
perturbation finding, an A102 localization/structural observation, or findings
from the other axes. A108 should receive only the findings and qualifications
needed to assess organism/sample fit. For example, a reported oxygen-dependent
activity can motivate a question about the sampled environment's oxygen
conditions. Its assay reliability remains the original axis's assessment; the
new A108 question is whether that requirement is compatible with the context.

Actual existing mechanisms are in
[shared_information.py](../gene_annotation_episode/shared_information.py:19):

| Operation | Exact operands and delivery meaning |
|---|---|
| `shared.request_information` | `target_ref`, `question`, `required_information`, `reason`, `blocking`, `available_record_refs`. Publishes a need, not a sibling commission, observation or score. |
| `shared.publish_information` | `target_ref`, `evidence_refs`. Advertises already received, scoped records. Saved grading/scoring sheets supply actual results and qualifications after receipt; no additional evidence-summary paragraph. Advertisement does not confer possession on another episode. |
| `shared.resolve_information_need` | `need_ref`, `status`, `evidence_refs`; operational `reason` only for unavailable/superseded replies. An addressed parent records a disposition and explicitly selects evidence for delivery. |
| `shared.read_information` | `publication_ref`. Actually admits the authorized publication and explicitly delivered evidence refs. |
| `shared.list_information` | `kind`, `offset`, `limit`. Pages authorized metadata; it does not admit the referenced scientific evidence. |

These tools currently authenticate only `annotation`, `scientific_process` and
`improvement` roles. A nested literature episode cannot simply call them or read
a sibling's private records. The A108 scientific parent must receive the
relevant records, then explicitly commission its context investigation with the
needed original records and requested return. Passing a sentence that says
another axis found something is not equivalent to delivering its retained
finding and qualifications.

The A108 adapter must preserve the following from a delivered finding:

- Original axis, observation/assessment and scientific subject references;
  retained/withdrawn status and explicit replacement/equivalence relationships.
- Original experiment and measurement identity, when the originating axis
  supplies them; original molecular form, conditions, units, direction and
  uncertainty, rather than a rewritten confidence number.
- The particular claim whose applicability is being considered and the
  source-qualified requirement extracted from it. A condition used in one assay
  is not automatically a requirement of the molecule in vivo.
- Original reliability and applicability qualifications, including missing
  operands. These accompany the fit result unchanged; A108 does not award a
  second assay-reliability score.
- Exact source and subscoring-sheet references required to inspect that claim.
  Corrections to the originating result remain visible.

[scientific_findings.py](../gene_annotation_episode/scientific_findings.py:1)
already checks typed source-claim identity and declared replacement scope.
[evidence_axis_scoring.py](../gene_annotation_episode/evidence_axis_scoring.py:63)
distinguishes original experiment, measurement and representation identity. Those
are useful existing contracts, not proof that the new A108 adapter is wired.
An A108 applicability relation must identify both the original qualified
finding and its context observation. Neither a parent delivery nor a database
copy of the same observation becomes an independent experiment.

## 2. Availability is not A108 exposure

Three different facts must stay separate: a provider is implemented in the
repository; an operation is exposed to a particular episode role; and its
return is accepted by that receiver with the required scientific meaning.

Current
[LiteratureEpisodes catalog](../gene_annotation_episode/literature_episodes.py:1090)
exposes its own `_ACCESS_TOOLS` and `_ACQUISITION_TOOLS`. It narrows
`public.ncbi.search` to **PubMed only**. It adds `public.ncbi.entrez`,
`public.ncbi.sequence`, `public.ncbi.geo` and `public.ncbi.sra.file` only when
the A106 intervention mode is enabled. Most context tools below therefore
require deliberate A108 exposure or a parent-mediated typed return. Enabling
A106 to get those tools would import the wrong scientific purpose.

| Existing capability | Current route | A108 work still required |
|---|---|---|
| Europe PMC search/full text; PMC assets; exact source/PDF/XLSX/archive/image access | Literature roles already have appropriate source operations; acquisition is limited to literature/strategy/search roles | New context questions, source-specific biological readers and fit subscoring sheets; existing readers supply bytes/cells, not A108 meaning. |
| UniProt search/record/native evidence | Global tool catalog; separate selected-return machinery | Deliberate A108 access or parent delivery. Selected native returns currently recognize `annotation`/`scientific_process` receivers; nested literature admission needs an explicit contract. |
| NCBI taxonomy, GenBank/GenPept; broader collection search | Global tool catalog | A108 catalog and context readers. BioSample search is discovery only: no BioSample record-fetch operation in the richer Entrez contract. |
| Supplied GenBank record/feature metadata | `material.annotations` over an actual parse | Admit original supplied-material records to A108; new context-qualifier reader. Not currently in the literature access list. |
| GEO and SRA experiment metadata through Entrez | Implemented global acquisition/native parsers; current literature access is A106-specific | A108-specific metadata access and context reader; no raw-read analysis required for this purpose. |
| BV-BRC Data API v2 | Existing API `launch_api` and `results` assignments; not a `public.*` literature tool | Explicit existing-service commission and typed parent return, then A108 context-reader admission. No direct-call shortcut or automatic polling. |
| ChEBI/Rhea/compound/reaction/ontology records | Global molecular source tools | A108-specific identity/terminology use and delivery; these do not measure organism/sample availability. |
| SABIO-RK/BRENDA/BioAssay/ChEMBL/MaveDB | Existing experimental-database literature operations | Conditional source use only. Retained organism/assay-context facts may help a particular fit question; their A105 graders are not A108 graders. |

## 3. Primary literature and original supplementary observations

### Search, paper and asset operations

Contracts are in [tools.py](../gene_annotation_episode/tools.py:479),
[acquisition.py](../gene_annotation_episode/acquisition.py:886) and
[literature_assets.py](../gene_annotation_episode/literature_assets.py).

| Operation | Inputs | Actual result and custody |
|---|---|---|
| `public.literature.search` | Required `query`; optional `size`, `cursor` | One Europe PMC JSON search page, using `resultType=core`. Retains query/source response and bibliographic discovery records. Search matches are leads. |
| `public.ncbi.search` with `database=pubmed` | `database`, `term`; optional `size`, `offset` | One ESearch JSON page with returned IDs/count/query information; not article text or the result of an experiment. |
| `public.literature.read` | `pmcid` | Original open full-text XML, ordered paragraph projection, article identifiers and separately identified cited-publication metadata. Returns source/text refs, representation identity, paragraph count, metadata issues, original-read query. |
| `public.pmc.versions` | `pmcid`; optional `continuation_token` | Actual advertised version page; no preferred/latest version silently selected. |
| `public.pmc.files` | `version_ref`; optional `continuation_token` | Actual selected-version file inventory plus listed JSON metadata. Optional metadata failure does not erase the inventory. |
| `public.pmc.asset` | `asset_ref` | One exact listed/advertised asset with original advertisement and checksums; no guessed filename or invented URL. |

The A108 search objective must describe the unresolved fit question: for
example, whether the supplied isolate was sampled under an oxygen regime, or
whether a reported substrate was measured in that sample. Search terms are
chosen from received identity/context and actual outcomes. No benchmark answer,
preferred paper or case-specific known phenotype belongs in the prompt.

The following **new A108 readers** are needed. These are descriptive reader
names in this plan, not claims that callable operations already exist:

| Reader purpose | Exact observations it must retain | Receiving fit purpose |
|---|---|---|
| Microbial trait and physiology passage/table reader | Named strain/isolate; observed property; measurement or reported category; original condition, comparator and method; quantitative value/unit/censoring when supplied; table headers/footnotes; source wording and locations | Whether the candidate finding's physiological requirement agrees with observations about that organism. Species-level generalization must remain explicit. |
| Sample provenance and habitat reader | Sample/isolate accession; specimen/material; sampling site, time/depth and environmental condition; whether measured, recorded by submitter, inferred or unspecified; exact target-to-sample link | Whether a context observation actually describes the target sample and what habitat/environmental support it provides. Isolation site alone does not prove present exposure. |
| Metabolite/substrate/cofactor observation reader | Chemical identity, sample/matrix/compartment, measured presence or concentration, units, qualifier and detection limit, conditions and sampling time, assignment ambiguity and original method | Whether the chemical required by the qualified finding is observed in the relevant accessible context. Added assay reagent, growth-medium ingredient and endogenous measured chemical are distinct. |
| Localization observation reader | Native molecule and construct/tag, organism/sample, observed compartment/fraction, experiment type, marker/contamination qualifications and original observation | Whether location reported for the relevant molecule is compatible with the candidate process and its required substrate/partner location. Curated location and prediction remain separate from measured location. |

Each reader supplies the matching custom fit subscoring sheet described in the
scientific plan, with the original finding and context-observation references.
There is no common numeric `literature quality` field that replaces these
different biological questions. Existing assay qualifications can be reused
where already available; genuinely new experimental observations need their
own applicable measurement qualification, not a renamed A105 activity sheet.

### Exact retained representations

| Operation | Inputs and output | A108 reader obligation |
|---|---|---|
| `source.read` | `source_ref`; optional `representation=text|original|stdout|stderr`, `offset`, `limit`. UTF-8 byte window with actual artifact/offset identity. | Anchor the biological statement to the selected representation. XML tables/headings omitted from paragraph text require `original`. |
| `source.locate` | `source_ref`, `representation=original|text`, `needle`; optional `offset`, `limit`, `context_bytes`. Literal matches and unchanged context. | Repeated matches remain distinct; no match means no literal match in examined bytes, not absence of the biological property. |
| `source.archive.members` / `source.archive.extract` | Inventory: `source_ref`, optional `offset`/`limit`; extraction: exact `member_ref`. | Preserve member ordinal and parent archive, including duplicate filenames. Pick the relevant original table, not an inferred member path. |
| `source.xlsx.sheets` / `source.xlsx.rows` | Inventory `source_ref`; rows require `source_ref`, `sheet_key`, `offset`, `limit`, `header_row`, `where`. `where` is null or `{column,match:equals|contains,value,case_sensitive}`. | Preserve original row/cell identity, literal/filter population, units/headers/footnotes, formulas and caches. No formula recalculation or biological interpretation occurs in this reader. |
| `source.pdf.info` / `source.pdf.text` | `source_ref`; text also `page`, optional `layout=reading_order|layout|raw`. | Physical page identity is separate from printed page numbers. Text derivative offsets are not original PDF byte positions. No OCR occurs. |
| `source.pdf.page` then `image.view` | Render `source_ref`, `page`, optional `dpi`; view `source_ref`, optional `frame`, `colour_conversion=preserve|rgb`. | Rendering alone does not show the image to the model. Actual image inspection must retain page/frame/panel identity and original legend/scale/context. |

These operations are documented in
[tools.py](../gene_annotation_episode/tools.py:463) and literal custody checks
in [source_locations.py](../gene_annotation_episode/source_locations.py:16).
They are not measurement-specific subscoring sheets. A scalar from an XLSX
cell, a quoted trait, and a localization micrograph need different scientific
readers even when all three sources use the same storage machinery.

Recovery stays specific. An incomplete XML paragraph view calls for original
XML; a missing table header calls for the relevant neighboring table context;
an unreadable PDF text page can motivate actual page-image inspection; an
unavailable PMC article can leave a citation lead and motivate another source.
None of these is a negative result for organism/sample fit.

## 4. Organism, isolate and sample records

### NCBI taxonomy and sequence-record context

The global [tool contracts](../gene_annotation_episode/tools.py:606) provide:

- `public.ncbi.search {database,term,size?,offset?}` for `protein`, `nuccore`,
  `assembly`, `taxonomy`, `biosample`, `bioproject`, `pubmed`. Each is one ESearch
  result page. BioSample/BioProject results identify leads, not sample fields.
- `public.taxonomy {taxon_id}` fetches the requested TaxaSet XML. It supplies
  native names and lineage; it does not assign that taxon to the target or
  establish its physiology.
- `public.ncbi.sequence {accession,database:protein|nuccore,start?,end?}` retains
  GenPept or GenBank-with-features bytes and imported reference/sequence records.
  A requested nucleotide interval is zero-based half-open and is converted for
  the native endpoint. Original record/feature context remains in the source.

The new NCBI context reader must extract the **actual source qualifiers** when
present: strain/isolate, organism/taxon cross-reference, isolation source, host,
collection time, location and sample links. An organism's name in an imported
reference is not proof that it is the user's sample. Retain accession/version,
native feature identity, original qualifier spelling, repeated qualifiers and
conflicting values. The sample-provenance fit subscoring sheet needs an explicit
chain from the target to that reference/strain/sample; a shared protein sequence
does not identify a unique source organism.

For supplied GenBank, the existing route is:

1. An actual received material/parse, or `material.from_source {source_ref,
   format}` followed by `material.parse {material_ref,format}` when appropriate.
2. `material.annotations {parse_ref,record_ordinal?,kind:record|feature?,offset?,
   limit?}` returns source assertions, not current target annotations.
3. Each entry has record/entry ordinal, source/artifact refs, byte start/end,
   native preview and exact `read_with` query. These are
   `normalized_native_jsonl_byte_offsets_not_original_genbank`; the original
   source remains separately linked.

[materials.py](../gene_annotation_episode/materials.py:384) returns
`native_annotations_not_available` when the parse has no native annotation
source. That means unavailable source metadata, not absent biology. A108 must
admit this route explicitly; it is absent from the current literature catalog.

### Richer Entrez and GEO/SRA context

`public.ncbi.entrez` has exact schemas in
[ncbi_entrez_acquisition.py](../gene_annotation_episode/ncbi_entrez_acquisition.py:20):

| Operation | Inputs | Scope |
|---|---|---|
| `search` | `operation`, `database`, `term`, `retstart`, `retmax`, `native_format=json`, `max_bytes` | One selected page; supported databases are protein, nuccore, gene, taxonomy, assembly, gds, sra, snp. |
| `summary` | `operation`, `database`, `ids`, `native_format=json`, `max_bytes` | Original summary records for supplied IDs; no assumed biological relationship between returned records. |
| `fetch` | `operation`, `database`, `ids`, fixed `native_format`, `max_bytes` | protein/genpept, nuccore/genbank, gene/gene_xml, taxonomy/taxonomy_xml or sra/sra_experiment_package_xml. SRA requires one literal SRR/ERR/DRR ID. |

Publication returns only `acquired`, `source_ref`, `data_ref`, `failure_code`;
success delivers the native File explicitly. The full native source is retained
before parsing/identity checks, including failures. See
[ncbi_entrez_tools.py](../gene_annotation_episode/ncbi_entrez_tools.py:154).
An acquisition receipt is not an organism-context observation.

**There is no BioSample/BioProject fetch or summary branch in this contract.**
A108 cannot follow an ESearch BioSample ID by inventing an unsupported call. It
can use actual supplied BioSample data, source-linked GenBank qualifiers, an
existing SRA experiment package's sample metadata, or literature. A dedicated
BioSample fetch/reader would be a separate source extension, not an already
available capability or an assumed requirement of this build.

`public.ncbi.geo`, in [geo_tools.py](../gene_annotation_episode/geo_tools.py:21),
requires `study=GSE...`, `data_type`, `max_bytes`; `series_matrix` and
`supplementary_file` additionally require the selected literal `file_name`.
`family_soft` derives the documented GSE family filename. Each call transfers
one file. The SOFT parser retains original entity type/ID/ordinal, attribute
name/value and locations, column descriptions, tables, native relations,
capture/decompression qualifications and parse issues. It does not infer sample
group membership or turn table values into organism-wide facts. A GDS Entrez
search can provide discovery; the GEO getter itself is not a general search.

New source-specific readers are required for:

- **GEO sample conditions:** selected GSM/GSE records, actual organism/strain,
  tissue/material, treatment and sampling condition, linked original methods,
  and source-declared sample relationship. Feed the sample/condition fit sheet.
- **SRA experiment-package sample context:** exact package/run/experiment/
  sample occurrence and native metadata. Preserve contradictory/missing sample
  attributes. Feed sample-provenance and environmental fit, not sequencing
  quality or expression evidence.

Reported processed observations can be considered with their original method
qualifications. Raw expression or sequencing data require the appropriate
analysis axis; A108 metadata access does not authorize analysis or import that
analysis's tool roster. `public.ncbi.sra.file` exists for raw advertised files
but is not needed merely to read sample context.

## 5. BV-BRC: actual microbial data API, specific available fields

This is an implemented source, not a proposed service. The principal code is
[api_bvbrc.py](../gene_annotation_episode/api_bvbrc.py:310),
[bvbrc_data_query.py](../gene_annotation_episode/bvbrc_data_query.py:30),
[bvbrc_data_fields.py](../gene_annotation_episode/bvbrc_data_fields.py:1),
[bvbrc_data_publication.py](../gene_annotation_episode/bvbrc_data_publication.py:190)
and [bvbrc_data_host.py](../gene_annotation_episode/bvbrc_data_host.py:464).
The exact established API route is described in
[api-bvbrc-data-v2.md](../gene_annotation_episode/launch_instruction_library/api-bvbrc-data-v2.md).

### Operations, request and retained return

`api.bvbrc.data.query {}` is called by the assigned `launch_api` child.
`api.bvbrc.data.result {}` is called by its `results` child. The request and
result selector are in the respective assignments, not in these empty
arguments. A scientific/literature parent cannot invoke the operation merely
because its name is mentioned in a prompt.

The request has `version=bvbrc_data_request_v2`, `collection`,
`mode=page|count|facet`, and AND-combined `filters`. Predicates are exact typed
`eq`, `in`, numeric `range`, or `exists`, only where registered field flags
permit them. Page selection can include `fields`, `sort`, `offset`, `limit`.
Analyzed text fields do not support arbitrary exact predicates. Omitted fields
select only the unique key; asking only for an ID cannot produce a context
record. The frozen collection/field contract is explicit and rejects unknown
fields. This is not arbitrary remote SQL, a general browser or schema discovery.

The result selector has all five keys:
`version=bvbrc_data_result_selector_v2`, `page`, `projection`, `inputs`,
`supplied_metadata`. Relevant projections are:

- `collection_rows`: selected `row_indices`, `numeric_fields`,
  `metadata_fields`; no extra joins or supplied metadata.
- `molecular_experiment`: selected `result_ids`, `measurement_fields` and
  source-level `metadata_fields`, with explicitly received bioset/result/
  experiment/feature pages and optional source-bound supplied metadata.
- `query_metadata`: acquisition population/page qualification only; its counts
  are not A108 biological evidence.

The original response is reused for the unchanged page. Selecting another page
makes one GET. There is no remote job handle, queue, required waiting action or
automatic page/retry loop. BV-BRC computational AppService is a different
capability and is unnecessary for this data access.

Publication retains native response bytes, exact prepared request, selector,
native numerical sheet, selected join sheets, deterministic components and
input/source bindings. Returned fields include `source_ref`,
`raw_artifact_ref`, `grading_artifact_ref`, `collection`, `mode`, `parse_status`,
`qualification`, `requested_projection_complete`, `projection_failures` plus
the actual acquisition/handoff receipts. The existing internal tool grading
artifact is not the A108 main evidence scoring sheet.

Actual typed return sources are `execution_bvbrc_pages`,
`execution_bvbrc_counts`, `execution_bvbrc_facets`,
`execution_bvbrc_numeric_rows`, `execution_bvbrc_feature_sequence_rows`, and
`execution_bvbrc_expression_rows`. Results and received annotation/scientific
parents have custody/materialization checks. The pure view module explicitly
does not implement model-facing rendering. A108 must implement a deliberate
context receiver; copying a source ref or a fact-source name is insufficient.

### Which BV-BRC records can inform A108

| Collection | Available relevant native fields | New A108 reader and limitation |
|---|---|---|
| `genome`, `taxonomy`, `id_ref`, `genome_feature` | Genome/taxon IDs, lineage, assembly/accession and feature links; source identifier mappings | Subject/organism-link reader preserving each mapping and ambiguity. These qualify applicability, not phenotype. The frozen `genome` contract does **not** include broad strain, habitat, host, isolation source, oxygen, pH, salinity or temperature traits. Do not promise them. |
| `experiment` | `exp_id`, name/type, repository/public identifier, genome/taxon membership, technique/instrument, sample/bioset counts and treatment name/amount/duration/type | Experiment-context reader linking the particular cited finding to actual deposited treatment metadata. Counts of samples/biosets are metadata, not evidence credit. |
| `bioset` | `bioset_id`, `exp_id`, entity/result type, genome/taxon, analysis-group descriptions, analysis method and treatment metadata | Contrast/context reader: preserve which group/treatment the observation concerns. `analysis_group_1/2` text is not a demonstrated biological replicate design. |
| `bioset_result` | Result/entity/feature identifiers, genome/taxon, deposited result type and measurements, treatment metadata | Where needed, join the exact result to the preceding context through actual keys. Do not reinterpret arbitrary `other_value` or native expression magnitude as substrate presence. A qualified measurement from another axis remains that axis's finding. |
| `structured_assertion` | `property`, `value`, native `score`, `source`, `evidence_code` and feature identifiers | Curated-assertion reader preserving source/evidence code and source subject. No guarantee that a requested localization or trait exists. Native score is not A108 fit credit; distinguish source assertion/prediction from direct observation. |
| `pathway` / `subsystem` / their reference collections | Native pathway/subsystem memberships and source labels | Only when a selected claim needs the actual recorded relationship. Membership annotation is not observed pathway operation, metabolite availability or physiological feasibility. Preserve its source-inference character; do not replace A103/A110 reasoning. |

Native molecular columns are `counts`, `fpkm`, `tpm`, `log2_fc`, `p_value`,
`z_score`, `other_value`. `sample_ids`, replicate IDs, units, normalization,
p-value correction and contrast are **supplied metadata fields**, requiring
received JSON source and exact JSON Pointer. They are not guaranteed native
fields, and the join does not discover them. Missing/ambiguous joins remain
unavailable/conflicting. The custom fit sheet must retain that limitation.

This makes BV-BRC useful for exact organism/finding/context links and deposited
treatment metadata. It is not a replacement for a broad microbial trait
database. Recovery after unsupported-field validation means choose an actually
supported source or report the missing capability; it does not mean weaken the
query to pretend the requested phenotype was retrieved.

## 6. UniProt curated source observations and localization

`public.uniprot.search {query,size?,cursor?}` acquires one native JSON search
page; `public.uniprot.record {accession}` pins one original record. Exact global
contracts are at [tools.py](../gene_annotation_episode/tools.py:575). Native
parsing and selected returns are in
[uniprot_native.py](../gene_annotation_episode/uniprot_native.py),
[uniprot_native_contracts.py](../gene_annotation_episode/uniprot_native_contracts.py),
[uniprot_return_contracts.py](../gene_annotation_episode/uniprot_return_contracts.py)
and [uniprot_returns.py](../gene_annotation_episode/uniprot_returns.py:30).

Original `proteinDescription`, `genes`, `comments`, `references`, `keywords`,
`extraAttributes`, features and cross-references remain native records.
Evidence arrays retain owner pointer/ordinal, ECO and native source IDs. The
record's taxon and secondary-accession relations remain separate from the
requested identifier. Absence/null/invalid data are distinguished. Import can
retain useful native data and projection issues together.

The **new UniProt context reader** selects only comments/evidence/subject
fields relevant to the actual fit question. For localization it returns the
exact location/topology/orientation/comment statement, source protein/form,
organism, evidence code and linked publication. For physiological/cofactor
comments it returns the exact qualified claim and source, without converting a
cofactor requirement into a measured environmental concentration. Source
assertions based on similarity or prediction retain that basis. Reviewed status,
protein-existence category and number of references are not biological fit
scores.

The receiving localization or chemical-context fit subscoring sheet compares
that statement with the already qualified candidate requirement, retaining the
applicability chain and any compartment/species/construct mismatch. A source
comment is not automatically a direct localization experiment. If the paper
matters, its citation is a discovery lead and the paper must actually be read.

Existing selected-return receivers are `annotation` and `scientific_process`.
A108 can deliberately receive that return in its scientific parent, or add a
specific native-source admission contract to its nested context reader. It
cannot assume the current literature roles already accept that selected-return
format.

Sequence-only source discovery is available through these actual contracts in
[literature_sequence_discovery.py](../gene_annotation_episode/literature_sequence_discovery.py:21)
and [source_sequences.py](../gene_annotation_episode/source_sequences.py:25):

- `public.literature.sequence_identity {subject_ref,size?,cursor?,reviewed?}`
  requires a received protein operand and verifies full sequence equality for
  every returned candidate.
- `source.sequence.references {subject_ref,source_ref,record_index,offset?,
  limit?}` rechecks the selected record's equality and returns its actual
  citation identifiers/scopes.
- `source.sequence.scan {subject_ref,source_ref,representation,offset?,
  window_bytes?,limit?,minimum_length?,formatting_hyphen_offsets?}` recognizes
  candidate source sequence blocks with original byte witnesses. Case, space,
  numbering and soft-hyphen normalization are explicit; hard-hyphen removal
  requires selected inspected offsets. Source boundaries may need overlapping
  reads.

Their role is establishing source leads,
not identifying a unique organism, deciding a candidate function or supplying
context-fit points. A108 first uses the identity and evidence actually received
from its parent; this route is conditional, not a mandatory A105-style entry
sequence.

## 7. Chemical identity and recorded reaction/compartment vocabulary

These implemented tools can disambiguate terms in a context observation.
**None by itself establishes that a chemical is present in a sample.** Global
contracts are in [tools.py](../gene_annotation_episode/tools.py:591) and
[molecular_provider_acquisition.py](../gene_annotation_episode/molecular_provider_acquisition.py:25).

| Operation | Exact inputs | Result and A108 use |
|---|---|---|
| `public.chebi.search` | `term`, optional `size`, `page` | One native text-result page with continuation. Select an actual identity; source stars/scores are not acceptance rules. |
| `public.chebi.compound` | `accession` | Native chemistry, structure strings and ontology relations; complete `native_record_ref` is readable through `state.query`. New chemical-identity reader preserves stereochemistry/charge/class ambiguity before comparing sample observation with requirement. |
| `public.pubchem.compound` | `cid`, `max_bytes` | Original compound JSON and acquisition qualification. Use exact identity relationships; no metabolite occurrence inference. |
| `public.rhea.search` | `query`, optional `limit` | Limited JSON reaction search; current route returns undefined-direction master records. No exhaustive absence/directional coverage claim. |
| `public.rhea.reaction` | `accession` | Literal selected accession lookup; no automatic master/directional ID substitution. Reader preserves native reaction identity/side/direction. |
| `public.kegg.reaction` | `reaction_id=R.....`, `max_bytes` | Original reaction flat-file fields, continuation lines, equation and cross-references. No organism direction, flux or gene membership. |
| `public.quickgo.term` | `term_id=GO:.......`, `max_bytes` | Term definition/synonyms/relations/obsolescence only. **No gene-product annotation endpoint is implemented by this tool.** Useful for the meaning of a reported compartment, not locating a protein. |
| `public.reactome.record` | `stable_id=R-XXX-...`, `max_bytes` | One native record with species, compartments, inputs/outputs/components/citations/inference flags when present. No search/traversal or species substitution. Conditional recorded-context clarification; applicability to the microbial target must be established. |

The identity reader supplies exact resolved/ambiguous relationships and source
qualifications to the chemical-availability or localization fit sheet. It
doesn't have a standalone score for “found a ChEBI term.” Measured chemical
availability comes from a sample observation, a genuinely relevant curated
observation or an already qualified other-axis finding. Unresolved isomer,
protonation, conjugation, matrix or compartment identity must survive the return.

`public.string.network` supplies functional-association channels for explicitly
disambiguated IDs/taxon; it does not establish physical colocalization or a
required partner's presence. That evidence belongs primarily with the relevant
partner/context axis. `public.hpa.gene` is implemented for an ENSG human gene;
it is not the microbial localization source for this build. Their presence in
the repository is not a reason to put them in A108's default catalog.

## 8. Existing experimental databases are conditional sources, not the roster

The operations below actually exist in
[experimental_database_acquisition.py](../gene_annotation_episode/experimental_database_acquisition.py:15).
Their shared native-record reader is
[source.experimental.records](../gene_annotation_episode/experimental_database_records.py:16),
with `source_ref`, optional `offset`, `limit`, `contains`, `contains_all`.
It returns native record indices, source links, selected summaries and
measurement selectors; it does not score evidence. Source/raw request custody
and native metadata associations remain required.

| Source | Actual operations and selected inputs | Legitimate, conditional A108 purpose and new reader obligation |
|---|---|---|
| SABIO-RK | `public.sabiork.search {query,page?,limit?,max_bytes?}`; `.read {entry_id,max_bytes?}` | Source-organism, assayed molecular form and reported pH/temperature/cofactor/substrate context can qualify how a received activity finding transfers to the actual organism. Reader must distinguish a condition tested in vitro from an in vivo requirement, and retain the original cited experiment. Do not re-run A105 activity grading. |
| BRENDA | `public.brenda.search {query,include_text_mining?,fields?,result_field?,max_bytes?}`; `.read {ec_number,reference_id?,max_bytes?}`; `.graph_search {field,query,limit?,offset?,max_bytes?}` | Curated organism/enzyme/source comments and primary references may answer a particular physiological-context question. Reader preserves organism/variant/reference and comment scope, particularly whether the statement is experimental or text-mined. Graph search is identifier/publication discovery, not kinetic data or complete coverage. |
| PubChem BioAssay | `public.bioassay.search {query,limit?,offset?,max_bytes?}`; `.read {aid,section:description|summary|results,sid?,max_bytes?}` | A microbial whole-cell assay description can provide the actual species/strain, medium, exposure or cellular context relevant to a parent finding. Results need matching description and result-column definitions; an assay reagent or screen endpoint is not environmental availability. A105/A106 qualification stays attached. |
| ChEMBL | `public.chembl.search {collection:target|assay,query?,accession?,target_id?,organism?,limit?,offset?,max_bytes?}`; `.read {collection:target|assay|document|activities,record_id,limit?,offset?,max_bytes?}` | Exact assay organism, cell/target context and document links can identify a context mismatch in an already qualified finding. Native target confidence/relationships are source metadata. Molecular binding activity does not become a microbial phenotype because the record has an organism field. |
| MaveDB | `public.mavedb.search {query,limit?,offset?,max_bytes?}`; `.read {urn,section:metadata|scores|counts,limit?,offset?,max_bytes?}` | Host strain, construct, selection environment and measured phenotype in score-set metadata can qualify transfer of a received variant/activity finding. Retain heterologous host and source protein separately. Variant scores/counts require the matching score-set metadata and preserve the native scale; their processing belongs to their originating axis. |

No A108 build condition should require all five sources to be used. Conversely,
mere access to them does not supply a microbial physiology, habitat, metabolite
or localization collection. When a database and a paper represent one original
experiment, the parent receives one qualified underlying observation with two
representations, not extra evidence for the database hit.

## 9. Missing capabilities and honest coverage

Repository searches found no dedicated source adapters for BacDive, BioCyc,
MGnify, MetaboLights or a general microbial trait/phenotype database. The skills
available to this Codex session are not episode tools in this repository and
were not consulted or invoked. A source mentioned in an old plan or a package
catalog is not an implemented A108 operation.

Consequently:

- Primary literature, original supplements, supplied metadata, source-record
  qualifiers and the concrete implemented records above are the currently
  grounded routes to organism/sample observations.
- Broad microbial phenotype discovery is not established by the existing
  BV-BRC selected-field contract.
- A returned BioSample ID is not a read BioSample record.
- An SRA/GEO study's existence is not a measured sample metabolite or habitat
  property.
- A chemical dictionary, reaction record, pathway membership or ontology term
  is not an observation of chemical availability or cellular localization.
- A source-dependent unavailable result is a valid limitation. It must not be
  replaced by a made-up observation or promoted to biological absence.

Adding a genuinely missing provider would require its own exact query/response
contract, native custody, provider-specific reader, fit-sheet operands and
failure return. That is separate from exposing and correctly using the actual
repo tools; this plan does not silently promise that extension.

## 10. Source routes for the eleven proposed fit subscoring sheets

The sheet names below match the independently designed scientific plan. The
same paper may supply different observations to several sheets, but those
relations retain one original finding identity. The source reader is chosen for
the actual representation and observation, not merely the sheet's title. All
eleven A108 fit reader/receiver connections are proposed work, not inherited
working A105 routes.

| Subscoring sheet and receiving grader | Available source routes | Required reader return and source-specific limitation |
|---|---|---|
| **Physiological-role fit** | Parent-delivered qualified activity/perturbation finding; literature physiology passage/table; conditional BRENDA curated observation | Original physiological endpoint, organism/strain, condition and the supported biological link to the proposed role, each with witnesses. A BV-BRC product/pathway label is not a measured physiological behavior. |
| **Substrate-access fit** | Parent-delivered substrate/transport/localization evidence; literature/sample chemical observations; ChEBI/PubChem identity; UniProt location comments with original evidence | Actual substrate/form and its sample/matrix/compartment observation, molecule location and separately supported access route. A chemical dictionary entry or a reagent added to an assay cannot fill the sample-availability operand. |
| **Substrate-utilization fit** | Literature original utilization/growth/uptake/assimilation observation; relevant already-qualified A105/A106 result; conditional microbial BioAssay protocol and source result | Actual tested resource, endpoint, sole/supplemental resource distinction, organism/community and condition relation. Do not replace utilization with database pathway membership or rerun a depletion assay grader as A108. |
| **Cofactor-state fit** | Parent-qualified cofactor requirement; literature cofactor/metal/availability observation; exact ChEBI/PubChem form; conditional UniProt/BRENDA notes | Required versus observed cofactor form, redox/metallation state, free/bound or bioavailable quantity where actually reported, compartment and access. A total element amount does not establish the required cofactor species. |
| **pH-circumstance fit** | Parent-qualified pH-dependent finding; measured culture/sample/compartment pH in original literature or supplied metadata; conditional assay/source notes | Actual pH and location/time/condition, measured versus set condition, and the original finding's condition dependence. A reported assay pH is not automatically an optimum or the target organism's pH. |
| **Temperature-circumstance fit** | Parent-qualified temperature dependence; original culture/sample/physiology observations; GEO/BV-BRC treatment metadata only where an actual temperature is present | Exact temperature/unit, exposure duration/state and sample relation. A taxon's name or strain collection location does not supply a temperature observation. |
| **Oxygen/redox-circumstance fit** | Parent-qualified oxygen/redox requirement; literature measured oxygen/redox or stated aeration/anaerobic condition; sample or exact deposited treatment metadata | Observed/set oxygen regime, local versus bulk context, reported electron donor/acceptor/redox state and original requirements. Aeration label, oxygen measurement and redox-potential measurement are different operands. |
| **Salinity/water-availability fit** | Literature or original sample/culture metadata with actual salt composition, salinity, osmotic condition or water-activity observation; parent-qualified dependence | Native quantity definition/unit, ionic composition where reported, sample/compartment and exposure. Do not substitute salinity for osmolarity or water activity; there is no dedicated broad trait provider in the inspected roster. |
| **Spatial-access fit** | Parent-delivered qualified localization/transport/partner finding; original microscopy/fractionation/localization source; UniProt evidence-qualified location; conditional BV-BRC structured assertion | Molecule and required component location, compartment relation, source construct/native state, evidence basis and actual access connection. GO term meaning only disambiguates a label; it cannot establish the molecule's location. |
| **Temporal/physiological-state fit** | Parent-qualified condition-dependent finding; original time/state observations; GEO exact sample attributes; BV-BRC experiment/bioset treatment duration and group descriptions | Actual observation time, growth/developmental/stress state and alignment to the candidate's relevant state. Metadata group labels and matching study IDs alone do not align time points or establish state. |
| **Ecological-exposure fit** | Original habitat/sample literature, supplied metadata, exact GenBank source qualifiers, SRA package sample attributes; taxonomy only for source-organism relation | Actual sampling/host/site/environmental exposure observation and source-to-target link, distinguishing recorded isolation site, measured exposure and inferred typical habitat. BioSample ESearch is a lead; BV-BRC's frozen genome fields do not supply the missing ecology. |

For every row, the grader receives the already-qualified original finding and
the particular context observation; it returns the named fit assessment with
its uncertainty and missing connection. The tool does not assign that fit.
The main evidence scoring sheet's numerical mapping and aggregation must be
settled in the scientific design; this source inventory supplies neither an
invented score nor A105's inherited reducers.

## 11. What is communicated at each boundary

The names below specify content, not a proposal to replace the repository's
existing episode mechanism with another one.

| Sender → receiver | Required saved content | What the receiver needs for its next decision |
|---|---|---|
| Shared parent → A108 scientific parent | Admitted qualified finding refs; actual target/organism/sample refs; original axis qualifications; specific applicability question | Which biological requirement is under consideration, what context is known, and which missing context operand could change the interpretation. |
| A108 → context literature/source investigation | Only the needed original finding/context refs, the exact unresolved fit question, permitted source capabilities and requested purpose-specific return | A scientific objective, not a literal prescripted query or test answer. |
| Acquisition operation → source-selecting episode | Native source/receipt refs; exact requested/returned identity, representation, completeness, continuation and specific failures | Whether the requested source was acquired and the next useful source/read choice. This is not a numeric evidence grade. |
| Source reader → matching context-fit grader | The particular observation with exact native location, subject/sample relationship, conditions and source qualifications, plus the original qualified finding's requirement and identity | Operands for that one physiological, sample/environmental, chemical-availability or localization fit question. A missing required operand stays missing. |
| Context-fit grader → its commissioning episode | Saved custom subscoring-sheet ref, calculated/result fields defined for that fit purpose, uncertainty/missing/conflict qualifications and source/other-axis dependencies | What the observation changes about the candidate's applicability, and what specific missing fact or competing interpretation remains. No duplicate assay-reliability grade. |
| A108 → shared parent | Selected saved fit results, exact qualified-finding/context links, qualifications and unresolved information needs; A108 main evidence scoring sheet through its own agreed aggregation | Enough to revise the parent interpretation and choose its next investigation. Raw pages, full tables and unrelated search hits remain behind retained refs. |

A new A108 source adapter must not discard a source qualification before its
fit grader receives it. The compact parent return is a projection of retained
complete evidence, not a model summary that substitutes for the source.
Availability notices, failure reports and missing-information requests are
operational information. No numerical search grade was found in the existing
literature acquisition/record reader contracts, and none is invented here.

## 12. Specific recovery information, without context flooding

Every failed/partial return needs the operation and selected source, the actual
failure, useful retained partial refs, and the specific missing operand. It
must reach the episode that can choose the next action.

| Observed problem | Required information to retain and return | Useful next choice |
|---|---|---|
| Literature hit lacks accessible full text | Citation/identifier, attempted representation and actual access failure | Another available source/version, or qualified lack of full text. Do not extract the cited experiment from a search snippet. |
| Paragraph projection omits table/legend | Original XML source and omitted-representation issue | Read original table/legend; existing projection failure does not erase original bytes. |
| Record identity conflicts | Requested and returned native identifiers, source/ref and mismatch | Resolve the actual identity before applicability; never silently substitute the requested ID. |
| Captured response/file is incomplete | Capture/decode/parse qualification and exact retained data refs | Select a supported representation/page or different source, preserving the partial result; no empty-success/absence interpretation. |
| BioSample discovery has no supported record reader | Search ID and absent operation capability | Use a received alternative context source or report the precise source gap. |
| BV-BRC field unsupported | Collection, requested field and registry validation failure | Select an actually supported field/source. Do not claim a missing trait was negative. |
| BV-BRC/GEO sample or condition join missing/ambiguous | Original records/keys, conflicting alternatives and missing supplied metadata | Seek the exact related context or keep applicability unresolved. Do not borrow another sample's metadata. |
| UniProt location is inferred/curated without direct experiment | Native evidence code/owner pointer and actual citation | Use the appropriately qualified assertion or acquire its underlying source if needed. |
| Chemical identity ambiguous | Original sample label and candidate chemical identities | Resolve the relevant isomer/form or keep the availability comparison unresolved. |
| Other-axis finding not received or withdrawn | Original ref/status and actual admission failure | Parent-mediated delivery or revised finding; no private sibling traversal or reconstructed score. |
| Database and paper duplicate one experiment | Both source refs and explicitly established original identity | Merge representations in the appropriate retained relation, retaining both witnesses. |

No recovery here installs a waiting action, a polling itinerary, a timeout,
usage budget, minimum continuation window or a substitute stopping rule.
Ordinary retrieval and source reading stay ordinary episode actions. The
existing continuation/yield mechanism remains separate from scientific source
interpretation and machine resource limits.

## 13. Implementation conditions for the source layer

Before A108 source work can be called complete, its implementation must show:

1. A role-specific operation catalog built from the actual context purposes
   above; no assumption that A105's catalog or A106's mode is appropriate.
2. Authenticated delivery of the parent-qualified finding and context records,
   with source/measurement/replacement identity and original qualifications.
3. A separate implemented reader contract for each supported context source and
   biological observation type. Merely parsing JSON/XML/XLSX is not the reader
   that establishes a physiological, sample, chemical or localization fact.
4. Explicit attachment of each reader's outputs to its purpose-specific A108
   fit subscoring sheet and receiving grader, with source-specific missing and
   conflicting values preserved. No shared catch-all evidence-quality scalar.
5. Native source custody and reproducible compact returns, including explicit
   BV-BRC/UniProt receiver bridges where used. Provider availability and current
   A108 exposure remain separately documented.
6. Discovery/access/format failures remain visible operational facts; they do
   not become biological contradiction, zero measurement or false absence.
7. The parent receives the selected fit changes and remaining information need,
   with complete original evidence retained behind references. A105 or another
   axis's original assay/analysis score is not counted again as A108 evidence.

These are design/implementation acceptance conditions. This source review does
not claim that the new adapters, sheets, graders, aggregation or full autonomous
A108 workflow have been built or validated.
