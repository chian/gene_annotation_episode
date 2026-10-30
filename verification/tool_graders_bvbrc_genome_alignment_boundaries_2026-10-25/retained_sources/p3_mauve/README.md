# Genome Alignment (Mauve)

## Overview
The bacterial Genome Alignment Service uses progressiveMauve to produce a whole genome alignment of two or more genomes. The resulting alignment can be visualized within the BV-BRC website, providing insight into homologous regions and changes due to DNA recombination. It should be noted that this service is currently released as beta. As always, we appreciate your feedback.

## About this module

This module is a component of the BV-BRC build system. It is designed to fit into the
`dev_container` infrastructure which manages development and production deployment of
the components of the BV-BRC. More documentation is available [here](https://github.com/BV-BRC/dev_container/tree/master/README.md).

There is one application service specification defined here:

1.  [GenomeAlignment](app_specs/GenomeAlignment.md): Service that that provides the backend for the BV-BRC web inerface; it takes genomes as input.

The code in this module provides the BV-BRC application service wrapper scripts for the genome annotation service as well
as some backend utilities:


| Script name | Purpose |
| ----------- | ------- |
| [App-GenomeAlignment.pl](service-scripts/App-GenomeAlignment.pl) | App script for the [Genome Alignment Service](https://www.bv-brc.org/docs/tutorial/genome_alignment/genome_alignment.html) |


## See also

* [Genome Alignment (Mauve) Service](https://www.bv-brc.org/app/GenomeAlignment)
* [Quick Reference](https://www.bv-brc.org/docs/quick_references/services/genome_alignment_service.html)
* [Genome Annotation Service Tutorial](https://www.bv-brc.org/docs/tutorial/genome_alignment/genome_alignment.html)

## References
Darling, A.E., B. Mau, and N.T. Perna, progressiveMauve: multiple genome alignment with gene gain, loss and rearrangement. PloS one, 2010. 5(6): p. e11147.
