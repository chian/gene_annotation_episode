# A102: DALI and the pairwise structural aligners (verified 2026-11-21)

Facts only; no design. Every request came from this machine with `curl`, User-Agent
`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36`, no name, no email, no
personal identifier. Raw files are under `runs/a102_dali_probe/` (not versioned); LIB =
`gene_annotation_episode/episodic_workflow/episode_support`. Test object: AFDB CspA P0A9X9
(`runs/a102_service_probe/afdb/cspa_model.pdb`, 70 residues).

## Table

| Tool | What it gives that the Foldseek search does not | Runs today how | Needs what |
| --- | --- | --- | --- |
| DALI web server (PDB search) | Z-score from distance-matrix alignment, a Z-score list over the full PDB (2505 hits with Z >= 2 for CspA), per-hit alignment, equivalences, rotation/translation, Pfam per hit | Yes, over plain `http` (port 443 timed out): one multipart POST, results after about 3 min (verified) | No email, no login. A file upload (legacy PDB format). Rate-limited, robots go to a lower-priority queue, results kept one week |
| DaliLite.v5 (standalone DALI) | Same scores locally, no queue; pairwise (`--cd1/--cd2`), all-against-all (`--matrix`), search against own structure set | Not installed | gfortran + gcc + make + perl; its own `dsspcmbi` ships; BLAST+ only for database search; free for academic/non-commercial use only; structures must be imported (`import.pl`) to its `.dat` format; a prebuilt AFDB set (9 GB) is offered, a prebuilt PDB set is not |
| RCSB alignment API (jFATCAT-rigid, jFATCAT-flexible, jCE, TM-align verified; jCE-CP, Smith-Waterman 3D listed, not run) | Pairwise only (not a search). Residue-by-residue alignment, 4x4 transformation per structure, TM-score, RMSD, identity, similarity; FATCAT adds flexible blocks and a similarity score; CE a similarity score | Yes: submit then poll, 0.4 to 4.8 s | No key. Entry ids or an uploaded file or a URL to a PDB/mmCIF file, up to 10 structures, chains of at least 10 residues |
| US-align (installed locally) | Both TM-scores with normalisations, rotation matrix, whole-model oligomer alignment (`-mm 1`), RNA/DNA (`-mol RNA`), non-sequential and flexible modes; 0.017 s for the test pair | Yes: `resources/software/usalign-20261019/bin/USalign a.pdb b.pdb` | g++ to build (done); PDB or mmCIF input |
| PDBeFold (SSM) | Secondary-structure matching, Q-score | Page online; not submitted | The page notice (inside an HTML comment) says it "is unable to process coordinate files uploaded by the user"; no API documented on the PDBe API page |
| FATCAT (local) | Flexible alignment with twists, `FATCAT -p1 a.pdb -p2 b.pdb` | Not installed; server https://fatcat.godziklab.org/ (pairwise, database search) not submitted | Source `github.com/GodzikLab/FATCAT-dist` (Apache-2.0), `make` |

## 1. DALI web server

Host `http://ekhidna2.biocenter.helsinki.fi/dali/` (raw: `server/index.html`, 31,196 B). `https://` on the same host: connection timed out after 30 s (curl) and refused (WebFetch, 128.214.209.18:443); the `http` page and forms work.

**Searches offered** (page text): "Heuristic PDB search - compares one query structure against those in the Protein Data Bank"; "Exhaustive PDB25 search - compares one query structure against a representative subset of the Protein Data Bank"; "Hierarchical AF-DB search - compares one query structure against a species subset of the AlphaFold Database v2" (one organism per search, 40-odd organisms listed, also Viro-3D and VAD models); "beta testing: AF-DB heuristic"; "Pairwise structure comparison - compares one query structure against those specified by the user" (up to 10 targets); "All against all structure comparison" (up to 64 structures, gives a dendrogram). PDB25 query "must have at least three secondary structure elements". Database size on `barcosel/tmp/pdbstat.html`: 734,396 chains in PDB, 82,192 in PDB90, 47,841 in PDB50, 29,709 in PDB25.

