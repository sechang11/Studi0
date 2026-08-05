#!/usr/bin/env python3
"""Catalogue the ComfyUI capability archive into studio/capabilities.json.

~/ComfyUI/output/claude-generated/ holds ~94 folders. Thirty-four of them are a
capability curriculum - one folder per thing ComfyUI can do on this box, most with a
CAPABILITY.json declaration written by scripts/_write_caps.py. The rest are production
runs (studio library generation, TERRA probes, motion sweeps, rendered shorts).

None of it is visible in the studio app. This tool walks the archive, merges the
declarations with MEASURED filesystem facts, resolves each capability's workflow file,
works out whether the studio app can actually run it, and writes one JSON the app can
render as a gallery.

    python3 studio/_tools/capability_scan.py            # write studio/capabilities.json
    python3 studio/_tools/capability_scan.py --print    # summary to stdout, no write

READ-ONLY over the archive. Nothing is moved, renamed or deleted.

The representative sample for each capability was chosen BY LOOKING at the images and at
frame strips pulled from the clips - not by taking the first file or trusting the folder
name. Where that choice differs from the declaration's own panel order, PICKS records why.
"""
import argparse
import json
import os
import sys
import time

HOME = os.path.expanduser("~")
ARCHIVE = os.path.join(HOME, "ComfyUI/output/claude-generated")
KIT = os.path.join(HOME, "shared/comfy-studio")
WORKFLOWS = os.path.join(KIT, "workflows")
OUT = os.path.join(KIT, "studio/capabilities.json")

# Folders that predate _write_caps.py and carry no CAPABILITY.json, but ARE capabilities
# (the archive README documents them). Everything else without a declaration is a
# production run, not a capability.
UNDECLARED = {
    "08-music": {
        "title": "Music generation from tags",
        "claim": "ACE-Step 1.5 Turbo writes a full cue from genre/instrumentation/mood/tempo "
                 "tags. Sixty seconds of scored music in well under ten. Prompt with TAGS, "
                 "not prose; leave lyrics empty for an instrumental.",
        "model": "ACE-Step 1.5 Turbo",
        "workflow": "06_acestep_music.json",
        "status": "verified", "verdict": "works",
    },
    "09-sound-effects": {
        "title": "Sound effects and ambience beds",
        "claim": "Stable Audio 3 Medium renders a named sound rather than a scene. "
                 "'Wind through dry grass, distant surf, occasional gust' beats "
                 "'a lonely coastal morning' every time.",
        "model": "Stable Audio 3 Medium",
        "workflow": "10_stableaudio_sfx.json",
        "status": "verified", "verdict": "works",
    },
    "11-short-film": {
        "title": "Assembled short films - every capability at once",
        "claim": "Ten finished shorts. Keyframes, clips, dialogue, score, ambience, burnt-in "
                 "captions and a cut, assembled by scripts/film.py and scripts/cartoon.py "
                 "from a JSON film spec. last-light is 56 s and 13 shots for about six "
                 "minutes of GPU time.",
        "model": "all of the above, assembled",
        "workflow": "scripts/film.py + scripts/cartoon.py",
        "status": "verified", "verdict": "works",
    },
}

# Files in the studio app's actual render path. A capability counts as EXPOSED only if one
# of these reaches its workflow. scripts/_write_caps.py and scripts/capcard.py are the
# archive's own generators and are deliberately excluded - they mention every workflow,
# including ones that do not exist.
APP_PATH = [
    "studio/compose.py", "studio/compile.py", "studio/serve.py",
    "studio/gallery_gen.py", "studio/tag_examples.py", "scripts/short.py",
]
# Reachable by running a script by hand, but never from the app UI.
SCRIPT_PATH = [
    "scripts/film.py", "scripts/cartoon.py", "scripts/epic.py", "scripts/pipeline.py",
    "scripts/idea.py", "scripts/sweep.py", "scripts/make_audio_library.py",
    "scripts/make_sheets.py", "scripts/style_ab.py",
]
EXCLUDE_FROM_EXPOSURE = {"scripts/_write_caps.py", "scripts/capcard.py",
                         "studio/_tools/capability_scan.py"}
# studio/_tools/*.py is also scanned and counts as the script tier - a tool you run by hand.
TOOLS_DIR = "studio/_tools"

