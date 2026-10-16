# Phân công nhóm 3 người

Đi kèm [SPEC.md](../SPEC.md) bản 2. Giờ ghi theo lịch của ban tổ chức:
- **0:00–0:15:** chốt đề, phân vai.
- **0:15–2:15:** build (120 phút).
- **1:15:** giảng viên đi kiểm tra. Lúc này phải có thứ chạy được từ đầu vào đến đầu ra.
- **2:15–2:30:** dừng code, quay video dự phòng, chốt số đo.
- **2:30:** demo.

## 1. Ba vai

| Vai | Người | Phụ trách | Sở hữu file |
|---|---|---|---|
| **Core** | Khánh | Calib, hình học, chạy YOLO trên Colab ra cache, đo M2/M4/M3 (Colab), so `yolo11n` với `yolo11m`, quay video dự phòng | `calib.py`, `geometry.py`, `detect.py`, `detect_cache.py`, `eval_bev.py`, `eval_zones.py`, `sources.py` (phần `PhenikaaSource`), `colab/` |
| **BE** | (tên) | Lõi hệ thống: đọc nguồn, gộp, bám vật, vùng cảnh báo, vòng lặp chính, log CSV, pipeline Live | `contracts.py`, `sources.py` (phần `NuScenesSource`, `WebcamSource`), `fuse.py`, `tracker.py`, `zones.py`, `app.py`, `config/` |
| **FE** | (tên) | Mọi thứ hiển thị: lưới 6 camera, BEV 360°, nền LiDAR, giao diện Live, phím tắt, ghi MP4; hiệu chuẩn webcam; slide | `ui.py`, `bev.py`, `tools/mock_state.py`, `tools/calib_webcam.py`, `calib/webcam.json`, slide |

Chỉ người sở hữu mới sửa file đó. Cần đổi giao kèo ở mục 2 thì báo cả nhóm trước khi sửa.

**Dữ liệu Phenikaa chỉ nằm trên máy của Khánh** (cũng là máy demo), trừ khi chủ dữ liệu cho phép chép sang máy khác.
- BE và FE code và thử trên nuScenes mini (tự tải được) cùng `mock_state`.
- Ghép với Phenikaa thì làm trên máy demo.
- Nếu chủ dữ liệu cho phép, Khánh chép cho BE và FE một mẫu 10 khung của COMPLEX CITY.

## 2. Giao kèo giữa các vai (chốt trước 0:15)

### 2.1 Core → BE: cache detection

`cache/<dataset>/<scene>/<model>.jsonl`, mỗi dòng là một camera ở một khung:

```json
{"t": 1700000000.123, "frame": 0, "cam": "CAM_P_F",
 "boxes": [{"cls": "motorcycle", "conf": 0.82, "xyxy": [812.0, 640.5, 905.2, 790.0]}]}
```

Tọa độ pixel tính trên ảnh gốc, chưa khử méo.

### 2.2 Core → BE: calib và hình học

```python
# calib.py
load_calib(dataset, root, scene) -> dict[str, CamCalib]
# CamCalib: K (3x3), dist (5 hoặc 8 hệ số), size (W, H), T_cam2ego (4x4), z_ground (float)

# geometry.py
ground_point(xyxy, cam: CamCalib) -> Hit | None
height_point(xyxy, cam: CamCalib, H: float) -> Hit | None
# Hit: x, y (m, hệ xe), dist (m), method ("ground" | "height"), at_edge (bool)
```

Trước khi `geometry.py` xong, BE dùng bản stub trả về điểm giả. Chữ ký hàm giữ nguyên.

### 2.3 BE: một khung từ nguồn

```python
Frame(t, images: dict[cam, ndarray BGR], calib: dict[cam, CamCalib],
      ego_T: 4x4 (xe → thế giới), gt: list[dict] | None)
# gt mỗi phần tử: cls, x, y, z, l, w, h, yaw (trong hệ xe)
```

### 2.4 BE → FE: trạng thái để vẽ

`app.py` gọi `ui.render(state, opts) -> ndarray` mỗi khung. `state` là dict:

```python
{
  "t": float, "source": "phenikaa" | "nuscenes" | "webcam", "scene": str, "model": str,
  "images": {cam: ndarray},
  "dets":   [{"cam", "cls", "conf", "xyxy", "track_id", "level", "uncertain"}],
  "tracks": [{"id", "cls", "x", "y", "vx", "vy", "trail": [[x, y], ...],
              "zone": "SAT_SUON" | "TAT_DAU" | "PHIA_TRUOC" | None,
              "level": 0 | 1 | 2, "ttc": float | None, "uncertain": bool}],
  "gt":     [{"cls", "x", "y", "l", "w", "yaw"}],          # có thể rỗng
  "ego_box": {"length", "width", "x_offset"},             # lấy từ config/
  "zone_cfg": {...},                                      # ngưỡng vùng, lấy từ config/
  "stats":  {"fps", "latency_ms", "n_tracks", "alerts": {"SAT_SUON": n, "TAT_DAU": n, "PHIA_TRUOC": n}}
}
```