**What a submission needs**: "Structures may be specified by concatenating the PDB identifier (4 characters) and a chain identifier (1 character) or, alternatively, you may upload a PDB file." Note on the page: "The Dali server expects 'legacy PDB' formatted files. Convert cif/mmCIF to PDB format before uploading." **Email is optional**: "STEP 2 - Optional data. You may leave an e-mail address for notification when the job has finished. The job title is used as subject heading in the e-mail." (input `name="address"`, no `required`.) The PDB-search form also has a checkbox `name="robot" value="human"` labelled "I'm human." under: "The server is saturated by requests from robots. Requests from self-identified humans go to a higher priority queue." It was not ticked.

**Terms and limits stated** (all of them found; there is no separate terms page on the site): "19.3.2026 - Firewall rules have been tightened to mitigate automated traffic. Requests exceeding the rate limit may be temporarily blocked; please wait ~60 seconds before retrying."; "Megausers please consider downloading the standalone program."; "If the same structure has been submitted recently, you will be redirected to the result page of the previous instance."; results page: "Results will be deleted after one week." Page banner "9 March, 2026. System Status: High network load may delay page rendering." Not found: any documented API, any statement forbidding automated use, any usage limit as a number, any turnaround time. Queue status file `barcosel/tmp/check_dali_queues.html` read "Number of queued jobs 1".

**Programmatic interface**: none documented; the forms post to `/cgi-bin/sans/dump.cgi` (multipart). The pairwise and all-against-all forms use the same URL with `method=pairwise` / `method=matrix`.

**The one search made** (script `server/submit.sh`; cwd `runs/a102_dali_probe/server`):

```
curl -sS -m 60 -A '<UA above>' -D submit.headers -o submit.html \
 -F cd1= -F file1=@../../a102_service_probe/afdb/cspa_model.pdb -F title= -F address= -F method=search -F submit=Submit \
 http://ekhidna2.biocenter.helsinki.fi/cgi-bin/sans/dump.cgi
```

Response `302 Found`, `Location: http://ekhidna2.biocenter.helsinki.fi/barcosel/tmp//6a1d17f83d93335f9a7e98d9756825425d96e65446fc0d5c85//index.html`. Polling that URL (`poll1..4.html`, 30 s apart, then `poll.sh` for the rest): first "DALI - Waiting", then "Dali Server - Queued: Our server is very busy, so your job has been entered into a queue", then results on the fifth poll, about 2.6 min after the submission (file times 13:56:48 to 13:59:25 local). Five polls in total.

**Results** (`server/result_index.html` and the files it links, all fetched once): `s001A.txt` (full PDB, 2,830,586 B), `s001A-25.txt`, `-50`, `-90` (PDB25 subset, 319,866 B for the 25 file), `.html` interactive versions, `s001A.dali.tsv` (1,770,360 B, 2505 rows). Text file layout: header `# Job:`, `# Query: s001A`, `# No: Chain Z rmsd lali nres %id PDB Description`, one row per hit, then `# Structural equivalences` (residue ranges), then `# Translation-rotation matrices`; the `.txt` rows are Z >= 2.0 (lowest 2.0, highest 15.4). First rows: `1: 1mjc-A 15.4 0.8 69 69 100 MOLECULE: MAJOR COLD-SHOCK PROTEIN 7.4;`, `2: 8xyf-B 14.7 0.8 67 67 70 ENDOLYSIN`, `3: 3i2z-B 14.7 0.8 67 67 72 RNA CHAPERONE, NEGATIVE REGULATOR OF CSPA`. TSV columns: `query database sbjct z-score rmsd ali-length sbjct-length seq-identity sbjct-sequence compressed-sbjct-dssp description qstarts sstarts lengths rotation translation all_pfam` (the 1mjcA row has rotation 9 numbers, translation 3, Pfam PF00313 4-69 E 1.1e-31). The PDB25 file's first hit is 9xw3-A Z 11.6 (CspB-like, %id 45).

## 2. DaliLite

