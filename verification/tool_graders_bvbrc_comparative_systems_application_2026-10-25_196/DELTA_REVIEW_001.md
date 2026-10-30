# ComparativeSystems delta review

The exact byte-level delta is DELTA_MANIFEST_001.json and DELTA_001.patch.
It is derived from all 935 original paths, the exact 25-file proteome182
composition, and all 1,045 candidate186 paths. Expected production after182
contains 952 paths. The ComparativeSystems delta has 99 paths: 93 additions,
6 changes and no deletions.

| Category | Files |
| --- | ---: |
| Runtime modules | 22 |
| Packaged schema | 1 |
| Package configuration | 1 |
| Test modules | 11 |
| Fixtures | 64 |

| Existing file | Added lines | Removed lines |
| --- | ---: | ---: |
| gene_annotation_episode/api_service_execution.py | 10 | 0 |
| gene_annotation_episode/bvbrc_appservice_adapters.py | 2 | 1 |
| gene_annotation_episode/bvbrc_appservice_host.py | 2 | 1 |
| gene_annotation_episode/bvbrc_appservice_publication.py | 26 | 5 |
| gene_annotation_episode/execution_episodes.py | 29 | 1 |
| pyproject.toml | 1 | 1 |

The 22 runtime files consist of 17 new ComparativeSystems modules and the
five shared consumers above. The new data file is the unchanged reviewed
115-definition handoff schema. pyproject.toml adds that packaged JSON asset.
All individual paths, before/after hashes and byte counts are in the manifest.

Of the 25 files composed from proteome182, 21 remain byte-identical. The four
composed files with further ComparativeSystems edits are adapters, publication,
execution_episodes and pyproject.toml. The two other changed shared files are
api_service_execution and bvbrc_appservice_host, unchanged by the182 composition.
Every other expected post182 file remains byte-identical, including both
proteome implementations, schemas, tests and native request handling.

Shared diffs preserve the proteome adapter registrations, return resolvers,
publication status/completion handling and packaged v2 schema while adding the
ComparativeSystems equivalents. I's exact shared-delta audit and preservation
receipt are checked against the full maps. The post-copy probe separately
requires unchanged v1/v2 pins and package002-equivalent numerical results.
Root still owns independent semantic review and actual application; this
worker has not executed either application or a production facade probe.

No method_loop, controller, credit, W05, pending/custody policy, namespace
redefinition or runtime test gate is introduced by this application utility.
The candidate's existing protocol additions are copied exactly after review;
the utility does not rewrite candidate behavior or infer further changes.
