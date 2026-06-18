// ===== i18n =====
const I18N = {
    zh: {
        title: "INT 叙事咨询",
        subtitle: "倾听你的故事，陪你重新书写生命",
        notice: "本系统是基于叙事疗法的 AI 辅助工具，仅作为研究用途，不能替代专业心理咨询。",
        participantPlaceholder: "参与者编号（用于找回历史，可选）",
        identityAnonymous: "当前为匿名本机会话；输入编号可找回历史",
        identityKnown: "当前身份：{id}",
        loadingHistory: "正在加载历史...",
        noHistory: "还没有历史对话",
        yourSessions: "你的历史对话",
        storyBtn: "我的故事",
        storyNeedId: "请输入参与者编号后再生成个人故事。",
        storyLoading: "正在读取你的故事历史...",
        storyGenerating: "正在整理你的个人故事...",
        storyGenerateBtn: "生成 / 更新故事",
        storyNotReady: "个人故事将在 {required} 轮对话后开放。当前 {count} 轮，还差 {remaining} 轮。",
        storyCurrent: "当前故事",
        storyHistory: "历史版本",
        storyVersion: "{turns} 轮 · {date}",
        storyNoHistory: "还没有历史故事版本",
        storyNoCurrent: "还没有生成过个人故事。达到轮次后，可以点击下方按钮生成。",
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
        exportUnavailable: "当前对话还没有保存的消息，发送一轮后即可导出。",
        newChatTitle: "新对话",
        exportTitle: "导出对话记录",
        langBtnLabel: "EN",
        htmlLang: "zh-CN",
        roleTagline: "请选择您的入口 / Please select your entry",
        participantEntry: "参与者入口 / Participant",
        participantDesc: "开始或继续您的咨询旅程 / Start or continue your session",
        researcherEntry: "研究者入口 / Researcher",
        researcherDesc: "访问管理后台 / Access admin dashboard",
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
        participantPlaceholder: "Participant ID (for history, optional)",
        identityAnonymous: "Anonymous local session; enter an ID to restore history",
        identityKnown: "Current identity: {id}",
        loadingHistory: "Loading history...",
        noHistory: "No previous sessions yet",
        yourSessions: "Your sessions",
        storyBtn: "My Story",
        storyNeedId: "Enter a participant ID before generating your story.",
        storyLoading: "Loading your story history...",
        storyGenerating: "Composing your personal story...",
        storyGenerateBtn: "Generate / Update Story",
        storyNotReady: "Your story opens after {required} turns. Current: {count}; remaining: {remaining}.",
        storyCurrent: "Current Story",
        storyHistory: "Past Versions",
        storyVersion: "{turns} turns · {date}",
        storyNoHistory: "No past story versions yet",
        storyNoCurrent: "No personal story has been generated yet. When enough turns are available, use the button below.",
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
        exportUnavailable: "This session has no saved messages yet. Export is available after one turn.",
        newChatTitle: "New Session",
        exportTitle: "Export conversation",
        langBtnLabel: "中",
        htmlLang: "en",
        roleTagline: "Please select your entry / 请选择您的入口",
        participantEntry: "Participant / 参与者入口",
        participantDesc: "Start or continue your session / 开始或继续您的咨询旅程",
        researcherEntry: "Researcher / 研究者入口",
        researcherDesc: "Access admin dashboard / 访问管理后台",
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
        // Works for both <input> and contenteditable div (data-placeholder attr)
        const val = t(el.dataset.i18nPlaceholder);
        if ("placeholder" in el) el.placeholder = val;
        if (el.dataset.placeholder !== undefined) el.dataset.placeholder = val;
    });
    document.querySelectorAll("[data-i18n-title]").forEach(el => {
        el.title = t(el.dataset.i18nTitle);
    });
    document.querySelectorAll(".lang-toggle").forEach(btn => {
        btn.textContent = t("langBtnLabel");
    });
    updateIdentityStatus();
    updateExportState();
    renderSessionHistory();
}

function toggleLang() {
    currentLang = currentLang === "zh" ? "en" : "zh";
    localStorage.setItem("lang", currentLang);
    applyLang();
}

// ===== Session 历史（Participant ID 跨 session；匿名时本机兜底） =====
function getStoredUserSessions() {
    try {
        return JSON.parse(localStorage.getItem("user_sessions") || "[]");
    } catch {
        return [];
    }
}

