/**
 * app.js — EduSimplify frontend logic (v2)
 *
 * Architecture:
 *   - Hero view: user pastes content, chooses level/language, clicks "Simplify Now".
 *   - Dashboard view: revealed after first result; seven independent result cards.
 *   - Each result card has its own Generate button, mini-spinner, output area,
 *     and Copy button.
 *   - Follow-up Q&A card lives at the bottom of the dashboard.
 *   - "← New Content" returns to the hero view.
 *
 * Backend API is unchanged — same endpoints, same request/response shape.
 */

/* ── DOM: shared inputs (always in DOM) ─────────────────────────────────── */
const contentInput   = document.getElementById("content-input");
const levelSelect    = document.getElementById("level-select");
const languageSelect = document.getElementById("language-select");
const inputError     = document.getElementById("input-error");
const charCount      = document.getElementById("char-count");
const charWarning    = document.getElementById("char-warning");

/* ── DOM: views ─────────────────────────────────────────────────────────── */
const heroSection    = document.getElementById("hero-section");
const resultsSection = document.getElementById("results-section");

/* ── DOM: hero CTA ──────────────────────────────────────────────────────── */
const simplifyBtn    = document.getElementById("simplify-btn");

/* ── DOM: dashboard ─────────────────────────────────────────────────────── */
const newContentBtn  = document.getElementById("new-content-btn");

/* ── DOM: follow-up ─────────────────────────────────────────────────────── */
const followupInput  = document.getElementById("followup-input");
const followupBtn    = document.getElementById("followup-btn");

/* ── Constants ──────────────────────────────────────────────────────────── */
const MAX_CHARS  = 5000;
const WARN_CHARS = 4000;

/**
 * Maps each API endpoint name to the result-card element ID it populates.
 * The follow-up card is handled separately.
 */
const ENDPOINT_TO_CARD = {
  simplify:  "card-simplify",
  keypoints: "card-keypoints",
  terms:     "card-terms",
  example:   "card-example",
  summary:   "card-summary",
  questions: "card-questions",
};

/* ── Live character counter ─────────────────────────────────────────────── */
contentInput.addEventListener("input", () => {
  const len = contentInput.value.length;
  charCount.textContent = len;

  if (len >= WARN_CHARS) {
    charWarning.classList.remove("hidden");
    charCount.style.color = len >= MAX_CHARS ? "var(--danger)" : "var(--warning)";
  } else {
    charWarning.classList.add("hidden");
    charCount.style.color = "";
  }
});

/* ── Hero "Simplify Now" button ─────────────────────────────────────────── */
simplifyBtn.addEventListener("click", async () => {
  const content = contentInput.value.trim();
  if (!validateContent(content)) return;

  // Reveal the dashboard first, then generate the simplification.
  showDashboard();
  await generateForCard("simplify");
});

/* ── "← New Content" button ─────────────────────────────────────────────── */
newContentBtn.addEventListener("click", () => {
  showHero();
});

/* ── Result card Generate buttons ───────────────────────────────────────── */
// Each card in the dashboard has a button with [data-endpoint].
// We delegate from the results section to handle all of them.
resultsSection.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-endpoint]");
  if (!btn || btn.id === "simplify-btn") return;   // ignore the hero CTA

  const endpoint = btn.dataset.endpoint;
  if (endpoint && ENDPOINT_TO_CARD[endpoint]) {
    generateForCard(endpoint);
  }
});

/* ── Follow-up button ───────────────────────────────────────────────────── */
followupBtn.addEventListener("click", () => {
  callFollowUp();
});

/* ── Copy buttons ───────────────────────────────────────────────────────── */
// Delegated: all .btn-copy buttons inside any result card.
resultsSection.addEventListener("click", async (e) => {
  const btn = e.target.closest(".btn-copy");
  if (!btn) return;

  // Find the output div in the same card.
  const card   = btn.closest(".result-card");
  const output = card.querySelector(".rc-output");
  const text   = output ? (output.innerText || output.textContent) : "";

  try {
    await navigator.clipboard.writeText(text);
    btn.textContent = "✅ Copied!";
    setTimeout(() => { btn.textContent = "📋 Copy"; }, 2000);
  } catch {
    btn.textContent = "⚠️ Copy failed";
    setTimeout(() => { btn.textContent = "📋 Copy"; }, 2000);
  }
});

/* ═══════════════════════════════════════════════════════════════════════════
   CORE: generate a result into a specific card
═══════════════════════════════════════════════════════════════════════════ */

/**
 * Fetch a result from the backend and populate the corresponding result card.
 * @param {string} endpoint - API path segment ("simplify", "keypoints", etc.)
 */
