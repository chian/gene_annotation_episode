# Pairwise sequence and selected-read alignment

`sequence.align` compares the supplied query and reference sequences.
`reads.align` compares each explicitly selected original read with the supplied
reference, preserving separate results and failures. Choose protein, DNA or RNA
and local or global alignment in the actual input contract. These operations
run Biopython pairwise alignment through the bounded local execution binding.
They do not search a sequence database or select another resource.

Use local alignment to inspect matching regions and global alignment to compare
the complete supplied operands under the recorded scoring model. Retain the
actual matrix, match/mismatch and gap parameters with the result. RNA inputs
retain their declared molecule; the native alignment normalizes U to T.

The retained output includes both gapped strings and zero-based, half-open
coordinate paths. The numerical sheet distinguishes paired residues,
identical pairs, substitutions, gap columns and residues aligned to gaps.
`paired_identity` divides identical pairs by paired positions;
`alignment_identity` divides them by all alignment columns. Paired coverage
divides paired positions by the complete corresponding operand length;
aligned coverage also includes that operand's residues opposite a gap.
The sheet preserves each denominator. Literal equality of ambiguity symbols
does not resolve the underlying residue.

An explicit local no-alignment result has zero aligned positions and unknown
identity. Invalid geometry cannot provide positional coverage. Native alignment
scores are model-dependent scores, not probabilities of function. Return only
the requested numerical components and correspondence; complete strings and
sheets remain retained for later explicitly scoped use. Parsing and calculation
belong to the same selected result action and do not create additional turns.
