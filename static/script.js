// ---------- State ----------
let sessionId = null;
const STORAGE_KEY = "coding_agent_session_id";

const messagesEl = document.getElementById("messages");
const chatScroll = document.getElementById("chat-scroll");
const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const fileInput = document.getElementById("file-input");
const fileListEl = document.getElementById("file-list");
const welcomeEl = document.getElementById("welcome-msg");
const newChatBtn = document.getElementById("new-chat-btn");

// ---------- Init: resume previous session if browser has one saved ----------
init();

async function init() {
  const savedId = localStorage.getItem(STORAGE_KEY);
  try {
    const res = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: savedId || null }),
    });
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem(STORAGE_KEY, sessionId);

    if (data.resumed) {
      welcomeEl.style.display = "none";
      (data.history || []).forEach((msg) => appendMessage(msg.role === "user" ? "user" : "agent", msg.content));
    }
    renderFileList(data.files || {});
  } catch (err) {
    showError("Session shuru nahi ho saka. Backend chal raha hai?");
  }
}

newChatBtn.addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  location.reload();
});

// ---------- Textarea auto-grow ----------
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// ---------- Send message ----------
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || !sessionId) return;

  appendMessage("user", text);
  input.value = "";
  input.style.height = "auto";
  setBusy(true);

  const thinkingEl = appendThinking();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });

    thinkingEl.remove();

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Kuch ghalat ho gaya." }));
      showError(err.detail || "Kuch ghalat ho gaya.");
      return;
    }

    const data = await res.json();
    appendMessage("agent", data.reply);
    renderFileList(data.files || {});
  } catch (err) {
    thinkingEl.remove();
    showError("Server se connect nahi ho saka.");
  } finally {
    setBusy(false);
  }
});

function setBusy(busy) {
  sendBtn.disabled = busy;
  input.disabled = busy;
}

// ---------- File upload ----------
fileInput.addEventListener("change", async () => {
  if (!sessionId || fileInput.files.length === 0) return;

  for (const file of fileInput.files) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`/api/upload?session_id=${sessionId}`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload fail." }));
        showError(`'${file.name}' upload nahi ho saki: ${err.detail}`);
        continue;
      }
      appendSystemNotice(`📎 '${file.name}' upload ho gayi.`);
    } catch (err) {
      showError(`'${file.name}' upload nahi ho saki.`);
    }
  }

  await refreshFiles();
  fileInput.value = "";
});

async function refreshFiles() {
  if (!sessionId) return;
  try {
    const res = await fetch(`/api/files/${sessionId}`);
    const files = await res.json();
    renderFileList(files);
  } catch (err) {
    /* silent */
  }
}

function renderFileList(files) {
  const names = Object.keys(files);
  fileListEl.innerHTML = "";

  if (names.length === 0) {
    const li = document.createElement("li");
    li.className = "file-empty";
    li.textContent = "koi file nahi";
    fileListEl.appendChild(li);
    return;
  }

  names.forEach((name) => {
    const li = document.createElement("li");
    li.textContent = name;
    li.title = `${name} — dekhne ke liye click karein`;
    li.addEventListener("click", () => openFilePreview(name, files[name]));
    fileListEl.appendChild(li);
  });
}

// ---------- File preview modal ----------
const fileModal = document.getElementById("file-modal");
const fileModalTitle = document.getElementById("file-modal-title");
const fileModalBody = document.getElementById("file-modal-body");
const closeFileModalBtn = document.getElementById("close-file-modal-btn");

function openFilePreview(filename, content) {
  fileModalTitle.textContent = filename;
  const ext = filename.includes(".") ? filename.split(".").pop() : "";
  fileModalBody.innerHTML = formatContent("```" + ext + "\n" + content + "\n```");
  fileModal.hidden = false;
}

closeFileModalBtn.addEventListener("click", () => (fileModal.hidden = true));
fileModal.addEventListener("click", (e) => {
  if (e.target === fileModal) fileModal.hidden = true;
});

// ---------- Previous chats modal ----------
const historyBtn = document.getElementById("history-btn");
const historyModal = document.getElementById("history-modal");
const closeHistoryBtn = document.getElementById("close-history-btn");
const historyList = document.getElementById("history-list");

historyBtn.addEventListener("click", async () => {
  historyModal.hidden = false;
  historyList.innerHTML = "<li class='history-empty'>Load ho raha hai...</li>";
  try {
    const res = await fetch("/api/sessions");
    const list = await res.json();
    renderHistoryModal(list);
  } catch (err) {
    historyList.innerHTML = "<li class='history-empty'>Load nahi ho saka.</li>";
  }
});

closeHistoryBtn.addEventListener("click", () => (historyModal.hidden = true));
historyModal.addEventListener("click", (e) => {
  if (e.target === historyModal) historyModal.hidden = true;
});

