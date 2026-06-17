// ===== 国际化 / i18n =====
const I18N = {
    zh: {
        title: "INT 叙事咨询",
        subtitle: "倾听你的故事，陪你重新书写生命",
        notice: "本系统是基于叙事疗法的 AI 辅助工具，仅作为研究用途，不能替代专业心理咨询。",
        participantPlaceholder: "请输入您的参与者编号（可选）",
        startBtn: "开始对话",
        headerTitle: "INT 叙事咨询",
        exportBtn: "导出记录",
        inputPlaceholder: "说说你的故事...",
        openingMessage: "你好，我是 INT 叙事咨询师~ 很高兴在这里遇见你。叙事疗法相信，每个人都是自己生命故事的专家。你有什么想和我聊聊的吗？",
        errorRetry: "抱歉，出现了一些问题，请稍后重试。",
        errorConn: "抱歉，连接出现问题，请稍后重试。",
        exportFail: "导出失败，请重试。",
        langBtnLabel: "EN",
        htmlLang: "zh-CN",
    },
    en: {
        title: "INT Narrative Therapy",
        subtitle: "Listening to your story, helping you rewrite your life",
        notice: "This is an AI-assisted tool based on narrative therapy, for research purposes only. It cannot replace professional psychological counseling.",
        participantPlaceholder: "Enter your participant ID (optional)",
        startBtn: "Start",
        headerTitle: "INT Narrative Therapy",
        exportBtn: "Export",
        inputPlaceholder: "Share your story...",
        openingMessage: "Hello, I'm your INT narrative therapy counselor. It's wonderful to meet you here. Narrative therapy believes that everyone is the expert of their own life story. What would you like to share with me today?",
        errorRetry: "Sorry, something went wrong. Please try again later.",
        errorConn: "Sorry, connection failed. Please try again.",
        exportFail: "Export failed. Please try again.",
        langBtnLabel: "中",
        htmlLang: "en",
    },
};

let currentLang = localStorage.getItem("lang") || "zh";

function t(key) {
    return I18N[currentLang][key] || I18N.zh[key] || key;
}

function applyLang() {
    document.documentElement.lang = t("htmlLang");
    document.title = t("title");

    // data-i18n → textContent
    document.querySelectorAll("[data-i18n]").forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });

    // data-i18n-placeholder → placeholder attribute
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
    });

    // lang toggle buttons: show the OTHER language
    document.querySelectorAll(".lang-toggle").forEach(btn => {
        btn.textContent = t("langBtnLabel");
    });

    localStorage.setItem("lang", currentLang);
}

function toggleLang() {
    currentLang = currentLang === "zh" ? "en" : "zh";
    applyLang();
}

// ===== 全局状态 =====
const API_BASE = "";

let sessionId = null;
let participantId = "";
let isWaiting = false;

// DOM 元素引用
const welcomeScreen = document.getElementById("welcome-screen");
const chatScreen = document.getElementById("chat-screen");
const messagesContainer = document.getElementById("messages");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const exportBtn = document.getElementById("export-btn");
const startBtn = document.getElementById("start-btn");
const participantInput = document.getElementById("participant-id-input");
const langBtnWelcome = document.getElementById("lang-btn-welcome");
const langBtnChat = document.getElementById("lang-btn-chat");

// ===== 初始化 =====
window.addEventListener("DOMContentLoaded", async () => {
    // 应用语言
    applyLang();

    // 语言切换
    langBtnWelcome.addEventListener("click", toggleLang);
    langBtnChat.addEventListener("click", toggleLang);

    // 检查 URL 参数中的 session
    const urlParams = new URLSearchParams(window.location.search);
    const urlSession = urlParams.get("session");

    if (urlSession) {
        sessionId = urlSession;
        participantId = localStorage.getItem("participant_id") || "";
        await restoreSession(urlSession);
        showChatScreen();
    } else {
        const savedSession = localStorage.getItem("session_id");
        if (savedSession) {
            sessionId = savedSession;
            participantId = localStorage.getItem("participant_id") || "";
            await restoreSession(savedSession);
            showChatScreen();
        }
    }

    startBtn.addEventListener("click", startChat);
    sendBtn.addEventListener("click", sendMessage);

    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendMessage();
        }
    });

    messageInput.addEventListener("input", () => {
        messageInput.style.height = "auto";
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
        sendBtn.disabled = messageInput.value.trim() === "" || isWaiting;
    });

    exportBtn.addEventListener("click", exportSession);

    participantInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            startChat();
        }
    });
});

