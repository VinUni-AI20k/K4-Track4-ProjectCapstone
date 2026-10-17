# 👁️ NHIỆM VỤ THÀNH VIÊN 1 (TRONG 4 BẠN): AI PERCEPTION & VẬT LIỆU (YOLO)

> **Dự án:** VinRobotics Waste Sorter Sim (Hệ thống Robot gắp phân loại phế liệu VinRobotics / VinFast)  
> **Thời gian:** 2 Giờ Build | 10 Phút Demo  
> **Nhánh Git phân công:** `feature/perception-yolo`  
> **Trụ cột Track 4 phụ trách:** **Trụ cột 1: HỌC (Learning / Material Classification)**

---

## 1. Nhiệm vụ chính
1. Kết nối với **Simulator của Leader** để lấy khung hình camera ảo (Virtual Camera Stream).
2. Chạy mô hình YOLOv8 nhận diện và phân loại vật liệu rác/phế liệu trên băng chuyền hoặc bàn thao tác của Sim:
   - `Plastic` (Chai lọ/nhựa tái chế)
   - `Metal` (Lon nước ngọt/phôi kim loại VinFast)
   - `Paper` (Giấy bìa các-tông)
   - `Defective_Part` (Phế liệu lỗi/bẹp dúm)
3. Trích xuất tâm pixel $(u, v)$ và Bounding Box, chuyển tiếp cho **Thành viên 2** (Geometry 3D).

---

## 2. Giao kèo dữ liệu kết nối (Interface Contract)
File `modules/detector.py` của bạn cung cấp class `WasteDetector`:

```python
# Đầu vào từ Leader Sim: frame (np.ndarray 480x640x3 BGR)
# Đầu ra gửi cho Thành viên 2 (Geometry):
detections = [
    {
        "bbox": [x1, y1, x2, y2],       # Pixel bounding box [int]
        "center_pixel": (u, v),         # Tâm vật thể trên ảnh (u, v)
        "material_class": "Plastic",    # "Plastic" | "Metal" | "Paper" | "Defective_Part"
        "confidence": 0.89,             # Độ tự tin model (0.0 -> 1.0)
        "inference_ms": 21.5            # Thời gian inference (ms)
    }
]
```

---

## 3. Code mẫu khung sườn (`modules/detector.py`)

```python
import cv2
import time
from ultralytics import YOLO

class WasteDetector:
    def __init__(self, model_path="yolov8n.pt", conf_thresh=0.35):
        print(f"[PERCEPTION] Khởi tạo YOLOv8 Detector từ {model_path}...")
        self.model = YOLO(model_path)
        self.conf_thresh = conf_thresh
        
        # Ánh xạ nhãn COCO sang nhóm vật liệu phế liệu VinFast/VinRobotics
        self.label_map = {
            "bottle": "Plastic",
            "cup": "Plastic",
            "can": "Metal",
            "book": "Paper",
            "cell phone": "E-Waste"
        }

    def detect(self, frame):
        start_t = time.time()
        # Chạy inference trên frame lấy từ Simulator của Leader
        results = self.model(frame, verbose=False, conf=self.conf_thresh)[0]
        inference_ms = (time.time() - start_t) * 1000

        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            cls_name = self.model.names[int(box.cls[0])].lower()

            material = self.label_map.get(cls_name, cls_name.capitalize())
            u = int((x1 + x2) / 2)
            v = int((y1 + y2) / 2)

            detections.append({
                "bbox": [x1, y1, x2, y2],
                "center_pixel": (u, v),
                "material_class": material,
                "confidence": round(conf, 3),
                "inference_ms": round(inference_ms, 2)
            })

        return detections
```

---

## 4. Định dạng Console Log Trace
```text
[FRAME #0120] [PERCEPTION] Sim Frame: 1 object detected.
              -> Class: 'Plastic' | Conf: 0.91 | Pixel Center: (395, 185) | Latency: 21.2ms
```

---

## 5. Quy trình Git
```bash
git checkout -b feature/perception-yolo
git add modules/detector.py
git commit -m "feat(perception): connect yolo inference to leader simulator virtual camera"
git push origin feature/perception-yolo
```

---

## 6. Vai trò trong buổi thuyết trình 10 phút
* **Phút 01:00 - 02:00:** Thuyết minh tầng Perception: *"Model thị giác máy tính nhận luồng ảnh trực tiếp từ Simulator của nhóm, nhận diện phân loại vật liệu phế liệu với độ trễ chỉ 21ms (> 30 FPS) để cung cấp đầu vào cho hệ thống tính toán tọa độ 3D."*
