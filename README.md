# VinFast FCW-BEV

Cảnh báo va chạm trước bằng một camera. Hệ thống phát hiện người và xe, ước lượng khoảng cách, tính TTC và vẽ BEV. Có hai chế độ: Live (webcam) và Replay (nuScenes mini, LiDAR làm đáp án).

- Spec: [SPEC.md](SPEC.md)
- Tận dụng từ dự án trước: [docs/REUSE_P115.md](docs/REUSE_P115.md)
- Colab (tùy chọn, chỉ cho bộ đo M2): [docs/COLAB.md](docs/COLAB.md)

## Chạy nhanh
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install ultralytics opencv-python numpy filterpy nuscenes-devkit streamlit
python -m src.app --source webcam
python -m src.app --source nuscenes --root data/mini-nuScenes --scene scene-0553
python -m src.eval_nuscenes --root data/mini-nuScenes --out results/m2.json
```

## Dữ liệu
nuScenes mini (CC BY-NC-SA 4.0) không nằm trong repo. Tải từ https://www.nuscenes.org/nuscenes#download rồi giải nén vào `data/mini-nuScenes/`.
