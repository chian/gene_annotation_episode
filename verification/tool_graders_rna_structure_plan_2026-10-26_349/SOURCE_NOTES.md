# Source attribution and limits

Official primary documentation read on 2026-10-26:

1. [ViennaRNA Python API](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/api/python.html),
   `RNA.fold` and `RNA.fold_compound.mfe`: the former uses default model settings;
   explicit fold compounds allow supplied settings. Energy is kcal/mol.
2. [Minimum Free Energy API](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/api/mfe.html),
   global MFE interface: a sequence structure accompanies its native energy.
3. [Free Energy Evaluation API](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/api/eval.html),
   energy evaluation and parameter I/O: `eval_structure` evaluates the supplied
   structure with its fold compound model; `params_load`,
   `params_load_RNA_Turner2004`, and `params_save` load/save parameter data.
   Documented load/save return nonzero on success. Parameter loading precedes
   model construction because the RNA loading helper resets geometric defaults.
4. [Official RNAfold tutorial, MFE example](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/usage/tutorial/RNAfold.html#mfe-structure-of-a-single-sequence).
   Exact native example excerpt (also saved as `documented_mfe_output.txt`):

   ```text
   CUACGGCGCGGCGCCCUUGGCGA
   ...........((((...)))). ( -5.00)
   ```

   This is documented output, not a locally retained native run. The original
   run's exact software/model snapshot is not supplied. The printed -5.00 is
   preserved at its reported precision. It is not evidence that the missing
   local Python package works. The same tutorial distinguishes separate
   partition-function work; MFE alone does not establish ensemble confidence.
5. [RNA structure formats](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/usage/io/rna_structures.html)
   and [RNAfold manual](https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/usage/man/RNAfold.html).
   The selected simple nested dot-bracket grammar is distinct from pseudo
   dot-bracket probabilities and extended crossing-pair representations.
   The CLI can convert T to U; the proposed binding does not silently do so.

The intermediate attempted URL `/doc/html/io/rna_structures.html` returned 404;
the correct official path is `/doc/html/usage/io/rna_structures.html`. A search
snippet also advertised a different CGAC... example that was not present in
the fetched current manual. It was not adopted into the packet.

The source wrapper observations come from complete inspected upstream functions
and actual retained `probe_upstream/probe_records.json`, not a description or
these external documents. All raw probe stdout and stderr remain available.
No external source overrides the authoritative user attachment or its 16
principles. No native prediction success is inferred from documentation.
