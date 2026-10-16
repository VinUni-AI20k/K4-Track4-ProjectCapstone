# Phối hợp phát triển

Phần Quý đã triển khai detector, bộ trạng thái và vòng chạy; xem `docs/implementation.md`.
Phần overlay, logger và đánh giá của Tuyên vẫn là khung trong bản này.
Phân công và giao diện dưới đây đã được chốt để hai người làm song song.

| Người | Branch | File phụ trách |
| --- | --- | --- |
| Quý | `feature/eye-detection` | `app.py`, `src/eye_detector.py`, `src/state_machine.py`, `tests/test_state_machine.py` |
| Tuyên | `feature/demo-evaluation` | `src/overlay.py`, `src/event_logger.py`, `scripts/evaluate.py`, tài liệu đánh giá/demo |

## Hợp đồng đã chốt

Quý cung cấp bộ xử lý nhận khung hình và `timestamp_s`, trả về các trường:

| Trường | Ý nghĩa |
| --- | --- |
| `ear_left`, `ear_right`, `ear` | Giá trị số hoặc trống khi không hợp lệ |
| `valid` | Có đủ dữ liệu quyết định hay không |
| `state` | CALIBRATING / OPEN / CLOSING / ALERT / UNKNOWN |
| `closed_duration_s` | Thời lượng mắt đóng liên tục |
| `close_threshold`, `open_threshold` | Ngưỡng đã hiệu chỉnh hoặc trống |
| `alert_event` | Chỉ đúng ở lần phát sinh sự kiện mới |

Kiểu chung nằm trong `src/contracts.py`. Cả hai import trực tiếp, không sao chép
hoặc tự thay đổi tên trường. API thống nhất như sau:

```python
# Quý — src/eye_detector.py
EyeDetector(model_path: str)
EyeDetector.detect(frame) -> EyeObservation
EyeDetector.close() -> None

# Quý — src/state_machine.py
DriverStateMachine(*, alert_after_s: float = 1.5,
                   calibration_samples: int = 60,
                   close_ratio: float = 0.65,
                   open_ratio: float = 0.75,
                   max_gap_s: float = 0.5)
DriverStateMachine.update(observation: EyeObservation,
                          timestamp_s: float) -> StateDecision
DriverStateMachine.reset() -> None

# Tuyên — src/overlay.py
draw_overlay(frame, result: FrameResult)  # Trả ảnh BGR mới, không sửa frame gốc

# Tuyên — src/event_logger.py
EventLogger(csv_path: str, metadata: dict)
EventLogger.write(result: FrameResult) -> None
EventLogger.close() -> None
```

Các mặc định là tham số phát triển ban đầu, cần kiểm chứng trước khi đánh giá.
`reset()` xóa hiệu chỉnh và bộ đếm. `frame` là ảnh BGR NumPy từ OpenCV;
detector tự đổi RGB khi cần. Mốc vẽ là tọa độ pixel trên ảnh gốc; chỉ phản chiếu
toàn bộ ảnh sau khi vẽ nếu muốn. Các module dùng cùng cơ sở thời gian:
webcam lấy đồng hồ đơn điệu trừ thời điểm đầu; video lấy thời gian video.
`timestamp_s` tăng dần; vòng chạy mới phải tạo/reset bộ trạng thái.

Quý ghép `EyeObservation` + `StateDecision` vào `FrameResult` trong `app.py`.
Tuyên không tự suy ra trạng thái lại trong overlay/logger. Bộ logger dùng
`CSV_FIELDS`, ghi enum bằng `.value`, số thiếu thành ô trống, bool thành 0/1;
lưu metadata ra file cùng tên CSV với đuôi `.json`. Metadata chứa cấu hình,
ngưỡng, phiên bản model/thư viện và nguồn vào; Quý cung cấp tại điểm tích hợp.
Ngưỡng được lấy từ kết quả hiệu chỉnh trước khi ghi phiên đánh giá.

## Tuyên bắt đầu ngay, không chờ Quý

1. Import `FrameResult` và `CSV_FIELDS` từ `src.contracts`.
2. Dùng `mock_results()` từ `scripts.mock_results` để làm overlay/logger.
   Chuỗi mẫu có đủ 5 trạng thái, một sự kiện mới và phục hồi sau mất quan sát.
3. Tạo ảnh BGR trống hoặc ảnh tự quay để kiểm tra overlay; vị trí mốc mẫu chỉ là minh họa.
4. Chuẩn bị công cụ đánh giá, mẫu báo cáo và kịch bản demo song song.
5. Khi Quý trả đúng `FrameResult`, thay nguồn mẫu bằng kết quả thực mà không đổi giao diện module.

Chạy thử nguồn mẫu tại gốc repo (không cần MediaPipe/OpenCV):

```bash
python -m scripts.mock_results
```

**Dữ liệu mẫu chỉ dùng phát triển.** Số đo, ca lỗi và video dự phòng phải chờ
luồng nhận diện thật, sau đó cả hai cùng quay, gán nhãn và đánh giá.
Quý phụ trách tích hợp `app.py`; Tuyên không cần sửa file này để làm module riêng.
Hợp đồng chung do Quý quản lý khi tích hợp; thay đổi phải cập nhật tài liệu và báo
cho Tuyên trước khi merge, không đổi âm thầm trên một nhánh.

CSV tối thiểu: `frame_id,timestamp_s,ear_left,ear_right,ear,valid,state,closed_duration_s,alert_event,processing_ms`.
Lưu cấu hình và ngưỡng cùng từng lượt chạy. `processing_ms` là thời gian xử lý phần mềm,
không đại diện cho độ trễ từ camera đến màn hình.

## Nhận mã nguồn

Lần đầu:

```bash
git clone https://github.com/quycute2003/K4-Track4-ProjectCapstone.git
cd K4-Track4-ProjectCapstone
```

Nếu đã clone, lưu công việc đang làm trước rồi cập nhật `main`:

```bash
git switch main
git pull --ff-only origin main
```

Tuyên tạo branch nhiệm vụ nếu chưa tồn tại:

```bash
git switch -c feature/demo-evaluation
```

Nếu branch đã tồn tại, dùng `git switch feature/demo-evaluation`.
Commit và push branch của mình; kiểm tra thay đổi trước khi merge vào `main`.
Chỉ người tích hợp chỉnh `app.py`, tránh hai người sửa cùng file.
