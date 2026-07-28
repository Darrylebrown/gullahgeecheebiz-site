#!/bin/bash
# Build the first Gullah Geechee Biz faceless commercial
# Each scene: image + text overlay + voiceover segment
# Output: 1080x1920 vertical video

DIR="$HOME/gullahgeecheebiz-site/video-scripts/faceless-commercial-1"
SCENES="$DIR/scenes"
OUT="$DIR/output"
VO="$DIR/voiceover.mp3"
FINAL="$DIR/output/ggb-faceless-commercial-1.mp4"

export PATH="$HOME/homebrew/bin:$PATH"

# Get voiceover duration
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VO")
echo "Voiceover duration: ${VO_DUR}s"

# Scene durations (seconds) - total must match voiceover ~60s
# Scene 1: 0-8s, Scene 2: 8-16s, Scene 3: 16-24s, Scene 4: 24-32s, Scene 5: 32-40s, Scene 6: 40-50s, Scene 7: 50-60s
DURS=(8 8 8 8 8 10 10)
TEXTS=(
  "300 years on this land"
  "Every basket carries a story"
  "Roots that run deep"
  "Our stories. Our voice."
  "GULLAH GEECHEE BIZ"
  "Shop. Read. Belong."
  "gullahgeecheebiz.com"
)

# Build each scene clip
CLIPS=""
for i in $(seq 0 6); do
  NUM=$((i+1))
  IMG="$SCENES/scene${NUM}.png"
  DUR=${DURS[$i]}
  TEXT="${TEXTS[$i]}"
  CLIP="$OUT/clip${NUM}.mp4"

  # Calculate voiceover segment start/end
  START=0
  for j in $(seq 0 $((i-1))); do
    START=$(echo "$START + ${DURS[$j]}" | bc)
  done
  END=$(echo "$START + $DUR" | bc)

  # Extract voiceover segment
  ffmpeg -y -i "$VO" -ss "$START" -t "$DUR" -c copy "$OUT/vo_seg${NUM}.m4a" 2>/dev/null

  # Create video clip: image + text overlay + voiceover
  # Use drawtext for text overlay with navy background bar
  ffmpeg -y -loop 1 -i "$IMG" \
    -i "$OUT/vo_seg${NUM}.m4a" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,drawbox=x=0:y=1700:w=1080:h=180:color=black@0.7:t=fill,drawtext=text='${TEXT}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=1730:fontfile=/System/Library/Fonts/Helvetica.ttc:box=0" \
    -c:v libx264 -preset fast -crf 23 \
    -c:a aac -b:a 128k \
    -t "$DUR" -pix_fmt yuv420p \
    "$CLIP" 2>/dev/null

  echo "Scene $NUM done (${DUR}s): $TEXT"
  CLIPS="$CLIPS -i $CLIP"
done

# Concatenate all clips
echo "Concatenating..."
ffmpeg -y $(for c in $CLIPS; do echo "$c"; done | tr '\n' ' ') \
  -filter_complex "concat=n=7:v=1:a=1" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -pix_fmt yuv420p \
  "$FINAL" 2>/dev/null

echo "Done! Output: $FINAL"
ls -la "$FINAL"
