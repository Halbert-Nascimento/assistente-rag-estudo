/* ============================================================
   Views: Início, Temas, Documentos, Desempenho, Histórico
   Todos os dados vêm da API (/api/*) — sem mock local.
   ============================================================ */

/* ---------------- INÍCIO / DASHBOARD ---------------- */
function HomeView({ goto, ask, temas }) {
  const [stats, setStats] = React.useState(null);
  const [historico, setHistorico] = React.useState([]);

  const byId = (id) =>
    temas.find((t) => t.id === id) || { nome: id || "Geral", cor: "#888", id };

  React.useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
    fetch("/api/historico")
      .then((r) => r.json())
      .then((d) => setHistorico(d.conversas || []))
      .catch(() => {});
  }, []);

  const m = stats || {};
  const emFoco = temas
    .filter((t) => !t.dominado && t.progresso > 0)
    .slice(0, 2);
  const sugestoes = m.sugestoes || [
    "O que é aprendizado supervisionado?",
    "Como funciona o K-Means?",
    "Quais são os 4 pilares do Reinforcement Learning?",
  ];

  return (
    <div className="page rise">
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div className="h-eyebrow">Inteligência Artificial · 2026.1</div>
          <h1 className="h1">Bom te ver de volta 👋</h1>
          <p className="sub">
            O assistente já processou{" "}
            <b>{(m.respondidas || 0) + (m.recusadas || 0)} perguntas</b> com
            confiança média de{" "}
            <b>{Math.round((m.confiancaMedia || 0) * 100)}%</b>. Faça uma nova
            pergunta ou continue de onde parou.
          </p>
        </div>
        <button
          className="btn btn-accent"
          style={{ padding: "12px 18px", fontSize: 15 }}
          onClick={() => goto("chat")}
        >
          <Icon name="spark" size={18} /> Perguntar ao assistente
        </button>
      </div>

      {/* Sugestões rápidas */}
      <div
        className="card"
        style={{
          marginTop: 22,
          padding: 18,
          display: "flex",
          alignItems: "center",
          gap: 14,
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: "linear-gradient(150deg,var(--brand-600),var(--brand))",
            color: "#fff",
            display: "grid",
            placeItems: "center",
            flex: "none",
          }}
        >
          <Icon name="chat" size={20} />
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontWeight: 700, fontSize: 15 }}>
            Tire uma dúvida agora
          </div>
          <div style={{ fontSize: 13, color: "var(--ink-3)" }}>
            Sugestões com base nas aulas indexadas:
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {sugestoes.slice(0, 3).map((s, i) => (
            <button
              className="chip"
              key={i}
              style={{ cursor: "pointer" }}
              onClick={() => ask(s)}
            >
              <Icon
                name="arrowR"
                size={13}
                style={{ color: "var(--accent)" }}
              />{" "}
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="perf-grid" style={{ marginTop: 24 }}>
        <StatCard
          icon="chat"
          label="Perguntas feitas"
          value={m.perguntas || 0}
          delta={m.perguntasDelta}
        />
        <StatCard
          icon="target"
          label="Confiança média"
          value={Math.round((m.confiancaMedia || 0) * 100)}
          suffix="%"
          tint="var(--high)"
        />
        <StatCard
          icon="clock"
          label="Tempo médio de resposta"
          value={m.tempoMedio || "—"}
          tint="var(--accent)"
        />
        <StatCard
          icon="layers"
          label="Cobertura do material"
          value={Math.round((m.cobertura || 0) * 100)}
          suffix="%"
          tint="var(--brand-600)"
        />
      </div>

      <div className="g2" style={{ marginTop: 24 }}>
        {/* Continue estudando */}
        <div>
          <SectionHead
            title="Continue estudando"
            action="Ver todos os temas →"
            onAction={() => goto("temas")}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {emFoco.length === 0 && (
              <div
                className="card"
                style={{
                  padding: 20,
                  color: "var(--ink-3)",
                  textAlign: "center",
                  fontSize: 14,
                }}
              >
                <Icon name="docs" size={22} style={{ marginBottom: 8, display: "block", margin: "0 auto 8px" }} />
                Nenhum documento indexado ainda.{" "}
                <button
                  className="btn btn-ghost"
                  style={{ marginLeft: 8, padding: "6px 12px", fontSize: 13 }}
                  onClick={() => goto("docs")}
                >
                  Indexar agora
                </button>
              </div>
            )}
            {emFoco.map((t) => (
              <div
                className="card"
                key={t.id}
                style={{
                  padding: 16,
                  display: "flex",
                  alignItems: "center",
                  gap: 15,
                  cursor: "pointer",
                }}
                onClick={() => goto("temas")}
              >
                <div
                  className="tema-ic"
                  style={{ background: t.cor, margin: 0, width: 44, height: 44 }}
                >
                  <Icon name="book" size={20} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      flexWrap: "wrap",
                      rowGap: 4,
                    }}
                  >
                    <span style={{ fontWeight: 700, fontSize: 15 }}>
                      {t.nome}
                    </span>
                    <span className="tag tag-mid" style={{ flex: "none" }}>
                      Em progresso
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: 12.5,
                      color: "var(--ink-3)",
                      margin: "5px 0 10px",
                    }}
                  >
                    {t.aulas} aula(s) · {t.docs} documento(s)
                  </div>
                  <div className="tema-prog">
                    <div className="bar">
                      <span
                        style={{ width: t.progresso + "%", background: t.cor }}
                      />
                    </div>
                    <span className="pct" style={{ color: t.cor }}>
                      {t.progresso}%
                    </span>
                  </div>
                </div>
                <Icon
                  name="chevR"
                  size={18}
                  style={{ color: "var(--ink-3)" }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Conversas recentes */}
        <div>
          <SectionHead
            title="Conversas recentes"
            action="Histórico →"
            onAction={() => goto("historico")}
          />
          {historico.length === 0 ? (
            <div
              className="card"
              style={{
                padding: 28,
                textAlign: "center",
                color: "var(--ink-3)",
                fontSize: 14,
              }}
            >
              Nenhuma conversa ainda. Comece fazendo uma pergunta!
            </div>
          ) : (
            <div className="card" style={{ padding: "4px 16px" }}>
              {historico.slice(0, 5).map((c) => {
                const t = byId(c.tema);
                return (
                  <div
                    className="list-row"
                    key={c.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => goto("chat")}
                  >
                    <div
                      className="list-ic"
                      style={{
                        background: t.cor + "1A",
                        color: t.cor,
                      }}
                    >
                      <Icon name="chat" size={17} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: 14,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {c.titulo}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--ink-3)" }}>
                        {t.nome} · {c.quando}
                      </div>
                    </div>
                    <ConfidenceMeter value={c.confianca || 0} compact />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------------- TEMAS ---------------- */
function TemasView({ goto, ask, temas }) {
  const totalProg =
    temas.length > 0
      ? Math.round(temas.reduce((s, t) => s + t.progresso, 0) / temas.length)
      : 0;

  return (
    <div className="page rise">
      <div className="h-eyebrow">Organização por matéria</div>
      <h1 className="h1">Temas da disciplina</h1>
      <p className="sub">
        Cada tema corresponde a um documento indexado. Progresso médio geral:{" "}
        <b>{totalProg}%</b>.
      </p>

      {temas.length === 0 ? (
        <div
          className="card"
          style={{
            marginTop: 24,
            padding: 40,
            textAlign: "center",
            color: "var(--ink-3)",
          }}
        >
          <Icon
            name="docs"
            size={28}
            style={{ marginBottom: 12, display: "block", margin: "0 auto 12px" }}
          />
          Nenhum documento encontrado na pasta{" "}
          <code style={{ fontFamily: "monospace" }}>docs/</code>.
          <br />
          Adicione arquivos .md, .pdf ou .txt e clique em{" "}
          <b>Processar Documentos</b>.
        </div>
      ) : (
        <div className="tema-grid" style={{ marginTop: 24 }}>
          {temas.map((t) => (
            <div
              className="card tema-card"
              key={t.id}
              onClick={() => ask("Me dê um resumo de " + t.nome)}
            >
              <div className="tema-top" style={{ background: t.cor }} />
              <div className="tema-in">
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div
                    className="tema-ic"
                    style={{ background: t.cor }}
                  >
                    <Icon name="book" size={19} />
                  </div>
                  {t.dominado ? (
                    <span className="tag tag-high">
                      <Icon
                        name="check"
                        size={11}
                        style={{ verticalAlign: "-1px" }}
                      />{" "}
                      Dominado
                    </span>
                  ) : t.progresso === 0 ? (
                    <span className="tag tag-muted">Não iniciado</span>
                  ) : (
                    <span className="tag tag-mid">Em progresso</span>
                  )}
                </div>
                <div className="tema-name">{t.nome}</div>
                <div className="tema-desc">{t.descricao}</div>
                <div className="tema-meta">
                  <span>
                    <b>{t.aulas}</b> aula(s)
                  </span>
                  <span>
                    <b>{t.docs}</b> doc(s)
                  </span>
                </div>
                <div className="tema-prog">
                  <div className="bar">
                    <span
                      style={{ width: t.progresso + "%", background: t.cor }}
                    />
                  </div>
                  <span className="pct" style={{ color: t.cor }}>
                    {t.progresso}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------- DOCUMENTOS ---------------- */
function DocumentosView({ temas }) {
  const [dados, setDados] = React.useState({
    arquivos: [],
    total: 0,
    indexados: 0,
    chunks: 0,
  });
  const [q, setQ] = React.useState("");
  const [filtro, setFiltro] = React.useState("todos");
  const [indexando, setIndexando] = React.useState(false);
  const [resultado, setResultado] = React.useState(null);

  const byId = (id) =>
    temas.find((t) => t.id === id) || { nome: id || "Geral", cor: "#888", id };
  const tipoCor = {
    md: "var(--brand-600)",
    pdf: "var(--accent)",
    txt: "var(--ink-2)",
  };

  function fetchDocs() {
    fetch("/api/documentos")
      .then((r) => r.json())
      .then(setDados)
      .catch(() => {});
  }

  React.useEffect(fetchDocs, []);

  async function indexar() {
    setIndexando(true);
    setResultado(null);
    try {
      const res = await fetch("/api/indexar", { method: "POST" });
      const data = await res.json();
      setResultado(data);
      fetchDocs();
    } catch {
      setResultado({ ok: false, erro: "Erro ao conectar ao servidor." });
    } finally {
      setIndexando(false);
    }
  }

  let rows = dados.arquivos || [];
  if (filtro === "indexados") rows = rows.filter((d) => d.indexado === true);
  if (filtro === "pendentes") rows = rows.filter((d) => !d.indexado);
  if (q.trim())
    rows = rows.filter((d) =>
      d.nome.toLowerCase().includes(q.toLowerCase())
    );

  return (
    <div className="page rise">
      <div className="h-eyebrow">Base de conhecimento</div>
      <h1 className="h1">Documentos de treino</h1>
      <p className="sub">
        Tudo o que o assistente pode consultar. Cada arquivo é dividido em{" "}
        <b>trechos (chunks)</b> e convertido em vetores no ChromaDB.
      </p>

      {/* Stats rápidas */}
      <div
        className="perf-grid"
        style={{ marginTop: 22, gridTemplateColumns: "repeat(4,1fr)" }}
      >
        <StatCard icon="docs" label="Documentos" value={dados.total} />
        <StatCard
          icon="check"
          label="Indexados"
          value={dados.indexados}
          tint="var(--high)"
        />
        <StatCard
          icon="layers"
          label="Trechos vetorizados"
          value={dados.chunks}
          tint="var(--brand-600)"
        />
        <StatCard
          icon="clock"
          label="Pendentes"
          value={dados.total - dados.indexados}
          tint="var(--mid)"
        />
      </div>

      {/* Feedback de indexação */}
      {resultado && (
        <div
          className="card"
          style={{
            marginTop: 16,
            padding: "14px 18px",
            borderColor: resultado.ok ? "var(--high)" : "var(--low)",
            background: resultado.ok ? "var(--high-100)" : "var(--low-100)",
            display: "flex",
            alignItems: "center",
            gap: 10,
            fontSize: 14,
          }}
        >
          <Icon
            name={resultado.ok ? "check" : "alert"}
            size={16}
            style={{ color: resultado.ok ? "var(--high)" : "var(--low)", flex: "none" }}
          />
          <div>
            {resultado.ok ? (
              <>
                <b>Indexação concluída!</b> {resultado.chunks} chunks de{" "}
                {resultado.arquivos} arquivo(s) armazenados.
                {resultado.falhas > 0 && (
                  <span style={{ color: "var(--low)", marginLeft: 8 }}>
                    {resultado.falhas} arquivo(s) com erro:{" "}
                    {(resultado.arquivos_com_erro || []).join(", ")}
                  </span>
                )}
              </>
            ) : (
              <>
                <b>Erro na indexação.</b>{" "}
                {resultado.erro || "Verifique o servidor."}
              </>
            )}
          </div>
          <button
            className="btn btn-ghost"
            style={{ marginLeft: "auto", padding: "5px 10px", fontSize: 12 }}
            onClick={() => setResultado(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Toolbar */}
      <div className="doc-toolbar" style={{ marginTop: 24 }}>
        <div className="searchbox">
          <Icon name="search" size={16} style={{ color: "var(--ink-3)" }} />
          <input
            placeholder="Buscar arquivo…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="seg">
          {[
            ["todos", "Todos"],
            ["indexados", "Indexados"],
            ["pendentes", "Pendentes"],
          ].map(([k, l]) => (
            <button
              key={k}
              className={filtro === k ? "on" : ""}
              onClick={() => setFiltro(k)}
            >
              {l}
            </button>
          ))}
        </div>
        <button
          className="btn btn-accent"
          style={{ marginLeft: "auto", padding: "9px 16px", fontSize: 14 }}
          onClick={indexar}
          disabled={indexando}
        >
          <Icon name={indexando ? "refresh" : "layers"} size={16} />
          {indexando ? "Processando…" : "Processar Documentos"}
        </button>
      </div>

      {/* Tabela */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div className="doc-row head">
          <span>Arquivo</span>
          <span>Tema</span>
          <span>Trechos</span>
          <span>Status</span>
          <span />
        </div>
        {rows.map((d) => {
          const t = byId(d.tema);
          return (
            <div className="doc-row" key={d.id}>
              <div className="doc-file">
                <div
                  className="doc-fic"
                  style={{ background: tipoCor[d.tipo] || "var(--ink-3)" }}
                >
                  {(d.tipo || "").toUpperCase()}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div className="doc-fname">{d.nome}</div>
                  <div className="doc-fmeta">
                    {d.tamanho} · adicionado em {d.data}
                  </div>
                </div>
              </div>
              <div>
                <span
                  className="chip"
                  style={{
                    borderColor: t.cor + "44",
                    color: t.cor,
                    background: t.cor + "12",
                  }}
                >
                  {t.nome}
                </span>
              </div>
              <div
                style={{
                  fontWeight: 700,
                  fontVariantNumeric: "tabular-nums",
                  color: d.chunks ? "var(--ink)" : "var(--ink-3)",
                }}
              >
                {d.chunks || "—"}{" "}
                <span
                  className="muted"
                  style={{ fontWeight: 500, fontSize: 12 }}
                >
                  chunks
                </span>
              </div>
              <div>
                {d.indexado === true ? (
                  <span className="tag tag-high">
                    <Icon
                      name="check"
                      size={11}
                      style={{ verticalAlign: "-1px" }}
                    />{" "}
                    Indexado
                  </span>
                ) : d.indexado === "processando" ? (
                  <span className="tag tag-mid">
                    <Icon
                      name="refresh"
                      size={11}
                      style={{ verticalAlign: "-1px" }}
                    />{" "}
                    Processando
                  </span>
                ) : (
                  <span className="tag tag-muted">
                    <Icon
                      name="clock"
                      size={11}
                      style={{ verticalAlign: "-1px" }}
                    />{" "}
                    Não indexado
                  </span>
                )}
              </div>
              <button className="icon-btn" style={{ width: 32, height: 32 }}>
                <Icon name="dot3" size={16} />
              </button>
            </div>
          );
        })}
        {rows.length === 0 && (
          <div
            style={{ padding: 40, textAlign: "center", color: "var(--ink-3)" }}
          >
            {dados.total === 0
              ? "Nenhum arquivo encontrado na pasta docs/."
              : "Nenhum arquivo corresponde ao filtro."}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------------- DESEMPENHO ---------------- */
function DesempenhoView() {
  const [stats, setStats] = React.useState(null);

  React.useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
  }, []);

  if (!stats) {
    return (
      <div className="page rise" style={{ color: "var(--ink-3)", textAlign: "center" }}>
        Carregando métricas…
      </div>
    );
  }

  const m = stats;
  const maxSerie = Math.max(...(m.serie || [0.001]));
  const totalDist = (m.dist || []).reduce((s, d) => s + d.v, 0);

  return (
    <div className="page rise">
      <div className="h-eyebrow">Acompanhamento</div>
      <h1 className="h1">Seu desempenho</h1>
      <p className="sub">
        Como suas perguntas estão indo — e o quanto o assistente conseguiu
        responder com confiança.
      </p>

      <div className="perf-grid" style={{ marginTop: 22 }}>
        <StatCard
          icon="chat"
          label="Perguntas feitas"
          value={m.perguntas}
          delta={m.perguntasDelta}
        />
        <StatCard
          icon="check"
          label="Respondidas"
          value={m.respondidas}
          tint="var(--high)"
        />
        <StatCard
          icon="shield"
          label="Recusadas (fora do escopo)"
          value={m.recusadas}
          tint="var(--low)"
        />
        <StatCard
          icon="clock"
          label="Tempo médio"
          value={m.tempoMedio}
          tint="var(--brand-600)"
        />
      </div>

      <div className="g2" style={{ marginTop: 24 }}>
        {/* Gráfico confiança por dia */}
        <div className="card" style={{ padding: 20 }}>
          <SectionHead title="Confiança média por dia" />
          {m.perguntas === 0 ? (
            <div style={{ textAlign: "center", color: "var(--ink-3)", padding: "32px 0", fontSize: 14 }}>
              Nenhuma pergunta registrada ainda.
            </div>
          ) : (
            <>
              <div className="bars">
                {(m.serie || []).map((v, i) => (
                  <div className="col" key={i}>
                    <div
                      className="b"
                      style={{
                        height: maxSerie > 0 ? (v / maxSerie) * 100 + "%" : "0%",
                        background: confColor(v),
                        minHeight: v > 0 ? 4 : 0,
                      }}
                    >
                      {v > 0 && <span className="v">{Math.round(v * 100)}</span>}
                    </div>
                    <span className="lbl">{(m.serieDias || [])[i]}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", gap: 16, marginTop: 16, fontSize: 12, color: "var(--ink-3)" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <i style={{ width: 9, height: 9, borderRadius: 3, background: "var(--high)" }} /> Alta
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <i style={{ width: 9, height: 9, borderRadius: 3, background: "var(--mid)" }} /> Média
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <i style={{ width: 9, height: 9, borderRadius: 3, background: "var(--low)" }} /> Baixa
                </span>
              </div>
            </>
          )}
        </div>

        {/* Donut qualidade */}
        <div className="card" style={{ padding: 20 }}>
          <SectionHead title="Qualidade das respostas" />
          {m.perguntas === 0 ? (
            <div style={{ textAlign: "center", color: "var(--ink-3)", padding: "32px 0", fontSize: 14 }}>
              Nenhuma pergunta registrada ainda.
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
              <Ring
                value={m.perguntas > 0 ? m.respondidas / m.perguntas : 0}
                size={118}
                stroke={11}
                color="var(--high)"
                label={
                  m.perguntas > 0
                    ? Math.round((m.respondidas / m.perguntas) * 100) + "%"
                    : "—"
                }
                sub="com fonte"
              />
              <div style={{ flex: 1 }}>
                {(m.dist || []).map((d, i) => (
                  <div className="dist-row" key={i}>
                    <div className="d-label">
                      <div style={{ fontWeight: 600, fontSize: 13.5 }}>
                        {d.faixa}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
                        {d.sub}
                      </div>
                    </div>
                    <div className="d-bar">
                      <span
                        style={{
                          width: totalDist > 0 ? (d.v / totalDist) * 100 + "%" : "0%",
                          background: d.cor,
                        }}
                      />
                    </div>
                    <div className="d-val">{d.v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------------- HISTÓRICO ---------------- */
function HistoricoView({ goto, temas }) {
  const [conversas, setConversas] = React.useState([]);

  const byId = (id) =>
    temas.find((t) => t.id === id) || { nome: id || "Geral", cor: "#888", id };

  React.useEffect(() => {
    fetch("/api/historico")
      .then((r) => r.json())
      .then((d) => setConversas(d.conversas || []))
      .catch(() => {});
  }, []);

  return (
    <div className="page rise">
      <div className="h-eyebrow">Suas conversas</div>
      <h1 className="h1">Histórico</h1>
      <p className="sub">
        Retome qualquer conversa anterior. Cada uma guarda as fontes que foram
        citadas.
      </p>

      {conversas.length === 0 ? (
        <div
          className="card"
          style={{
            marginTop: 22,
            padding: 48,
            textAlign: "center",
            color: "var(--ink-3)",
          }}
        >
          <Icon
            name="history"
            size={28}
            style={{ marginBottom: 12, display: "block", margin: "0 auto 12px" }}
          />
          Nenhuma conversa ainda.
          <br />
          <button
            className="btn btn-ghost"
            style={{ marginTop: 14, fontSize: 14 }}
            onClick={() => goto("chat")}
          >
            <Icon name="chat" size={16} /> Iniciar uma conversa
          </button>
        </div>
      ) : (
        <div className="card" style={{ marginTop: 22, padding: "4px 18px" }}>
          {conversas.map((c) => {
            const t = byId(c.tema);
            return (
              <div
                className="list-row"
                key={c.id}
                style={{ cursor: "pointer" }}
                onClick={() => goto("chat")}
              >
                <div
                  className="list-ic"
                  style={{ background: t.cor + "1A", color: t.cor }}
                >
                  <Icon name="chat" size={18} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: 14.5,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {c.titulo}
                  </div>
                  <div
                    style={{
                      fontSize: 12.5,
                      color: "var(--ink-3)",
                      marginTop: 1,
                    }}
                  >
                    <span
                      className="chip"
                      style={{
                        padding: "1px 8px",
                        borderColor: t.cor + "44",
                        color: t.cor,
                        background: t.cor + "12",
                        fontSize: 11.5,
                      }}
                    >
                      {t.nome}
                    </span>
                    &nbsp;· {c.msgs} mensagens · {c.quando}
                  </div>
                </div>
                <ConfidenceMeter value={c.confianca || 0} compact />
                <Icon
                  name="chevR"
                  size={18}
                  style={{ color: "var(--ink-3)" }}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

Object.assign(window, {
  HomeView,
  TemasView,
  DocumentosView,
  DesempenhoView,
  HistoricoView,
});
