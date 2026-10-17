# Điều khiển robot gắp hàng bằng cánh tay thật

Demo dùng webcam laptop để nhận diện vai, khuỷu, cổ tay và các keypoint bàn tay. Panda trong PyBullet chuyển động theo cánh tay; người vận hành đưa đầu gắp tới hộp trên băng chuyền, chụm ngón để gắp rồi đưa hộp vào giỏ và mở tay để thả.

## Chạy trên Windows

Mở PowerShell tại thư mục gốc repo:

```powershell
./setup-demo.ps1
./run-demo.ps1
```

Lần đầu cần Internet để tải runtime Python, thư viện CPU, model MediaPipe và Three.js. Lệnh chạy mở cửa sổ webcam có keypoint cùng trang mô phỏng 3D theo trạng thái PyBullet. Cho phép ứng dụng truy cập webcam. Nếu camera khác là camera mặc định, dùng `./run-demo.ps1 --source 1`.

## Thao tác

1. Đứng đủ xa để webcam thấy vai, khuỷu, cổ tay và bàn tay phải. Nhấn **C**, giữ yên trong lúc hiệu chuẩn.
2. Di chuyển cánh tay để đưa robot theo. Hộp gần đầu gắp được tô vàng.
3. Đưa đầu gắp sát hộp rồi chụm ngón cái–trỏ. Nếu hộp chưa gắn, mở tay rồi thử lại khi đầu gắp chạm gần hộp hơn.
4. Đưa cánh tay tới giỏ, hạ đầu gắp vào trong giỏ và mở ngón để thả.
5. **P** tạm dừng; **C** hiệu chuẩn lại/tiếp tục; **R** đặt lại cảnh; **Q** hoặc **Esc** thoát.

Mất keypoint vai, khuỷu, cổ tay hoặc bàn tay sẽ tạm dừng robot. Nếu đang mang hộp, liên kết được giữ để hộp không rơi. Chế độ theo cánh tay dùng độ sâu tương đối từ webcam và ánh xạ đã hiệu chuẩn; đây không phải phép đo khoảng cách 3D chính xác.

## Thành phần

- `arm_vision.py`: MediaPipe Holistic chạy CPU, keypoint cánh tay/bàn tay và pinch ratio.
- `arm_control.py`: hiệu chuẩn vai, bám cổ tay/khuỷu, giới hạn workspace/tốc độ, pause khi mất tracking, điều khiển pinch.
- `simulation/__init__.py`: PyBullet Panda, băng chuyền dừng, ba hộp, giỏ; chỉ gắn hộp khi khoảng cách vật lý đạt ngưỡng.
- `simulation/serve.py` và `simulation/app.js`: trang Three.js hiển thị robot cùng trạng thái thực từ PyBullet.
- `main.py`: điều phối camera, controller, simulator và HTTP viewer trên máy cục bộ.
- `HACKATHON_PLAN.md`: mục tiêu MVP, phạm vi và tiêu chí demo.

Chế độ mặc định là điều khiển toàn cánh tay có gắp/thả bằng pinch. Để dùng chế độ lòng bàn tay và chu trình pick/place có sẵn, chạy `./run-demo.ps1 --mode pick`. Có thể chọn tay trái với `--hand Left`, bật thêm GUI PyBullet bằng `--gui`, hoặc chạy không có trang trình duyệt bằng `--no-web`.

Viewer lấy dữ liệu từ PyBullet và không gửi hình webcam qua HTTP. Trang 3D cần trình duyệt hỗ trợ WebGL và tải Three.js từ CDN. Mô phỏng vật lý và nhận diện ảnh chạy cục bộ trên CPU; tay gắp mô phỏng dùng liên kết cố định đơn giản, không mô phỏng chính xác lực kẹp.
