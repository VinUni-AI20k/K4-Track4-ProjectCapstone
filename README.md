# K4 Track 4 Project Capstone — Vin Perception Hackathon

Trang đề bài hackathon cuối khóa Track 4 (Computer Vision & Robotics): 2 giờ build, 10 phút demo mỗi team, đề tài gắn với hệ sinh thái Vin.

- `index.html`: trang đề bài (một file, không cần build). Mở trực tiếp bằng trình duyệt.

Nội dung gồm hướng đề tài gợi ý, bốn yêu cầu của mỗi demo, bảy trụ cột Track 4, công cụ gợi ý, thang điểm, lịch trình, checklist trước demo và FAQ. Ngày giờ, địa điểm, giám khảo, giải thưởng sẽ được ban tổ chức cập nhật.

---

# Đề tài đã chọn: VinFast DMS — cảnh báo tài xế ngủ gật bằng webcam

**Vì sao chọn đề tài này:** khả thi nhất trong 2 giờ. Chỉ cần webcam laptop, model pretrained (MediaPipe Face Landmarker, chạy CPU ~12 ms/khung), không cần train, không cần phần cứng. Dễ có số đo kiểm chứng và ca lỗi để phân tích, và giám khảo có thể tự ngồi vào thử tại chỗ.

**Người dùng:** tài xế xe VinFast, đặc biệt tài xế taxi/xe dịch vụ chạy ca dài và ca đêm. **Nỗi đau:** ngủ gật 1–2 giây ở 60 km/h là xe đi mù ~17–33 m. Hệ thống phát hiện mắt nhắm quá lâu, dấu hiệu buồn ngủ tích lũy (PERCLOS, ngáp) và việc không nhìn đường, rồi kêu cảnh báo.

## Chạy

```bash
pip install -r requirements.txt
python run_dms.py                 # webcam; lần đầu tự tải model (~3,7 MB) vào models/
python run_dms.py --protocol      # webcam + kịch bản đo có ground truth (khoảng 1 phút)
python evaluate.py logs/session-*.csv --plot ear.png   # số đo, quét ngưỡng, biểu đồ
python -m pytest tests            # 11 test logic + hình học trên dữ liệu tổng hợp
```

Phím: `q` thoát, `c` hiệu chuẩn lại (khi đổi người lái), `p` chạy kịch bản đo.
Video dự phòng: `python run_dms.py --source clip.mp4` (thêm `--headless` để chỉ xử lý và ghi log).

5 giây đầu là **hiệu chuẩn**: nhìn thẳng, mở mắt bình thường. Mọi ngưỡng sau đó tính theo chính người lái này.

## Hệ thống

```
webcam ─► Face Landmarker (pretrained, 478 điểm) ─► đặc trưng ─► Monitor ─► cảnh báo + âm thanh
                                                   EAR, MAR,      hiệu chuẩn,       │
                                                   yaw/pitch      hysteresis,       ▼
                                                   (solvePnP)     cửa sổ thời gian  logs/*.csv ─► evaluate.py (replay)
```

| File | Vai trò |
|---|---|
| `dms/features.py` | Landmark → EAR (độ mở mắt), MAR (độ mở miệng), hướng đầu bằng `solvePnP` |
| `dms/monitor.py` | Logic trạng thái tài xế, không phụ thuộc camera (test và replay được) |
| `dms/evaluation.py` | Kịch bản đo, đọc log, replay, tính chỉ số |
| `run_dms.py` | App demo: webcam/video, overlay, âm thanh, ghi log |
| `evaluate.py` | Báo cáo số đo từ log, quét ngưỡng trên cùng bản ghi, vẽ biểu đồ |

## Trụ cột Track 4 và vị trí trong hệ thống

