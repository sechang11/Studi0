#!/usr/bin/env python3
"""Write studio/domains/*.json - the descriptors that drive every non-film wizard.

WHY A DESCRIPTOR AND NOT FIVE WIZARDS

Voice, music, sfx, image and mesh all want the same shape: pick from a library, see what
each option produces, generate, and keep the recipe. Only three things differ - which
ComfyUI workflow runs, which node inputs the fields map to, and what comes out the far
end. So those three things are DATA and there is one runner and one page.

Adding a sixth domain is then a JSON file, not a feature.

Every `node` path below was read out of the workflow JSON on the box, not guessed. An
earlier patch in this project sprayed settings at four candidate node ids and would have
set none of them; the fix was to go and look. Same discipline here.
"""
import json, os

import argparse
argparse.ArgumentParser(description='make domains').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "domains")

DOMAINS = [
{
  "id": "voice",
  "name": "Voice",
  "icon": "🎙",
  "desc": "Speak a line in a chosen voice. The one place a character's emotion reaches "
          "the performance rather than just the face.",
  "output": "audio",
  "workflow": "17_higgs_v3_voice.json",
  "alt_workflow": {"engine": "indextts2", "workflow": "16_indextts2_voice.json"},
  "cost": "~3s per line",
  "nodes": {
    "text":     "30.inputs.text",
    "voice":    "30.inputs.narrator_voice",
    "seed":     "30.inputs.seed",
    "prefix":   "40.inputs.filename_prefix"
  },
  "fields": [
    {"key": "text", "label": "The line", "type": "textarea", "required": True,
     "default": "Nine years. Nine years we have come here and gone home quiet.",
     "hint": "Punctuation drives delivery more than any setting here. A full stop is a "
             "beat; a comma is not."},
    {"key": "voice", "label": "Voice", "type": "library", "library": "voices",
     "value_field": "file",
     "hint": "Cast by pointing at a distinct reference voice, never by pitch-shifting one "
             "pack - past about ±10% rubberband wrecks formants, which is why five "
             "characters once sounded like one actor on a varispeed tape."},
    {"key": "emotion", "label": "Emotion", "type": "library", "library": "emotions",
     "optional": True,
     "hint": "Only the indextts2 engine accepts an emotion vector. On higgs_v3 this is "
             "recorded but does nothing - the engine selector below decides."},
    {"key": "engine", "label": "Engine", "type": "enum",
     "values": ["higgs_v3", "indextts2"], "default": "higgs_v3",
     "hint": "higgs_v3 is the house engine. indextts2 is the only one with the 8-dimension "
             "emotion vector (Happy/Angry/Sad/Surprised/Afraid/Disgusted/Calm/Melancholic)."}
  ],
  "emotion_nodes": {"prefix": "20.inputs.",
                    "dims": ["Happy", "Angry", "Sad", "Surprised", "Afraid",
                             "Disgusted", "Calm", "Melancholic"]},
  "post": "normalise to -18 LUFS / -3 dBTP with a compressor first; raw output varies by "
          "about 4 LU between packs",
  "note": "Four packs are clones of real people and are marked blocked in the library. "
          "Do not cast them."
},
{
  "id": "music",
  "name": "Music",
  "icon": "🎵",
  "desc": "Generate a score cue. Fast enough to try five and keep one.",
  "output": "audio",
  "workflow": "06_acestep_music.json",
  "cost": "~7.6s per 60s of audio",
  "nodes": {
    "tags":    "10.inputs.tags",
    "lyrics":  "10.inputs.lyrics",
    "bpm":     "10.inputs.bpm",
    "key":     "10.inputs.keyscale",
    "duration":"10.inputs.duration",
    "seconds": "11.inputs.seconds",
    "seed":    "10.inputs.seed",
    "seed2":   "12.inputs.seed",
    "steps":   "12.inputs.steps",
    "cfg":     "12.inputs.cfg",
    "prefix":  "14.inputs.filename_prefix"
  },
  "defaults": {"steps": 20, "cfg": 1.0},
  "fields": [
    {"key": "cue", "label": "Start from a cue", "type": "library", "library": "cues",
     "optional": True, "spreads": {"tags": "tags", "bpm": "bpm", "key": "key"},
     "hint": "Picking one fills the three fields below; change any of them afterwards."},
    {"key": "tags", "label": "Instrumentation and mood", "type": "textarea", "required": True,
     "default": "sparse melancholy piano, single sustained cello, restrained, instrumental",
     "hint": "Name instruments and playing style, not feelings. Always end 'instrumental' "
             "unless you want singing."},
    {"key": "bpm", "label": "BPM", "type": "number", "default": 90,
     "hint": "0 means unmetered - do not try to cut to it."},
    {"key": "key", "label": "Key", "type": "text", "default": "D minor"},
    {"key": "seconds", "label": "Seconds", "type": "number", "default": 30,
     "hint": "Generate LONGER than the picture needs and trim in. ACE-Step has no "
             "hit-point conditioning and cannot spot to a cut."}
  ],
  "note": "cfg 1.0 is CORRECT here and not a mistake - ACE-Step 1.5 turbo is a distilled "
          "model. A listening test preferred it over the larger v1 3.5B."
},
{
  "id": "sfx",
  "name": "Sound effect",
  "icon": "🔊",
  "desc": "One sound, dry, to sit under picture.",
  "output": "audio",
  "workflow": "10_stableaudio_sfx.json",
  "cost": "1.7-3.0s",
  "nodes": {
    "text":     "3.inputs.text",
    "negative": "4.inputs.text",
    "seconds":  "5.inputs.seconds",
    "seed":     "6.inputs.seed",
    "steps":    "6.inputs.steps",
    "cfg":      "6.inputs.cfg",
    "prefix":   "8.inputs.filename_prefix"
  },
  "defaults": {"steps": 100, "cfg": 7},
  "fields": [
    {"key": "preset", "label": "Start from a preset", "type": "library", "library": "sfx",
     "optional": True, "spreads": {"text": "prompt", "seconds": "seconds",
                                   "negative": "negative"}},
    {"key": "text", "label": "The sound", "type": "textarea", "required": True,
     "default": "a single heavy low thud with a short tail, dry, no reverb",
     "hint": "ONE sound per generation - the model cannot layer. Describe it physically: "
             "what hits what, how hard, how long it rings."},
    {"key": "negative", "label": "Negative", "type": "text",
     "default": "music, speech, tonal, melodic"},
    {"key": "seconds", "label": "Seconds", "type": "number", "default": 3,
     "hint": "Lands about 30ms short of what you ask for."}
  ],
  "post": "normalise to -20 LUFS / -3 dBTP - at cfg 7 the raw output clips",
  "note": "100 steps and cfg 7 are measured settings, not defaults. It was previously run "
          "at 8 steps / cfg 1 / lcm and the results were unusable."
},
{
  "id": "image",
  "name": "Image",
  "icon": "🖼",
  "desc": "A single still, using the same look, lighting, weather and emotion libraries "
          "the films use.",
  "output": "image",
  "workflow": "13_qwen_t2i_styled.json",
  "alt_workflow": {"engine": "anime", "workflow": "22_anime_kf_ipadapter.json"},
  "cost": "~4.5s",
  "nodes": {
    "text":     "10.inputs.text",
    "negative": "11.inputs.text",
    "width":    "12.inputs.width",
    "height":   "12.inputs.height",
    "seed":     "13.inputs.seed",
    "steps":    "13.inputs.steps",
    "cfg":      "13.inputs.cfg",
    "prefix":   "15.inputs.filename_prefix"
  },
  "defaults": {"steps": 20, "cfg": 2.5, "width": 1664, "height": 928},
  "fields": [
    {"key": "subject", "label": "Subject", "type": "textarea", "required": True,
     "default": "a lone figure standing at the edge of an empty stadium",
     "hint": "Name things. A quality like 'dramatic' does roughly nothing; 'floodlights "
             "behind, long shadow across wet grass' does the work."},
    {"key": "look", "label": "Look", "type": "library", "library": "looks", "optional": True,
     "hint": "Applied as a colour grade after generation, so it is exact - the one "
             "reliable way to get the colour you asked for."},
    {"key": "lighting", "label": "Lighting", "type": "library", "library": "lighting",
     "optional": True},
    {"key": "weather", "label": "Weather", "type": "library", "library": "weather",
     "optional": True},
    {"key": "engine", "label": "Engine", "type": "enum", "values": ["qwen", "anime"],
     "default": "qwen",
     "hint": "qwen wants prose and does photoreal or illustrated; anime wants danbooru "
             "tags. Feeding one the other's format returns abstract colour shapes."}
  ],
  "note": "Past about 2 MP this model duplicates composition - two horizons, repeated "
          "subjects. Generate at 1-2 MP and upscale 4x instead."
},
{
  "id": "mesh",
  "name": "3D asset",
  "icon": "🧊",
  "desc": "Turn one image into 3D geometry. Read the limits before planning around it.",
  "output": "mesh",
  "workflow": "24_hunyuan3d_mesh.json",
  "alt_workflow": {"engine": "triposplat", "workflow": "25_triposplat.json"},
  "cost": "~19.5s",
  "nodes": {
    "image":  "2.inputs.image",
    "seed":   "7.inputs.seed",
    "steps":  "7.inputs.steps",
    "cfg":    "7.inputs.cfg",
    "prefix": "10.inputs.filename_prefix"
  },
  "defaults": {"steps": 30, "cfg": 5.0},
  "fields": [
    {"key": "preset", "label": "Start from a preset", "type": "library", "library": "mesh",
     "optional": True, "spreads": {"source_prompt": "source_prompt"}},
    {"key": "source_prompt", "label": "The object", "type": "textarea", "required": True,
     "default": "a single leather football boot, centred, plain grey background, even "
                "lighting, whole object visible",
     "hint": "ONE object, centred, plain background, evenly lit, nothing cropped. A "
             "cinematic shot makes a terrible source - this is a product photo, not a "
             "film frame."},
    {"key": "engine", "label": "Method", "type": "enum",
     "values": ["hunyuan3d", "triposplat"], "default": "hunyuan3d",
     "hint": "hunyuan3d gives a mesh; triposplat gives a gaussian splat plus a 360 "
             "turntable video."}
  ],
  "warning": "GEOMETRY ONLY. Hunyuan3D 2.1 outputs a POSITION attribute and nothing else - "
             "no UVs, no texture, no vertex colour, no normals, about 525k triangles. "
             "TripoSplat outputs a splat with no faces at all. Neither is a game-ready "
             "asset: both need retopology and texturing before they are usable in an "
             "engine. They are good for blockouts, silhouette reference and 3D-print bases.",
  "note": "The image is generated first and fed in, so a mesh is really an image recipe "
          "plus 3D settings."
}
]

os.makedirs(OUT, exist_ok=True)
for d in DOMAINS:
    with open(os.path.join(OUT, d["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
print("wrote %d domain descriptors to %s" % (len(DOMAINS), OUT))
for d in DOMAINS:
    print("  %-7s %-14s %s" % (d["id"], d["output"], d["workflow"]))
