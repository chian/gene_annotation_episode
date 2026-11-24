# Parts discovery: the arm that says what is in a piece of DNA

Status: design agreed with the owner on 2026-11-23 ("That now seems more sensible to me. Wrote it down, then send subagents to
build it. Don't touch root yet but assume you will be recoding the annotation object and scoring to alter the base type to
reflect a set of annotations with coherence"). Nothing was built when this was written.

## What the arm is

It came out of the design of the context arm (`a103_tree.md`). The owner: "Maybe this is just the parts discovery arm"; "Maybe
those both being as separate things under the root". Two arms:

- Parts discovery (this note): what are the parts in this piece of DNA, and where does each begin and end. It needs no
  annotation and comes first. It is not one of the nine evidence axes: it makes the subjects they work on.
- Context (`a103_tree.md`): how the parts relate, and which account of a stretch fits them together.

Like A102 it both proposes and checks (the owner: "looking for something that might be there is really a claim check"):

- It proposes parts: "a gene at these positions", "an RNA gene here", "a repeat here". These say what kind of thing is at
  some positions, not what it does.
- It checks claims about what is there: existence ("a Y is in this stretch"), extent ("this gene starts earlier"), unity
  ("these two calls are one gene", "this call is two"), kind ("this call is not a gene"), the genetic code of the piece.
  The claims come from the context arm, from where the other arms' evidence ends, and from the root's claim maker, always
  through the root.

A check has three answers: found (how well, where); looked properly and not there; could not look (with the reason). That
the first pass called no Y is not evidence that Y is absent: nobody looked for it.

## Rules it is built on (the owner, 2026-11-23)

- The start is "an arbitrary piece of dna of any size"; a protein given directly joins after the gene finding.
- The genetic code is "frozen except in a few specific examples": the default first; another only when a special case is
  triggered, by lineage or by how the genes come out under the default.
- Every reading is revisable, and "Revision means all revisions". The piece is the one fixed thing; a part is a reading of
  positions on it; evidence is anchored to positions; the root decides the reading it holds and passes it down.
- Tool or child: "Search for part is a tool if it is a fixed workflow, called the same way for any part. It is an iterative
  workflow if different tools can be used for different things under different circumstances."
- The arms do not do each other's work. What another arm can evaluate goes up to the root (for example a model of a protein
  family from its relatives is the sequence arm's work; this arm asks for it and receives it).
- It is not "merely a set of tool calls": the first pass is, the rest is thought (what is missing, what is doubtful, which
  check would settle it for its cost).

## The head's cycle

1. The first pass is owed once (no choice).
2. Look at the reading as it stands: what is missing, what is doubtful, which claims wait.
3. Choose the one check that would settle the most for its cost; commission it.
4. Revise how sure each part is. Stop when no remaining check is worth its cost (the forecast yield controller).

## The subtree

```
parts_discovery                       HEAD   Its cycle improves the reading of one piece. Commissioned on a piece of DNA,
│                                            or on claims about what is there.
│   the first pass (owed once; fixed workflows)
├─ describe_piece                    TOOL   Composition and signature of the bare DNA.
├─ find_genes                        TOOL   Protein genes. One field: the genetic code, from a fixed list.
├─ find_rna_genes                    TOOL   RNA genes, by family models.
├─ find_known_elements               TOOL   One class per call: repeats, mobile elements, CRISPR arrays, terminators,
│                                           promoter and ribosome-binding sites, origin boxes.
│
├─ part_search                       CHILD  One claim: "a Y is in this stretch". Chooses the method that fits what Y is.
│   │                                       Its cycle improves the answer to that claim.
│   ├─ scan_with_protein_model       TOOL   A family model over every frame, across frame breaks.
│   ├─ scan_with_rna_model           TOOL   A structure-aware model of an RNA family.
│   ├─ scan_with_site_model          TOOL   A short site model.
│   └─ scan_for_repeat_structure     TOOL   Repeat arrays and inverted repeats.
│
├─ reading_revision                  CHILD  One proposed change to the reading. Gathers the evidence that fits the kind of
│   │                                       change. Its cycle improves how sure that change is.
│   ├─ start_site_evidence           TOOL   Ribosome-binding site; where relatives begin.
│   ├─ frame_break_evidence          TOOL   One family model spanning two calls in different frames.
│   ├─ coding_evidence               TOOL   Coding signal of a call against the piece; overlaps.
│   └─ extent_evidence               TOOL   Where passed-down evidence runs past a part or stops short.
│
└─ motif_discovery                   CHILD  A motif nobody named in advance. Its cycle improves one motif's model and its
    │                                       list of sites.
    ├─ collect_stretches             TOOL
    ├─ propose_motif                 TOOL
    ├─ build_model                   TOOL
    └─ scan_piece                    TOOL
```

- The head decides which doubt or claim is worth working on next; each child decides how to settle the one thing it was
  given; each tool is one fixed measurement.
- The first-pass tools pass the owner's test for a tool: run the same way for any piece; which code and whether the piece is a
  fragment follow from fixed rules.
- The scan methods and the kinds of evidence are a first list from how the field works; there may be more of each.

## What passes

Up, to the root:

- the parts, each with its positions (one stretch, or several joined), strand, kind, the code it was read under, whether an
  end is cut off by the end of the piece, and how sure the reading is;
- proposed revisions with their evidence (the root decides the reading);
- one row per claim checked: found, looked properly and not there, or could not look;
- requests it cannot fill itself ("a model of family Y is needed", "where do this gene's relatives begin").

Down, from the root: the piece; the reading the root holds; the claims to check; models and position-anchored evidence other
arms produced.

## Scores and credit

- The annotation score of a part is how well its reading is supported (state, recomputed from what the head holds).
- Credit is progress, tied to changes in those scores: a part admitted; a test that moves the two leading readings of one
  stretch differently (two starts, joined or separate, gene or not); a check that settles a claim. A repeat earns nothing.
  Revisions follow `a102_regrouping.md`: only above the best reached so far.

## What is assumed about the rest of the system

The root is not touched now. The owner: assume the annotation object and its scoring will be recoded so that the base type is
a set of annotations with coherence. So this arm returns its parts as annotations of spans (positions, kind, how sure), ready
to be members of such sets, and its rows per claim; it does not depend on the root's present one-protein sheet. Until the
root takes it, the head is run as the entry with the root's commission supplied in the run setup.

## Order of building

1. The head with the first pass: `describe_piece`, `find_genes`, `find_rna_genes`, on a real piece of bacterial DNA.
2. `part_search` with `scan_with_protein_model` and `scan_with_rna_model`.
3. `reading_revision`.
4. `find_known_elements`, `motif_discovery`, the remaining scans.
Genes with introns are in the design (a part may be several joined stretches) and are built after the above.

## What was checked on 2026-11-23, and what was not

- The intake takes DNA (`init --molecule dna`; formats fasta, fastq, genbank among others): read in the code, not run.
- A head in any folder under `root/` is found by its name (`run_command._folder`), so this arm lives at
  `root/parts/parts_discovery`.
- Importable here: `pyrodigal` 3.7.1 (a gene finder), `pyhmmer`, Biopython, numpy. Installed: Infernal 1.1.5 with Rfam 15.1,
  Pfam, BLAST+ 2.17, minimap2 2.31. Not installed: a finder for genes with introns; anything specific to repeats, CRISPR
  arrays, terminators or motif discovery.
- No tool of the subtree was run.
