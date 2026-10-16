# VinFast Surround Rider Warning: cảnh báo xe máy áp sát và tạt đầu bằng nhiều camera, có BEV 360°

Spec cho Vin Perception Hackathon, Track 4: 2 giờ build, 10 phút demo. Bản 2, ngày 16/10/2026.

**Đổi so với bản 1:**
- Bỏ hướng cảnh báo va chạm phía trước (FCW) bằng một camera. Lý do: ở đường Việt Nam, tình huống nguy hiểm thường gặp là xe máy vượt sát sườn hoặc tạt đầu, ít khi là ô tô áp sát phía trước. Dữ liệu Phenikaa (Hà Nội) cho thấy rõ điều này.
- Dùng 6 camera quanh xe. Thêm dữ liệu Phenikaa.
- Colab làm phần tính toán nặng; máy local lo hiển thị và chế độ Live.

## 1. Bài toán và người dùng

- **Đơn vị Vin:** VinFast, mảng hỗ trợ lái (ADAS).
- **Người dùng:**
  - Kỹ sư kiểm thử ADAS: cần biết khi nào và vì sao cảnh báo kêu sai hoặc kêu muộn.
  - Tài xế: nhận cảnh báo khi xe máy hoặc người áp sát sườn, tạt đầu, hoặc lao vào phía trước.
- **Nỗi đau:**
  - Ở Việt Nam, xe máy bám quanh ô tô với mật độ rất dày (Phenikaa COMPLEX CITY: trung bình 164 vật mỗi khung, trong đó khoảng 44% là xe máy có người lái).
  - Gương và điểm mù không đủ để thấy hết.
  - Cảnh báo kêu liên tục thì tài xế tắt tính năng. Kêu sót thì quẹt xe.
- **Sản phẩm:**
  - phát hiện người, xe máy và ô tô trên 6 camera quanh xe;
  - đặt từng vật lên bản đồ nhìn từ trên xuống 360° (BEV) trong hệ tọa độ của xe;
  - bám vật qua các khung để ra vận tốc;
  - cảnh báo theo vùng: **SÁT SƯỜN**, **TẠT ĐẦU**, **PHÍA TRƯỚC** (có TTC);
  - bật cờ "KHÔNG CHẮC" khi hình học không đáng tin.

## 2. Ba nguồn dữ liệu, một pipeline

Pipeline nhận N camera, mỗi camera có K, hệ số méo và ngoại tham số camera → xe. Các nguồn chỉ khác N và cách đọc dữ liệu.

| Nguồn | N camera | Tần số | Đáp án | Vai trò |
|---|---|---|---|---|
| **Phenikaa** (Hà Nội): COMPLEX CITY, COMPLEX URBAN | 6: `CAM_P_F`, `CAM_P_FL`, `CAM_P_FR`, `CAM_P_L`, `CAM_P_R`, `CAM_P_B` | 10 Hz, 200 khung mỗi scene (20 s) | nhãn 3D trong hệ LiDAR (Car, Rider, Pedestrian), LiDAR `.laz`, ego pose | **demo chính**, đo M2 và M4 trên đường Việt Nam |
| **nuScenes mini** (Boston, Singapore) | 6: `CAM_FRONT`, `CAM_FRONT_LEFT`, `CAM_FRONT_RIGHT`, `CAM_BACK`, `CAM_BACK_LEFT`, `CAM_BACK_RIGHT` | 2 Hz keyframe | box 3D có `visibility`, LiDAR | đo M2 và M4 trên đủ 10 scene; ca lỗi ban đêm; so sánh với Phenikaa |
| **Live** (webcam laptop) | 1 | 30 Hz | thước dây | đoạn demo tương tác; đo M1 và M3 |

- Bỏ 4 camera mắt cá `CAM_F_*` của Phenikaa. Chúng theo mô hình Kannala-Brandt, không chiếu theo pinhole được, và 6 camera `CAM_P_*` đã phủ đủ 360°.
- Chế độ Live chỉ có vùng PHÍA TRƯỚC, vì N = 1.