Ý nghĩa `level`:
- **0:** không cảnh báo;
- **1:** cảnh báo vàng;
- **2:** nguy hiểm, màu đỏ.

Nếu `uncertain` là `true` thì vẽ viền vàng và không bao giờ vẽ đỏ.

### 2.5 FE: phím tắt và ghi hình

| Phím | Tác dụng |
|---|---|
| `Space` | dừng hoặc chạy tiếp |
| `←` / `→` | lùi hoặc tiến 1 khung |
| `g` | bật hoặc tắt lớp đáp án |
| `m` | đổi model (nếu có cả hai cache) |
| `r` | bắt đầu hoặc dừng ghi |
| `q` | thoát |

Cờ `--record out.mp4` ghi đúng khung hình đang hiện ra màn hình, nên Khánh dùng nó để quay video dự phòng.

## 3. Lịch từng người

| Giờ | Core (Khánh) | BE | FE |
|---|---|---|---|
| **0:00–0:15** | Bắt đầu chạy `up.sh` với `WITH_PHENIKAA=1` ngay, vì upload khoảng 355 MB mất thời gian. Tạo repo và khung thư mục | Viết `contracts.py` (mục 2.3–2.4) | Viết `mock_state.py` sinh `state` giả có chuyển động. In hoặc mở sẵn bàn cờ |
| **0:15–0:35** | `calib.py` cho Phenikaa. **Kiểm tra chiều ngoại tham số:** chiếu nhãn vào `CAM_P_F`, so với `COMPLEX_CITY_projected_3d_box_5x2.mp4`. Trên Colab: chạy `detect_cache` với `yolo11n`, Phenikaa 2 scene | `NuScenesSource` (6 camera, keyframe, ego pose, đáp án đổi sang hệ xe). Stub `geometry` | Khung `ui.py`: lưới 2×3 + vùng BEV + thanh trạng thái, chạy với `mock_state`. Chụp 15–20 ảnh bàn cờ → `calib_webcam.py` → `calib/webcam.json` |
| **0:35–0:55** | `geometry.py`: khử méo, điểm tiếp đất, camera → xe, dự phòng f·H/h. Fit z_g từ LiDAR. Tải cache về. Viết `PhenikaaSource` (đồng bộ 6 camera theo timestamp) | `fuse.py`: gộp rider, gộp vật trùng giữa camera. `app.py`: nguồn + cache + geometry + fuse → `state` → `ui.render`. Log CSV | `bev.py`: khung xe, lưới 1 m, tô vùng, chấm theo lớp, vệt quỹ đạo, mũi tên vận tốc, lớp đáp án. Vẽ box lên camera, viền camera có cảnh báo |
| **0:55–1:15** | **Ghép trên máy demo** (cả nhóm): Replay Phenikaa hiện detection của 6 camera trên BEV. Live đơn giản: webcam → YOLO → f·H/h → chấm phía trước | ← | ← |
| **1:15** | **Mốc kiểm tra của giảng viên.** Chạy Replay Phenikaa và Live thô | | |
| **1:15–1:40** | `eval_bev`: M2 cho Phenikaa và nuScenes. Trên Colab: cache `yolo11m`, cache nuScenes 6 camera, M3 Colab. **Quay video V1** | `tracker.py`: bù ego pose, ghép gần nhất với cổng 1,5 m, Kalman [x, y, vx, vy] | Nền LiDAR (dùng lại hàm P-115, thử trên nuScenes, dựng ảnh Phenikaa trên máy demo). Phím tắt, `--record`, bố cục Live |
| **1:40–2:00** | `eval_zones`: M4 (dùng `zones.py` của BE). M2 tách ngày/đêm (L3). Cùng BE chọn khung cho L1, L2, L4. Chạy `stop.sh` | `zones.py`: SÁT SƯỜN, TẠT ĐẦU, PHÍA TRƯỚC + TTC, cờ KHÔNG CHẮC. Live: nối tracker và zones, đo M3 Live (FPS, độ trễ p50/p95) | Đo M1 cùng BE: một người đứng ở 1, 2, 3 m, mỗi mốc 30 khung. Slide: bài toán, bảng M1–M4, ca lỗi, 7 trụ cột, impact |
| **2:00–2:15** | **Đóng băng code.** Quay **video V2** bằng `app --record` | Sửa lỗi chặn demo, không thêm tính năng | Điền số vào slide. Tập demo một lượt |
| **2:15–2:30** | Quay **video V3** (Live). Kiểm tra cả 3 video phát được trên máy demo | Chạy thử Live ở chỗ demo (ánh sáng, khoảng cách) | Bấm giờ một lượt 10 phút |

Mốc nội bộ:
- **0:55:** mỗi người có phần của mình chạy được riêng (Core: chấm BEV trên `CAM_P_F` khớp nhãn; BE: `app.py` chạy với stub; FE: UI chạy với `mock_state`).
- **1:15:** chạy được từ đầu vào đến đầu ra, chưa cần bám vật.

