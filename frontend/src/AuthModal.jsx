const { useState, useEffect } = React;

function AuthModal({ mode, initialEmail, onClose, onAuthSuccess }) {
  const [username, setUsername] = useState(initialEmail || "");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentMode, setCurrentMode] = useState(mode || "login");

  useEffect(() => {
    if (initialEmail) setUsername(initialEmail);
  }, [initialEmail]);

  const reset = () => {
    setPassword("");
    setPasswordConfirm("");
    setError("");
  };

  const switchMode = (newMode) => {
    reset();
    setCurrentMode(newMode);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (currentMode === "register") {
        if (password !== passwordConfirm) {
          setError("As senhas nao conferem.");
          setLoading(false);
          return;
        }
        await apiRegister(username.trim(), password, passwordConfirm);
      } else {
        await apiLogin(username.trim(), password);
      }
      onAuthSuccess();
      onClose();
    } catch (err) {
      if (currentMode === "login" && err.message.includes("nao cadastrado")) {
        switchMode("register");
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-header">
          <h2>{currentMode === "login" ? "Entrar" : "Cadastrar"}</h2>
          <button className="auth-modal-close" onClick={onClose} aria-label="Fechar">&times;</button>
        </div>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Nome de usuario"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />

          <input
            type="password"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={1}
          />

          {currentMode === "register" && (
            <input
              type="password"
              placeholder="Confirmar senha"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              minLength={1}
            />
          )}

          <button type="submit" disabled={loading}>
            {loading ? "Aguarde..." : currentMode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>

        <p className="auth-switch">
          {currentMode === "login" ? (
            <>
              Nao tem conta?{" "}
              <a href="#" onClick={() => switchMode("register")}>
                Cadastre-se
              </a>
            </>
          ) : (
            <>
              Ja tem conta?{" "}
              <a href="#" onClick={() => switchMode("login")}>
                Faca login
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}