#!/bin/bash
# Chạy nền một lệnh trong /content/hack. JOB mặc định = M2 trên nuScenes mini.
. "$(dirname "$0")/_env.sh"
JOB=${JOB:-python -m src.eval_nuscenes --root /content/nusc --out results/m2.json}
T=$(mktemp)
printf '#!/bin/bash\ncd /content/hack && mkdir -p results\n%s\necho "JOB_DONE EXIT=$?"\n' "$JOB" > $T
$C upload -s $SESS $T /content/job.sh 2>&1 | tail -1
rm -f $T
$C exec -s $SESS -f $H/colab/bg.py --env BG_SCRIPT=/content/job.sh --env BG_LOG=$LOG 2>&1 | tail -1
echo "Đang chạy: $JOB -> $LOG"
