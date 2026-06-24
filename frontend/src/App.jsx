const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [messages, setMessages] = useState([
    {
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authInitialEmail, setAuthInitialEmail] = useState("");
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Check session on mount
  useEffect(() => {
    apiMe()
      .then((data) => setUser(data.user || null))
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false));
  }, []);

  // Load sessions when user changes
  useEffect(() => {
    if (!authLoading) {
      loadSessions(true);
    }
  }, [user, authLoading]);

  // Track if we should create a new session on first message
  const pendingNewSessionRef = useRef(false);

  const loadSessions = async (selectFirst = false) => {
    try {
      const data = await apiListSessions();
      setSessions(data.sessions || []);
      if (selectFirst && data.sessions?.length > 0 && !currentSessionId) {
        switchSession(data.sessions[0].id);
      }
    } catch {
      setSessions([]);
    }
  };

  const switchSession = useCallback(async (sessionId) => {
    setCurrentSessionId(sessionId);
    pendingNewSessionRef.current = false;
    try {
      const data = await apiGetSession(sessionId);
      const msgs = data.messages || [];
      const formatted = msgs.map((m) => ({
        id: createMessageId(),
        role: m.role,
        content: m.content,
      }));
      if (formatted.length === 0) {
        setMessages([{
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        }]);
      } else {
        setMessages(formatted);
      }
    } catch {
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    }
  }, []);

  const handleNewSession = async () => {
    pendingNewSessionRef.current = true;
    try {
      const created = await apiCreateSession();
      setCurrentSessionId(created.id);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
      loadSessions();
    } catch {
      setCurrentSessionId(null);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      await apiDeleteSession(sessionId);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }
      loadSessions();
    } catch {
      // ignore
    }
  };

  const openLogin = (email) => {
    setAuthMode("login");
    setAuthInitialEmail(email || "");
    setShowAuth(true);
  };

  const openRegister = (email) => {
    setAuthMode("register");
    setAuthInitialEmail(email || "");
    setShowAuth(true);
  };

  const handleLogout = async () => {
    try {
      await apiLogout();
      setUser(null);
      setSessions([]);
      setCurrentSessionId(null);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    } catch {
      setUser(null);
      setSessions([]);
      setCurrentSessionId(null);
    }
  };

  const handleAuthSuccess = async () => {
    try {
      const data = await apiMe();
      setUser(data.user || null);
    } catch {
      setUser(null);
    }
  };

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");

    // If no session and pending new, create one
    let activeSessionId = currentSessionId;

    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantMessageId, role: "assistant", content: "" },
    ]);
    setText("");
    setBusy(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        signal: abortController.signal,
        sessionId: activeSessionId,
        onDone: (data) => {
          if (data.session_id) {
            setCurrentSessionId(data.session_id);
            pendingNewSessionRef.current = false;
            // Reload sessions to get updated list with title
            loadSessions(false);
          }
        },
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: `${msg.content}${delta}` }
                : msg
            )
          );
        },
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );
    } catch (err) {
      const aborted = err?.name === "AbortError";
      if (!aborted) {
        setError(err.message || "Falha inesperada ao gerar resposta.");
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: msg.content.trim() ? msg.content : "Nao foi possivel obter resposta do modelo agora." }
              : msg
          )
        );
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId && !msg.content.trim()
              ? { ...msg, content: "Resposta interrompida." }
              : msg
          )
        );
      }
    } finally {
      abortControllerRef.current = null;
      setBusy(false);
    }
  };

  if (authLoading) {
    return <main className="app-shell"><p style={{ textAlign: "center", padding: 40 }}>Carregando...</p></main>;
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="header-left">
          <button
            className="btn-sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label={sidebarOpen ? "Fechar sidebar" : "Abrir sidebar"}
            title={sidebarOpen ? "Fechar sidebar" : "Abrir sidebar"}
          >
            {sidebarOpen ? "\u2039" : "\u2630"}
          </button>
          <span className="brand">ChatLLM Lab</span>
        </div>
        <div className="header-right">
          {user ? (
            <div className="auth-info">
              <span className="user-email">{user.username}</span>
              <button className="btn-logout" onClick={handleLogout}>Sair</button>
            </div>
          ) : (
            <button className="btn-login" onClick={() => openLogin()}>Login</button>
          )}
        </div>
      </header>

      <div className="app-body">
        {sidebarOpen && (
          <aside className="sidebar">
            <div className="sidebar-header">Conversas</div>
            <button className="btn-new-session" onClick={handleNewSession}>
              + Nova conversa
            </button>
            <div className="sidebar-sessions">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className={`sidebar-item ${currentSessionId === s.id ? "active" : ""}`}
                  onClick={() => switchSession(s.id)}
                >
                  <span className="sidebar-item-title">{s.title}</span>
                  <button
                    className="sidebar-item-delete"
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    title="Deletar"
                  >
                    &times;
                  </button>
                </div>
              ))}
              {sessions.length === 0 && (
                <div className="sidebar-empty">Nenhuma conversa</div>
              )}
            </div>
          </aside>
        )}

        <div className="app-main">
          <section className="messages" aria-live="polite" ref={messagesRef}>
            <div className="messages-inner">
              {messages.map((msg) => (
                <article key={msg.id} className={`bubble ${msg.role}`}>
                  <MessageContent content={msg.content} />
                </article>
              ))}
            </div>
          </section>

          <Composer
            text={text}
            busy={busy}
            error={error}
            onChangeText={setText}
            onSubmit={onSubmit}
            onStop={onStop}
          />

          <div className="warning-banner">
            {user
              ? `Conversas salvas na conta: ${user.username}`
              : "Conversas n\u00e3o ser\u00e3o salvas, logue para mudar isso!"}
          </div>
        </div>
      </div>

      {showAuth && (
        <AuthModal
          mode={authMode}
          initialEmail={authInitialEmail}
          onClose={() => setShowAuth(false)}
          onAuthSuccess={handleAuthSuccess}
        />
      )}
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

