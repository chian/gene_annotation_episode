# Organism identification: the head that says which organism a piece of DNA is from

Status, 2026-11-24: tools installed and measured on real pieces; the head `root/organism_identification` is built with one
tool, `kraken2_classify`, and returned from its first real run (`runs/organism_identification_20261124`, run 01: the
hepatitis E genome, two classifications, stopped by its own yield estimator, species Paslahepevirus balayani at score 1.98).
The root does not link it yet; the other tools are not in the head yet. Written by the session that builds the root. An agent's note: the
owner's words quoted here decide, the rest is that session's reading.

## The global task and this head's part

The task is to annotate an arbitrary DNA string with nothing told about it. This head says which organism the DNA is from,
as candidate taxa with scores. It is not one of the nine evidence axes. The root holds its candidates and decides what to
pass down to the other heads (the database a search uses, the genetic code of gene finding, the organism a claim is about).

The owner, 2026-11-24:

- "I think it would make much more sense to add a commission after we add organismal taxa ID potential candidates as a new
  head from root." Earlier the same day, in the parts discovery talk: "so sounds like taxa signatures needs to be separated
  out."
- "make it more generic than for a protein. it should work from a dna sequence." "let's build for dna first. not protein for
  now."
- On taking the organism from the sequence homology head's protein hits: "that's not an intelligent tool choice or way it
  would ever work if we keep adding. b/c adding would give us more appropriate tools. remember to check the tool library for
  anything already existing."
- "i am surprised you aren't using more kmer-based tools like kraken or similar. Mash is a very quick version of this, but
  for smaller sequences, it seems like you could use kmers better."
- "Composition is not to identify but to add to score by being an additional source of coherence between signals."
- "you are going to have to add the viral taxa tools. that will be important to this specific test."
- On VITAP after its live run: "great so use it as is then."
- On wiring: "you need a set of graders and then you need a set of subscoring sheets and scoring sheets and finally you need a
  way to pass this info on taxa candidates to the root who can pass whatever info it decides down to the other children."

## The head's iteration

What its cycle improves: how well the candidate taxa are separated and how deep the placement goes (family, genus, species).
Why iterating pays, measured on the pieces below:

- No tool works at every distance. Exact k-mers name the species of a piece that has a close relative in the index, from as
  little as 300 letters, in seconds; for a distant virus they find nothing. The protein-level virus tools place the distant
  virus, at family or class, and never go below family.
- A tool's database decides what its answer can mean. The viral-only Kraken 2 index called a stretch of the E. coli
  chromosome a phage from 9 k-mers in 60,000; the general index called it E. coli.
- A piece can be of a kind a tool does not cover (VITAP gives a virus answer for bacterial DNA; geNomad scores the same
  piece as not a virus).

## Test pieces (hidden: each is given under a neutral name)

`runs/root_lowvan_20261124/organism_head_inventory.md` and the scratchpad's `organism_queries/KEY.txt` of that session:
piece_1 hepatitis E virus M73218 (7,207 nt, itself in the databases); piece_2 fish-associated hepevirus OP933684 (7,704 nt,
distant); piece_3 60 kb of the E. coli K-12 chromosome (2,790,000 to 2,850,000); piece_4 and piece_5 1,000 nt of piece_1 and
piece_2; piece_6 300 nt of piece_1; piece_7, 8, 9 hepeviruses ON009841, OR232336, OR713884 (relatives of database genomes,
not in them). The genomes are the reference contigs of `modules/Hepeviridae` of github.com/jimdavis1/LowVan_Skill.

## Tools, by program, as measured (one CPU; raw results in the run folders named)

