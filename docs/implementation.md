# Bàn giao phần Quý

## Đã triển khai

- `EyeDetector(model_path).detect(frame)` trả đúng `EyeObservation` trong hợp đồng chung.
- MediaPipe Tasks Face Landmarker, CPU, IMAGE mode, tối đa 2 mặt để từ chối đầu vào nhiều người.
- Lấy 6 mốc mỗi mắt, đổi từ tọa độ chuẩn hóa sang pixel trước khi tính EAR.
- Loại mốc không hữu hạn, nằm ngoài khung hình hoặc mắt có chiều rộng dưới 3 pixel.
- Bộ trạng thái hiệu chỉnh bằng trung vị 60 mẫu hợp lệ liên tiếp; ngưỡng đóng/mở mặc định bằng 0,65/0,75 lần tham chiếu.
- Mắt đóng khi EAR dưới ngưỡng đóng; chỉ mở lại khi EAR đạt ngưỡng mở. Khoảng giữa hai ngưỡng giữ quyết định trước để giảm dao động.
- Cảnh báo mới một lần mỗi chuỗi mắt đóng; mặc định sau 1,5 giây. `alert_after_s=0` hỗ trợ phương án cơ sở.
- Mất quan sát/khoảng cách hai mẫu vượt 0,5 giây → UNKNOWN và hủy chuỗi mắt đóng; giữ hiệu chỉnh đã hoàn thành. Hiệu chỉnh chưa xong thì xóa mẫu dở.
- `reset()` xóa hiệu chỉnh, bộ đếm và mốc thời gian. Camera mất kết nối được báo lỗi và đóng tài nguyên; không tự mở camera lại.
- Webcam dùng đồng hồ đơn điệu tương đối; video FPS cố định dùng `frame_id / source_fps`.
- Vòng chạy tích hợp, hiển thị tối thiểu, phát lại video, chế độ không mở cửa sổ và tải model có checksum.

EAR = `(distance(p2,p6) + distance(p3,p5)) / (2 × distance(p1,p4))`.
EAR tổng hợp là trung bình hai mắt. Công thức khoảng cách dùng thư viện chuẩn;
ảnh BGR và đầu vào MediaPipe dùng NumPy/OpenCV. Không dùng tọa độ x/y chuẩn hóa
trực tiếp vì chiều rộng và chiều cao ảnh có thể khác nhau.

API MediaPipe tham khảo: [Face Landmarker Python](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python).
IMAGE mode được chọn để giữ API `detect(frame)` và xử lý đồng bộ; chưa tận dụng tracking của VIDEO mode.

## Tuyên tích hợp như thế nào?

Giữ nguyên hợp đồng trong `src/contracts.py` và chữ ký trong `docs/development.md`.

- Khi `src.overlay.draw_overlay(frame, result)` đã có, `app.py` tự dùng thay hiển thị tối thiểu.
- Khi `src.event_logger.EventLogger(csv_path, metadata)` đã có, dùng `--log` để ghi.
- CSV bắt đầu từ khi hiệu chỉnh hoàn thành; metadata chứa tham chiếu, ngưỡng và cấu hình thực tế.
- Bấm R đóng log hiện tại; sau hiệu chỉnh lại ghi sang `run.part2.csv`, `run.part3.csv`… để không trộn các ngưỡng trong cùng phiên.
- Logger ghi enum bằng `.value`, dữ liệu thiếu thành ô trống và metadata cùng tên file với đuôi `.json`.
- Hiện `--log` báo rõ chưa có logger nếu module Tuyên vẫn là khung, không giả vờ đã ghi.

Không cần Tuyên đổi cấu trúc `FrameResult`. Phần overlay không quyết định trạng thái.

## Kiểm thử và giới hạn

Kiểm thử tự động gồm hình học trên ảnh không vuông, hiệu chỉnh, hysteresis, chớp mắt,
cảnh báo một lần, mất quan sát, dữ liệu lỗi, thay đổi FPS, thời gian video và đóng tài nguyên.
Các test dùng dữ liệu tổng hợp/camera giả, không phải số đo chất lượng nhận diện.

Kiểm tra đã chạy trong lần bàn giao:

- 29 kiểm thử tự động đạt; `pip check` không phát hiện phụ thuộc hỏng.
- Model thật nhận ảnh trống và trả quan sát không hợp lệ.
- Video tổng hợp không có mặt, 10 khung hình: 10 UNKNOWN, không có sự kiện cảnh báo,
  đọc hết video và đóng bình thường.
- Chưa mở webcam hoặc đánh giá khuôn mặt thật. Không dùng các kiểm tra trên làm số đo chính xác.

Trên macOS, dù chọn CPU, MediaPipe vẫn có thể cần ngữ cảnh đồ họa hệ thống khi
khởi tạo. Lượt kiểm tra model thật đã chạy ngoài sandbox sau khi sandbox báo lỗi
`NSOpenGLPixelFormat`; nếu gặp lỗi này, chạy từ terminal thông thường của máy.

Môi trường phát triển: Python 3.12.14, macOS 15.1 arm64; MediaPipe 0.10.32,
OpenCV contrib 4.11.0.86, NumPy 1.26.4. `requirements.txt` chốt các phụ thuộc trực tiếp.
Máy Windows/Linux và phiên bản Python khác cần được kiểm tra riêng.

Phải kiểm tra tiếp trên Quý/Tuyên: ngưỡng hiệu chỉnh thực, kính/ánh sáng/góc mặt,
FPS thực tế và cảnh báo nhầm/bỏ sót. Khi hiệu chỉnh, người dùng phải mở mắt;
chương trình không thể tự xác nhận nhãn mắt mở chỉ từ chính EAR. Hai mắt được
lấy trung bình nên có thể bỏ sót đóng một mắt. Không có nhận dạng danh tính;
người thay nhau vào hình phải bấm R. Confidence model không chứng minh rằng
mốc mắt chính xác trong mọi điều kiện. Video tốc độ khung hình biến thiên cần
đổi sang FPS cố định hoặc bổ sung bộ giải mã timestamp trước khi đánh giá.

Không có kết quả thực nghiệm, video dự phòng hoặc tuyên bố độ chính xác trong bản bàn giao này.
