// ===== i18n =====
const I18N = {
    zh: {
        title: "INT 叙事咨询",
        subtitle: "倾听你的故事，陪你重新书写生命",
        notice: "本系统是基于叙事疗法的 AI 辅助工具，仅作为研究用途，不能替代专业心理咨询。",
        participantPlaceholder: "参与者编号（可选）",
        startBtn: "开始新对话",
        headerTitle: "INT 叙事咨询",
        exportBtn: "导出",
        inputPlaceholder: "说说你的故事...",
        openingMessage: "你好，我是 INT 叙事咨询师~ 很高兴在这里遇见你。叙事疗法相信，每个人都是自己生命故事的专家。你有什么想和我聊聊的吗？",
        historyTitle: "历史对话",
        resumeBtn: "继续",
        anonymous: "匿名",
        turnsUnit: "轮",
        errorRetry: "抱歉，出现了一些问题，请稍后重试。",
        errorConn: "抱歉，连接出现问题，请稍后重试。",
        exportFail: "导出失败，请重试。",
        newChatTitle: "新对话",
        langBtnLabel: "EN",
        htmlLang: "zh-CN",
        stageLabels: {
            "trust building": "建立信任",
            "problem externalization": "问题外化",
            "re-authoring": "重述故事",
            "re-membering": "重组关系",
        },
    },
    en: {
        title: "INT Narrative Therapy",
        subtitle: "Listening to your story, helping you rewrite your life",
        notice: "This is an AI-assisted tool based on narrative therapy, for research purposes only. It cannot replace professional counseling.",
        participantPlaceholder: "Participant ID (optional)",
        startBtn: "Start New Session",
        headerTitle: "INT Narrative Therapy",
        exportBtn: "Export",
        inputPlaceholder: "Share your story...",
        openingMessage: "Hello, I'm your INT narrative therapy counselor. It's wonderful to meet you here. Narrative therapy believes that everyone is the expert of their own life story. What would you like to share with me today?",
        historyTitle: "Previous Sessions",
        resumeBtn: "Resume",
        anonymous: "Anonymous",
        turnsUnit: "turns",
        errorRetry: "Sorry, something went wrong. Please try again later.",
        errorConn: "Sorry, connection failed. Please try again.",
        exportFail: "Export failed. Please try again.",
        newChatTitle: "New Session",
        langBtnLabel: "中",
        htmlLang: "en",
        stageLabels: {
            "trust building": "Trust Building",
            "problem externalization": "Problem Externalization",
            "re-authoring": "Re-authoring",
            "re-membering": "Re-membering",
        },
    },
};

let currentLang = localStorage.getItem("lang") || "zh";

function t(key) {
    return I18N[currentLang][key] ?? I18N.zh[key] ?? key;
}

function applyLang() {
    document.documentElement.lang = t("htmlLang");
    document.title = t("title");
    document.querySelectorAll("[data-i18n]").forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll("[data-i18n-title]").forEach(el => {
        el.title = t(el.dataset.i18nTitle);
    });
    document.querySelectorAll(".lang-toggle").forEach(btn => {
        btn.textContent = t("langBtnLabel");
    });
    // re-render history cards (they contain translated text)
    renderSessionHistory();
}

function toggleLang() {
    currentLang = currentLang === "zh" ? "en" : "zh";
    localStorage.setItem("lang", currentLang);
    applyLang();
}

// ===== 本地 session 历史（用户自己的） =====
function getUserSessions() {
    try {
        return JSON.parse(localStorage.getItem("user_sessions") || "[]");
    } catch {
        return [];
    }
}

function saveUserSession(session) {
    const sessions = getUserSessions().filter(s => s.id !== session.id);
    sessions.unshift(session);
    localStorage.setItem("user_sessions", JSON.stringify(sessions.slice(0, 30)));
}

function updateUserSessionPreview(id, preview, turnCount) {
    const sessions = getUserSessions();
    const s = sessions.find(s => s.id === id);
    if (s) {
        s.preview = preview;
        s.turn_count = turnCount;
        localStorage.setItem("user_sessions", JSON.stringify(sessions));
    }
}

