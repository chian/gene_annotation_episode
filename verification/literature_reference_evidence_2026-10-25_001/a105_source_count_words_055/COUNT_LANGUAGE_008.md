# 055 finite count language and selected-source boundary

This records the implemented first-stage contract. It does not claim general
English interpretation, model-backed extraction or scientific independence.
The selecting model/episode remains responsible for identifying which source
statement describes the requested count and its experimental meaning.

The argument is the existing exact source witness plus a selected numeral span.
The complete source quote is authenticated as UTF8 bytes; the inner span uses
Unicode character positions. The parser examines actual adjacent source text
within the existing HTML/JATS field boundary, including outside a narrowed
witness and across inline markup. Original bytes and raw selected words are
retained. The parser does not supply or rewrite a source number.

## Exact numeral grammar

Decimal digits retain their existing scalar numerical-range/custody guards.
Only an unqualified positive digit count populates the exact canonical count.
A full selected zero or negative integer is retained as not_positive; clipping
the sign remains a caller error. Decimal fractions or exponent expressions are
unsupported count notation, not silently rounded positive integers.

English cardinal words use case-insensitive recognition and whitespace
normalization only for lexical reading. Atomic words are zero–nineteen and the
tens twenty–ninety. Tens may have a1–9 unit after whitespace or one hyphen.
Hundreds use a1–9 unit followed by hundred, optionally followed by a1–99
remainder with an optional single and. Million and thousand groups occur once
each in descending order, with each multiplier group1–999. A final remainder
below100 may have a preceding and after a scale group. The grammar recognizes
0–999999999. This is a declared reader-language limit; larger scientific counts
are not capped or converted to the limit.

The parser does not infer counts from a/single/once/duplicate/triplicate/dozen,
ordinals, Roman numerals, fractions, an arbitrary phrase or another language.
The complete selected text is retained as unsupported with exact count null.

## Qualification grammar outside the selected numeral

Recognized prefix relations are <, <=, ≤, >, >=, ≥ and the existing finite
spellings less/greater than (including or equal to), below/above, at least/most,
more than and no more/less than. Recognized approximation prefixes include
~,≈,≃,≅,∼ and approximately/roughly/around/about/circa/approx. Prefix qualifiers
may occur in either order. They populate finite relation/approximation meanings,
but an exact canonical repetition count stays null.

Recognized suffix lower-count bounds are or more/greater/above and and above.
Recognized suffix upper-count bounds are or less/fewer/below and and below.
Recognized suffix approximations are approximately/roughly/around/about/circa/
approx. These supply a reported numeral with its relation or approximation,
never an exact n. For example, at least three returns reported numeral3, ge,
qualified, and exact count null.

Residual no/not/never, including significantly/substantially/clearly, make a
negated or unsupported qualifier unresolved. Additional unresolved qualifier
cues include fewer/less/more than, up to, at minimum/maximum, under/over and
nearly/almost. Unrecognized comparative suffix combinations beginning or/and
with no, greater/less/fewer/more/above/below or at least/most also stay unresolved.
Conflicting/composite relations stay unresolved. For example, no greater than
three retains reported numeral3 with unresolved relation; it does not assert
the misleading positive greater-than bound. A missing supported grammar never
authorizes a model-independent claim that all possible source semantics were
understood. Arbitrary uncaptured language remains a source-reading limitation.

Recognized range/alternative contexts include between ... and ..., from/range/
interval/CI markers, adjacent to/or, and complete dash-separated count ranges.
They retain raw selected wording with no chosen endpoint or mean. A clipped
dash-separated endpoint remains an actionable selection error; nominate the
complete range expression to obtain its useful unavailable count reading.
Distinct prose such as three independent experiments with four technical
measurements each does not multiply counts or become a range.

## Caller failures and unresolved scientific input

False quotations, source authorization failures, invalid byte/character spans,
clipped words/digits/signs, partial cardinal compounds and physical quantity/
percentage/spread/arithmetic roles remain caller failures. Narrow selections
cannot lose minus/negative/plus/positive prefixes, word decimal point
continuations or fractional continuations such as and a half. A complete
unsupported expression can be retained without losing the valid parameter
measurements; a clipped token requests meaningful repair.

Count None means not_selected, not source-unreported. A selected reading has
one status: exact, qualified, range_or_alternatives, unsupported or not_positive.
Only exact supplies the canonical positive integer. Qualified input can retain
its reported numeral for a corresponding requested raw-parameter return, with
its actual finite relation/approximation separately declared. Unrequested count
numbers remain null in derived-only or opposite-operand rows.

Source wording and custody do not prove biological attribution. Count3 with
repetition basis unspecified remains unspecified. A separately witnessed
technical/biological interpretation is preserved but does not create a
preparation identity, independence, covariance or statistical model.045 scientific
calculations and observation/credit accounting remain unchanged.

## Verified stage and outstanding consumer

The six-module test generation006 passed405 checks with all18 captured code/test
dependencies stable. After qualifier corrections, the focused generation007
count/input tests passed202 checks; its outer receipt harness separately found
052's concurrent shared renderer change, so007 is not a coherent whole-shared-
generation integration claim. These milestones overlap and are not additive.

The saved typed metadata carries count status/relation now. The held052-owned
renderer does not yet display those fields. A direct synthetic mechanical probe
confirmed it displays reported numeral3 while omitting qualified/ge meanings.
HELD_RENDERER_GAP_007.json records this genuine unfinished consumer. Full native
presentation/admission/reconstruction verification awaits explicit renderer
ownership transfer and a stable final connected test generation.
