# Film spec builders (LTX era, August 2026)

`specs_*.py` were loose in `studio/`; each writes one film's shot specs for the LTX-2.5 route and
imports nothing from the app. They are kept as the record of how those films were specified.

The current way to write a film as data is a shot script in `studio/shotscripts/` run by
`studio/_tools/fight.py` (or the `/shots` page), or the film editor at `/film`.
