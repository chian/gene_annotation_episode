import json, runpy, sys
from Bio.Restriction import Restriction as impl
counts = {"batch_search_calls": 0, "original_finditer_calls": 0}
batch, finditer = impl.RestrictionBatch.search, impl.FormattedSeq.finditer
def searched(self, dna, linear=True):
    counts["batch_search_calls"] += 1
    return batch(self, dna, linear=linear)
def found(self, pattern, size):
    counts["original_finditer_calls"] += 1
    return finditer(self, pattern, size)
impl.RestrictionBatch.search, impl.FormattedSeq.finditer = searched, found
request, output, counter = sys.argv[1:]
sys.argv = ["gene_annotation_episode.restriction_mapping_worker", request, output]
try:
    runpy.run_module("gene_annotation_episode.restriction_mapping_worker", run_name="__main__")
finally:
    with open(counter, "x") as stream:
        json.dump(counts, stream, sort_keys=True)
