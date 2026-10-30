# Additive original HTML selector correction

Parent inspected original PMC HTML selectors before integration. The measured
BtsT Km paragraph has no p id. It lies in section sec2-4 and is its second direct
scientific paragraph (zero-based index1); intervening Figure4 is not a paragraph
operand and its caption must not supply uncertainty.

The finite HTML reader therefore also accepts paragraph_id=`direct_paragraph:N`
where N is canonical nonnegative decimal, selecting the Nth direct p child of
the explicitly selected section. This selector is retained unchanged in
source.paragraph_id and paragraph text/expression offsets stay original-text
coordinates. No synthetic ID is inserted, source bytes rewritten, full-article
convenience scan used or paragraph projected into purported original JATS.
Ordinary ID selectors still require globally unique original IDs and scoped
direct prose. Test ambiguous reserved selectors and out-of-range indices.

Repository dispatch uses source_kind=primary_html for original HTML. Existing
primary_jats and synthetic_fixture JATS paths remain as before. Synthetic HTML
is exercised directly at the reader boundary, while selected original HTML uses
actual immutable original source artifacts and the existing quantity return.