## 3. Chia việc giữa Colab và máy local

| Nơi chạy | Làm gì | Vì sao |
|---|---|---|
| **Colab** (GPU) | Chạy YOLO trên mọi khung của 6 camera, ghi ra cache detection. Chạy M2 và M4. Chạy cả `yolo11n` và `yolo11m` để so sánh | Phần cần GPU. Model lớn bắt xe máy nhỏ ở xa và bị che tốt hơn |
| **Local** (CPU là đủ) | Đọc cache, chiếu BEV, bám vật, cảnh báo, vẽ UI. Dựng nền LiDAR. Quay MP4 dự phòng | Màn hình demo không phụ thuộc vào kết nối Colab |
| **Local** (RTX 4050) | Chế độ Live với `yolo11n` | Đi qua Colab thì webcam trễ vài trăm ms, làm hỏng M3 và cảnh báo |

- Định dạng cache: `cache/<dataset>/<scene>/<model>.jsonl`, mỗi dòng là `{t, cam, boxes: [{cls, conf, xyxy}]}`. Có cache rồi thì Replay chạy lại được bao nhiêu lần cũng ra cùng kết quả.
- Lúc demo, có thể chạy thật một đoạn Phenikaa 5 s trên Colab để cho thấy hệ thống chạy trực tiếp: in FPS và hiện khung kết quả. Đây là phần thêm; bản chính vẫn là Replay local đọc cache.
- Chi tiết các script Colab nằm ở [docs/COLAB.md](docs/COLAB.md). `up.sh` cần thêm biến `WITH_PHENIKAA=1`: đóng gói 6 thư mục `CAM_P_*`, `label/`, `ego_pose/` và `Calib Information/` của 2 scene (khoảng 355 MB). Dùng `tar cf` không nén, vì ảnh JPEG đã nén sẵn.

## 4. Pipeline

```
khung hình của N camera (t_capture)
  → YOLO (COCO): box + lớp + confidence, từng camera             [HỌC]
  → gộp person + motorcycle/bicycle chồng nhau thành "rider"      [BIỂU DIỄN]
  → điểm tiếp đất: giữa cạnh đáy box → khử méo → tia → cắt mặt đường  [HÌNH HỌC]
      dự phòng khi đáy box chạm mép ảnh: d = f · H_lớp / h_box
  → đổi hệ camera → hệ xe (ngoại tham số)                        [HÌNH HỌC]
  → gộp vật trùng giữa các camera chồng vùng nhìn                 [BIỂU DIỄN]
  → bù chuyển động xe (ego pose) + bám vật + Kalman [x, y, vx, vy]  [THỜI GIAN]
  → vùng SÁT SƯỜN / TẠT ĐẦU / PHÍA TRƯỚC (TTC)                   [THỜI GIAN]
  → mức cảnh báo + cờ "KHÔNG CHẮC"                               [BẤT ĐỊNH]
  → vẽ: lưới 6 camera, BEV 360°, FPS, độ trễ
  → log CSV từng khung                                            [DỮ LIỆU]
```

Hệ tọa độ xe: x hướng về phía trước, y sang trái, z hướng lên.

### 4.1 Hình học

- **Khử méo:** chỉ khử méo các điểm cần dùng bằng `cv2.undistortPoints`, không khử méo cả ảnh. Méo của Phenikaa khá mạnh (k1 ≈ −0,34). Bỏ bước này thì vật ở rìa ảnh bị đặt sai chỗ.
  - `CAM_P_F/FL/FR/B`: mô hình 5 hệ số, f ≈ 1845, ảnh 1920×1536.
  - `CAM_P_L/R`: mô hình rational 8 hệ số, f ≈ 871 (góc rộng).