Official page `http://ekhidna2.biocenter.helsinki.fi/dali/` "Software": "DaliLite.v5 (last update 11 April 2025)" (manual `README.v5.html`, saved `dalilite/README.v5.html`); also "A Docker image of DaliLite.v5 is available" and "DaliLite is now on GitHub" (`github.com/liisaholm/DaliLite.v5`, size 347 kB metadata, pushed 2026-05-08).

- Download: `wget http://ekhidna2.biocenter.helsinki.fi/dali/DaliLite.v5.tar.gz`; HEAD: 200, `Content-Length: 1126434`, last modified 11 Apr 2025. Not downloaded.
- Licence (GitHub `LICENCE`, `dalilite/LICENCE`), quoted: "DaliLIte is free software for academic and non-commercial use. Redistribution and use in source and binary forms, with or without modification, are permitted for non-commercial purposes provided that the following conditions are met" (retain notice; reproduce in binaries; "Publications resulting from use of this software must cite: Holm L (2019) Benchmarking fold detection by DaliLite v.5. Bioinformatics 35, 5326-5327"); "Use of this software for commercial purposes, or incorporation into a commercial product or service, requires prior written permission from the copyright holder." The file still carries template placeholders ("Copyright (c) 2024, [Your Name / Your Institution]", "Contact [your email]"); GitHub reports the licence as "Other / NOASSERTION". Redistribution: allowed for non-commercial purposes with the conditions above.
- Needs (manual "System requirements"): "Linux OS; openmpi; Fortran-90 and C compilers; Perl; Blast; Internet connection"; "openmpi is optional, the software can be run serially"; tested "on Red Hat Linux operating system, gcc 4.8.5 and mpirun (Open MPI) 1.10.7"; build `cd DaliLite.v5/bin; make` ("ignore Warnings"), `make parallel` for MPI. DSSP: "The distribution package includes dsspcmbi, Elmar Krieger's version from 2000, which compiles correctly with gcc 4.8.5"; newer `mkdssp` can be used by editing `$DSSP_EXE` in `dali.pl` ("--output-format=dssp"). BLAST (`blastp`, `makeblastdb`) is used only for the database-search options (clustering of the PDB); the "Internet connection" is for `--rsync` mirroring and the `--walk` search ("The knowledge base is accessed remotely over the Internet"). Limits: 10,000 residues per PDB entry; 200 secondary-structure elements per structure ("the program crashes otherwise", digest page).
- Usage: `import.pl --pdbfile f.pdb --pdbid xxxx --dat DAT` (pdbid exactly four letters; chains appended, five-letter ids like `1pptA`; `.gz` accepted); `dali.pl --cd1 1pptA --cd2 1bbaA --dat1 DAT --dat2 DAT --outfmt "summary,alignments,equivalences,transrot" --clean` or `--pdbfile1/--pdbfile2` directly (pairwise uses structure data only, no external programs); `--query q.list --db target.list`; `--matrix` (all-against-all); `--hierarchical --repset pdb70.list --db pdb.list` and `--walk` (database searches). Output `<query>.txt`: "# No: Chain Z rmsd lali nres %id PDB Description" summary, "Pairwise alignments" with DSSP strings, "Structural equivalences", "Translation-rotation matrices" (`-matrix "... U(1,.) ..."`); "Structural alignments with a Z-score above 2 are reported"; `applymatrix.pl` superimposes. Alignments use C-alpha only.
- Database: no prebuilt PDB set. For PDB searching "You must mirror the PDB database and prepare a local PDB-Blast database" (`import.pl --rsync`, `dat2fasta.pl`, `makeblastdb`, CD-HIT for PDB70). A preprocessed AlphaFold DB for DaliLite is offered (`dali/digest.html`: "compressed size 9 Gb uncompressed size 36 Gb", Zenodo record 19221154, not reachable by curl: 403). The repository holds only toy structures.
- Run time: the manual states none (grep for minutes/hours/seconds found nothing); the server page says only that the hierarchical search "uses 40 processes" in its example (`--np 40`). No per-1000-structure figure exists in the documentation.
- This machine: `which gcc g++ make perl` gives `/usr/bin/gcc /usr/bin/g++ /usr/bin/make /usr/bin/perl`; `gfortran` not installed (apt candidate `4:15.2.0-5ubuntu1`); apt `dssp` candidate 4.5.7-1 (not needed, DaliLite ships dsspcmbi); apt candidates `openmpi-bin` 5.0.10-1, `mpich` 4.3.2-2; BLAST+ 2.17.0+ is already in `resources/software/ncbi-blast-2.17.0+`.

