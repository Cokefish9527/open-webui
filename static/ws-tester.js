const STORAGE_KEY = "openwebui_ws_tester_config_v2";

const DEFAULT_CONFIG = {
  serverBaseUrl: "http://localhost:8080",
  autoLogin: true,
  autoConnect: true,
  credentials: {
    email: "saiter2306001@163.com",
    password: "hsai1234",
  },
  subscriptions: {
    hsai_response: true,
    hsai_error: true,
    "channel-events": false,
    connect_error: true,
    disconnect: true,
    ping: true,
    pong: true,
  },
  messageTemplates: [
    {
      label: "欢迎语",
      payload: {
        type: "welcome",
        user_id: "",
        session_id: "",
        entry_type: "chat",
        metadata: { preset: "welcome" },
      },
    },
    {
      label: "工作流触发",
      payload: {
        type: "workflow_trigger",
        content: "请分析目标公司的经营状况。",
        entry_type: "chat",
        metadata: { test_mode: true },
      },
    },
  ],
};

const $ = (id) => document.getElementById(id);

class WebSocketTester {
  constructor() {
    this.socket = null;
    this.token = null;
    this.userId = null;
    this.handleKeydown = this.handleKeydown.bind(this);
    this.activeModalMessage = null;
    this.primarySession = null;
    this.activeMarkdownMessage = null;
    this.loginButtonResetTimer = null;
    this.connectButtonResetTimer = null;

    this.pendingMetrics = [];
    this.conversations = new Map();
    this.replayQueue = [];
    this.rawLogs = [];

    this.stats = {
      sent: 0,
      received: 0,
      errors: 0,
      totalLatency: 0,
      samples: 0,
      minLatency: null,
      maxLatency: null,
      latestLatency: null,
    };

    this.config = this.loadConfig();
    this.bindElements();
    this.setLoginButtonState("idle");
    this.setConnectButtonState("idle");
    this.applyConfigToUI();
    this.bindEvents();
    this.renderSubscriptions();
    this.renderTemplates();
    this.updateMetrics();
    this.appendSystemEvent("页面加载完成，等待操作。");
    this.updateAuthControls();

    if (this.config.autoLogin) {
      this.autoLogin();
    }
  }

