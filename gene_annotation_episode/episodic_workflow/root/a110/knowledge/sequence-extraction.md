# Sequence extraction and oriented views

`sequence.view` creates a reusable view of a supplied sequence, feature or
product. It is a supporting transformation. The chosen processing model does
not classify the original material or provide independent evidence of function.

The operation is local. Select it through the existing child tool binding with
`subject_ref`, required `molecule` (`dna`, `rna` or `protein`), optional
`segments` and optional `orientation` (`as_is`, the default, or
`reverse_complement`). Each segment has integer `start` and `end` in zero-based,
half-open input-symbol coordinates. Omitting segments selects the whole input.
Segments must be nonempty and within the supplied sequence. Their order,
repetitions and overlaps are meaningful: the operation concatenates exactly
that selection before applying the requested orientation.

`as_is` preserves every symbol and its case, including unusual symbols. Reverse
complement requires nucleotide symbols and a DNA or RNA model; it is undefined
for protein. Both T and U complement to A. A complements to T for the DNA model
and U for the RNA model. Ambiguity symbols and lowercase letters retain their
corresponding complement and case. Reverse complementation reverses segment
traversal as well as symbols within segments.

The actual result retains the complete output sequence, effective input
segments, orientation, selected model, lengths and coordinate convention.
Publication retains its original source and derives a reusable product with
the supplied exact original-source path. Views of translated products retain
three original nucleotide units per protein symbol, including split codons and
separate source identities. Original source units are never inferred from the
selected model. A reference sequence remains evidence, not another target.

The separate extraction reader and calculator compare actual output symbols
with the supplied selection. They retain requested and verified correspondence,
counts of selected occurrences, distinct input positions, repeated selections,
output lengths and case-sensitive matches/mismatches. Physical-source coverage
is reported separately for each original source identity and unit. Missing
ancestry stays unavailable; partial comparisons retain their actual denominator.
Length agreement alone does not validate symbol correspondence. These components
are transformation checks, not annotation confidence. Complete numerical sheets
stay in retained grading artifacts; request only the facts needed for the
receiving investigation through its existing typed return form.
