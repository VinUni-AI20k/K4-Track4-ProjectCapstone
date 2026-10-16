#!/bin/bash
# Tạo session GPU, đưa code (+ nuScenes mini nếu WITH_DATA=1) lên /content, cài thư viện. Không đụng key.
set -e
. "$(dirname "$0")/_env.sh"
GPU=${GPU:-G4}
NUSC=${NUSC:-/mnt/c/Users/Khanh/Documents/AInAction/final_project/P-115/data/mini-nuScenes}
T=$(mktemp -d)

echo "== 1/4 Tạo session $SESS ($GPU)"
$C new -s $SESS --gpu $GPU 2>&1 | tail -3

echo "== 2/4 Đóng gói và đưa code lên"
tar czf $T/code.tgz -C $H --exclude=__pycache__ src requirements.txt $( [ -d $H/calib ] && echo calib )
$C upload -s $SESS $T/code.tgz /content/code.tgz 2>&1 | tail -1
if [ "${WITH_DATA:-0}" = "1" ]; then
  echo "   + nuScenes mini (samples/CAM_FRONT + v1.0-mini)"
  tar czf $T/nusc.tgz -C $NUSC samples/CAM_FRONT v1.0-mini LICENSE
  $C upload -s $SESS $T/nusc.tgz /content/nusc.tgz 2>&1 | tail -1
fi

echo "== 3/4 Giải nén"
cat > $T/unpack.py <<'PY'
import subprocess
cmd = ("mkdir -p /content/hack /content/nusc && tar xzf /content/code.tgz -C /content/hack && "
       "( [ -f /content/nusc.tgz ] && tar xzf /content/nusc.tgz -C /content/nusc || true ) && "
       "ls /content/hack /content/nusc && nvidia-smi --query-gpu=name,memory.total --format=csv")
r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(r.stdout[-2000:], r.stderr[-1000:])
PY
$C exec -s $SESS -f $T/unpack.py --timeout 300 2>&1 | tail -12

echo "== 4/4 Cài thư viện (nền, log /content/setup.log)"
cat > $T/setup.sh <<'X'
#!/bin/bash
cd /content/hack
pip install -q -r requirements.txt || pip install -q ultralytics opencv-python-headless numpy filterpy nuscenes-devkit
python -c "import ultralytics, torch; print('ultralytics', ultralytics.__version__, 'cuda', torch.cuda.is_available())"
echo SETUP_DONE
X
$C upload -s $SESS $T/setup.sh /content/setup.sh 2>&1 | tail -1
$C exec -s $SESS -f $H/colab/bg.py --env BG_SCRIPT=/content/setup.sh --env BG_LOG=/content/setup.log 2>&1 | tail -1
rm -rf $T
echo "Xong. Xem cài đặt: LOG=/content/setup.log bash colab/log.sh (chờ SETUP_DONE), rồi chạy colab/run.sh."
