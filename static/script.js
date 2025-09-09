// static/script.js
document.addEventListener("DOMContentLoaded", () => {
  console.log("Enhanced FaceRecognitionApp loaded ✅");

  // ---- Registration photo preview ----
  const fileInput = document.querySelector("input[type='file']");
  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const previewBox = document.querySelector("#preview");
      if (!previewBox) return;
      previewBox.innerHTML = ""; // clear
      const file = e.target.files[0];
      if (file) {
        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        img.className = "thumb";
        previewBox.appendChild(img);
      }
    });
  }

  // ---- Admin search filter ----
  const searchInput = document.querySelector("#search");
  if (searchInput) {
    searchInput.addEventListener("keyup", () => {
      const filter = searchInput.value.toLowerCase();
      document.querySelectorAll(".entries tbody tr").forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? "" : "none";
      });
    });
  }

  // ---- Highlight pending rows ----
  document.querySelectorAll(".entries tbody tr").forEach(row => {
    const status = row.querySelector("td:nth-child(6)")?.innerText.trim().toLowerCase();
    if (status === "pending") {
      row.style.backgroundColor = "rgba(255,200,100,0.08)";
      row.style.transition = "background 0.5s ease";
    }
  });
});
