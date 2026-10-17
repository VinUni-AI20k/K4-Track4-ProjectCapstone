# Mô phỏng robot gắp hàng

## Chế độ demo tích hợp

Từ gốc repo, chạy `./setup-demo.ps1` một lần rồi `./run-demo.ps1`. Runner hiển thị webcam phủ keypoint ngay trong viewer Three.js, còn PyBullet giữ trạng thái vật lý chuẩn. Mặc định robot được điều khiển bằng chuyển động vai–khuỷu–cổ tay; pinch gắp/thả hộp. Xem README_DEMO.md để biết thao tác và phím điều khiển.

Viewer tích hợp hiển thị webcam đã phủ keypoint và trạng thái robot từ PyBullet. Các nút trên trang gửi lệnh pause/resume/reset qua bridge local. Dùng `./run-demo.ps1` để khởi động sản phẩm hoàn chỉnh; địa chỉ chính xác được in trong terminal nếu cổng mặc định đang bận.

Tọa độ vật lý là mét, Z-up. Viewer đổi trục để hiển thị trên Three.js. Băng chuyền giữ ba hộp tại trạm gắp; attach chỉ thành công khi điểm gắp thực sự gần hộp. Hộp chỉ được tính vào giỏ sau khi được thả, nằm trọn trong giỏ và ổn định.

## Viewer độc lập cũ

`python simulation/serve.py` chỉ mở cảnh Three.js độc lập; nó không khởi động webcam, PyBullet hoặc bridge điều khiển robot. Nếu trang báo chưa nối robot, hãy chạy `./run-demo.ps1` và mở đúng địa chỉ localhost được in trong terminal.
