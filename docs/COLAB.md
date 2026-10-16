# Chạy trên Colab (tùy chọn)

**Live demo chạy local, không dùng Colab.** Webcam đi qua Colab bị trễ vài trăm ms, làm hỏng số đo M3 và cảnh báo TTC. RTX 4050 local chạy YOLOv8n/11n thời gian thực được.

Colab chỉ đáng dùng khi:
- chạy M2 (`src/eval_nuscenes.py`) với model lớn hơn (`yolo11m`/`yolo11l`) để so với bản nhỏ;
- dựng lại video Replay dài;
- máy local đang bận demo.

nuScenes mini chỉ có 10 scene (404 keyframe CAM_FRONT), nên M2 bản nhỏ chạy local được.

## Điều kiện

- WSL Ubuntu có CLI Colab: `/home/khanh/.local/bin/colab`, đăng nhập sẵn với `HOME=/home/khanh/colab9` (tài khoản lauren.stevens).
- Bước gắn Drive (`drivemount`) cần terminal thật để bấm link cấp quyền. Chỉ cần gắn khi đọc dữ liệu từ Drive. Với nuScenes mini, script tự đóng gói dữ liệu từ máy rồi đưa lên, không cần Drive.
- Kiểm còn bao nhiêu CU trước khi tạo session: `bash colab/usage.sh`.

## Các script (chạy từ PowerShell)

Mọi script nằm trong `colab/` và chạy qua WSL:

```
wsl -d Ubuntu -e bash /mnt/c/Users/Khanh/Documents/AInAction/final_hackathon/colab/<script>.sh
```

| Script | Làm gì | Biến môi trường |
|---|---|---|
| `usage.sh` | liệt kê session, xem CU còn lại | |
| `up.sh` | tạo session GPU; đóng gói `src/` + `requirements.txt` (+ nuScenes mini nếu `WITH_DATA=1`); đưa lên; giải nén; cài thư viện | `SESS` (mặc định `hack-g4`), `GPU` (mặc định `G4`), `WITH_DATA`, `NUSC` (đường dẫn WSL tới nuScenes mini) |
| `run.sh` | chạy nền một lệnh Python trong `/content/hack`, ghi log | `JOB` (mặc định là lệnh M2), `LOG` |
| `log.sh` | xem đuôi log | `LOG`, `N` |
| `dl.sh` | tải `/content/hack/results/` về `results/colab/` | |
| `stop.sh` | tắt session để ngừng tốn CU | |

### Quy trình M2 trên Colab

```
# 1. Tạo session, đưa code và dữ liệu lên (chỉ samples/CAM_FRONT 404 ảnh, 71 MB + v1.0-mini 32 MB; đủ cho M2)
$env:WSLENV="WITH_DATA/u"; $env:WITH_DATA="1"
wsl -d Ubuntu -e bash /mnt/c/Users/Khanh/Documents/AInAction/final_hackathon/colab/up.sh

# 2. Chạy M2 với model lớn
$env:WSLENV="JOB/u"; $env:JOB="python -m src.eval_nuscenes --root /content/nusc --model yolo11m.pt --out results/m2_yolo11m.json"
wsl -d Ubuntu -e bash /mnt/c/Users/Khanh/Documents/AInAction/final_hackathon/colab/run.sh

# 3. Theo dõi (log in JOB_DONE EXIT=<mã> khi xong)
wsl -d Ubuntu -e bash /mnt/c/Users/Khanh/Documents/AInAction/final_hackathon/colab/log.sh

# 4. Tải kết quả, rồi tắt session
wsl -d Ubuntu -e bash /mnt/c/Users/Khanh/Documents/AInAction/final_hackathon/colab/dl.sh
wsl -d Ubuntu -e bash /mnt/c/Users/Khanh/Documents/AInAction/final_hackathon/colab/stop.sh
```

`WSLENV` cho phép biến từ PowerShell đi vào WSL. Nếu chạy trong terminal Ubuntu thì chỉ cần `WITH_DATA=1 bash colab/up.sh`.

## Lỗi đã gặp ở dự án trước

- `drivemount` treo khi không có tty: chạy trong terminal thật, đừng chạy qua công cụ tự động.
- Git Bash đổi `/content/...` thành đường dẫn Windows: chạy qua `wsl.exe`, hoặc đặt `MSYS_NO_PATHCONV=1`.
- Session không tự tắt vẫn tốn CU: luôn chạy `stop.sh` khi xong.
- Không đưa `.env` hay key lên Colab. M2 không cần key.
