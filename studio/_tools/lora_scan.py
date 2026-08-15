#!/usr/bin/env python3
"""Every LoRA on disk has a card, and every card points at a file that is really there.

    python3 studio/_tools/lora_scan.py            # the report
    python3 studio/_tools/lora_scan.py --json     # the same facts, machine readable
    python3 studio/_tools/lora_scan.py --loras /elsewhere/models/loras

WHY THIS EXISTS

The styles library shipped 46 of 64 cards marked `ready` having never been rendered, and
27 of 64 routed to the wrong engine. Both failures were invisible for weeks because
nothing ever compared the library against reality. A LoRA library can go wrong the same
way and three more, all of them quiet:

  A FILE WITH NO CARD       someone drops a .safetensors into models/loras and the
                            resolver cannot see it. Installed and unreachable.
  A CARD WITH NO FILE       the card offers a choice that fails at render time, deep
                            inside ComfyUI, as a stack trace rather than a message.
  A CARD ON THE WRONG BASE  the expensive one. A LoRA is a delta on specific weights.
                            An animagine-trained LoRA loaded onto Qwen does not raise:
                            ComfyUI logs `lora key not loaded` once per key - 68,628 of
                            those lines are sitting in ~/ComfyUI/user/comfyui_8188.log
                            right now - and then renders exactly as if no LoRA were
                            present. A mis-filed base_model buys you a silent no-op or
                            mush, never an exception.
  A CARD THAT CLAIMS READY  `status: ready` with an empty `verdict` is the styles-library
  WITHOUT A VERDICT         mistake in one line. If nobody looked, nobody may claim.

So this walks models/loras/, parses each safetensors header directly (the 8-byte
little-endian length prefix and the JSON that follows), and checks the library against
what the bytes actually say.

WHAT THE HEADER CAN AND CANNOT SETTLE - read this before trusting a WARN

  CAN   architecture family, from tensor key geometry. SDXL carries input_blocks /
        output_blocks / middle_block and, decisively, `label_emb` (the pooled
        size-conditioning embedder that SD1.5 does not have). Qwen-Image is 60
        transformer_blocks. LTX-2.3 is 48 transformer_blocks plus audio-attention
        families. Wan-14B is 40 `blocks` at width 5120. FLUX.1 is 19 double + 38 single
        at width 3072; FLUX.2 is 8 double + 48 single at width 6144. A text-encoder LoRA
        is all `text_encoders.*`. These are structural and cannot be faked by a rename.

  CANNOT  the base REVISION. Qwen-Image, Qwen-Image-2512, Qwen-Image-Edit-2509 and
        Qwen-Image-Edit-2511 all present as 60 blocks at width 3072. The two
        Qwen-Image-Edit Lightning files on this box have architecturally IDENTICAL
        headers - 2160 tensors, 720 modules, rank 64, alpha 8 - and differ only in
        sha256 and filename. If those two filenames were ever swapped, nothing in this
        tool could tell. Revision is the failure mode that already bit this project once:
        qwen_image_modern_anime_lora is a delta against ORIGINAL Qwen-Image while the box
        runs 2512, which loads silently, cleanly, and does nothing.

  So the base check below is a FAMILY check. It catches "animagine LoRA filed as qwen".
  It cannot catch "2509 LoRA filed as 2511". Only a render catches that.

METADATA IS MOSTLY ABSENT AND THAT IS NORMAL. Nine of the twenty files here have no
__metadata__ key at all (ComfyUI's own SaveLoRA writes none), and two more have a present
but empty dict. There is no sidecar convention on this box either - no .json, no
.civitai.info, no preview .png anywhere under models/. The cards ARE the sidecar layer,
which is exactly why nothing may be assumed into them silently.

Python 3 standard library only, on purpose: this has to run on the box with no venv.
"""
import argparse
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)

