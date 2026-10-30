# Bounded primary evidence for the VDB field contract

These are source/specification observations, not newly executed VDB searches
or metadata acquisitions. Hashes, URLs and acquisition results are in
`sources/MANIFEST.json`. Pinned C++ files use NCBI commit
`d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05`, the same commit retained by workload
306. The VDB utility digest exactly matches the source cited in workload 302.
The commit is not asserted identical to installed BLAST+ 2.17.0.

| Source inspected | Exact relevant fact | Contract consequence |
|---|---|---|
| [NCBI VDB utility](https://raw.githubusercontent.com/ncbi/ncbi-cxx-toolkit-public/d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05/src/algo/blast/vdb/vdb2blast_util.cpp), local GetVDBSeqIdFromOID at line 403 | Recognized cSRA reference accessions can replace the run-qualified raw name. | Accession equality cannot recover a lost run origin. Catalogue membership and report origin are separate. |
| Same file, CreateBioseqFromVDBSeqId at 459 and CreateBioseqFromOid at 529 | Explicit ID extraction reads 4na; ordinal enumeration uses 2na. | Do not presume both paths preserve ambiguity identically for full-sequence identity. |
| Same file, GetVDBStats at 667/682 and its constructor | Statistics construction fixes filtered-read inclusion false. | A reported total does not automatically match an include-filtered search population. |
| [NCBI blast_vdb_cmd](https://raw.githubusercontent.com/ncbi/ncbi-cxx-toolkit-public/d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05/src/app/blastvdb/blast_vdb_cmd.cpp), complete relevant Write and x_ProcessSearchRequest paths, x_PrintBlastDatabaseInformation at 531 | Explicit output supports ID, accession spelling, length, sequence; information output separately displays sequence/base counts. | A bounded supplied-output parser is implementable, with exact format/context and absent metadata limits. |
| [NCBI GBSeq schema](https://raw.githubusercontent.com/ncbi/ncbi-cxx-toolkit-public/d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05/src/objects/gbseq/gbseq.asn), complete schema | Sequence is optional; features retain location, intervals, qualifiers and partial flags. | Preserve no-sequence and complex-location states rather than manufacture full-sequence hashes/codon maps. |
| [INSDC feature definition](https://www.insdc.org/submitting-standards/feature-table/), version 11.4, sections 3.4 and codon_start/CDS qualifier definitions | Native locations are one-based inclusive, with explicit partial/remote forms; coding start offsets and coding-table qualifiers have declared meaning. | Exact interval conversion and source-qualified coding fields; unsupported exceptions remain overlap-only. |
| [NCBI SRA download documentation](https://www.ncbi.nlm.nih.gov/sra/docs/sradownload/) | Run metadata is obtained separately; RunInfo CSV differs from Run Selector tabular metadata. | Do not infer sample metadata from SRA file possession or confuse the two table formats. |
| [NCBI Entrez Direct Examples](https://www.ncbi.nlm.nih.gov/books/NBK565821/pdf/Bookshelf_NBK565821.pdf), pages 22–23 in the official web tool representation | RunInfo example includes Run, Sample, BioSample, TaxID, spots and bases as separate columns/values. | Literal same-row run/sample mapping is implementable; spots are retained separately from reads, and sample taxon is contextual. |

The direct HTML and PDF fetches of Entrez Direct Examples returned a browser
challenge, not the requested documentation. Those bytes are retained and marked
rejected in the manifest; they are not evidence for RunInfo fields. The official
web tool exposed the PDF text, including the exact separate fields. No challenge
bypass or biological API call was performed.

Local source study included the complete collector, program-context resolver,
303 sequence adapter and its frozen contract/addenda; the complete reusable
alignment geometry and column-correspondence functions; existing source
metadata functions; 302 sections 1–4 and 8–11 and complete shared port; and
305/306 contracts/addenda for profile/master versus biological sequence meaning.
No existing file outside this verification directory was changed. Source
inspection does not establish parsing tests, native-result fixtures, deployment
or episode-return integration.
