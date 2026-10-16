# K4 Track 4 Capstone — Bài làm nhóm

Repository chung cho bài Capstone Day 28, Track 4 (Computer Vision & Robotics), thuộc Vin Perception Hackathon.

**Repository:** https://github.com/quycute2003/K4-Track4-ProjectCapstone

## Thành viên

| Họ và tên | Mã học viên |
| --- | --- |
| Phạm Xuân Quý | 2A202602745 |
| Nguyễn Hoàng Tuyên | 2A202602439 |

Nhóm gồm 2 người và đã được chấp nhận tham gia với quy mô này.

## Trạng thái dự án

- Sử dụng repository này làm nơi phát triển và nộp bài chung của nhóm.
- Đề tài đã chốt: **Vin Driver Watch — cảnh báo nhắm mắt kéo dài bằng webcam**.
- Xem [kế hoạch thực hiện](PLAN.md) để biết phạm vi, phân công đề xuất, lịch 120 phút, đánh giá và checklist nộp bài.
- Phân công branch đã chốt; tên nhóm và trưởng nhóm sẽ cập nhật khi xác nhận.
- Phần Quý đã có: detector MediaPipe, EAR, hiệu chỉnh, bộ trạng thái và vòng chạy webcam/video; xem [ghi chú triển khai](docs/implementation.md).
- Overlay chính thức, CSV và đánh giá của Tuyên chưa triển khai ở bản này. Ứng dụng có hiển thị tối thiểu để thử độc lập.

## Bắt đầu phát triển

Xem [hướng dẫn phối hợp](docs/development.md) để clone/pull và dùng giao diện module đã chốt.
Quý làm `feature/eye-detection`; Tuyên làm `feature/demo-evaluation` song song bằng
dữ liệu mẫu trong `scripts/mock_results.py`. Kiểu dữ liệu chung ở `src/contracts.py`.

```text
app.py                    Điểm tích hợp ứng dụng (Quý)
requirements.txt          Phiên bản phụ thuộc đã kiểm tra
src/eye_detector.py       Mốc mắt và EAR (Quý)
src/state_machine.py      Hiệu chỉnh, trạng thái và cảnh báo (Quý)
src/overlay.py            Giao diện OpenCV (Tuyên)
src/event_logger.py       Log CSV (Tuyên)
scripts/evaluate.py       Đánh giá sự kiện (Tuyên)
tests/test_state_machine.py  Vị trí kiểm thử logic (Quý)
docs/                    Hướng dẫn phát triển, đánh giá và demo
data/                    Dữ liệu cục bộ, bỏ qua bởi Git
models/                  Model cục bộ, bỏ qua bởi Git
```

## Cài đặt và chạy phần nhận diện

Dùng Python **3.10–3.12**; khuyến nghị 3.12. Tạo môi trường tại gốc repo:

```bash
python3.12 -m venv .venv
```

Kích hoạt trên macOS/Linux:

```bash
source .venv/bin/activate
```

Trên Windows PowerShell, thay lệnh tạo môi trường bằng `py -3.12 -m venv .venv`, rồi kích hoạt:

```powershell
.venv\Scripts\Activate.ps1
```

Trong môi trường đã kích hoạt:

```bash
python -m pip install -r requirements.txt
python -m scripts.download_model
python app.py --camera 0
```

Chỉ một người trong hình, nhìn thẳng và mở mắt bình thường đến khi đủ 60 mẫu.
`R` hiệu chỉnh lại; `Q` hoặc `Esc` thoát. Cấp quyền Camera cho ứng dụng terminal nếu macOS yêu cầu.
Model tải về được kiểm tra SHA256 và không commit lên Git.

Phát lại video tự quay có FPS cố định (đầu video cần có đoạn mắt mở để hiệu chỉnh):

```bash
python app.py --video data/videos/test.mp4
python app.py --video data/videos/test.mp4 --headless
```

`--alert-after 0` chạy phương án cơ sở cảnh báo ngay; mặc định là 1,5 giây.
`--fps` chỉ dùng để cung cấp FPS nguồn nếu metadata sai/thiếu; không dùng video tốc độ khung hình biến thiên cho đánh giá hiện tại.
`--log data/logs/run.csv` chỉ dùng sau khi Tuyên triển khai `EventLogger`.
Ứng dụng không tự quay video hoặc lưu hình ảnh.

Kiểm thử không cần model/webcam:

```bash
python -m unittest discover -s tests -v
```

Chưa có số đo nhận diện trên Quý/Tuyên; kiểm thử tự động không thay thế đánh giá thực tế.

## Yêu cầu sản phẩm

- Xây dựng trong 2 giờ một demo Computer Vision hoặc Robotics chạy thật trên webcam, cảm biến hoặc mô phỏng, gắn với hệ sinh thái Vin.
- Vận dụng và giải thích ít nhất 2 trụ cột Track 4.
- Có ít nhất một số đo kiểm chứng được và một ca lỗi kèm phân tích nguyên nhân.
- Thành viên tự đóng vai; không sử dụng dữ liệu thật của bệnh nhân hoặc sinh viên.
- Chuẩn bị video dự phòng và phần demo, hỏi đáp trong tổng cộng 10 phút.

## Phối hợp và nộp bài

1. Đảm bảo repository ở chế độ **Public** và cả hai thành viên có quyền Collaborator.
2. Mỗi thành viên làm việc trên branch riêng theo nhiệm vụ; kiểm tra thay đổi trước khi merge vào `main`.
3. Chốt mã nguồn, hướng dẫn chạy, số đo, ca lỗi và video dự phòng trên `main`.
4. **Cả hai thành viên đều tự nộp URL repository chung trên tài khoản VLearn cá nhân**, tại bài nộp Day 28.
5. Ghi chú nộp bài gồm tên nhóm, trưởng nhóm và vai trò cá nhân.

## Tài liệu đề bài

- [`index.html`](index.html): trang đề bài gốc, mở trực tiếp bằng trình duyệt, không cần build.
- [Repository đề bài chính thức](https://github.com/VinUni-AI20k/K4-Track4-ProjectCapstone).

Trang đề bài gồm hướng đề tài gợi ý, bốn yêu cầu demo, bảy trụ cột Track 4, công cụ gợi ý, thang điểm, lịch trình, checklist và FAQ.