# Some capabilities reach the app as a PAGE rather than as a runnable workflow. Verified by
# reading the page, not assumed from its name.
APP_PAGE = {
    "17-lora-mechanics": ("/loras", "app",
        "The page renders a strength ladder whose leftmost cell is forced to strength 0 "
        "because a LoRA is a delta on the base - which is folder 17's exact lesson, applied "
        "across 22 LoRAs instead of one accelerator. The capability is productised even "
        "though the sweep workflow is not wired."),
    "31-character-identity": ("/cast, /character/TERRA", "adjacent",
        "NOT the same capability. The declared LTX ID-LoRA route is untested and unexposed. "
        "The app attacks the same problem - identity across shots - from the other side, with "
        "reusable cast cards backed by trained character LoRAs. Counted as adjacent, not as "
        "exposed, so the gallery does not imply ID-LoRA works."),
}

# The archive documents the 2026-07-29/31 generation of workflows. The kit has since moved
# on, and several capabilities are live in the app through a NEWER workflow the archive
# never mentions. Without this table the scan reports "not exposed" for things the app
# plainly does. Every entry was verified by grepping the app render path.
APP_EQUIV = {
    "01-text-to-image": [("13_qwen_t2i_styled.json",
        "The app's text-to-image is the styled variant, driven by compile.py and short.py. "
        "22_anime_kf_ipadapter.json is the second, illustration-engine route.")],
    "02-image-editing": [("14_qwen_edit_ref.json",
        "The app edits with a reference image rather than by bare instruction - short.py and "
        "make_sheets.py. The archived 03_qwen_image_edit.json path is not wired up.")],
    "10-voice": [("16_indextts2_voice.json",
        "short.py routes voice to IndexTTS2, which has the forced duration the declaration "
        "lists as the one thing missing from Chatterbox."),
        ("17_higgs_v3_voice.json",
        "short.py also routes to Higgs v3, and seventeen named hv3_* voices now sit in the "
        "folder. The declared 'one voice pack, characters are pitch-shifted' problem is solved.")],
    "27-lora-training": [("33_train_character_lora.json",
        "SCRIPT TIER, and it flatly contradicts the folder. The workflow exists (2026-08-03) "
        "and studio/_tools/train_character.py drives it; TERRA's rank-16 v3 LoRA is its "
        "output. The declaration still says 'not built yet'.")],
    "16-style-range": [("13_qwen_t2i_styled.json",
        "Productised: the /styles page carries 130 authored style cards resolved through "
        "compose.py, which is this capability turned into a library rather than a sweep.")],
    "11-short-film": [("13_qwen_t2i_styled.json",
        "compile.py builds a .movie and short.py renders it - keyframes, clips, voice, music. "
        "The app assembles films; the archived shorts are its output.")],
}

# Places where the folder's own declaration is provably out of date or overstated. Each was
# checked against the current filesystem or against the pixels, not inferred.
STALE = {
    "27-lora-training":
        "Declares status not-explored and 'workflow: not built yet'. Both are now false: "
        "workflows/33_train_character_lora.json exists (2026-08-03), studio/_tools/ holds "
        "train_character.py and make_train_wf.py, twenty-two LoRAs sit in studio/loras, and "
        "TERRA carries a trained rank-16 character LoRA at strength 0.5, retrained twice to "
        "v3. This is the archive's single most out-of-date entry - it calls the largest "
        "untouched capability something that has since been done.",
    "31-character-identity":
        "Declares planned/untested. The LTX ID-LoRA route specifically is still untested, but "
        "the underlying problem is partly solved by another route the declaration does not "
        "know about: a trained character LoRA plus /cast and /character/TERRA.",
    "10-voice":
        "Declares one Chatterbox voice pack with characters differentiated by pitch-shifting, "
        "and names zero-shot cloning as the unwired fix. The folder now holds seventeen named "
        "Higgs v3 voices and short.py routes to both 16_indextts2_voice.json and "
        "17_higgs_v3_voice.json.",
    "08-music":
        "The archive README still lists score/electronic_pulse/acoustic_folk/song_with_vocals. "
        "The folder was regenerated 2026-08-04 with six entirely different cues.",
    "09-sound-effects":
        "Same as 08 - the README's file table predates a 2026-08-04 regeneration and names "
        "files that are no longer here.",
    "03-controlnet":
        "The look_at says the rock outline and horizon 'match to the pixel'. Checked against "
        "the edge map: they do not. The output is a squat concrete bunker on a dry grassy "
        "dune; the control map is a slender lighthouse on jagged sea rock. The composition "
        "rhymes, the structure does not.",
    "16-style-range":
        "Declares one failure out of twelve (stained glass). There are two - style_11 "
        "bronze-sculpture is a desaturated photograph of a live heron, not a bronze. Same "
        "trap, and it strengthens rather than weakens the folder's own lesson.",
}

