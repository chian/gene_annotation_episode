# Proposed source-linked raw-weight oracle — not run

This is a verification proposal, not an execution record or production path.
No compiler, native program, test import or scientific calculation was run by
this helper worker. Root owns the frozen native lifecycle with 20 GiB RAM,
4 GiB scratch, zero swap and no invented wall-time limit.

To compare the exact raw operands, compile the pinned retained
`easel/esl_msaweight.c` into a diagnostic-only translation unit with its calls to
`esl_vec_DNorm` and `esl_vec_DScale` intercepted as no-ops. Native GSC/BLOSUM then
write the authentic pre-normalization weights into `msa->wgt`; their singleton
early return still gives 1.0. Do not reimplement the native GSC post/preorder
weight algorithm in the oracle. Include the native vector header before defining
the call-interception macros so the originals' declarations are unaffected.
Link against the retained Easel library with source/build/compiler identities
recorded, and keep any generated source/object/executable/output in the bounded
verification workspace. Neither retained sources nor production execution should
be changed.

For each original digital input, independently call the original native
`esl_dst_XDiffMx`, `esl_tree_UPGMA` and `esl_tree_SetCladesizes` to emit children,
branches and clade sizes. For BLOSUM, call `esl_msacluster_SingleLinkage` to emit
native cluster assignments and sizes. Print doubles at sufficient precision
(17 significant decimal digits or C hex floats) and retain the complete source
alignment and row order. Singleton tree arrays are absent by construction and
should be explicitly represented as the agreed derived empty arrays.

Compare the small synthetic fixtures named in `REPORT.md`, plus authentic
alimask CLI cases that expose the full small map through safe singleton
model-coordinate endpoint requests. Oracle outputs are source-linked diagnostic
measurements and must stay separate from captured native CLI stdout/MM/WT data.
The source-linked oracle is not evidence that the originally selected alimask
binary was built identically; root must retain the executable/profile association
and compare actual CLI map behavior as required by contract 516.
