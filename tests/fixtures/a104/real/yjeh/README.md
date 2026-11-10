# Original YjeH/APC inputs

These required inputs are original UniProt REST JSON responses acquired on
2026-11-04 for the real A104 investigation. They are inputs, not execution output
or expected functional answers.

The four `family-*.json` pages requested 12 bacterial nonfragment proteins per
exact gene-name lead (yjeH, adiC, cadB, potE), with lengths 250–700. These labels
selected a broad comparative panel; their product descriptions do not establish
an experimentally characterized function. The original anonymous target is the
418-residue peptide of P39277. Distinct records and taxa are preserved, including
identical sequences; their occurrences are not independent functional tests.

`yjeh-organismal-markers.json` requested three independent ribosomal marker
families (rplB/rpl2, rplC/rpl3, rpsC/rps3) in eight actual sampled taxon IDs:
83333,1042163,588858,1918946,225345,54291,61651,1691940. All eight had one unique
peptide per marker in the acquired page. This supports an inferred three-marker
reference tree with explicit sampling and orthology assumptions. It does not
constitute a measured whole-genome species tree or a biological root.

The reusable offline builder is `tools/a104_inputs.py`. It preserves original
response hashes, verifies membership and records missing or ambiguous marker
sets. Native alignments, tree inference, reports and all execution receipts live
under the investigation's local/remote run directories. Individual markers must
be aligned separately before concatenation.
