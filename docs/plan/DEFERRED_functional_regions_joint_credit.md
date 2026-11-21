# Functional regions and joint credit: deferred design (2026-11-20)

**Status: DEFERRED.** The owner decided this waits until the base function of each individual axis is in better
shape. Nothing here is built, scheduled or tested. It is recorded so it can be picked up later without
reconstructing the conversation. It is written for the new paradigm (AGENTS.md): controlled messaging, custody,
credit from held records, stopping by the yield estimator. Old-structure specifics were deliberately not carried.

Marks: **[owner]** = said by the owner. **[inference]** = proposed by Claude, not yet accepted.

## What a region is for

- **[owner]** A region confirms that a key function or sequence feature exists. It does not make a hit better, and
  a small region has little scoring power, so it is never a magnitude added to a correspondence score.
- **[owner]** The regions and the reference sequence are defined from outside and need an experimental anchor. They
  do not come from the sequence-homology tools.
- **[owner]** Region work does not belong in A101. A101 keeps producing alignments and their sheets; it does not
  interpret regions.

## Certainty

- **[owner]** A region on a close homolog counts more than one on a distant exemplar, because the mapping is more
  certain. A region that holds across many exemplars in an alignment counts more again. A chain to something certain
  to map to is strong.
- **[owner]** A single distant sequence carries two uncertainties: is it the same function, and were the regions
  lined up correctly.
- **[inference]** Keep those two as separate recorded quantities and combine them only in scoring, so the formula can
  change later without losing data.
- **[inference]** Near-duplicate exemplars are not independent support. Counting independent exemplars needs
  clustering (this is a use for the clustering of the A101 `all_vs_all` child).

## Outcomes, support and credit

- **[owner]** Region confirmation can confirm or deny a region. Denial is possible when sequences are far enough
  apart, so it can lower support as well as raise it.
- **[owner]** Credit is progress. Lowering support still earns credit, because knowledge is now sharper.
- **[inference]** Outcomes are confirmed, denied or indeterminate. Indeterminate earns nothing and is not a denial.
- **[inference]** Credit is the gain in certainty over what was already known, symmetric for confirmed and denied.
  Repeating a held determination earns nothing. Credit falls only when an established fact is lost.
- **[owner]** Credit design: the joint design made more sense (shared credit with a joint term). A105 and A106 are
  credited for evidencing regions; the alignment side is credited through A101's ordinary credit for the alignments
  it produces; a joint term is earned only when both exist for the same region and target.
- **[inference]** The joint term counts only the increment over the base experimental evidence, so one experiment does
  not pay twice.
- **Not decided:** exactly how the alignment side is credited now that confirmation is not an A101 episode.

## Design in the new paradigm

All of this is a proposal for the owner to strike or correct.

- **Region record.** A record in custody with controlled fields only: the exemplar sequence, the position or
  interval, the expected residues, a role from a fixed vocabulary, the perturbation type, the effect direction, the
  evidence type, and a reference to the source observation. It is written through the producing episode's own
  custody, so the producer is the only place it can be created. The producer runs the numbering check: the stated
  residue at the stated position must match the exemplar, or the record is unresolved.
- **Producers.** The experimental axes (A105 for assays on constructs or fragments, A106 for substitution, deletion
  and truncation experiments), and any other axis that holds an experimental anchor.
- **Commission down.** The root asks an experimental axis for region evidence with controlled values and record
  references only: the proposed annotation and the exemplar sequences, each as a record reference. No paragraph and
  no free-text ask.
- **Return up.** The axis declares what it can return, including references to the region records it produced. The
  parent selects them. Credit and finding are always returned.
- **Alignment.** The root commissions an ordinary alignment run (a pairwise run, or a database or all-vs-all run) between exemplar
  and target, passing both sequences as records. The pairwise chain already works at leaf level.
- **Projector at the root.** A deterministic composition. It reads only the records it actually received or produced,
  through the custody reader: the region records and the alignment sheets, as references passed up. It computes the
  per-region facts (outcome, mapping certainty, functional-equivalence certainty, number of independent exemplars)
  and the joint credit. Its credit comes from the records it holds, and stopping stays with the yield estimator.

## Facts known about A105 and A106 today (from a read-only review, not independently verified)

- Neither axis has a field for a mutation, truncation, segment or variant. A construct is an opaque identity used to
  check sameness across arms. A mutation name such as "D52N" would currently live only in a free-text label.
- Coordinates exist only on the target side. No record carries positions on an exemplar.
- Neither axis's sheets or controlled features hold anything region-like. The A105 sheet defers the correspondence
  between exemplar and target.
- Homolog versus target evidence is already kept apart by an applicability field and separate subject and
  source-subject references.
- A new record type, beside the existing reference and feature records, would be needed to carry segments on an
  exemplar.

## Re-entry criteria (when to pick this up)

The base function of each axis involved is in better shape, meaning at least:
1. A105 and A106 each run for real at leaf level and up to their own roots.
2. The A101 pairwise chain works through its parents to the head.
3. The root composition (shared-root credit from retained records) works for the axes already composed there.

## Withdrawn

Questions about extraction-episode sections, reasoning-commit sections and "final sheets send findings upward" came
from reading the old structure and are withdrawn; the design above restates that ground in the new paradigm.
