# A103 (gene context evidence): the whole design

Status: design for the owner's review, 2026-11-23, from a thinking session with the owner ("No coding yet. I want to just
think"). Nothing here is built. The design covers the whole arm; the order of building is a separate matter and is at the end.
The owner on why (2026-11-23): "The point of designing first is to be able to know what the holistic shape needs to be before
you slot in parts that do not work with the broad design."

## What the axis is for

The process library entry A103: "Investigate genomic organization and identified neighboring components to discover and
distinguish possible functional relationships"; "Establish the relevant locus and actual genome or assembly before interpreting
context; an unmapped sequence or fragment does not supply a neighborhood"; neighbours, gene order, strand, spacing, fusions
and regulatory features.

The owner widened it: an arm "that can, like this arm [A102], propose annotations and/or verify claims"; "context is defined as
a bunch of annotations to begin with and some broader context for coding frequency, AT bias, and so on".

## The shape

1. **The piece of DNA is the one fixed thing.** "in reality it should be an arbitrary piece of dna of any size": a read, a
   contig, a chromosome, a genome, a set of pieces from one sample; from any organism, organelle, plasmid or virus. A protein
   given directly is also taken ("I do want this to take in both aa and dna sequences but primarily this will all start from
   dna ... Aa has to come after a gene caller"): it joins where the gene caller's products join and has no position.
2. **Everything else is a reading of positions on the piece.** A feature is a set of positions on one strand read as one
   thing: a protein gene (one stretch, or several stretches joined when the gene has introns), an RNA gene, a regulatory
   site, a repeat, a mobile element, an operon, an island, the whole piece. An annotation is always about such a set of
   positions. So "this piece is a plasmid", "these six genes are one operon" and "this gene is RecA" are the same kind of
   statement at three sizes, and the root's sheet needs one kind of line for all three.
3. **Context comes first.** With a piece of DNA nobody has yet said what the things in it are, so this arm also finds the
   features the other arms work on ("Yes, i realized the same thing. Context comes first").
4. **Three sources of context**, needing less and less annotation: (a) the bare sequence; (b) context borrowed from already
   annotated relatives: "use proposed annotation (and perhaps potential taxa identified from first item) to suggest possible
   neighboring gene annotations and search the neighborhood for those specifically"; (c) a shallow first pass over the
   neighbours, sharpened in later passes.
5. **The genetic code** is "frozen except in a few specific examples": the default first, another code only when a known
   special case is triggered, by lineage or by how the genes come out under the default.
6. **Every reading is revisable, and revision means every revision** (the owner: "Revision means all revisions"): a start or
   an end moved, two readings joined, one split, a strand or a frame changed, the stretches of a gene with introns changed, a
   reading dropped as no gene, a new one added. All of them are one operation: a set of readings of some positions is
   replaced by another set. It is the problem solved for names (`a102_regrouping.md`): the observations stay as observed and
   are anchored to positions; a reading is applied when the evidence is read; credit follows the change in annotation scores;
   going back and forth without new evidence earns nothing.
7. **The root decides.** The root is above this head, as above every head. This arm proposes readings and reports the
   evidence for and against them; the other arms report what they see about a feature's extent; the root holds the reading
   of the piece and passes it down, as it passes the grouping of names.
8. **Redoing work after a revision is a forecast, not a rule**: "As long as we can usefully revise based on the expected gain
   (i.e., only minor change in sequence, likely same binding score)". A redo is an offered action whose expected gain depends
   on how much of the feature changed and whether the changed part touches what the test measured.

## The analyses (SOP Step 0A)

What this axis observes that no other does: where things are and what surrounds them. A101 and A102 look at one sequence at a
time and see none of it.

| # | Analysis | Question it answers | Needs first | Measures | Proposes or tells apart |
|---|---|---|---|---|---|
| C1 | Composition | what kind of DNA is this: which lineage; chromosome, plasmid, virus or organelle | the piece | base fractions, skew, short-word signature, overall and along the piece | proposes annotations of the piece and of regions |
| C2 | Protein genes without introns | where are the genes, strand, start | the piece, the code | readings with their scores, alternative starts, ends cut off by the piece's end | makes features |
| C3 | Protein genes with introns | which stretches join into one gene | the piece, C1 (which kind of organism) | readings as joined stretches, with the evidence for each junction | makes features |
| C4 | Code check | is one of the few special codes in use | C1, C2 or C3 | the lineage signal; the length of genes and the coding share under the default | switches the code and the gene finding is run again |
| C5 | RNA genes | where are the RNA genes | the piece | family, span, strand, score against the family's threshold | makes features; proposes RNA families |
| C6 | Other features | where are repeats, mobile elements, regulatory sites | the piece, C2, C3, C5 | spans and kinds | makes features |
| C7 | Layout | which features go together: same-strand runs, spacing, overlaps | the features | distances, runs, overlaps | proposes regions (an operon, a cluster) |
| C8 | Native or acquired | does a gene or region belong to its surroundings | C1, the features | the deviation of its composition and codon use from the piece's | proposes annotations of regions; tells apart |
| C9 | Placement | where does this piece, or a protein given alone, sit in known genomes | the piece or the protein | the matching places, how exact, in which genomes | supplies a neighbourhood the piece itself does not hold (a read, a lone protein) |
| C10 | Predicted neighbourhood | if this is function X, what should be beside it | a candidate annotation with its family identifier; the lineage from C1 | per neighbouring family: in what share of genomes it is beside X, how far, which strand | each candidate predicts a different neighbourhood |
| C11 | Neighbourhood check | are the predicted neighbours here | C10, the features | which predicted neighbours are found, how well, where; for the leader and its rival in one test | tells two candidates apart |
| C12 | Fusion and split | is one feature two things that are separate neighbours elsewhere, or two features one thing | the features, C10 | the parts' matches and whether those families are neighbours or one gene elsewhere | proposes a revision; tells apart |
| C13 | Extent evidence | does evidence say a feature's extent is wrong | the features; the position-anchored evidence of every arm | how far evidence extends beyond a feature, or stops short, on which side | proposes a revision |

Could another axis have produced a row? C11 uses a sequence search, A101's kind of tool, but it asks whether a predicted
neighbour is present beside the target, which A101 does not ask. C9 likewise. No other row has a counterpart.

## The subtree

```
gene_context_evidence              HEAD. Forecast yield controller. Offers only what the given piece allows.
├─ describe_piece                 TOOL   C1.
├─ find_genes                     TOOL   C2, C3, C4: the gene finding that fits the piece (with or without introns; fragment or
│                                        whole), the default code, and again under another code when a special case is triggered.
├─ find_rna_genes                 TOOL   C5.
├─ find_other_features            TOOL   C6.
├─ layout                         TOOL   C7.
├─ native_or_acquired             TOOL   C8.
├─ place                          TOOL   C9. For a piece too short to hold a neighbourhood, and for a protein given alone.
├─ predicted_neighbourhood        TOOL   C10. Per candidate annotation, the leader and its rival.
├─ neighbourhood_check            TOOL   C11.
├─ fusion_and_split               TOOL   C12.
└─ extent_evidence                TOOL   C13.
```

- Each node is a set path with no decisions inside it, so each is a tool (the owner's rule). A node becomes a child episode
  only if it turns out to be a long job on an outside service.
- What the arm returns to the root: the readings it proposes (each a set of positions on a strand, what kind of feature, the
  code, whether an end is cut off, how sure), candidate annotations of features, regions and the piece, and its rows for the
  claims it was asked to check.
- What the arm receives from the root: the piece (or the protein), the reading of the piece the root holds, the grouping of
  names it holds, and the candidate annotations or claims to work on.
- As a verifier it checks claims about place: "encoded in the organelle or in the main genome", "beside X", "part of one
  operon with X", "native to this genome". The root cannot write such claims yet.

## What this asks of the rest of the system

- The root holds a piece and its readings, not one protein: it decides which feature to work on next and what each is worth.
- The root's sheet takes annotations of any set of positions (a gene, a region, the piece).
- The other arms return their evidence with positions, so it can be read under a revised reading.
- The claim maker gets kinds of claim about place.
- The intake takes DNA.

## Order of building (not the design's scope)

1. The bare sequence first (the owner: "the easiest to build"): `describe_piece`, then `find_genes` for genes without introns
   and `find_rna_genes`.
2. `predicted_neighbourhood` and `neighbourhood_check`.
3. The rest; genes with introns, the placement of reads and whole-genome comparison are heavier and come later.

## What was checked on 2026-11-23, and what was not

- Installed here: the gene finder library `pyrodigal` 3.7.1 (importable; no run made; how it handles short pieces is not
  verified), Infernal 1.1.5 with Rfam 15.1, BLAST+ 2.17, minimap2 2.31. Not installed: a finder for genes with introns, Mauve
  (the library has readers for its format), a lineage classifier with its own database.
- Seen live in BV-BRC: a feature carries its position, strand, global family and the hash of its exact sequence.
- None of the thirteen analyses was run.
- The old A103 head (`root/a103/gene_context_evidence`, old-runner children, does not load on the current system) and its
  library folders (`episode_support/*/gene_context_evidence`) were not read. That inventory (SOP Step 0A item 7) is still to do.
