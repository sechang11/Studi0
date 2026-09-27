# The attic

Files moved out of the repository root and `studio/` on 2026-09-27 because they were in the way
of a reader, not because they were wrong. Nothing here is imported by anything.

- `route_ltx25.py` - the one-shot patch (2026-08-16) that made LTX-2.5 a selectable engine and
  wrote its measurement into the chooser; it ran once. The measurement lives in the playbook.
- `bambu_result.json` - a Bambu Studio slicer error from the 3D-printing work (`craft/PRINTING.md`).
- `*.log`, `check_fix.png` - July 2026 render logs from the first kit (`docs/STATE.md` section 2).
- `*.bak-*` - August 2026 hand backups of `serve.py`, `film.py` and `film_editor.html` made
  before camera-rig patches; git history holds every version, so these stay untracked.

The film spec builders that were loose in `studio/` (`specs_*.py`) went to `films/specs/`, beside
the other film builders.
