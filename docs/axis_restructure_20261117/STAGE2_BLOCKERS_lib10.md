# Stage 2 blockers, scope readers/ and tools/ (agent lib10)

1. A read selection's members. The five `tools/<axis>/tools.py` copies (sequence_homology, structural_homology, gene_context, evolutionary_history, partner_presence) read
   `SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref` to write the `queries.fasta` of a read mapping.
   Call needed on the scoped store and the reader: `store.selection_members(selection_ref)` returning the `read_ref`s of the held read selection in order
   (the selection must be held; each member is then read through the Store). The files carry this call; it does not exist yet.