function getUserSessions() {
    return getStoredUserSessions().filter(s => Number(s.turn_count || 0) > 0);
}

function normalizeParticipantId(value) {
    return String(value || "").trim();
}

function saveUserSession(session) {
    if (Number(session.turn_count || 0) <= 0) return;
    session.participant_id = normalizeParticipantId(session.participant_id);
    const sessions = getStoredUserSessions()
        .filter(s => s.id !== session.id && Number(s.turn_count || 0) > 0);
    sessions.unshift(session);
    localStorage.setItem("user_sessions", JSON.stringify(sessions.slice(0, 30)));
}

function getLocalParticipantSessions(pid) {
    const normalized = normalizeParticipantId(pid);
    if (!normalized) return getUserSessions();
    return getUserSessions().filter(s => normalizeParticipantId(s.participant_id) === normalized);
}

function mergeSessionHistories(remoteSessions, localSessions) {
    const merged = new Map();
    for (const session of localSessions || []) {
        merged.set(session.id, session);
    }
    for (const session of remoteSessions || []) {
        merged.set(session.id, session);
    }
    return Array.from(merged.values()).sort((a, b) => {
        const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
        const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
        return bTime - aTime;
    });
}

function currentParticipantIdInput() {
    return normalizeParticipantId(participantInput?.value || "");
}

function updateIdentityStatus() {
    if (!identityStatus) return;
    const pid = currentParticipantIdInput();
    identityStatus.textContent = pid
        ? t("identityKnown").replace("{id}", pid)
        : t("identityAnonymous");
}

async function loadParticipantHistory() {
    const pid = currentParticipantIdInput();
    if (pid) {
        localStorage.setItem("last_participant_id", pid);
    }
    updateIdentityStatus();

    if (!pid) {
        participantHistory = getUserSessions();
        renderSessionHistory();
        return;
    }

    renderSessionHistory([], t("loadingHistory"));
    try {
        const resp = await fetch(`${API_BASE}/api/participant/${encodeURIComponent(pid)}/sessions`);
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        participantHistory = await resp.json();
    } catch {
        participantHistory = [];
    }
    renderSessionHistory();
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

function buildSessionCard(s) {
    const card = document.createElement("div");
    card.className = "session-card";
    if (s.id === sessionId) card.classList.add("active");

    const stageLabel = (I18N[currentLang]?.stageLabels ?? {})[s.stage] || s.stage || "";
    const who = s.participant_id || t("anonymous");
    const turns = s.turn_count ?? 0;
    const turnsText = `${turns} ${t("turnsUnit")}`;
    const dateText = formatDate(s.updated_at || s.created_at);
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

    const resume = () => resumeSession(s.id, s.participant_id || currentParticipantIdInput());
    card.addEventListener("click", resume);
    card.querySelector(".session-resume-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        resume();
    });
    return card;
}

function renderCardsInto(list, sessions, statusText = "") {
    if (!list) return;
    list.innerHTML = "";
    if (statusText) {
        list.innerHTML = `<div class="history-empty">${escapeHtml(statusText)}</div>`;
        return;
    }
    if (!sessions.length) {
        list.innerHTML = `<div class="history-empty">${escapeHtml(t("noHistory"))}</div>`;
        return;
    }
    sessions.slice(0, 30).forEach(s => list.appendChild(buildSessionCard(s)));
}

function renderSessionHistory(sourceSessions = null, statusText = "") {
    const pid = currentParticipantIdInput();
    const sessions = sourceSessions || (
        pid
            ? mergeSessionHistories(participantHistory, getLocalParticipantSessions(pid))
            : getUserSessions()
    );
    const section = document.getElementById("history-section");
    const list = document.getElementById("history-list");

    if (section && list) {
        if (!sessions.length && !pid && !statusText) {
            section.classList.add("hidden");
        } else {
            section.classList.remove("hidden");
            renderCardsInto(list, sessions, statusText);
        }
    }

    if (!sessionSidebar || !chatHistoryList) return;
    if (!pid && !sessions.length && !statusText) {
        sessionSidebar.classList.add("hidden");
        chatHistoryList.innerHTML = "";
        return;
    }
    sessionSidebar.classList.remove("hidden");
    renderCardsInto(chatHistoryList, sessions, statusText);
}