# The mirror of the main finding. These workflows exist in the kit but have no folder in
# the capability archive - so they are undocumented as capabilities even when the app leans
# on them daily.
ORPHAN_NOTES = {
    "22_anime_kf_ipadapter.json":
        "THE BIGGEST GAP. This is the app's illustration engine - animagine-xl-4.0 with "
        "IPAdapter reference - reached from compose.py, short.py, gallery_gen.py and "
        "tag_examples.py. It carries the whole anime/illustration side of the studio and the "
        "capability archive documents it nowhere. Everything numbered here is the qwen side.",
    "21_sdxl_anime_restyle.json":
        "SDXL restyle on the illustration engine. No capability folder, no card.",
    "32_qwen_turnaround.json":
        "One portrait to many consistent views - the input to character LoRA training. Driven "
        "by studio/_tools/turnaround.py. A real capability with no folder and no card.",
    "33_train_character_lora.json":
        "Character LoRA training, driven by studio/_tools/train_character.py. Folder 27 "
        "declares this 'not built yet'; it was built on 2026-08-03 and TERRA's v3 LoRA came "
        "out of it. The folder and the workflow contradict each other.",
    "15_llm_prompt_studio.json":
        "An earlier LLM prompt path superseded by 16_llm_to_image.json (folder 13).",
    "15_acestep_v1_full.json":
        "ACE-Step v1 full graph. Folder 25 uses 31_acestep_remix.json off the same checkpoint.",
    "18_ltx_prompt_enhancer.json":
        "LTX's own prompt enhancer, including soundscape text. Unused and undocumented.",
}

MEDIA = {
    "image": (".png", ".jpg", ".jpeg", ".webp"),
    "video": (".mp4", ".webm", ".mov", ".mkv"),
    "audio": (".mp3", ".wav", ".flac", ".ogg"),
    "mesh":  (".glb", ".gltf", ".obj", ".ply", ".spz"),
    "text":  (".txt", ".md", ".json", ".srt", ".csv"),
}

