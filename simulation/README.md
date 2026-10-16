# Mô phỏng robot gắp hàng

## Chế độ demo tích hợp

Từ gốc repo, chạy ./setup-demo.ps1 một lần rồi ./run-demo.ps1. Runner mở webcam overlay và viewer Three.js, còn PyBullet giữ trạng thái vật lý chuẩn. Mặc định robot được điều khiển bằng chuyển động vai–khuỷu–cổ tay; pinch gắp/thả hộp. Xem README_DEMO.md để biết thao tác và phím điều khiển.

Viewer có tại http://127.0.0.1:8765. Nó nhận snapshot từ PyBullet; lệnh HTTP không điều khiển robot. Webcam ở cửa sổ OpenCV cục bộ, không được gửi lên bridge.

Tọa độ vật lý là mét, Z-up. Viewer đổi trục để hiển thị trên Three.js. Băng chuyền giữ ba hộp tại trạm gắp; attach chỉ thành công khi điểm gắp thực sự gần hộp. Hộp chỉ được tính vào giỏ sau khi được thả, nằm trọn trong giỏ và ổn định.

## Viewer độc lập cũ

Để xem riêng cảnh Three.js minh họa, có thể chạy python simulation/serve.py rồi mở http://127.0.0.1:8765. Chế độ này không nhận webcam và không phải kết quả vật lý dùng để đánh giá demo tích hợp.
