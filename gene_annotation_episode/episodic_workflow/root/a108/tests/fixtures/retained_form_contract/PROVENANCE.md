These original test sources are retained exactly from commit
fb1e4d9bac279edcae98e8f2b3324b73c1679e51.

* original_uniprot_compact_selection.py.txt: tests/test_uniprot_compact_selection.py,
  SHA256 bc6be3e110fa9fd084dd9fe9480be09102c17e47e11ee677df052c99b8086041.
* original_restriction_declarations.py.txt: tests/test_restriction_mapping_declarations_733.py,
  SHA256 68de782ba789dcbab7e695fdc2164e64d32964e29e57880c384242f9643a6705.

Owned test_retained_uniprot_form_contract.py preserves all original pure helper
and test bodies. test_retained_restriction_form_contract.py selects only the
first four pure schema test functions and their three pure fixture helpers.
Their original assertions and decorators remain exact. The later native/Store
workflow cases and their environment opt-in are not copied into this pure scope.
Both files bind to each actual private axis helper via an autouse fixture.
They are post-install controls: an absent helper is an error, not substituted by
a test implementation. Final owner routing must agree with the audited installed
form-contract imports before these tests are run or credited.