// ===== DOM 引用 =====
const API_BASE = "";
let sessionId = null;
let participantId = "";
let isWaiting = false;
let currentTurnCount = 0;
let participantHistory = [];
let storyVersions = [];

const roleScreen     = document.getElementById("role-screen");
const welcomeScreen  = document.getElementById("welcome-screen");
const chatScreen     = document.getElementById("chat-screen");
const messagesContainer = document.getElementById("messages");
const messageInput   = document.getElementById("message-input");
const sendBtn        = document.getElementById("send-btn");
const exportBtn      = document.getElementById("export-btn");
const storyBtn       = document.getElementById("story-btn");
const storyCard      = document.getElementById("story-card");
const storyContent   = document.getElementById("story-content");
const storyCloseBtn  = document.getElementById("story-close-btn");
const startBtn       = document.getElementById("start-btn");
const newChatBtn     = document.getElementById("new-chat-btn");
const participantInput = document.getElementById("participant-id-input");
const identityStatus = document.getElementById("identity-status");
const sessionSidebar = document.getElementById("session-sidebar");
const chatHistoryList = document.getElementById("chat-history-list");

// ===== 初始化 =====
window.addEventListener("DOMContentLoaded", () => {
    participantInput.value = localStorage.getItem("last_participant_id") || "";
    applyLang();

    document.getElementById("lang-btn-role").addEventListener("click", toggleLang);
    document.getElementById("lang-btn-welcome").addEventListener("click", toggleLang);
    document.getElementById("lang-btn-chat").addEventListener("click", toggleLang);

    // Role screen navigation
    const participantCard = document.getElementById("participant-card");
    const researcherCard  = document.getElementById("researcher-card");

    function selectParticipant() {
        roleScreen.classList.add("hidden");
        welcomeScreen.classList.remove("hidden");
        loadParticipantHistory();
    }

    participantCard.addEventListener("click", selectParticipant);
    participantCard.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectParticipant(); }
    });

    researcherCard.addEventListener("click", () => {
        window.location.href = "/admin.html";
    });
    researcherCard.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); window.location.href = "/admin.html"; }
    });

    startBtn.addEventListener("click", startChat);
    newChatBtn.addEventListener("click", showWelcomeScreen);
    sendBtn.addEventListener("click", sendMessage);
    exportBtn.addEventListener("click", exportSession);
    storyBtn.addEventListener("click", showStoryCard);
    storyCloseBtn.addEventListener("click", () => storyCard.classList.add("hidden"));

    // contenteditable div: Enter sends, Shift+Enter adds newline
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendMessage();
        }
    });

    messageInput.addEventListener("input", () => {
        sendBtn.disabled = !getInputText() || isWaiting;
    });

    participantInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); startChat(); }
    });
    participantInput.addEventListener("input", debounce(loadParticipantHistory, 350));
    participantInput.addEventListener("blur", loadParticipantHistory);

    // applyLang() above already calls renderSessionHistory(); no second call needed here
});

// ===== 页面切换 =====
function showChatScreen() {
    welcomeScreen.classList.add("hidden");
    chatScreen.classList.remove("hidden");
    updateExportState();
    setTimeout(() => messageInput.focus(), 100);
}

function showWelcomeScreen() {
    chatScreen.classList.add("hidden");
    welcomeScreen.classList.remove("hidden");
    // Refresh history in case new messages were added
    loadParticipantHistory();
}

