# Retained UniProtKB native example

`P0AAW1.json` is an exact 8,650-byte copy of the historical 2026-10-23 HTTP
entity retained at
`verification/api_service_expansion_2026-10-23_001/live_public_002/uniprot/state/artifacts/dc/dc1e11907d2d7a9ea423dd90e9f6bea7393cdf21669d139b1b04e1a8647d0e3e`.
SHA-256: `dc1e11907d2d7a9ea423dd90e9f6bea7393cdf21669d139b1b04e1a8647d0e3e`.

`P0AAW1.transport.json` is the exact retained request/transport metadata artifact
with SHA-256 `c2c89095b2d4c9662cf65535768b4720a8dc094ffa3426bb54e4d933ada1c952`.
The historical request was accession P0AAW1. Retained release is 2026_03 and
release date is 02-September-2026. No new request was made for these fixtures.

Native expected values: primary P0AAW1, secondary P75772, taxon 83333, full
sequence length 253 aa, Chain feature 1..253 inclusive (derived [0,253)), three
citation records, and 42 cross references. Cross-reference ordinal 31 is
GO:0005886; its evidence is ECO:0007005 / PubMed / 32127419 owned by
`/uniProtKBCrossReferences/31`. Legacy name is Uncharacterized protein YbhP;
the legacy EC list is empty. Retrieval is not scientific confidence.

Other native bodies are explicitly controlled fixtures constructed in
`test_uniprot_native.py`. They test malformed/partial states and page behavior;
they do not establish an authentic search-page response or new live operation.
