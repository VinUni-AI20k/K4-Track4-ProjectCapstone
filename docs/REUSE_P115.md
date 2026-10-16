# Tận dụng từ dự án P-115 (ViR-Bot)

Repo P-115 nằm ở `C:\Users\Khanh\Documents\AInAction\final_project\P-115`. File này liệt kê phần dùng lại được, phần không nên dùng, và cách chép sang repo hackathon.

## 1. Dùng được ngay

### Dữ liệu
| Thứ | Đường dẫn trong P-115 | Dùng cho |
|---|---|---|
| nuScenes mini: 10 scene gồm `v1.0-mini/`, `samples/`, `sweeps/`, `maps/` | `data/mini-nuScenes/` | chế độ Replay, đo M2, bản đồ LiDAR |
| Video bản đồ LiDAR đã dựng: `lidar_map_follow.mp4` (bám xe) và `lidar_map_overview.mp4` (toàn cảnh 360°) của 10 scene mini | `data/demo/videos/nuscenes__v1.0__<token>/` | hình minh họa trên slide hoặc trong video mở đầu. Nói rõ là dựng từ LiDAR + ego pose ở dự án trước, không phải phần build 2 giờ |
| Video BEV `bev.mp4` | cùng thư mục | chỉ để minh họa. Video này do model dựng sẵn, không chạy trực tiếp, nên không tính là phần hệ thống |

Ánh xạ scene sang token (dùng tên thư mục `nuscenes__v1.0__<token>`):

| scene | token đầu | mô tả nuScenes |
|---|---|---|
| scene-0061 | cc8c0bf5 | xe tải đỗ, công trường, giao lộ |
| scene-0103 | fcbccedd | nhiều người đi bộ bên phải |
| scene-0553 | 6f83169d | chờ ở giao lộ, xe đạp, xe tải lớn, người qua đường (**nên dùng cho demo ban ngày**) |
| scene-0655 | bebf5f5b | bãi đỗ xe, người băng qua sai làn |
| scene-0757 | 2fc37537 | giao lộ đông, xe buýt, xe đạp |
| scene-0796 | c5224b9b | xe scooter, người đi bộ, xe buýt |
| scene-0916 | 325cef68 | bãi đỗ, giá xe đạp, nhiều người đi bộ |
| scene-1077 | d2571844 | **đêm**, đường lớn, tốc độ cao |
| scene-1094 | de7d80a1 | **đêm**, sau mưa, nhiều người đi bộ |
| scene-1100 | e233467e | **đêm**, người qua vạch kẻ đường |

### Code: chép hàm, không import chéo repo
Từ `eval/vir_bot/demo/lidar_map_render.py`:

| Hàm | Dòng | Dùng cho |
|---|---|---|
| `quat_to_matrix(q)` | 64 | quaternion của `ego_pose` / `calibrated_sensor` sang ma trận R |
| `transform_points(points, R, t)` | 72 | đổi hệ tọa độ |
| `sensor_to_scene(points, sensor_R, sensor_t, ego_R, ego_t, origin)` | 77 | LiDAR → ego → global, để dựng nền bản đồ |
| `keep_mask(points_ego, box, max_range)` | 90 | bỏ điểm trên thân xe và điểm quá xa |
| `voxel_keys` / `voxel_centers` | 104 / 112 | gộp nhiều sweep thành bản đồ voxel 0,15 m |
| `height_above_ground` | 148 | độ cao so với mặt đất, để tô màu |
| `turbo(t)` / `map_colors(points)` | 163 / 172 | bảng màu turbo theo độ cao (giống video đã duyệt) |
| `load_nuscenes(root, scene_key)` | 313 | đọc toàn bộ sweep LIDAR_TOP của một scene cùng pose |

Từ `eval/vir_bot/demo/colab/depth_points_render.py`:

| Hàm | Dòng | Dùng cho |
|---|---|---|
| `encode_mp4(png_dir, out_mp4, fps)` | 278 | ghép khung thành video dự phòng (cần ffmpeg) |
| `draw_caption(frame, text)` | 208 | chữ tiếng Anh trên video |