# ── Representative samples, chosen by looking ────────────────────────────────────────
# "why" is the reason this file and not another. Several deliberately disagree with the
# declaration's own panels[0]; those say so.
PICKS = {
    "01-text-to-image": ("typography_00001_.png",
        "Three separate lines of text render legibly - THE LAST SIGNAL / LIVE AT THE HARBOUR "
        "HALL / NOVEMBER 14. That is the one thing other open models still fail, and eight of "
        "this folder's files are near-identical lighthouse variants from a resolution sweep."),
    "02-image-editing": ("relight_goldenhour_00001_.png",
        "Storm to golden hour with the rock silhouette, tower position and framing untouched - "
        "reads correctly on its own, without needing the before shot beside it. "
        "object_removal_00001_.png is the more astonishing file (the lighthouse is gone "
        "entirely, bare stack and intact sky) and is the direct counterexample to folder 24."),
    "03-controlnet": ("qwen_controlnet_00001_.png",
        "The only output in the folder. NOTE: checked against the edge map and the "
        "declaration overstates it - the concrete bunker on a dry grassy dune does NOT match "
        "the jagged sea rock and slender lighthouse 'to the pixel'. Composition rhymes; "
        "structure does not. Control strength was evidently loose."),
    "04-upscaling": ("crop_comparison_1to1.png",
        "The only honest file here. A fit-to-screen view of a 24.7 MP upscale proves nothing; "
        "this is the same region at 1:1, naive 4x left and RealESRGAN right. Verified by "
        "looking: the lantern glazing bars, gallery railing and rain streaks resolve on the "
        "right and are mush on the left."),
    "05-image-to-video": ("wan22_i2v_00002_.mp4",
        "The 720p/81f point of the benchmark - the delivery resolution. Frame strip confirms "
        "waves breaking and the beacon sweeping with the keyframe's art direction intact."),
    "06-text-to-video-with-audio": ("train_00001_.mp4",
        "OVERRIDES the declaration's pick of ltx23_av_00002_.mp4, which is a near-black rainy "
        "roof and unreadable as a gallery tile. The train is 1280x704 with real motion blur on "
        "the passing wagons and a generated audio track - it shows the capability and survives "
        "being looked at."),
    "07-frame-interpolation": ("interp32_00001_.mp4",
        "The only clip. Probed: 161 frames over 5.03 s, i.e. 32 fps from an 81-frame source."),
    "08-music": ("epic_battle_00001.mp3",
        "One of six 60 s cues. NOT AUDITIONED - audio cannot be judged by looking, and this "
        "pick is by filename only. Flagged rather than dressed up."),
    "09-sound-effects": ("sword_clash_00001.mp3",
        "NOT AUDITIONED - same caveat as 08. Picked as the clearest single-event sound in the "
        "set; the ambience beds (fire_large, crowd_hubbub, wind_desolate) are longer."),
    "10-voice": ("hv3_samuel_00001.mp3",
        "NOT AUDITIONED. Picked from the hv3_* set on purpose: the declaration says characters "
        "are pitch-shifted from one Chatterbox voice pack, but seventeen named Higgs v3 voices "
        "now sit in this folder and short.py routes to 17_higgs_v3_voice.json. The stale part "
        "of the declaration is the interesting part."),
    "11-short-film": ("last-light/LAST-LIGHT_final.mp4",
        "The finished 56 s film with captions, dialogue and score - the assembled artefact "
        "rather than a keyframe or a clip out of it."),
    "12-segmentation-matting": ("sam3_proof_on_magenta_00001_.png",
        "The stronger of the two claims: the prompt was the words 'the wristwatch' and SAM 3.1 "
        "returned the mask with no clicking or box drawing. Magenta compositing is the only way "
        "to see an alpha channel is right way round - the plain RGBA cutout looks normal even "
        "when inverted."),
    "13-llm-prompt-studio": ("llm_to_image_00001_.png",
        "The diver and the corroded bell. Best-looking image in the folder by a clear margin. "
        "idea_00003 is the instructive one - the astronaut eats noodles through a sealed visor, "
        "because neither the LLM nor the image model reasons about physical plausibility."),
    "14-ltx-two-stage-upscale": ("ltx23_2stage_00001_.mp4",
        "The only clip. Compare against 06's ltx23_av_00002 at the same resolution to see what "
        "the extra 4.5 s of refine pass buys."),
    "15-product-composite": ("product_composite_00001_.png",
        "Verified by looking: the watch is byte-identical to the source and the backdrop key "
        "light does match its direction - and the declared flaw is real, there is no contact "
        "shadow and the bracelet floats out over the water."),
    "16-style-range": ("style_03_ukiyo-e-woodblock_00001_.png",
        "The cleanest win of the twelve - keyline, flat colour, paper grain, and the heron "
        "redrawn rather than photographed. Two failures worth keeping: style_09 stained-glass "
        "put a photoreal heron IN FRONT of a stained glass window, and style_11 bronze-sculpture "
        "is a desaturated photograph of a live bird, not a bronze. Both are the same trap - a "
        "medium that is also a plausible object gets drawn as the object."),
    "17-lora-mechanics": ("strength_04_1-0_00001_.png",
        "The design point. The sweep is the actual lesson: 0.0 is soft grainy 4-step mush, 1.0 "
        "is correct, 1.3 is crushed sky and streaky oversharpened rain. Verified by looking - "
        "1.3 is damage, not more style."),
    "18-audio-to-video": ("ltx_ia2v_speech_00001_.mp4",
        "Frame strip confirms five clearly different mouth shapes across the clip while the "
        "face holds identity. This is the only local path that is DRIVEN BY audio you already "
        "have, rather than generating audio alongside picture."),
    "19-llm-lyrics-song": ("llm_song_00001.mp3",
        "NOT AUDITIONED. The only artefact; the declaration is candid that diction is unverified."),
    "20-qwen-edit-2511": ("edit2511_two_people_00001_.png",
        "Verified by looking: the boatbuilder from 01's portrait and the woman from 18's driver "
        "portrait, generated hours apart in unrelated sessions, are in one photograph with both "
        "faces distinct and the workshop window light falling across both. This is the casting "
        "tool, and it is the thing 2509 cannot do."),
    "21-3d-generation": ("triposplat_orbit_00001_.mp4",
        "A still proves nothing about 3D. Frame strip verified across the full 360: the back of "
        "the brass clockwork owl - which the model never saw and had to invent - holds feather "
        "detail and stays coherent all the way round."),
    "22-flux2": ("flux2_beekeeper_00001_.png",
        "The only output, and it earns the photorealism claim: propolis staining in the nail "
        "beds, bees sharp on the near comb and blurring at the frame edge."),
    "23-control-maps": ("normals_moge_00001_.png",
        "Chosen over depth because it makes the declaration's own point visible - depth flattens "
        "the jacket into one distance, normals hold the fabric folds, the hull curve and the "
        "individual pots on the shelves. Verified side by side."),
    "24-outpaint-removal": ("outpaint_wide_00001_.png",
        "The success, not the failure. 1024 square becomes 2048x1024 with the beekeeper's torso "
        "invented on one side and a whole apiary on the other, and there is no seam. The two "
        "removal files are kept as a documented failure - they put a rope ring and then a stone "
        "ring where the watch had been."),
    "25-music-remix": ("remix_piano_00001.mp3",
        "NOT AUDITIONED. source_original.mp3 sits beside it; the pair is the demo, since the "
        "claim is that the remix keeps the original's bones."),
    "26-vision-caption": ("source_image.png",
        "The image the model was shown; caption.txt holds what it wrote. Worth reading together "
        "- it recovered the weathered hands and shallow depth of field, then called deliberately "
        "flat overcast light 'a bright, sunny day'."),
}


