# Phối hợp phát triển

Hiện là khung dự án, chưa có nhận diện, cảnh báo hoặc đánh giá hoạt động.
Phân công là đề xuất theo PLAN.md; mỗi người làm trên branch riêng.

| Người | Branch đề xuất | File phụ trách |
| --- | --- | --- |
| Quý | `feature/eye-detection` | `app.py`, `src/eye_detector.py`, `src/state_machine.py`, `tests/test_state_machine.py` |
| Tuyên | `feature/demo-evaluation` | `src/overlay.py`, `src/event_logger.py`, `scripts/evaluate.py`, tài liệu đánh giá/demo |

## Hợp đồng cần chốt trước khi viết

Quý cung cấp bộ xử lý nhận khung hình và `timestamp_s`, trả về các trường:

| Trường | Ý nghĩa |
| --- | --- |
| `ear_left`, `ear_right`, `ear` | Giá trị số hoặc trống khi không hợp lệ |
| `valid` | Có đủ dữ liệu quyết định hay không |
| `state` | CALIBRATING / OPEN / CLOSING / ALERT / UNKNOWN |
| `closed_duration_s` | Thời lượng mắt đóng liên tục |
| `close_threshold`, `open_threshold` | Ngưỡng đã hiệu chỉnh hoặc trống |
| `alert_event` | Chỉ đúng ở lần phát sinh sự kiện mới |

Hai người thống nhất tên hàm, kiểu dữ liệu và cách truyền mốc mắt trước khi tích hợp.
Tuyên không tự suy ra trạng thái lại trong overlay/logger.

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