function renderHistoryModal(list) {
  historyList.innerHTML = "";
  if (!list || list.length === 0) {
    historyList.innerHTML = "<li class='history-empty'>Koi purani chat nahi mili.</li>";
    return;
  }

  list.forEach((item) => {
    const li = document.createElement("li");
    const isActive = item.session_id === sessionId;
    if (isActive) li.classList.add("active-session");

    const date = item.last_timestamp ? new Date(item.last_timestamp * 1000).toLocaleString() : "";

    const info = document.createElement("div");
    info.className = "hist-info";
    info.innerHTML = `
      <span class="hist-preview">${escapeHtml(item.preview || "(naam nahi)")}</span>
      <span class="hist-time">${escapeHtml(date)}${isActive ? " · <span class='hist-active-tag'>abhi wala</span>" : ""}</span>
    `;
    info.addEventListener("click", () => {
      if (isActive) return;
      localStorage.setItem(STORAGE_KEY, item.session_id);
      location.reload();
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "hist-delete-btn";
    deleteBtn.type = "button";
    deleteBtn.textContent = "🗑";
    deleteBtn.title = "Ye chat delete karein";
    deleteBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Ye chat hamesha ke liye delete ho jayegi. Pakka?")) return;

      await fetch(`/api/sessions/${item.session_id}`, { method: "DELETE" });

      if (isActive) {
        localStorage.removeItem(STORAGE_KEY);
        location.reload();
        return;
      }

      const res = await fetch("/api/sessions");
      renderHistoryModal(await res.json());
    });

    li.appendChild(info);
    li.appendChild(deleteBtn);
    historyList.appendChild(li);
  });
}

// ---------- Message rendering ----------
function appendMessage(role, text) {
  welcomeEl.style.display = "none";

  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const roleLabel = document.createElement("div");
  roleLabel.className = "msg-role";
  roleLabel.textContent = role === "user" ? "aap" : "agent";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = formatContent(text);

  wrap.appendChild(roleLabel);
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  scrollToBottom();
  return wrap;
}

// File-upload jaisi chhoti notifications — welcome message ko hide NAHI
// karti (taaky khali chat screen na dikhe jab tak asal baat-cheet shuru na ho).
function appendSystemNotice(text) {
  const wrap = document.createElement("div");
  wrap.className = "msg system-notice";
  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  scrollToBottom();
  return wrap;
}

const THINKING_PHRASES = [
  "Soch raha hai...",
  "Plan bana raha hai...",
  "Code likh raha hai...",
  "Test kar raha hai...",
];

function appendThinking() {
  const wrap = document.createElement("div");
  wrap.className = "msg agent";
  wrap.innerHTML = `
    <div class="msg-role">agent</div>
    <div class="msg-bubble">
      <div class="thinking">
        <div class="thinking-dots"><span></span><span></span><span></span></div>
        <span class="thinking-label">${THINKING_PHRASES[0]}</span>
      </div>
    </div>
  `;
  messagesEl.appendChild(wrap);
  scrollToBottom();

  // Best-effort: backend abhi real-time status nahi bhejta (single
  // request/response hai), is liye ye sirf ek rotating hint hai, exact
  // sync nahi.
  let i = 0;
  const label = wrap.querySelector(".thinking-label");
  const interval = setInterval(() => {
    i = (i + 1) % THINKING_PHRASES.length;
    if (label) label.textContent = THINKING_PHRASES[i];
  }, 2200);

  const originalRemove = wrap.remove.bind(wrap);
  wrap.remove = () => {
    clearInterval(interval);
    originalRemove();
  };

  return wrap;
}

function showError(text) {
  const wrap = document.createElement("div");
  wrap.className = "msg agent error";
  wrap.innerHTML = `<div class="msg-role">error</div><div class="msg-bubble">${escapeHtml(text)}</div>`;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

// ---------- Minimal markdown-ish formatting (code fences + inline code) ----------
function formatContent(text) {
  const escaped = escapeHtml(text);
  const withBlocks = escaped.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const language = lang || "text";
    return `
      <div class="code-block">
        <div class="code-block-header">
          <span class="code-lang">${language}</span>
          <div class="code-actions">
            <button type="button" class="code-btn copy-btn">Copy</button>
            <button type="button" class="code-btn download-btn" data-lang="${language}">Download</button>
          </div>
        </div>
        <pre><code>${code}</code></pre>
      </div>`;
  });
  const withInline = withBlocks.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  return withInline;
}

function extensionFor(lang) {
  const map = {
    python: "py", py: "py", javascript: "js", js: "js", typescript: "ts", ts: "ts",
    html: "html", css: "css", java: "java", c: "c", cpp: "cpp", "c++": "cpp",
    json: "json", bash: "sh", sh: "sh", shell: "sh", sql: "sql", go: "go",
    rust: "rs", php: "php", ruby: "rb", yaml: "yml", yml: "yml", text: "txt", "": "txt",
  };
  return map[lang.toLowerCase()] || "txt";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Code block copy/download buttons ----------
// document.body par lagaya hai (sirf messagesEl par nahi) taaky file
// preview modal ke andar wale code blocks par bhi kaam kare.
document.body.addEventListener("click", (e) => {
  const copyBtn = e.target.closest(".copy-btn");
  if (copyBtn) {
    const block = copyBtn.closest(".code-block");
    const code = block.querySelector("code").innerText;
    navigator.clipboard.writeText(code).then(() => {
      const original = copyBtn.textContent;
      copyBtn.textContent = "Copied!";
      setTimeout(() => (copyBtn.textContent = original), 1500);
    });
    return;
  }

  const downloadBtn = e.target.closest(".download-btn");
  if (downloadBtn) {
    const block = downloadBtn.closest(".code-block");
    const code = block.querySelector("code").innerText;
    const ext = extensionFor(downloadBtn.dataset.lang || "text");
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `snippet.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }
});