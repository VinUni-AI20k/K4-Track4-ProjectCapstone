# Kế hoạch Capstone: Vin Driver Watch

## 1. Mục tiêu và phạm vi

Xây dựng ứng dụng Python dùng webcam để phát hiện nhắm mắt kéo dài, cảnh báo và ghi dữ liệu đánh giá. Bối cảnh ứng dụng là giám sát người lái VinFast/VinBus. Sản phẩm là bản thử nghiệm trên laptop; kết quả không đủ để kết luận buồn ngủ hoặc mức giảm tai nạn.

Nhóm gồm 2 thành viên, đã được chấp nhận quy mô này:

| Thành viên | Mã học viên |
| --- | --- |
| Phạm Xuân Quý | 2A202602745 |
| Nguyễn Hoàng Tuyên | 2A202602439 |

Repository chung: https://github.com/quycute2003/K4-Track4-ProjectCapstone

Tên nhóm và trưởng nhóm cần được hai thành viên xác nhận. Phân công bên dưới là kế hoạch đề xuất, sẽ cập nhật theo đóng góp thực tế.

### Bắt buộc hoàn thành

- Chạy trên webcam một người, đọc được video để phát lại.
- Dùng MediaPipe pretrained lấy mốc mắt; tính EAR bằng NumPy.
- Hiệu chỉnh theo người dùng bằng mẫu mắt mở; ngưỡng và thời gian chờ cấu hình được.
- Phân biệt chớp mắt ngắn với nhắm mắt kéo dài bằng thời gian thực.
- Hiển thị trạng thái, EAR, thời lượng mắt đóng và cảnh báo trực quan bằng OpenCV.
- Xử lý mất quan sát, phục hồi và hiệu chỉnh lại.
- Ghi log CSV phục vụ đánh giá; có kết quả thật, ca lỗi và video dự phòng.
- Tài liệu giải thích thiết kế, ít nhất hai trụ cột, cách chạy, đánh giá và giới hạn.

### Chỉ làm khi phần bắt buộc đã xong

- Âm báo có thời gian nghỉ giữa các lần phát.
- Biểu đồ EAR từ log và thống kê hiệu năng bổ sung.

### Ngoài phạm vi 2 giờ

Train model, nhận diện ngáp, góc đầu 3D, theo dõi nhiều người, dashboard web, kết nối xe hoặc điều khiển phương tiện.

## 2. Thiết kế kỹ thuật và hợp đồng tích hợp

Luồng xử lý: đầu vào webcam/video → MediaPipe → mốc mắt → EAR → kiểm tra hợp lệ → bộ trạng thái theo thời gian → giao diện + log.

Công cụ: Python 3.10+, OpenCV, MediaPipe, NumPy và thư viện chuẩn Python. Chốt phiên bản tương thích sau khi chạy thử trên đúng máy demo; ghi vào file phụ thuộc. Không cần YOLO, Streamlit hoặc Gradio cho phạm vi này.

### Quy tắc xử lý

- EAR mỗi mắt = tổng hai khoảng cách dọc / (2 × khoảng cách ngang), tính trên tọa độ có cùng đơn vị pixel; kiểm tra mẫu số và mốc hợp lệ.
- Dùng trung vị EAR của mẫu mắt mở hợp lệ làm tham chiếu; ngưỡng đóng là một hệ số cấu hình nhân với tham chiếu. Chọn hệ số trên dữ liệu phát triển rồi khóa trước đánh giá.
- Hiệu chỉnh chỉ hoàn thành khi đủ số mẫu hợp lệ. Người dùng nhìn thẳng, mở mắt bình thường; nếu không đủ mẫu thì yêu cầu thử lại.
- Ngưỡng thời gian khởi đầu: 1,5 giây để thử nghiệm, không phải chuẩn an toàn. Dùng ngưỡng mở lại cao hơn ngưỡng đóng để hạn chế trạng thái dao động; chốt cả hai trên dữ liệu phát triển.
- Webcam dùng đồng hồ đơn điệu; video dùng thời gian của video. Không lấy tốc độ phát lại làm thời lượng mắt đóng.
- Khi mất mặt, mốc không hợp lệ hoặc khoảng trống xử lý vượt giới hạn cấu hình: chuyển sang `UNKNOWN`, hủy bộ đếm mắt đóng. Không nối hai đoạn quan sát qua khoảng mất dữ liệu.
- Một chuỗi mắt đóng liên tục chỉ tạo một sự kiện cảnh báo; chỉ cho phép sự kiện mới sau khi mở mắt hoặc phục hồi từ mất quan sát.
- Nếu có nhiều mặt, hiển thị cảnh báo phạm vi một người và không tự đổi người trong cùng một sự kiện.

