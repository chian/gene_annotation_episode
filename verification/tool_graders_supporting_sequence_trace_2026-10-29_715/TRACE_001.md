# Four supporting sequence operations: current source and consumer trace

2026-10-29. Read-only implementation evidence for root; not a goal, scope
amendment, accepted prompt or completed operation. The original user attachment
is authoritative. No production, test, inventory or progress file was changed.
No application/scientific import, test, native call, network request, model
call, installation or acquisition was performed. Only this report and its
source-pin JSON were written. All four fixed rows and R1–R7 remain unfinished.

This trace reuses the earlier nine-operation investigation in
`verification/tool_graders_support_operation_boundaries_2026-10-28_555/`.
Its BOUNDARIES sections1–4 and VERIFICATION_CASES sections1–3 were read;
its proposed interfaces remain proposals. Current relevant source paths were
then inspected again, including actual consumers, rather than treating the
old report or a pending inventory label as proof of implementation absence.

## Current status and exact equivalence

| Fixed row | Existing authority to reuse | Specific remaining path |
| --- | --- | --- |
| `biomni.tool.molecular_biology.get_gene_coding_sequence` | NCBI nucleotide acquisition; GenBank readers; `sequence.view` and existing extraction grading | Gene candidate/locus selection and typed Gene/accession/feature joins; selected CDS adapter and requested return; real resource-child acquisition binding |
| `biomni.tool.molecular_biology.get_plasmid_sequence` | NCBI nucleotide acquisition; existing GenBank/FASTA supplied-material parsing | Selected provider/record typed output preserving UID versus accession; Addgene acquisition/parser; actual requested return |
| `biomni.tool.molecular_biology.find_restriction_sites` | Biopython `RestrictionBatch.search`, using an explicit enzyme set | One shared restriction producer/catalog snapshot/typed reader/return, correct cut-coordinate meanings |
| `biomni.tool.molecular_biology.find_restriction_enzymes` | The same `RestrictionBatch.search`, using `CommOnly` | Alias to that same producer/reader with the exact resolved commercial-enzyme population and different topology default |

WORK_STATUS has these unchanged entries at row indices177,178,182,183, all
six completion columns pending. The historical restriction classification as
`scientific_algorithm` does not override the user's supporting-operation
treatment. PROGRESS_057 retains all four names under R3 and the older555
mapping as delivered work. This investigation does not add four new algorithms
or increment whole-tool/connected-operation counts.

Exact four operation strings have no references in current top-level
`gene_annotation_episode/*.py`, nor exact-name tests in `tests/*.py`.
That is a static search result, not a claim that their component algorithms
are absent. The source Biomni catalog contains all four names, but it belongs
to `reference/episode_tools`, whose execution workflow is not this episode
build's implementation.

## Original upstream behavior and information loss

The complete four bodies are in
`reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/molecular_biology.py`.
The separate upstream catalog is `biomni/tool/tool_description/molecular_biology.py`.

### get_gene_coding_sequence

Signature: `(gene_name: str, organism: str, email: str=None) -> list[dict[str,str]]`,
lines252–327. The actual return is an object
`{explanation,sequences:[{refseq_id,sequence}]}`, contradicting the annotation.

It optionally mutates `Entrez.email`, searches Gene using
`{organism}[Organism] AND {gene_name}[Gene]` with `retmax=5`, chooses
`IdList[0]`, fetches Gene XML, chooses `Entrezgene_locus[0]`, constructs an
accession.version, fetches nucleotide `gbwithparts`, and extracts every CDS
whose first `gene` qualifier exactly equals the supplied gene string.
Extraction is `feature.location.extract(seq_record).seq`. Any exception is
wrapped in a RuntimeError; a successfully parsed record with no matching CDS
returns a genuine empty list.

The returned sequence is nucleotide extraction, not a new gene/function
prediction. Search count/page, alternative Gene/locus candidates, selected
GeneID, taxon, record/feature ordinals, protein/transcript IDs, location order,
remote references, fuzzy boundaries, codon_start, transl_table and other
qualifiers are lost from the wrapper's output. Its prose claim that every
CDS begins ATG and ends with a stop is not checked by the implementation.
There is no genetic-code selection or protein translation in this wrapper.

