/* ============================================================
   App shell — sidebar nav + topbar + router
   ============================================================ */

const NAV = [
  { id: "home",       label: "Início",         icon: "home"    },
  { id: "chat",       label: "Assistente",      icon: "chat",    badge: "IA" },
  { id: "temas",      label: "Temas & Matérias",icon: "layers"  },
  { id: "docs",       label: "Documentos",      icon: "docs"    },
  { id: "desempenho", label: "Desempenho",       icon: "chart"   },
  { id: "historico",  label: "Histórico",        icon: "history" },
];

const CRUMB = {
  home:       ["Início"],
  chat:       ["Assistente"],
  temas:      ["Temas & Matérias"],
  docs:       ["Documentos"],
  desempenho: ["Desempenho"],
  historico:  ["Histórico"],
};

function App() {
  const [view,     setView]     = React.useState("home");
  const [seed,     setSeed]     = React.useState(null);
  const [nonce,    setNonce]    = React.useState(0);
  const [status,   setStatus]   = React.useState({ ollama: false, pronto: false, modelo: "llama3.1", docs_indexados: 0 });
  // temas: null = ainda carregando (BUG-001); [] = realmente vazio
  const [temas,    setTemas]    = React.useState(null);
  const [resumeId, setResumeId] = React.useState(null);   // conversa a retomar (BUG-002)
  const [materia,  setMateria]  = React.useState(null);   // escopo do chat (FEAT-003)

  function refreshStatus() {
    fetch("/api/status")
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => {});
  }

  function refreshTemas() {
    fetch("/api/documentos")
      .then((r) => r.json())
      .then((d) => setTemas(d.temas || []))
      .catch(() => setTemas([]));
  }

  React.useEffect(() => {
    refreshStatus();
    refreshTemas();
    const id = setInterval(refreshStatus, 30000);
    return () => clearInterval(id);
  }, []);

  React.useEffect(() => {
    if (view === "home" || view === "temas") refreshTemas();
  }, [view]);

  function goto(v) { setView(v); }

  /* Pergunta vinda da Home (escopo geral) */
  function ask(q) {
    setSeed(q); setResumeId(null); setMateria(null);
    setNonce((n) => n + 1); setView("chat");
  }

  /* Chat limpo */
  function newChat() {
    setSeed(null); setResumeId(null); setMateria(null);
    setNonce((n) => n + 1); setView("chat");
  }

  /* Retomar conversa do histórico (BUG-002) */
  function openConversation(id) {
    setSeed(null); setResumeId(id); setMateria(null);
    setNonce((n) => n + 1); setView("chat");
  }

  /* Chat limpo com escopo de matéria (BUG-005 + FEAT-003) */
  function openMateria(t) {
    setSeed(null); setResumeId(null); setMateria(t);
    setNonce((n) => n + 1); setView("chat");
  }

  const temasList = temas || [];

  const statusColor  = status.pronto ? "var(--high)" : status.ollama ? "var(--mid)" : "var(--low)";
  const statusBg     = status.pronto ? "var(--high-100)" : status.ollama ? "var(--mid-100)" : "var(--low-100)";
  const statusBorder = status.pronto ? "rgba(47,133,89,.2)" : status.ollama ? "rgba(198,137,27,.2)" : "rgba(194,66,48,.2)";
  const statusLabel  = status.pronto
    ? `Ollama · ${status.modelo} ativo`
    : status.ollama
    ? `Ollama ativo · sem docs indexados`
    : "Ollama offline";

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="side">
        <div className="brand">
          <div className="brand-mark">
            <Icon name="book" size={20} style={{ color: "#fff" }} />
          </div>
          <div>
            <div className="brand-name">
              Assistente de estudos
            </div>
          </div>
        </div>

        <div className="nav-label">Navegação</div>
        {NAV.slice(0, 2).map((n) => (
          <button
            key={n.id}
            className={"nav-item" + (view === n.id ? " active" : "")}
            onClick={() => (n.id === "chat" ? newChat() : goto(n.id))}
          >
            <Icon name={n.icon} size={19} /> {n.label}
            {n.badge && <span className="nav-badge">{n.badge}</span>}
          </button>
        ))}

        <div className="nav-label">Conteúdo</div>
        {NAV.slice(2).map((n) => {
          const badge = n.id === "temas" && temasList.length > 0 ? String(temasList.length) : n.badge;
          return (
            <button
              key={n.id}
              className={"nav-item" + (view === n.id ? " active" : "")}
              onClick={() => goto(n.id)}
            >
              <Icon name={n.icon} size={19} /> {n.label}
              {badge && <span className="nav-badge">{badge}</span>}
            </button>
          );
        })}

        <div className="side-spacer" />

        <div className="side-card">
          <div className="sc-title">
            <Icon name="shield" size={15} style={{ color: "var(--accent)" }} /> Modo confiável
          </div>
          <div className="sc-row">
            <span className="sc-dot" style={{ background: status.pronto ? "var(--high)" : "var(--mid)" }} />
            {temas === null
              ? "Carregando documentos…"
              : temasList.length > 0
              ? `${temasList.reduce((s, t) => s + t.docs, 0)} documento(s) · ${status.docs_indexados} trechos`
              : "Nenhum documento indexado"}
          </div>
          <div className="sc-meta">
            O assistente responde <b style={{ color: "#fff" }}>somente</b> com
            base no material das aulas e cita as fontes.
          </div>
        </div>

      </aside>

      {/* Main */}
      <div className="main">
        <header className="topbar">
          <div className="crumb">
            <Icon name="home" size={15} />
            <Icon name="chevR" size={13} />
            {(CRUMB[view] || ["Início"]).map((c, i, arr) => (
              <React.Fragment key={i}>
                {i === arr.length - 1 ? <b>{c}</b> : <span>{c}</span>}
                {i < arr.length - 1 && <Icon name="chevR" size={13} />}
              </React.Fragment>
            ))}
            {view === "chat" && materia && (
              <>
                <Icon name="chevR" size={13} />
                <b style={{ color: materia.cor }}>{materia.nome}</b>
              </>
            )}
          </div>
          <div className="topbar-spacer" />

          {/* Badge de status dinâmico */}
          <div
            className="status-pill"
            style={{ color: statusColor, background: statusBg, borderColor: statusBorder }}
          >
            <span
              className="led"
              style={{ background: statusColor, boxShadow: `0 0 0 0 ${statusColor}80` }}
            />
            {statusLabel}
          </div>

          {view === "chat" && (
            <button
              className="btn btn-ghost"
              style={{ padding: "8px 13px", fontSize: 13 }}
              onClick={newChat}
            >
              <Icon name="plus" size={16} /> Nova conversa
            </button>
          )}
          <button className="icon-btn">
            <Icon name="search" size={18} />
          </button>
          <div className="avatar">IA</div>
        </header>

        <div
          className="main-body"
          style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}
        >
          {view === "home"       && <div className="scroll"><HomeView       goto={goto} ask={ask} newChat={newChat} temas={temas} openConversation={openConversation} /></div>}
          {view === "chat"       && <ChatView key={nonce} seed={seed} resumeId={resumeId} materia={materia} />}
          {view === "temas"      && <div className="scroll"><TemasView      goto={goto} temas={temas} openMateria={openMateria} /></div>}
          {view === "docs"       && <div className="scroll"><DocumentosView temas={temasList} onIndexed={refreshTemas} /></div>}
          {view === "desempenho" && <div className="scroll"><DesempenhoView /></div>}
          {view === "historico"  && <div className="scroll"><HistoricoView  goto={goto} newChat={newChat} temas={temasList} openConversation={openConversation} /></div>}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
