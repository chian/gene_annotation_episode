# Empty selected population correction

The610/006 contract explicitly defines records={mode:selected,entries:[]} as
requesting no sequence quantities. A nonempty quantities name list with that
empty population therefore has no Sheet/Components input requirement. It can
fulfill its empty selected numerical request while the separately recorded native
state remains unknown/failed/incomplete. This differs from records={mode:all}
with requested quantities and no parsed input population, which remains unavailable.

The pure projector now applies that exact distinction before declaring a missing
sheet. This changes no public shape, calculation, native state or artifact grant.