| Trụ cột | Nằm ở đâu | Vì sao làm vậy |
|---|---|---|
| **Biểu diễn** | `features.py`: khuôn mặt → 4 con số (EAR, MAR, yaw, pitch) | EAR không phụ thuộc kích thước mặt trong ảnh (tỉ số), nên không cần biết tài xế ngồi xa hay gần. |
| **Hình học** | `features.head_pose`: `solvePnP` giữa mô hình mặt 3D chung và 6 landmark, ma trận camera ước lượng (f ≈ chiều rộng ảnh) | Lấy góc từ hướng mũi thay vì phân rã Euler (phân rã Euler làm mất dấu yaw — đã gặp và sửa, xem ca lỗi 3). Cho PnP một ước lượng ban đầu "nhìn về camera" để không nhảy sang nghiệm gương. |
| **Bất định** | `monitor.py`: ngưỡng theo từng người (median EAR lúc hiệu chuẩn × 0,70), hysteresis (đóng < 0,70, mở > 0,80), trạng thái `UNCERTAIN` khi quay đầu > 25° | Ngưỡng cố định 0,2 sai với người mắt hẹp. Khi quay đầu, mắt xa bị co ngắn nên EAR giảm dù mắt mở: hệ thống *từ chối kết luận* thay vì báo ngủ gật giả. PERCLOS chỉ cảnh báo khi đã quan sát ≥ 50% cửa sổ. |
| **Thời gian** | Ngủ gật = nhắm liên tục ≥ 1,0 s; chớp mắt = ≤ 0,5 s; PERCLOS = tỉ lệ thời gian nhắm trong cửa sổ 30 s, có trọng số theo thời gian (khung bị rớt không làm lệch) | Quyết định dựa trên thời lượng chứ không dựa trên số khung, nên đúng cả khi FPS dao động. Độ trễ xử lý được đo và ghi log mỗi khung. |
| **Dữ liệu** | Log CSV mỗi khung lưu đặc trưng thô, không lưu quyết định | Có thể replay để thử ngưỡng khác trên đúng bản ghi đó (`evaluate.py` quét 12 cấu hình). Không lưu ảnh nào. |
| **Bằng chứng** | Kịch bản đo `--protocol`: 8 lần bíp cao "nhắm mắt 2 s", bíp trầm "mở", xen giữa là 4–7 s mở mắt chớp tự nhiên | Ground truth đến từ kịch bản chứ không từ chính hệ thống. Đo: tỉ lệ phát hiện, cảnh báo giả/phút, độ trễ cảnh báo, precision/recall trạng thái mắt theo khung. |

## Bằng chứng

Đã kiểm chứng trên máy phát triển (chưa có số đo webcam người thật — team cần chạy `--protocol` và điền vào đây trước khi demo):

- Test logic: chớp mắt 0,2 s không báo; nhắm 1,5 s báo sau 1,0 s (±1 khung); quay đầu 40° với mắt "nhắm" → `UNCERTAIN` rồi `DISTRACTED`, không báo ngủ gật; mất mặt 2,5 s → `NO_FACE`; diễn viên tổng hợp phản xạ 0,3 s → 4/4 phát hiện, 0 báo giả, độ trễ 1,3 s.
- Hình học: chiếu mô hình 3D với yaw/pitch đã biết (±30°, ±20°, kết hợp) → `head_pose` khôi phục sai số < 1°.
- Pipeline thật trên video 14 s (ảnh mặt tĩnh + 3 s khung đen): 30 FPS, xử lý p50 11,8 ms / p95 13,9 ms trên CPU, báo `NO_FACE` đúng đoạn khung đen.

Mẫu điền khi demo (từ `evaluate.py`):

| Chỉ số | Kết quả |
|---|---|
| Ngủ gật được phát hiện | _ / 8 |
| Cảnh báo giả / phút mở mắt | _ |
| Độ trễ cảnh báo (từ tiếng bíp) | _ s (gồm phản xạ người + quy tắc 1,0 s) |
| Precision / recall trạng thái mắt theo khung | _ / _ |
| Độ trễ xử lý p95 | _ ms |

## Ca lỗi (đã biết, nên chủ động cho xem)

