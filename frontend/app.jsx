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
  const [view,   setView]   = React.useState("home");
  const [seed,   setSeed]   = React.useState(null);
  const [nonce,  setNonce]  = React.useState(0);
  const [status, setStatus] = React.useState({ ollama: false, pronto: false, modelo: "llama3.1", docs_indexados: 0 });
  const [temas,  setTemas]  = React.useState([]);

  /* Busca status e temas na montagem e a cada 30 s */
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
      .catch(() => {});
  }

  React.useEffect(() => {
    refreshStatus();
    refreshTemas();
    const id = setInterval(refreshStatus, 30000);
    return () => clearInterval(id);
  }, []);

  /* Refresh de temas após indexação (DocumentosView chama goto("docs") de volta) */
  React.useEffect(() => {
    if (view === "home" || view === "temas") refreshTemas();
  }, [view]);

  function goto(v)  { setView(v); }
  function ask(q)   { setSeed(q); setNonce((n) => n + 1); setView("chat"); }
  function newChat(){ setSeed(null); setNonce((n) => n + 1); setView("chat"); }

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
              Aula<span style={{ color: "var(--accent)" }}>·</span>RAG
            </div>
            <div className="brand-sub">Assistente de estudos</div>
          </div>
        </div>

        <div className="nav-label">Navegação</div>
        {NAV.slice(0, 2).map((n) => (
          <button
            key={n.id}
            className={"nav-item" + (view === n.id ? " active" : "")}
            onClick={() => goto(n.id)}
          >
            <Icon name={n.icon} size={19} /> {n.label}
            {n.badge && <span className="nav-badge">{n.badge}</span>}
          </button>
        ))}

        <div className="nav-label">Conteúdo</div>
        {NAV.slice(2).map((n) => {
          const badge = n.id === "docs" && temas.length > 0 ? String(temas.length) : n.badge;
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
            {temas.length > 0
              ? `${temas.length} documento(s) · ${status.docs_indexados} trechos`
              : "Nenhum documento indexado"}
          </div>
          <div className="sc-meta">
            O assistente responde <b style={{ color: "#fff" }}>somente</b> com
            base no material das aulas e cita as fontes.
          </div>
        </div>

        <div className="nav-item" style={{ marginTop: 8 }}>
          <div className="avatar" style={{ width: 30, height: 30, fontSize: 12 }}>
            IA
          </div>
          <div style={{ lineHeight: 1.2 }}>
            <div style={{ color: "#fff", fontWeight: 600, fontSize: 13 }}>
              Estudante
            </div>
            <div style={{ fontSize: 11, color: "var(--side-ink-3)" }}>
              IA · Prof. Rogério
            </div>
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
          {view === "home"       && <div className="scroll"><HomeView       goto={goto} ask={ask} temas={temas} /></div>}
          {view === "chat"       && <ChatView key={nonce} goto={goto} seed={seed} />}
          {view === "temas"      && <div className="scroll"><TemasView      goto={goto} ask={ask} temas={temas} /></div>}
          {view === "docs"       && <div className="scroll"><DocumentosView temas={temas} /></div>}
          {view === "desempenho" && <div className="scroll"><DesempenhoView /></div>}
          {view === "historico"  && <div className="scroll"><HistoricoView  goto={goto} temas={temas} /></div>}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