async function generateForCard(endpoint) {
  const content  = contentInput.value.trim();
  const level    = levelSelect.value;
  const language = languageSelect.value;

  if (!validateContent(content)) {
    showHero();   // take user back to fix the content
    return;
  }

  const cardId = ENDPOINT_TO_CARD[endpoint];
  const card   = document.getElementById(cardId);
  if (!card) return;

  setCardLoading(card, true);

  try {
    const res  = await fetch(`/api/${endpoint}`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ content, level, language }),
    });
    const data = await res.json();

    if (data.error) {
      setCardError(card, data.error);
    } else {
      setCardResult(card, data.result);
    }
  } catch {
    setCardError(card, "Could not reach the server. Please check your connection.");
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   CORE: follow-up Q&A
═══════════════════════════════════════════════════════════════════════════ */

async function callFollowUp() {
  const content  = contentInput.value.trim();
  const level    = levelSelect.value;
  const language = languageSelect.value;
  const question = followupInput.value.trim();

  if (!validateContent(content)) {
    showHero();
    return;
  }

  if (!question) {
    followupInput.focus();
    followupInput.style.borderColor = "var(--danger)";
    setTimeout(() => { followupInput.style.borderColor = ""; }, 2000);
    return;
  }

  const card = document.getElementById("card-followup");
  setFollowUpLoading(true);

  try {
    const res  = await fetch("/api/followup", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ content, level, language, question }),
    });
    const data = await res.json();

    if (data.error) {
      setFollowUpResult(data.error, true);
    } else {
      setFollowUpResult(data.result, false);
    }
  } catch {
    setFollowUpResult("Could not reach the server. Please check your connection.", true);
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   CARD STATE HELPERS
═══════════════════════════════════════════════════════════════════════════ */

/**
 * Show or hide the mini-spinner and disable/enable the Generate button.
 * @param {HTMLElement} card
 * @param {boolean} loading
 */
function setCardLoading(card, loading) {
  const spinner    = card.querySelector(".rc-loading");
  const output     = card.querySelector(".rc-output");
  const generateBtn = card.querySelector(".btn-rc");

  if (loading) {
    spinner.classList.remove("hidden");
    output.classList.add("hidden");
    if (generateBtn) generateBtn.disabled = true;
  } else {
    spinner.classList.add("hidden");
    output.classList.remove("hidden");
    if (generateBtn) generateBtn.disabled = false;
  }
}

/**
 * Populate a result card with AI-generated text.
 * @param {HTMLElement} card
 * @param {string} text
 */
function setCardResult(card, text) {
  setCardLoading(card, false);

  const output = card.querySelector(".rc-output");
  const foot   = card.querySelector(".rc-foot");

  // textContent prevents HTML injection from AI output.
  output.textContent = text;
  output.classList.remove("rc-placeholder");
  card.classList.add("has-content");

  // Show the Copy button.
  if (foot) foot.classList.remove("hidden");
}

/**
 * Show an error message inside a result card.
 * @param {HTMLElement} card
 * @param {string} message
 */
function setCardError(card, message) {
  setCardLoading(card, false);

  const output = card.querySelector(".rc-output");
  output.textContent = `⚠️ ${message}`;
  output.classList.remove("rc-placeholder");
  output.style.color = "var(--danger)";

  // Reset color on next successful result.
  output.dataset.hasError = "true";
}

/* Follow-up specific helpers */
function setFollowUpLoading(loading) {
  const card    = document.getElementById("card-followup");
  const spinner = card.querySelector(".rc-loading");
  const output  = document.getElementById("followup-output");
  const foot    = document.getElementById("followup-foot");

  followupBtn.disabled = loading;

  if (loading) {
    spinner.classList.remove("hidden");
    output.classList.add("hidden");
    if (foot) foot.classList.add("hidden");
  } else {
    spinner.classList.add("hidden");
    output.classList.remove("hidden");
  }
}

function setFollowUpResult(text, isError) {
  setFollowUpLoading(false);

  const output = document.getElementById("followup-output");
  const foot   = document.getElementById("followup-foot");

  output.textContent = isError ? `⚠️ ${text}` : text;
  output.classList.remove("rc-placeholder");
  output.style.color = isError ? "var(--danger)" : "";

  if (!isError && foot) foot.classList.remove("hidden");
}

/* ═══════════════════════════════════════════════════════════════════════════
   VIEW SWITCHING
═══════════════════════════════════════════════════════════════════════════ */

/** Switch to the results dashboard view. */
function showDashboard() {
  heroSection.classList.add("hidden");
  resultsSection.classList.remove("hidden");
  // Scroll to top of dashboard.
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

/** Return to the hero input view. */
function showHero() {
  resultsSection.classList.add("hidden");
  heroSection.classList.remove("hidden");
  clearInputError();
  heroSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ═══════════════════════════════════════════════════════════════════════════
   INPUT VALIDATION
═══════════════════════════════════════════════════════════════════════════ */

/**
 * Validate the textarea. Returns true if valid, false + shows error if not.
 * @param {string} content - Trimmed textarea value.
 * @returns {boolean}
 */
function validateContent(content) {
  clearInputError();

  if (!content) {
    showInputError("Please paste or type some academic content before generating.");
    contentInput.focus();
    return false;
  }

  if (content.length > MAX_CHARS) {
    showInputError(
      `Content is too long (${content.length} characters). ` +
      `Please trim it to ${MAX_CHARS} characters or fewer.`
    );
    contentInput.focus();
    return false;
  }

  return true;
}

function showInputError(message) {
  inputError.textContent = message;
  inputError.classList.remove("hidden");
}

function clearInputError() {
  inputError.textContent = "";
  inputError.classList.add("hidden");
}

/* ═══════════════════════════════════════════════════════════════════════════
   FILE UPLOAD — tab switching, drop-zone, text extraction, quick actions
   All code below is additive; nothing above is changed.
═══════════════════════════════════════════════════════════════════════════ */

/* ── DOM refs (upload) ──────────────────────────────────────────────────── */
const tabType        = document.getElementById("tab-type");
const tabUpload      = document.getElementById("tab-upload");
const typePanel      = document.getElementById("type-panel");
const uploadPanel    = document.getElementById("upload-panel");

const dropZone       = document.getElementById("drop-zone");
const fileInput      = document.getElementById("file-input");
const uploadSpinner  = document.getElementById("upload-spinner");
const uploadError    = document.getElementById("upload-error");
const fileInfo       = document.getElementById("file-info");
const fileInfoName   = document.getElementById("file-info-name");
const fileInfoSize   = document.getElementById("file-info-size");
const fileClearBtn   = document.getElementById("file-clear-btn");
const extractedPrev  = document.getElementById("extracted-preview");
const extractedText  = document.getElementById("extracted-text");
const docActions     = document.getElementById("doc-actions");

/** Stores the text most recently extracted from an uploaded file. */
let _extractedContent = "";

/* ── Tab switching ──────────────────────────────────────────────────────── */

tabType.addEventListener("click", () => switchTab("type"));
tabUpload.addEventListener("click", () => switchTab("upload"));

/**
 * Switch between "Type / Paste" and "Upload File" tabs.
 * @param {"type"|"upload"} tab
 */
function switchTab(tab) {
  if (tab === "type") {
    tabType.classList.add("active");
    tabType.setAttribute("aria-selected", "true");
    tabUpload.classList.remove("active");
    tabUpload.setAttribute("aria-selected", "false");
    typePanel.classList.remove("hidden-panel");
    uploadPanel.classList.remove("active");
  } else {
    tabUpload.classList.add("active");
    tabUpload.setAttribute("aria-selected", "true");
    tabType.classList.remove("active");
    tabType.setAttribute("aria-selected", "false");
    uploadPanel.classList.add("active");
    typePanel.classList.add("hidden-panel");
  }
  clearInputError();
}

/* ── Drag-and-drop on the drop zone ─────────────────────────────────────── */

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFile(file);
});

/* ── File input change (click to browse) ────────────────────────────────── */
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

/* ── Clear button ───────────────────────────────────────────────────────── */
fileClearBtn.addEventListener("click", resetUpload);

/* ─────────────────────────────────────────────────────────────────────────
   handleFile — validate client-side, POST to /api/upload, show result
───────────────────────────────────────────────────────────────────────── */

const MAX_UPLOAD_MB   = 5;
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;
const ALLOWED_EXTS    = ["pdf", "txt"];

/**
 * Client-side validate and upload a file to /api/upload.
 * @param {File} file
 */
async function handleFile(file) {
  resetUpload();
  hideUploadError();

  // Client-side extension check.
  const ext = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED_EXTS.includes(ext)) {
    showUploadError(
      `Unsupported file type ".${ext}". Please upload a PDF or .txt file.`
    );
    return;
  }

  // Client-side size check.
  if (file.size > MAX_UPLOAD_BYTES) {
    const mb = (file.size / (1024 * 1024)).toFixed(1);
    showUploadError(
      `File is too large (${mb} MB). Maximum allowed size is ${MAX_UPLOAD_MB} MB.`
    );
    return;
  }

  // Show spinner, disable doc-action buttons.
  uploadSpinner.classList.add("visible");
  setDocActionButtons(true);

  // Build multipart form data.
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res  = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (data.error) {
      showUploadError(data.error);
      return;
    }

    // Success — show file info strip, extracted text, and quick-action buttons.
    _extractedContent = data.text;

    fileInfoName.textContent = data.filename;
    fileInfoSize.textContent = formatBytes(file.size);
    fileInfo.classList.add("visible");

    extractedText.value = data.text;
    extractedPrev.classList.add("visible");

    docActions.classList.add("visible");
    setDocActionButtons(false);

  } catch {
    showUploadError("Could not reach the server. Please check your connection.");
  } finally {
    uploadSpinner.classList.remove("visible");
  }
}