- **Ngoại tham số:**
  - Phenikaa: `Sensor_Extrinsics.json`. Tính tay vài box thì thấy ma trận có vẻ là LiDAR → camera. **Phải kiểm tra trong 15 phút đầu:** chiếu nhãn vào `CAM_P_F` rồi so với `COMPLEX_CITY_projected_3d_box_5x2.mp4`. Hệ xe của Phenikaa lấy bằng hệ LiDAR, vì nhãn nằm trong hệ LiDAR.
  - nuScenes: lấy `calibrated_sensor` (camera → ego). Hệ ego có gốc trên mặt đất.
- **Mặt đường:** giả định đường phẳng.
  - nuScenes: mặt đường là z = 0 trong hệ ego.
  - Phenikaa: lấy z_g bằng cách fit mặt phẳng trên điểm LiDAR thấp quanh xe, làm một lần như hiệu chuẩn lúc lắp camera. Ghi rõ là hiệu chuẩn. Camera đặt cao khoảng 1,9 m so với gốc LiDAR (tính từ ngoại tham số).
- **Giới hạn tầm:** điểm tiếp đất ở xa hơn 30 m thì tia gần song song với mặt đường, nên sai số rất lớn. Bật cờ KHÔNG CHẮC và không cảnh báo đỏ.

### 4.2 Tham số (giả định thiết kế, không phải số đo)

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| Model | Colab: `yolo11n.pt` và `yolo11m.pt`; Live: `yolo11n.pt` | Ultralytics, lớp COCO |
| Lớp dùng | person, bicycle, car, motorcycle, bus, truck | |
| Ghép lớp với nhãn | rider ↔ Phenikaa `Rider`, nuScenes `vehicle.motorcycle/bicycle`; person ↔ `Pedestrian` / `human.pedestrian.*`; car/bus/truck ↔ `Car` / `vehicle.car/bus/truck` | nuScenes không đánh nhãn người lái thành người đi bộ, nên gộp rider khớp với cả hai bộ nhãn |
| Gộp rider | box person có điểm giữa cạnh đáy nằm trong box motorcycle/bicycle, hoặc IoU > 0,3 | điểm tiếp đất lấy từ box xe |
| Chiều cao dự phòng H | person 1,70 m; rider 1,60 m; car 1,50 m; bus 3,20 m; truck 3,00 m | chỉ dùng khi đáy box chạm mép ảnh |
| Confidence tối thiểu | 0,40 | |
| Gộp vật trùng giữa camera | cùng lớp, cách nhau < 1,0 m trên BEV | lấy trung bình vị trí, giữ confidence cao hơn |
| Bám vật | ghép gần nhất trên BEV, cổng 1,5 m | không dùng IoU vì vật đi qua nhiều camera |
| Kalman | trạng thái [x, y, vx, vy], vận tốc không đổi; R lấy từ phần dư của M2 (Replay) và M1 (Live) | |
| Khung xe | hình chữ nhật, kích thước và vị trí đặt trong config riêng cho từng dataset | Phenikaa: dùng hộp thân xe như `keep_mask` trong P-115 |
| **SÁT SƯỜN** | vật nằm trong dải ±1,0 m quanh hai bên thân xe, theo x trong chiều dài xe ± 1 m | |
| **TẠT ĐẦU** | vật ở phía trước 0–10 m, có vy hướng vào làn xe, thời gian để vào làn (\|y\| < W/2 + 0,3 m) < 1,5 s | |
| **PHÍA TRƯỚC** | vật trong làn phía trước; TTC = x / max(−vx, ε); cảnh báo khi < 2,5 s, nguy hiểm khi < 1,5 s | Live chỉ có vùng này |
| Cờ "KHÔNG CHẮC" | confidence < 0,55; HOẶC box chạm mép ảnh; HOẶC điểm tiếp đất xa > 30 m; HOẶC hai camera lệch nhau > 1,5 m; HOẶC sai lệch Kalman > 3σ | khi có cờ: hiện viền vàng, không phát cảnh báo đỏ |

### 4.3 Hệ số camera cho Live