## 3. Other searchers

- **PDBeFold (SSM)**: `https://www.ebi.ac.uk/msd-srv/ssm/` answers 200 (title "PDBe < Fold < EMBL-EBI"); `https://www.ebi.ac.uk/pdbe/pdbe-fold/` is 404. Comment in the page source: "PDBeFold currently is unable to process coordinate files uploaded by the user." (also an old maintenance notice dated Sep 2025 in a comment). The PDBe API documentation page (`pdbe/api/doc/`, 73 kB) contains no mention of fold or SSM. Not submitted.
- **FATCAT**: server `https://fatcat.godziklab.org/` (200): "PAIRWISE ALIGNMENT", "DATABASE SEARCH" and "HOMOLOGY SEARCH" functions, no API documented on the page; `http://fatcat.burnham.org/` unreachable. Source `https://github.com/GodzikLab/FATCAT-dist` (Apache-2.0 per GitHub, last push 2023-01-13): build with `make`; example `FATCAT -p1 1a21A.pdb -p2 1hwgC.pdb -o 1a21A_1hwgC -m -ac -t`. Paper: FATCAT 2.0, NAR 2020 (gkaa443).
- **RCSB pairwise structure alignment** (`https://alignment.rcsb.org/`; OpenAPI at `/api-reference.json`, ReDoc at `/api-reference.html`; JSON schemas under `/schema/request/` and `/schema/response/`, saved in `rcsb/`).
  Docs page (`rcsb.org/docs/tools/pairwise-structure-alignment`): methods jFATCAT-rigid, jFATCAT-flexible, jCE, jCE-CP, TM-align, Smith-Waterman 3D; "You can select up to 10 structures per comparison"; "Selected polymer chains must be at least 10 residues long"; "The structure must include C-alpha backbone coordinates"; uploads (.cif .bcif .pdb .ent) or "a URL to an mmCIF or PDB file" allowed. API method names in the schema: `tm-align`, `fatcat-rigid`, `fatcat-flexible`, `ce`, `ce-cp`, `smith-waterman-3d`. Inputs per structure: `{"entry_id","selection"}`, `{"format":"pdb|mmcif","selection"}` (file as multipart part), `{"url","format","name","selection"}`; selection `{"asym_id" (label_asym_id, case sensitive),"beg_seq_id","end_seq_id"}`; option `return_sequence_data` (default true). Limits: no rate figure stated.
  Request (script `rcsb/run_rcsb.sh <method>`; `req_<method>.json` holds the query):
  `POST https://alignment.rcsb.org/api/v1/structures/submit?query=<url-encoded JSON>` with header `Content-Type: application/json` (without it: HTTP 415 "Content-Type 'null' is not supported"). Query: `{"context":{"mode":"pairwise","method":{"name":"tm-align"},"structures":[{"entry_id":"1MJC","selection":{"asym_id":"A"}},{"entry_id":"1C9O","selection":{"asym_id":"A"}}]},"options":{"return_sequence_data":true}}`. Response body: the job uuid. Then `GET .../api/v1/structures/results?uuid=<uuid>`: first `{"info":{"status":"RUNNING"}}`, or HTTP 404 "No such UUID" for the first seconds, then `status":"COMPLETE"`. Submit endpoint: 6 requests (two early 415 failures, four jobs); polls not counted.
  Results for 1MJC.A (69 res) vs 1C9O.A (66 res) (`rcsb/result_<method>.json`, `time_<method>.txt`; seconds from submit to result):

  | method | TM-score | RMSD A | pairs | identity | extra summary scores | seconds |
  | --- | --- | --- | --- | --- | --- | --- |
  | tm-align | 0.87 | 1.12 | 66 | 0.58 | none | 0.4 (first poll RUNNING, complete 5 s later) |
  | fatcat-rigid | 0.87 | 1.12 | 66 | 0.58 | similarity-score 169.39, sequence-similarity 0.73; block RMSD 1.23 | 4.8 |
  | fatcat-flexible | 0.87 | 1.12 | 66 | 0.58 | same as rigid (one block, no twist) | 4.7 |
  | ce | 0.87 | 1.12 | 66 | 0.58 | similarity-score 139.88, sequence-similarity 0.73 | 2.5 |

  Response fields: `info{uuid,status}`, `meta{alignment_mode,alignment_method}`, `results[0].structures[]`, `results[0].structure_alignment[]` (per block: `regions[]` per structure with `asym_id, beg_seq_id, beg_index, length`; `transformations[]`, one 16-number column-major 4x4 per structure (identity for the first; the second for tm-align: rotation rows -0.63 -0.73 -0.27 / 0.60 -0.24 -0.77 / 0.49 -0.64 0.59, translation 42.3 83.9 80.4); `summary{scores[], n_aln_residue_pairs, ...}`), `results[0].sequence_alignment[]` (aligned sequences with `regions` and `gaps`), `results[0].summary` (`n_modeled_residues` [69, 66], `seq_aln_len`, `aln_coverage` [96, 100]). The summary's TM-score and RMSD are the same in all four methods (0.87, 1.12; the reason is not documented), while the alignments differ in index offsets. Not run: `ce-cp`, `smith-waterman-3d` (the six-request cap on the submit endpoint was reached).