DEFAULT_CARDS = os.path.join(STUDIO, "loras")
# A LoRA file has TWO possible owners and this scanner only ever knew about one.
# studio/loras/*.json is the pickable library. studio/characters/*.json ALSO names a file,
# in its `lora` key, and compose.py resolves it there - a trained character LoRA is
# deliberately not in the pickable library, because a character is chosen by casting her,
# not by ticking a LoRA. Scanning only the library therefore reports every trained
# character as "installed and unreachable by the resolver", which is the exact opposite of
# true, and the report has said PROBLEMS FOUND on that basis since the first character was
# trained. Worse, it is a boy-who-cried-wolf failure: a REAL orphan now arrives in a list
# that is already known to be wrong and gets skipped.
DEFAULT_CHARS = os.path.join(STUDIO, "characters")
DEFAULT_LORAS = os.environ.get(
    "COMFY_LORAS", os.path.expanduser("~/ComfyUI/models/loras"))

# --- the card schema, kept here so the scanner and the library cannot drift apart ------
REQUIRED = ("id", "name", "file", "base_model", "engine", "kind", "strength",
            "strength_range", "trigger", "means", "status", "verdict", "note")
BASE_MODELS = ("animagine", "illustrious", "sdxl", "qwen", "qwen_edit",
               "ltx", "wan", "flux", "other")
ENGINES = ("anime", "qwen", "video", None)
KINDS = ("character", "style", "speedup", "edit", "utility",
         # experiment: an arm of a measured experiment (photo-count, rank sweeps)
         # - kept re-runnable, carries its verdict, never pickable as a style
         # (compose.LORA_STYLE_KINDS is {"style"} only).
         "experiment")
STATUSES = ("ready", "weak", "untested", "unavailable")

# base_model -> engine. `engine` is DERIVED, never independently authored, so that a
# resolver filtering by engine and a resolver filtering by base_model can never disagree.
# flux is null because no film engine reaches it: workflows 26 and 29 exist but short.py
# renders only anime and qwen. `other` is null because a text-encoder LoRA does not go in
# a MODEL slot at all.
ENGINE_FOR = {
    "animagine": "anime", "illustrious": "anime", "sdxl": "anime",
    "qwen": "qwen", "qwen_edit": "qwen",
    "ltx": "video", "wan": "video",
    "flux": None, "other": None,
}

# geometry family -> the base_model values that geometry permits. Deliberately loose:
# this is a family check, not a revision check. See the docstring.
ALLOWED_BASE = {
    "sdxl": {"animagine", "illustrious", "sdxl"},
    "sd-unet": {"sdxl", "other"},
    "qwen-family": {"qwen", "qwen_edit"},
    "ltx": {"ltx"},
    "wan": {"wan"},
    "flux1": {"flux"},
    "flux2": {"flux"},
    "text-encoder": {"other"},
    "unknown": set(BASE_MODELS),
}


# ---------------------------------------------------------------------------
# safetensors header
# ---------------------------------------------------------------------------

def read_header(path):
    """The JSON header of a safetensors file, plus the byte offset its data starts at.

    Format is fixed and trivial: 8 bytes little-endian uint64 giving the header length,
    then that many bytes of UTF-8 JSON mapping tensor name -> {dtype, shape,
    data_offsets}, plus an optional `__metadata__` string dict. Everything after is raw
    tensor data. No dependency needed, which is the point - this must run with nothing
    installed.
    """
    with open(path, "rb") as fh:
        raw = fh.read(8)
        if len(raw) < 8:
            raise ValueError("file is shorter than the 8-byte header prefix")
        n = struct.unpack("<Q", raw)[0]
        if n <= 0 or n > 200_000_000:
            raise ValueError("implausible header length %d - not a safetensors file" % n)
        blob = fh.read(n)
        if len(blob) < n:
            raise ValueError("truncated header")
        return json.loads(blob.decode("utf-8")), 8 + n


_STRUCT = {"F64": ("<d", 8), "F32": ("<f", 4), "F16": ("<e", 2),
           "I64": ("<q", 8), "I32": ("<i", 4), "I16": ("<h", 2), "I8": ("<b", 1)}