## 4. Video dự phòng (Core)

| Video | Lúc quay | Nội dung | Cách làm |
|---|---|---|---|
| **V1** | 1:15–1:40 | Lưới 6 camera Phenikaa có box YOLO và box nhãn chiếu vào. Thêm một đoạn `yolo11n` cạnh `yolo11m` | Script trên Colab đọc cache, vẽ, `encode_mp4` (P-115), tải về |
| **V2** | 2:00–2:15 | Replay COMPLEX CITY đầy đủ UI: lưới 6 camera + BEV + cảnh báo. Gồm 3 đoạn: xe máy vượt sát sườn, xe tạt đầu, xe bị cắt mép (L2) | `python -m src.app --source phenikaa ... --record v2.mp4` |
| **V3** | 2:15–2:30 | Live: một thành viên đi về phía webcam, TTC giảm, vàng rồi đỏ; rồi ngồi xuống (L5) | `python -m src.app --source webcam --record v3.mp4`, chỉ quay thành viên đội |

Lưu ý:
- Khi chuyển sang video lúc demo, phải nói rõ đó là video.
- Tiêu chí "Demo chạy được" chấm thấp nếu demo chủ yếu là video, nên video chỉ dùng để dự phòng. Live phải chạy thật trước mặt giám khảo.

## 5. Nếu chậm

| Ai | Bỏ trước | Không được bỏ |
|---|---|---|
| Core | nuScenes 6 camera (chỉ giữ `CAM_FRONT` cho L3), `yolo11m`, V1 | kiểm tra ngoại tham số, cache Phenikaa `yolo11n`, M2 Phenikaa, V2 |
| BE | TẠT ĐẦU (chỉ giữ SÁT SƯỜN + PHÍA TRƯỚC), gộp vật trùng giữa camera | `app.py` chạy được, Live với TTC, cờ KHÔNG CHẮC |
| FE | nền LiDAR, phím `m`, Streamlit | lưới 6 camera + BEV, `--record`, `calib/webcam.json` (nếu không kịp thì dùng fx ước lượng từ HFOV và ghi rõ) |

## 6. Chia lời khi demo (10 phút)

| Phút | Người nói | Nội dung |
|---|---|---|
| 0–1 | FE | Bài toán, người dùng, đọc màn hình (màu, vùng, viền vàng nghĩa là gì) |
| 1–3 | Core | Replay Phenikaa: SÁT SƯỜN, TẠT ĐẦU, L2; bật lớp đáp án |
| 3–5 | BE | Live: mời giám khảo bước về phía webcam; TTC; ngồi xuống thì ra L5 |
| 5–7 | Core | M1–M4, một ca lỗi kèm lý do, 7 trụ cột (chỉ vào sơ đồ pipeline) |
| 7 | FE | Impact và hướng mở rộng |
| 7–10 | cả nhóm | Hỏi đáp |

## 7. Câu hỏi mỗi người phải trả lời được

Theo tiêu chí chấm, giám khảo có thể hỏi bất kỳ thành viên nào. Mỗi người cần nắm phần của mình và nói được pipeline từ đầu đến cuối trong 30 giây.

- **Core:**
  - Vì sao dùng điểm tiếp đất mà không dùng f·H/h?
  - Kiểm tra chiều ngoại tham số bằng cách nào?
  - Vì sao giới hạn ở 30 m?
  - M2 ghép detection với nhãn trên ảnh để tránh lỗi gì?
  - `yolo11n` và `yolo11m` khác nhau bao nhiêu, đổi lấy gì?
- **BE:**
  - Vì sao bám vật trên BEV mà không dùng IoU?
  - R của Kalman lấy ở đâu?
  - Không bù ego pose thì sai thế nào?
  - TTC tính ra sao?
  - Vì sao ngưỡng gộp vật trùng là 1,0 m?
  - Khi nào bật KHÔNG CHẮC?
- **FE:**
  - Mỗi màu và mỗi vùng nghĩa là gì?
  - Độ trễ đo từ đâu đến đâu?
  - Vì sao dùng cửa sổ OpenCV mà không dùng Streamlit?
  - Lớp đáp án lấy từ đâu?
  - Hiệu chuẩn webcam ra fx bao nhiêu?

## 8. Việc làm trước buổi (nếu ban tổ chức cho phép)

Chỉ chuẩn bị môi trường, không viết sẵn code sản phẩm:
- **Core:**
  - thêm `WITH_PHENIKAA=1` vào `colab/up.sh`, chạy thử một lần rồi `stop.sh`;
  - xin chủ dữ liệu Phenikaa đồng ý cho dùng trên Colab và chiếu lên slide.
- **Cả nhóm:**
  - cài `ultralytics`, `opencv-python`, `nuscenes-devkit`, `laspy[lazrs]`;
  - tải sẵn `yolo11n.pt` và nuScenes mini;
  - thử webcam trên máy demo.
- **FE:** in bàn cờ hiệu chuẩn.
