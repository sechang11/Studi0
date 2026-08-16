"""studio/engine.py - the one home for graph building and engine plumbing.

    from engine import image_graph, video_graph, keyscale, apply_dials, style_pool

WHY (ARCHITECTURE Phase 2). Engine knowledge lived in five files: routing in compose,
subject rules in roll, graph branches in render_job, a dialect guard in isolation_run,
subject modes in sequence_render - and keyscale existed TWICE, in render_job and epic,
identical but for the docstring. Scattered copies are how the flux2 dials went unset for
weeks and how wave 4 lost 82 frames: the fix lands in one copy and not its siblings.

WHAT LIVES HERE. Graph builders (image, the LTX video pass), dial application by input
key, the keyscale guard (SOUND-05), and style_pool - which styles may legally meet a
given character. Routing itself stays in compose.resolve and the dialect LAW stays in
compose._check_character (Phase 1); this module consumes both, it does not compete.

DEPENDENCY DIRECTION. engine imports comfy, compose and cards. It never imports epic or
any script: before this module, render_job - a UI-facing tool - imported a FILM SCRIPT to
get load_wf, which meant the film script owned the render spine's plumbing. image_graph
and keyscale were extracted from render_job VERBATIM and proven byte-equal before their
originals were replaced with delegations.
"""
import json
import os
import sys

STUDIO = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import set_path                            # noqa: E402

HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")


def load_wf(name):
    """A workflow file as a graph dict, underscore keys dropped. The same three lines
    epic.py carries; this copy exists so the render spine does not import a film script
    to read a JSON file. epic delegates here in a later pass."""
    return {k: v for k, v in json.load(open(os.path.join(ROOT, "workflows", name),
                                            encoding="utf-8")).items()
            if not k.startswith("_")}


def image_graph(job):
    """The exact ComfyUI graph for this job, built and not submitted.

    Split out of render_image so /library can show the workflow that produced a picture
    without re-rendering it, and without a second copy of the wiring that would drift away
    from this one.
    """
    eng = job.get("engine", "anime")
    if eng == "flux2":
        wf = load_wf("40_flux2_t2i.json")
        # Dials are applied BY INPUT KEY, not by class name. 40_flux2_t2i is a custom
        # sampler graph - the seed is `noise_seed` on RandomNoise, the steps and the size
        # are on Flux2Scheduler, and the latent is EmptyFlux2LatentImage. Matching class
        # names meant the seed and the size were never set at all, and every flux2 render
        # silently reused whatever was saved in the workflow file. A steps sweep returned
        # four pixel-identical frames before this was found.
        for nid, n in wf.items():
            if not isinstance(n, dict):
                continue
            ct = n.get("class_type", "")
            ins = n.get("inputs")
            if not isinstance(ins, dict):
                continue
            if ("CLIPTextEncode" in ct or "TextEncode" in ct) and "text" in ins:
                ins["text"] = job["prompt"]
            for k in ("noise_seed", "seed"):
                if k in ins:
                    ins[k] = job["seed"]
            if "width" in ins and "height" in ins:
                ins["width"] = job["width"]
                ins["height"] = job["height"]
            if "steps" in ins and job.get("steps"):
                ins["steps"] = int(job["steps"])
            if ct == "SaveImage":
                ins["filename_prefix"] = "claude-generated/rolled/%s" % job["id"]
    elif eng == "qwen":
        wf = load_wf("13_qwen_t2i_styled.json")
        set_path(wf, "10.inputs.text", job["prompt"])
        set_path(wf, "11.inputs.text", job.get("negative") or "")
        set_path(wf, "12.inputs.width", job["width"])
        set_path(wf, "12.inputs.height", job["height"])
        set_path(wf, "13.inputs.seed", job["seed"])
        if job.get("style_lora"):
            set_path(wf, "7.inputs.lora_name", job["style_lora"])
            set_path(wf, "7.inputs.strength_model", float(job.get("style_lora_strength") or 1.0))
        else:
            set_path(wf, "7.inputs.strength_model", 0.0)
        set_path(wf, "15.inputs.filename_prefix", "claude-generated/rolled/%s" % job["id"])
    else:
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
        set_path(wf, "4.inputs.weight", 0.0)
        set_path(wf, "5.inputs.text", job["prompt"])
        set_path(wf, "6.inputs.text", job.get("negative") or
                 "lowres, worst quality, bad anatomy, bad hands, watermark, text")
        set_path(wf, "8.inputs.seed", job["seed"])
        for n in ("7", "10"):
            set_path(wf, "%s.inputs.width" % n, job["width"])
            set_path(wf, "%s.inputs.height" % n, job["height"])
        if job.get("character_lora"):
            # compose.resolve() already checked the base model, so reaching here means the
            # weights genuinely attach to this checkpoint. Injected rather than assumed to
            # exist in the graph, the same way epic.py does it for identity on clips.
            wf["60"] = {"class_type": "LoraLoaderModelOnly",
                        # Spliced between the IPAdapter patch and the sampler, NOT straight
                        # off the checkpoint - node 8 reads its model from node 4, so
                        # hanging this on node 1 would leave it dangling and silently unused.
                        "inputs": {"model": ["4", 0], "lora_name": job["character_lora"],
                                   "strength_model": float(
                                       job.get("character_lora_strength") or 0.5)}}
            set_path(wf, "8.inputs.model", ["60", 0])
        set_path(wf, "11.inputs.filename_prefix", "claude-generated/rolled/%s" % job["id"])
    return wf


