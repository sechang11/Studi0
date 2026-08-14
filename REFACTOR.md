> **Superseded.** This document is absorbed into [ARCHITECTURE.md](ARCHITECTURE.md),
> which carries the current consolidation plan. Kept because its incident list is
> the evidence behind that plan; do not extend it here.

# Refactor: what to reorganise before adding more

Written against the tree as it stands: 106 tools in one folder, 22 HTML pages, 21 sibling
card directories, 20 markdown files in the root, 44 workflows, 25 scripts.

Nothing here is style preference. Every item below is something that has **already caused a
real bug in this project**, with the incident named. The order is by how much damage the
problem has done, not by how satisfying it would be to fix.

---

## The one bug class that matters

Almost every failure this project has had is the same shape: **the work succeeded and the
reporting lied.** Not crashes - crashes are cheap, they point at themselves. The expensive
ones looked like success.

- the scoreboard counted 5 successes as failures, because it parsed the wrong line
- `/api/story` progress always answered "no such job", because a per-request
  `importlib.reload()` wiped the job table
- `lora_check` re-tiled the *previous* character's images, because `ensure_local` returns
  early when the destination exists - so a fixed `/tmp` name meant every recheck showed
  the first result
- `takegrid.sh` silently dropped 2 of 6 takes, because an `xstack` layout string only
  addressed 2x2
- `-v error` suppressed `silencedetect`, so every voice take reported "0 pauses" -
  including a control file with a deliberate 0.9s gap
- a character card written with tags as a **list** instead of a string crashed the reader,
  and the crash was reported as a MISSING verdict rather than an error

**So the organising principle of the refactor is: make it structurally hard for a component
to report success it did not have.** Every proposal below is judged against that.

---

## 1. `studio/_tools/` - 106 scripts, no contract  *(highest damage, fix first)*

The hazard is already written down in the project's own notes: **17-20 of these tools have
no argparse and run their entire job on ANY argument, including `--help`.** Several write
files at module import. That is why `/tools` had to be a hand-curated allowlist of 14
rather than a generic runner - the folder cannot be safely enumerated.

It is also where duplicates breed. In this session alone I started writing a second
printability checker before noticing `mesh_doctor.py` already did it properly, held to a
spec. There are also `terra_3d_source.py` + `_v2`, and `terra_mesh.py` + `_v2`, with no
statement of which one is current.

**Do:**

- **A CLI contract, enforced by a test.** Every tool: `argparse`, `--help` exits 0 without
  side effects, no work at import. A test that imports each module with a stubbed
  filesystem and fails on any write. This turns the allowlist from a safety measure into a
  convenience.
- **Group into packages** by what they act on, not by when they were written:
  `tools/cards/`, `tools/render/`, `tools/mesh/`, `tools/sound/`, `tools/story/`,
  `tools/check/`. A tool's folder should tell you what it can damage.
- **One job, one implementation.** Delete or clearly retire the `_v2` pairs. Where two
  tools measure the same property, one calls the other - two checkers that can disagree
  are worse than one checker that is wrong, because you cannot tell which to believe.
- **Separate the one-shot scripts from the library.** A lot of `make_*.py` files are
  records of a thing done once. They belong in `tools/oneshot/` with the date, not
  alongside tools meant to be re-run.

## 2. Card libraries - 21 sibling folders, no shared loader

`styles/ characters/ places/ motions/ loras/ voices/ models3d/ emotions/ looks/ lighting/
weather/ pacing/ shots/ transitions/ cues/ sfx/ soundscapes/ tags/ domains/ layers/
templates/` - all siblings of `_tools/` and `samples/`, all JSON cards, each read by
whatever code happens to want one.

This is what let a `wear_tags` **ladder of 5 damage rungs** get flattened into a tag string
across 9 cards - nothing knew what the field meant, so nothing objected. It was caught by
reading a diff, which is not a system.

**Do:**

- **`studio/cards/<type>/`**, so a card library is distinguishable from an output folder at
  a glance.
- **One loader, one schema per type.** Field types declared once: which are strings, which
  are ladders, which are inherited, which are hashed into an inputs hash. A loader that
  refuses a card of the wrong shape would have blocked both the `wear_tags` flattening and
  the tags-as-list crash.
