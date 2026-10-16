# K4 Track 4 Project Capstone — Vin Perception Hackathon

Trang đề bài hackathon cuối khóa Track 4 (Computer Vision & Robotics): 2 giờ build, 10 phút demo mỗi team, đề tài gắn với hệ sinh thái Vin.

- `index.html`: trang đề bài (một file, không cần build). Mở trực tiếp bằng trình duyệt.

Nội dung gồm hướng đề tài gợi ý, bốn yêu cầu của mỗi demo, bảy trụ cột Track 4, công cụ gợi ý, thang điểm, lịch trình, checklist trước demo và FAQ. Ngày giờ, địa điểm, giám khảo, giải thưởng sẽ được ban tổ chức cập nhật.

## Triển khai hệ thống

- `HACKATHON_PLAN.md`: phạm vi MVP, phân công, kiến trúc và tiêu chí nghiệm thu.
- `TV1_HANDOFF.md`: giao diện tích hợp, hướng dẫn chạy và giới hạn kiểm chứng phần TV1.
- `contracts.py`, `config.py`, `control.py`, `main.py`: hợp đồng, cấu hình, điều khiển và vòng lặp tích hợp.

Chạy độc lập phần TV1 bằng Python 3.11, không cần dependency ngoài:

```powershell
.venv/Scripts/python.exe -m dev.run_control
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Runner dùng dữ liệu tổng hợp. Chạy `main.py` với webcam/robot thật cần module
`vision.py` của TV2 và `simulation.py` của TV3 theo giao diện trong tài liệu bàn giao.