_KEYSCALE = {}


def keyscale(want):
    """Coerce a cue card's key into a spelling the ACE-Step node will accept, or drop it.

    The cards are written the way a musician writes: `B flat minor`, `E flat major`. The
    node's widget is a fixed 34-item combo that spells those `Bb minor` and `Eb major`, and
    a value outside the list is a HARD prompt-validation error - ComfyUI refuses the whole
    graph, render_job.py dies before printing anything, and the harness sees only
    `failed (no result)`. That cost 20 of 137 jobs in one run.

    The allowed list is read from the running server rather than copied here, so it cannot
    drift from the node. Anything still unmatched is dropped: an unkeyed cue is fine, a
    refused graph is not.
    """
    want = str(want or "").strip()
    if not want:
        return ""
    if not _KEYSCALE:
        try:
            import urllib.request
            raw = urllib.request.urlopen(
                "http://%s/object_info/TextEncodeAceStepAudio1.5" % HOST, timeout=8).read()

            def find(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k == "keyscale":
                            return v[1]["options"]
                        r = find(v)
                        if r:
                            return r
                elif isinstance(o, list):
                    for v in o:
                        r = find(v)
                        if r:
                            return r
                return None
            for o in (find(json.loads(raw)) or []):
                _KEYSCALE[o.lower()] = o
        except Exception:
            return ""
    cand = want.lower()
    for a, b in ((" flat ", "b "), (" sharp ", "# ")):
        cand = cand.replace(a, b)
    return _KEYSCALE.get(cand, "")


def apply_dials(wf, text=None, seed=None, steps=None, width=None, height=None,
                prefix=None):
    """Set dials BY INPUT KEY, never by class name.

    The lesson is measured: 40_flux2_t2i keeps its seed on RandomNoise as `noise_seed` and
    its steps on Flux2Scheduler, so code matching class names like "Sampler" set nothing,
    and a steps sweep returned four pixel-identical frames while reporting eight distinct
    successes. A node that HAS an input gets the value; class names differ per graph and
    per custom-node pack, but the input a node accepts is the thing that is actually true
    about it.
    """
    for n in wf.values():
        if not isinstance(n, dict):
            continue
        ins = n.get("inputs")
        if not isinstance(ins, dict):
            continue
        ct = n.get("class_type", "")
        if text is not None and ("TextEncode" in ct) and "text" in ins:
            ins["text"] = text
        if seed is not None:
            for k in ("noise_seed", "seed"):
                if k in ins:
                    ins[k] = seed
        if steps is not None and "steps" in ins:
            ins["steps"] = int(steps)
        if width is not None and "width" in ins and "height" in ins:
            ins["width"], ins["height"] = int(width), int(height or width)
        if prefix is not None and ct == "SaveImage":
            ins["filename_prefix"] = prefix
    return wf


def style_pool(libs, pool, character_card=None, allow_self_contained=None):
    """The styles in `pool` that may legally meet this context.

    Two exclusions, both paid for. A style on an engine that cannot read the character's
    dialect deletes the character (wave 4: 82 of 200 frames, one woman rendered from
    leftover "male focus" tags). A self-contained style is already the whole picture - a
    sign, a printed page - and roll drops the character when it meets one: the same bug
    wearing a different hat. `allow_self_contained` defaults to False when a character is
    present and True otherwise.
    """
    import cards
    import compose
    if allow_self_contained is None:
        allow_self_contained = character_card is None
    ok_engines = cards.engines_for(character_card) if character_card else None
    out = []
    for s in pool:
        card = (libs.get("styles") or {}).get(s) or {}
        if not allow_self_contained and card.get("self_contained"):
            continue
        if ok_engines is not None:
            try:
                e = compose.resolve(libs, {"style": s}).get("engine")
            except Exception:
                continue
            # "either" is excluded on purpose: it resolves per SUBJECT, so a
            # per-character pool cannot vouch for which engine it lands on -
            # matching the styles_for this replaces, proven set-equal.
            if e not in ok_engines:
                continue
        out.append(s)
    return out


def negative_node(wf):
    """The id of the node feeding a sampler's `negative` input - by GRAPH SHAPE.

    Never by remembered number: node 11 is the negative encoder in 12_ltx23_i2v_audio,
    a SaveImage prefix in another workflow and an audio duration in a third. The first
    negative-prompt check grepped for `set_path(wf, "11.` and reported all four graphs
    healthy while the negative was unreachable in every one of them."""
    for nid, node in wf.items():
        if not isinstance(node, dict):
            continue
        v = (node.get("inputs") or {}).get("negative")
        if isinstance(v, list) and v and str(v[0]) in wf:
            return str(v[0])
    return None


def set_negative(wf, text, keep_shipped=True, positive=""):
    """Write the negative prompt onto whichever node the graph routes as `negative`.

    keep_shipped: the workflow's committed baseline stays as the head of the string
    (it encodes per-model lessons - "pc game, console game" on LTX, "3d render" on
    qwen-edit) and the film/style text is appended. Any shipped clause whose every word
    the POSITIVE asks for is dropped first - asking for "1girl" and forbidding "1girl,
    girl, female" on the same beat was fatal for a whole class of character.
    Returns the node id written, or None when the graph has no negative input (ACE-Step's
    tag graph, for instance) - callers treat None as "this graph has no negative", not
    as failure."""
    nid = negative_node(wf)
    if nid is None:
        return None
    ins = wf[nid].setdefault("inputs", {})
    key = "text" if "text" in ins else "prompt" if "prompt" in ins else None
    if key is None:
        return None
    parts = []
    if keep_shipped:
        shipped = str(ins.get(key) or "")
        if positive:
            import re as _re
            have = set(_re.findall(r"[a-z0-9_]+", positive.lower()))
            kept = []
            for clause in shipped.split(","):
                words = _re.findall(r"[a-z0-9_]+", clause.lower())
                if words and all(w in have for w in words):
                    continue
                kept.append(clause.strip())
            shipped = ", ".join(k for k in kept if k)
        if shipped.strip():
            parts.append(shipped.strip())
    if str(text or "").strip():
        parts.append(str(text).strip())
    ins[key] = ", ".join(parts)
    return nid


def video_graph(job, staged_image):
    """The LTX image-to-video pass over a staged keyframe.

    job["video_engine"] picks the model, default unchanged:
      "ltx23" (default) - 12_ltx23_i2v_audio. More motion (8.79 vs 1.54 measured), but
                          the picture DRIFTS off the approved keyframe (0.141 SSIM lost
                          across 4s).
      "ltx25"           - 51_ltx25_i2v. Holds the keyframe (drift -0.004, i.e. the last
                          frame is as close as the first) with gentler motion, and is
                          the only engine here that can generate CONNECTED SHOTS with a
                          cut inside one pass (studio/_tools/multishot.py).
    Numbers from samples/ltx25_probe/report.json, one keyframe, same seed and motion
    text; the static floor is motion 0.001, so 2.5 moves, it just moves less."""
    if str(job.get("video_engine") or "ltx23") == "ltx25":
        return video_graph_25(job, staged_image)
    frames = int(round(job["seconds"] * 24 / 8)) * 8 + 1
    vw, vh = (1216, 704) if job["width"] <= job["height"] else (
        min(1216, job["width"] // 8 * 8), min(704, job["height"] // 8 * 8))
    staged = staged_image
    wf = load_wf("12_ltx23_i2v_audio.json")
    set_path(wf, "8.inputs.image", staged)
    set_path(wf, "10.inputs.text", job.get("motion_text") or "gentle natural motion")
    set_path(wf, "20.inputs.width", vw)
    set_path(wf, "20.inputs.height", vh)
    set_path(wf, "20.inputs.length", frames)
    set_path(wf, "21.inputs.frames_number", frames)
    # The shipped graph asks the audio latent for 25 fps against a 24 fps video. That is a
    # 4% drift - a second of slip over half a minute - so it is corrected here to match the
    # video rate rather than inherited (open task #45 fixes it in the workflow itself).
    set_path(wf, "21.inputs.frame_rate", 24)
    set_path(wf, "32.inputs.noise_seed", job["seed"])
    set_path(wf, "43.inputs.filename_prefix", "claude-generated/rolled/%s" % job["id"])
    return wf


def video_graph_25(job, staged_image):
    """LTX-2.5 i2v (51_ltx25_i2v.json). Node ids are the template's own, recorded in the
    workflow's `_` block: 395 image, 376 prompt, 373 negative, 362 seconds, 361 fps,
    383 the LLM prompt-expander switch, 339/338 the two sampler seeds, 75 prefix.

    The expander is left OFF by default: it rewrites the motion text into a long cinematic
    caption, which is lovely for a one-off and fatal for a film, where the same motion card
    must mean the same thing on every beat."""
    wf = load_wf("51_ltx25_i2v.json")
    seconds = float(job.get("seconds") or 4)
    set_path(wf, "395.inputs.image", staged_image)
    set_path(wf, "376.inputs.value", job.get("motion_text") or "gentle natural motion")
    if job.get("negative"):
        set_path(wf, "373.inputs.text", job["negative"])
    set_path(wf, "383.inputs.value", bool(job.get("prompt_expander")))
    set_path(wf, "362.inputs.value", max(1, int(round(seconds))))
    set_path(wf, "361.inputs.value", 24)
    set_path(wf, "339.inputs.noise_seed", int(job.get("seed") or 0))
    set_path(wf, "338.inputs.noise_seed", int(job.get("seed") or 0))
    set_path(wf, "75.inputs.filename_prefix",
             "claude-generated/rolled/%s" % job.get("id", "ltx25"))
    return wf
