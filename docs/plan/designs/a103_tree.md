# A103 (gene context evidence): what was agreed, and a tree derived from it

Status: draft for the owner's review, 2026-11-23. Written from a thinking session with the owner ("No coding yet. I want to just
think"; then "Wrote this down along with a subtree design that matches these criteria"). Nothing here is built. It follows
`docs/sop/evidence_axis_build_sop.md` Step 0A as far as the table; the full inventory of the old A103 library (Step 0A item 7)
is not done yet and is listed at the end.

## What the axis is for

The process library entry A103 (`research/slotted_process_library/publications/2026-10-24-001/entries/A103.json`): "Investigate
genomic organization and identified neighboring components to discover and distinguish possible functional relationships";
"Establish the relevant locus and actual genome or assembly before interpreting context; an unmapped sequence or fragment does
not supply a neighborhood"; neighbours, gene order, strand, spacing, fusions and regulatory features.

The owner widened it on 2026-11-23: an arm "that can, like this arm [A102], propose annotations and/or verify claims"; "context
is defined as a bunch of annotations to begin with and some broader context for coding frequency, AT bias, and so on".

## What was agreed (the owner's rulings, 2026-11-23)

1. The start is DNA. "in reality it should be an arbitrary piece of dna of any size"; "I do want this to take in both aa and
   dna sequences but primarily this will all start from dna (since that is how sequencing rolls). Aa has to come after a gene
   caller, which now becomes necessary".
2. Context comes first. With a piece of DNA nobody has yet said what the things in it are, so this arm also finds the targets
   the other arms work on ("Yes, i realized the same thing. Context comes first").
3. Three sources of context, needing less and less annotation: (a) the bare sequence, no annotation at all; (b) context
   borrowed from already annotated relatives; (c) a shallow first pass over the neighbours, sharpened in later passes. Build
   (a) first ("Only bc that's the easiest to build").
4. Source (b), in the owner's words: "use proposed annotation (and perhaps potential taxa identified from first item) to
   suggest possible neighboring gene annotations and search the neighborhood for those specifically".
5. The genetic code: "frozen except in a few specific examples. So that seems like you know mostly where to start unless you
   trigger a special case of taxa". Default code first; another code only when a known special case is triggered.