| Trạng thái | Ý nghĩa |
| --- | --- |
| `CALIBRATING` | Chưa đủ mẫu hiệu chỉnh |
| `OPEN` | Mắt mở, dữ liệu hợp lệ |
| `CLOSING` | Mắt đóng nhưng chưa đủ thời gian cảnh báo |
| `ALERT` | Mắt đóng liên tục đủ thời gian |
| `UNKNOWN` | Không đủ dữ liệu để quyết định |

### Giao diện giữa các phần

Quý cung cấp bộ xử lý nhận khung hình và thời gian tính bằng giây, trả về: EAR trái/phải/tổng hợp (hoặc giá trị trống), trạng thái, thời lượng mắt đóng, ngưỡng và cờ sự kiện cảnh báo mới. Tuyên dùng kết quả này để vẽ và ghi log; giao diện không tự tính lại logic cảnh báo.

CSV tối thiểu: `frame_id`, `timestamp_s`, `ear_left`, `ear_right`, `ear`, `valid`, `state`, `closed_duration_s`, `alert_event`, `processing_ms`. Lưu cấu hình và ngưỡng hiệu chỉnh của mỗi lượt để tái hiện. Thời gian xử lý khung hình chỉ là thời gian phần mềm đo được, không gọi là độ trễ camera đến màn hình.

### Cấu trúc dự kiến

```text
app.py                  # Chạy webcam/video, tích hợp các module
requirements.txt        # Phiên bản đã kiểm tra trên máy demo
src/
  eye_detector.py       # MediaPipe, mốc mắt, EAR
  state_machine.py      # Hiệu chỉnh và logic theo thời gian
  overlay.py            # Hiển thị trạng thái
  event_logger.py       # Ghi CSV
scripts/
  evaluate.py           # Đối chiếu sự kiện dự đoán và nhãn
tests/
  test_state_machine.py # Kiểm thử logic không cần webcam
docs/
  evaluation.md         # Giao thức thử, kết quả thật, ca lỗi
  demo.md               # Kịch bản 10 phút và dự phòng
data/                   # Video/nhãn/log cục bộ; không tự công khai
README.md
PLAN.md
index.html              # Trang đề bài gốc
```

Đây là cấu trúc dự kiến, chưa phải các file đã triển khai.

## 3. Phân công và quy trình Git

| Người | Phần chính | Sản phẩm bàn giao |
| --- | --- | --- |
| Quý | Đầu vào camera/video, MediaPipe, EAR, hiệu chỉnh, bộ trạng thái | Luồng nhận diện và cảnh báo; kiểm thử bộ trạng thái |
| Tuyên | Overlay, CSV, đánh giá, tài liệu | Giao diện, log, đối chiếu nhãn, báo cáo và kịch bản demo |
| Cả hai | Chốt giao diện module, tích hợp, diễn thử và kiểm tra bản cuối | Bản chạy trên máy demo, kết quả thật và video dự phòng |

- Kiểm tra repo Public, quyền Collaborator và lời mời đã được chấp nhận.
- Branch đề xuất: `feature/eye-detection` cho Quý, `feature/demo-evaluation` cho Tuyên.
- Mỗi phần ưu tiên file riêng; thống nhất người tích hợp `app.py` để tránh sửa đè.
- Commit từng phần chạy được, đẩy branch và kiểm tra thay đổi trước merge `main`.
- Không commit môi trường ảo, cache, thông tin riêng hoặc toàn bộ dữ liệu quay thử. Thêm quy tắc bỏ qua trước lần commit ứng dụng đầu tiên.
- Hai người cùng hiểu toàn bộ hệ thống, không chỉ phần mình viết.

## 4. Lịch thực hiện 120 phút

Nếu ban tổ chức cho phép chuẩn bị trước: kiểm tra webcam, Python, Git, quyền repo và tải model theo quy định. Nếu chưa chuẩn bị được, thực hiện trong chặng đầu và giảm phần tùy chọn.

| Thời gian từ lúc build | Quý | Tuyên | Điều kiện qua mốc |
| --- | --- | --- | --- |
| 0–15 phút | Kiểm tra thư viện/model, mở webcam và lấy mốc | Tạo cấu trúc, bộ log/overlay tối thiểu, mẫu nhãn | Đọc được khung hình; thống nhất đầu ra giữa module |
| 15–40 phút | Tính EAR và hiệu chỉnh | Hoàn thiện overlay, CSV, đầu vào video ở phần tích hợp đã thống nhất | Nhìn thấy EAR và trạng thái trên ảnh thật |
| 40–60 phút | Bộ trạng thái, mất quan sát, kiểm thử logic | Tích hợp giao diện/log, thử phát lại | Có luồng đầu vào → cảnh báo → log chạy thật |
| 60–80 phút | Sửa lỗi tích hợp; khóa tham số bằng lượt phát triển | Cùng quay clip thử và gán nhãn | Webcam chạy ổn; lưu cấu hình trước đánh giá |
| 80–105 phút | Chạy hai phương án trên cùng dữ liệu | Tính số đo, ghi và giải thích ca lỗi | Có bảng kết quả thật và đoạn minh chứng |
| 105–120 phút | Kiểm tra bản cuối từ hướng dẫn chạy | Chốt README, quay dự phòng, tập chuyển phần | `main` chạy được; đủ tài liệu và video |