def read_scalar(fh, entry, data_start):
    """One numeric value out of the tensor data. Used only for `.alpha` tensors.

    Alpha does NOT live in the metadata - it is a real tensor, so the only way to learn a
    LoRA's effective scale is to seek into the data and decode it. Worth the trouble: the
    alpha/rank factor varies 32x across the files on this box (0.03125 to 1.0) and is
    invisible in every UI, so "strength 1.0" means materially different things per file.

    BF16 is decoded by hand because struct has no format for it - a bfloat16 is the top
    16 bits of a float32, so padding two zero bytes below it and reading as float32 is
    exact.
    """
    dt = entry.get("dtype")
    off = entry.get("data_offsets") or [0, 0]
    fh.seek(data_start + off[0])
    if dt == "BF16":
        b = fh.read(2)
        return struct.unpack("<f", b"\x00\x00" + b)[0] if len(b) == 2 else None
    spec = _STRUCT.get(dt)
    if not spec:
        return None
    b = fh.read(spec[1])
    return struct.unpack(spec[0], b)[0] if len(b) == spec[1] else None


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------

# The separator before a block family is `.` in most files and `_` in sd-scripts output,
# which flattens the whole key: `lora_unet_transformer_blocks_0_attn_to_q.lora_down.weight`.
# qwen_image_modern_anime_lora is the one file here in that dialect, and a dot-only regex
# silently classified it as `unknown` - i.e. the scanner would have waved through any
# base_model at all on the one file whose base revision is already known to be wrong.
_DOUBLE = re.compile(r"(?:^|[._])transformer_blocks[._](\d+)[._]")
_SINGLE = re.compile(r"(?:^|[._])single_(?:transformer_)?blocks[._](\d+)[._]")
_PLAIN = re.compile(r"(?:^|[._])blocks[._](\d+)[._]")
_RANKISH = re.compile(r"(lora_down|lora_A|lora\.down)")


def _indices(rx, names, exclude=None):
    out = set()
    for n in names:
        if exclude and exclude in n:
            continue
        m = rx.search(n)
        if m:
            out.add(int(m.group(1)))
    return out


def infer_family(names, widest):
    """Architecture family from key geometry alone. Never a revision - see the docstring.

    Order matters. SDXL is checked before the block-index families because
    `input_blocks.0.0` would otherwise match the bare `blocks.N` pattern that Wan uses,
    and the diffusers spelling is checked before them too - see the comment below.
    """
    if any(n.startswith("text_encoders.") for n in names):
        return "text-encoder"
    # THREE naming conventions reach the same SD/SDXL UNet and all three have to be
    # recognised here, because a family this function cannot name is scored "unknown" and
    # ALLOWED_BASE["unknown"] permits every base - so a silent SKIP of the base check is
    # indistinguishable from a PASS. The dotted test alone missed two of the three:
    #   ldm / ComfyUI   input_blocks.4.1.proj_in
    #   kohya           lora_unet_input_blocks_4_1_proj_in     <- underscores, no dots
    #   diffusers       unet.down_blocks.1.attentions.0. ...   <- different block names
    # Dropping the trailing dot covers kohya. The diffusers form needs its own test AND
    # needs to run BEFORE the transformer-block families below, because its
    # `transformer_blocks.0` matches the DiT double-block pattern at index 0 and fell
    # through to "unknown" - which is how five SDXL style LoRAs on this box went
    # unchecked without a single warning.
    if any(("input_blocks" in n) or ("output_blocks" in n) or ("middle_block" in n)
           for n in names):
        # label_emb is the SDXL pooled/size-conditioning embedder. SD1.5 has no such key,
        # so its presence confirms SDXL from the keys and not from the filename.
        return "sdxl" if any("label_emb" in n for n in names) else "sd-unet"
    if any(("down_blocks" in n) or ("up_blocks" in n) or ("mid_block" in n)
           for n in names):
        # Deliberately the conservative "sd-unet" rather than "sdxl". Cross-attention
        # width would separate SDXL (2048) from SD1.5 (768), but an attention-only LoRA
        # need not patch a cross-attention layer at all, so the width is not always there
        # to read. sd-unet permits base sdxl or other, which is still enough to catch a
        # Qwen or FLUX file filed as sdxl - the mistake this check exists for.
        return "sd-unet"

    # `single_transformer_blocks` also matches the double pattern once `_` is an allowed
    # separator, so exclude it explicitly rather than relying on a lookbehind.
    dbl = _indices(_DOUBLE, names, exclude="single_")
    sgl = _indices(_SINGLE, names)
    if sgl:
        # FLUX.1 = 19 double + 38 single at width 3072. FLUX.2 = 8 double + 48 single at
        # width 6144. The two are not confusable.
        if len(dbl) >= 15 and len(sgl) >= 30:
            return "flux1"
        return "flux2"
    if dbl:
        top = max(dbl)
        if top >= 55:
            return "qwen-family"
        # 48 blocks (0..47) is LTX-2.3. The audio-attention families corroborate it but
        # must NOT be required: ltx-2.3-22b-ic-lora-union-control patches attn1/attn2/ff
        # only, has no audio keys at all, and an audio-gated test filed it as `unknown`.
        if 40 <= top < 55:
            return "ltx"
        return "unknown"
    plain = _indices(_PLAIN, names)
    if plain and max(plain) >= 30 and widest >= 5120:
        return "wan"
    return "unknown"