1. **Kính râm / kính phản sáng.** Landmark mắt vẫn được model "đoán" ra nhưng không nhìn thấy mắt thật; EAR không thay đổi khi nhắm → bỏ sót ngủ gật. Lý do: model pretrained ước lượng hình dạng mặt hợp lý ngay cả khi mắt bị che. Xe thật dùng camera hồng ngoại xuyên qua kính râm.
2. **Quay đầu nhiều (> 25°) hoặc cúi xuống điện thoại.** EAR không còn tin được; hệ thống chuyển `UNCERTAIN` và chỉ cảnh báo mất tập trung sau 2 s. Tức là ngủ gật *trong lúc* đang quay đầu sẽ không được báo là ngủ gật (đánh đổi có chủ đích để tránh báo giả).
3. **Góc đầu tuyệt đối bị lệch.** Trên ảnh thử, `solvePnP` với mô hình mặt chung cho yaw ≈ 37° trong khi ma trận pose của MediaPipe cho ≈ 20°. Hệ thống chỉ dùng góc *tương đối* so với lúc hiệu chuẩn nên vẫn hoạt động, nhưng ngưỡng 30° không phải 30° thật. Trước demo nên kiểm: quay đầu tới một mốc dán sẵn ở 30° và xem giá trị yaw. Khắc phục đúng: hiệu chuẩn nội tại camera (bàn cờ/ArUco).
4. **Phiên bản đầu bị lỗi nghiệm gương PnP:** cùng một ảnh tĩnh, yaw nhảy +37° ↔ −42° giữa các khung → sẽ báo mất tập trung giả. Sửa bằng ước lượng ban đầu (xem bảng trụ cột).
5. **Thiếu sáng / ngược sáng:** landmark rung, EAR nhiễu. Hysteresis giảm nhấp nháy nhưng không khắc phục được ảnh tối.

## Tác động nếu triển khai ở Vin (ước lượng, các con số là giả định cần team thay bằng số liệu thật)

- **Quy định:** EU yêu cầu cảnh báo buồn ngủ và mất tập trung (DDAW/ADDW, Quy định 2019/2144) trên xe mới bán ra; VinFast bán xe ở châu Âu nên DMS là yêu cầu chứ không chỉ là tính năng.
- **Đội xe dịch vụ:** giả sử 10 000 tài xế taxi điện chạy ca 10 giờ. Nếu mỗi tài xế có 1 lần ngủ gật ≥ 1 s mỗi tuần, đó là ~520 000 lần/năm hệ thống có thể đánh thức. Chi phí phần mềm gần bằng 0 trên xe đã có camera trong cabin.
- **Mở rộng:** chạy trên camera cabin hồng ngoại; gửi PERCLOS theo ca về trung tâm điều phối để đề nghị nghỉ trước khi xảy ra ngủ gật.
- **Rủi ro:** cảnh báo giả làm tài xế tắt tính năng (vì vậy đo báo giả/phút); quyền riêng tư (hệ thống không lưu ảnh, chỉ lưu đặc trưng số); chưa kiểm chứng trên tài xế thật buồn ngủ — kịch bản đo chỉ là nhắm mắt có chủ đích.

## Kịch bản demo 10 phút

1. **1 phút** — Bài toán: tài xế ca đêm, 1 s ngủ gật = ~17 m đi mù ở 60 km/h.
2. **4 phút** — Demo trực tiếp: hiệu chuẩn → chớp mắt (không báo) → nhắm 2 s (báo, kêu) → quay đầu sang bên (UNCERTAIN, rồi MẤT TẬP TRUNG) → **mời giám khảo ngồi vào**, bấm `c` hiệu chuẩn lại cho họ.
3. **2 phút** — Bảng số đo từ `--protocol` + biểu đồ `ear.png`, ca lỗi kính râm (đeo kính râm và nhắm mắt trực tiếp), trụ cột, ước lượng tác động.
4. **3 phút** — Hỏi đáp.

Dữ liệu an toàn: chỉ thành viên đội tự đóng vai; log không chứa ảnh.
