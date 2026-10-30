# Preserve existing descriptions as well as validation semantics in072

072 correctly found that the bare native partner schema already contains
inherited REF descriptions, although its103 witness objects/15 number selectors/
6 definition objects lack their own operand instructions. The root release's
shorthand about removing descriptions means stripping them on BOTH schemas.
Do not delete or overwrite existing descriptions to make a mistaken assertion
pass. Preserve the failed first assertion and correction additively.

Require both: recursive description-stripped equality, AND a recursive exact
additive-key comparison proving every preexisting key/value remains identical
and the only added keys are descriptions. The existing native rate information
must remain exact. No new default, validation field, reader acceptance/error,
numeric result or science interpretation is authorized by this clarification.