function debounce(fn, delay) {
    let timer = null;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// ===== 开始新对话 =====
async function startChat() {
    participantId = normalizeParticipantId(participantInput.value);
    if (participantInput) participantInput.value = participantId;
    sessionId = crypto.randomUUID();
    currentTurnCount = 0;
    updateExportState();
    if (participantId) {
        await loadParticipantHistory();
    }

    messagesContainer.innerHTML = "";
    showChatScreen();
    addMessage("therapist", t("openingMessage"));
    renderSessionHistory();
}

// ===== 恢复特定 session =====
async function resumeSession(sid, pid) {
    sessionId = sid;
    participantId = normalizeParticipantId(pid || "");
    if (participantId && participantInput) participantInput.value = participantId;
    messagesContainer.innerHTML = "";
    showChatScreen();

    try {
        const resp = await fetch(`${API_BASE}/api/session/${sid}`);
        if (!resp.ok) throw new Error("not found");
        const session = await resp.json();
        currentTurnCount = (session.turns || []).length;
        updateExportState();
        addMessage("therapist", t("openingMessage"));
        for (const turn of (session.turns || [])) {
            if (turn.client)    addMessage("user", turn.client);
            if (turn.therapist) addMessage("therapist", turn.therapist);
        }
    } catch {
        sessionId = null;
        currentTurnCount = 0;
        updateExportState();
        addMessage("therapist", t("openingMessage"));
    }
}

// ===== 读取 contenteditable 文本 =====
function getInputText() {
    return (messageInput.innerText || messageInput.textContent || "").trim();
}

function clearInput() {
    messageInput.innerHTML = "";
}

// ===== 发送消息 =====
async function sendMessage() {
    const text = getInputText();
    if (!text || isWaiting) return;

    addMessage("user", text);
    clearInput();
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
                language: currentLang,
            }),
        });

        if (!resp.ok) throw new Error("HTTP " + resp.status);

        removeTypingIndicator(typingId);
        therapistWrapper = addMessage("therapist", "");

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalStage = "trust building";
        let therapistText = "";
        let streamCompleted = false;

        function handleSseLine(line) {
            if (!line.startsWith("data: ")) return;
            const raw = line.slice(6).trim();
            if (!raw) return;
            try {
                const data = JSON.parse(raw);
                if (data.error) {
                    appendToMessage(therapistWrapper, "\n\n" + t("errorRetry"));
                    streamCompleted = true;
                    return;
                }
                if (data.token != null) {
                    appendToMessage(therapistWrapper, data.token);
                    therapistText += data.token;
                    return;
                }
                if (data.done === true) {
                    if (data.session_id) sessionId = data.session_id;
                    if (data.stage) finalStage = data.stage;
                    streamCompleted = true;
                }
            } catch {
                // Keep the stream alive if one partial/event line is malformed.
            }
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                handleSseLine(line);
            }
        }
        buffer += decoder.decode();
        if (buffer.trim()) {
            for (const line of buffer.split("\n")) {
                handleSseLine(line);
            }
        }

        if (!streamCompleted) {
            throw new Error("Stream ended before completion");
        }

        // Update local history with the user's message as preview (matches server-side logic)
        currentTurnCount += 1;
        const now = new Date().toISOString();
        const sessions = getStoredUserSessions();
        const s = sessions.find(s => s.id === sessionId);
        if (s) {
            s.preview = text;
            s.turn_count = currentTurnCount;
            s.stage = finalStage;
            s.updated_at = now;
            localStorage.setItem("user_sessions", JSON.stringify(sessions));
        } else {
            saveUserSession({
                id: sessionId,
                participant_id: participantId,
                stage: finalStage,
                created_at: now,
                updated_at: now,
                preview: text,
                turn_count: currentTurnCount,
            });
        }
        updateExportState();
        if (participantId) {
            loadParticipantHistory();
        } else {
            renderSessionHistory();
        }

    } catch {
        removeTypingIndicator(typingId);
        const msg = t("errorConn");
        if (!therapistWrapper) {
            addMessage("therapist", msg);
        } else {
            const bubble = therapistWrapper.querySelector(".message-bubble");
            if (bubble && !bubble.textContent.trim()) {
                bubble.textContent = msg;
            } else if (bubble) {
                bubble.textContent += "\n\n" + msg;
            }
        }
    } finally {
        isWaiting = false;
        sendBtn.disabled = !getInputText();
        scrollToBottom();
    }
}

async function showStoryCard() {
    const pid = participantId || currentParticipantIdInput();
    storyCard.classList.remove("hidden");
    if (!pid) {
        storyContent.innerHTML = `<p>${escapeHtml(t("storyNeedId"))}</p>`;
        return;
    }

    storyContent.innerHTML = `<p>${escapeHtml(t("storyLoading"))}</p>`;
    try {
        const resp = await fetch(`${API_BASE}/api/participant/${encodeURIComponent(pid)}/stories`);
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        const history = await resp.json();
        const latest = Array.isArray(history) && history.length ? history[0].story_markdown : "";
        renderStoryCard(latest || "", history || []);
    } catch {
        storyContent.innerHTML = `<p>${escapeHtml(t("errorRetry"))}</p>`;
    }
}