**Mốc 60 phút:** bắt buộc có luồng chạy thật. Nếu chậm, bỏ âm báo và biểu đồ; ưu tiên cửa sổ OpenCV, log, kiểm thử và đánh giá. Không bỏ xử lý mất quan sát hoặc bịa kết quả để kịp giờ.

Nếu có 15 phút chuẩn bị demo riêng sau build theo lịch ban tổ chức, dùng để kiểm tra thiết bị và tập trình bày; không phụ thuộc khoảng này để hoàn thành chức năng chính.

## 5. Kiểm thử và bằng chứng

### Kiểm thử logic trước khi quay

- Chớp mắt ngắn không tạo cảnh báo.
- Mắt đóng vượt ngưỡng tạo đúng một sự kiện.
- Mở mắt cho phép bắt đầu sự kiện tiếp theo.
- Mất quan sát hủy bộ đếm; phục hồi không dùng lại thời gian cũ.
- Cùng một chuỗi theo thời gian nhưng lấy mẫu ở FPS khác nhau cho hành vi tương đương trong sai số lấy mẫu.
- Dữ liệu không hợp lệ, hiệu chỉnh thiếu mẫu và khoảng trống xử lý không bị tính là nhắm mắt liên tục.

### Dữ liệu đánh giá

Chỉ Quý và Tuyên tự đóng vai. Dùng lượt phát triển riêng để chọn tham số; không sửa tham số theo kết quả đánh giá rồi báo cáo lại như dữ liệu chưa từng xem.

Mục tiêu tối thiểu trên mỗi người:

| Tình huống | Số lượng dự kiến | Mục đích |
| --- | --- | --- |
| Nhìn bình thường, chớp mắt tự nhiên | 60 giây/người | Đo cảnh báo nhầm/phút |
| Nhắm mắt chủ đích khoảng 2–3 giây | 5 lần/người, có đoạn mở mắt giữa các lần | Đo phát hiện và thời gian cảnh báo |
| Che mặt, ra/vào khung hình | 2 lần/người | Kiểm tra mất quan sát và phục hồi |
| Nheo mắt, quay nghiêng hoặc ánh sáng yếu | Ít nhất một đoạn | Tìm lỗi thực tế và giới hạn |

Gán nhãn thủ công thời điểm bắt đầu/kết thúc mắt đóng; nhãn `UNKNOWN` cho đoạn không quan sát được. Xem video để đặt nhãn, không dùng kết quả EAR làm nhãn chuẩn. Báo cáo số clip/số lượt thực sự thực hiện và quy tắc nhãn. Nêu rõ mẫu chỉ có hai người và việc hiệu chỉnh cá nhân.

### So sánh công bằng

- Cơ sở: cảnh báo ngay khi EAR dưới ngưỡng.
- Hoàn chỉnh: cùng ngưỡng EAR, thêm điều kiện thời gian.
- Cả hai dùng cùng video, ngưỡng, quy tắc dữ liệu hợp lệ và cách gom sự kiện.
- Mỗi sự kiện dự đoán chỉ ghép với một sự kiện nhắm mắt đã gán nhãn. Một lần nhắm mắt đủ dài được phát hiện nếu có sự kiện cảnh báo sau thời gian chờ và trước khi mắt mở lại; báo cáo quy tắc sai số nhãn nếu dùng.

### Số đo phải báo cáo

1. **Cảnh báo nhầm/phút:** số sự kiện cảnh báo trong clip hoạt động bình thường / thời lượng clip tính bằng phút; báo cáo thêm tỉ lệ thời gian quan sát hợp lệ.
2. **Tỉ lệ phát hiện:** số sự kiện nhắm mắt kéo dài được phát hiện / tổng sự kiện đủ dài đã gán nhãn. Đếm bỏ sót cả các lần thất bại vì mất quan sát, đồng thời tách nguyên nhân.
3. **Thời gian cảnh báo:** từ thời điểm mắt đóng trong nhãn đến cảnh báo đầu tiên; báo cáo trung vị và phạm vi, ghi rõ gồm thời gian chờ chủ đích.

Không đặt trước kết quả đạt được. Nếu bản hoàn chỉnh không cải thiện, báo cáo đúng kết quả và phân tích.

