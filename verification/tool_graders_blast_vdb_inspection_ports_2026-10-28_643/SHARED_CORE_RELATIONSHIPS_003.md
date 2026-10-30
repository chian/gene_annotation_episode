# Explicit VDB sample and dependency relationships

This supplies two missing relationship inputs identified during implementation
of 002. It changes no goal, numerical policy, episode or prompt. Keep 001/002 as
the original implementation records; these additions are not silently folded
into them.

## Provenance validation boundary

The pure core validates provenance shape, JSON-pointer syntax and the explicit
relationships actually present in its inputs. It cannot authenticate a Store
source record or the contents of a captured document. Do not invent a known
source set from occurrence IDs: occurrence IDs and source references have
different meanings. The original captured-context worker must authenticate
every provenance reference against the actual selected input/request and its
captured content before constructing a result. That is an explicit integration
dependency. Core tests do not establish that authentication.

## Sample links

Add this required array to `blast_vdb_utility_context_v1`; empty means no
supplied sample relationship:

    sample_links: [{
        dataset_key: nonblank string,
        link: {
            sample_key: nonblank string,
            sample_identifier: identity,
            biosample_identifier: identity | null,
            source: provenance
        }
    }]

`identity` and `provenance` are exactly the existing VDB metadata meanings.
The nested `link` has the existing `blast_vdb_inputs._sample_link` shape, without
its search-related dataset wrapper. Dataset keys must belong to declared
source_inputs. A member's non-null sample_key requires a uniquely established
matching dataset_key/sample_key link; conflicting identity links do not justify
selecting one. Keep raw conflicting supplied links, while the member sample_key
remains null. Exact repeated links do not imply separate samples. The worker
must verify the supplied link's content; the core must not infer a sample from
a run label or grant access because a source_ref string exists.

## Path dependencies

Add these required arrays to the same context; either may be empty:

    dependency_database_bindings: list[existing DatabaseBinding]
    declared_dependencies: list[existing DATABASE_DEPENDENCY_SCHEMA]

Reuse `blast_preparation_contracts.DATABASE_DEPENDENCY_SCHEMA` exactly. Its
current fields are role=database, ordinal, database_key, native_path_index,
native_reference, source, list_occurrence_id and list_entry_ordinal. The earlier
643 tuple predates native_path_index; do not create a competing truncated tuple.

Combine the primary result DatabaseBinding with the explicit dependency
bindings by database_key. Duplicate/conflicting keys are invalid. Each declared
dependency has its own unique nonnegative ordinal, refers to an existing
binding and a valid native_path_index, and retains its original reference and
list source. List occurrence/entry references use the existing meanings and
refer only to declared captured inputs. No new file or dataset is discovered.

Each path record's matched_dependency_ordinals must refer to supplied
declared_dependencies. A match requires literal equality of the reported
native_path with that dependency's native_reference or its explicitly bound
native path. No basename guessing, normalization-based equivalence or alias
edge inference. Unmatched native path rows remain usable reported rows with an
empty match list. Saved-only validation therefore has the original dependency
facts rather than an unchecked integer or a hidden external lookup.

The core verifies supplied shapes and relationships. The native/context worker
remains responsible for proving these bindings came from the actual original
selection and captured manifest/list documents. A path report itself cannot
authorize additional capture or fill these arrays by discovery.

## Schema object compatibility

The public ArtifactOccurrence schema may remain one detached extended
properties object for current consumers that require that shape. Preserve all
old nested version-schema objects exactly; no in-place enum mutation. Use the
same component definitions, not a second extraction calculation.
