# Aurora storage and charging

The user's current requirements are exact:

- All workflow software, environments, databases, caches, inputs, temporary
  files, logs and run directories belong under
  `/lus/flare/projects/BioReason-Aurora-Test`.
- New Aurora PBS jobs charge `EpiCalib` through `-A EpiCalib`. Storage and
  charging are independent; charging EpiCalib does not move this work there.
- The only workflow file allowed in Aurora home is the small directory index
  `/home/chian/WORKSPACE_DIRECTORY.md`. No run folders, environments, output,
  caches, temporary files or backup work in home.

The caller's explicit PBS configuration must carry the required account and a
workspace within that project. Do not repair conflicting configuration by
silently changing the account, job, allocation or storage. Return the specific
conflict for repair by its owner. Set working, output, temporary and cache
locations in project storage. If loading a module changes cache/user-base
variables, restore their explicit project locations before an operation writes.

The inventory identifies reusable preparations and their observed provenance.
Its content hash detects changed catalog bytes; matching hashes do not prove
the listed files still exist, are usable or match the assigned software/data.
Current quota, filesystem load and queue state are separate observations with
timestamps. They do not change the original preparation record or historical
job account. Allocation balances and expiry dates in old records need a current
observation when relevant to a decision.

The 2026-10-22 manual test used storage under this project and charged
`BioReason-Aurora-Test` before the later charging instruction. Keep that original
receipt true. New instructions do not relabel that historical allocation.
Source table rows A3–A4 identify the current direction and original records.
