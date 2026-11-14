# A110 saved-carrier probe

The local `private_saved_carriers.py` entrypoint selects A110 explicitly. Shared
test mechanics, controlled ports and exact evidence limits are documented in
`../../a107/tests/PRIVATE_SAVED_CARRIERS.md`. A110 constructs its actual 27-binding
registry and eight distinct Launch/Results owners; it has no API execution owner
and no A107 masking helper. All application imports and method_loop identities
resolve to A110. No saved descriptor supplies an import target.