Hiệu chuẩn bằng bàn cờ in sẵn hoặc hiện trên màn hình điện thoại, với `cv2.calibrateCamera` và 15–20 ảnh. Lưu vào `calib/webcam.json`. Nếu không kịp, dùng dự phòng fx = (W/2) / tan(HFOV/2) với HFOV khoảng 70°, và ghi rõ là ước lượng. Live dùng công thức chiều cao d = f·H/h, vì webcam đặt trên bàn nên không có mặt đường chuẩn.

## 5. Giao diện (local)

- **Trái:** lưới 6 camera (2×3), có box, lớp, màu cảnh báo. Camera nào đang có cảnh báo thì có viền đậm.
- **Phải:** BEV 360°.
  - Xe ở giữa, ô lưới 1 m, các vùng SÁT SƯỜN / TẠT ĐẦU / PHÍA TRƯỚC tô nhạt.
  - Chấm vật kèm vệt quỹ đạo 1 s gần nhất và mũi tên vận tốc.
  - Nền là bản đồ LiDAR của scene (tô màu theo độ cao), dựng ở local.
  - Bật/tắt lớp chấm "đáp án" từ nhãn để thấy ngay sai số.
- **Thanh dưới:** FPS, độ trễ, số vật đang bám, model đang dùng, số cảnh báo theo từng vùng.
- **Live:** chỉ có một ảnh webcam và nửa BEV phía trước.
- Giao diện là cửa sổ OpenCV. Streamlit chỉ làm nếu còn thời gian.

## 6. Số đo (bắt buộc ≥ 1, làm cả bốn)

| Mã | Đo gì | Cách đo | Báo |
|---|---|---|---|
| **M1** | Sai số khoảng cách trên webcam | Một thành viên đứng ở 1, 2 và 3 m (đo bằng thước dây), mỗi mốc 30 khung | sai số tuyệt đối trung bình và độ lệch chuẩn ở từng mốc; độ lệch chuẩn khi đứng yên là R của Kalman ở Live |
| **M2** | Sai số vị trí trên BEV so với nhãn LiDAR | Ghép detection với nhãn **trên ảnh**, không ghép trên BEV, để không dùng chính thứ đang đo: chiếu box 3D nhãn vào từng camera, IoU ≥ 0,5. nuScenes lọc `visibility` ≥ 2. Phenikaa không có visibility, nên chỉ giữ nhãn có ≥ 50% box chiếu nằm trong ảnh. Sai số = khoảng cách giữa điểm BEV ước lượng và tâm đáy box nhãn | sai số theo dải 0–5, 5–10, 10–20 và 20–30 m; tách theo nhóm camera (trước / hông / sau); tách Phenikaa và nuScenes; tách ngày và đêm (nuScenes); `yolo11n` so với `yolo11m`; số cặp ghép được |
| **M3** | Thời gian | Live (local): đo FPS và độ trễ từ lúc chụp đến lúc ra quyết định. Colab: thời gian suy luận cho một khung 6 camera, theo từng model | FPS; độ trễ p50/p95 (ms); ms mỗi khung 6 camera. Ghi rõ số Colab không phải độ trễ end-to-end |
| **M4** | Cảnh báo SÁT SƯỜN có đúng không | Ở mỗi khung, nhãn cho biết vùng SÁT SƯỜN có vật hay không (footprint nhãn giao với vùng). So với việc hệ thống có cảnh báo hay không. Không cần track ID của nhãn | precision và recall theo khung, cho Phenikaa (400 khung) và nuScenes (404 keyframe); báo hai bản: tính cả khung có cờ KHÔNG CHẮC và bỏ chúng ra |

Chưa đo thì ghi "chưa đo". Không điền số ước lượng vào bảng.

TẠT ĐẦU và PHÍA TRƯỚC chưa có số đo tự động, vì nhãn không có track ID nên không tính được vận tốc đáp án. Nói rõ điều này khi demo.

## 7. Ca lỗi (bắt buộc ≥ 1, chuẩn bị sẵn 4)

