const OPENING_MESSAGE = "你好，我是 INT 叙事咨询师~ 很高兴在这里遇见你。叙事疗法相信，每个人都是自己生命故事的专家。你有什么想和我聊聊的吗？";
const API_BASE = "";  // 同源，留空

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

// ===== 初始化 =====
window.addEventListener("DOMContentLoaded", async () => {
    // 检查 URL 参数中的 session
    const urlParams = new URLSearchParams(window.location.search);
    const urlSession = urlParams.get("session");

    if (urlSession) {
        sessionId = urlSession;
        participantId = localStorage.getItem("participant_id") || "";
        await restoreSession(urlSession);
        showChatScreen();
    } else {
        // 检查 localStorage
        const savedSession = localStorage.getItem("session_id");
        if (savedSession) {
            sessionId = savedSession;
            participantId = localStorage.getItem("participant_id") || "";
            await restoreSession(savedSession);
            showChatScreen();
        }
        // 否则停留在欢迎页
    }

    // 事件监听
    startBtn.addEventListener("click", startChat);
    sendBtn.addEventListener("click", sendMessage);

    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendMessage();
        }
    });

    messageInput.addEventListener("input", () => {
        // 自动增高 textarea
        messageInput.style.height = "auto";
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
        // 根据输入内容启用/禁用发送按钮
        sendBtn.disabled = messageInput.value.trim() === "" || isWaiting;
    });

    exportBtn.addEventListener("click", exportSession);

    // 参与者编号输入框回车键触发开始
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
    // 显示开场白（不经过后端，前端直接渲染）
    addMessage("therapist", OPENING_MESSAGE);
}

// ===== 恢复历史 session =====
async function restoreSession(sid) {
    try {
        const resp = await fetch(`${API_BASE}/api/session/${sid}`);
        if (!resp.ok) {
            // session 不存在或已失效，重新开始
            localStorage.removeItem("session_id");
            sessionId = crypto.randomUUID();
            localStorage.setItem("session_id", sessionId);
            addMessage("therapist", OPENING_MESSAGE);
            return;
        }
        const session = await resp.json();
        // 先显示开场白，再渲染历史消息
        addMessage("therapist", OPENING_MESSAGE);
        const turns = session.turns || [];
        for (const turn of turns) {
            if (turn.client) addMessage("user", turn.client);
            if (turn.therapist) addMessage("therapist", turn.therapist);
        }
    } catch (e) {
        // 网络异常，直接显示开场白
        addMessage("therapist", OPENING_MESSAGE);
    }
}

// ===== 发送消息 =====
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isWaiting) return;

    // 显示用户消息气泡
    addMessage("user", text);
    messageInput.value = "";
    messageInput.style.height = "auto";
    sendBtn.disabled = true;
    isWaiting = true;

    // 显示 typing indicator
    const typingId = addTypingIndicator();

    // 治疗师消息气泡引用（流式填充）
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

        // 移除 typing indicator，创建空的治疗师气泡
        removeTypingIndicator(typingId);
        therapistWrapper = addMessage("therapist", "");

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // 按换行拆分 SSE 事件
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";  // 保留不完整的最后一行

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const rawData = line.slice(6).trim();
                    if (!rawData) continue;
                    try {
                        const data = JSON.parse(rawData);
                        if (data.token !== undefined && data.token !== null) {
                            appendToMessage(therapistWrapper, data.token);
                        } else if (data.done === true) {
                            // 更新 session_id（以服务端返回的为准）
                            if (data.session_id) {
                                sessionId = data.session_id;
                                localStorage.setItem("session_id", sessionId);
                            }
                        } else if (data.error) {
                            appendToMessage(therapistWrapper, "\n\n抱歉，出现了一些问题，请稍后重试。");
                        }
                    } catch (parseErr) {
                        // 忽略解析失败的 SSE 行
                    }
                }
            }
        }

    } catch (e) {
        // 移除 typing indicator（若还在）
        removeTypingIndicator(typingId);
        if (!therapistWrapper) {
            // 完全没有收到响应时显示错误提示
            addMessage("therapist", "抱歉，连接出现问题，请稍后重试。");
        } else {
            // 已收到部分内容后断流
            const bubble = therapistWrapper.querySelector(".message-bubble");
            if (bubble && !bubble.textContent.trim()) {
                bubble.textContent = "抱歉，连接出现问题，请稍后重试。";
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
        if (!resp.ok) throw new Error("导出失败：HTTP " + resp.status);
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
        alert("导出失败，请重试。");
    }
}

// ===== HTML 转义（防 XSS） =====
function escapeHtml(text) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}
