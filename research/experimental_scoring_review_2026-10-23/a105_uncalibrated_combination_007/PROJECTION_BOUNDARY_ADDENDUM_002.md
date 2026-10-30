# Missing-data projection boundary

2026-10-23. Additive clarification to the unchanged proposal and arithmetic
checker 001. This adds no alternative combination or new source information.

Unknown K need not make c unknown if every allowed K is nonpositive. The
defined projection `c=max(0,K)` then has the singleton image {0}. More generally,
fill the c point exactly when its allowed image is a singleton. Otherwise leave
it null and retain its bounds. The original checker 001 conservatively leaves
c null whenever K lacks a point, even if c bounds coincide; that output shortcut
does not change its correct bounds. The additional boundary check below makes
the intended sheet result explicit.

Synthetic example: one source has S=-4 and R=1, giving q=-2. A second source
has unknown source S but known R=.4; in a separate proposed accounting block,
its q lies between `-atanh(.4)` and `+atanh(.4)`. Therefore

```
K point = null
K bounds = [-.9844231523453708, -.9180301233918929]
c bounds = [0,0]
c point = 0
```

This zero is identified by the complete allowed-set calculation. It is not a
default assigned to a missing source, a detection claim, a discarded opposition
or a confidence statement. The unknown source S remains unknown. The main
all-unknown example still has K null with bounds [-1,1], and c null with bounds
[0,1].

`check_projection_boundary_002.py` passed 8 additional assertions covering this
case, a crossing-zero range, the all-unknown range and a fully known point.
Its output is `projection_boundary_002.json`. The 255 original assertions and
their artifact remain unchanged. These are source-free arithmetic checks only.