Biopython SimpleLocation.extract slices nominal `[start,end)` and reverse
complements a minus-strand part. A remote part requires the explicit
`references` mapping; this wrapper supplies none. CompoundLocation.extract
extracts each part in retained order, applying each part's strand, then joins
the results. Passing native ordered minus-strand parts unchanged to a single
global `sequence.view` reverse complement would reverse the part order again;
an adapter must preserve and validate both native part order and its explicit
extraction request. Mixed/unknown strands and missing remote operands cannot
be filled with an empty or fabricated CDS.

### get_plasmid_sequence

Signature: `(identifier: str, is_addgene: bool=None) -> dict[str,Any] | None`,
lines330–419. With `None`, numeric identifiers select Addgene; a supplied
boolean overrides that rule. No fallback between providers occurs.

Addgene GETs `https://www.addgene.org/{id}/sequences/`, without an explicit
timeout/byte bound, selects the first `textarea.copy-from`, requires the
literal first line `> Addgene NGS Result`, joins the remaining lines and
removes spaces. It returns `{explanation,source:'Addgene',identifier,sequence}`.
Non-200, absent textarea or unexpected heading prints a message and returns
None. This merges distinct acquisition/representation failures and a genuine
no-sequence page. Multiple depositor/NGS records, native HTML and locators are
not retained. Alphabet, topology and completeness are not validated.

NCBI searches nuccore for `Cloning vector {name}`, `retmax=1`, relevance sort;
takes the first search UID, fetches FASTA and uses `SeqIO.read` for one record.
It returns the search UID under `identifier` while its explanation calls it an
accession, and discards the fetched FASTA identifier/title. No search hit or a
parse exception returns None; other network/search exceptions can propagate.
Neither branch establishes circularity or complete plasmid sequence from a
successful response. UID, requested name and returned accession.version must
be separate fields. Default automatic provider selection is existing wrapper
behavior to document, not authority for infrastructure to substitute a provider.

### Restriction aliases

`find_restriction_sites(dna_sequence: str, enzymes: list[str], is_circular=True)`
at725–788 uppercases input and calls
`RestrictionBatch(enzymes).search(Seq(...),linear=not is_circular)`.
The actual result contains sequence length/topology and every selected enzyme,
including empty-site rows. `recognition_sequence` is actually
`enzyme.elucidate()` (a cut diagram), not `enzyme.site` (the IUPAC motif).
Rows with hits additionally retain `fst5`, `fst3`, `ovhg` and a derived
sticky/blunt label; rows without hits omit those catalog fields.

`find_restriction_enzymes(sequence: str, is_circular=False)` at791–819 calls
the same search on `Restriction.CommOnly`, then drops empty enzyme rows.
Actual return is `{explanation,enzyme_sites:{name:[positions]}}`, despite
the annotated `dict[str,list]`. Sequence length, topology, exact searched
enzyme population and catalog version are not in that return. An omitted
enzyme cannot be interpreted as a measured negative without its batch.

The native source explicitly defines returned positions as the first base of
the 3-prime fragment, after the cut. FormattedSeq adds a leading space for
one-based indexing. Therefore these raw positions are one-based cut-result
positions, not zero-based recognition starts as both wrappers claim.
OneCut uses `recognition_start + fst5`; reverse recognition uses
`recognition_start - fst3`. Native `_drop` checks cuts on both strands for
linear input and wraps circular cut positions. NonPalindromic merges forward
and reverse events into the cut list; that list alone cannot recover event
orientation or uniquely associate repeated cuts with recognition events.
`CommOnly` is explicitly the commercial-enzyme batch assembled using is_comm,
not all known enzymes or a generic biological prevalence population.

The inspected reference Bio declares1.87; the retained529 dependency source
declares1.88. Nine inspected search/extraction methods have equal ASTs; the
tenth, AbstractCut._drop, differs only by the docstring typo
`outsite`→`outside`. This supports the specific source semantics above, not
runtime compatibility or equivalence of the complete enzyme dictionaries.
The future result must bind the actual executed version/dictionary and batch.

