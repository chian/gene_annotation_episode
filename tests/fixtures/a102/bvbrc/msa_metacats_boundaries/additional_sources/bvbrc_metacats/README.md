# Metadata-driven Comparative Analysis Tool (Meta-CATS)

## Overview

The meta-CATS metadata genome comparison tool takes sequence data and determines the aligned positions that significantly differ between two (or more) user-specified groups. Once an analysis is started, a multiple sequence alignment is performed if the input was unaligned (such as from a database query). A chi-square test of independence is then performed on each non-conserved column of the alignment, to identify those that have a non-random distribution of bases. A quantitative statistical value of variation is computed for all positions. Columns that are perfectly conserved will not be identified as statistically significant. All other non-conserved columns will be evaluated to determine whether the p-value is lower than the specified threshold value. Terminal gaps flanking the aligned sequences will not be taken into account for the analysis.

## About this module

This module is a component of the BV-BRC build system. It is designed to fit into the
`dev_container` infrastructure which manages development and production deployment of
the components of the BV-BRC. More documentation is available [here](https://github.com/BV-BRC/dev_container/tree/master/README.md).

There is one application service specifications defined here:

1. [Meta_CATS](app_specs/MetaCATS.md): The Meta-CATS tool looks for positions that significantly differ between user-defined groups of sequences.

The code in this module provides the BV-BRC application service wrapper scripts for the Meta-CATS service as well
as some backend utilities:

| Script name | Purpose |
| ----------- | ------- |
| [App-MetaCATS.pl](service-scripts/App-MetaCATS.pl) | App script for the [Meta-CATS service](https://www.bv-brc.org/docs/quick_references/services/metacats.html) |

## See also

* [Meta-CATS Service](https://www.bv-brc.org/app/MetaCATS)
* [Quick Reference](https://www.bv-brc.org/docs/quick_references/services/metacats.html)
* [Meta-CATS Service Tutorial](https://www.bv-brc.org/docs/tutorial/metacats/metacats.html)


## References

Pickett, B. E., et al. "Metadata-driven comparative analysis tool for sequences (meta-CATS): an automated process for identifying significant sequence variations that correlate with virus attributes." Virology 447.1-2 (2013): 45-51.



