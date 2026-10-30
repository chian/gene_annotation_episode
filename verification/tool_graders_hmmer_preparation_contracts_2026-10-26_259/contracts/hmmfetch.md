# hmmfetch — proposed exact contract

Modes `single_key`, `key_file`, `index`. Invocations:
`hmmfetch [-o output|-O] models key`, `hmmfetch [-o output] -f models keyfile`,
`hmmfetch --index models`. Input roles: models (native supported HMMER format),
optional explicitly associated SSI index for retrieval, keyfile text for -f or
retained request occurrence for positional key. Indexing cannot read stdin;
retrieval permits models OR keyfile stdin, not both. Stage indexing into a private
working copy so `<models>.ssi` never mutates the caller's original location.
-O writes a filename equal to key, so its key/output-path relationship requires
safe exact confinement, not arbitrary unvalidated path traversal.

Retrieval output is HMMER3/f ASCII, even from older/binary input; retain complete
model bytes and stdout/stderr. Index output is SSI binary plus summary with model,
primary-name and secondary-accession counts. SSI/model source association must be
explicit; automatic ambient sibling-index discovery is not a trustworthy binding.
Models use NAME as primary key and ACC as alias; no alias inferred from taxon or
other annotations. Existing index makes order and multiplicity differ:
with SSI, output follows keyfile order, onefetch per key; without SSI, models are
scanned in source order and emitted once when name OR accession matches.

Sheet keeps every key occurrence/line, first token (native ignores later tokens,
# starts comments), input model occurrence and native name/accession, requested
lookup mode and index occurrence, output model occurrence, and exact many-to-many
requested-key -> source-model -> output-model joins. Duplicate identical key tokens
are native errors; distinct alias/name keys may refer to one model. Duplicate
model NAME/ACC ambiguity must remain explicit. Unindexed single key returns the
first matching model; this is native behavior, not a scientifically unique match.

Functions: `parse_hmmfetch_index_summary(text, *, occurrence, operation)`;
`extract_hmmfetch_keys(content, *, occurrence)`;
`populate_hmmfetch_sheet(*, operation, inputs, outputs, models)`;
`validate_hmmfetch_sheet(sheet, *, parameters={source_index_bindings,
probability_tolerance})`. Recalculable counts: requested key occurrences, distinct
keys, resolved keys, missing keys, source-model occurrences selected, output-model
occurrences and duplicate representations; full decoded lengths/headers/body
comparisons for each proven association. SSI has byte count/signature/association
checks until a full SSI reader is provided; do not claim decoded index contents
from file size. Native counts and independently extracted counts remain separate.

Critical missing-key distinction: unindexed -f silently omits unmatched keys and
can return exit0; indexed -f fails when onefetch cannot resolve a key and preserves
earlier output. 'Native successful' is separate from 'all requested keys resolved'.
Checks cover missing/duplicate keys, wrong/stale index, truncated model, unsupported
format, source/output mismatch, duplicate aliases, existing-index refusal and
partial prefixes after failure. COMMON.md defines typed partial/failure envelopes
and handoff to a proposed preparation-results collector, with no observation or
confidence score. Selected fetched models/indexes may feed later explicit jobs.

Native evidence: `native/hmmfetch_single` key TINY001 ->1 model LENG12 NSEQ3,
6670bytes. `native/hmmfetch_index` ->1 model,1 name,1 accession; SSI165bytes.
`*_unindexed_alias` keys tiny_protein,TINY001 ->1 model; `*_indexed_alias` ->2
identical models/13340bytes. `*_unindexed_missing` keys tiny_protein,MISSING
exits0 with1 model; `*_indexed_missing` exits1 with1 valid model prefix.
`*_duplicate` identical key repeated exits1 after the first indexed fetch.
All complete files and receipts are retained. Full hmmfetch.c was inspected.
No production parsing/calculation or episode integration is claimed.
