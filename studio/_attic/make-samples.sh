#!/usr/bin/env bash
# make-samples.sh - generate a representative sample in every category folder.
# Safe to re-run: ComfyUI appends a counter, it never overwrites.
set -uo pipefail
cd "$(dirname "$0")/.."
R() { python3 scripts/comfy.py run "$@" 2>/dev/null; }
O=claude-generated

echo "=== 01 text-to-image: style range ==="
R workflows/01_qwen_t2i_turbo.json -s 13.inputs.seed=201 \
  -s 15.inputs.filename_prefix="$O/01-text-to-image/portrait" \
  -s 12.inputs.width=1104 -s 12.inputs.height=1472 \
  -s 10.inputs.text="Environmental portrait of an elderly boatbuilder in a cluttered workshop, weathered hands resting on a half-planked hull, shafts of dusty light from a high window, warm muted palette, 85mm, shallow depth of field, documentary photography"
R workflows/01_qwen_t2i_turbo.json -s 13.inputs.seed=202 \
  -s 15.inputs.filename_prefix="$O/01-text-to-image/product" \
  -s 12.inputs.width=1328 -s 12.inputs.height=1328 \
  -s 10.inputs.text="A brushed titanium mechanical watch on a slab of dark slate, single softbox from the left, deep shadows, water droplets on the crystal, macro product photography, seamless charcoal background, ultra sharp"
R workflows/01_qwen_t2i_turbo.json -s 13.inputs.seed=203 \
  -s 15.inputs.filename_prefix="$O/01-text-to-image/illustration" \
  -s 12.inputs.width=1664 -s 12.inputs.height=928 \
  -s 10.inputs.text="Flat vector illustration of a mountain railway station at dusk, limited palette of teal, ochre and cream, bold geometric shapes, subtle paper grain texture, mid-century travel poster style"
R workflows/02_qwen_t2i_quality.json -s 13.inputs.seed=204 \
  -s 15.inputs.filename_prefix="$O/01-text-to-image/typography" \
  -s 12.inputs.width=1104 -s 12.inputs.height=1472 \
  -s 10.inputs.text="A letterpress concert poster on textured cream stock, large condensed sans type reading \"THE LAST SIGNAL\", below it in smaller type \"LIVE AT THE HARBOUR HALL\" and \"NOVEMBER 14\", two-colour ink in deep teal and burnt orange, visible plate impression, slight registration offset"

echo "=== 02 image-editing: instruction range ==="
cp ~/ComfyUI/output/claude-generated/01-text-to-image/qwen_turbo_00001_.png ~/ComfyUI/input/edit_src.png
R workflows/03_qwen_image_edit.json -s 7.inputs.image=edit_src.png -s 13.inputs.seed=301 \
  -s 15.inputs.filename_prefix="$O/02-image-editing/relight_goldenhour" \
  -s 10.inputs.prompt="Relight the scene as warm golden hour: low sun from the left casting long shadows across the rocks, the sky clear with soft haze, water glinting. Keep the lighthouse architecture, camera angle and composition exactly the same."
R workflows/03_qwen_image_edit.json -s 7.inputs.image=edit_src.png -s 13.inputs.seed=302 \
  -s 15.inputs.filename_prefix="$O/02-image-editing/style_watercolour" \
  -s 10.inputs.prompt="Convert this photograph into a loose watercolour painting with visible brushwork, bleeding pigment edges and white paper showing through. Keep the composition and all elements in the same positions."
R workflows/03_qwen_image_edit.json -s 7.inputs.image=edit_src.png -s 13.inputs.seed=303 \
  -s 15.inputs.filename_prefix="$O/02-image-editing/object_removal" \
  -s 10.inputs.prompt="Remove the lighthouse and its outbuilding entirely, leaving only the bare rock stack with the sea breaking against it. Keep the sky, lighting, waves and camera angle exactly the same."

echo "=== 08 music: genre range ==="
R workflows/06_acestep_music.json -s 10.inputs.seed=401 -s 12.inputs.seed=401 \
  -s 10.inputs.duration=45 -s 11.inputs.seconds=45 -s 10.inputs.bpm=92 -s 10.inputs.keyscale="A minor" \
  -s 14.inputs.filename_prefix="$O/08-music/electronic_pulse" \
  -s 10.inputs.tags="dark synthwave, analogue arpeggiator, deep sub bass, gated reverb drums, tape saturation, driving and hypnotic, night drive, instrumental"