function formatDate(iso) {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const diffH = diffMs / 3600000;
    if (diffH < 1) return currentLang === "zh" ? "刚刚" : "Just now";
    if (diffH < 24) return currentLang === "zh"
        ? `${Math.floor(diffH)} 小时前` : `${Math.floor(diffH)}h ago`;
    if (diffH < 168) {
        const days = Math.floor(diffH / 24);
        return currentLang === "zh" ? `${days} 天前` : `${days}d ago`;
    }
    return d.toLocaleDateString(currentLang === "zh" ? "zh-CN" : "en-US",
        { month: "short", day: "numeric" });
}

function renderSessionHistory() {
    const sessions = getUserSessions();
    const section = document.getElementById("history-section");
    const list = document.getElementById("history-list");
    if (!section || !list) return;

    if (!sessions.length) {
        section.classList.add("hidden");
        return;
    }

    section.classList.remove("hidden");
    list.innerHTML = "";

    sessions.slice(0, 6).forEach(s => {
        const card = document.createElement("div");
        card.className = "session-card";

        const stageLabel = (I18N[currentLang]?.stageLabels ?? {})[s.stage] || s.stage || "";
        const who = s.participant_id || t("anonymous");
        const turns = s.turn_count ?? 0;
        const turnsText = `${turns} ${t("turnsUnit")}`;
        const dateText = formatDate(s.created_at);
        const preview = s.preview || "";

        card.innerHTML = `
            <div class="session-card-meta">
                <span class="session-who">${escapeHtml(who)}</span>
                <span class="session-stage">${escapeHtml(stageLabel)}</span>
                <span class="session-date">${dateText} · ${turnsText}</span>
            </div>
            ${preview ? `<p class="session-preview">${escapeHtml(preview)}</p>` : ""}
            <button class="session-resume-btn">${t("resumeBtn")}</button>
        `;
        card.querySelector(".session-resume-btn")
            .addEventListener("click", (e) => {
                e.stopPropagation();
                resumeSession(s.id, s.participant_id || "");
            });
        list.appendChild(card);
    });
}

// ===== DOM 引用 =====
const API_BASE = "";
let sessionId = null;
let participantId = "";
let isWaiting = false;
let currentTurnCount = 0;

const welcomeScreen  = document.getElementById("welcome-screen");
const chatScreen     = document.getElementById("chat-screen");
const messagesContainer = document.getElementById("messages");
const messageInput   = document.getElementById("message-input");
const sendBtn        = document.getElementById("send-btn");
const exportBtn      = document.getElementById("export-btn");
const startBtn       = document.getElementById("start-btn");
const newChatBtn     = document.getElementById("new-chat-btn");
const participantInput = document.getElementById("participant-id-input");

// ===== 初始化 =====
window.addEventListener("DOMContentLoaded", () => {
    applyLang();

    document.getElementById("lang-btn-welcome").addEventListener("click", toggleLang);
    document.getElementById("lang-btn-chat").addEventListener("click", toggleLang);

    startBtn.addEventListener("click", startChat);
    newChatBtn.addEventListener("click", () => {
        showWelcomeScreen();
    });
    sendBtn.addEventListener("click", sendMessage);
    exportBtn.addEventListener("click", exportSession);

    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendMessage();
        }
    });

    messageInput.addEventListener("input", () => {
        messageInput.style.height = "auto";
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
        sendBtn.disabled = !messageInput.value.trim() || isWaiting;
    });

    participantInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); startChat(); }
    });

    // Always start at welcome screen — no auto-restore
    renderSessionHistory();
});

// ===== 页面切换 =====
function showChatScreen() {
    welcomeScreen.classList.add("hidden");
    chatScreen.classList.remove("hidden");
    setTimeout(() => messageInput.focus(), 100);
}

function showWelcomeScreen() {
    chatScreen.classList.add("hidden");
    welcomeScreen.classList.remove("hidden");
    participantInput.value = "";
    // Refresh history in case new messages were added
    renderSessionHistory();
}

// ===== 开始新对话 =====
async function startChat() {
    participantId = participantInput.value.trim();
    sessionId = crypto.randomUUID();
    currentTurnCount = 0;

    // Save to local history immediately
    saveUserSession({
        id: sessionId,
        participant_id: participantId,
        stage: "trust building",
        created_at: new Date().toISOString(),
        preview: "",
        turn_count: 0,
    });

    messagesContainer.innerHTML = "";
    showChatScreen();
    addMessage("therapist", t("openingMessage"));
}