6. A gene call is a proposal and stays revisable ("The keep the gene/region revisable part is the hard part here"). It is the
   problem already solved for names (`a102_regrouping.md`): the DNA piece is the one fixed thing, a call is a reading of
   positions on it, the observations stay as observed, one place decides the call in force, and credit follows the change in
   annotation scores. Redoing an expensive test after a revision is decided by expected gain ("only minor change in sequence,
   likely same binding score"), not by a rule.

## Step 0A: the derivation

**Targets.** A piece of DNA of any size (a read, a contig, a genome); a protein given directly (it joins after the gene
caller and has no position, neighbours or surrounding composition).

**What this axis can observe that no other axis can.** Where things are and what surrounds them: the composition of the DNA
itself, where the reading frames and RNA genes lie, their order, strand and spacing, whether a gene looks native to its
surroundings, and what a family is usually found next to. A101 and A102 look at one sequence at a time and see none of this.

| # | Analysis | Question it answers | Needs first | Does it today (checked 2026-11-23) | Measures | Tells candidates apart |
|---|---|---|---|---|---|---|
| C1 | Composition of the piece | what kind of DNA is this: which lineage, chromosome or plasmid or phage or organelle | the piece | computed in the repository's Python (numpy, Biopython importable) | base fractions, skew, short-word signature, along the piece and overall | piece-level candidates (lineage, replicon kind) |
| C2 | Gene calls | where are the protein genes, on which strand, with which start | the piece, the code (default) | `pyrodigal` 3.7.1 is importable in the venv; no call was run; its modes for short pieces are not verified | calls with their scores, start alternatives, partial ends | no: it makes the targets |
| C3 | Code check | is one of the few special genetic codes in use | C1, C2 | a fixed table of the known cases, to be written; nothing checked | lineage signal; under the default code the length of calls and the coding share | switches the code, then C2 again |
| C4 | RNA genes | where are the RNA genes | the piece | Infernal 1.1.5 and Rfam 15.1 are installed (A102 scans RNA targets with them); a scan of a whole piece was not run | hits with family, span, strand, bit score against the family threshold | makes targets; admits RNA family candidates |
| C5 | Layout | which genes run together: same-strand runs, spacing, overlaps | C2, C4 | computed | distances, run lengths, overlaps | supports C8, C9 |
| C6 | Atypical gene or region | is this gene native to its surroundings or acquired | C1, C2 | computed | the deviation of a gene's composition and codon use from the piece's | feature-level: native or acquired |
| C7 | Locus of a given protein | where does a protein given alone sit in known genomes | a protein | BV-BRC features carry `aa_sequence_md5` (field seen live); a lookup by it was not run | the features with exactly that sequence, their genome and position | no: it supplies a neighbourhood |
| C8 | Predicted neighbourhood | if this is function X, what should be beside it | a candidate annotation with its family identifier; lineage from C1 | BV-BRC features carry the global family and their position (seen live); the neighbourhood query was not run | per neighbouring family, in what share of genomes it sits beside X, at what distance and strand | yes: each candidate predicts a different neighbourhood |
| C9 | Neighbourhood check | are the predicted neighbours here | C8, and the piece's own calls (C2) | BLAST+ 2.17 is installed; nothing run | which predicted neighbours are found, their match values and positions, for the leader AND its rival | yes: the direct comparison of two candidates |
| C10 | Fusion | is one call the fusion of two things that are separate neighbours elsewhere | C2, C8 | not checked | the two halves' matches and whether those families are neighbours elsewhere | yes |
| C11 | Boundary evidence | does evidence from other arms say a call's start or end is wrong | calls, the other arms' position-anchored evidence | nothing exists | how far evidence extends beyond a call, on which side | no: it revises targets |

The check the SOP asks for (could another axis have produced this row?): C9 uses a sequence search, which is A101's kind of
tool, but what it measures (whether a predicted neighbour is present beside the target) is not something A101 asks. No other
row has a counterpart.

## The subtree

```
gene_context_evidence                HEAD. Forecast yield controller. Offers only what the given piece allows.
├─ describe_piece                   TOOL   C1. Set path, no choices. First unit for a DNA piece.
├─ call_genes                       TOOL   C2 with the default code; C3 decides whether it is run again with another code.
├─ scan_rna_genes                   TOOL   C4. One local job.
├─ layout                           TOOL   C5. Computed from the calls.
├─ atypical_regions                 TOOL   C6.
├─ locate_protein                   TOOL   C7. Only for a protein given alone.
├─ predicted_neighbourhood          TOOL   C8. Commissioned per candidate annotation (leader and rival).
├─ neighbourhood_check              TOOL   C9. One local job; measures both candidates in one test.
└─ fusion_check                     TOOL   C10.
```

- Every node is a tool, not a child: each is a set path with no decisions inside it (the owner's rule that a set path is a
  tool). A child appears only if one of them turns out to be a long job on an outside service.
- `describe_piece` and `call_genes` earn nothing about function by themselves: they are what the rest stands on. The SOP says a
  prerequisite that earns nothing cannot be an action on the forecast controller (its ceiling would be 0); here they do earn,
  because they admit piece-level candidates (lineage, replicon kind) and make the targets. This has to be settled when the
  credit is designed.
- As a proposer the arm returns candidate annotations from C8 to C10 and the piece-level candidates from C1, C3 and C6. As a
  verifier it checks claims of kinds the root cannot make yet: "encoded in the organelle or the main genome", "beside X",
  "native to this genome".
- What the arm hands the root: the features it called (each a sequence with its position, strand, code and whether an end is
  cut off), so the other arms can be commissioned on them.

## Revisable calls

- Evidence is anchored to positions on the piece. A call says which positions are one gene; it is applied when evidence is
  read, as a grouping of names is in A102.
- The arms report what they see about boundaries (C11); one place decides the call in force and passes it down.
- A gene is then a group of calls. Evidence gathered on any call of the group counts for the gene.
- A revision that changes annotation scores earns; going back and forth without new evidence earns nothing.
- After a revision, redoing a test is an offered action whose expected gain depends on how much of the sequence changed and
  whether the changed part touches what the test measured.

## Heavy, later

| What | Adds | Why it waits |
|---|---|---|
| Gene calling in eukaryotes | genes with introns | a different and much harder problem; not asked for yet |
| Assembly or mapping of reads | a neighbourhood for a read | needs a reference or enough reads; not designed |
| Whole-genome alignment (Mauve: the library has readers for its format; the program is not installed) | conserved order across genomes | a build and long runs |
| A lineage classifier with a large database | a firmer lineage than composition gives | a large download; not installed |

## Open, for the owner

1. Is the first target prokaryotic DNA (bacteria, archaea, their phages), with eukaryotes later?
2. Does "revisable" mean corrected starts and ends first, or also joining and splitting calls?
3. Who is the one place that decides the call in force: the root, or this arm?
4. Where do annotations that belong to the piece and not to a gene (lineage, replicon kind, code) live on the root's sheet?
5. One piece gives many targets; the root today directs the annotation of one protein.

## Not done

- The inventory of what the repository already holds for A103 (SOP Step 0A item 7): the old head (`root/a103/
  gene_context_evidence`, old-runner children, does not load on the current system) and its library folders
  (`episode_support/*/gene_context_evidence`: knowledge notes on alignment sites, minimap2 placements, read composition,
  sequence extraction and translation; `calculations/comparative_ops.py`, `evidence_geometry.py`; `tools/detection.py`). None
  of it was read for this note.
- No tool in the table was run. Each "does it today" cell says what was checked and what was not.
