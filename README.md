# K4 Track 4 Project Capstone — Vin Perception Hackathon

Trang đề bài hackathon cuối khóa Track 4 (Computer Vision & Robotics): 2 giờ build, 10 phút demo mỗi team, đề tài gắn với hệ sinh thái Vin.

- `index.html`: trang đề bài (một file, không cần build). Mở trực tiếp bằng trình duyệt.

Nội dung gồm hướng đề tài gợi ý, bốn yêu cầu của mỗi demo, bảy trụ cột Track 4, công cụ gợi ý, thang điểm, lịch trình, checklist trước demo và FAQ. Ngày giờ, địa điểm, giám khảo, giải thưởng sẽ được ban tổ chức cập nhật.

## Member 2 — Geometry 3D

Module [modules/geometry.py](modules/geometry.py) biến pixel thành giao điểm tia camera với mặt phẳng đã biết, trong hệ tọa độ robot Z-up (mét). Không suy ra độ sâu từ một ảnh đơn lẻ; phải có calibration và giả định mặt phẳng.

### Chạy nhanh

Python 3.10+; chỉ cần NumPy, không cần tải dataset hoặc train model:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python demo_geometry.py
python demo_geometry.py --snapshot tests/fixtures/threejs_camera_snapshot.json --meters-per-unit 1
```

- Demo mặc định dùng camera và ground truth tổng hợp, được ghi rõ `SYNTHETIC`.
- Replay dùng ma trận và pixel tham chiếu đã xuất từ simulator Three.js thực chạy. Đây là kiểm chứng hình học, không phải benchmark detector hoặc robot thật.
- Ca lỗi demo: ngoài workspace, confidence thấp, pixel NaN và vật cao hơn mặt phẳng 5 cm.
- `tests/fixtures/threejs_camera_snapshot.json` là snapshot của ba điểm tham chiếu trên sàn, không phải dữ liệu nhận diện vật liệu.

### Phối hợp các nhánh của team

- Nhánh geometry được tạo trên `origin/feature/temporal-uncertainty` tại `bc1ae39`; giữ nguyên thuật toán và 9 test của Member 3.
- Hai file simulator lấy từ `origin/huy20/simulator` tại `7ceb888`; chưa tạo merge commit. Chỉ bản `Trash Bin Simulator 3D.html` được bổ sung API đọc camera.
- `simulator.html` dùng CSS 3D, không có camera metric. Không dùng pixel của trang này để giả lập calibration vật lý.
- `Trash Bin Simulator 3D.html` dùng Three.js PerspectiveCamera, trục **Y-up**, camera quay/zoom được. Snapshot phải lấy cùng frame với ảnh; không tái dùng calibration cũ sau resize/quay/zoom.
- Simulator hiện là actuator mở nắp thùng, chưa có cánh tay robot, IK hoặc bàn gắp vật lý. Pixel tham chiếu không phải bounding box của model.
- Tracker nhận `target_world_3d`, `material_class`, `confidence`, `is_within_reach`; trả `should_trigger_pick`. Geometry chưa nối Python với trình duyệt qua server/WebSocket.

### Quy ước tọa độ và giao diện

Camera pinhole dùng OpenCV: X phải, Y xuống, Z nhìn về trước. `camera_to_world` là ma trận 4×4 **camera → robot world**, translation tính bằng mét. World thuận tay phải, Z lên. Với `K` không skew:

```text
r_camera = [(u-cx)/fx, (v-cy)/fy, 1]
r_world  = R_camera_to_world @ r_camera
lambda   = dot(normal, plane_point - camera_origin) / dot(normal, r_world)
P_world  = camera_origin + lambda * r_world
```

Từ Three.js sang robot: **(X, Y, Z) → (X, -Z, Y) × meters_per_unit**. Scale phải được Leader thống nhất, không tự suy ra đơn vị scene là mét. Phép đổi này giữ hệ thuận tay phải và đưa mặt sàn X–Z thành mặt X–Y mà tracker đang dùng để tính sai số.

```python
from modules import GeometryCoordinateTransformer, WasteTemporalUncertaintyTracker

# Cấu hình DEMO, không phải calibration của simulator thực tế.
geometry = GeometryCoordinateTransformer(
    fx=550, fy=550, cx=320, cy=240, image_size=(640, 480),
    camera_to_world=[[1, 0, 0, 0], [0, -1, 0, 0.35],
                     [0, 0, -1, 0.25], [0, 0, 0, 1]],
    plane_point=(0, 0, -0.1),
    workspace_limits=((-0.25, 0.25), (0.15, 0.50), (-0.11, 0.1)),
    clearance_m=0.05,
)
tracker = WasteTemporalUncertaintyTracker()
detections = [{"material_class": "Plastic", "confidence": 0.95,
               "center_pixel": [398.57142857142856, 240]}]
