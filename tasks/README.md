# 🚀 VIN PERCEPTION HACKATHON — TEAM FAN MU (5 THÀNH VIÊN)
## Đề tài: VinRobotics Closed-Loop Waste Sorter (Hệ thống Robot Phân loại Phế liệu Khép kín trong Môi trường Mô phỏng)

---

### 🌟 Kiến trúc Tổng thể: Vòng Lặp Khép Kín (Closed-Loop System)
Hệ thống kết hợp giữa **Môi trường Mô phỏng Robot (Simulator của Leader)** và **Pipeline Xử lý Thị giác / Điều khiển (4 Thành viên)**:

```
                          ┌────────────────────────────────────────────────────────┐
                          │         LEADER: SIMULATOR & ROBOT ENVIRONMENT          │
                          │                                                        │
                          │  • Render Virtual Camera Stream (Frame RGB 640x480)    │
                          │  • Cung cấp Ground Truth (X, Y, Z thật của vật)        │
                          │  • Cung cấp hàm execute_action() cho Robot gắp         │
                          └───────────────────────────┬────────────────────────────┘
                                                      │ Virtual Camera Frame
                                                      ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                 4 THÀNH VIÊN TÍCH HỢP VÀO SIMULATOR CỦA LEAD                                     │
 ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 👤 TV1: AI PERCEPTION & VẬT LIỆU (YOLO)               [Nhánh: feature/perception-yolo]                           │
 │   • Nhận ảnh từ Sim của Lead -> Chạy YOLOv8 phân loại: Nhựa, Kim loại, Giấy, Phế liệu lỗi                        │
 │   • Xuất ra Bounding Box và tọa độ tâm pixel (u, v)                                                              │
 ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 👤 TV2: 3D CAMERA GEOMETRY & TỌA ĐỘ GẮP SIM           [Nhánh: feature/geometry-3d]                               │
 │   • Chuyển từ pixel (u, v) sang tọa độ thế giới thực 3D (X, Y, Z)_world của Simulator                            │
 │   • Tính toán góc tiếp cận và điểm gắp (Pick Point) tối ưu cho cánh tay robot                                   │
 ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 👤 TV3: TEMPORAL KALMAN & LỌC BẤT ĐỊNH                [Nhánh: feature/temporal-uncertainty]                      │
 │   • Bộ lọc Kalman 3D làm mượt tọa độ gắp, theo dõi vật trôi trên băng chuyền ảo của Lead                         │
 │   • Đánh giá Bất định (Uncertainty): So sánh với Ground Truth của Sim, ngăn gắp khi có nguy cơ va chạm           │
 ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 👤 TV4: CLOSED-LOOP BRIDGE, HUD & BẰNG CHỨNG          [Nhánh: feature/control-hud-evidence]                      │
 │   • Gửi lệnh điều khiển ngược lại cho Simulator của Lead (Gắp - Phân loại vào thùng)                             │
 │   • Dựng HUD trực quan trên frame Sim + Ghi file CSV Log Trace kiểm chứng                                        │
 │   • Chốt 1 Số đo định lượng (Sai số mm Sim-to-Perception) + 1 Ca lỗi thực nghiệm                                 │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 📋 Bảng Phân Chia Task và File Hướng Dẫn Chi Tiết

| Thành viên | Vai trò | Trụ cột Track 4 phụ trách | Nhánh Git | File nhiệm vụ chi tiết (.md) |
| :---: | :--- | :--- | :--- | :--- |
| **LEADER** | **Robot & Simulator Architect** | **MÔ PHỎNG (Sim2Real)** | `feature/robot-simulator` | [TASK_MEMBER_1_LEADER_SIMULATOR.md](file:///d:/AI_ThựcChiến/Track2/Day13/K4-Track4-Capstone-TeamFanMU/tasks/TASK_MEMBER_1_LEADER_SIMULATOR.md) |
| **TV 1** | **AI Perception Engineer** | **Trụ cột 1: HỌC** (YOLOv8 Material) | `feature/perception-yolo` | [MEMBER_1_PERCEPTION_YOLO.md](file:///d:/AI_ThựcChiến/Track2/Day13/K4-Track4-Capstone-TeamFanMU/tasks/MEMBER_1_PERCEPTION_YOLO.md) |
| **TV 2** | **3D Geometry Engineer** | **Trụ cột 2: HÌNH HỌC** (Camera Projection) | `feature/geometry-3d` | [MEMBER_2_GEOMETRY_3D.md](file:///d:/AI_ThựcChiến/Track2/Day13/K4-Track4-Capstone-TeamFanMU/tasks/MEMBER_2_GEOMETRY_3D.md) |
| **TV 3** | **Temporal & State Estimation** | **Trụ cột 5: THỜI GIAN** (Kalman) + **BẤT ĐỊNH** | `feature/temporal-uncertainty` | [MEMBER_3_TEMPORAL_UNCERTAINTY.md](file:///d:/AI_ThựcChiến/Track2/Day13/K4-Track4-Capstone-TeamFanMU/tasks/MEMBER_3_TEMPORAL_UNCERTAINTY.md) |
| **TV 4** | **Actuator Bridge & Evidence QA** | **Trụ cột 6: DỮ LIỆU** (Log CSV) + **BẰNG CHỨNG** | `feature/control-hud-evidence` | [MEMBER_4_CONTROL_HUD_EVIDENCE.md](file:///d:/AI_ThựcChiến/Track2/Day13/K4-Track4-Capstone-TeamFanMU/tasks/MEMBER_4_CONTROL_HUD_EVIDENCE.md) |

---

### ⏱️ Kế Hoạch 2 Giờ Build
1. **00:00 - 00:15:** Cả nhóm clone repo, đọc file task của mình, tạo branch riêng.
2. **00:15 - 01:15 (60 phút):** 
   - Leader hoàn thiện môi trường Simulator trong `modules/simulator.py`.
   - 4 bạn code song song 4 module theo đúng giao kèo dữ liệu đã chuẩn hóa.
3. **01:15 - 01:40:** Trưởng nhóm merge lần lượt 4 branch vào `main`. Chạy kiểm tra vòng lặp khép kín `main.py`.
4. **01:40 - 01:50:** Ghi nhận 1 số đo định lượng (Sai số mm) và 1 ca lỗi trên màn hình.
5. **01:50 - 02:00:** Quay video backup 30s vào `backup_demo/`, kiểm tra log CSV. **Tất cả 5 thành viên nộp link repo lên VLearn cá nhân.**

---

### 🎤 Kịch Bản Thuyết Trình 10 Phút (Phân công cả 5 thành viên đều nói)
* **00:00 - 01:00 (1 phút - Leader):** Giới thiệu bài toán phân loại phế liệu VinRobotics/VinFast và kiến trúc Simulator.
* **01:00 - 02:00 (1 phút - TV 1):** Trình bày mô hình Perception YOLOv8 chạy trên camera ảo.
* **02:00 - 03:00 (1 phút - TV 2):** Trình bày biến đổi hình học 3D từ pixel sang tọa độ thế giới Sim.
* **03:00 - 04:00 (1 phút - TV 3):** Trình bày bộ lọc Kalman 3D và cơ chế đánh giá Bất định.
* **04:00 - 05:00 (1 phút - TV 4):** Trình bày vòng lặp điều khiển khép kín (Gửi action gắp) và giao diện HUD.
* **05:00 - 07:00 (2 phút - Cả nhóm):** Trình diễn 1 Số đo kiểm chứng (Sai số mm) + 1 Ca lỗi thực nghiệm.
* **07:00 - 10:00 (3 phút):** Hội đồng phản biện (Q&A).