Source-derived example, not a native run: EcoRI's retained dictionary has
motif `GAATTC`, fst5=1, fst3=-1, ovhg=-4 and REBASE993. Over
`AAAAGAATTCTTTT`, expected recognition is `[4,10)`, native cut position6,
Watson boundary5 and Crick boundary9. This is a four-base 5-prime overhang;
the wrapper's claim that negative ovhg means a 3-prime overhang is false.
These expected numbers require future authentic native and return checks.

## Current acquisition, supplied-input and return consumers

`PublicClients.ncbi_search(database,term,*,size=10,offset=0)` already performs
one ESearch request and retains SourceSnapshot bytes/request/transport. Its
current allowlist is protein,nuccore,assembly,taxonomy,biosample,bioproject,
pubmed. Gene is absent. Future molecular bindings must apply the user's
molecular allowlist and must not expose the excluded PubMed/PMC work.

`PublicClients.ncbi_sequence(accession,*,database='nuccore',start=None,end=None)`
already fetches protein GenPept or nuccore gbwithparts. Supplied nucleotide
`[start,end)` becomes `seq_start=start+1,seq_stop=end`. These acquisition
intervals must remain distinct from feature coordinates within the fetched
record. `_http` retains actual response/error bytes and transport metadata,
but currently reads the entire response with `response.read()`; it is not a
selected byte-budget implementation. Reuse acquisition/publication mechanics
while adding the required explicit bounded molecular request, not a second
unbounded provider hidden in a reader.

ToolRegistry.catalog and `_acquisition_request` bind `public.ncbi.search` and
`public.ncbi.sequence` directly. `_import('public.ncbi.sequence',...)` creates
external reference records with returned accession, sequence, molecule and
length; original feature context remains in its retained source. The fallback
search result is `{source_ref,provider_result,raw_artifact_ref}`. Neither is
the typed CDS/plasmid result or selected Gene/feature association requested
by the four wrappers.

`parse_genbank(content)` preserves source_record_index, accession/version,
available sequence, topology, annotations, located/unlocated features,
source_feature_index, ordered per-part strands, fuzzy classes/text, remote
refs, location operator/text, partial flags and qualifiers. It performs no
acquisition or target annotation. Undefined sequence stays None.

For supplied files, `materials.register_material` preserves actual source
custody; `parse_material` delegates GenBank to `genbank_intake.records` and
retains native record/feature projections in a separate source. Partial
frames/features and undefined sequence retain specific diagnostics.
`material.annotations` uses `annotation_page`, returning exact record/feature
ordinals and source-byte windows plus next_query, not inferred target features.
This allows a CDS/plasmid investigation to begin from supplied file content
without a searchable gene name or candidate function.

`sequence_views.view_sequence` already extracts explicit ordered half-open
segments under a selected molecule model/orientation. ToolRegistry._derive
calls the sole `grade_extraction`, saves source/grading artifacts and publishes
mapped feature/product/observation records. Its shared authority remains
`sequence_extraction_sheet_v1` / `sequence_extraction_scores_v1`,
`build_extraction_sheet` / `calculate_extraction_scores`; saved calculations
use retained operands without Bio execution, acquisition or I/O. Existing
input/output/compared lengths, selected occurrence versus union populations,
source paths and missingness must be reused unchanged by a CDS adapter.
`sequence.translate` and its frozen code-table grading are separate existing
operations, not a prerequisite or substitute for nucleotide CDS extraction.

APIServicePrimitive already supplies common prepare/invoke/decode/publish/
result-selector ports; `publish_existing_acquisition` retains/republishes
acquired bytes once with operation-key operand checks and partial records.
Current `build_service` supports uniprot,bvbrc_data,ncbi_blast,bvbrc_minhash,
rfam_batch,bvbrc_appservice. It has no general NCBI Gene/Nucleotide data or
Addgene service primitive. Existing ordinary NCBI operations therefore do not
prove the selected resource-child/typed return path for these wrapper names.

ScientificProcessEpisodes resolves actual child_tool_info through its tool
library/information catalog and restricts invocation to resolved direct tools.
Its inspected fact_sources/facts expose process provenance and existing
alignment-site projections, not four new supporting result schemas. A
source catalog entry or generic record return must not be relabelled as a
completed requested molecular return. Preserve evidence_axis, thought_pattern,
child_tool_info and shared method_loop; no new episode type is needed.