// ===== 页面切换 =====
function showChatScreen() {
    welcomeScreen.classList.add("hidden");
    chatScreen.classList.remove("hidden");
    messageInput.focus();
}

// ===== 开始新对话 =====
async function startChat() {
    participantId = participantInput.value.trim();
    sessionId = crypto.randomUUID();
    localStorage.setItem("session_id", sessionId);
    if (participantId) {
        localStorage.setItem("participant_id", participantId);
    } else {
        localStorage.removeItem("participant_id");
    }
    showChatScreen();
    addMessage("therapist", t("openingMessage"));
}

// ===== 恢复历史 session =====
async function restoreSession(sid) {
    try {
        const resp = await fetch(`${API_BASE}/api/session/${sid}`);
        if (!resp.ok) {
            localStorage.removeItem("session_id");
            sessionId = crypto.randomUUID();
            localStorage.setItem("session_id", sessionId);
            addMessage("therapist", t("openingMessage"));
            return;
        }
        const session = await resp.json();
        addMessage("therapist", t("openingMessage"));
        const turns = session.turns || [];
        for (const turn of turns) {
            if (turn.client) addMessage("user", turn.client);
            if (turn.therapist) addMessage("therapist", turn.therapist);
        }
    } catch (e) {
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

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const rawData = line.slice(6).trim();
                    if (!rawData) continue;
                    try {
                        const data = JSON.parse(rawData);
                        if (data.token !== undefined && data.token !== null) {
                            appendToMessage(therapistWrapper, data.token);
                        } else if (data.done === true) {
                            if (data.session_id) {
                                sessionId = data.session_id;
                                localStorage.setItem("session_id", sessionId);
                            }
                        } else if (data.error) {
                            appendToMessage(therapistWrapper, "\n\n" + t("errorRetry"));
                        }
                    } catch (parseErr) {
                        // ignore malformed SSE lines
                    }
                }
            }
        }

    } catch (e) {
        removeTypingIndicator(typingId);
        if (!therapistWrapper) {
            addMessage("therapist", t("errorConn"));
        } else {
            const bubble = therapistWrapper.querySelector(".message-bubble");
            if (bubble && !bubble.textContent.trim()) {
                bubble.textContent = t("errorConn");
            }
        }
    } finally {
        isWaiting = false;
        sendBtn.disabled = messageInput.value.trim() === "";
        scrollToBottom();
    }
}

// ===== 添加消息气泡 =====
function addMessage(role, text) {
    const wrapper = document.createElement("div");
    wrapper.className = `message-wrapper ${role}`;

    const now = new Date();
    const timeStr =
        now.getHours().toString().padStart(2, "0") + ":" +
        now.getMinutes().toString().padStart(2, "0");

    if (role === "therapist") {
        wrapper.innerHTML = `
            <div class="avatar">AI</div>
            <div class="message-content">
                <div class="message-bubble therapist-bubble">${escapeHtml(text)}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;
    } else {
        wrapper.innerHTML = `
            <div class="message-content">
                <div class="message-bubble user-bubble">${escapeHtml(text)}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;
    }

    messagesContainer.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
}

// ===== 向气泡追加 token（流式） =====
function appendToMessage(wrapper, token) {
    if (!wrapper) return;
    const bubble = wrapper.querySelector(".message-bubble");
    if (bubble) {
        bubble.textContent += token;
        scrollToBottom();
    }
}

// ===== 打字动画指示器 =====
function addTypingIndicator() {
    const id = "typing-" + Date.now();
    const wrapper = document.createElement("div");
    wrapper.id = id;
    wrapper.className = "message-wrapper therapist";
    wrapper.innerHTML = `
        <div class="avatar">AI</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(wrapper);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ===== 滚动到底部 =====
function scrollToBottom() {
    messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: "smooth",
    });
}

// ===== 导出记录 =====
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
    } catch (e) {
        alert(t("exportFail"));
    }
}

// ===== HTML 转义（防 XSS） =====
function escapeHtml(text) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}