try:
    items = geometry.process(detections)
    tracked = tracker.update(items, {"true_world_pos": [0.05, 0.35, -0.1]})
except ValueError:
    tracker.reset()
    tracked = {"target_object": None, "should_trigger_pick": False}
```

Kết quả geometry bổ sung:

- `target_world_3d`: tọa độ trên mặt phẳng, không làm tròn nội bộ.
- `pre_pick_world_3d`: target + clearance × normal.
- `pick_approach_vector`: hướng `-normal`; mặc định `(0, 0, -1)`.
- `is_within_reach`: cả target và pre-pick nằm trong AABB XYZ được cấu hình.
- `coordinate_frame`: `robot_world_z_up`.
- Chấp nhận `center_pixel` hoặc `pixel_center`; nếu cả hai tồn tại thì phải bằng nhau. Giữ nguyên metadata như object ID. Thiếu nhãn/confidence/pixel hoặc dữ liệu không hữu hạn gây `ValueError`, không phát tọa độ giả `(0,0,0)`.

Member 1 cần quy đổi pixel từ resize/letterbox về ảnh gốc được calibration; ảnh camera thật cần khử distortion trước. Không đưa confidence theo phần trăm 0–100; dùng 0–1.

### Xuất snapshot từ simulator Three.js

Mở `Trash Bin Simulator 3D.html` trong trình duyệt có WebGL và truy cập được CDN Three.js. Trong Chrome DevTools Console:

```javascript
const snapshot = TrashBins.getGeometrySnapshot([
  [0, 0, 0], [0.1, 0, 0.2], [-0.2, 0, -0.1]
]);
copy(JSON.stringify(snapshot, null, 2));
```

Lưu nội dung clipboard thành `camera_snapshot.json`, rồi chạy:

```bash
python demo_geometry.py --snapshot camera_snapshot.json --meters-per-unit 1
```

Giá trị `1` là lựa chọn scale cho phép thử; đổi theo calibration của team. API dùng kích thước **canvas drawing buffer**, không phải CSS clientWidth hoặc toàn bộ screenshot trang. Ma trận Three.js được tuần tự theo column-major; adapter Python đã xử lý thứ tự này và khác biệt GL/OpenCV.

`TrashBins.projectWorldPoint([x,y,z])` trả pixel và `in_view` (trong frustum, KHÔNG kiểm tra bị vật khác che). Replay chỉ nhận reference points trên sàn scene Y=0. Điểm tham chiếu phải xuất cùng snapshot để tránh lệch pose camera.

### Giới hạn cần trình bày đúng

- AABB không phải kiểm tra IK, collision hay bảo đảm an toàn robot; hướng tiếp cận không phải full orientation/yaw tối ưu.
- Không đo chiều cao vật thể từ bbox. Vật lệch khỏi mặt phẳng sẽ có sai số; demo minh họa lỗi 3D khoảng 50.69 mm khi vật cao hơn 5 cm. Có thể chỉnh mặt phẳng nếu biết độ cao, hoặc bổ sung depth sau.
- Tracker hiện chỉ tính sai số XY, không phát hiện sai số riêng trên Z; không gọi đó là kiểm chứng sai số 3D đầy đủ.
- Tracker có một bộ lọc, ưu tiên phần tử reachable đầu tiên; integration phải giữ cùng một target qua các frame và gọi `reset()` khi đổi vật thể hoặc gặp calibration/input lỗi. Không tuyên bố hỗ trợ multi-object tracking.
- Simulator nhận các khóa `metal/paper/plastic/organic`, còn tracker giữ nhãn nguyên văn. Member 4 cần mapping nhãn rõ ràng và chỉ điều khiển khi gate cho phép; ví dụ `Glass` không tự map vào một thùng khác.
- Không tải Roboflow dataset: truy cập Universe bị Cloudflare chặn và geometry không cần ảnh huấn luyện. Chưa xác minh class list/license của dataset, chưa tích hợp detector thật.

Tài liệu nhiệm vụ gốc [MEMBER_2_GEOMETRY_3D.md](MEMBER_2_GEOMETRY_3D.md) được giữ nguyên; công thức/output ở đó là khung tham khảo, không thay thế phép đổi camera → world ở implementation này.