/* ─────────────────────────────────────────────────────────────────────────
   Quick-action buttons — "Simplify Entire Document", "Simplify Selection", etc.
───────────────────────────────────────────────────────────────────────── */

docActions.addEventListener("click", (e) => {
  const btn      = e.target.closest(".btn-doc-action");
  if (!btn) return;
  const docEndpt = btn.dataset.docEndpoint;
  if (!docEndpt) return;

  handleDocAction(docEndpt);
});

/**
 * Copy extracted (or selected) text into the main textarea, switch to the
 * type tab, and trigger the matching feature endpoint on the dashboard.
 *
 * "simplify-selection" uses whatever text the student has highlighted inside
 * the editable extracted-text preview; all others use the full extracted text.
 *
 * @param {string} docEndpoint - one of the data-doc-endpoint values
 */
async function handleDocAction(docEndpoint) {
  let textToUse = extractedText.value.trim();

  if (docEndpoint === "simplify-selection") {
    // Use highlighted text if the student selected some.
    const sel = window.getSelection ? window.getSelection().toString().trim() : "";
    const selInTextarea =
      extractedText.selectionStart !== extractedText.selectionEnd
        ? extractedText.value.slice(
            extractedText.selectionStart,
            extractedText.selectionEnd
          ).trim()
        : "";

    if (selInTextarea) {
      textToUse = selInTextarea;
    } else if (sel) {
      textToUse = sel;
    }
    // If nothing selected, fall through to the full document text.
  }

  if (!textToUse) {
    showUploadError("No text available. Please upload a file first.");
    return;
  }

  // Truncate to 5000 chars with a clear notice rather than silently cutting off.
  if (textToUse.length > 5000) {
    textToUse = textToUse.slice(0, 5000);
  }

  // Populate the hidden textarea that all existing generate logic reads.
  contentInput.value = textToUse;

  // Trigger a synthetic input event so the character counter updates.
  contentInput.dispatchEvent(new Event("input"));

  // Map doc endpoint names to the real API endpoint names.
  const apiEndpoint =
    docEndpoint === "simplify-selection" ? "simplify" : docEndpoint;

  // Switch to type tab so the user can see the content that will be sent.
  switchTab("type");

  // Reveal the dashboard and run the generation.
  showDashboard();
  await generateForCard(apiEndpoint);
}

