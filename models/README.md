# Model cục bộ

Model: **MediaPipe Face Landmarker, float16, version 1**.

- [Nguồn tải chính thức](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task).
- [Tài liệu model của Google](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker).
- Đường dẫn mặc định: `models/face_landmarker.task`.
- SHA256: `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`.

Tại gốc repo, trong môi trường Python đã kích hoạt:

```bash
python -m scripts.download_model
```

Script không ghi đè file có sẵn, kiểm tra checksum trước khi đặt file vào vị trí cuối.
File model được bỏ qua bởi Git; mỗi thành viên tự tải. Dùng `--model` khi chạy ứng dụng
nếu đặt model tại đường dẫn khác.