- **Provenance is a required field, not a convention.** The 3D model library already does
  this - every card carries its licence, source URL and whether attribution is required.
  Characters carry `provenance: invented`. Make it schema-required everywhere, because the
  field that matters most is the one nobody remembers to write.
- **Keep the four blocked voice packs blocked in the schema, not in each picker.** They are
  clones of real people, marked `status: blocked`, and right now every consumer has to
  remember to filter them. One loader-level rule is one place to get it right.

## 3. Engine routing is the project's real invariant - give it a home

The hardest-won facts here are all about **which model can be asked what**:

- the engine is a **property of the style**, resolved by `compose.resolve()`, never a free
  choice
- a character LoRA is a delta on **specific weights** - animagine LoRAs attach to nothing
  on Qwen and are passed through, quietly never read
- Qwen cannot be prompted off photography at any cfg
- the model renders **nouns, not adjectives**

These are enforced in scattered places, and FLUX.2 is installed, works, and **no style card
routes to it** - so it is unreachable. That is the invariant failing quietly in the other
direction: a capability that exists and cannot be used.

**Do:** one `engine/` module owning routing, LoRA-to-base-model compatibility, and the
negative-prompt discipline. A check that every installed engine has at least one reachable
style card, and that every LoRA names its base model and is refused against another.

## 4. Rules should all work the way `VIDEO_RULES.md` works

`craft/VIDEO_RULES.md` is the best thing in this codebase: human-readable rules with
machine-readable blocks, parsed by `filmrules.py`, enforced by name, exit 1 on error. It
came from a real bug - SFX at full level under narration - and it now prevents that bug.

Everything else is enforced by scattered `if` statements or by nothing.

**Do:** extend the pattern. `PRINTING.md` already exists as a spec that `mesh_doctor`
is held to - make it a machine-read ruleset too. Same for card schemas and engine routing.
One rule format, one runner, one exit code.

## 5. 22 HTML pages, each with its own copy of the stylesheet

Every page re-declares the same `:root{--bg:#0f1115;...}` block and its own header markup.
A theme change is a 22-file edit, which means it will be a 19-file edit and three pages
will silently drift.

**Do:** one `shell.html` + one `studio.css` + one nav built from a route table. Pages
become content. Low risk, entirely mechanical, and it makes the next page cheap - which
matters because more pages are coming.

## 6. 20 markdown files in the root, several overlapping

`FILMCRAFT.md` / `FILMMAKING.md` / `FILM-CRAFT-AUDIT.md`. `CAPABILITIES.md` /
`NEW-CAPABILITIES.md`. `GENERATED.md` / `GENERATING.md`. When two documents describe the
same thing, the reader cannot tell which is current, so both rot.

**Do:** `craft/` for rules that are enforced by code (the VIDEO_RULES pattern), `docs/` for
everything explanatory, one `README.md` at the root as the map. Merge the overlapping
pairs; where a file is a historical record, say so in its first line and stop editing it.

---

## Order of work

1. **CLI contract + the import-time-side-effect test.** Highest damage, and it makes every
   later step safe to automate.
2. **Card schema + one loader.** Second highest, and it is the precondition for the app
   growing new card types without growing new bug classes.
3. **Engine module** - including making FLUX.2 reachable, which is a capability sitting
   unused right now.
4. **Page shell.** Mechanical, low risk.
5. **Docs consolidation.** Do it last; it is the easiest to get wrong while things move.

## What NOT to do

- **Do not move the sample tree.** `studio/samples/` is ~4 GB of rendered evidence and
  several tools discover work by path convention (`<slug>_3d/`, `mesh/REPORT.json`).
  Moving it breaks discovery silently, which is exactly the bug class we are trying to
  eliminate.
- **Do not rename card ids.** LoRA cards resolve through `studio/loras/<id>.json`, story
  files reference cards by id, and an inputs hash is computed over card fields. A rename
  invalidates saved work.
- **Do not refactor and change behaviour in the same commit.** Every incident in the list
  at the top was found by comparing an output to what it should have been. Keep the
  outputs comparable.