### Một ca lỗi bắt buộc

Lưu đoạn xảy ra báo nhầm hoặc bỏ sót, thời điểm, cấu hình, trạng thái mong muốn/thực tế, dấu hiệu trong log, nguyên nhân có căn cứ và hướng khắc phục. Mất mặt được báo `UNKNOWN` đúng thiết kế không tự tính là ca lỗi. Kính tối màu là tình huống thử thêm nếu có sẵn, không phải lỗi được giả định trước.

## 6. Đối chiếu sáu tiêu chí chấm điểm

| Tiêu chí | Bằng chứng nhóm cần có |
| --- | --- |
| Kiến thức — 25 | Sơ đồ luồng, hai trụ cột chính Biểu diễn + Thời gian, giải thích EAR/hiệu chỉnh/trạng thái và so sánh phương án |
| Demo — 25 | Webcam chạy trực tiếp, người mới hiệu chỉnh rồi thử, xử lý mất quan sát và phục hồi; video dự phòng |
| Hữu ích — 15 | Người dùng cụ thể là tài xế; cảnh báo dễ hiểu và nhật ký giúp rà soát sự kiện; định vị rõ bản thử nghiệm |
| Impact — 15 | Kịch bản thử nghiệm mở rộng, ước lượng định lượng có giả định, rủi ro và điều kiện triển khai |
| Bằng chứng — 10 | Giao thức thử, dữ liệu/log có thể đối chiếu, bảng số đo thật, một ca lỗi và giới hạn |
| Trình bày/hỏi đáp — 10 | Kịch bản 10 phút; cả hai giải thích được thiết kế, đánh giá và phạm vi kết luận |

Impact có thể ước lượng theo công sức rà soát: `số giờ ghi × số tài xế` so với `số sự kiện × thời gian rà soát mỗi sự kiện`. Ghi rõ đâu là giả định và đâu là số đã đo. Không diễn giải giảm thời gian xem video thành giảm tai nạn. Rủi ro cần nêu: báo nhầm, bỏ sót, ánh sáng, kính, vị trí camera, khác biệt người dùng và dữ liệu khuôn mặt. Việc thử trên xe thật cần đánh giá riêng; bản này trình diễn trên laptop.

## 7. Kịch bản trình bày 10 phút

| Thời lượng | Nội dung | Phụ trách đề xuất |
| --- | --- | --- |
| 1 phút | Người dùng, bài toán và phạm vi sản phẩm | Quý |
| 4 phút | Webcam: hiệu chỉnh, chớp mắt, nhắm mắt kéo dài, mất mặt/phục hồi; mời thử đầu vào mới | Quý thao tác, Tuyên hỗ trợ |
| 2 phút | Hai trụ cột, kết quả so sánh, ca lỗi, tác động và giới hạn | Tuyên |
| 3 phút | Hỏi đáp về toàn hệ thống | Cả hai |

Nếu camera lỗi: thử phục hồi nhanh; nếu không được, chuyển sang video đã quay và nói rõ đó là video dự phòng.

## 8. Tiêu chí hoàn thành và nộp bài

- [ ] Repo Public; cả hai có quyền cộng tác; tên nhóm/trưởng nhóm được chốt.
- [ ] Cài và chạy được theo README trên đúng máy demo.
- [ ] Có hướng dẫn lấy model, phiên bản phụ thuộc và cấu hình tái hiện.
- [ ] Webcam và video đều chạy; đọc hết video hoặc mất camera không làm ứng dụng treo.
- [ ] Hiệu chỉnh, cảnh báo, mất quan sát và phục hồi hoạt động đúng.
- [ ] Kiểm thử logic cốt lõi đạt; kiểm tra trực tiếp với cả hai người.
- [ ] CSV, nhãn, bảng kết quả và ca lỗi đối chiếu được.
- [ ] Tài liệu ghi rõ ít nhất hai trụ cột, impact, giả định và giới hạn.
- [ ] Có video dự phòng; chỉ công khai đoạn hai thành viên đồng ý dùng để nộp; kiểm tra người chấm truy cập được.
- [ ] `main` chứa phiên bản hoàn chỉnh; phân công phản ánh đóng góp thực tế.
- [ ] Quý tự nộp URL repo chung trên tài khoản VLearn của Quý.
- [ ] Tuyên tự nộp URL repo chung trên tài khoản VLearn của Tuyên.
- [ ] Mỗi bản nộp ghi tên nhóm, trưởng nhóm, vai trò cá nhân và kiểm tra trạng thái nộp thành công.

Kế hoạch hướng tới đáp ứng mức xuất sắc của sáu tiêu chí; điểm thực tế phụ thuộc sản phẩm, bằng chứng và đánh giá của giảng viên.