R workflows/06_acestep_music.json -s 10.inputs.seed=402 -s 12.inputs.seed=402 \
  -s 10.inputs.duration=45 -s 11.inputs.seconds=45 -s 10.inputs.bpm=78 -s 10.inputs.keyscale="G major" \
  -s 14.inputs.filename_prefix="$O/08-music/acoustic_folk" \
  -s 10.inputs.tags="intimate acoustic folk, fingerpicked steel string guitar, upright bass, brushed snare, room mics, warm and unhurried, instrumental"
R workflows/06_acestep_music.json -s 10.inputs.seed=403 -s 12.inputs.seed=403 \
  -s 10.inputs.duration=50 -s 11.inputs.seconds=50 -s 10.inputs.bpm=104 -s 10.inputs.keyscale="E minor" \
  -s 14.inputs.filename_prefix="$O/08-music/song_with_vocals" \
  -s 10.inputs.tags="indie rock, female lead vocal, jangly electric guitars, driving bass, live drums, anthemic chorus, 90s alternative" \
  -s 10.inputs.lyrics="[verse]
Thirty years of empty air
Nothing on the wire
[chorus]
And the light still turns
And the light still turns
Over the water tonight"

echo "=== 09 sound-effects: sound design range ==="
R workflows/10_stableaudio_sfx.json -s 6.inputs.seed=501 -s 5.inputs.seconds=20 \
  -s 8.inputs.filename_prefix="$O/09-sound-effects/rain_on_metal" \
  -s 3.inputs.text="Heavy rain drumming on a corrugated metal roof, water running off the edge into a puddle, occasional distant thunder, no music, field recording"
R workflows/10_stableaudio_sfx.json -s 6.inputs.seed=502 -s 5.inputs.seconds=20 \
  -s 8.inputs.filename_prefix="$O/09-sound-effects/machine_room" \
  -s 3.inputs.text="Interior of an old machine room, low humming transformer, rhythmic mechanical relay clicking, faint electrical buzz, concrete room reverb, no music"
R workflows/10_stableaudio_sfx.json -s 6.inputs.seed=503 -s 5.inputs.seconds=20 \
  -s 8.inputs.filename_prefix="$O/09-sound-effects/forest_dawn" \
  -s 3.inputs.text="Dense forest at dawn, layered birdsong, light wind through leaves, distant woodpecker, damp still air, nature field recording, no music"
R workflows/10_stableaudio_sfx.json -s 6.inputs.seed=504 -s 5.inputs.seconds=12 \
  -s 8.inputs.filename_prefix="$O/09-sound-effects/impact_oneshot" \
  -s 3.inputs.text="Single heavy metal door slamming shut in a large empty hall, long reverberant tail decaying to silence, one shot"

echo "=== 10 voice: delivery range ==="
R workflows/08_chatterbox_tts.json -s 1.inputs.seed=601 -s 1.inputs.exaggeration=0.3 -s 1.inputs.cfg_weight=0.3 \
  -s 2.inputs.filename_prefix="$O/10-voice/documentary_flat" \
  -s 1.inputs.text="The station was decommissioned in the winter of nineteen seventy nine. Its logbooks record thirty years of silence, broken only once."
R workflows/08_chatterbox_tts.json -s 1.inputs.seed=602 -s 1.inputs.exaggeration=0.9 -s 1.inputs.cfg_weight=0.6 \
  -s 2.inputs.filename_prefix="$O/10-voice/expressive" \
  -s 1.inputs.text="Wait. Say that again. You're telling me the array picked something up? After all this time?"
R workflows/08_chatterbox_tts.json -s 1.inputs.seed=603 -s 1.inputs.exaggeration=0.5 -s 1.inputs.cfg_weight=0.45 \
  -s 2.inputs.filename_prefix="$O/10-voice/neutral_narration" \
  -s 1.inputs.text="This is a local text to speech sample, generated on the machine with no external service involved."

echo "=== 06 text-to-video with audio: subject range ==="
R workflows/11_ltx23_t2v_audio.json -s 32.inputs.noise_seed=701 \
  -s 43.inputs.filename_prefix="$O/06-text-to-video-with-audio/campfire" \
  -s 10.inputs.text="A campfire burning at night in a forest clearing, sparks lifting into the dark, flames moving over split logs, warm light flickering across surrounding tree trunks. Static camera, shallow depth of field."
R workflows/11_ltx23_t2v_audio.json -s 32.inputs.noise_seed=702 -s 20.inputs.width=1280 -s 20.inputs.height=704 \
  -s 43.inputs.filename_prefix="$O/06-text-to-video-with-audio/train" \
  -s 10.inputs.text="A freight train passing through a rural level crossing at dusk, wagons rolling past the camera, warning bell ringing, dust and grit lifting from the track bed, low sun behind. Locked-off camera."

echo "=== done ==="