## 4. US-align installed locally

Pin (`LIB/tools/native_setup.py`, `PINS['US-align']`): version `20261019`, commit `23f14ffcf8647f2dc1c0e01043db3a7f3a661c28`, URL `https://codeload.github.com/pylelab/USalign/tar.gz/<commit>`, archive sha256 `2d485ac1e10ce04ce78372d4c7ea9b59567cffe3fa0463882b17bd71e9f79765`; compile `g++ -O3 -o USalign USalign.cpp` in the unpacked source (the installer has no `-static -ffast-math`; that figure of the inventory is not in this file). The installer imports `jobs/local_execution/.../local_jobs` (old runner), so it was not run; its three steps were done by hand: download (285,771 B; sha256 equals the pin), extract, compile.

- Install: `resources/software/usalign-20261019/{src,bin/USalign,build.log}`; archive `resources/software/usalign-20261019-23f14ff.tar.gz`; records `resources/software/usalign.json` and `usalign-20261019-acquisition.json`. `git check-ignore resources/software` prints `resources/software` (ignored; nothing committed).
- Binary `bin/USalign` sha256 `39f586662ab97939365c8be4bdd56a28be3f9b692388def36d9c9b4b7d5345d6`, 1,143,680 B; build 20.7 s; source `USalign.cpp` sha256 `93f0847fca104a1925757a7c13236900e2a9ebaaccf6a79e5ffd2b024908be11`; `USalign -v` prints "US-align (Version 20261019)".
- Licence (`src/LICENSE`, sha256 `5bb88694...bcdca`): "Permission to use, copy, modify, and distribute this program for any purpose, with or without fee, is hereby granted, provided that the notices on the head, the reference information, and this copyright notice appear in all copies or substantial portions of the Software." (cite Nat Protoc 21:517-541, Nat Methods 19:1109-1115, iScience 25:105218). `USalign.cpp` is also under the Boost licence for part of its code.
- The same page at `zhanggroup.org/US-align/bin/module/USalign.cpp` serves a different single-file build, Version 20260527 (sha256 `5e05ddcd...13f5`, 729,547 B), not used; `zhanggroup.org/US-align/readme.txt` is 404.

Run (`runs/a102_dali_probe/usalign/`; `1MJC.pdb` from `https://files.rcsb.org/download/1MJC.pdb`, 69,093 B, one chain A of 69 residues):

