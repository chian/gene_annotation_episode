#078 truthful absent local arms

## Truthful absent local arm/source-kind semantics

LocalReading007 now permits source_kind=null with this REQUIRED equivalence:

```
arm=null  <=> source_kind=null
arm=null   => measurement_method=not_selected
```

A null arm represents a genuinely absent/unselected ORIGINAL primary arm. It is
not a selected source reading whose number could not be obtained. Every selected
primary or companion with missing/unreadable/unavailable measurement retains its
actual NONNULL Arm, original nonnull source_kind, actual science and native status;
method=not_selected is allowed with that nonnull Arm if its measurement nomination
was null. Source absence never acquires a fabricated primary/retained/synthetic
source kind or measurement origin. A companion's original source-v3 Arm nomination
is nonnull; a local null arm with nonnull companion reading_key is invalid.

The fixed primary registry retains ALL four original primary selectors, including
absent ones, followed by every selected companion in original order. If an absent
raw role is requested, it has an explicit saved raw roster key and unavailable
CELL_FIELDS, not a disappearing key:

* key=raw:<role>:primary, reading={role,reading_key:null};
* value/lower/upper=null, relation=none, approximate=false, unit=null,
  status=unavailable, origin=null, unavailable_reason=[missing_arm],
  formula_code=source_response, conditional_on=[], bound_kind=none,
  bound_state={lower:unknown,upper:unknown}.

LocalCell007 origin now permits null specifically to express absence of any source
measurement. This does not change the original owner006/076 Cell schema/outputs.
An available raw value must retain its actual source origin; null cannot erase a
reported/graph/synthetic origin. For a wholly absent raw role, its canonical
uncertainty record is unknown with null magnitude/interval/confidence/count and
unknown repetition/estimate basis; do not invent 'unreported' from no source.
Native raw native_reading=null, source-kind/origin lists empty, actual scientific
statuses unknown. Its explicit unavailable key can be requested/admitted exactly
like another actual saved key; no number or scientific contribution is invented.

A pair selector referencing a registered absent primary is meaningful and returns
an explicit unavailable difference with missing_arm. Its variance/SE cannot gain
a known owner/binding from the absent arm. Other present raw/local pairs survive.
A selector whose key is NOT in the parsed readings roster is a contract error
(local_reading_selector_unresolved), NOT an implicit absent arm; duplicate selectors
are invalid too. Binding a known covariance owner to a null arm is invalid. Full
original supplied C still validates before any marginal, even for unavailable pairs.

For SELECTED but numerically missing nonnull arms, preserve actual source meanings,
kind/unit/status. Difference remains unavailable when it needs that missing numeric
operand. Variance availability is evaluated from its OWN actual source-means science,
owner/index/unit/C-scope dependencies; a missing difference alone is not a synthetic
variance-zero or automatic independent model. A source-grounded variance can survive
missing point magnitude only when those dependencies are independently established;
absence/unknown owner does not establish them. No dummy number or whole-sheet
stand-in is introduced.
