# Bàn giao TV1 — tích hợp điều khiển

## Trạng thái hiện tại

Phần điều khiển đã được ghép với webcam, PyBullet và viewer Three.js. Tài liệu chạy hiện hành là README_DEMO.md; phạm vi lab và tiêu chí nghiệm thu ở HACKATHON_PLAN.md.

## Luồng điều khiển

- arm_vision.py nhận diện vai, khuỷu, cổ tay và keypoint bàn tay; tạo pinch ratio và overlay webcam.
- arm_control.py hiệu chuẩn tư thế, điều khiển đầu gắp theo tay, giới hạn workspace/tốc độ và pause khi mất tracking.
- main.py điều phối Vision, controller, PyBullet, log và bridge cục bộ.
- simulation/__init__.py sở hữu robot Panda, hộp, giỏ, IK, attach/release và xác nhận hộp đã nằm ổn định trong giỏ.
- simulation/app.js chỉ hiển thị snapshot vật lý; phím bấm trên trang được chuyển lại main.py.

## Chạy

Trên Windows, chạy setup-demo.ps1 một lần, sau đó run-demo.ps1. Runner mặc định hiển thị webcam có keypoint và cảnh 3D theo trạng thái PyBullet. Nhấn C để hiệu chuẩn, P để tạm dừng, R để reset, Q hoặc Esc để thoát.

Chế độ arm cho người vận hành tự đưa đầu gắp đến hộp và giỏ bằng chuyển động cánh tay. Pinch gắp khi điểm gắp đủ gần hộp; mở tay chỉ thả trong vùng giỏ. Chế độ lòng bàn tay với chu trình nâng/hạ tự động chọn bằng run-demo.ps1 --mode pick.

Các kiểm tra tự động nằm trong thư mục tests; chưa được chạy trong lượt tích hợp này.
