#!/usr/bin/env bash
# The showreel: the night's strongest moments over an ACE-Step score.
#
# LTX will not write music - asked for an orchestra it produces wind - so the bed comes
# from the right tool. ACE-Step also fades out if asked for too long: 95s trailed to
# silence after about 45, while 46s holds level all the way through, so the reel is cut to
# the music rather than the music stretched to the reel.
#
# Each clip keeps its own location sound underneath the score, quiet, so the wok still
# roars and the blade still rings.
set -e
L=~/shared/LTX-FILM
W=1472; H=832
SCORE=$(ls -t ~/ComfyUI/output/claude-generated/reel/score45*.mp3 | head -1)
cd /tmp
rm -f reel.txt

# file  start  seconds
CLIPS="
hero_atlas:0.4:3.0
hk_signal:5.0:3.0
tx_fire:0.2:3.0
atlas_a:5.2:3.0
s3_duel:7.5:3.0
ct3:1.0:3.0
hk_library:6.0:3.0
lr4:5.5:3.0
lib_pace:3.0:3.0
tx_ice:4.0:3.0
hk_lowtide:9.0:3.0
lib_creatine:2.0:3.0
lr6:10.0:3.0
hero_anime:4.0:3.0
lib_atlas:10.5:3.0
"

i=0
for c in $CLIPS; do
  f=${c%%:*}; rest=${c#*:}; ss=${rest%%:*}; d=${rest#*:}
  src="$L/$f.mp4"
  [ -f "$src" ] || { echo "missing $src"; continue; }
  out="/tmp/reelseg_$(printf %02d $i).mp4"
  ffmpeg -y -v error -ss "$ss" -t "$d" -i "$src" \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24" \
    -af "volume=0.22,afade=t=in:st=0:d=0.12,afade=t=out:st=$(echo "$d-0.12"|bc):d=0.12" \
    -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -ac 2 "$out"
  echo "file '$out'" >> reel.txt
  i=$((i+1))
done
echo "segments: $i"

ffmpeg -y -v error -f concat -safe 0 -i reel.txt -c copy /tmp/reel_cut.mp4
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/reel_cut.mp4)
echo "cut length: $DUR"

# score on top, location sound underneath, everything fading out together at the end
ffmpeg -y -v error -i /tmp/reel_cut.mp4 -i "$SCORE" -filter_complex \
 "[1:a]atrim=0:${DUR},asetpts=N/SR/TB,volume=1.0[m];\
  [0:a][m]amix=inputs=2:duration=first:normalize=0[mx];\
  [mx]afade=t=out:st=$(echo "$DUR-2.2"|bc):d=2.2,alimiter=limit=0.95[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 "$L/SHOWREEL.mp4"

ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,width,height -of csv=p=0 "$L/SHOWREEL.mp4"
