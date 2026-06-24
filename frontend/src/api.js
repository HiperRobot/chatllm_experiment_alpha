const API_BASE = window.location.origin;

function formatChatError(status, detail) {
  const rawDetail = typeof detail === "string" ? detail : JSON.stringify(detail || {});
  const normalized = rawDetail.toLowerCase();

  if (
    status === 403 &&
    (normalized.includes("key limit exceeded") ||
      normalized.includes("total limit") ||
      normalized.includes("credit") ||
      normalized.includes("credits") ||
      normalized.includes("quota"))
  ) {
    return "Os créditos acabaram. Tente novamente mais tarde ou revise sua chave do OpenRouter.";
  }

  return rawDetail || "Erro ao enviar mensagem para o servidor.";
}

// ── Chat ──

async function sendMessageStream({ message, history, onDelta, signal, sessionId, onDone }) {
  const body = { message, history };
  if (sessionId) body.session_id = sessionId;
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(formatChatError(response.status, body?.detail));
  }

  if (!response.body) {
    throw new Error("Streaming nao suportado no ambiente atual.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      const line = rawEvent
        .split("\n")
        .find((part) => part.startsWith("data:"));
      if (!line) continue;

      const payloadText = line.slice(5).trim();
      if (!payloadText) continue;

      let payload;
      try {
        payload = JSON.parse(payloadText);
      } catch {
        continue;
      }

      if (payload.error) {
        throw new Error(formatChatError(403, payload.error));
      }

      if (payload.delta) {
        onDelta(payload.delta);
      }

      if (payload.done && onDone) {
        onDone(payload);
      }
    }
  }
}

// ── Auth ──

async function apiAuth(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  let data;
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) {
    const detail = data.detail;
    const msg = Array.isArray(detail) ? detail.map(d => d.msg || String(d)).join("; ") : (detail || "Erro de autenticacao.");
    throw new Error(msg);
  }
  return data;
}

function apiRegister(username, password, passwordConfirm) {
  return apiAuth("POST", "/api/auth/register", { username, password, password_confirm: passwordConfirm });
}

function apiLogin(username, password) {
  return apiAuth("POST", "/api/auth/login", { username, password });
}

function apiLogout() {
  return apiAuth("POST", "/api/auth/logout");
}

function apiMe() {
  return apiAuth("GET", "/api/auth/me");
}

// ── Sessions ──

async function apiSessions(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}/api/sessions${path}`, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro de sessao.");
  return data;
}

function apiListSessions() {
  return apiSessions("GET", "");
}

function apiCreateSession(title) {
  return apiSessions("POST", "", title ? { title } : {});
}

function apiGetSession(sessionId) {
  return apiSessions("GET", `/${sessionId}`);
}

function apiDeleteSession(sessionId) {
  return apiSessions("DELETE", `/${sessionId}`);
}

function apiUpdateSession(sessionId, title) {
  return apiSessions("PATCH", `/${sessionId}`, { title });
}
