# Global scoring scheme: note (2026-11-19)

Source: docs/ALL_AXES_ROOT_SCALARS.md (the root discussion before the refactor), read today; plus the owner's direction
in this session. This note replaces my first version, which was framed around one axis.

## What the root discussion says

- The root scores PROPOSED ANNOTATIONS (plural), discovered again at every decision from the work actually received.
  Each actual subject of each proposed annotation has its own score. There is no scalar over different annotations or
  genes; competing annotations are COMPARED, not merged into one number.
- The scientific contribution of each axis to an annotation is kept SEPARATE from the credit a returned child task
  earns. Two things: (1) per-annotation scientific score from the nine axes; (2) task credit (progress).
- Signed: an experiment against a claim is information (opposition); missing homology information is NOT evidence
  against the claim. Support and opposition are combined as `signed_evidence_split_product_v2`: supporting values and
  opposing magnitudes are multiplied separately, then opposition is subtracted from support. These are conventions,
  not calibrated probabilities.
- Each row holds: support, opposition, their difference, the nine-axis vector, a status, and missing reasons. An
  entirely unknown vector has a null score; a measured zero stays scored.
- Comparisons group the same actual subject, original-input region, predicate and declared contexts. Exact ties and
  unscored candidates are kept separately; unknown candidates never numerically outrank negative evidence.
- The episode (the root/head) retains the annotation decision and the next action.
- Axis inputs differ in kind: A101-A104 contribute their native profiles (A101 a value in [0,1]); A105 and A106 and
  A108 contribute signed values from their sheets (for example tanh of the sheet's overall); see the doc's table.

## What this means for literature

Literature evidence is what the literature axes (A105 experimental activity, A106 perturbation, A108 sample context)
score; it enters the global scheme as the signed support or opposition of those axes for each proposed annotation.
It is not a private chain of one axis, and it does not feed one annotation at a time. A piece that cannot change a
per-annotation support or opposition has no role and is dropped (owner rule).

## Still open (I could not make sense of these from the code or docs)

- Which per-annotation inputs the A101-A104 axes take from literature, if any, since the doc gives them their native
  profiles. Owner direction in this session: literature is global, not an A101-specific chain.
- How the refactored root episode discovers proposed annotations at each decision and keeps the decision and next
  action (this doc describes the old SignedEvidenceRootSupport; the refactored root credit reads only axis credits).