| Ca | Cách tái hiện | Lý do hệ thống sai |
|---|---|---|
| **L1: xe máy nối đuôi, che nhau** | Phenikaa COMPLEX CITY, chọn khung có cụm xe máy dày đặc | Đáy box của xe phía sau bị xe phía trước che, nên điểm tiếp đất bị đẩy ra xa hoặc lệch. YOLO cũng gộp hoặc bỏ sót xe |
| **L2: xe máy sát hông bị cắt mép** | Phenikaa, camera `CAM_P_L/R`, xe máy chạy sát thân xe | Đáy box chạm mép ảnh nên không có điểm tiếp đất. Công thức chiều cao cũng sai vì box bị cắt. Cờ KHÔNG CHẮC phải bật; nếu không bật thì đó là lỗi thật cần nói |
| **L3: ban đêm** | nuScenes scene-1077, scene-1094, scene-1100 | YOLO học trên COCO, phần lớn là ảnh ban ngày, nên bỏ sót hoặc confidence thấp. M2 tách ngày và đêm để thấy rõ chênh lệch |
| **L4: nhân đôi hoặc ghép rider sai** | Vật đi qua vùng chồng giữa `CAM_P_F` và `CAM_P_FL/FR`; người đứng cạnh xe máy đỗ | Hai camera cho hai vị trí lệch nhau hơn ngưỡng gộp, nên một xe thành hai chấm. Người đi bộ đứng cạnh xe máy đỗ bị gộp thành rider |
| (Live) L5: người ngồi hoặc cúi | Thành viên ngồi xuống ở mốc 2 m | h_box giảm khoảng một nửa trong khi H vẫn là 1,7 m, nên d bị ước gấp khoảng 2 lần |

**Giới hạn đã chứng minh (nói thẳng khi demo):**
- giả định đường phẳng; dốc, gờ giảm tốc hoặc xe nghiêng sẽ làm lệch điểm tiếp đất;
- chỉ có camera, không có radar;
- Phenikaa chỉ có 2 scene × 20 s; nhãn không có visibility và track ID;
- Replay chạy trên dữ liệu ghi sẵn; chưa đo độ trễ end-to-end trên xe thật;
- Live chỉ đo ở 1–3 m;
- nuScenes mini quay ở Boston và Singapore.

## 8. Bảy trụ cột: nằm ở đâu và vì sao chọn cách này

| Trụ cột | Ở đâu | Vì sao không chọn cách khác |
|---|---|---|
| Học | YOLO COCO, `yolo11n` và `yolo11m` | Không tự huấn luyện vì chỉ có 2 giờ. So hai cỡ model để thấy đánh đổi giữa tốc độ và độ chính xác. Giới hạn dữ liệu COCO được nói rõ ở L3 |
| Hình học | khử méo; điểm tiếp đất cắt mặt đường; ngoại tham số camera → xe; dự phòng f·H/h | Điểm tiếp đất cho cả vị trí ngang lẫn khoảng cách và không cần giả định chiều cao, nên hợp với xe máy sát bên. Không dùng model đoán độ sâu vì không giải thích được và chạy chậm |
| Bất định | cờ "KHÔNG CHẮC"; R của Kalman lấy từ M1 và M2 | Cảnh báo kêu nhầm làm tài xế mất tin tưởng, nên thà báo "không chắc" còn hơn báo đỏ nhầm |
| Biểu diễn | box → rider → điểm BEV (x, y) trong hệ xe → trạng thái [x, y, vx, vy] | Một hệ tọa độ chung cho 6 camera thì gộp được vật trùng, và bám được vật khi nó đi từ camera này sang camera khác |
| Thời gian | bù chuyển động xe bằng ego pose; Kalman; TTC và thời gian vào làn; độ trễ | Lấy hiệu vị trí thô giữa hai khung thì nhiễu, cảnh báo nhảy loạn. Không bù chuyển động xe thì vật đứng yên trông như đang lao tới |
| Dữ liệu | cache detection; log CSV; Phenikaa + nuScenes | Có cache thì Replay tái lập được. Phenikaa là dữ liệu đường Việt Nam, đúng bối cảnh của VinFast |
| Bằng chứng | M1–M4, L1–L5, giới hạn | Nhãn LiDAR là đáp án khách quan, không cần nhãn tay |

