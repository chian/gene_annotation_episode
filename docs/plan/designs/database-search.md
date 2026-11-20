# Database search (BLAST): design record, phase 1 (2026-11-20)

Fork F1. Scope: the database-search kind of BLAST, one query against a reference set, to identify what the query most
likely is. Written for the new paradigm (AGENTS.md). Nothing here has been run: phase 1 ran no workload, and the new
library modules below have not even been imported yet (the window's one workload slot was held by another fork's real
run). They are plain pure functions written to the shapes of the existing grader and must be exercised first in
phase 2.

Marks: **[owner]** said by the owner (plan decisions D4-D14 and the October statements they cite). **[inference]**
mine, a proposal. **[found]** read in the current code.

## 1. What the owner asked for, against what already exists

Owner's list for a database search **[owner]**: score the whole hit list (not the top hit) Bayesian-style; adjust for
how often an annotated function occurs in the database at all (representation); keep the taxa of the hits and whether
they cohere with each other and with the target's own taxon; keep the source of each hit (a metagenome is less
reliable than a cultured, closed genome); deterministic, no model, built once as functions, same sheet for the same
analysis with a different parser per source; not run locally. The formula matters less than having every piece as
data first.

| Owner's piece | Exists in the sheet (data) | Reaches the parent as controlled features today | Missing |
|---|---|---|---|
| Whole hit list, duplicates collapsed | yes: native hits, sequence groups, duplicate count | counts only | nothing |
| Bayesian score over the list | yes: a bit-score kernel with function priors, conditional weights per function | conditional weight, representation-adjusted weight | the formula is deliberately simple; owner says adjust later |
| Representation (how often a function is in the database) | yes, **if a profile is supplied**: per-function counts and fractions, with reasons when unavailable | only the adjusted weight | nothing supplies the profile in the real episode; the parent sees no fraction |
| Taxa and their coherence | yes: per rank, taxon counts, same-taxon pair fraction, agreement with the target's taxon | only the target's match at genus | coherence among the hits, dominant-taxon share, top-rank mixing |
| Source and its reliability | yes: source, origin fields, assembly measurements by method (completeness, contamination, contigs) | nothing | a controlled source class; the quality summaries |
| Functions of the hits | only **if reference metadata is supplied**; never read from titles | per-function rows | in the real episode nothing supplies the metadata |

**The central finding [found].** In the real results episode the database grading is called with no reference
metadata, no target context and no database profile. So today a real database sheet has hits but no function labels,
no lineages beyond what the native record states, no sources and no representation, and the probability model has
nothing to weigh (it needs explicit function assignments). The grader and the sheet are largely there. What is
missing is the supply of the inputs, and the reading of the retained pieces as controlled features.

## 2. The route and one coupling to decide [found]

- Scoring dispatches a database sheet by its own schema, so a database sheet is never mistaken for a pairwise one.
- But for `blastp` it turns every hit's high-scoring pairs into native-correspondence comparisons, which feed the same
  correspondence subscore as a pairwise run (max over overlapping comparisons, mean over tools). So a database search
  contributes residue correspondence to the target (through its best references) as well as identification evidence.
  Other programs raise `a101_translated_or_nucleotide_map_not_bound` when scored. **Owner decision D-DB-1:** keep the
  database search's contribution to correspondence, or keep identification and correspondence as separate evidence.
  My design leaves the route unchanged and adds identification features beside it.

## 3. The kind: declared and derived [owner D9]

- Declared value: `database_search`, a field of the commission (the results assignment, and the launch and monitor
  commissions in the head). Module written: `forms/sequence_homology_evidence/blast_database_kind.py`.
- Derived from the job, never from a name:
  - the job of the public NCBI service is `{program, database, hitlist_size, query_file}`: one staged query and a
    database name and no subject sequence, so it derives to a database search;
  - a native job whose declared mode is `database` against exactly one prepared sequence database (and a profile job
    whose mode is `database`) derives to a database search; a native job whose mode is `pairwise` derives to
    `pairwise`; any other job has no derivable kind and raises.
- `require_declared_kind(declared, derived)` raises `blast_analysis_kind_conflict:declared:<x>:derived:<y>`. Fails the
  commission with that error; no repair and no fallback.
