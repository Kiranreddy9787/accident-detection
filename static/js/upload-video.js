(() => {
  const input = document.getElementById("video");
  const selectedFile = document.getElementById("selectedFile");
  const form = document.getElementById("uploadForm");
  const fileDrop = document.getElementById("fileDrop");
  const uploadButton = document.getElementById("uploadButton");
  const picker = document.getElementById("cameraPicker");
  const openRecorder = document.getElementById("openRecorder");
  const recorderPanel = document.getElementById("cameraRecorder");
  const preview = document.getElementById("cameraPreview");
  const start = document.getElementById("startRecording");
  const stop = document.getElementById("stopRecording");
  const status = document.getElementById("cameraStatus");
  let stream;
  let recorder;
  let chunks = [];

  const MAX_FILE_SIZE = 500 * 1024 * 1024;
  const updateSelectedFile = () => {
    const file = input.files[0];
    if (!file) {
      selectedFile.textContent = "No file selected";
      return;
    }
    const size = (file.size / (1024 * 1024)).toFixed(1);
    selectedFile.textContent = `${file.name} · ${size} MB`;
  };

  input.addEventListener("change", updateSelectedFile);
  ["dragenter", "dragover"].forEach(eventName => fileDrop.addEventListener(eventName, event => {
    event.preventDefault();
    fileDrop.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach(eventName => fileDrop.addEventListener(eventName, event => {
    event.preventDefault();
    fileDrop.classList.remove("dragging");
  }));
  fileDrop.addEventListener("drop", event => {
    if (!event.dataTransfer.files.length) return;
    input.files = event.dataTransfer.files;
    updateSelectedFile();
  });

  // This uses the device's camera app on mobile browsers. capture=environment
  // requests the rear-facing camera and is removed immediately afterwards so
  // the ordinary file chooser remains available.
  picker.addEventListener("click", () => {
    input.setAttribute("capture", "environment");
    input.click();
    window.setTimeout(() => input.removeAttribute("capture"), 0);
  });

  openRecorder.addEventListener("click", async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      status.textContent = "This browser does not support in-page recording. Use Connect to camera instead.";
      recorderPanel.hidden = false;
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } }, audio: true,
      });
      preview.srcObject = stream;
      recorderPanel.hidden = false;
      status.textContent = "Camera connected. Start recording when you are ready.";
    } catch (error) {
      recorderPanel.hidden = false;
      status.textContent = "Camera access was not granted. Allow camera permission, then try again.";
    }
  });

  start.addEventListener("click", () => {
    if (!stream) return;
    const preferredType = ["video/mp4", "video/webm;codecs=vp9,opus", "video/webm"]
      .find(type => MediaRecorder.isTypeSupported(type));
    recorder = preferredType ? new MediaRecorder(stream, { mimeType: preferredType }) : new MediaRecorder(stream);
    chunks = [];
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.onstop = () => {
      const mimeType = recorder.mimeType || preferredType || "video/webm";
      const extension = mimeType.includes("mp4") ? "mp4" : "webm";
      const file = new File([new Blob(chunks, { type: mimeType })], `camera-recording-${Date.now()}.${extension}`, { type: mimeType });
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      selectedFile.textContent = `Recorded: ${file.name}`;
      status.textContent = "Recording is ready to upload.";
      stream.getTracks().forEach(track => track.stop());
      preview.srcObject = null;
      start.disabled = false;
      stop.disabled = true;
    };
    recorder.start();
    status.textContent = "Recording…";
    start.disabled = true;
    stop.disabled = false;
  });

  stop.addEventListener("click", () => { if (recorder?.state === "recording") recorder.stop(); });
  form.addEventListener("submit", event => {
    const file = input.files[0];
    if (!file) return;
    if (file.size > MAX_FILE_SIZE) {
      event.preventDefault();
      selectedFile.textContent = "This video is larger than the 500 MB upload limit.";
      return;
    }
    uploadButton.disabled = true;
    uploadButton.setAttribute("aria-busy", "true");
    uploadButton.firstChild.textContent = "Uploading video… ";
  });
  window.addEventListener("pagehide", () => stream?.getTracks().forEach(track => track.stop()));
})();