def walk(folder):
    """Measured facts for one folder. Read-only."""
    files, total, oldest, newest = 0, 0, None, None
    kinds = {}
    for root, _dirs, names in os.walk(folder):
        for n in names:
            p = os.path.join(root, n)
            try:
                st = os.stat(p)
            except OSError:
                continue
            files += 1
            total += st.st_size
            oldest = st.st_mtime if oldest is None else min(oldest, st.st_mtime)
            newest = st.st_mtime if newest is None else max(newest, st.st_mtime)
            ext = os.path.splitext(n)[1].lower()
            kind = next((k for k, exts in MEDIA.items() if ext in exts), "other")
            kinds[kind] = kinds.get(kind, 0) + 1
    return {
        "files": files,
        "bytes": total,
        "size_h": human(total),
        "media": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
        "oldest": stamp(oldest),
        "newest": stamp(newest),
    }


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0


def stamp(t):
    return time.strftime("%Y-%m-%d", time.localtime(t)) if t else None


def workflow_files(decl):
    """Split a declaration's workflow field into individual .json filenames."""
    raw = (decl.get("workflow") or "").strip()
    if not raw or raw == "not built yet":
        return []
    return [p.strip() for p in raw.replace("·", "|").replace("+", "|").split("|")
            if p.strip().endswith(".json")]