- **Making "derived from the job" trustworthy [inference].** The handoff row records the job's digest (`job_sha256`)
  and not the job. So the results commission must pass the job as it was submitted, and the grading unit (which can
  read custody; `read_from_parent` cannot) must check that the digest of the passed job equals the handoff row's
  `job_sha256` before it derives the kind and grades. A job that does not match its row is refused as the pairwise
  grading refuses a wrong operand: a failed unit with its named error and no credit.
- The vocabulary of the declared field is the union of the kinds every BLAST use declares; the pairwise path's
  `pairwise` and this `database_search` are two values of one field. The all-vs-all and preparation forks add theirs.

## 4. The job contract

- **Hosted service (start here) [owner: not local].** The service's job and the launch leaf already exist in the new
  scheme: the leaf builds the request from the service's own request form, the parent fixing some parameters, the
  query is staged from a held record, and the route keeps the provider's spacing. Nothing to build for the job.
- **Custom database on HPC (after the preparation fork's prepared-database record exists).** The existing standard
  prepared-database job contract (mode `database`, exactly one database operand, query a sequence or profile) is the
  shape. Following D10 (no stdout/stderr paths) the A101 job should be its own contract that declares only the one
  JSON report the grader reads, as the pairwise path now does; I have **not** written it, because its database
  operand must come from the preparation fork's manifest. It must be validated offline (contract and compiled
  command) before the owner's Aurora run.

## 5. Supplying the inputs the grader needs (new module `blast_database_grading_inputs.py`)

Pure builders; they read no record and no network, so they cannot reach a record the caller does not hold.

- `database_identity` and `calculation_context`: the searched database's identity (namespace, name, version, release,
  scope, where it was read from) and the reporting facts (hit array present, hits reported, the limits asked for,
  producer complete or unknown). A limit or completeness not known is `None`, never invented.
- `database_profile`: per-function counts of the searched database built on that identity. It is for exactly one
  database and release; a profile for another release leaves the adjustment unavailable with the grader's reason.
- `target_context`: the target's taxon, with a flag saying whether it was established independently of the search
  (the search's own best hit is not independent).
- `metadata_accounting`: what the supplied reference metadata covers of the hit list. A hit with no record is
  counted as missing, not as a hit with no function. No hit array is a result that said nothing, never zero hits.

**Where the metadata comes from [inference].** The deterministic readers exist (UniProt entries into exact EC
assignments with evidence codes, NCBI taxonomy into lineages, an NCBI assembly report into assembly level, completeness
and contamination, with an explicitly recorded protein-to-assembly link, never chosen by organism name). Acquiring
those records is a separate act of public requests keyed by the hit accessions, and I have not yet found which
acquisition functions in the new library to use (to find in phase 2). It belongs as units of the results episode's
database family, not in a separate episode, because the metadata populates the sheet and the sheet must stay a record
of the episode that graded it (a separate episode would have to pass bulk metadata upward, which controlled messaging
forbids). Politeness: batched requests, the services' own spacing, a generic client name and no contact address.

**First real run: search Swiss-Prot [inference].** Its hits are UniProt accessions, so function (exact EC with
evidence codes) and the curated status come from the UniProt record directly, taxa from the taxonomy, and no
protein-to-assembly link is needed. The large non-curated database needs an accession mapping and assembly links; defer.
A honest limit to expect: EC assignments exist only for enzymes, so for other proteins most groups will have no
explicit function and the identification will say little. Other function vocabularies (the reader keeps GO terms
separate and never converts them to EC) are an owner decision (D-DB-3).

## 6. Grader slots and the missing functions (new modules)

The existing grader keeps the pieces; no change to it. Three new pure modules read them:

1. `blast_database_context_features.py`: controlled features read from a retained grading.
   - Taxonomy coherence, for the whole hit list and for each function's groups: at each rank (superkingdom or domain,
     kingdom, phylum, class, order, family, genus, species) the counts of groups with one taxon, several taxa and no
     taxon, the number of distinct taxa, the dominant-taxon share, the same-taxon pair fraction, and the agreement and
     conflict with the target's taxon (absent when the target's taxon is not independently known). Plus whether the
     groups fall in more than one taxon at the top rank (absent when no top-rank taxon is known).
   - Source: the number of sequence groups per source class, and the reported assembly measurements by method.
   - Representation: whether counts matching the database and release were supplied, how many reasons said no, and per
     function the database count, total and fraction (absent when unavailable).
   - It computes no weight, no probability and no verdict of outlier or horizontal transfer: coherence is given as the
     measurements it is made of, and what they mean is the scoring's.
