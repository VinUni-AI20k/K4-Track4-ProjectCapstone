# Hand/Arm tracking -> PyBullet simulation

## Chay nhanh trong VS Code
1. Giai nen, **File -> Open Folder** chon thu muc `hand_sim`.
2. Mo terminal Conda va tao moi truong Python 3.11:
   ```powershell
   conda create -n hand-sim python=3.11 pip -y
   conda activate hand-sim
   python -m pip install -r requirements-holistic.txt
   ```
3. `Ctrl+Shift+P` -> **Python: Select Interpreter** -> chon moi truong Conda `hand-sim`.
4. Nhan **F5** -> chon `Holistic + Sim (webcam)`. Nhan **Esc** tren cua so video de thoat.

Hoac chay tu terminal sau khi `conda activate hand-sim`:
```powershell
python run_holistic.py --sim
```
`setup.bat` va `setup.sh` van co the dung neu muon tao moi truong `.venv` thay vi Conda.

## File
- `run_holistic.py`  : MediaPipe Holistic (canh tay + 21 keypoint moi ban tay) -> mo phong
- `sim_env.py`       : moi truong PyBullet, ban tay 21 khop, logic cam/nam
- `train_hand.py`    : huan luyen model tren CMU Panoptic Hand (tuy chon, can torch)
- `run_pipeline.py`  : Pose + model CMU tu train (tuy chon, can `pip install torch torchvision`)
- `requirements-holistic.txt` : chi can cho run_holistic.py
- `requirements.txt` : day du, gom torch (cho train_hand / run_pipeline)

## Loi thuong gap
- `AttributeError: module 'mediapipe' has no attribute 'solutions'`: kiem tra da chay `conda activate hand-sim` va chon moi truong Conda `hand-sim` trong **Python: Select Interpreter**. Moi truong nay cai MediaPipe `0.10.14`; khong chay bang Python khac da cai MediaPipe phien ban moi.
- Webcam den/khong mo: thu `--source 1`, dong Zoom/Teams, cap quyen camera.
- Giat: chon cau hinh `Holistic nhe (complexity 0)`.
- Tay trong sim bi lat/nguoc: doi dau trong `to_sim()` o `sim_env.py`.