// ===== 恢复特定 session =====
async function resumeSession(sid, pid) {
    sessionId = sid;
    participantId = pid || "";
    messagesContainer.innerHTML = "";
    showChatScreen();

    try {
        const resp = await fetch(`${API_BASE}/api/session/${sid}`);
        if (!resp.ok) throw new Error("not found");
        const session = await resp.json();
        currentTurnCount = (session.turns || []).length;
        addMessage("therapist", t("openingMessage"));
        for (const turn of (session.turns || [])) {
            if (turn.client)    addMessage("user", turn.client);
            if (turn.therapist) addMessage("therapist", turn.therapist);
        }
    } catch {
        currentTurnCount = 0;
        addMessage("therapist", t("openingMessage"));
    }
}

// ===== 发送消息 =====
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isWaiting) return;

    addMessage("user", text);
    messageInput.value = "";
    messageInput.style.height = "auto";
    sendBtn.disabled = true;
    isWaiting = true;

    const typingId = addTypingIndicator();
    let therapistWrapper = null;

    try {
        const resp = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                message: text,
                participant_id: participantId || undefined,
            }),
        });

        if (!resp.ok) throw new Error("HTTP " + resp.status);

        removeTypingIndicator(typingId);
        therapistWrapper = addMessage("therapist", "");

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalStage = "trust building";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const raw = line.slice(6).trim();
                if (!raw) continue;
                try {
                    const data = JSON.parse(raw);
                    if (data.token != null) {
                        appendToMessage(therapistWrapper, data.token);
                    } else if (data.done === true) {
                        if (data.session_id) sessionId = data.session_id;
                        if (data.stage) finalStage = data.stage;
                    } else if (data.error) {
                        appendToMessage(therapistWrapper, "\n\n" + t("errorRetry"));
                    }
                } catch { /* ignore */ }
            }
        }

        // Update local history with latest preview and turn count
        currentTurnCount += 1;
        updateUserSessionPreview(sessionId, text, currentTurnCount);
        // Also update stage in local history
        const sessions = getUserSessions();
        const s = sessions.find(s => s.id === sessionId);
        if (s) { s.stage = finalStage; localStorage.setItem("user_sessions", JSON.stringify(sessions)); }

    } catch {
        removeTypingIndicator(typingId);
        const msg = t("errorConn");
        if (!therapistWrapper) {
            addMessage("therapist", msg);
        } else {
            const bubble = therapistWrapper.querySelector(".message-bubble");
            if (bubble && !bubble.textContent.trim()) bubble.textContent = msg;
        }
    } finally {
        isWaiting = false;
        sendBtn.disabled = !messageInput.value.trim();
        scrollToBottom();
    }
}

// ===== 消息气泡 =====
function addMessage(role, text) {
    const wrapper = document.createElement("div");
    wrapper.className = `message-wrapper ${role}`;
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    if (role === "therapist") {
        wrapper.innerHTML = `
            <div class="avatar">AI</div>
            <div class="message-content">
                <div class="message-bubble therapist-bubble">${escapeHtml(text)}</div>
                <div class="message-time">${timeStr}</div>
            </div>`;
    } else {
        wrapper.innerHTML = `
            <div class="message-content">
                <div class="message-bubble user-bubble">${escapeHtml(text)}</div>
                <div class="message-time">${timeStr}</div>
            </div>`;
    }
    messagesContainer.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
}

function appendToMessage(wrapper, token) {
    if (!wrapper) return;
    const bubble = wrapper.querySelector(".message-bubble");
    if (bubble) { bubble.textContent += token; scrollToBottom(); }
}

function addTypingIndicator() {
    const id = "typing-" + Date.now();
    const wrapper = document.createElement("div");
    wrapper.id = id;
    wrapper.className = "message-wrapper therapist";
    wrapper.innerHTML = `
        <div class="avatar">AI</div>
        <div class="message-content">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>`;
    messagesContainer.appendChild(wrapper);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    document.getElementById(id)?.remove();
}

function scrollToBottom() {
    messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: "smooth" });
}

// ===== 导出 =====
async function exportSession() {
    if (!sessionId) return;
    try {
        const resp = await fetch(`${API_BASE}/api/export/${sessionId}`);
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `session_${sessionId.slice(0, 8)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch {
        alert(t("exportFail"));
    }
}

// ===== XSS 防护 =====
function escapeHtml(text) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}
