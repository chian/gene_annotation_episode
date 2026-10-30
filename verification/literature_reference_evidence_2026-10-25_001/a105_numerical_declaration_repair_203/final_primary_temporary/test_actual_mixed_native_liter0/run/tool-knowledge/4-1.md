# Selected columns from a retained BLAST HSP

`result.blast.hsp` reads one explicitly received HSP observation. Supply its
`observation_ref`, a zero-based `column_offset`, and a `column_limit` from 1 to
4096. These coordinates select alignment columns, including gaps. They are
different from query or reference sequence positions. Offset equal to the
available alignment length returns an empty terminal page; a larger offset is
invalid. The selected observation and its complete original HSP must lie within
the assigned scope and be present in the child's received inputs.

This is a supplied-result read in the scientific child. It uses retained NCBI
BLAST JSON HSP data or an actual retained native paired BLAST JSON15 or declared
tabular HSP from the authenticated original result, covering blastn,
blastp, blastx, tblastn and tblastx. It launches no alignment or database search,
acquires no full reference sequence, and selects no alternative HSP or resource.
The original API execution and its submission ancestry remain separate facts.
Native paired observations retain their own bundle, captured report, original
search/hit/HSP ordinals and complete original operands. They do not acquire an
API request or RID. JSON translated negative frames can have ascending native
endpoints; tabular endpoints are directional. The retained actual format
determines this interpretation, including when recalculating a saved sheet.

The response preserves the requested native string window, its realized extent,
the total available columns and the next offset when another page exists.
Column correspondence includes both native symbols, zero-based half-open
intervals in the original query/reference operands, their explicit units, and
the reported frame and strand. A translated amino-acid column consumes three
nucleotide units on that translated operand. Reverse intervals keep ascending
bounds and a separate direction. Native amino-acid symbols do not reconstruct
nucleotides. A gap has no corresponding interval. Separately supplied original
derivation mappings can retain ordered split codons, repeated segments and
source orientation; absent ancestry remains unavailable.

Selected-window measurements count paired columns, identical uppercase native
symbol pairs, substitutions and each operand's gap columns. Literal equality
of an ambiguity symbol does not resolve its underlying residue. Paired identity
uses the paired-column denominator; alignment identity uses all selected
columns. Paired coverage uses the union of checked paired intervals divided by
the complete corresponding operand length in its native units. Every ratio
retains its numerator and denominator. Native bit score, alignment score and
E-value retain their whole-HSP meaning and do not enter these window ratios.

Missing strings give unavailable window counts. Readable strings with invalid
coordinates can retain string counts while positional coverage is unavailable.
Reported extent or midline conflicts also prevent checked positional mapping.
An empty terminal window has zero counts and null identity. A measured zero
score remains zero. Complete native input, sheet and separate calculator output
are retained for recalculation; return only the requested bounded facts.

Reading and calculation create no new scientific source or observation, no
annotation confidence and no separate credit. Original HSP measurements and
prior history remain unchanged. Repeated representations or separate pages do
not become independent scientific evidence.
