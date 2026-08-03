#!/usr/bin/env bash
# mixdown.sh - mux an audio bed onto a finished cut.
#
#   bash mixdown.sh film.mp4 score.mp3 [sfx.wav ...]
#   bash mixdown.sh --under film.mp4 score.mp3     # keep the film's own audio
#
# First audio file is the bed (looped or trimmed to picture length, faded in/out).
# Any further audio files are layered on top at -6 dB. Writes <film>_scored.mp4.
#
# --under mixes the bed BENEATH the video's existing audio track at low level. Use it
# when the cut already carries dialogue or ambience you want to keep; without it the
# original audio is replaced entirely.
set -euo pipefail

UNDER=0
if [[ "${1:-}" == "--under" ]]; then UNDER=1; shift; fi
VID=$1; shift
[[ $# -ge 1 ]] || { echo "usage: mixdown.sh <video> <bed.mp3> [layer.wav ...]"; exit 1; }

DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$VID")
OUT="${VID%.*}_scored.mp4"
FADE=1.5

args=(-i "$VID")
for a in "$@"; do args+=(-stream_loop -1 -i "$a"); done

filt=""
n=1
for a in "$@"; do
  vol=$([[ $n -eq 1 ]] && echo 1.0 || echo 0.5)
  filt+="[$n:a]atrim=0:$DUR,asetpts=N/SR/TB,volume=$vol[a$n];"
  n=$((n+1))
done
if [[ $# -eq 1 ]]; then
  filt+="[a1]"
else
  for i in $(seq 1 $#); do filt+="[a$i]"; done
  filt+="amix=inputs=$#:duration=first:normalize=0[m];[m]"
fi
filt+="afade=t=in:st=0:d=$FADE,afade=t=out:st=$(echo "$DUR-$FADE" | bc):d=$FADE[bed]"

if [[ $UNDER -eq 1 ]]; then
  # duck the bed well under the existing track so dialogue stays intelligible
  filt+=";[bed]volume=0.34[bedq];[0:a]volume=1.0[orig];"
  filt+="[orig][bedq]amix=inputs=2:duration=first:normalize=0,dynaudnorm=f=300:g=9[aout]"
else
  filt+=";[bed]anull[aout]"
fi

# -t (not -shortest): an xfade/acrossfade chain can leave the audio track a little
# shorter than the video, and -shortest would silently trim the tail off the picture.
ffmpeg -y -v error "${args[@]}" \
  -filter_complex "$filt" \
  -map 0:v -map "[aout]" \
  -c:v copy -c:a aac -b:a 256k -t "$DUR" -movflags +faststart "$OUT"

echo "-> $OUT"