def describe(path):
    """Everything this tool knows about one file on disk, read from its own bytes.

    ALPHA IS PAIRED WITH ITS OWN LAYER'S RANK, not with the file's modal rank. The first
    version of this function divided one layer's alpha by a different layer's rank and
    reported ltx_2.3_22b_distilled at scale 0.826. That file is a dynamic-rank resize
    where alpha == rank in EVERY layer, i.e. scale 1.0 throughout, and the wrong number
    would have been copied straight into a card as if measured. Pairing by key prefix
    fixes it and costs nothing.
    """
    hdr, data_start = read_header(path)
    meta = hdr.get("__metadata__")
    names = [k for k in hdr if k != "__metadata__"]

    widest, ranks, rank_of, alpha_names = 0, {}, {}, []
    for n in names:
        shape = hdr[n].get("shape") or []
        for d in shape:
            if isinstance(d, int) and d > widest:
                widest = d
        m = _RANKISH.search(n)
        if m and len(shape) == 2:
            r = min(shape)
            ranks[r] = ranks.get(r, 0) + 1
            rank_of[n[:m.start()].rstrip("._")] = r
        elif n.endswith(".alpha"):
            alpha_names.append(n)

    # MODAL rank, not the only rank. ltx_2.3_22b_distilled is a genuine dynamic-rank
    # resize whose per-layer rank runs from 3 to 384; reporting one number for it would
    # be a lie, so the dynamic case is flagged and printed with a `~`.
    rank = max(ranks, key=ranks.get) if ranks else None
    dynamic = len(ranks) > 8

    alpha, scales = None, {}
    if alpha_names:
        with open(path, "rb") as fh:
            for n in alpha_names[:600]:          # sampled; 600 layers settle any file here
                v = read_scalar(fh, hdr[n], data_start)
                if v is None:
                    continue
                if alpha is None:
                    alpha = v
                r = rank_of.get(n[:-len(".alpha")])
                if r:
                    s = round(v / r, 6)
                    scales[s] = scales.get(s, 0) + 1
    if scales:
        scale = max(scales, key=scales.get)
    elif rank:
        scale = 1.0                # ComfyUI defaults a LoRA with no alpha tensor to 1.0
    else:
        scale = None

    return {
        "bytes": os.path.getsize(path),
        "tensors": len(names),
        "rank": rank,
        "rank_dynamic": dynamic,
        "rank_distinct": len(ranks),
        "alpha": alpha,
        "scale": scale,
        "scale_uniform": len(scales) <= 1,
        "dtypes": sorted({hdr[n].get("dtype") for n in names if hdr[n].get("dtype")}),
        "family": infer_family(names, widest),
        "widest_dim": widest,
        "meta_keys": sorted(meta) if isinstance(meta, dict) else None,
        "meta": meta if isinstance(meta, dict) else None,
    }


