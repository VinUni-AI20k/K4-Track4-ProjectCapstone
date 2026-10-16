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
- Tên nhóm, trưởng nhóm và phân công chính thức sẽ được cập nhật khi xác nhận.
- Đã tạo khung thư mục và file để hai thành viên phát triển. Nhận diện, cảnh báo và đánh giá chưa được triển khai.

## Bắt đầu phát triển

Xem [hướng dẫn phối hợp](docs/development.md) để clone/pull, tạo branch và thống nhất giao diện module.

```text
app.py                    Điểm tích hợp ứng dụng (Quý)
requirements.txt          Phụ thuộc dự kiến, chưa chốt phiên bản
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

Để kiểm tra điểm chạy khung, dùng `python app.py` (hoặc `python3 app.py`). Lệnh này chỉ in trạng thái dự án, chưa mở webcam.
Hướng dẫn cài phụ thuộc, tải model và chạy nhận diện sẽ được bổ sung khi triển khai và kiểm tra trên máy demo.

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
