# MSA source-byte implementation and saved validation

Root owns `bvbrc_msa_xmfa_inputs.py` and its test file within accepted workload C.
The frozen XMFA_PROVIDER_EXTENSION_001 signatures and records remain unchanged.
The file also exports two saved-record validators needed by the MSA sheet:

```python
validate_msa_xmfa_source_verification(value: dict, *, associations: dict | None = None) -> dict
validate_msa_xmfa_binding_record(value: dict, *, document: dict, associations: dict) -> dict
```

These validate closed saved records, exact supplied/effective input subsets,
source file states and original occurrence/length/transformation relationships.
The binding validator additionally checks its actual document and saved source
sequences/components through the existing document-aware source validator.
They do not parse bytes, reopen paths, execute calculators or authenticate
external custody. The existing host retains responsibility for the original
authenticated publication; structural validation is not a second byte receipt.

The byte verifier accepts a previously validated common AssociationSet from the
provider/adapter. It checks the exact original MemberKey, known original length,
and that the named transformation explicitly includes that original member.
Missing or contradictory maps remain in supplied_inputs with requirements and
are omitted from verified_inputs. An unknown map does not discard verified
source sequences or the native XMFA coordinates.

Unequal FASTA sequence lengths are valid for staged source records. The existing
alignment reader's unequal-length diagnostic is retained as a qualification in
this source-record interpretation; it is not used to claim a complete alignment.
Any other error in the selected native reader prevents source-file verification.
Raw DNA permits only ASCII DNA IUPAC and CRLF/LF endings. Its full-file location
uses byte interval [0, byte_count), with physical line numbers, including an
explicit empty record for actual empty raw bytes. No filename or header inference.

The source verifier is one part of the MSA provider. C's remaining sheet,
component dispatch and saved validators, then E/F/G integration, remain required.
