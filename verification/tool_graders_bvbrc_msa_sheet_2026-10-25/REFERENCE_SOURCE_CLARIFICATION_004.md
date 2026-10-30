Reference string provenance clarification, 2026-10-25.

Root inspected the retained App-MSA.pl lines 481–485: the source trims leading
and trailing whitespace from ref_string; for ref_type='string' it writes that
string and a newline to input.fasta. It does not insert a FASTA header. This
provider therefore does not synthesize a reference header from a bare sequence.
This is a retained-source fact, not a live deployed-version observation.

The unchanged saved record can prove reference identity only using the exact
original inline InputBinding value, the already parsed InlineSequenceInput,
a unique full MemberKey occurrence and resolved row association, and exact
simple transformation records leading to the selected row. The sheet validator
checks these retained relationships without invoking an inline/native parser.
The whole sequence is compared under only explicit identity, rename, uppercase,
remove_symbols and align_insert_gaps records. Complex transformations lacking
sufficient unchanged-record proof leave reference identity unresolved; their
explicit original coordinate maps remain retained independently.

Missing or contradictory reference proof downgrades the extracted identity to
unresolved and records msa_reference_unresolved. Original request parameters
remain unchanged. Calculations use the qualified sheet reference, permitting
only the original resolved declaration to become unresolved, never the reverse.
Independent staged differences remain available. A saved identity cannot be
upgraded by changing only the state; exact input and occurrence proof is checked.