def stated_base(meta):
    """A base model NAMED IN THE FILE, or None. Distinguishes READ from INFERRED.

    Only one file on this box names an exact revision (`Qwen/Qwen-Image-2512`). Most
    state at most a family, and nine state nothing at all - so a card whose `note` claims
    the header gave it the base had better show up here.
    """
    if not meta:
        return None
    for k in ("base_model", "ss_base_model_version", "ss_sd_model_name",
              "modelspec.architecture", "model_version"):
        v = meta.get(k)
        if v:
            return "%s = %s" % (k, v)
    return None


def stated_trigger(meta):
    """A trigger phrase READ FROM THE FILE, or None.

    The repo's own LORAS.md asserts there is no way to read a trigger word off a
    safetensors file. That is false, and this is the check that proves it every run:
    qwen_image_2512_storybook_anime_lora carries trigger_phrase directly.
    """
    if not meta:
        return None
    for k in ("trigger_phrase", "ss_trigger_words", "trigger_words", "activation_text"):
        v = meta.get(k)
        if v:
            return str(v)
    return None


# ---------------------------------------------------------------------------
# cards
# ---------------------------------------------------------------------------

def load_cards(d):
    """Every card, plus every card file that would not parse.

    A broken card is REPORTED, not raised - same choice compose.load_libs makes, and for
    the same reason: one malformed file must not blind you to the other nineteen.
    """
    cards, broken = {}, []
    if not os.path.isdir(d):
        return cards, [(d, "card directory does not exist")]
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(d, fn)
        try:
            with open(p, "r", encoding="utf-8") as fh:
                c = json.load(fh)
            cards[c.get("id") or fn[:-5]] = c
        except Exception as exc:                                   # noqa: BLE001
            broken.append((fn, str(exc)))
    return cards, broken


