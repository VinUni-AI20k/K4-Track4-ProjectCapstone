(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var sequence = 0, currentUrl = null, connected = false;

  function setMessage(title, detail) {
    $("run-state").textContent = title;
    $("run-detail").textContent = detail;
  }

  function showToast(message) {
    var toast = $("toast");
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(function () { toast.classList.remove("show"); }, 2400);
  }

  function setConnected(state) {
    var justConnected = !connected;
    connected = true;
    document.body.classList.add("integrated");
    window.robotBridgeConnected = true;
    $("camera-card").hidden = false;
    $("integration-controls").hidden = false;
    if (justConnected) {
      $("camera-state").textContent = "ĐANG CHỜ CAMERA";
      $("camera-placeholder").textContent = "Đang nhận hình từ webcam…";
    }
    $("connection").textContent = "ROBOT ĐÃ KẾT NỐI";
    document.querySelector(".live-dot").classList.remove("offline");
    var armMode = state.control_mode === "arm";
    var demoButton = $("demo-button");
    demoButton.style.display = armMode ? "none" : "";
    $("reset-button").style.display = "none";
    var trialButton = document.querySelector('[data-input="t"]');
    trialButton.style.display = armMode ? "none" : "";
    if (!window.THREE) {
      setMessage(state.controller_state || "Đã nối webcam và robot", state.message || "Nhấn C để hiệu chuẩn cánh tay.");
      if (state.ee_xyz) {
        ["coord-x", "coord-y", "coord-z"].forEach(function (id, i) {
          $(id).innerHTML = Number(state.ee_xyz[i]).toFixed(2) + " <small>m</small>";
        });
      }
    }
  }

  function pollState() {
    fetch("/api/state", {cache: "no-store"})
      .then(function (response) {
        if (!response.ok) throw new Error("state unavailable");
        return response.json();
      })
      .then(function (state) {
        if (state.active && state.ready) {
          setConnected(state);
        } else if (!state.active) {
          connected = false;
          window.robotBridgeConnected = false;
          document.body.classList.remove("integrated");
          $("integration-controls").hidden = true;
          $("camera-card").hidden = false;
          $("connection").textContent = "CHƯA NỐI ROBOT";
          document.querySelector(".live-dot").classList.add("offline");
          $("camera-state").textContent = "CHƯA KẾT NỐI";
          $("camera-placeholder").hidden = false;
          $("camera-placeholder").textContent = "Chạy ./run-demo.ps1 để nối webcam và robot; không mở riêng simulation/serve.py.";
          setMessage("Chưa nối webcam và robot", "Chạy sản phẩm bằng ./run-demo.ps1 từ thư mục gốc repo.");
        } else {
          document.body.classList.remove("integrated");
          $("camera-card").hidden = false;
          $("connection").textContent = "ĐANG KẾT NỐI ROBOT";
          document.querySelector(".live-dot").classList.remove("offline");
          $("camera-state").textContent = "ĐANG CHỜ CAMERA";
          $("camera-placeholder").hidden = false;
          $("camera-placeholder").textContent = "Đang khởi động webcam và PyBullet…";
          setMessage("Đang kết nối", "Giữ trang này mở trong khi main.py khởi động.");
        }
      })
      .catch(function () {
        connected = false;
        window.robotBridgeConnected = false;
        document.body.classList.remove("integrated");
        $("integration-controls").hidden = true;
        $("camera-card").hidden = false;
        $("connection").textContent = "MAIN NGOẠI TUYẾN";
        document.querySelector(".live-dot").classList.add("offline");
        $("camera-state").textContent = "CHƯA KẾT NỐI";
        $("camera-placeholder").hidden = false;
        $("camera-placeholder").textContent = "Không thấy main.py. Hãy chạy ./run-demo.ps1 và mở đúng URL được in trong terminal.";
        setMessage("Không kết nối được main.py", "Mở đúng địa chỉ localhost do ./run-demo.ps1 in ra.");
      })
      .finally(function () { window.setTimeout(pollState, 250); });
  }

  function pollCamera() {
    if (!connected) {
      window.setTimeout(pollCamera, 250);
      return;
    }
    fetch("/api/camera.jpg?after=" + sequence, {cache: "no-store"})
      .then(function (response) {
        if (response.status === 204) return null;
        if (!response.ok) throw new Error("camera unavailable");
        var nextSequence = Number(response.headers.get("X-Frame-Id") || sequence);
        return response.blob().then(function (blob) { return {sequence: nextSequence, blob: blob}; });
      })
      .then(function (frame) {
        if (!frame) return;
        sequence = frame.sequence;
        var nextUrl = URL.createObjectURL(frame.blob);
        var previousUrl = currentUrl;
        currentUrl = nextUrl;
        $("camera-frame").src = nextUrl;
        $("camera-frame").classList.add("live");
        $("camera-placeholder").hidden = true;
        $("camera-state").textContent = "LIVE · KEYPOINTS";
        if (previousUrl) window.setTimeout(function () { URL.revokeObjectURL(previousUrl); }, 1000);
      })
      .catch(function () {
        $("camera-state").textContent = "CAMERA NGOẠI TUYẾN";
        $("camera-placeholder").hidden = false;
        $("camera-placeholder").textContent = "Robot đã nối nhưng chưa nhận khung hình từ webcam. Kiểm tra camera hoặc dùng --source 1.";
      })
      .finally(function () { window.setTimeout(pollCamera, 80); });
  }

  function sendInput(key) {
    fetch("/api/input", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({key: key})
    }).then(function (response) {
      if (!response.ok) throw new Error("input rejected");
      showToast("Đã gửi lệnh " + key.toUpperCase() + " tới robot");
    }).catch(function () {
      showToast("Không gửi được lệnh; kiểm tra kết nối main.py");
    });
  }
  window.robotBridgeSendInput = sendInput;

  document.querySelectorAll("#integration-controls [data-input]").forEach(function (button) {
    button.addEventListener("click", function () {
      sendInput(button.getAttribute("data-input"));
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) return;
    if (/INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
    var key = event.key.toLowerCase();
    if (connected && ["p", "c", "r", "q", "t"].indexOf(key) >= 0) sendInput(key);
  });

  window.robotBridgeConnected = false;
  window.setTimeout(function () {
    if (!window.THREE) $("loading").classList.add("done");
  }, 3000);
  pollState();
  pollCamera();
})();
