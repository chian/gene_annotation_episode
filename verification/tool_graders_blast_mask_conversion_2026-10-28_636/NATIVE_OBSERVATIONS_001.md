# convert2blastmask native format observations — 636/001

This is native characterization evidence for the existing R7 conversion boundary,
not a replacement goal, production parser, new scoring implementation, or whole-tool
completion claim. The current implementation proposal is 620/001 section 4.5.
The original user attachment was read in full; its objective and entire operating
principles were reread during the work. GOAL.md was not read.

One bounded attempt executed the nine explicitly selected commands once each.
The capture test passed: **1 passed in 0.60 seconds**. Eight native commands
returned zero; malformed input returned one as selected. No search, database
preparation, data download, remote service, or help/version rerun occurred.

## Original artifacts and verification

The original artifact directory is:

`verification/tool_graders_hmmer_map_verification_2026-10-28_529/check097_blast_mask_conversion_formats/temporary/convert2blastmask_formats_636/`

It retains all six original FASTA files under `inputs/`, every selected argv and
exact native environment in `<case>/SELECTED_COMMAND_001.json`, native output
bytes in `<case>/native_output.<format>`, full `stdout.bin` and `stderr.bin`, and
each outcome in `<case>/OUTCOME_001.json`. Empty streams remain retained files.
No original artifact was moved, replaced, or regenerated.

`CAPTURE_001.json` in this packet is an exact text copy of the original capture
receipt. It also retains complete text outputs, the full binary output as hex,
original input contents, original paths, sizes and SHA-256 identities. The native
XML element tree in that receipt is a bounded examination aid, not a production
association parser. `EVIDENCE_INDEX_001.json` identifies every original artifact,
copied runner receipt and original before/after closure manifest.

The original handle is `check097_blast_mask_conversion_formats/handle.json`, unit
`gene-local-job-322d5e0fbe2545a7a8467b17d31ea50d.service`, under the existing 529
runner. The collected receipt is terminal and quiescent, return code zero.
Enforced limits were 21,474,836,480 bytes RAM, 4,294,967,296 bytes scratch, zero
swap, and no wall limit. Observed scratch was 624,910,336 bytes. Source,
dependency, standard-library, interpreter and native-library pins were unchanged;
the execution audit reports no outside modules or unbound mappings.

The selected invocation is recorded in `runner_evidence/selected_request.json`.
It used `run_checks.py launch check097_blast_mask_conversion_formats`, dependency
closure `check005/dependencies`, only
`test_native_convert2blastmask_formats_636.py`, and only the selected
`resources/software/ncbi-blast-2.17.0+/bin/convert2blastmask` executable. Three
explicit support files supplied the retained source, help and version identities.
The original handle was collected without resubmission.

| Identity | SHA-256 | Bytes |
| --- | --- | ---: |
| Native executable | `4a386044ba1cad366be0b7452cdbcca81bf33869d48345e7ac5f9117c0537833` | 23,440,776 |
| Frozen capture test | `3c27dd24596e3702d02ba1c02736ee7adfb06cb739e51869a5592534fba2f0a8` | 9,070 |
| Retained official `convert2blastmask.cpp` | `8a8596deb5a78c7b16674cee3a3c0ffefa02559c99f0e3d4a24d545fcbd09742` | 9,451 |
| Complete capture receipt | `3486c2d364c111da02d8baf7ddd65fa665a4b0dfe72cf9279708a85b7524f217` | See index |

The official source is retained evidence, not a proven build-source identity for
this executable. The exact source and prior CLI artifacts were frozen in this
attempt's source snapshot. Their original packet is
`verification/tool_graders_blast_utility_boundaries_2026-10-28_620/`.

## Selected commands and observed native results

Every command used explicit `-in`, `-out`, `-outfmt`, `-masking_algorithm` and
`-masking_options`; all except `nucleotide_xml_unparsed` used `-parse_seqids`.
The option string was exactly
`supplied lowercase; no detector run; fixture 636`. Algorithms are declared
upstream provenance, not evidence that DUST, SEG or another detector ran.

