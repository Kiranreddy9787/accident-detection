const menuButton = document.getElementById("menuButton");
const sidebar = document.getElementById("sidebar");
const analysisVideo = document.getElementById("analysisVideo");
const playbackTime = document.getElementById("playbackTime");
const analysisForm = document.getElementById("analysisForm");

if (menuButton && sidebar) menuButton.addEventListener("click", () => sidebar.classList.toggle("open"));
if (analysisVideo && playbackTime) {
  analysisVideo.addEventListener("timeupdate", () => {
    const seconds = Math.floor(analysisVideo.currentTime || 0);
    playbackTime.textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  });
}

if (analysisForm) {
  analysisForm.addEventListener("submit", () => {
    const button = analysisForm.querySelector("button[type='submit']");
    if (!button) return;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.querySelector(".button-label").textContent = "Analyzing video…";
    const note = analysisForm.querySelector(".analysis-note");
    if (note) note.textContent = "Analysis is running. This can take a few minutes for longer videos.";
  });
}
