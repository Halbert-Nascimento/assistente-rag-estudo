/* ============================================================
   ChatView — interface de conversa com o assistente RAG
   ============================================================ */

const CHAT_SUGESTOES = [
  "O que é aprendizado supervisionado?",
  "Como funciona o K-Means?",
  "Quais são os 4 pilares do Reinforcement Learning?",
  "Para que serve o StandardScaler?",
];

function ChatView({ seed }) {
  const [messages, setMessages] = React.useState([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [sessionId] = React.useState(() =>
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2)
  );
  const bottomRef = React.useRef(null);

  /* Auto-scroll ao adicionar mensagens */
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  /* Enviar pergunta inicial (seed vinda do HomeView) */
  React.useEffect(() => {
    if (seed) sendMessage(seed);
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
        body: JSON.stringify({ pergunta, session_id: sessionId }),
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
      <div className="chat-scroll">
        <div className="chat-inner">

          {/* Empty state */}
          {empty && (
            <div className="chat-hero rise">
              <div className="halo">
                <Icon name="book" size={26} />
              </div>
              <h1>Como posso ajudar?</h1>
              <p>
                Faça uma pergunta sobre o conteúdo das aulas.
                O assistente responde <strong>somente</strong> com base nos
                documentos indexados e cita as fontes.
              </p>
              <div
                className="sugg-grid"
                style={{ maxWidth: 640, margin: "22px auto 0" }}
              >
                {CHAT_SUGESTOES.map((s, i) => (
                  <button
                    className="sugg"
                    key={i}
                    onClick={() => sendMessage(s)}
                  >
                    <div className="s-ic">
                      <Icon name="chat" size={15} />
                    </div>
                    {s}
                    <Icon name="arrowR" size={14} className="s-arrow" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Mensagens */}
          {messages.map((msg, i) => (
            <div key={i} className={`msg ${msg.role === "user" ? "user" : "bot"}`}>
              <div className="msg-av">
                {msg.role === "user" ? "MA" : <Icon name="book" size={16} />}
              </div>
              <div className="msg-body">
                {msg.role === "user" ? (
                  /* Bubble do usuário */
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
                  /* Resposta normal com fontes */
                  <div className="answer-card">
                    <div className="answer-top">
                      <div className="bubble-bot">{msg.content}</div>
                    </div>
                    <div className="answer-foot">
                      {msg.fontes && msg.fontes.length > 0 && (
                        <>
                          <div className="answer-foot-head">
                            <Icon name="docs" size={13} /> Fontes consultadas
                          </div>
                          <div className="src-list">
                            {msg.fontes.map((f, j) => (
                              <SourceCard
                                key={j}
                                src={{ doc: f.doc, secao: "", sim: f.sim }}
                                idx={j + 1}
                              />
                            ))}
                          </div>
                          <div style={{ marginTop: 12 }}>
                            <ConfidenceMeter value={msg.sim || 0} />
                          </div>
                        </>
                      )}
                      {msg.erro && (
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
                      )}
                    </div>
                  </div>
                )}

                {/* Ações (copiar) — apenas respostas normais */}
                {msg.role === "assistant" && !msg.recusou && !msg.erro && (
                  <div className="msg-actions">
                    <button
                      className="msg-act"
                      onClick={() =>
                        navigator.clipboard?.writeText(msg.content)
                      }
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
                        style={{
                          background: "var(--high-100)",
                          color: "var(--high)",
                        }}
                      >
                        <Icon name="check" size={11} />
                      </div>
                      Contexto recuperado do ChromaDB
                    </div>
                    <div className="think-step">
                      <div
                        className="ts-ic"
                        style={{
                          background: "var(--brand-100)",
                          color: "var(--brand-600)",
                        }}
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

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Composer (input fixo no fundo) */}
      <div className="composer-wrap">
        <div className="composer">
          <div className="composer-box">
            <textarea
              placeholder="Faça uma pergunta sobre as aulas…"
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
              <Icon
                name="shield"
                size={12}
                style={{ color: "var(--high)" }}
              />
              Responde somente com base nos documentos indexados · limiar 0,68
            </span>
            <span>Enter para enviar · Shift+Enter para nova linha</span>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ChatView });