Ghi chú khi chép:
- `lidar_map_render.py` import `depth_points_render` qua `sys.path`. Chỉ chép các hàm thuần numpy trong bảng; không chép `render_layer` / `render_points` (dựng phối cảnh bằng torch), vì BEV hackathon là ảnh nhìn thẳng từ trên xuống, tự vẽ bằng numpy + OpenCV đơn giản hơn.
- Đầu mỗi file chép, ghi một dòng nguồn: `# Adapted from P-115 eval/vir_bot/demo/lidar_map_render.py`.
- BEV top-down cho Replay:
  1. gộp sweep quanh keyframe hiện tại (±5 sweep);
  2. đổi về hệ ego của keyframe;
  3. rasterize (x, y) lên lưới 0,1 m;
  4. tô màu bằng `map_colors`.

### Lấy box đáp án (cho M2)
`nuscenes-devkit` đã cài trong `.venv` của P-115. Trong repo mới thì `pip install nuscenes-devkit`.

```python
from nuscenes.nuscenes import NuScenes
from nuscenes.utils.geometry_utils import BoxVisibility, view_points
nusc = NuScenes("v1.0-mini", dataroot=ROOT, verbose=False)
cam = nusc.get("sample_data", sample["data"]["CAM_FRONT"])
path, boxes, K = nusc.get_sample_data(cam["token"], box_vis_level=BoxVisibility.ANY)
# boxes ở hệ CAM_FRONT: khoảng cách đáp án = box.center[2]
# box 2D đáp án = min/max của view_points(box.corners(), K, normalize=True)
# lọc nusc.get("sample_annotation", box.token)["visibility_token"] >= "2"
```

### Môi trường máy
- GPU RTX 4050 Laptop 6 GB, torch 2.6 + CUDA 12.4: chạy YOLOv8n/11n thời gian thực được.
- `.venv` của P-115 đã có torch, OpenCV và nuscenes-devkit; **chưa có** ultralytics, mediapipe, streamlit, filterpy. Nên tạo venv riêng cho hackathon, đừng cài thêm vào venv P-115:
  ```
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install torch --index-url https://download.pytorch.org/whl/cu124
  pip install ultralytics opencv-python numpy filterpy nuscenes-devkit streamlit
  pip freeze > requirements.txt
  ```

### Colab
CLI Colab trong WSL đã đăng nhập sẵn (tài khoản lauren.stevens, `HOME=/home/khanh/colab9`). Có thể chạy M2 trên Colab nếu cần; xem `docs/COLAB.md`. Live demo vẫn chạy local.

## 2. Không nên dùng

| Thứ | Lý do |
|---|---|
| Gaussian splatting / DriveStudio | Phải tối ưu riêng từng scene, mất hàng chục phút; không chạy trực tiếp; không thuộc trụ cột Track 4. Dự án trước cũng đã bỏ |
| Điểm dày Depth Anything V2 | Đã bị đánh giá "quá xấu"; model nặng; giấy phép CC-BY-NC-4.0 |
| BEV Qwen-Drive làm phần hệ thống | Không chạy trực tiếp; giám khảo coi là "gọi model có sẵn", tiêu chí 1 bị mức thấp |
| Toàn bộ tìm kiếm ViR-Bot (SigLIP 2, Qdrant, GPT-4o parse) | Lạc đề; có gọi dịch vụ trả phí |
| Dữ liệu Phenikaa | Dữ liệu của dự án khác; không đưa lên repo public |
| `.env`, key OpenAI, `DATABASE_URL` | Tuyệt đối không chép |

## 3. Câu trả lời sẵn khi giám khảo hỏi "có phải dùng lại dự án cũ không"

> "Nền bản đồ LiDAR dùng lại hàm đổi hệ tọa độ ego → global từ dự án trước của em. Phần build trong 2 giờ là: phát hiện, khoảng cách pinhole, Kalman, TTC, cờ bất định, BEV và bộ đo M1–M3. Toàn bộ số đo đều chạy mới hôm nay."