async function generateStoryCard() {
    const pid = participantId || currentParticipantIdInput();
    if (!pid) {
        storyContent.innerHTML = `<p>${escapeHtml(t("storyNeedId"))}</p>`;
        return;
    }

    renderStoryCard("", storyVersions, t("storyGenerating"));
    try {
        const resp = await fetch(`${API_BASE}/api/participant/${encodeURIComponent(pid)}/story`, {
            method: "POST",
        });
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        const data = await resp.json();
        if (!data.eligible) {
            const msg = t("storyNotReady")
                .replace("{required}", data.required_turns ?? 20)
                .replace("{count}", data.turn_count ?? 0)
                .replace("{remaining}", data.remaining_turns ?? 0);
            renderStoryCard("", data.history || storyVersions, msg);
            return;
        }
        renderStoryCard(data.story_markdown || "", data.history || []);
    } catch {
        renderStoryCard("", storyVersions, t("errorRetry"));
    }
}

function renderStoryCard(currentMarkdown, history, statusText = "") {
    storyVersions = Array.isArray(history) ? history : [];
    const historyButtons = storyVersions.length
        ? storyVersions.map((item, idx) => {
            const label = t("storyVersion")
                .replace("{turns}", item.source_turn_count ?? 0)
                .replace("{date}", formatStoryDate(item.created_at));
            return `<button class="story-version-btn" data-story-index="${idx}">${escapeHtml(label)}</button>`;
        }).join("")
        : `<div class="story-history-empty">${escapeHtml(t("storyNoHistory"))}</div>`;
    const currentContent = statusText
        ? `<p>${escapeHtml(statusText)}</p>`
        : (currentMarkdown ? renderMarkdown(currentMarkdown) : `<p>${escapeHtml(t("storyNoCurrent"))}</p>`);

    storyContent.innerHTML = `
        <div class="story-actions">
            <button class="story-generate-btn" data-story-generate="true">${escapeHtml(t("storyGenerateBtn"))}</button>
        </div>
        <div class="story-section-label">${escapeHtml(t("storyCurrent"))}</div>
        <div id="story-rendered">${currentContent}</div>
        <div class="story-history-panel">
            <div class="story-section-label">${escapeHtml(t("storyHistory"))}</div>
            <div class="story-version-list">${historyButtons}</div>
        </div>
    `;
}

function formatStoryDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString(currentLang === "zh" ? "zh-CN" : "en-US", {
        month: "short",
        day: "numeric",
    });
}

storyContent.addEventListener("click", event => {
    const generateBtn = event.target.closest("[data-story-generate]");
    if (generateBtn) {
        generateBtn.disabled = true;
        generateStoryCard();
        return;
    }

    const btn = event.target.closest(".story-version-btn");
    if (!btn) return;
    const idx = Number(btn.dataset.storyIndex);
    const item = storyVersions[idx];
    if (!item) return;
    const rendered = document.getElementById("story-rendered");
    if (rendered) rendered.innerHTML = renderMarkdown(item.story_markdown || "");
    storyContent.querySelectorAll(".story-version-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
});

function renderMarkdown(markdown) {
    const escaped = escapeHtml(markdown || "");
    return escaped
        .replace(/^### (.*)$/gm, "<h3>$1</h3>")
        .replace(/^## (.*)$/gm, "<h2>$1</h2>")
        .replace(/^# (.*)$/gm, "<h1>$1</h1>")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .split(/\n{2,}/)
        .map(block => {
            if (/^<h[123]>/.test(block)) return block;
            return `<p>${block.replace(/\n/g, "<br>")}</p>`;
        })
        .join("");
}

// ===== 消息气泡 =====
function addMessage(role, text) {
    const wrapper = document.createElement("div");
    wrapper.className = `message-wrapper ${role}`;
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    if (role === "therapist") {
        wrapper.innerHTML = `
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
function updateExportState() {
    if (!exportBtn) return;
    const canExport = Boolean(sessionId) && currentTurnCount > 0;
    exportBtn.disabled = !canExport;
    exportBtn.title = canExport ? t("exportTitle") : t("exportUnavailable");
}

async function exportSession() {
    if (!sessionId || currentTurnCount <= 0) {
        alert(t("exportUnavailable"));
        updateExportState();
        return;
    }

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
        a.remove();
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
