#!/usr/bin/env python3
"""Publish the capability archive's chosen samples into the studio tree.

studio/capabilities.json is a read-only catalogue of ~/ComfyUI/output/claude-generated,
which is NOT in git and gets cleaned. Every sample path in it points there, so a page
built straight off that catalogue shows empty boxes the first time the output tree is
tidied. This tool copies the chosen samples in, re-encoding stills to webp and pulling a
poster frame off each clip, and writes studio/samples/capabilities/index.json - the
teaching layer the page actually renders.

Two things live here that are NOT in the archive catalogue, because the archive is a
catalogue and this is a curriculum:

  CURRICULUM  the group each capability belongs to, its order within that group from
              simplest to most advanced, one plain sentence saying what it does, and why
              you would want it. The archive's own `what_it_does` opens with a model name
              and a VRAM figure, and its `why_it_matters` is an instruction about what to
              look at in the sample - neither is the sentence a newcomer needs first.

  COMPANIONS  a second file per capability that teaches by contrast: the edge map beside
              the ControlNet output, the documented failure beside the success, the
              original beside the remix. Chosen by hand, each with the reason it is there.

NOTHING RUNS AT IMPORT. Seventeen tools in this directory do their entire job when handed
any argument including --help, which is how a previous audit clobbered ten style cards.
This one parses arguments first and touches nothing until main() is called.

  python3 studio/_tools/capability_publish.py            # publish everything
  python3 studio/_tools/capability_publish.py --dry-run   # say what it would do
  python3 studio/_tools/capability_publish.py --only 03-controlnet 21-3d-generation

Idempotent: a sample is re-encoded only when the source is newer than the published file,
unless --force.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))          # studio/_tools
STUDIO = os.path.dirname(HERE)                             # studio
DEFAULT_ARCHIVE = os.path.expanduser(
    os.environ.get("COMFY_ROOT", "~/ComfyUI")) + "/output/claude-generated"
DEFAULT_OUT = os.path.join(STUDIO, "samples", "capabilities")
CATALOGUE = os.path.join(STUDIO, "capabilities.json")

STILL = {".png", ".jpg", ".jpeg", ".webp"}
CLIP = {".mp4", ".webm", ".mov"}
SOUND = {".mp3", ".wav", ".flac", ".ogg"}
TEXT = {".txt", ".md", ".json"}

# ---------------------------------------------------------------------------
# The groups, in the order a newcomer should meet them: make a picture, change a
# picture, control what the model does, make it move, make it sound, the new
# modality, teach the model, get it out the door, then the thing it all adds up to.
GROUPS = [
    ("image", "Image",
     "Make a picture out of nothing but words. Everything else on this page is built on "
     "top of this one."),
    ("editing", "Editing",
     "Change a picture that already exists. The hard part is never the change - it is "
     "leaving the rest of the frame alone."),
    ("control", "Control",
     "Stop rolling dice. Extract a structural signal from something real and make the "
     "model obey it."),
    ("video", "Video",
     "Make it move. Three video models with genuinely different strengths, plus what you "
     "do to a clip after it exists."),
    ("audio", "Audio",
     "Sound is half of a film, and by far the cheapest half here - a full 60-second cue "
     "costs less GPU time than one still."),
    ("3d", "3D",
     "The newest modality on the box and the smallest: both models together are under "
     "10 GB."),
    ("training", "Training",
     "Teach the models something they do not already know - and understand the dial "
     "before you turn it."),
    ("utility", "Utility",
     "The unglamorous stages that decide whether what you generated is deliverable."),
    ("assembly", "Assembly",
     "Every capability above, in one artefact."),
]

# ---------------------------------------------------------------------------
# id -> group, order within the group, one plain sentence, and why you would want it.
# `order` runs simplest to most advanced. Planned capabilities sort to the end of their
# group by convention (order >= 50) so a group reads as a working path first.
CURRICULUM = {
    "01-text-to-image": dict(group="image", order=10,
        one_line="Type a description, get a picture - 1664x928 in four and a half seconds.",
        why="The floor everything else stands on. It is also the only local model that "
            "renders readable text inside the image, so signs, posters, packaging and UI "
            "mockups come out legible instead of as glyph soup."),
    "16-style-range": dict(group="image", order=20,
        one_line="The same subject rendered twelve different ways by changing one clause "
                 "of the prompt - no LoRAs, no extra weights.",
        why="This is the free baseline any style LoRA has to beat, so run it before you "
            "download or train anything. Two of the twelve failed the same way, which is "
            "the most useful thing in the set: a medium that is also a plausible object "
            "gets drawn as the object."),
    "22-flux2": dict(group="image", order=30,
        one_line="A second image model with a different aesthetic, currently the strongest "
                 "open model on photorealism.",
        why="When the first model's picture is competent but flat, this is the other "
            "opinion. Its text encoder is an actual LLM, so it pays off for complete "
            "sentences about physical detail rather than keyword lists."),
    "13-llm-prompt-studio": dict(group="image", order=40,
        one_line="Eight words in; a local LLM writes the full art-directed prompt and the "
                 "image renders in the same graph.",
        why="It automates the part of the job most people are worst at, in six seconds "
            "end to end with no copy-paste and no API key. Each image is saved with the "
            "exact prompt beside it, so a good accident stays reproducible."),
    "33-zimage-turbo": dict(group="image", order=50,
        one_line="A one-second-per-image model, installed and never run.",
        why="At one second you browse ideas instead of committing to them - a 40-image "
            "concept sheet in under a minute. That is a different way of working, not a "
            "speedup, and nothing here has measured whether it holds up."),

    "02-image-editing": dict(group="editing", order=10,
        one_line="Change one thing in a picture you already have, with a plain-English "
                 "instruction.",
        why="Composition, camera angle and the structure of the subject all survive, "
            "which is what makes it an edit rather than a re-roll. You can relight or "
            "re-season a shot whose framing you already like."),
    "20-qwen-edit-2511": dict(group="editing", order=20,
        one_line="Put two separately generated people into one photograph with both faces "
                 "staying themselves.",
        why="A casting tool, not a collage tool - it reconciles the light across both "
            "subjects instead of leaving each with its original key. The previous model "
            "averages two faces into one and takes six times as long at the single-edit job."),
    "24-outpaint-removal": dict(group="editing", order=30,
        one_line="Extend a picture past its own edges, or try to delete something out of it.",
        why="Outpainting works and leaves no seam. Removal is kept here because it failed, "
            "and the pair tells you the rule: removal works on a small object in a scene "
            "with context to borrow from, and not on the subject of a product shot."),
    "15-product-composite": dict(group="editing", order=40,
        one_line="Generate a new scene around a real product without ever regenerating "
                 "the product.",
        why="Every pixel of the object stays byte-identical, which is the whole difference "
            "between usable and unusable when it carries a logo or a serial number. Match "
            "the key light direction in the backdrop prompt - compositing does not relight "
            "the subject, and there is no contact shadow yet."),

    "23-control-maps": dict(group="control", order=10,
        one_line="Extract depth, normals and a full-body pose from any picture in a second "
                 "and a half.",
        why="These are not pictures, they are the signals that let you dictate composition, "
            "staging and camera movement in the NEXT generation. Everything else in this "
            "group starts here, and so does the unbuilt camera control."),
    "12-segmentation-matting": dict(group="control", order=20,
        one_line="Cut a named object out of a picture by typing its name, or matte a "
                 "portrait with no prompt at all.",
        why="No clicking, no box drawing, no mask painting. This is the mask supply for "
            "compositing, removal and inpainting. Always check an alpha channel over "
            "magenta: an inverted matte looks completely normal in any viewer that ignores "
            "alpha, and you will have kept the background and thrown away your subject."),
    "03-controlnet": dict(group="control", order=30,
        one_line="Keep the structure of one image and generate a completely different "
                 "subject inside it.",
        why="This is the difference between a filter and structural control - you keep the "
            "composition you already framed and change material, era and subject. Control "
            "strength decides how literal it is, and on the one sample here it was clearly "
            "set loose."),
    "30-camera-control": dict(group="control", order=50,
        one_line="Drive the video model's camera with a depth pass pulled off a real clip. "
                 "Not built.",
        why="It turns 'slow push in' from a hopeful prompt phrase into an actual trajectory. "
            "Every weight is already installed - this is plumbing, not shopping - and it is "
            "exactly what the studio's own camera library still cannot prove."),

    "06-text-to-video-with-audio": dict(group="video", order=10,
        one_line="Type a description, get a video with a synced soundtrack generated in the "
                 "same pass.",
        why="Nothing else local makes picture and sound together, and it is roughly eight "
            "times faster than the alternative with a cost curve that is almost flat in "
            "clip length. Treat the audio as a reality bed to layer designed sound over - "
            "it does not know what any named object sounds like."),
    "05-image-to-video": dict(group="video", order=20,
        one_line="Animate a still you already like, without the model redrawing it.",
        why="When a keyframe's art direction is already right, this preserves it where the "
            "faster model reinterprets it. It also leads the open models on photoreal "
            "humans, which is why it stays in the kit at eight times the cost."),
    "07-frame-interpolation": dict(group="video", order=30,
        one_line="Invent a new frame between every pair of existing ones - 16 fps becomes 32.",
        why="Seven and a half seconds and a tenth of a gigabyte of VRAM removes the stutter "
            "that gives generated footage away. It is not frame duplication: every inserted "
            "frame is generated content showing the subject part-way between its neighbours."),
    "14-ltx-two-stage-upscale": dict(group="video", order=40,
        one_line="Run the video model the way it was designed: sample at half resolution, "
                 "upscale the latent, then re-denoise from part-way.",
        why="Four and a half extra seconds buys a refine pass at 1280x704 with stereo audio "
            "in the same generation. Clear on detailed subjects and not on soft foggy "
            "material, which is worth knowing before you spend it."),
    "18-audio-to-video": dict(group="video", order=45,
        one_line="Feed in a still portrait and a narration track; out comes video whose "
                 "mouth matches the audio.",
        why="Mind the direction - everything else here generates audio, this one is DRIVEN "
            "by audio you already have. It is the only local route to lip-synced dialogue "
            "coverage, and the mechanism is one float: the audio latent is pinned so the "
            "model can only satisfy its objective by moving the face."),
    "34-flf2v-transitions": dict(group="video", order=50,
        one_line="Give the model a first frame AND a last frame and it generates the motion "
                 "between them. Not built.",
        why="The missing tool for deliberate transitions and cutting on action, and it needs "
            "zero downloads. Chain several and you have a long take."),
    "28-vace-video-editing": dict(group="video", order=51,
        one_line="Restyle, inpaint or extend footage that already exists. Not built.",
        why="The only real answer on this box to shot-to-shot look matching, which the "
            "film-craft audit names as a structural gap. Expect it to be slow at 53.8 GB "
            "with heavy offload, and measure that honestly before building on it."),
    "29-hunyuanvideo": dict(group="video", order=52,
        one_line="A third video model specialising in believable motion - cloth, smoke, "
                 "fluid, object interactions. Not built.",
        why="Complementary rather than competing: one model owns audio and speed, one owns "
            "photoreal humans, this one owns physics. All seven files are installed, "
            "including the encoder without which the 46.5 GB of weights are dead."),
    "31-character-identity": dict(group="video", order=53,
        one_line="Lock one character's face across every shot using an identity LoRA. "
                 "Not built.",
        why="Identity drift is the single thing separating an AI short from a real one - an "
            "audience forgives soft motion, not a face that is 90% the same. Be clear-eyed: "
            "this LoRA was trained on talking video, so it is identity lock for dialogue "
            "coverage, not for arbitrary wide shots. The app already attacks the same "
            "problem from the other side, with trained character LoRAs on the cast page."),

    "09-sound-effects": dict(group="audio", order=10,
        one_line="Render a named sound or an ambience bed - a sword clash, wind through "
                 "dry grass.",
        why="Name the sound, not the scene: 'wind through dry grass, distant surf, "
            "occasional gust' beats 'a lonely coastal morning' every time. This is the "
            "designed layer you put over the video model's built-in audio."),
    "08-music": dict(group="audio", order=20,
        one_line="Sixty seconds of scored music from genre, instrument, mood and tempo tags.",
        why="A full cue in well under ten seconds means you score a scene to picture instead "
            "of hunting a library for something that nearly fits. Prompt with tags, not "
            "prose, and leave the lyrics empty for an instrumental."),
    "10-voice": dict(group="audio", order=30,
        one_line="Narration and character dialogue generated on the box - no API, no key.",
        why="Dialogue is what turns a sequence of clips into a scene. The archive card is "
            "out of date here in a way that matters: it describes one voice pack "
            "pitch-shifted per character, but seventeen named voices from a newer engine "
            "now sit in that folder and the renderer already routes to them."),
    "25-music-remix": dict(group="audio", order=40,
        one_line="Feed music in and get the same music back in a different instrumentation.",
        why="This is what makes scoring a film practical. Generate a theme once, remix it "
            "lightly per act, and the variations are recognisably the same theme - which "
            "three separately generated cues never are."),
    "19-llm-lyrics-song": dict(group="audio", order=50,
        one_line="One line of intent becomes structured lyrics and then a sung, scored song.",
        why="Twelve seconds from a sentence to sixty seconds of music with vocals. The "
            "verse and chorus tags are load-bearing rather than decorative - the composer "
            "arranges to them, and without them you get a shapeless wash with no lift."),

    "21-3d-generation": dict(group="3d", order=10,
        one_line="One flat picture in; a real polygon mesh and a Gaussian splat out, about "
                 "twenty seconds each.",
        why="The cheapest new modality on the box. It is geometry only - no UVs, no texture "
            "- and the side the model never saw is invented, so it is excellent for renders "
            "and turntables and not a game asset without Blender work."),

    "17-lora-mechanics": dict(group="training", order=10,
        one_line="The same prompt and seed across a ladder of LoRA strengths, so you can "
                 "see what the number actually does.",
        why="Read this before you train anything or reach for a bigger strength value. "
            "Above about 1.1 a LoRA is not adding more style, it is fighting the base "
            "model: crushed sky, oversharpened edges, streaky rain. The studio's LoRA page "
            "applies the same lesson across 22 LoRAs."),
    "27-lora-training": dict(group="training", order=20,
        one_line="Train your own LoRA inside ComfyUI itself - no Kohya, no second Python "
                 "environment.",
        why="The only technique that gives you BOTH a consistent character and a range of "
            "performance. The archive card calls this the largest untouched capability "
            "here and is now simply wrong: the workflow exists, the tools exist, 22 LoRAs "
            "sit in the library and the reference character carries a trained one."),

    "04-upscaling": dict(group="utility", order=10,
        one_line="Four times the pixels in four and a half seconds, on two gigabytes of VRAM.",
        why="The image models start duplicating composition past about 2 MP, so you never "
            "chase resolution in the sampler - you generate at 1-2 MP and upscale after. "
            "That is the whole delivery workflow. Judge any upscaler on a 1:1 crop; a "
            "fit-to-screen view of 24.7 megapixels proves nothing."),
    "26-vision-caption": dict(group="utility", order=20,
        one_line="A vision model looks at a picture and writes the prompt that would "
                 "recreate it.",
        why="The pipeline run backwards: reverse-engineer a look from a reference, QA your "
            "own renders at scale, or caption a LoRA training set - the most tedious part "
            "of training, automated. It reads brightness more reliably than quality of "
            "light, so check what it claims about the lighting before you trust it."),
    "32-seedvr2-upscale": dict(group="utility", order=50,
        one_line="A diffusion upscaler that invents plausible detail rather than sharpening "
                 "what is there. Not built.",
        why="On faces and text - exactly where the GAN upscaler is weakest - that difference "
            "is decisive. The demo writes itself: a 1:1 crop A/B against the existing "
            "upscaler on the same source region."),

    "11-short-film": dict(group="assembly", order=10,
        one_line="Ten finished shorts - keyframes, clips, dialogue, score, ambience, burnt-in "
                 "captions and a cut - assembled from one JSON spec.",
        why="This is what all of it is for. Fifty-six seconds and thirteen shots for about "
            "six minutes of GPU time. Every capability above is a component of this one."),
}

# ---------------------------------------------------------------------------
# The second panel. Each of these was picked because the capability is not legible from
# one file: a ControlNet output means nothing without its control map, and a removal
# failure is the whole lesson of the folder it sits in.
COMPANIONS = {
    "02-image-editing": [
        ("object_removal_00001_.png",
         "The same picture with the lighthouse removed entirely - bare stack, intact sky. "
         "This is the direct counterexample to the removal failure in Outpainting & object "
         "removal: it works here because the scene has context to borrow from."),
    ],
    "03-controlnet": [
        ("qwen_controlnet_edgemap_00001_.png",
         "THE CONTROL INPUT - an edge map extracted from a lighthouse photograph. Put it "
         "beside the output and judge for yourself: the archive claims they match to the "
         "pixel, and they do not. Composition rhymes, structure does not."),
    ],
    "12-segmentation-matting": [
        ("birefnet_proof_on_magenta_00001_.png",
         "The other model, with no prompt at all - BiRefNet mattes a portrait "
         "automatically. Same magenta proof, because that is the only way to see an alpha "
         "channel is the right way round."),
    ],
    "13-llm-prompt-studio": [
        ("idea_00003_.png",
         "The instructive failure: the astronaut is eating noodles through a sealed visor. "
         "Neither the LLM nor the image model reasons about physical plausibility, so an "
         "automated prompt still needs a human reading it."),
    ],
    "16-style-range": [
        ("style_09_stained-glass_00001_.png",
         "The documented failure - a photoreal heron IN FRONT OF a stained glass window "
         "instead of rendered AS stained glass. Any medium that is also a plausible object "
         "in a scene can be misread this way."),
        ("style_11_bronze-sculpture_00001_.png",
         "A second failure the archive does not declare, found by looking: a desaturated "
         "photograph of a live heron, not a bronze. Same trap, which strengthens rather "
         "than weakens the folder's own lesson."),
    ],
    "17-lora-mechanics": [
        ("strength_01_0-0_00001_.png",
         "Strength 0.0 - the same seed with the accelerator LoRA off. Soft, grainy and "
         "flat, because four steps without it is not enough. A LoRA is a delta on the base "
         "model, so this control is what the value is measured against."),
        ("strength_05_1-3_00001_.png",
         "Strength 1.3. This is not more style, it is damage: crushed sky, oversharpened "
         "edges, streaky rain. Above roughly 1.1 the LoRA fights the base model."),
    ],
    "21-3d-generation": [
        ("source_owl_00001_.png",
         "The single flat image both the mesh and the splat were built from. The model "
         "never saw the back of this owl and had to invent it."),
    ],
    "23-control-maps": [
        ("depth_colored_00001_.png",
         "Depth on the same frame, for contrast with the normals. Depth flattens the jacket "
         "into one distance; normals hold the fabric folds, the hull curve and the "
         "individual pots on the shelves. That is why you want both."),
    ],
    "24-outpaint-removal": [
        ("removed_object_v2_00001_.png",
         "The failure, kept on purpose. Asked to remove the watch, it produced a stone ring "
         "where the watch had been - a rope ring on the first attempt. The mask was "
         "verified correct and both prompt conventions were tried."),
    ],
    "25-music-remix": [
        ("source_original.mp3",
         "The source track. Play it, then the remix: same length, same bones, different "
         "instrument. NOT AUDITIONED - neither file has been listened to."),
    ],
}

# A text sidecar worth reading next to the sample. Inlined into index.json rather than
# copied, so the page needs no new MIME type and no second fetch.
TEXT_COMPANIONS = {
    "26-vision-caption": ("caption.txt",
        "What the vision model wrote when shown the image. It recovered the weathered "
        "hands, the honeycomb, the shallow depth of field and the warm palette - then "
        "called the light 'a bright, sunny day' when the image is deliberately flat "
        "overcast."),
}


# ---------------------------------------------------------------------------
def kind_of(path):
    e = os.path.splitext(path)[1].lower()
    if e in STILL:
        return "image"
    if e in CLIP:
        return "video"
    if e in SOUND:
        return "audio"
    if e in TEXT:
        return "text"
    return "file"


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def newer(src, dst):
    return not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst)


def publish_still(src, dst_base, force, log):
    """PNG in, webp out. The archive stills are 1-3 MB each and there are 40 of them;
    webp at q90 is roughly 8x smaller with no visible loss at the sizes this page shows.
    Nothing is resized - the upscaling capability's whole point is a 1:1 crop, and
    resampling it would destroy the only honest file in that folder."""
    dst = dst_base + ".webp"
    if force or newer(src, dst):
        rc, out = run(["magick", src, "-quality", "90", dst])
        if rc != 0:
            log.append("magick failed on %s: %s" % (src, out.strip()[:200]))
            # A copy of the original beats no sample at all.
            dst = dst_base + os.path.splitext(src)[1].lower()
            shutil.copy2(src, dst)
    return dst


def publish_clip(src, dst_base, force, log):
    """Copied, not transcoded - these are already small h264 and re-encoding would only
    lose quality. A poster frame is pulled at 1 s so the grid shows pictures instead of
    black rectangles before anything is played."""
    dst = dst_base + os.path.splitext(src)[1].lower()
    if force or newer(src, dst):
        shutil.copy2(src, dst)
    poster = dst_base + "_poster.webp"
    if force or newer(src, poster):
        rc, out = run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", src,
                       "-frames:v", "1", "-vf", "scale=640:-2", poster])
        if rc != 0 or not os.path.exists(poster):
            # Clips shorter than the seek point give an empty output; retry from frame 0.
            rc, out = run(["ffmpeg", "-y", "-v", "error", "-i", src,
                           "-frames:v", "1", "-vf", "scale=640:-2", poster])
        if rc != 0 or not os.path.exists(poster):
            log.append("no poster for %s: %s" % (os.path.basename(src), out.strip()[:160]))
            poster = None
    return dst, poster


def probe_duration(src):
    rc, out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", src])
    try:
        return round(float(out.strip()), 1) if rc == 0 else None
    except ValueError:
        return None


def publish_one(src, out_dir, stem, force, log):
    """Publish one archive file. Returns the record the page renders, or None."""
    if not os.path.isfile(src):
        log.append("MISSING in archive: %s" % src)
        return None
    k = kind_of(src)
    base = os.path.join(out_dir, stem)
    rec = {"kind": k, "source": src, "bytes_source": os.path.getsize(src)}
    if k == "image":
        dst = publish_still(src, base, force, log)
    elif k == "video":
        dst, poster = publish_clip(src, base, force, log)
        rec["duration"] = probe_duration(src)
        if poster:
            rec["poster_file"] = os.path.basename(poster)
    elif k == "audio":
        dst = base + os.path.splitext(src)[1].lower()
        if force or newer(src, dst):
            shutil.copy2(src, dst)
        rec["duration"] = probe_duration(src)
    else:
        dst = base + os.path.splitext(src)[1].lower()
        if force or newer(src, dst):
            shutil.copy2(src, dst)
    rec["file"] = os.path.basename(dst)
    rec["bytes"] = os.path.getsize(dst)
    return rec


def main():
    ap = argparse.ArgumentParser(
        description="Copy the capability archive's chosen samples into "
                    "studio/samples/capabilities/ and write the curriculum index.")
    ap.add_argument("--archive", default=DEFAULT_ARCHIVE,
                    help="ComfyUI capability archive root (default: %(default)s)")
    ap.add_argument("--catalogue", default=CATALOGUE,
                    help="studio/capabilities.json, written by capability_scan.py")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output directory")
    ap.add_argument("--only", nargs="*", default=None,
                    help="publish only these capability ids")
    ap.add_argument("--force", action="store_true",
                    help="re-encode even when the published file is up to date")
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would be published and write nothing")
    a = ap.parse_args()

    if not os.path.exists(a.catalogue):
        print("no catalogue at %s - run studio/_tools/capability_scan.py first" % a.catalogue)
        return 2
    with open(a.catalogue, encoding="utf-8") as f:
        cat = json.load(f)
    caps = cat.get("capabilities", [])
    if not caps:
        print("catalogue holds no capabilities")
        return 2

    # Every capability must be taught or the page silently drops it.
    unplaced = [c["id"] for c in caps if c["id"] not in CURRICULUM]
    if unplaced:
        print("NOT IN CURRICULUM (they will not appear on the page): %s" % ", ".join(unplaced))
    orphan = [k for k in CURRICULUM if k not in {c["id"] for c in caps}]
    if orphan:
        print("CURRICULUM entries with no capability in the catalogue: %s" % ", ".join(orphan))

    log, entries = [], {}
    published = missing = 0
    for c in caps:
        cid = c["id"]
        if a.only and cid not in a.only:
            continue
        cur = CURRICULUM.get(cid)
        if not cur:
            continue
        e = dict(cur)
        e["id"] = cid
        out_dir = os.path.join(a.out, cid)
        if a.dry_run:
            print("%-28s %-9s order %-3s" % (cid, cur["group"], cur["order"]))
        else:
            os.makedirs(out_dir, exist_ok=True)

        # the representative sample the archive survey chose by looking
        s = c.get("sample") or {}
        if s.get("path"):
            src = os.path.join(a.archive, s["path"])
            if a.dry_run:
                print("    sample     %s%s" % (s["path"], "" if os.path.isfile(src) else "  MISSING"))
            else:
                rec = publish_one(src, out_dir, "sample", a.force, log)
                if rec:
                    rec["why"] = s.get("why", "")
                    rec["url"] = "/samples/capabilities/%s/%s" % (cid, rec["file"])
                    if rec.pop("poster_file", None):
                        rec["poster"] = "/samples/capabilities/%s/sample_poster.webp" % cid
                    e["sample"] = rec
                    published += 1
                else:
                    missing += 1
        elif c.get("verdict") == "planned":
            e["no_sample"] = ("Nothing has been rendered for this. The folder holds a "
                              "capability card and a plan, and that is the honest state.")

        # the companion panel, chosen by hand to teach by contrast
        comps = []
        for i, (fn, cap) in enumerate(COMPANIONS.get(cid, [])):
            src = os.path.join(a.archive, cid, fn)
            if a.dry_run:
                print("    companion  %s%s" % (fn, "" if os.path.isfile(src) else "  MISSING"))
                continue
            rec = publish_one(src, out_dir, "companion%d" % (i + 1), a.force, log)
            if rec:
                rec["caption"] = cap
                rec["url"] = "/samples/capabilities/%s/%s" % (cid, rec["file"])
                if rec.pop("poster_file", None):
                    rec["poster"] = ("/samples/capabilities/%s/companion%d_poster.webp"
                                     % (cid, i + 1))
                comps.append(rec)
                published += 1
            else:
                missing += 1
        if comps:
            e["companions"] = comps

        # a text sidecar, inlined
        tc = TEXT_COMPANIONS.get(cid)
        if tc:
            src = os.path.join(a.archive, cid, tc[0])
            if os.path.isfile(src):
                with open(src, encoding="utf-8", errors="replace") as f:
                    e["text_companion"] = {"file": tc[0], "caption": tc[1],
                                           "text": f.read().strip()}
            else:
                log.append("MISSING text companion: %s" % src)
        entries[cid] = e

    if a.dry_run:
        print("\ndry run - nothing written. %d capabilities in the curriculum." % len(entries))
        return 0

    idx = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "generator": "studio/_tools/capability_publish.py",
        "archive": a.archive,
        "note": ("The teaching layer over studio/capabilities.json. Group, order, the plain "
                 "sentence and the reason to want it are authored here; every fact about "
                 "models, cost, workflows and exposure comes from the catalogue. Samples "
                 "are copies, so this page does not depend on ComfyUI's output tree."),
        "groups": [{"id": g, "name": n, "blurb": b} for g, n, b in GROUPS],
        "entries": entries,
        "published_files": published,
        "missing_files": missing,
        "log": log,
    }
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=1, ensure_ascii=False)

    total = 0
    for root, _dirs, files in os.walk(a.out):
        for fn in files:
            total += os.path.getsize(os.path.join(root, fn))
    print("published %d files for %d capabilities into %s (%.1f MB)"
          % (published, len(entries), a.out, total / 1e6))
    if missing:
        print("%d chosen files were MISSING from the archive" % missing)
    for line in log:
        print("  ! " + line)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