| Program | What it measures | Near (piece_1) | Far (piece_2) | E. coli (piece_3) | Short | Time | Run |
|---|---|---|---|---|---|---|---|
| Kraken 2 2.17.2, viral index (0.6 GB) | taxon of each k-mer, lowest common ancestor | species, 7,093 of 7,173 k-mers | unclassified | "Escherichia phage", 12 of 59,967 k-mers | species from 300 nt | 3 to 4 s | `runs/organism_kmer_check_1` |
| Kraken 2, standard index capped at 8 GB (7.5 GB, read from disk) | same | species | unclassified | Escherichia coli | species from 300 nt | 0.2 to 30 s | same |
| sourmash 4.9.4, NCBI viruses 2025.01, k=21 and k=31, scaled 50 | share of the piece's k-mers contained in each genome | 1.00, then 0.22 and 0.03 to other genotypes | no match | 0.04 to a phage | 1.00 from 300 nt | about 100 s a search | same |
| geNomad 1.13.0 (database 1.9) | kind of DNA (chromosome, plasmid, virus scores); virus taxonomy from marker genes | virus 0.97, family Hepeviridae | virus 0.89, family Hepeviridae | chromosome 0.45, plasmid 0.44, virus 0.11 | family at 1,000 nt with a marker; none at 300 | 518 s for nine pieces at 16 splits | `runs/genomad_run_2` |
| VITAP 1.7.1, ready database (taxonomy release 37, RefSeq 209, IMG/VR 4) | lineage score per rank, every rival lineage, a confidence level | family, 3.19, high | class only, 0.41, medium | Caudoviricetes, 0.21, medium | family from 300 nt, 1.78 | 149 s for nine pieces | `runs/vitap_run_2` |
| Mash sketch (BV-BRC Similar Genome Finder) | distance to each BV-BRC genome | 0.063 to hepatitis E | nothing | not run | not run | 12 s | `runs/organism_dna_probe_2` |
| BLAST blastn against genome sequences (BV-BRC Homology, `viral-reference`, `fna`) | identity and covered length per genome | 6,723 of 7,176 identical | 0 hits | not run | not run | 10 s at the service | `runs/organism_dna_probe_1`, `_2` |
| BLAST blastx, DNA in six frames against proteins (same) | the same at protein level | not run | 12 hepevirus hits, about 29 percent identical | not run | not run | 10 s | `runs/organism_dna_probe_2` |

Not measured yet: vConTACT3 3.1.6 (installed; its database v230, 2.14 GB, was downloading when this was written); Kraken 2
and sourmash on piece_7 to piece_9; sourmash's `skip_m2n3` sketches (need a plugin that is not installed).

Composition (AT content, dinucleotide bias, short-word frequencies) proposes nothing. It is a scoring row: the piece's
composition against each candidate's own genomes (BV-BRC `genome` records carry `gc_content` and `genome_length`; the
`taxonomy` collection carries `genetic_code` and the mean genome length of a taxon). The library holds a GC count
(`calculations/sequence_operations/sequence_ops.py`, `inspect_sequence`) and nothing for dinucleotides or short words.

Heavy, for HPC (the owner, 2026-11-24: "anything that goes over that [10 GB] will need hpc"): Kraken 2's full standard index
(109 GB), VITAP's current version with UniRef90, GTDB-Tk.

## Ground rules for every tool of this head (proposed to the owner 2026-11-24; VITAP: "use it as is")

1. A tool states what it takes and what its database covers.
2. A tool is not offered for a piece it cannot take (its check refuses, its ceiling is 0).
3. Three answers are kept apart: found; looked properly and nothing there; could not look.
4. An answer from a database that cannot contain the truth is read with the general database's answer and with the kind of DNA.
5. No cut-off inside a grader: the tool's own measure of support goes into the score by degree.
6. Every answer becomes NCBI taxon ids with ranks before it enters the scoring sheet, with the database's release recorded; a
   name that cannot be mapped is reported as unmapped.

## Where the software is