  loadConfig() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          ...DEFAULT_CONFIG,
          ...parsed,
          credentials: {
            ...DEFAULT_CONFIG.credentials,
            ...(parsed.credentials || {}),
          },
          subscriptions: {
            ...DEFAULT_CONFIG.subscriptions,
            ...(parsed.subscriptions || {}),
          },
          messageTemplates:
            parsed.messageTemplates || DEFAULT_CONFIG.messageTemplates,
        };
      }
    } catch (error) {
      console.error("读取配置失败", error);
    }
    return structuredClone(DEFAULT_CONFIG);
  }

  saveConfig() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.config));
  }

  bindElements() {
    const ids = [
      "serverUrl",
      "loginEmail",
      "loginPassword",
      "autoLogin",
      "autoConnect",
      "loginBtn",
      "refreshTokenBtn",
      "logoutBtn",
      "connectBtn",
      "disconnectBtn",
      "connectionDot",
      "connectionStatus",
      "socketId",
      "tokenInfo",
      "importConfigBtn",
      "exportConfigBtn",
      "clearStorageBtn",
      "configFileInput",
      "messageType",
      "entryType",
      "sessionId",
      "lockSession",
      "messageContent",
      "metadataInput",
      "userId",
      "taskId",
      "sendMessageBtn",
      "sendWelcomeBtn",
      "sendStatusBtn",
      "templateList",
      "subscriptionList",
      "selectAllSubscriptionsBtn",
      "clearSubscriptionsBtn",
      "pingInfo",
      "conversationContainer",
      "conversationFilter",
      "eventFilter",
      "clearMessagesBtn",
      "exportLogsBtn",
      "statSent",
      "statReceived",
      "statErrors",
      "statAvgLatency",
      "statLatencyRange",
      "statLatestLatency",
      "recentEvents",
      "replayContainer",
      "messageModal",
      "messageModalTitle",
      "messageModalMeta",
      "messageModalBody",
      "messageModalClose",
      "markdownModal",
      "markdownModalTitle",
      "markdownModalMeta",
      "markdownModalBody",
      "markdownModalClose",
      "primarySessionIndicator",
      "primarySessionLabel",
      "focusSessionBtn",
      "focusLatestBtn",
      "clearFocusBtn",
    ];

    this.el = Object.fromEntries(ids.map((id) => [id, $(id)]));
  }

  setLoginButtonState(state = "idle") {
    const btn = this.el.loginBtn;
    if (!btn) return;
    const labels = {
      idle: "登录",
      loading: "登录中…",
      success: "已登录",
      error: "重新登录",
    };
    btn.textContent = labels[state] || labels.idle;
    const isLoading = state === "loading";
    btn.classList.toggle("is-loading", isLoading);
    btn.disabled = isLoading;
    this.loginButtonState = state;

    if (this.loginButtonResetTimer) {
      clearTimeout(this.loginButtonResetTimer);
      this.loginButtonResetTimer = null;
    }
    if (state === "success" || state === "error") {
      this.loginButtonResetTimer = setTimeout(() => {
        this.setLoginButtonState("idle");
      }, 1500);
    }
  }

  setConnectButtonState(state = "idle") {
    const btn = this.el.connectBtn;
    if (!btn) return;
    const labels = {
      idle: "连接 Socket",
      loading: "连接中…",
      success: "已连接",
      error: "重新连接",
    };
    btn.textContent = labels[state] || labels.idle;
    const isLoading = state === "loading";
    btn.classList.toggle("is-loading", isLoading);
    const shouldDisable = isLoading || state === "success" || !this.token;
    btn.disabled = shouldDisable;
    this.connectButtonState = state;

    if (this.el.disconnectBtn) {
      if (state === "success") {
        this.el.disconnectBtn.disabled = false;
      } else if (state === "loading") {
        this.el.disconnectBtn.disabled = true;
      } else {
        this.el.disconnectBtn.disabled = true;
      }
    }
  }

  updateAuthControls() {
    const hasToken = !!this.token;
    if (this.el.refreshTokenBtn) {
      this.el.refreshTokenBtn.disabled = !hasToken;
    }
    if (this.el.logoutBtn) {
      this.el.logoutBtn.disabled = !hasToken;
    }
    if (this.el.connectBtn) {
      const forbidClick =
        !hasToken ||
        this.connectButtonState === "loading" ||
        (this.connectButtonState === "success" && this.socket?.connected);
      this.el.connectBtn.disabled = forbidClick;
      if (!hasToken) {
        this.el.connectBtn.classList.remove("is-loading");
        this.connectButtonState = "idle";
        this.el.connectBtn.textContent = "连接 Socket";
      }
    }
    if (this.el.disconnectBtn && (!this.socket || !this.socket.connected)) {
      this.el.disconnectBtn.disabled = true;
    }
    if (this.el.loginBtn && this.loginButtonState !== "loading") {
      this.el.loginBtn.disabled = false;
    }
  }

  applyConfigToUI() {
    this.el.serverUrl.value = this.config.serverBaseUrl || "";
    this.el.loginEmail.value = this.config.credentials.email || "";
    this.el.loginPassword.value = this.config.credentials.password || "";
    this.el.autoLogin.checked = !!this.config.autoLogin;
    this.el.autoConnect.checked = !!this.config.autoConnect;
  }

  bindEvents() {
    this.el.loginBtn.addEventListener("click", () => this.login());
    this.el.refreshTokenBtn.addEventListener("click", () => this.login(true));
    this.el.logoutBtn.addEventListener("click", () => this.clearToken());
    this.el.connectBtn.addEventListener("click", () => this.connectSocket());
    this.el.disconnectBtn.addEventListener("click", () => this.disconnectSocket());

    this.el.autoLogin.addEventListener("change", (event) => {
      this.config.autoLogin = event.target.checked;
      this.saveConfig();
    });
    this.el.autoConnect.addEventListener("change", (event) => {
      this.config.autoConnect = event.target.checked;
      this.saveConfig();
    });
    this.el.serverUrl.addEventListener("blur", () => {
      this.config.serverBaseUrl = this.el.serverUrl.value.trim();
      this.saveConfig();
    });

    this.el.importConfigBtn.addEventListener("click", () =>
      this.el.configFileInput.click()
    );
    this.el.configFileInput.addEventListener("change", (event) =>
      this.handleConfigImport(event)
    );
    this.el.exportConfigBtn.addEventListener("click", () => this.exportConfig());
    this.el.clearStorageBtn.addEventListener("click", () => this.clearStorage());

    this.el.sendMessageBtn.addEventListener("click", () => this.sendMessage());
    this.el.sendWelcomeBtn.addEventListener("click", () => {
      this.el.messageType.value = "welcome";
      this.sendMessage("welcome");
    });
    this.el.sendStatusBtn.addEventListener("click", () => this.sendStatusRequest());

    this.el.sessionId.addEventListener("input", () =>
      this.updateFocusControls()
    );
    this.el.conversationFilter.addEventListener("change", () => {
      this.renderConversations();
    });
    this.el.eventFilter.addEventListener("change", () => {
      this.renderConversations();
    });
    this.el.clearMessagesBtn.addEventListener("click", () => this.clearMessages());
    this.el.exportLogsBtn.addEventListener("click", () => this.exportLogs());
    this.el.focusSessionBtn.addEventListener("click", () =>
      this.focusByEditorSession()
    );
    this.el.focusLatestBtn.addEventListener("click", () =>
      this.focusByLatestSession()
    );
    this.el.clearFocusBtn.addEventListener("click", () =>
      this.setPrimarySession(null)
    );

    this.el.selectAllSubscriptionsBtn.addEventListener("click", () =>
      this.setAllSubscriptions(true)
    );
    this.el.clearSubscriptionsBtn.addEventListener("click", () =>
      this.setAllSubscriptions(false)
    );

    if (this.el.messageModal) {
      this.el.messageModalClose.addEventListener("click", () =>
        this.hideMessageModal()
      );
      this.el.messageModal.addEventListener("click", (event) => {
        if (event.target === this.el.messageModal) {
          this.hideMessageModal();
        }
      });
    }

    if (this.el.markdownModal) {
      this.el.markdownModalClose.addEventListener("click", () =>
        this.hideMarkdownModal()
      );
      this.el.markdownModal.addEventListener("click", (event) => {
        if (event.target === this.el.markdownModal) {
          this.hideMarkdownModal();
        }
      });
    }

    document.addEventListener("keydown", this.handleKeydown);
    this.updateFocusControls();
  }

  autoLogin() {
    if (!this.el.loginEmail.value || !this.el.loginPassword.value) {
      this.appendSystemEvent("自动登录已开启，但账号或密码为空。");
      return;
    }
    this.appendSystemEvent("正在执行自动登录…");
    this.login(true);
  }

  async login(isRefresh = false) {
    const email = this.el.loginEmail.value.trim();
    const password = this.el.loginPassword.value.trim();
    const baseUrl = this.el.serverUrl.value.trim() || this.config.serverBaseUrl;

    if (!email || !password || !baseUrl) {
      this.appendSystemEvent("请填写服务器地址、账号和密码。");
      return;
    }

    const refreshBtn = this.el.refreshTokenBtn;
    if (isRefresh && refreshBtn) {
      refreshBtn.dataset.originalText = refreshBtn.textContent;
      refreshBtn.textContent = "刷新中…";
      refreshBtn.classList.add("is-loading");
      refreshBtn.disabled = true;
    } else {
      this.setLoginButtonState("loading");
    }

    let loginResult = "error";

    try {
      const response = await fetch(`${baseUrl}/api/v1/auths/signin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || response.statusText);
      }

      const data = await response.json();

      this.token = data.token;
      this.userId = data.id || data.user_id || "";
      if (this.userId) {
        this.el.userId.value = this.userId;
      }

      this.config.serverBaseUrl = baseUrl;
      this.config.credentials = { email, password };
      this.saveConfig();

      this.updateTokenInfo();
      this.appendSystemEvent(
        isRefresh ? "Token 已刷新。" : "登录成功，Token 已更新。"
      );
      loginResult = "success";

      if (this.config.autoConnect) {
        this.connectSocket();
      }
    } catch (error) {
      console.error(error);
      this.appendSystemEvent(`登录失败：${error.message}`);
      this.token = null;
      this.userId = null;
      this.el.userId.value = "";
    } finally {
      if (isRefresh && refreshBtn) {
        refreshBtn.classList.remove("is-loading");
        refreshBtn.disabled = !this.token;
        refreshBtn.textContent =
          refreshBtn.dataset.originalText || "刷新 Token";
        delete refreshBtn.dataset.originalText;
      } else {
        this.setLoginButtonState(loginResult);
      }
      this.updateAuthControls();
    }
  }

  updateTokenInfo() {
    if (!this.token) {
      this.el.tokenInfo.textContent = "尚未获取 Token";
      return;
    }
    try {
      const [, payload] = this.token.split(".");
      const decoded = JSON.parse(
        atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
      );
      const issued = decoded.iat
        ? new Date(decoded.iat * 1000).toLocaleString()
        : "未知";
      const expires = decoded.exp
        ? new Date(decoded.exp * 1000).toLocaleString()
        : "未知";
      this.el.tokenInfo.innerHTML = `
        <div>用户 ID：${decoded.id || decoded.sub || "-"}</div>
        <div>签发时间：${issued}</div>
        <div>过期时间：${expires}</div>
      `;
    } catch (error) {
      console.error(error);
      this.el.tokenInfo.textContent = "Token 解析失败";
    }
  }

  clearToken() {
    this.token = null;
    this.userId = null;
    this.el.userId.value = "";
    this.el.tokenInfo.textContent = "Token 已清除";
    this.appendSystemEvent("Token 已清空，需要重新登录。");
    this.setConnectButtonState("idle");
    this.updateAuthControls();
  }

  connectSocket() {
    if (!this.token) {
      this.appendSystemEvent("请先登录获取 Token。");
      this.setConnectButtonState("idle");
      this.updateAuthControls();
      return;
    }
    const baseUrl = this.el.serverUrl.value.trim() || this.config.serverBaseUrl;
    if (!baseUrl) {
      this.appendSystemEvent("请填写服务器地址。");
      this.setConnectButtonState("idle");
      this.updateAuthControls();
      return;
    }

    if (this.socket) {
      this.socket.disconnect();
    }

    this.appendSystemEvent("正在建立 Socket 连接…");
    this.setConnectButtonState("loading");
    this.socket = io(baseUrl, {
      path: "/ws/socket.io",
      auth: { token: this.token },
      transports: ["websocket", "polling"],
      query: { user_id: this.el.userId.value.trim() || this.userId || "" },
    });

    this.bindSocketEvents();
  }

  bindSocketEvents() {
    if (!this.socket) return;

    this.socket.on("connect", () => {
      this.el.connectionDot.classList.add("connected");
      this.el.connectionStatus.textContent = "已连接";
      this.el.socketId.textContent = this.socket.id;
      this.appendSystemEvent("Socket 连接成功。");
      this.setConnectButtonState("success");
      this.updateAuthControls();
    });

    this.socket.on("disconnect", (reason) => {
      this.el.connectionDot.classList.remove("connected");
      this.el.connectionStatus.textContent = `已断开（${reason}）`;
      this.el.socketId.textContent = "";
      this.appendSystemEvent(`连接断开：${reason}`);
      this.setConnectButtonState("idle");
      this.updateAuthControls();
    });

    this.socket.on("connect_error", (error) => {
      this.appendSystemEvent(`连接错误：${error.message}`);
      this.setConnectButtonState("error");
      this.updateAuthControls();
    });

    ["hsai_response", "hsai_error", "channel-events", "connect_error", "disconnect"].forEach(
      (eventName) =>
        this.socket.on(eventName, (payload) => this.handleEvent(eventName, payload))
    );

    this.socket.on("ping", () => this.handlePing());
    this.socket.on("pong", () => this.handlePong());
  }

  disconnectSocket() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.el.connectionDot.classList.remove("connected");
    this.el.connectionStatus.textContent = "尚未连接";
    this.el.socketId.textContent = "";
    this.appendSystemEvent("已手动断开 Socket 连接。");
    this.setConnectButtonState("idle");
    this.updateAuthControls();
  }

  handleEvent(eventName, payload) {
    this.addRawLog("in", eventName, payload);
    if (!this.config.subscriptions[eventName]) {
      return;
    }
    if (eventName === "hsai_response") {
      this.handleResponse(payload);
    } else if (eventName === "hsai_error") {
      this.handleError(payload);
    } else if (eventName === "channel-events") {
      const sessionId = payload?.channel_id || "channel";
      this.appendConversationMessage("received", eventName, payload, {
        sessionId,
      });
    } else {
      this.appendSystemEvent(`${eventName}：${JSON.stringify(payload)}`);
    }
  }

  handleResponse(payload) {
    const sessionId =
      payload?.session_id ||
      payload?.sessionId ||
      payload?.context?.session_id ||
      "未标识会话";
    const subtype = payload?.subtype;
    let latency = null;
    this.stats.received += 1;
    if (subtype !== "workflow_started") {
      latency = this.consumePendingMetric(sessionId);
    }
    this.updateMetrics(latency);
    this.appendConversationMessage("received", "hsai_response", payload, {
      sessionId,
      latency,
    });
    if (subtype === "workflow_started") {
      this.appendSystemEvent("工作流开始执行，等待最终结果…");
    }
  }

  handleError(payload) {
    const sessionId =
      payload?.session_id || payload?.sessionId || "未标识会话";
    const latency = this.consumePendingMetric(sessionId);
    this.stats.errors += 1;
    this.updateMetrics(latency);
    this.appendConversationMessage("error", "hsai_error", payload, {
      sessionId,
      latency,
      sessionId,
    });
  }

  handlePing() {
    this.lastPing = Date.now();
    this.el.pingInfo.textContent = `收到 ping：${new Date(
      this.lastPing
    ).toLocaleTimeString()}`;
  }

  handlePong() {
    const now = Date.now();
    const latency = this.lastPing ? `${now - this.lastPing} ms` : "-";
    this.el.pingInfo.textContent = `收到 pong：${new Date(
      now
    ).toLocaleTimeString()} · 延迟 ${latency}`;
  }

  appendConversationMessage(
    direction,
    eventName,
    payload,
    { sessionId = "未标识会话", latency = null } = {}
  ) {
    const list = this.ensureConversation(sessionId);
    list.push({
      direction,
      eventName,
      payload,
      timestamp: new Date(),
      latency,
      sessionId,
    });
    if (!this.primarySession && sessionId) {
      this.primarySession = sessionId;
    }
    this.renderConversations();
  }

  ensureConversation(sessionId) {
    if (!this.conversations.has(sessionId)) {
      this.conversations.set(sessionId, []);
      this.updateConversationFilterOptions();
    }
    return this.conversations.get(sessionId);
  }

  getSortedConversations() {
    return Array.from(this.conversations.entries())
      .map(([session, messages]) => ({ session, messages }))
      .sort(
        (a, b) =>
          (b.messages.at(-1)?.timestamp?.getTime() || 0) -
          (a.messages.at(-1)?.timestamp?.getTime() || 0)
      );
  }

  renderConversations() {
    const container = this.el.conversationContainer;
    container.innerHTML = "";

    const filterSession = this.el.conversationFilter.value;
    const filterEvent = this.el.eventFilter.value;

    const groups = this.getSortedConversations();

    if (!groups.length) {
      container.innerHTML =
        "<p style='color:var(--muted);'>暂无消息，请先发送测试请求。</p>";
      this.updateFocusControls(null);
      return;
    }

    const configuredPrimary = this.primarySession;
    let resolvedPrimary =
      configuredPrimary && this.conversations.has(configuredPrimary)
        ? configuredPrimary
        : null;

    const lockedSession =
      this.el.lockSession.checked && this.el.sessionId.value.trim();

    if (!configuredPrimary) {
      if (lockedSession && this.conversations.has(lockedSession)) {
        resolvedPrimary = lockedSession;
        this.primarySession = lockedSession;
      } else if (
        filterSession !== "all" &&
        this.conversations.has(filterSession)
      ) {
        resolvedPrimary = filterSession;
        this.primarySession = filterSession;
      } else if (!resolvedPrimary && groups.length) {
        resolvedPrimary = groups[0].session;
        this.primarySession = resolvedPrimary;
      }
    }

    let renderedCount = 0;

    for (const { session, messages } of groups) {
      if (filterSession !== "all" && filterSession !== session) {
        continue;
      }

      const visibleMessages = messages.filter((msg) => {
        if (filterEvent === "all") return true;
        if (filterEvent === "sent") return msg.direction === "sent";
        return msg.eventName === filterEvent;
      });

      if (!visibleMessages.length) {
        continue;
      }

      renderedCount += 1;

      const group = document.createElement("div");
      const classes = ["message-group"];
      const isPrimary = resolvedPrimary && session === resolvedPrimary;
      if (isPrimary) {
        classes.push("primary");
      } else if (resolvedPrimary) {
        classes.push("muted");
      }
      group.className = classes.join(" ");
      group.dataset.sessionId = session;

      const header = document.createElement("div");
      header.className = "message-group__header";

      const meta = document.createElement("div");
      meta.innerHTML = `<h3>${session}</h3><span>${visibleMessages.length} 条可见事件</span>`;

      const actions = document.createElement("div");
      actions.className = "message-group__actions";

      const focusBtn = document.createElement("button");
      focusBtn.type = "button";
      focusBtn.className = "message-focus";
      focusBtn.textContent = isPrimary ? "主会话" : "设为主会话";
      focusBtn.disabled = isPrimary;
      focusBtn.addEventListener("click", () => this.setPrimarySession(session));

      actions.appendChild(focusBtn);
      header.append(meta, actions);

      const listEl = document.createElement("div");
      listEl.className = "message-list";

      for (const message of visibleMessages) {
        listEl.appendChild(this.renderMessageCard(message));
      }

      group.append(header, listEl);
      container.appendChild(group);
    }

    if (!renderedCount) {
      container.innerHTML =
        "<p style='color:var(--muted);'>当前筛选条件下没有消息。</p>";
    }

    this.updateFocusControls(configuredPrimary || resolvedPrimary);
  }

  renderMessageCard(message) {
    const card = document.createElement("article");
    card.className = "conversation-card";
    if (message.direction === "sent") {
      card.classList.add("conversation-card--sent");
    } else if (message.direction === "error") {
      card.classList.add("conversation-card--error");
    }

    const header = document.createElement("div");
    header.className = "conversation-card__header";
    header.innerHTML = `<span>${this.getEventLabel(
      message
    )}</span><span>${this.formatTimestamp(message)}</span>`;

    const previewButton = document.createElement("button");
    previewButton.type = "button";
    previewButton.className = "conversation-card__preview";
    const previewText = this.getMessagePreview(message);
    previewButton.textContent = previewText || "（无可显示内容，点击查看 JSON）";
    const markdownSource = this.getMarkdownSource(message);
    if (markdownSource) {
      previewButton.addEventListener("click", () =>
        this.showMarkdownModal(message, markdownSource)
      );
    } else {
      previewButton.addEventListener("click", () => this.showMessageModal(message));
    }

    const footer = document.createElement("div");
    footer.className = "conversation-card__footer";
    const viewBtn = document.createElement("button");
    viewBtn.type = "button";
    viewBtn.className = "link-button";
    viewBtn.textContent = "查看 JSON";
    viewBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      this.showMessageModal(message);
    });

    footer.appendChild(viewBtn);
    card.append(header, previewButton, footer);
    return card;
  }

  getEventLabel(message) {
    if (message.direction === "sent") {
      const type = message.payload?.type || message.eventName || "message";
      return `发送 · ${type}`;
    }
    if (message.direction === "error") {
      return `错误 · ${message.eventName || "unknown"}`;
    }
    return `接收 · ${message.eventName || "message"}`;
  }

  formatTimestamp(message) {
    const time =
      message.timestamp instanceof Date
        ? message.timestamp.toLocaleTimeString()
        : "-";
    if (message.latency != null) {
      return `${time} · ${message.latency} ms`;
    }
    return time;
  }

  getMessagePreview(message) {
    const payload = message?.payload;
    if (!payload) return "";

    const pickString = (value) =>
      typeof value === "string" && value.trim() ? value.trim() : null;

    const candidates = [
      pickString(payload.displayText),
      pickString(payload.content),
      pickString(payload.message),
      pickString(payload.error),
    ].filter(Boolean);

    if (candidates.length) {
      return this.truncate(candidates[0]);
    }

    if (typeof payload === "string") {
      return this.truncate(payload);
    }

    try {
      return this.truncate(JSON.stringify(payload));
    } catch {
      return "[无法渲染的对象]";
    }
  }

  truncate(text, maxLength = 120) {
    if (!text || text.length <= maxLength) return text || "";
    return `${text.slice(0, maxLength - 1)}…`;
  }

  getMarkdownSource(message) {
    const payload = message?.payload;
    if (!payload) return "";
    if (typeof payload.displayText === "string" && payload.displayText.trim()) {
      return payload.displayText.trim();
    }
    if (typeof payload.content === "string" && payload.content.trim()) {
      return payload.content.trim();
    }
    return "";
  }

  showMessageModal(message) {
    if (!this.el.messageModal) return;
    this.activeModalMessage = message;
    this.el.messageModalTitle.textContent = this.getEventLabel(message);
    this.el.messageModalMeta.textContent = `${message.sessionId || "未标识会话"} · ${this.formatTimestamp(
      message
    )}`;
    this.el.messageModalBody.textContent = JSON.stringify(
      message.payload,
      null,
      2
    );
    this.el.messageModal.removeAttribute("hidden");
  }

  hideMessageModal() {
    if (!this.el.messageModal) return;
    this.el.messageModal.setAttribute("hidden", "");
    this.activeModalMessage = null;
  }

  showMarkdownModal(message, markdownSource) {
    if (!this.el.markdownModal) {
      this.showMessageModal(message);
      return;
    }
    this.activeMarkdownMessage = message;
    this.el.markdownModalTitle.textContent = this.getEventLabel(message);
    this.el.markdownModalMeta.textContent = `${message.sessionId || "未标识会话"} · ${this.formatTimestamp(
      message
    )}`;
    if (window.marked && typeof window.marked.parse === "function") {
      this.el.markdownModalBody.innerHTML = window.marked.parse(markdownSource);
    } else {
      this.el.markdownModalBody.textContent = markdownSource;
    }
    this.el.markdownModal.removeAttribute("hidden");
  }

  hideMarkdownModal() {
    if (!this.el.markdownModal) return;
    this.el.markdownModal.setAttribute("hidden", "");
    this.activeMarkdownMessage = null;
    if (this.el.markdownModalBody) {
      this.el.markdownModalBody.innerHTML = "";
    }
  }

  handleKeydown(event) {
    if (event.key === "Escape") {
      let handled = false;
      if (this.el.messageModal && !this.el.messageModal.hasAttribute("hidden")) {
        this.hideMessageModal();
        handled = true;
      }
      if (this.el.markdownModal && !this.el.markdownModal.hasAttribute("hidden")) {
        this.hideMarkdownModal();
        handled = true;
      }
      if (handled) {
        event.preventDefault();
      }
    }
  }

  focusByEditorSession() {
    const session = this.el.sessionId.value.trim();
    if (!session) {
      this.appendSystemEvent("请输入 Session ID 后再聚焦。");
      return;
    }
    this.setPrimarySession(session);
  }

  focusByLatestSession() {
    const latest = this.getLatestSessionId();
    if (!latest) {
      this.appendSystemEvent("暂无会话可聚焦，先发送或接收一条消息吧。");
      return;
    }
    this.setPrimarySession(latest);
  }

  getLatestSessionId() {
    const [first] = this.getSortedConversations();
    return first?.session || null;
  }

  setPrimarySession(sessionId) {
    const normalized = sessionId ? String(sessionId).trim() : "";
    this.primarySession = normalized || null;
    const hasConversation =
      normalized && this.conversations.has(normalized);
    this.renderConversations();
    if (this.primarySession) {
      const tip = hasConversation
        ? `已聚焦会话：${this.primarySession}`
        : `已设置聚焦会话 ${this.primarySession}，待消息写入后自动高亮。`;
      this.appendSystemEvent(tip);
    } else {
      this.appendSystemEvent("已取消聚焦，所有会话恢复正常对比。");
    }
  }

  updateFocusControls(focusedSession = this.primarySession) {
    if (this.el.focusSessionBtn) {
      this.el.focusSessionBtn.disabled = !this.el.sessionId.value.trim();
    }
    if (this.el.focusLatestBtn) {
      this.el.focusLatestBtn.disabled = !this.getLatestSessionId();
    }
    if (this.el.clearFocusBtn) {
      const disabled = !focusedSession;
      this.el.clearFocusBtn.disabled = disabled;
    }
    if (this.el.primarySessionIndicator) {
      if (focusedSession) {
        this.el.primarySessionIndicator.hidden = false;
        this.el.primarySessionLabel.textContent = focusedSession;
      } else {
        this.el.primarySessionIndicator.hidden = true;
        this.el.primarySessionLabel.textContent = "";
      }
    }
  }

  updateConversationFilterOptions() {
    const select = this.el.conversationFilter;
    const current = select.value;
    select.innerHTML = "<option value='all'>全部会话</option>";
    for (const session of this.conversations.keys()) {
      const option = document.createElement("option");
      option.value = session;
      option.textContent = session;
      select.appendChild(option);
    }
    if (current && this.conversations.has(current)) {
      select.value = current;
    }
    this.updateFocusControls();
  }

  addRecentEvent(text) {
    const item = document.createElement("div");
    item.textContent = `${new Date().toLocaleTimeString()} · ${text}`;
    this.el.recentEvents.prepend(item);
    while (this.el.recentEvents.children.length > 20) {
      this.el.recentEvents.removeChild(this.el.recentEvents.lastChild);
    }
  }

  appendSystemEvent(text) {
    this.addRecentEvent(text);
  }

  addRawLog(direction, eventName, payload, extra = {}) {
    this.rawLogs.push({
      direction,
      event: eventName,
      payload,
      timestamp: new Date().toISOString(),
      ...extra,
    });
    if (this.rawLogs.length > 600) {
      this.rawLogs.shift();
    }
  }

  recordPendingMetric(sessionId) {
    this.pendingMetrics.push({ sessionId, time: performance.now() });
    if (this.pendingMetrics.length > 120) {
      this.pendingMetrics.shift();
    }
  }

  consumePendingMetric(sessionId) {
    const index = this.pendingMetrics.findIndex(
      (item) => item.sessionId === sessionId
    );
    if (index === -1) return null;
    const { time } = this.pendingMetrics.splice(index, 1)[0];
    return Math.round(performance.now() - time);
  }

  updateMetrics(latency) {
    if (typeof latency === "number") {
      this.stats.samples += 1;
      this.stats.totalLatency += latency;
      this.stats.latestLatency = latency;
      this.stats.minLatency =
        this.stats.minLatency === null
          ? latency
          : Math.min(this.stats.minLatency, latency);
      this.stats.maxLatency =
        this.stats.maxLatency === null
          ? latency
          : Math.max(this.stats.maxLatency, latency);
    }

    this.el.statSent.textContent = this.stats.sent;
    this.el.statReceived.textContent = this.stats.received;
    this.el.statErrors.textContent = this.stats.errors;
    this.el.statAvgLatency.textContent = this.stats.samples
      ? Math.round(this.stats.totalLatency / this.stats.samples)
      : "-";
    this.el.statLatencyRange.textContent = this.stats.samples
      ? `${this.stats.minLatency} / ${this.stats.maxLatency}`
      : "-";
    this.el.statLatestLatency.textContent =
      this.stats.latestLatency != null ? this.stats.latestLatency : "-";
  }

  buildPayload(type) {
    const userId = this.el.userId.value.trim() || this.userId;
    if (!userId) {
      this.appendSystemEvent("未识别用户 ID，请确保已登录。");
      return null;
    }

    let sessionId = this.el.sessionId.value.trim();
    if (!sessionId) {
      sessionId = `${type}_${Math.random().toString(16).slice(2, 10)}`;
      if (this.el.lockSession.checked) {
        this.el.sessionId.value = sessionId;
      }
    }

    const metadata = this.safeParseJSON(this.el.metadataInput.value) || {};
    metadata.client_request_id =
      metadata.client_request_id || this.generateUUID();

    const payload = {
      type,
      content: this.el.messageContent.value.trim(),
      user_id: userId,
      session_id: sessionId,
      entry_type: this.el.entryType.value.trim() || "chat",
      metadata,
    };

    if (!payload.content && type !== "welcome") {
      this.appendSystemEvent("请填写消息内容。");
      return null;
    }

    if (this.el.taskId.value.trim()) {
      payload.task_id = this.el.taskId.value.trim();
    }
    return payload;
  }

  safeParseJSON(text) {
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch {
      this.appendSystemEvent("Metadata 不是合法 JSON，已忽略。");
      return {};
    }
  }

  emitMessage(payload) {
    this.socket.emit("message", payload);
  }

  emitStatus(payload) {
    this.socket.emit("hsai_status", payload);
  }

  sendMessage(typeOverride) {
    const type = typeOverride || this.el.messageType.value;
    const payload = this.buildPayload(type);
    if (!payload) return;

    if (!this.socket || !this.socket.connected) {
      this.appendSystemEvent("尚未连接 Socket，操作已取消。");
      return;
    }

    this.emitMessage(payload);
    this.stats.sent += 1;
    this.recordPendingMetric(payload.session_id);
    this.updateMetrics();
    this.appendConversationMessage("sent", "message", payload, {
      sessionId: payload.session_id,
    });
    this.addReplayItem("message", payload, { sessionId: payload.session_id });
    this.addRawLog("out", "message", payload, { sessionId: payload.session_id });
    this.appendSystemEvent("消息已发送。");

    if (type !== "welcome" && !this.el.lockSession.checked) {
      this.el.messageContent.value = "";
      this.el.sessionId.value = "";
    }
  }

  sendStatusRequest() {
    if (!this.socket || !this.socket.connected) {
      this.appendSystemEvent("尚未连接 Socket，无法请求状态。");
      return;
    }
    const payload = {
      request_id: this.generateUUID(),
      user_id: this.el.userId.value.trim() || this.userId,
      timestamp: Date.now(),
    };
    this.emitStatus(payload);
    this.addRawLog("out", "hsai_status", payload);
    this.addReplayItem("hsai_status", payload, { sessionId: payload.request_id });
    this.appendSystemEvent("已发起状态查询。");
  }

  addReplayItem(eventName, payload, meta = {}) {
    this.replayQueue.unshift({
      id: this.generateUUID(),
      createdAt: new Date(),
      eventName,
      payload,
      meta,
    });
    if (this.replayQueue.length > 40) {
      this.replayQueue.pop();
    }
    this.renderReplayQueue();
  }

  renderReplayQueue() {
    const container = this.el.replayContainer;
    container.innerHTML = "";
    if (!this.replayQueue.length) {
      container.innerHTML =
        "<p style='color:var(--muted);margin:0;'>暂无重放记录。</p>";
      return;
    }
    this.replayQueue.forEach((item, index) => {
      const card = document.createElement("div");
      card.className = "replay-item";
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="tag">${item.eventName} · ${item.meta.sessionId || "会话"}</span>
          <small style="color:var(--muted);">${item.createdAt.toLocaleTimeString()}</small>
        </div>
        <pre style="white-space:pre-wrap;word-break:break-word;">${JSON.stringify(
          item.payload,
          null,
          2
        )}</pre>
      `;
      const actions = document.createElement("div");
      actions.className = "button-row";

      const fillBtn = document.createElement("button");
      fillBtn.className = "secondary";
      fillBtn.textContent = "填充到编辑器";
      fillBtn.addEventListener("click", () => this.loadReplayItem(item));

      const replayBtn = document.createElement("button");
      replayBtn.className = "primary";
      replayBtn.textContent = "立即重放";
      replayBtn.addEventListener("click", () => this.replayItem(item));

      const removeBtn = document.createElement("button");
      removeBtn.className = "danger";
      removeBtn.textContent = "移除";
      removeBtn.addEventListener("click", () => {
        this.replayQueue.splice(index, 1);
        this.renderReplayQueue();
      });

      actions.append(fillBtn, replayBtn, removeBtn);
      card.appendChild(actions);
      container.appendChild(card);
    });
  }

  loadReplayItem(item) {
    if (item.payload.type) this.el.messageType.value = item.payload.type;
    if (item.payload.entry_type) this.el.entryType.value = item.payload.entry_type;
    if (item.payload.session_id) {
      this.el.sessionId.value = item.payload.session_id;
      this.el.lockSession.checked = true;
    }
    this.el.messageContent.value = item.payload.content || "";
    this.el.metadataInput.value = JSON.stringify(
      item.payload.metadata || {},
      null,
      2
    );
    if (item.payload.user_id) this.el.userId.value = item.payload.user_id;
    if (item.payload.task_id) this.el.taskId.value = item.payload.task_id;
    this.appendSystemEvent("已填充重放请求到编辑器。");
  }

  replayItem(item) {
    if (!this.socket || !this.socket.connected) {
      this.appendSystemEvent("未连接 Socket，重放操作已取消。");
      return;
    }
    if (item.eventName === "message") {
      this.emitMessage(item.payload);
    } else if (item.eventName === "hsai_status") {
      this.emitStatus(item.payload);
    }
    this.appendSystemEvent("已重放选中请求。");
  }

  clearMessages() {
    this.conversations.clear();
    this.pendingMetrics = [];
    this.rawLogs = [];
    this.replayQueue = [];
    this.primarySession = null;
    this.updateConversationFilterOptions();
    this.renderConversations();
    this.renderReplayQueue();
    this.appendSystemEvent("已清空消息记录。");
  }

  exportLogs() {
    const blob = new Blob([JSON.stringify(this.rawLogs, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ws_logs_${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    this.appendSystemEvent("已导出消息日志。");
  }

  exportConfig() {
    const blob = new Blob([JSON.stringify(this.config, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ws_tester_config_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    this.appendSystemEvent("配置已导出。");
  }

  handleConfigImport(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const json = JSON.parse(reader.result);
        this.applyImportedConfig(json);
        this.appendSystemEvent("已导入配置文件。");
      } catch {
        this.appendSystemEvent("配置文件格式错误。");
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  }

  applyImportedConfig(config) {
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
      credentials: {
        ...DEFAULT_CONFIG.credentials,
        ...(config.credentials || {}),
      },
      subscriptions: {
        ...DEFAULT_CONFIG.subscriptions,
        ...(config.subscriptions || {}),
      },
      messageTemplates:
        config.messageTemplates || DEFAULT_CONFIG.messageTemplates,
    };
    this.saveConfig();
    this.applyConfigToUI();
    this.renderSubscriptions();
    this.renderTemplates();
  }

  renderSubscriptions() {
    this.el.subscriptionList.innerHTML = "";
    Object.entries(this.config.subscriptions).forEach(([name, checked]) => {
      const row = document.createElement("label");
      row.className = "toggle-line";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = !!checked;
      input.addEventListener("change", (event) => {
        this.config.subscriptions[name] = event.target.checked;
        this.saveConfig();
      });
      row.append(input, document.createTextNode(name));
      this.el.subscriptionList.appendChild(row);
    });
  }

  setAllSubscriptions(value) {
    Object.keys(this.config.subscriptions).forEach((key) => {
      this.config.subscriptions[key] = value;
    });
    this.saveConfig();
    this.renderSubscriptions();
  }

  renderTemplates() {
    this.el.templateList.innerHTML = "";
    if (!this.config.messageTemplates.length) {
      this.el.templateList.innerHTML =
        "<p style='margin:0;'>暂无模板。</p>";
      return;
    }
    this.config.messageTemplates.forEach((template) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.justifyContent = "space-between";
      row.style.alignItems = "center";
      row.style.marginBottom = "8px";
      const label = document.createElement("span");
      label.textContent = template.label;
      const button = document.createElement("button");
      button.className = "link-button";
      button.textContent = "填充";
      button.addEventListener("click", () => this.applyTemplate(template));
      row.append(label, button);
      this.el.templateList.appendChild(row);
    });
  }

  applyTemplate(template) {
    this.el.messageType.value = template.payload.type || "chat";
    this.el.entryType.value = template.payload.entry_type || "chat";
    this.el.messageContent.value = template.payload.content || "";
    this.el.metadataInput.value = JSON.stringify(
      template.payload.metadata || {},
      null,
      2
    );
    if (template.payload.session_id) {
      this.el.sessionId.value = template.payload.session_id;
      this.el.lockSession.checked = true;
    }
    this.appendSystemEvent(`已载入模板：${template.label}`);
  }

  clearStorage() {
    localStorage.removeItem(STORAGE_KEY);
    this.config = structuredClone(DEFAULT_CONFIG);
    this.applyConfigToUI();
    this.renderSubscriptions();
    this.renderTemplates();
    this.appendSystemEvent("已清空本地缓存，恢复默认配置。");
  }

  generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }
}

document.addEventListener("DOMContentLoaded", () => new WebSocketTester());

