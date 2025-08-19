const DEFAULT_NOTES = window.DEFAULT_NOTES;
const PURCHASE_KEY = window.PURCHASE_KEY;

const elScope = document.getElementById("scope");
const scopeBtns = document.querySelectorAll(".scope-btn");
const noteChild = document.getElementById("note_child");
const noteChildCount = document.getElementById("childNoteCount");
const startsEl = document.getElementById("starts_at");
const endsEl = document.getElementById("ends_at");
const presetBtns = document.querySelectorAll(".preset-btn");
const submitBtn = document.querySelector('button[type="submit"]');
const originalBtnContent = submitBtn.innerHTML;
const childSearch      = document.getElementById("childSearch");
const clearSearch      = document.getElementById("clearSearch");
const childBox         = document.getElementById("childBox");
const childChecks      = () => Array.from(document.querySelectorAll(".child-check"));
const chipsWrap        = document.getElementById("chips");
const childIdsHidden   = document.getElementById("child_ids");
const selCount         = document.getElementById("selCount");
const selectVisibleBtn = document.getElementById("selectVisible");
const clearAllBtn      = document.getElementById("clearAll");

function setScopeActive(val) {
  elScope.value = val;
  scopeBtns.forEach(b => b.dataset.active = (b.dataset.value === val) ? "true" : "false");
  if (DEFAULT_NOTES[val]) {
    noteChild.value = DEFAULT_NOTES[val];
    updateChildNoteCount();
  }
}

function updateChildNoteCount() {
  noteChildCount.textContent = `${noteChild.value.length}/140`;
}

function parseLocalDatetime(input) {
  if (!input) return null;
  const d = new Date(input);
  return isNaN(d.getTime()) ? null : d;
}

function formatToLocalInput(dt) {
  if (!dt) return "";
  const pad = n => `${n}`.padStart(2,"0");
  const y = dt.getFullYear();
  const m = pad(dt.getMonth()+1);
  const d = pad(dt.getDate());
  const hh = pad(dt.getHours());
  const mm = pad(dt.getMinutes());
  return `${y}-${m}-${d}T${hh}:${mm}`;
}

function applyPreset(key) {
  const start = parseLocalDatetime(startsEl.value);
  if (!start) return;

  if (key === "indefinite") { endsEl.value = ""; return; }

  if (key === "eod_il") {
    const eod = new Date(start);
    eod.setHours(23,59,0,0);
    endsEl.value = formatToLocalInput(eod);
    return;
  }

  const days = parseInt(key, 10);
  if (!isNaN(days)) {
    const end = new Date(start);
    end.setDate(end.getDate() + days);
    endsEl.value = formatToLocalInput(end);
  }
}

function updateSelectedUIFromChecks() {
  const selected = childChecks().filter(ch => ch.checked);
  selCount.textContent = `${selected.length} נבחרו`;
  chipsWrap.innerHTML = "";
  selected.slice(0, 10).forEach(ch => {
    const chip = document.createElement("span");
    chip.className = "rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700";
    const row = ch.closest(".child-row");
    chip.textContent = row ? row.querySelector("span")?.textContent?.trim() || ch.value : ch.value;
    chipsWrap.appendChild(chip);
  });
  childIdsHidden.value = selected.map(ch => ch.value).join(",");
}

function filterChildren() {
  const q = childSearch.value.trim().toLowerCase();
  const rows = Array.from(document.querySelectorAll(".child-row"));
  rows.forEach(row => {
    const username = row.querySelector(".child-check")?.dataset.username || "";
    row.style.display = username.includes(q) ? "" : "none";
  });
  selCount.classList.toggle("text-brand-700", q.length > 0);
}

function selectVisible() {
  const rows = Array.from(document.querySelectorAll(".child-row"));
  rows.forEach(row => {
    if (row.style.display !== "none") {
      const ch = row.querySelector(".child-check");
      if (ch) ch.checked = true;
    }
  });
  updateSelectedUIFromChecks();
}

function clearAll() {
  childChecks().forEach(ch => ch.checked = false);
  updateSelectedUIFromChecks();
}

// Events
scopeBtns.forEach(btn => btn.addEventListener("click", () => setScopeActive(btn.dataset.value)));

presetBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    btn.classList.add("ring-2","ring-brand-300");
    setTimeout(() => btn.classList.remove("ring-2","ring-brand-300"), 400);
    applyPreset(btn.dataset.preset);
  });
});

childBox.addEventListener("change", (e) => {
  if (e.target.classList.contains("child-check")) updateSelectedUIFromChecks();
});

childSearch.addEventListener("input", filterChildren);
clearSearch.addEventListener("click", () => { childSearch.value = ""; filterChildren(); });

selectVisibleBtn.addEventListener("click", () => {
  selectVisible();
  selectVisibleBtn.classList.add("ring-2","ring-brand-300");
  setTimeout(() => selectVisibleBtn.classList.remove("ring-2","ring-brand-300"), 400);
});

clearAllBtn.addEventListener("click", () => {
  clearAll();
  clearAllBtn.classList.add("ring-2","ring-brand-300");
  setTimeout(() => clearAllBtn.classList.remove("ring-2","ring-brand-300"), 400);
});

document.getElementById("banForm").addEventListener("submit", (e) => {
  if (!childIdsHidden.value) {
    e.preventDefault();
    selCount.classList.add("animate-pingsoft","text-brand-700");
    setTimeout(() => selCount.classList.remove("animate-pingsoft","text-brand-700"), 1200);
  }
});

document.getElementById("banForm").addEventListener("submit", (e) => {
  if (!childIdsHidden.value) {
    e.preventDefault();
    selCount.classList.add("animate-pingsoft","text-brand-700");
    setTimeout(() => selCount.classList.remove("animate-pingsoft","text-brand-700"), 1200);
    return;
  }
  // Disable button and show spinner
  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <div class="flex items-center justify-center gap-2">
      <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span>שומר...</span>
    </div>
  `;
  submitBtn.classList.add("opacity-75", "cursor-not-allowed");
  submitBtn.classList.remove("hover:bg-brand-700", "active:scale-[0.99]");
});

// Init
setScopeActive(PURCHASE_KEY);
updateChildNoteCount();
filterChildren();
updateSelectedUIFromChecks();