## 9. Impact (điền khi có nguồn, không đoán)

Khung tính để nói trong 2 phút:
- **Kiểm thử:** "Một kỹ sư xem lại N giờ log mỗi tuần để tìm ca cảnh báo sai. Bộ log CSV và chế độ Replay lọc ngay các khung có cờ hoặc kêu sai so với nhãn, nên thời gian chỉ còn M." N và M lấy từ phỏng vấn hoặc giả định ghi rõ.
- **An toàn:** chỉ dẫn số liệu có nguồn công khai (ví dụ thống kê tai nạn liên quan xe máy ở Việt Nam, hoặc nghiên cứu về cảnh báo điểm mù) và ghi nguồn lên slide. Không tự đặt con số.
- **Mở rộng:** thêm radar góc trên xe VinFast thật; tinh chỉnh YOLO trên dữ liệu xe máy Việt Nam; chạy trên phần cứng nhúng.
- **Rủi ro:** kêu nhầm trong giờ cao điểm; ban đêm; đường không phẳng.

## 10. Kế hoạch 2 giờ (3 người)

Lịch chi tiết, giao kèo giữa các vai, video dự phòng và phần nói của từng người nằm ở [docs/PHAN_CONG.md](docs/PHAN_CONG.md). Giờ ghi theo lịch của ban tổ chức: build từ 0:15 đến 2:15, giảng viên kiểm tra lúc 1:15.

| Giờ | Core (Khánh): hình học + Colab + video | BE: lõi hệ thống | FE: hiển thị + trình bày |
|---|---|---|---|
| 0:00–0:15 | `up.sh` với `WITH_PHENIKAA=1`, khung repo | `contracts.py` | `mock_state.py` |
| 0:15–0:55 | calib, **kiểm tra chiều ngoại tham số**, cache `yolo11n` Phenikaa, `geometry.py`, `PhenikaaSource` | `NuScenesSource`, `fuse.py`, `app.py` + log CSV | `ui.py`, `bev.py`, hiệu chuẩn webcam |
| 0:55–1:15 | **ghép trên máy demo: Replay Phenikaa hiện detection của 6 camera trên BEV; Live thô** | ← | ← |
| 1:15–2:00 | M2, cache `yolo11m` + nuScenes, M3 Colab, M4, L3; video V1; `stop.sh` | `tracker.py`, `zones.py`, Live đầy đủ, M3 Live | nền LiDAR, phím tắt, `--record`, M1, slide |
| 2:00–2:15 | **đóng băng code**; video V2 | chỉ sửa lỗi | điền số vào slide, tập demo |
| 2:15–2:30 | video V3 (Live) | thử Live ở chỗ demo | bấm giờ 10 phút |

Nếu chậm mốc 1:15: bỏ nuScenes 6 camera (chỉ giữ `CAM_FRONT` cho L3), bỏ TẠT ĐẦU, bỏ nền LiDAR và Streamlit. Không bỏ Phenikaa, Live và cờ KHÔNG CHẮC.

## 11. Kịch bản 10 phút

1. **1 phút: bài toán.** Xe máy vượt sát sườn và tạt đầu là tình huống thường gặp ở Việt Nam. Người dùng là kỹ sư kiểm thử ADAS và tài xế.
2. **4 phút: demo.**
   - Replay Phenikaa COMPLEX CITY: lưới 6 camera và BEV 360°. Chỉ một xe máy vượt sát sườn → SÁT SƯỜN; một xe tạt đầu → TẠT ĐẦU; một xe bị cắt mép → viền vàng KHÔNG CHẮC (L2).
   - Bật lớp đáp án: chấm ước lượng nằm cạnh chấm nhãn LiDAR.
   - (Tùy chọn) Chạy thật một đoạn 5 s trên Colab, so `yolo11n` với `yolo11m`.
   - Live: mời giám khảo bước về phía webcam; TTC giảm, cảnh báo vàng rồi đỏ.
   - Một scene đêm của nuScenes cho thấy L3.