The native environment was explicitly constructed with `BLAST_USAGE_REPORT=false`,
`NCBI_DONT_USE_NCBIRC=1`, `LANG=C`, `LC_ALL=C`, `PATH=/usr/bin:/bin`, and per-case
project-scratch `TMPDIR`, `TMP`, `TEMP`, `XDG_CACHE_HOME`. Each native command had
its own explicit project-scratch cwd. No native child inherited PYTHONHOME or an
unrestricted host environment. No molecule option exists in the retained CLI;
molecule was supplied as test input metadata.

| Case | Format | Algorithm declaration | Return code | Native output bytes |
| --- | --- | --- | ---: | ---: |
| nucleotide_xml_parsed | maskinfo_xml | dust | 0 | 5,214 |
| nucleotide_text_parsed | maskinfo_asn1_text | dust | 0 | 1,123 |
| nucleotide_binary_parsed | maskinfo_asn1_bin | dust | 0 | 479 |
| nucleotide_xml_unparsed | maskinfo_xml | dust | 0 | 4,563 |
| duplicate_headers_xml | maskinfo_xml | other | 0 | 2,387 |
| protein_xml | maskinfo_xml | seg | 0 | 2,328 |
| single_interval | interval | other | 0 | 12 |
| uppercase_only_xml | maskinfo_xml | other | 0 | 669 |
| malformed_xml | maskinfo_xml | other | 1 | 669 |

The first three commands use identical supplied nucleotide input bytes. Parsed
XML and text retain these native intervals and identifiers:

| Original occurrence | Original header token | Supplied sequence | Native inclusive intervals | Half-open representation |
| ---: | --- | --- | --- | --- |
| 0 | lcl\|mask_a | AAaaNNttRRYy | [2,3], [6,7], [11,11] | [2,4), [6,8), [11,12) |
| 1 | lcl\|upper_a | ACGTNNRY | No emitted record | Requires successful complete-input context for known zero |
| 2 | ref\|NM_999999999.7\| | nnACgtNN | [0,1], [4,5] | [0,2), [4,6) |
| 3 | gnl\|fixture636\|mask_general | ACgtNNrY | [2,3], [6,6] | [2,4), [6,7) |

These are synthetic identifiers; no accession was queried. The native endpoint
extents are 5 positions in the first 12-position sequence, 4 in the third
8-position sequence, and 3 in the fourth 8-position sequence. These are direct
hand checks of the observed intervals, not output of a new or existing scoring
calculator. Lowercase ambiguous `n`, `r`, `y` positions are retained as masks;
uppercase ambiguous symbols are not masked in these supplied examples.

The protein input `MKWVtfISLLflFSSaysR` has length 19. Native XML emits inclusive
`[4,5]`, `[10,11]`, `[15,17]`, corresponding to seven lowercase positions and
half-open `[4,6)`, `[10,12)`, `[15,18)`. Its native program declaration is SEG;
the executable performed mask conversion, not SEG detection.

## Exact grammar and identity distinctions

Each observed XML file has one XML declaration, a `Blast-db-mask-info` DOCTYPE
reference, one root and one mask-list object. No external DTD was fetched.
Root paths are:

```text
Blast-db-mask-info
  Blast-db-mask-info_algo-id                         0
  Blast-db-mask-info_algo-program
    Blast-filter-program                            value="dust", text 10
  Blast-db-mask-info_algo-options                    exact supplied text
  Blast-db-mask-info_masks
    Blast-mask-list
      Blast-mask-list_masks
        Seq-loc                                     repeated masked occurrence
      Blast-mask-list_more                           value="false"
```

Other observed algorithm labels/codes are `seg`/20 and `other`/100. All observed
root algorithm IDs are zero. The label/code, options, root grouping, native
ordering and boolean attributes must remain native facts. These fields do not
prove upstream detector execution or establish a database-assigned mask ID.

A **single** mask interval uses `Seq-loc/Seq-loc_int/Seq-interval`; multiple
intervals use `Seq-loc/Seq-loc_packed-int/Packed-seqint/Seq-interval`. A reader
that only accepts packed intervals loses valid native output. Each interval has
`Seq-interval_from`, `Seq-interval_to`, and `Seq-interval_id/Seq-id`. Observed
identifier alternatives are:

| Native XML alternative | Retained information | Observation |
| --- | --- | --- |
| Seq-id_local / Object-id / Object-id_str | Exact string | mask_a, duplicate, protein_a |
| Seq-id_local / Object-id / Object-id_id | Integer identity, distinct from a string | 1, 3, 4 without parse_seqids |
| Seq-id_other / Textseq-id | Accession and version separately | NM_999999999 and 7 |
| Seq-id_general / Dbtag | db and typed tag | fixture636 plus Object-id_str mask_general |

The parsed ASN.1 text begins `Blast-db-mask-info ::= {`, retains `algo-id 0`,
`algo-program dust`, the quoted options, nested `masks { masks { ... }, more
FALSE }`, and three `packed-int` groups. Its interval identity expressions are
`id local str "mask_a"`, `id other { accession "NM_999999999", version 7 }`,
and `id general { db "fixture636", tag str "mask_general" }`.
Single-interval ASN.1 text syntax was not independently observed in this run.

The native binary file is retained byte-for-byte and starts with hex `30 80`.
Its SHA-256 is `43116d1573486794eea859d4c26804a2e9a58c6550d6aa53df0d817beb7bac3d`.
No binary schema decoder or XML/text/binary semantic equality check was executed.
Binary production alone does not establish a working binary parser.

## Association, omission and failure contract consequences

With parsed IDs, the four-record input emits three Seq-loc groups in masked
input order, for original occurrences 0, 2 and 3. There is no placeholder for
uppercase occurrence 1. Native group number is therefore not the input ordinal.
The artifact carries neither molecule identity nor original sequence lengths;
both require the original supplied sequence occurrence and its provenance.

Without `-parse_seqids`, the same three groups carry integer local IDs 1, 3 and
4. The original headers are absent. This run shows an ordinal relationship with
a gap for the omitted occurrence; it does not authorize a general silent mapping
rule. Preserve these integer IDs and require an explicitly verified original
occurrence binding before projecting per-sequence quantities.

The duplicate input is exactly:

```text
>duplicate
AAaaGG
>duplicate
ttCCaa
```

It succeeds with no stderr. Native group 0 is a single `Seq-loc_int` [2,3];
group 1 is packed [0,1], [4,5]. Both identify `local str "duplicate"`.
The native ID alone does not identify the original occurrence. Keep both groups
and both input occurrences; do not merge by header or resolve them by first
match. An exact occurrence association remains a separate validation problem.

The one-record interval input `AAaaNNtt` produces exactly these 12 bytes:

```text
2 - 3
6 - 7
```

There is no header, sequence ID, grouping field, algorithm metadata or length.
Use this format only with an explicitly bound single original input record;
multi-record ordinal association is not established by this evidence.

Uppercase-only input succeeds and emits a complete XML document with empty
`Blast-mask-list_masks` and `more=false`. The malformed input
`not a FASTA header\nAAaa\n` returns one with a 410-byte stderr exception,
`CObjReaderParseException::eNoDefline`, around input line 1. It emits **identical
669-byte XML**, SHA-256
`92ab1567f9c98a24d2698c03845ece48e927fd8c5a7dd626eafc4cdd64cefd02`.
Thus neither a well-formed empty document nor `more=false` establishes successful
processing, completeness, or known zero. Original native outcome, complete
supplied inputs and authenticated association remain necessary. Keep failed
empty conversion distinct from successfully observed no-mask input.

Every observed `more` flag is false. Concatenated roots, more=true, multiple
mask-list chunks, post-prefix failure, header-plus-interval input, additional
Seq-id alternatives and remote execution were not exercised. The retained
source describes header-plus-interval input using dummy internal symbols; this
task did not execute or bind that mode and does not claim those symbols provide
a valid sequence denominator.

## Handoff and remaining work

This packet supplies authentic artifacts for the existing `SequenceMaskingSheet`
and `calculate_sequence_masking_components` conversion extension. Those shared
components were not invoked or edited here. A future parser must retain both
single and packed interval forms, complete native identities and metadata,
separate native parsing from original-occurrence association, and qualify
known-zero omissions with the original successful outcome and complete inputs.

Completed here: bounded native capture, input/command/environment/output custody,
observed grammar, empty/failure distinction, source/binary pins and exact receipts.
Unfinished: production parsing, explicit association policy, shared-sheet
population/recalculation, published/requested typed returns, episode integration
and any remote-resource verification. No inventory completion row was changed.