`resources/software`: `kraken2-2.17.2-install`, `kraken2-db/k2_viral_20261022`, `kraken2-db/k2_standard_08_GB_20261022`
(each with `index.manifest.json` once written), `sourmash-4.9.4/venv`, `sourmash-db`, `micromamba-2.10.0`,
`genomad-1.13.0/env`, `genomad-db/genomad_db`, `vitap-1.7.1/env`, `vitap-db/DB_hybrid_MSL37_RefSeq209_IMGVR` (its DIAMOND
database rebuilt with DIAMOND 2.2.9), `vcontact3-3.1.6/env`, `vcontact3-db`. geNomad needs `--splits 16` under 5 GiB.

## The wiring, in order (one piece at a time)

1. The head `root/organism_identification`, each file a copy of the file of the same name of `root/sequence_homology_evidence`
   changed only where it must differ, with one tool end to end first: Kraken 2.
2. A grader per tool: the tool's own output as facts per taxon. Kraken 2: `episode_support/grading/taxonomic_classification/
   kraken2_grader.py` (written).
3. A subscoring sheet per tool run: the grader's sheet, kept as a `tool_grading_sheet` data product by the tool's unit
   (`episode_support/tools/taxonomic_classification/kraken2_classification.py`, written; data product kinds
   `taxonomic_classification_results` and `taxonomic_classification_report` added to `records/data_products.py`).
4. The scoring sheet: one row per candidate taxon, each tool's support beside it. Not written.
5. The return to the root: candidate rows (taxon id, rank, score, status) and credit.
6. The root's side: it reads the rows, holds them, and chooses what goes into the other heads' commissions.

Then sourmash, geNomad, VITAP, vConTACT3 and the composition row join the same sheet one at a time.

## One thing with no counterpart in the reference: candidates are nested

In the reference a candidate is a name and two candidates are rivals. Here a candidate is a taxon, and a family contains its
genera and species. The owner's rule, 2026-11-24 (after the session proposed the opposite, support counted upward so that a
family outscored its species): "i think this support from vaguer levels makes sense with the fines grain level having the
most score. never rivals, just different supporting bits of info. rivals are when there is a difference in call that is not
nested."

- Support flows down the lineage: a call at a vaguer level (a family) is a supporting bit of information for every finer
  candidate inside it.
- A candidate's score is the sum of the supporting bits on its own lineage: its own call and every vaguer call above it. The
  finest-grain candidate the signals agree on therefore has the most score.
- A taxon and its ancestor are never rivals. Rivals are calls that are not nested: neither taxon is on the other's lineage
  (two families, or two species of one genus). The differential credit of a test is between the two leading rivals.
- Kraken 2 decides the same way (it sums the k-mers along each root-to-leaf path and takes the leaf with the most), so a
  candidate's Kraken 2 value is the k-mers mapped to the candidate and to each of its ancestors (`kmers_direct` of the
  sheet's rows along `lineage_taxon_ids`).
- The session's reading, not the owner's words: every taxon that received a call is a candidate row, so the root sees the
  nested rows and how much of the leading candidate's score comes from each level.

## Mapping of the head's files (reference: `root/sequence_homology_evidence`)

| File | Same as the reference | Must differ |
|---|---|---|
| `goal.py` | the four members | the text: candidate taxa of the scope's DNA |
| `episode.py` | the binding | no child slots at first, so no `msg_to_child.py`, `read_from_child.py`, `resume_action`, `outcome_pending` |
| `yield_estimator.py` | the forecast yield controller over the head's ceilings | the credit definition record and the epoch name |
| `messages/read_from_parent.py` | scope, scope references, in custody | no proposed annotation, no evidence-axis selection of the process library (the published library has no entry for this head) |
| `task.py` | one request the model fills, one check, one library function that runs and grades | the tools: `kraken2_classify` first |
| `credit.py` | credit from graded sheets; a derived ceiling per action | the candidates are taxa (see above) |
| `messages/internal_summary.py` | held sequences, held runs, the candidate table | taxa |
| `messages/final_to_parent.py` | candidate rows and credit, controlled fields only | taxon id, rank, score, status |
