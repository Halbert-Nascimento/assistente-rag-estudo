/* ============================================================
   ChatView — interface de conversa com o assistente RAG
   Props:
     seed     — pergunta inicial (vinda da Home)
     resumeId — id de conversa do historico para retomar
     materia  — {id, nome, cor} para chat com escopo de materia
   ============================================================ */

const CHAT_SUGESTOES = [
  "O que é aprendizado supervisionado?",
  "Como funciona o K-Means?",
  "Quais são os 4 pilares do Reinforcement Learning?",
  "Para que serve o StandardScaler?",
];

/* ---------- Markdown leve (negrito, itálico, código, listas) ---------- */
function mdInline(text) {
  const parts = String(text).split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (/^\*[^*]+\*$/.test(p)) return <em key={i}>{p.slice(1, -1)}</em>;
    if (/^`[^`]+`$/.test(p)) return <code key={i}>{p.slice(1, -1)}</code>;
    return p;
  });
}

function MarkdownLite({ text }) {
  const blocks = String(text || "").trim().split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, i) => {
        const lines = block.split("\n").filter((l) => l.trim() !== "");
        const isList = lines.length > 0 && lines.every((l) => /^\s*([-*•]|\d+[.)])\s+/.test(l));
        if (isList) {
          return (
            <ul key={i}>
              {lines.map((l, j) => (
                <li key={j}>{mdInline(l.replace(/^\s*([-*•]|\d+[.)])\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i}>
            {lines.map((l, j) => (
              <React.Fragment key={j}>
                {mdInline(l)}
                {j < lines.length - 1 && <br />}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}

/* ---------- Fontes consultadas (retrátil, fechada por padrão) ---------- */
function FontesRetratil({ fontes, sim }) {
  const [open, setOpen] = React.useState(false);
  if (!fontes || fontes.length === 0) return null;
  return (
    <div className="answer-foot">
      <button className="fontes-toggle" onClick={() => setOpen((o) => !o)}>
        <Icon name="docs" size={13} />
        {fontes.length} fonte{fontes.length > 1 ? "s" : ""} consultada{fontes.length > 1 ? "s" : ""}
        <span className="muted" style={{ fontWeight: 500 }}>
          · {Math.round((sim || 0) * 100)}% similaridade
        </span>
        <Icon
          name="chevR"
          size={13}
          style={{
            marginLeft: "auto",
            transform: open ? "rotate(90deg)" : "none",
            transition: "transform .15s",
          }}
        />
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          <div className="src-list">
            {fontes.map((f, j) => (
              <SourceCard key={j} src={{ doc: f.doc, secao: "", sim: f.sim }} idx={j + 1} />
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            <ConfidenceMeter value={sim || 0} />
          </div>
        </div>
      )}
    </div>
  );
}

function ChatView({ seed, resumeId, materia }) {
  const [messages, setMessages] = React.useState([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [sessionId] = React.useState(
    () =>
      resumeId ||
      (typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2))
  );
  const scrollRef = React.useRef(null);

  /* Auto-scroll: rola apenas o contêiner interno do chat (BUG-004) */
  React.useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  /* Retomar conversa do histórico (BUG-002) ou enviar seed */
  React.useEffect(() => {
    if (resumeId) {
      fetch(`/api/historico/${resumeId}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((c) => {
          if (!c || !c.mensagens) return;
          setMessages(
            c.mensagens.map((m) =>
              m.role === "user"
                ? { role: "user", content: m.content }
                : {
                    role: "assistant",
                    content: m.content,
                    fontes: m.fontes || [],
                    sim: m.sim || 0,
                    recusou: m.recusou || false,
                  }
            )
          );
        })
        .catch(() => {});
    } else if (seed) {
      sendMessage(seed);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function sendMessage(text) {
    const pergunta = (text !== undefined ? String(text) : input).trim();
    if (!pergunta || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: pergunta }]);
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pergunta,
          session_id: sessionId,
          materia: materia ? materia.id : null,
        }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.resposta,
          fontes: data.fontes || [],
          sim: data.sim || 0,
          recusou: data.recusou,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Erro ao conectar ao assistente. Verifique se o servidor está rodando e o Ollama ativo.",
          fontes: [],
          sim: 0,
          recusou: false,
          erro: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function handleTextarea(e) {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 140) + "px";
  }

  const empty = messages.length === 0 && !loading;

  return (
    <div className="chat-wrap">
      {/* Área de mensagens */}
      <div className="chat-scroll" ref={scrollRef}>
        <div className="chat-inner">

          {/* Empty state */}
          {empty && (
            <div className="chat-hero rise">
              <div
                className="halo"
                style={materia ? { background: materia.cor } : undefined}
              >
                <Icon name="book" size={26} />
              </div>
              <h1>
                {materia ? `Pergunte sobre ${materia.nome}` : "Como posso ajudar?"}
              </h1>
              <p>
                {materia ? (
                  <>
                    Este chat busca respostas <strong>somente nos documentos
                    de {materia.nome}</strong> e cita as fontes.
                  </>
                ) : (
                  <>
                    Faça uma pergunta sobre o conteúdo das aulas. O assistente
                    responde <strong>somente</strong> com base nos documentos
                    indexados e cita as fontes.
                  </>
                )}
              </p>
              {!materia && (
                <div
                  className="sugg-grid"
                  style={{ maxWidth: 640, margin: "22px auto 0" }}
                >
                  {CHAT_SUGESTOES.map((s, i) => (
                    <button className="sugg" key={i} onClick={() => sendMessage(s)}>
                      <div className="s-ic">
                        <Icon name="chat" size={15} />
                      </div>
                      {s}
                      <Icon name="arrowR" size={14} className="s-arrow" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mensagens */}
          {messages.map((msg, i) => (
            <div key={i} className={`msg ${msg.role === "user" ? "user" : "bot"}`}>
              <div className="msg-av">
                {msg.role === "user" ? "EU" : <Icon name="book" size={16} />}
              </div>
              <div className="msg-body">
                {msg.role === "user" ? (
                  <div className="bubble-user">{msg.content}</div>
                ) : msg.recusou ? (
                  /* Recusa determinística */
                  <div className="refusal">
                    <div className="refusal-head">
                      <Icon name="shield" size={17} /> Fora do escopo
                    </div>
                    <p>{msg.content}</p>
                    <div className="why">
                      <Icon name="alert" size={14} />
                      Similaridade top-1:{" "}
                      <strong>{Math.round((msg.sim || 0) * 100)}%</strong> —
                      abaixo do limiar de 68%
                    </div>
                  </div>
                ) : (
                  /* Resposta normal: corpo + fontes retráteis (BUG-003) */
                  <div className="answer-card">
                    <div className="answer-top">
                      <div className="bubble-bot">
                        <MarkdownLite text={msg.content} />
                      </div>
                    </div>
                    {msg.erro ? (
                      <div className="answer-foot">
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            color: "var(--low)",
                            fontSize: 13,
                          }}
                        >
                          <Icon name="alert" size={14} />
                          Verifique se o Ollama está rodando e o modelo baixado.
                        </div>
                      </div>
                    ) : (
                      <FontesRetratil fontes={msg.fontes} sim={msg.sim} />
                    )}
                  </div>
                )}

                {/* Ações (copiar) — apenas respostas normais */}
                {msg.role === "assistant" && !msg.recusou && !msg.erro && (
                  <div className="msg-actions">
                    <button
                      className="msg-act"
                      onClick={() => navigator.clipboard?.writeText(msg.content)}
                    >
                      <Icon name="copy" size={13} /> Copiar
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Indicador de carregamento */}
          {loading && (
            <div className="msg bot">
              <div className="msg-av">
                <Icon name="book" size={16} />
              </div>
              <div className="msg-body">
                <div className="thinking">
                  <div className="think-steps">
                    <div className="think-step done">
                      <div
                        className="ts-ic"
                        style={{ background: "var(--high-100)", color: "var(--high)" }}
                      >
                        <Icon name="check" size={11} />
                      </div>
                      Contexto recuperado do ChromaDB
                    </div>
                    <div className="think-step">
                      <div
                        className="ts-ic"
                        style={{ background: "var(--brand-100)", color: "var(--brand-600)" }}
                      >
                        <span className="dots">
                          <span />
                          <span />
                          <span />
                        </span>
                      </div>
                      Gerando resposta com llama3.1…
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Composer (input fixo no fundo) */}
      <div className="composer-wrap">
        <div className="composer">
          <div className="composer-box">
            <textarea
              placeholder={
                materia
                  ? `Pergunte sobre ${materia.nome}…`
                  : "Faça uma pergunta sobre as aulas…"
              }
              value={input}
              onChange={handleTextarea}
              onKeyDown={handleKey}
              rows={1}
              disabled={loading}
              style={{ minHeight: 38 }}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              title="Enviar (Enter)"
            >
              <Icon name="arrowR" size={18} />
            </button>
          </div>
          <div className="composer-hint">
            <span className="composer-scope">
              {materia ? (
                <>
                  <Icon name="layers" size={12} style={{ color: materia.cor }} />
                  Escopo: <b style={{ color: materia.cor }}>{materia.nome}</b> · só
                  documentos desta matéria
                </>
              ) : (
                <>
                  <Icon name="shield" size={12} style={{ color: "var(--high)" }} />
                  Responde somente com base nos documentos indexados · limiar 0,68
                </>
              )}
            </span>
            <span>Enter para enviar · Shift+Enter para nova linha</span>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ChatView });