```
USalign runs/a102_service_probe/afdb/cspa_model.pdb runs/a102_dali_probe/usalign/1MJC.pdb -m matrix.txt      # out_default.txt, matrix.txt
USalign runs/a102_service_probe/afdb/cspa_model.pdb runs/a102_dali_probe/usalign/1MJC.pdb -outfmt 2        # out_fmt2.txt
```

Output (wall time 0.017 s, "Total CPU time is 0.01 seconds"; `-outfmt 2` 0.007 s):

```
Length of Structure_1: 70 residues      Length of Structure_2: 69 residues
Aligned length= 69, RMSD=   0.82, Seq_ID=n_identical/n_aligned= 1.000
TM-score= 0.92809 (normalized by length of Structure_1: L=70, d0=2.92)
TM-score= 0.94064 (normalized by length of Structure_2: L=69, d0=2.89)
MSGKMTGIVKWFNADKGFGFITPDDGSKDVFVHFSAIQNDGYKSLDEGQKVSFTIESGAKGPAAGNVTSL
 :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
-SGKMTGIVKWFNADKGFGFITPDDGSKDVFVHFSAIQNDGYKSLDEGQKVSFTIESGAKGPAAGNVTSL
```

Matrix (`-m`; Structure_1 onto Structure_2): t = 27.7071705983, 22.4143127267, 28.1436242335; u rows (-0.1203943060 -0.2425573408 -0.9626375993), (0.8665659818 0.4474065232 -0.2211126458), (0.4843228368 -0.8608096999 0.1563267423); applied as `X = t[0] + u[0][0]*x + u[0][1]*y + u[0][2]*z`, etc.

`-outfmt 2` (tab separated): `#PDBchain1 PDBchain2 TM1 TM2 RMSD ID1 ID2 IDali L1 L2 Lali` then `cspa_model.pdb:A  1MJC.pdb:A  0.9281  0.9406  0.82  0.986  1.000  1.000  70  69  69`.

**Comparison for this pair**:

| Figure | US-align (local) | Foldseek server hit `1mjc-assembly1.cif.gz_A` (`foldseek/result2_tmalign_0.json`) | A102 sheet (`a102_pdb100_check/out_cspa_pdb100.json`, rank 1) | DALI server (hit 1mjcA, rank 1) | RCSB TM-align (1MJC vs 1C9O, a different pair) |
| --- | --- | --- | --- | --- | --- |
| TM-score normalised by the target (1MJC, L=69) | 0.94064 | `score` 92 / 100 = 0.92 | not given | Z 15.4 | not applicable |
| TM-score normalised by the query (70) | 0.92809 | not given | not given | | |
| RMSD | 0.82 | not given (has `alnLength` 69, `seqId` 100, `prob` 0.997, `eval` 0.9344) | 0.8223 (least squares, 69 pairs) | 0.8 | |
| Aligned length | 69 | 69 | 69 (`usable_pairs` 69, `target_coverage` 0.9857) | 69 | |

The Foldseek `score` 92 (0.92) is close to, but not equal to, either US-align normalisation (0.928 by query, 0.941 by target); a score field of 92 is an integer, so the difference may be rounding down of 0.928, but this was not verified. RMSD and aligned length agree with the sheet (0.8223 vs 0.82; 69 vs 69).

US-align's own text on RNA and on multi-chain alignment: `USalign -h`: "-mol ... prot: only align proteins in a structure. RNA: only align RNA and DNA in a structure."; "-atom ... Default is ' C3'' for RNA/DNA and ' CA ' for proteins". Home page `zhanggroup.org/US-align/` (saved `usalign/dl/home.html`): "Alignment of a pair of monomer (default of the US-align program). Only the first chain of each structure is considered." and "Alignment of a pair of oligomers ("-mm 1" option of the US-align program)"; `-h`: "-mm 1: alignment of two multi-chain oligomeric structures ... To use -mm 1 or -mm 2, '-ter' option must be 0 or 1." Example from `-h`: `USalign 1qf6.cif 5yyn.pdb.gz -mol RNA    # pairwise monomeric RNA alignment`; the server limit "currently only aligns up to 10 structures".