3. **2 phút:** bảng M1–M4; một ca lỗi kèm lý do; 7 trụ cột; impact.
4. **3 phút: hỏi đáp.** Mỗi người trả lời được phần của mình (mục 10).

Nếu Colab hoặc mạng hỏng: Replay vẫn chạy local từ cache đã tải về. Nếu cả local hỏng: chiếu MP4 dự phòng.

## 12. Dữ liệu an toàn và giấy phép

- **Phenikaa:**
  - Chỉ dùng khi chủ dữ liệu đồng ý, gồm cả việc đưa lên Colab (tài khoản Google bên ngoài) và chiếu ảnh lên slide hoặc video demo.
  - Không commit vào repo. Không lưu lên Drive.
  - Chạy `stop.sh` sau khi xong để xóa VM.
- **nuScenes mini:** giấy phép phi thương mại CC BY-NC-SA 4.0 (xem `LICENSE` trong thư mục dữ liệu). Không commit vào repo public.
- `data/` và `cache/` để trong `.gitignore`. README hướng dẫn tự lấy dữ liệu.
- Live chỉ quay thành viên đội. Không quay người ngoài, bệnh nhân hay sinh viên khác.
- Không commit `.env`, key hay file của dự án khác ngoài phần code đã liệt kê trong `docs/REUSE_P115.md`.

## 13. Cấu trúc repo đề xuất

```
src/
  calib.py         đọc K, hệ số méo, ngoại tham số (Phenikaa, nuScenes, webcam)
  sources.py       PhenikaaSource, NuScenesSource, WebcamSource (khung N camera + calib + ego pose + đáp án)
  detect.py        YOLO, lọc lớp và confidence
  detect_cache.py  chạy trên Colab: detect mọi khung → cache/<dataset>/<scene>/<model>.jsonl
  geometry.py      khử méo, điểm tiếp đất, camera → xe, dự phòng f·H/h
  fuse.py          gộp rider, gộp vật trùng giữa camera
  tracker.py       bám vật trên BEV, bù ego pose, Kalman [x, y, vx, vy]
  zones.py         vùng SÁT SƯỜN / TẠT ĐẦU / PHÍA TRƯỚC, TTC, cờ KHÔNG CHẮC
  bev.py           vẽ BEV 360°, nền LiDAR, lớp đáp án
  app.py           vòng lặp chính, UI OpenCV, log CSV
  eval_bev.py      M2 → results/m2_<dataset>_<model>.json
  eval_zones.py    M4 → results/m4_<dataset>_<model>.json
config/            kích thước khung xe, ngưỡng vùng theo dataset
calib/webcam.json
cache/             detection từ Colab (không commit)
results/           m1.csv, m2_*.json, m3.json, m4_*.json, log_*.csv
colab/             script Colab (docs/COLAB.md)
docs/REUSE_P115.md, docs/COLAB.md
```

Lệnh chạy dự kiến:
- Colab: `python -m src.detect_cache --dataset phenikaa --root /content/phenikaa --model yolo11n.pt --out cache/`
- Colab: `python -m src.eval_bev --dataset nuscenes --root /content/nusc --cache cache/ --model yolo11n.pt --out results/m2_nuscenes_yolo11n.json`
- Local: `python -m src.app --source phenikaa --root <Phenikaa> --scene "COMPLEX CITY" --cache cache/`
- Local: `python -m src.app --source nuscenes --root <nuScenes mini> --scene scene-1094 --cache cache/`
- Local: `python -m src.app --source webcam`