def check_card(card, facts):
    """Schema and reality problems with one card, worst first, as plain sentences."""
    out = []
    cid = card.get("id", "?")

    for f in REQUIRED:
        if f not in card:
            out.append("missing required field `%s`" % f)

    if card.get("base_model") not in BASE_MODELS:
        out.append("base_model %r is not one of %s"
                   % (card.get("base_model"), "|".join(BASE_MODELS)))
    if card.get("engine") not in ENGINES:
        out.append("engine %r is not one of anime|qwen|video|null" % card.get("engine"))
    if card.get("kind") not in KINDS:
        out.append("kind %r is not one of %s" % (card.get("kind"), "|".join(KINDS)))
    if card.get("status") not in STATUSES:
        out.append("status %r is not one of %s"
                   % (card.get("status"), "|".join(STATUSES)))

    bm = card.get("base_model")
    if bm in ENGINE_FOR and card.get("engine") != ENGINE_FOR[bm]:
        out.append("engine %r contradicts base_model %r, which derives engine %r"
                   % (card.get("engine"), bm, ENGINE_FOR[bm]))

    sr = card.get("strength_range")
    st = card.get("strength")
    if not (isinstance(sr, list) and len(sr) == 2):
        out.append("strength_range must be a two-element list")
    elif isinstance(st, (int, float)) and not (sr[0] <= st <= sr[1]):
        out.append("strength %s is outside strength_range %s" % (st, sr))

    # THE STYLES-LIBRARY MISTAKE, caught mechanically. A status that claims something was
    # seen, with nothing recorded about what was seen, is the exact shape of the 46 cards
    # that shipped `ready` unrendered.
    if card.get("status") in ("ready", "weak") and not (card.get("verdict") or "").strip():
        out.append("status=%s but `verdict` is empty - a status that claims a render must "
                   "say what the render looked like" % card.get("status"))
    if card.get("status") == "untested" and (card.get("verdict") or "").strip():
        out.append("status=untested but `verdict` is not empty - if there is a verdict, "
                   "the status should reflect it")

    if facts:
        fam = facts["family"]
        allowed = ALLOWED_BASE.get(fam, set(BASE_MODELS))
        if bm not in allowed:
            out.append("BASE MISMATCH: keys are %s geometry, which permits %s, but the "
                       "card says %r. A LoRA on the wrong base is a silent no-op."
                       % (fam, "|".join(sorted(allowed)) or "nothing", bm))
        trg = stated_trigger(facts.get("meta"))
        if trg and (card.get("trigger") or "").strip() != trg.strip():
            out.append("the FILE states trigger %r but the card says %r"
                       % (trg, card.get("trigger")))
    return ["%s: %s" % (cid, m) for m in out]


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cards", default=DEFAULT_CARDS)
    ap.add_argument("--characters", default=DEFAULT_CHARS,
                    help="character cards, which own their trained LoRAs by `lora` key")
    ap.add_argument("--loras", default=DEFAULT_LORAS)
    ap.add_argument("--json", action="store_true", help="machine-readable, no prose")
    a = ap.parse_args(argv)

    cards, broken = load_cards(a.cards)
    by_file = {}
    for cid, c in cards.items():
        by_file.setdefault(c.get("file"), []).append(cid)

    on_disk = {}
    unreadable = []
    if os.path.isdir(a.loras):
        for fn in sorted(os.listdir(a.loras)):
            if not fn.endswith(".safetensors"):
                continue
            try:
                on_disk[fn] = describe(os.path.join(a.loras, fn))
            except Exception as exc:                               # noqa: BLE001
                unreadable.append((fn, str(exc)))
                on_disk[fn] = None

    # Files claimed by a character card: reachable, just not through the pickable library.
    char_owner = {}
    if os.path.isdir(a.characters):
        for fn in sorted(os.listdir(a.characters)):
            if not fn.endswith(".json"):
                continue
            try:
                cc = json.load(open(os.path.join(a.characters, fn), encoding="utf-8"))
            except Exception:                                      # noqa: BLE001
                continue
            for key in ("lora", "lora_previous_file"):
                v = cc.get(key)
                if isinstance(v, str) and v.endswith(".safetensors"):
                    char_owner.setdefault(v, []).append(cc.get("id") or fn[:-5])
    # A superseded LoRA is kept ON PURPOSE so a claim can be re-measured instead of taken
    # on trust (see TERRA.lora_previous). It is neither an orphan nor a live card, so it
    # gets its own line rather than a warning: the same trained stem as a file the cast
    # DOES point at, with a version suffix.
    def _stem(f):
        # character_terra_00001_v3.safetensors and character_terra_00001_.safetensors are
        # the same trained character at two revisions. train_character.py names revisions
        # with a _vN suffix on the SaveLoRA stem, so strip it and compare the stem.
        return re.sub(r"_v\d+$", "", f.rsplit(".safetensors", 1)[0]).rstrip("_")
    stems = {_stem(f) for f in char_owner}
    def superseded(f):
        return _stem(f) in stems

    char_files = [f for f in on_disk
                  if f not in by_file and (f in char_owner or superseded(f))]
    orphan_files = [f for f in on_disk if f not in by_file and f not in char_files]
    missing_char = sorted({f for f in char_owner if f not in on_disk})
    missing_files = sorted({c.get("file") for c in cards.values()
                            if c.get("file") not in on_disk})
    dupes = {f: ids for f, ids in by_file.items() if len(ids) > 1}

    problems = []
    for cid in sorted(cards):
        problems += check_card(cards[cid], on_disk.get(cards[cid].get("file")))

    rollup = {}
    for c in cards.values():
        rollup[c.get("status")] = rollup.get(c.get("status"), 0) + 1

    if a.json:
        json.dump({"cards": len(cards), "files": len(on_disk),
                   "orphan_files": sorted(orphan_files), "missing_files": missing_files,
                   "character_owned": sorted(char_files),
                   "character_missing": missing_char,
                   "duplicate_file_refs": dupes, "unreadable": unreadable,
                   "broken_cards": broken, "problems": problems, "status": rollup,
                   "facts": on_disk}, sys.stdout, indent=2, sort_keys=True)
        print()
        return 0 if not (orphan_files or missing_files or missing_char
                         or problems or broken) else 1

    print("LoRA LIBRARY SCAN")
    print("  cards  %s" % a.cards)
    print("  files  %s" % a.loras)
    print("  %d cards, %d .safetensors on disk" % (len(cards), len(on_disk)))
    print()

    print("MATCHED  (card <-> file, and what the file's own bytes say)")
    hdr = "  %-32s %-11s %-9s %-11s %-6s %-6s %s"
    print(hdr % ("id", "base(card)", "kind", "geom(file)", "rank", "scale", "status"))
    for cid in sorted(cards):
        c = cards[cid]
        f = on_disk.get(c.get("file"))
        if not f:
            continue
        print(hdr % (cid[:32], c.get("base_model"), c.get("kind"), f["family"],
                     "%s%s" % (f["rank"], "~" if f["rank_dynamic"] else ""),
                     ("%.4g" % f["scale"]) if f["scale"] else "-",
                     c.get("status")))
    print("  rank ~ = per-layer dynamic rank, the printed value is only the modal one.")
    print("  scale  = alpha/rank as ComfyUI applies it, or 1.0 where the file carries no")
    print("           alpha tensor. It varies 32x across this set and is invisible in every")
    print("           UI - but do NOT read a low value as `weak`: sd-scripts applies the")
    print("           same factor during training, so the learned weights compensate.")
    print()

    def section(title, rows, empty):
        print(title)
        if not rows:
            print("  %s" % empty)
        for r in rows:
            print("  %s" % r)
        print()

    section("ON DISK WITH NO CARD  (installed and unreachable by the resolver)",
            ["%s   [%s, rank %s, %d tensors]"
             % (f, (on_disk[f] or {}).get("family", "?"),
                (on_disk[f] or {}).get("rank"), (on_disk[f] or {}).get("tensors", 0))
             for f in sorted(orphan_files)],
            "none - every .safetensors on disk has a card")

    section("OWNED BY A CHARACTER CARD  (not in the pickable library, and should not be)",
            ["%s   <- %s" % (f, ", ".join(char_owner.get(f) or ["superseded, kept for "
                                                               "re-measurement"]))
             for f in sorted(char_files)],
            "none")

    section("CARD WITH NO FILE  (offers a choice that will fail inside ComfyUI)",
            missing_files + ["%s <- character %s" % (f, ", ".join(char_owner[f]))
                             for f in missing_char],
            "none - every card points at a file that exists")

    section("TWO CARDS, ONE FILE",
            ["%s <- %s" % (f, ", ".join(ids)) for f, ids in sorted(dupes.items())],
            "none")

    section("UNPARSEABLE", ["%s: %s" % (f, e) for f, e in broken + unreadable], "none")

    section("PROBLEMS", problems, "none")

    print("HONESTY LEDGER  (what the library CLAIMS to have seen)")
    for s in STATUSES:
        n = rollup.get(s, 0)
        if n:
            print("  %-12s %d" % (s, n))
    seen = rollup.get("ready", 0) + rollup.get("weak", 0)
    print("  %d of %d cards claim a render happened. Every one of those must carry a "
          "verdict" % (seen, len(cards)))
    print("  saying what was seen; the check above fails the build if one does not.")
    print()

    bad = bool(orphan_files or missing_files or missing_char or problems or broken
               or unreadable or dupes)
    print("RESULT: %s" % ("PROBLEMS FOUND" if bad else "clean"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