/* ─────────────────────────────────────────────────────────────────────────
   Upload UI helpers
───────────────────────────────────────────────────────────────────────── */

/** Reset the upload panel to its initial empty state. */
function resetUpload() {
  // Reset file input so the same file can be re-selected.
  fileInput.value = "";
  _extractedContent = "";

  fileInfo.classList.remove("visible");
  fileInfoName.textContent = "";
  fileInfoSize.textContent = "";

  extractedText.value = "";
  extractedPrev.classList.remove("visible");

  docActions.classList.remove("visible");
  setDocActionButtons(false);

  uploadSpinner.classList.remove("visible");
  hideUploadError();
}

/**
 * Show an error message in the upload panel.
 * @param {string} msg
 */
function showUploadError(msg) {
  uploadError.textContent = msg;
  uploadError.classList.remove("hidden");
}

function hideUploadError() {
  uploadError.textContent = "";
  uploadError.classList.add("hidden");
}

/**
 * Enable or disable all doc-action buttons.
 * @param {boolean} disabled
 */
function setDocActionButtons(disabled) {
  docActions.querySelectorAll(".btn-doc-action").forEach((b) => {
    b.disabled = disabled;
  });
}

/**
 * Format a byte count as a human-readable string.
 * @param {number} bytes
 * @returns {string}
 */
function formatBytes(bytes) {
  if (bytes < 1024)       return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