2. `blast_source_class.py`: a fixed vocabulary of source classes (curated reference, unreviewed reference, complete
   genome, chromosome-level, scaffold-level, contig-level, metagenome-derived, single-cell-derived, unclassified)
   derived only from three explicitly reported fields in a fixed order (genome notes, assembly level, entry type);
   a value the table does not hold gives `unclassified`. It records a class, not a reliability: weighting is the
   scoring's later. **Risk:** the exact strings (for example the genome-note texts for derived sources) are from my
   recollection of the services' documentation and must be checked against real reports in phase 2; the tables are
   parameters for this reason.
3. `blast_database_grading_inputs.py`: the builders in section 5.

What I did not touch: the probability model. The owner said the formula matters less and wants the data first. The
features above are that data; how coherence or source class should modify the weights can be decided once the owner
has seen real values.

## 7. Credit and return

- **Credit [found, then inference].** The existing family earns the credit unit once, when a grading is saved. Under
  D14 credit is the gain in certainty. I would keep the once-per-saved-grading credit for now and refine it later
  (for example by how many groups resolved to an explicit function), because a sheet with no functions teaches little.
  **Owner decision D-DB-2.**
- **Return (controlled fields only):** the existing finding features, plus the new context features (rank rows,
  mixing flag, source-class counts, quality rows, representation rows), the grading's reference, the source, the search
  row. The sheet, the hit list and the metadata stay in the episode as retained artifacts; nothing free-text travels.
  The return form needs a finding field for the new features (see the patches).

## 8. Real-run mechanics (designed in)

- **Machine bounds:** 1 CPU, 5 GiB RAM, no swap, one workload at a time. The hosted search runs at the service; the
  local work is the JSON2 parse and the sheet, bounded by the hit-list size, which is a BLAST search parameter and not
  an execution budget. A database large enough not to fit here (the non-redundant protein set) is never searched
  locally; a custom database goes to HPC.
- **Allocation:** lives in the assignment's constraints and the resource policy. For the PBS route a walltime request
  is a scheduler allocation, not an application deadline; **owner decision D-DB-4:** who sets it and from what (the
  estimate table).
- **Staged inputs:** the query sequence is a held artifact staged to the job as an input of the job service; the
  prepared database on the cluster is named by the prepared-database record.
- **Durations:** expected through the estimates recorded at launch and observed by the monitor; no deadline anywhere.
  The ledger records that the public service's job answered WAITING at three visits about a minute apart and never
  reached READY, so the monitor must be able to leave a job outstanding for many visits with no cutoff. The earlier
  outstanding job may no longer exist at the service (results are kept for a limited time), so do not rely on it.
- **Idempotency:** the submission's job handle comes from the unit's operation key, so a re-run unit does not submit
  again; an abandoned handoff row is taken over, not duplicated. A reply that was lost does not establish that no job
  exists.
- **Incomplete is not zero:** a result with no hit array, a hit list that reached its limit, a producer not known to
  have completed, and metadata that does not cover the hits are each recorded as what they are
  (`hit_list_present`, `limit_reached`, `complete: False`, missing accessions), never as zero hits or no function.
- **Public service etiquette:** one submission, the route's spacing between contacts and between status requests of a
  job (it refuses a too-early request with `provider_spacing_required` and sends nothing), a generic client name and
  **no contact address** (the route sends a contact address only if one is configured; configure none).
- **HPC:** needs the owner to authenticate first. I never authenticate, never replace the master connection and never
  run ssh, scp or qsub. Prepare it offline: validate the job against its contract, compile its command, and have it
  ready for the owner's run.

## 9. What fails and how

- A declared kind that differs from the job's derived kind: the commission fails with `blast_analysis_kind_conflict`.
- A passed job whose digest differs from its handoff row: the grading unit is refused, no credit.
- A database name or release that conflicts with the profile's: the representation is unavailable with its reasons;
  nothing is defaulted.
- A metadata record that conflicts (two lineages for one taxon): the sheet keeps both visible and the lineage is empty.
- A result that is not a database result, or is for another query: refused as the pairwise grading refuses a wrong
  operand.

## 10. Predictions for the phase-2 real run (to be sharpened before it)

Run: a real protein that is **not** in Swiss-Prot (so the search does not just return itself) but has an
EC-annotated unreviewed entry, searched against Swiss-Prot through the real service, hit-list size a few tens.

