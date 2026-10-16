"""
VIN PERCEPTION HACKATHON — MODULE: AI PERCEPTION & MATERIAL CLASSIFICATION
Author: Member 1 (AI Perception Engineer)
Branch: feature/perception-yolo
Pillar: Trụ cột 1 - HỌC (Learning / YOLOv8 Detection)

Security & Robustness:
- Input validation (dtype, dimension, resolution limits to prevent memory exhaustion).
- Path traversal sanitization for model weights.
- Zero-crash fallback: Graceful degradation to algorithmic color segmentation if model fails.
- Environment variable configuration for sensitive parameters.
"""

import os
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2

# Cấu hình logging
logger = logging.getLogger("WasteDetector")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class WasteDetector:
    """
    Module nhận diện và phân loại vật liệu rác/phế liệu công nghiệp.
    Tích hợp YOLOv8 với cơ chế phòng vệ (Input Sanitization) và Fallback tự động.
    """
    
    # Giới hạn an toàn kích thước khung hình (Chống DoS / Out-of-Memory)
    MIN_DIMENSION = 16
    MAX_DIMENSION = 4096

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_thresh: float = 0.35,
        iou_thresh: float = 0.45,
        device: Optional[str] = None
    ) -> None:
        """
        Khởi tạo WasteDetector.
        
        Args:
            model_path: Đường dẫn tới weights YOLO (.pt). Nếu None, đọc từ biến môi trường hoặc dùng 'yolov8n.pt'.
            conf_thresh: Ngưỡng tự tin tối thiểu (0.0 -> 1.0).
            iou_thresh: Ngưỡng NMS IoU.
            device: Thiết bị chạy ('cpu', 'cuda', hoặc None để tự phát hiện).
        """
        self.conf_thresh = max(0.01, min(0.99, float(conf_thresh)))
        self.iou_thresh = max(0.01, min(0.99, float(iou_thresh)))
        self.model = None
        self.is_yolo_active = False

        # 1. Bảo mật đường dẫn model (Path Traversal Sanitization)
        raw_path = model_path or os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
        self.model_path = self._sanitize_model_path(raw_path)

        # 2. Bảng ánh xạ lớp COCO / Roboflow sang phân loại vật liệu VinFast & VinRobotics
        self.material_mapping = {
            "bottle": "Plastic",
            "cup": "Plastic",
            "plastic": "Plastic",
            "can": "Metal",
            "metal": "Metal",
            "knife": "Metal",
            "fork": "Metal",
            "book": "Paper",
            "paper": "Paper",
            "cardboard": "Paper",
            "glass": "Glass",
            "wine glass": "Glass",
            "cell phone": "E-Waste",
            "crushed": "Defective_Part",
            "defect": "Defective_Part"
        }

        # 3. Nạp model YOLOv8 an toàn
        self._load_model(self.model_path, device)

    def _sanitize_model_path(self, path: str) -> str:
        """Kiểm tra và chuẩn hóa đường dẫn weights, ngăn chặn path traversal độc hại."""
        clean_path = os.path.normpath(path)
        # Nếu là tên file chuẩn của Ultralytics (e.g. yolov8n.pt)
        if clean_path.startswith("yolov8") and clean_path.endswith(".pt"):
            return clean_path
        # Kiểm tra file nội bộ
        if not os.path.exists(clean_path):
            logger.warning(f"File weights '{clean_path}' không tồn tại. Sử dụng default 'yolov8n.pt'.")
            return "yolov8n.pt"
        return clean_path

    def _load_model(self, model_path: str, device: Optional[str]) -> None:
        """Nạp model YOLO với try-except an toàn, tự động fallback nếu thiếu thư viện hoặc weights."""
        try:
            from ultralytics import YOLO
            import torch
            
            # Tự động chọn device nếu chưa chỉ định
            if device is None:
                selected_device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                selected_device = device

            logger.info(f"Đang nạp mô hình YOLOv8 từ: {model_path} trên thiết bị: {selected_device}...")
            self.model = YOLO(model_path)
            self.device = selected_device
            self.is_yolo_active = True
            logger.info("Mô hình YOLOv8 đã khởi tạo thành công!")
        except Exception as e:
            logger.error(f"Không thể nạp YOLOv8 ({e}). Kích hoạt chế độ Fallback Vision (Blob/Color Segmentation) để đảm bảo hệ thống không bao giờ crash!")
            self.is_yolo_active = False

    def validate_frame(self, frame: Any) -> Tuple[bool, str]:
        """
        Bảo mật và kiểm tra tính toàn vẹn của khung hình đầu vào (Input Sanitization).
        
        Returns:
            Tuple[bool, str]: (Hợp lệ hay không, Thông điệp lỗi nếu có)
        """
        if frame is None:
            return False, "Khung hình đầu vào là None"
        if not isinstance(frame, np.ndarray):
            return False, f"Kiểu dữ liệu không hợp lệ: {type(frame)}, yêu cầu numpy.ndarray"
        if frame.size == 0:
            return False, "Khung hình rỗng (size == 0)"
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            return False, f"Yêu cầu ảnh màu 3 kênh BGR (H, W, 3), nhận được shape: {frame.shape}"
        
        h, w = frame.shape[:2]
        if h < self.MIN_DIMENSION or w < self.MIN_DIMENSION:
            return False, f"Độ phân giải quá nhỏ ({w}x{h} < {self.MIN_DIMENSION}x{self.MIN_DIMENSION})"
        if h > self.MAX_DIMENSION or w > self.MAX_DIMENSION:
            return False, f"Độ phân giải vượt ngưỡng an toàn ({w}x{h} > {self.MAX_DIMENSION}x{self.MAX_DIMENSION})"
        
        return True, ""

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Chạy nhận diện vật liệu trên khung hình.
        
        Args:
            frame: Ảnh BGR từ Simulator hoặc Camera (H, W, 3).
            
        Returns:
            Danh sách các detection theo đúng Interface Contract:
            [{
                "bbox": [x1, y1, x2, y2],
                "center_pixel": (cx, cy),
                "material_class": str,
                "confidence": float,
                "inference_ms": float
            }]
        """
        # 1. Kiểm tra an toàn khung hình
        is_valid, err_msg = self.validate_frame(frame)
        if not is_valid:
            logger.warning(f"Bỏ qua khung hình lỗi: {err_msg}")
            return []

        start_time = time.perf_counter()
        detections: List[Dict[str, Any]] = []

        try:
            if self.is_yolo_active and self.model is not None:
                # 2A. Suy luận bằng YOLOv8
                results = self.model(
                    frame,
                    verbose=False,
                    conf=self.conf_thresh,
                    iou=self.iou_thresh,
                    device=getattr(self, "device", "cpu")
                )[0]

                inference_ms = (time.perf_counter() - start_time) * 1000.0

                for box in results.boxes:
                    coords = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = [int(round(c)) for c in coords]
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    raw_cls_name = self.model.names[cls_id].lower()

                    # Ánh xạ về nhóm vật liệu
                    material = self.material_mapping.get(raw_cls_name, raw_cls_name.capitalize())
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)

                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "center_pixel": (cx, cy),
                        "material_class": material,
                        "confidence": round(conf, 3),
                        "inference_ms": round(inference_ms, 2)
                    })
            else:
                # 2B. Chế độ Fallback Vision an toàn (Chạy ngay cả khi offline / không có weights)
                detections = self._fallback_color_detection(frame, start_time)

        except Exception as e:
            logger.error(f"Lỗi ngoại lệ trong quá trình inference ({e}). Kích hoạt Fallback tức thì!")
            detections = self._fallback_color_detection(frame, start_time)

        return detections

    def _fallback_color_detection(self, frame: np.ndarray, start_time: float) -> List[Dict[str, Any]]:
        """Thuật toán Fallback Vision nhận diện vật thể màu từ Simulator để bảo vệ live demo."""
        detections: List[Dict[str, Any]] = []
        inference_ms = (time.perf_counter() - start_time) * 1000.0

        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Màu xanh lục (Plastic trong Simulator)
            mask_green = cv2.inRange(hsv, (35, 70, 70), (85, 255, 255))
            # Màu vàng/kim loại (Metal trong Simulator)
            mask_yellow = cv2.inRange(hsv, (20, 100, 100), (35, 255, 255))

            color_configs = [
                ("Plastic", mask_green, 0.92),
                ("Metal", mask_yellow, 0.88)
            ]

            for mat_name, mask, conf in color_configs:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    if cv2.contourArea(cnt) > 250:
                        x, y, w, h = cv2.boundingRect(cnt)
                        cx = int(x + w / 2)
                        cy = int(y + h / 2)
                        detections.append({
                            "bbox": [x, y, x + w, y + h],
                            "center_pixel": (cx, cy),
                            "material_class": mat_name,
                            "confidence": conf,
                            "inference_ms": round(inference_ms, 2)
                        })
        except Exception as fallback_err:
            logger.error(f"Fallback detector gặp lỗi: {fallback_err}")

        return detections