def scan_consumers():
    """Map workflow filename -> list of kit files that reference it."""
    hits = {}
    tools = []
    tdir = os.path.join(KIT, TOOLS_DIR)
    if os.path.isdir(tdir):
        tools = [f"{TOOLS_DIR}/{n}" for n in sorted(os.listdir(tdir)) if n.endswith(".py")]
    for rel in APP_PATH + SCRIPT_PATH + tools:
        if rel in EXCLUDE_FROM_EXPOSURE:
            continue
        p = os.path.join(KIT, rel)
        if not os.path.exists(p):
            continue
        try:
            body = open(p, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for wf in os.listdir(WORKFLOWS):
            if wf.endswith(".json") and wf in body:
                hits.setdefault(wf, []).append(rel)
    return hits


def pick_sample(folder, name, decl):
    """Representative sample: curated first, then the declaration, then largest media."""
    if name in PICKS:
        rel, why = PICKS[name]
        if os.path.exists(os.path.join(folder, rel)):
            return rel, why
    for panel in decl.get("panels") or []:
        f = panel.get("file", "")
        if f and not f.startswith("..") and os.path.exists(os.path.join(folder, f)):
            return f, "First panel of the folder's own declaration."
    best, best_size = None, -1
    for n in sorted(os.listdir(folder)):
        if n.startswith("_capability_card"):
            continue
        p = os.path.join(folder, n)
        ext = os.path.splitext(n)[1].lower()
        if os.path.isfile(p) and any(ext in MEDIA[k] for k in ("image", "video", "audio", "mesh")):
            s = os.path.getsize(p)
            if s > best_size:
                best, best_size = n, s
    if best:
        return best, "Largest media file - no curated pick and no usable declared panel."
    return None, "No sample rendered. This folder is a plan, not a result."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="show", action="store_true",
                    help="summary to stdout, do not write capabilities.json")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    if not os.path.isdir(ARCHIVE):
        sys.exit(f"archive not found: {ARCHIVE}")

    consumers = scan_consumers()
    have_wf = {f for f in os.listdir(WORKFLOWS) if f.endswith(".json")} \
        if os.path.isdir(WORKFLOWS) else set()

    caps, other = [], []
    for name in sorted(os.listdir(ARCHIVE)):
        folder = os.path.join(ARCHIVE, name)
        if not os.path.isdir(folder):
            continue
        decl_path = os.path.join(folder, "CAPABILITY.json")
        decl = {}
        if os.path.exists(decl_path):
            try:
                decl = json.load(open(decl_path, encoding="utf-8"))
            except (OSError, ValueError):
                decl = {}
        elif name in UNDECLARED:
            decl = dict(UNDECLARED[name])
        else:
            m = walk(folder)
            other.append({"folder": name, "files": m["files"], "size_h": m["size_h"],
                          "newest": m["newest"], "media": m["media"]})
            continue

        measured = walk(folder)
        wfs = workflow_files(decl)
        wf_rows, app, script = [], False, False
        for wf in wfs:
            users = consumers.get(wf, [])
            in_app = [u for u in users if u in APP_PATH]
            in_scr = [u for u in users if u in SCRIPT_PATH or u.startswith(TOOLS_DIR)]
            app = app or bool(in_app)
            script = script or bool(in_scr)
            wf_rows.append({
                "file": wf,
                "exists": wf in have_wf,
                "path": f"workflows/{wf}" if wf in have_wf else None,
                "used_by": sorted(users),
            })

        equiv = []
        for wf, note in APP_EQUIV.get(name, []):
            users = consumers.get(wf, [])
            in_app = [u for u in users if u in APP_PATH]
            app = app or bool(in_app)
            script = script or bool([u for u in users
                                     if u in SCRIPT_PATH or u.startswith(TOOLS_DIR)])
            equiv.append({"file": wf, "exists": wf in have_wf,
                          "used_by": sorted(users), "note": note})

        page = APP_PAGE.get(name)
        if page and page[1] == "app":
            app = True

        exposure = "app" if app else ("script-only" if script else "none")
        if exposure == "none" and page and page[1] == "adjacent":
            exposure = "adjacent"
        sample, why = pick_sample(folder, name, decl)

        caps.append({
            "id": name,
            "number": name.split("-")[0],
            "name": decl.get("title") or name,
            "what_it_does": decl.get("claim"),
            "why_it_matters": decl.get("look_at"),
            "status": decl.get("status", "undeclared"),
            "verdict": decl.get("verdict"),
            "model": decl.get("model"),
            "released": decl.get("released"),
            "vram": decl.get("vram"),
            "cost": decl.get("cost"),
            "workflow_declared": decl.get("workflow"),
            "workflows": wf_rows,
            "app_equivalent": equiv,
            "app_page": {"page": page[0], "tier": page[1], "note": page[2]} if page else None,
            "has_runnable_workflow": any(r["exists"] for r in wf_rows)
                                     or any(r["exists"] for r in equiv),
            "exposed_in_app": exposure == "app",
            "exposure": exposure,
            "declaration_stale": STALE.get(name),
            "sample": {"file": sample,
                       "path": f"{name}/{sample}" if sample else None,
                       "why": why},
            "card": "_capability_card.png" if os.path.exists(
                os.path.join(folder, "_capability_card.png")) else None,
            "measured": measured,
            "strong": decl.get("strong", []),
            "weak": decl.get("weak", []),
            "limits": decl.get("limits", []),
            "alternatives": decl.get("alternatives", []),
            "next_steps": decl.get("next_steps", []),
        })

    claimed = {r["file"] for c in caps for r in c["workflows"]} | \
              {r["file"] for c in caps for r in c["app_equivalent"]}
    orphan_wf = []
    for f in sorted(have_wf - claimed):
        users = consumers.get(f, [])
        orphan_wf.append({
            "file": f,
            "used_by": sorted(users),
            "tier": "app" if any(u in APP_PATH for u in users)
                    else ("script" if users else "unused"),
            "exists": True,
            "note": ORPHAN_NOTES.get(f),
        })

    doc = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "generator": "studio/_tools/capability_scan.py",
        "archive": ARCHIVE,
        "note": "Read-only catalogue of the capability archive. Representative samples were "
                "chosen by looking at the pixels and at frame strips pulled from the clips, "
                "not by taking the first file. Audio picks are flagged NOT AUDITIONED.",
        "totals": {
            "archive_folders": len(caps) + len(other),
            "capabilities": len(caps),
            "production_folders": len(other),
            "with_runnable_workflow": sum(1 for c in caps if c["has_runnable_workflow"]),
            "exposed_in_app": sum(1 for c in caps if c["exposure"] == "app"),
            "script_only": sum(1 for c in caps if c["exposure"] == "script-only"),
            "adjacent": sum(1 for c in caps if c["exposure"] == "adjacent"),
            "not_exposed": sum(1 for c in caps if c["exposure"] == "none"),
            "rendered": sum(1 for c in caps if c["sample"]["file"]),
            "planned_only": sum(1 for c in caps if not c["sample"]["file"]),
            "declarations_stale": sum(1 for c in caps if c["declaration_stale"]),
        },
        # The honest answer to "what can this box do that the app never shows you".
        "not_exposed_in_app": [
            {"id": c["id"], "name": c["name"], "exposure": c["exposure"],
             "status": c["status"], "verdict": c["verdict"],
             "workflow": next((r["file"] for r in c["workflows"] if r["exists"]), None),
             "sample": c["sample"]["path"]}
            for c in caps if c["exposure"] != "app"
        ],
        # Verified, rendered, runnable today - and invisible. The shortlist worth building.
        "ready_and_invisible": [
            c["id"] for c in caps
            if c["exposure"] == "none" and c["status"] == "verified"
            and c["has_runnable_workflow"] and c["sample"]["file"]
        ],
        "app_render_path": APP_PATH,
        "capabilities": caps,
        "workflows_with_no_capability_folder": orphan_wf,
        "production_folders": sorted(other, key=lambda r: -r["files"]),
    }

    if args.show:
        t = doc["totals"]
        print(f"{t['capabilities']} capabilities, {t['production_folders']} production folders")
        print(f"exposed in app {t['exposed_in_app']} | script-only {t['script_only']} "
              f"| not exposed {t['not_exposed']}")
        print(f"rendered {t['rendered']} | planned only {t['planned_only']}\n")
        for c in caps:
            mark = {"app": "APP ", "script-only": "scr ",
                    "adjacent": "adj ", "none": "  - "}[c["exposure"]]
            wf = ",".join(r["file"] for r in c["workflows"] if r["exists"]) or "-"
            print(f"{mark}{c['id']:<28} {c['measured']['files']:>5}f "
                  f"{c['measured']['size_h']:>9}  {wf}")
        if orphan_wf:
            print("\nworkflows with no capability folder:")
            for w in orphan_wf:
                print(f"  [{w['tier']:<6}] {w['file']}")
        stale = [c for c in caps if c["declaration_stale"]]
        if stale:
            print(f"\n{len(stale)} declarations are out of date:")
            for c in stale:
                print(f"  {c['id']}")
        return

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    t = doc["totals"]
    print(f"wrote {args.out}")
    print(f"  {t['capabilities']} capabilities, {t['production_folders']} production folders")
    print(f"  exposed in app {t['exposed_in_app']} | script-only {t['script_only']} "
          f"| not exposed {t['not_exposed']}")


if __name__ == "__main__":
    main()