- The submission is accepted once and a request id is returned; the monitor sees WAITING for some visits (the
  duration is unknown) and then READY; the JSON2 result is fetched and retained.
- The sheet has tens of hits, collapsed to fewer sequence groups; most top hits are curated orthologs; their taxa
  cluster within a family or genus; the function weight concentrates on one EC; the target taxon agreement is present
  only if I supply an independent taxon.
- Source classes: nearly all `curated_reference`.
- Representation adjustment is most likely unavailable (the service's Swiss-Prot release and a UniProt count's release
  will not match), so the adjusted weight and database fractions are absent, with the reasons counted.
- Many groups without an explicit function if the query is not an enzyme; choose an enzyme for the first run.
- Credit: the launch earns its handoff credit; the grading unit earns the once-only credit; resume asks the model
  nothing.

## 11. Proposed patches to existing files (not applied)

Patch A, `execution_result_acquisition/messages/read_from_parent.py` (and the form): add `analysis_kind` (a choice
field over the kinds) required for the BLAST families; for family `blast_graded` the assignment's target carries
`assignment.job` (the API job as submitted). After the family is known:
```python
kind = derive_kind_from_api_job(target['assignment']['job'])        # blast_database_kind
require_declared_kind(assignment['analysis_kind'], kind)
```
Patch B, `execution_result_acquisition/task.py`, `blast_grade`: before grading, check
`content_digest(target['assignment']['job']) == handoff_row['detail']['job_sha256']` (the row is read through
`ctx.store` from the handoff the commission passed); build the inputs with the new builders; call the grader with them:
```python
grading = grade_blast_result(content, mode='database', resource='api', output_format='json2', request=operand,
                             reference_metadata=rows, target_context=target, database_profile=profile,
                             _retain_correspondence=True)
```
`grade_blast_result` does not forward `calculation_context` to `build_database_sheet` today, so the library function
`grade_blast_result` needs one added pass-through parameter (`calculation_context`), or the episode calls
`build_database_sheet` and `calculate_database_probabilities` directly. Also add units for fetching the reference
metadata (section 5) and keep the account of its completeness in the unit's outcome.
Patch C, `blast_database_features.grading_features`: also return `context_features(grading)` under one key, and the
return form's finding gains controlled fields for it.
Patch D, the head's commission builders: results and launch commissions for this kind pass `analysis_kind` as a
controlled value of the slot, the job as submitted, the handoff row and the query's records in custody.

## 12. Open owner decisions

- D-DB-1: does a database search keep feeding the correspondence subscore, or are identification and correspondence
  separate evidence?
- D-DB-2: credit for a database search: once per saved grading, or scaled by the information gained?
- D-DB-3: besides EC, which function vocabularies count as explicit functions for the identification (GO terms by
  evidence code, product names)?
- D-DB-4: who sets a PBS job's walltime, and from what?
- D-DB-5: are profile searches (the profile and position-specific programs) the same kind as a database search?
  I treat them as the same kind (mode `database`) and flag it.
- D-DB-6: for a hosted database whose release does not match any available count, is an approximate profile with a
  recorded release mismatch acceptable, or is the adjustment simply absent? Current behaviour: absent.

## 13. Real-run recipe for phase 2 (one workload at a time, after the slot is free)

1. In a scratch script, with the three new library modules, exercise them on a synthetic database sheet (the grader's
   own fixtures) as function-level checks only, and fix what they show.
2. Find the library's acquisition functions for UniProt entries and NCBI taxonomy and decide the unit shape.
3. Choose the real query (see section 10) and write the prediction for the run.
4. Run the real launch leaf with the hosted service (generic client name, no contact address, the route's spacing), then
   the monitor over many visits with no cutoff, then the results episode with the acquisition units and the grading.
5. Inspect the journal, the handoff and check rows, the retained artifacts, the sheet, the new features and the
   credit; resume must ask the model nothing.
6. Record what the real report's strings gave for source classes and adjust the tables.

## 14. Files written in phase 1 (new, library only; none run yet)

- `episode_support/forms/sequence_homology_evidence/blast_database_kind.py`
- `episode_support/grading/similarity_search/sequence_homology_evidence/blast_source_class.py`
- `episode_support/grading/similarity_search/sequence_homology_evidence/blast_database_context_features.py`
- `episode_support/grading/similarity_search/sequence_homology_evidence/blast_database_grading_inputs.py`
