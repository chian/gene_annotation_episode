# Minhash / Similar Genome Finder Service

## Overview

When a researcher has a new genome sequence, one of the first things they want to identify is the closest relatives of their genome. BV-BRC provides a service that allows researchers to do this using Mash/MinHash[1]. Mash reduces large sequences and sequence-sets to small, representative sketches, from which global mutation distances can be rapidly estimated. The MinHash dimensionality-reduction technique to include a pairwise mutation distance and P value significance test, enabling the efficient clustering and search of massive sequence collections.

This module contains the service code that implements the BV-BRC Similar Genome Finder service.

It provides utilities for maintaining a minhash database of the collected BV-BRC genomes (both bacterial and viral) and a JSONRPC-based synchronous lookup service. The BV-BRC API uses this service to implement the [similar genome finder service](https://www.bv-brc.org/docs/quick_references/services/similar_genome_finder_service.html).

## About this module

This module is a component of the BV-BRC build system. It is designed to fit into the
`dev_container` infrastructure which manages development and production deployment of
the components of the BV-BRC. More documentation is available [here](https://github.com/BV-BRC/dev_container/tree/master/README.md).

This service is run as a sychronous service via the KBase JSONRPC service mechanism. As such, the API for the service is defined in the [Minhash.spec](Minhash.spec) file.

## See also

- [Similar Genome Finder Service](https://www.bv-brc.org/docs/tutorial/similar_genome_finder/similar_genome_finder.html)
- [Similar Genome Finder Quick Reference](https://www.bv-brc.org/docs/quick_references/services/similar_genome_finder_service.html)
- [Similar Genome Finder Tutorial](https://www.bv-brc.org/docs/tutorial/similar_genome_finder/similar_genome_finder.html)

## References

Ondov BD, Treangen TJ, Melsted P et al. Mash: fast genome and metagenome distance estimation using MinHash, Genome biology 2016;17:132.
