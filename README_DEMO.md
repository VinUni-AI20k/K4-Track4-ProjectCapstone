# Hướng dẫn demo tích hợp

## Khởi động

Trên Windows, tại gốc repo:

```powershell
./setup-demo.ps1
./run-demo.ps1
```

Setup tạo runtime Python 3.11 trong .runtime, cài MediaPipe/OpenCV/PyBullet CPU và tải model vào models. Sau setup, run-demo mặc định mở webcam overlay và viewer Three.js tại http://127.0.0.1:8765; PyBullet chạy DIRECT. Không cần GPU hoặc camera depth.

Tùy chọn thường dùng:

```powershell
./run-demo.ps1 --source 1
./run-demo.ps1 --hand Left
./run-demo.ps1 --gui
./run-demo.ps1 --no-web
```

## Điều khiển bằng cánh tay và gắp hàng

Webcam cần thấy vai, khuỷu, cổ tay và bàn tay của bên đã chọn. Cửa sổ camera vẽ bộ xương tay, các điểm bàn tay và pinch ratio. Trang 3D hiển thị Panda, hộp đang được nhắm tới, hộp đang mang và các hộp đã vào giỏ.

1. Giữ tư thế thoải mái rồi nhấn C. Giữ cánh tay yên khoảng 0.6 giây để robot lấy tư thế hiện tại làm mốc.
2. Di chuyển cánh tay. Cổ tay điều khiển vị trí đầu gắp trong XYZ tương đối với vai; khuỷu là gợi ý cho tư thế IK của Panda.
3. Đưa đầu gắp xuống sát hộp được tô vàng và chụm ngón cái–trỏ. Hệ thống chỉ gắn hộp nếu điểm gắp thực tế đủ gần.
4. Di chuyển cánh tay để mang hộp tới giỏ. Hạ đầu gắp vào trong vùng giỏ rồi mở ngón cái–trỏ. Mở tay ngoài giỏ không làm rơi hộp.
5. Nếu robot chưa gắp, mở tay và thử lại khi đầu gắp gần hộp hơn.

Pinch được xác nhận sau 0.12 giây; mất tracking làm robot pause và giữ hộp đang mang. Phím **P** pause, **C** hiệu chuẩn lại/tiếp tục, **R** reset cảnh, **Q** hoặc **Esc** thoát. Các nút tương ứng cũng có trên viewer.

Chế độ này cho người vận hành tự đưa đầu gắp xuống và nâng lên theo cánh tay. Z từ webcam là tương đối, không phải khoảng cách tuyệt đối. Panda và tay người có cấu trúc khác nhau nên IK chỉ tìm tư thế robot gần với khuỷu và cổ tay mong muốn.

## Luồng tích hợp

```text
webcam -> Holistic CPU -> ArmSample + keypoint overlay
       -> arm controller -> RobotCommand -> PyBullet Panda
                                              -> attach/release + basket check
                                              -> local HTTP snapshot -> Three.js
```

Main thread duy nhất thao tác simulator. Worker camera chỉ cập nhật mẫu mới nhất; bridge web chỉ đọc snapshot và nhận nút pause/resume/reset. Webcam không được truyền qua HTTP hoặc ghi vào log. Các hộp đứng tại trạm trên băng chuyền trong MVP; trang 3D minh họa đầy đủ dây chuyền, còn vật lý PyBullet xác nhận gắp/thả.

## Chế độ khác

Chế độ lòng bàn tay có chu trình nâng/hạ tự động:

```powershell
./run-demo.ps1 --mode pick
```

Demo đầu vào tổng hợp (không dùng webcam, nhưng vẫn chạy vật lý PyBullet):

```powershell
./run-demo.ps1 --mode arm --demo
```

Log phiên chạy được lưu dưới results/live; demo tổng hợp được tách dưới results/synthetic. Chỉ tính thành công khi hộp đã vào giỏ và ổn định trong mô phỏng.
