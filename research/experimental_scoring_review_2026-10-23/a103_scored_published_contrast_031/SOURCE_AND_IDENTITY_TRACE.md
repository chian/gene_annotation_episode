# Source, field and identity trace

## Published BioY case: inspected scope and denominator diagnosis

[Hebbeln et al., 2007](https://pmc.ncbi.nlm.nih.gov/articles/PMC1815280/), DOI [10.1073/pnas.0609905104](https://www.pnas.org/doi/10.1073/pnas.0609905104): comparative Results paragraphs 1–5, Fig. 1 caption, Discussion, and Methods “Bioinformatic Techniques”; the organism/construct distinction is in “Bacterial Strains” and “Heterologous Expression.” The study surveys 150 retained BioY orthologs in 127 genomes and describes both linked and separately located BioMN genes. Its approximate one-third summary therefore does not unambiguously specify the current sheet's spatial predicate without the per-locus supplement. The SB1003 genes were expressed in recombinant *E. coli*; those assay constructs are distinct from today's reference loci. The present native observation evaluates neighborhood association only. It neither reproduces a historical experiment nor establishes identity of the assayed construct.

The inspected historical packet was `../a103_numerical_sheet_011/paper_01_bioy.md`, read completely. Newly browsed primary text independently confirmed the context and method statements above. Main-text Results and Discussion were available; this worker did not inspect the supplementary spreadsheet or figures themselves. The remaining biochemical Methods were not fully read and are not numerical inputs here. No fresh RibK paper or RibK-specific retained packet was opened.

Supplement access was bounded: the publisher's linked [09905table1.xls](https://www.pnas.org/doi/suppl/10.1073/pnas.0609905104/suppl_file/09905table1.xls) redirected to a cookie page. Europe PMC's supplementary endpoint returned an explicit not-open-access error, and its full-text XML endpoint returned HTTP 500. The NCBI OA URL attempted returned HTTP 404. Complete responses and statuses are retained in `bioy_retrieval_attempts.json` and the three `.response` files. The linked publisher correction returned HTTP 403 and was not inspected; its contents are unknown. None of these failures is converted to biological absence.

## Query to reference-identity chain

| Stage | Exact returned information | What is established / what remains unknown |
| --- | --- | --- |
| Named organism | Primary paper names *R. capsulatus* SB1003. [NCBI BioProject PRJNA55](https://www.ncbi.nlm.nih.gov/bioproject/55), Organism, identifies SB1003 as taxon **272942**, with RCAP locus prefix | Organism/strain link to the selected taxon; no construct-sequence identity claim |
| STRING name mapping | `get_string_ids` queried `bioY`, `bioN`, `bioM`, species `272942`; **three records returned**, all retained in `string_bioy_mapping_001.json` | All returned mappings are preserved; this endpoint returns best matches, not an exhaustive biological ambiguity search |
| BioY mapping | Query index 0: `bioY` → `272942.RCAP_rcc03249`, preferredName `bioY` | Exact API mapping |
| BioN mapping | Query index 1: `bioN` → `272942.RCAP_rcc03250`, preferredName `cbiQ3` | Display-name difference is explicit |
| Additional returned mapping, not scored | Query index 2: `bioM` → `272942.RCAP_rcc03251`, preferredName `cbiO3` | Retained for completeness, not a second question or contribution |
| UniProt cross-check | Exact-locus search within taxon 272942 returned **two records**: [D5ARG8 / BIOY_RHOCB](https://www.uniprot.org/uniprotkb/D5ARG8/entry), `bioY`, locus `RCAP_rcc03249`; [D5ARG9 / BION_RHOCB](https://www.uniprot.org/uniprotkb/D5ARG9/entry), `bioN`, synonyms `cbiQ3`, `ecfT`, locus `RCAP_rcc03250` | Both identify strain SB1003 and explicitly cross-reference the corresponding STRING IDs; all returned records retained in `uniprot_locus_aliases_001.json` |
| Scope of identity | One BioY and one BioN reference-locus record in that restricted search; no additional candidate returned | Not proof that an unspecified sample has no paralogs, that historical constructs match exactly, or that a supplied sequence maps uniquely |

The initial STRING name mapping alone was insufficient for a construct-identity claim. The exact-locus UniProt cross-links resolve the `cbiQ3`/`bioN` alias for this reference pair. The historical assayed construct's exact sequence, tags/start-codon differences and identity to the current reference proteins remain unverified. This limitation does not change which pair received the native score.

## Native measurement custody and documentation

All API calls used the installed STRING or UniProt skill's `scripts/rest_request.py`. `request_manifest.json` retains full request operands, requested endpoints, successful status outputs, returned-row counts and file-write UTC timestamps. The skill retains the complete parsed JSON response, serialized to disk; it does not claim to preserve original HTTP byte formatting or response headers.

The first STRING network request used the two IDs separated by a newline, `limit=10`, `required_score=0`, `add_nodes=0`, `network_type=functional`. It unexpectedly returned 44 rows, retained in full, while its console preview showed 10. Its exact pair occurs at zero-based row 34. No unseen preview item was treated as absent. A second request used the documented `%0d` separator and omitted the network-irrelevant `limit` parameter. It returned **one complete row**, the exact BioY/BioN pair, with the same values. The cause of the first expansion was not isolated; changing two request operands does not identify which caused it.

The preferred measurement file is `string_bioy_bion_network_002.json`, row 0. It contains `nscore=.844` and `score=.999`. The separate `version` endpoint returned **12.5** and `https://version-12-5.string-db.org`. The recorded calls used the current `string-db.org` endpoint; version 12.5 was observed in the same retrieval session, rather than enforced atomically by the network URL.

[STRING API documentation](https://string-db.org/help/api/#retrieving-interaction-network), network output fields, distinguishes `nscore` (gene neighborhood) from `score` (combined), `pscore` (phyletic profile) and other channels. The [STRING FAQ](https://string-db.org/help/faq/), score-column definitions, associates neighborhood with inter-gene nucleotide distance. Its integer-times-1000 rule concerns downloadable link files; the retrieved API value is already a decimal score. It is preserved as `.844`, not divided again by 1000. The API's functional network is an association network; it is not restricted to experimentally demonstrated physical binding. Direct/transferred contributions were not decomposed by this response.

## Component trace

| Component path | Populated value or state | Input/source locator | Calculation / scope |
| --- | --- | --- | --- |
| `native.pair_ids`, `taxon_ref` | Exact BioY/BioN pair; 272942 | STRING row 0; UniProt genes/organism/STRING cross-references; NCBI Organism | Reference identity, not assay construct identity |
| `native.channel`, `field_name`, `raw_scale` | neighborhood; nscore; unit_interval | STRING API output-field definition and actual decimal response | Only this channel contributes |
| `native.raw_value`, `native.score` | .844 | Preferred native response, row 0, `nscore` | Recorded native score |
| `native.direction`, `direction_evidence_ref` | supports_context_predicate | Named BioY/BioN association question; primary biological case | Logical compatibility +1, not a numerical confidence judgment |
| `C`, `E`, count-route fields | not_applicable in the native example | Existing A103 native-route contract | No invented foreground/background table |
| `t`, `S`, `O`, `c` | .844, .844, 0, .844 | Recorded .844, fixed w=1; existing sheet equations | Proposed arithmetic conversion |
| Sampling/calibration uncertainty | null/unreported | Not supplied in native row | No manufactured interval or certainty multiplier |
| Historical BioY count route | unknown/bounded | Primary context; unrecovered supplement | Distinct from the new native example |
| RibK comparator | .956, combined .959 | Parent-validated values and `../a103_complete_deliverable_023/EXAMPLES.md` | Inherited comparator, not a freshly reviewed paper or query |
| Descriptive differences | .112 neighborhood; .040 combined | Those four exact recorded values | Arithmetic only; no common probability calibration claimed |

No paper count, alias count, annotation text, assay activity or STRING combined score enters the new A103 coordinate. The native row and its repeated retrieval are one measurement representation for scoring purposes.