## Existing verification to reuse, with limits

No four-wrapper native/episode tests were found, and none was executed here.
The following current source cases are reusable components, not proof that
these four aliases currently work. No fresh passing counts are claimed.

* `test_sequence_extraction_grader.py` covers ordered/repeated/overlapping
  segments, reversed ancestry, missing/conflicting cells and saved-only
  recalculation with native/Store/I/O/network forbidden. Its explicit example
  has9 input symbols,12 selected occurrences,7 distinct positions and5 repeated
  occurrences; this is an inspected test expectation, not a new result.
* `test_sequence_derivation_publication.py` compares actual retained extraction
  sheet/scores with publication measurements and replays one operation. Its
  saved recalculation blocks native execution/network and keeps one observation.
* `test_sequence_views_integration.py` checks source scope, ancestry, case/model
  declarations and exact replay without remote calls or annotation claims.
* `test_comparative_ops.py::test_reverse_strand_order_partial_boundaries_and_labels_are_source_faithful`
  checks GenBank ordered minus-strand parts/fuzzy bounds and source labels.
* `test_genbank_intake.py` checks supplied GenBank custody, exact full qualifier
  access, bounded feature pages, partial records and cached external evidence.
* `test_native_genbank_projection.py` preserves fuzzy/mixed/remote locations,
  incomplete frames, complete native qualifier arrays and source assertions.
  Its saved-acquisition case names AJ320226.1,4368 original bytes,1489nt and
  four native features with recorded provenance. This pass read that test;
  it neither imported/reparsed the artifact nor inspected a fresh test receipt.

555/VERIFICATION_CASES.md already lists focused positive/failure/source-format
checks for these four operations. Reuse those cases; do not rerun the baseline
scientific implementation merely because this alias remains unfinished.

## Smallest next implementation boundaries

1. **Shared restriction support**, independent of remote access: freeze one
   typed native/catalog/request/result contract for both aliases, with exact
   selected sequence File/reference/version, topology and resolved enzyme
   population. Implement one native producer and deterministic reader/return.
   Keep native one-based cuts and any explicit boundary conversion separate;
   motif and cut diagram are distinct. Do not infer strand/site associations
   from cut-only dictionaries. Preserve unknown geometry, actual empty results,
   unsupported enzymes and native failures. No confidence score/calculator.
   Verify tiny native cases once under bounded current software, then saved
   reader and actual requested-return replay with search disabled.
2. **Supplied CDS adapter**, independent of Gene network acquisition: use
   existing GenBank/native material feature identity and exact selected feature
   ordinals, then existing extraction results/sheets for representable local
   geometry. Add closed typed source associations and requested projection;
   retain unsupported/remote/fuzzy cases with specific missing inputs. Do not
   rebuild extraction math or require a publicly searchable name.
3. **NCBI provider seam**: extend the existing molecular request/acquisition
   ports for bounded Gene XML and Gene-to-accession links, selected candidates
   and explicit pages. Nucleotide acquisition/parsing remains shared. Bind the
   resource child and returned rows before declaring the name-based wrapper
   complete. GeneID/taxon/accession conflicts and partial pages need tests.
4. **Plasmid alias plus Addgene mode**: reuse selected NCBI nucleotide rows;
   separately implement bounded selected Addgene acquisition/HTML record
   parsing if that mode is exposed. Preserve every native selected sequence
   label/locator and returned accession; no first-hit or provider fallback.
   Source completeness and topology remain unknown without actual assertions.

The exact future signatures already proposed by555 are
`read_coding_sequences(records,*,selection,extracted,source_ref,source_request,gene_links)`,
`read_plasmid_sequences(native,*,request,source_ref,format)`,
`run_restriction_mapping(sequence,*,sequence_binding,enzyme_selection,topology)`
and `read_restriction_mapping(native,*,selected_sequence,enzyme_catalog)`.
They are reusable design inputs, not approved/coded interfaces. Root should
freeze owned files, concrete closed fields/failures and actual consumers before
delegating implementation. Concrete tool-information/TASK/STEERING templates
retain their separate required user-feedback boundary; this report contains
no proposed model prompt. No scientific acceptance gate, scheduler, hidden
retry, extra observation, W05 aggregation or resource substitution is added.
