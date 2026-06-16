/* ============================================================
   Views: Início, Temas, Documentos, Desempenho, Histórico
   Todos os dados vêm da API (/api/*) — sem mock local.
   Convenção: temas === null → carregando; [] → vazio de fato.
   ============================================================ */

function Loading({ label }) {
  return (
    <div
      className="card"
      style={{
        padding: 28,
        textAlign: "center",
        color: "var(--ink-3)",
        fontSize: 14,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
      }}
    >
      <span className="dots">
        <span />
        <span />
        <span />
      </span>
      {label || "Carregando…"}
    </div>
  );
}

/* ---------------- INÍCIO / DASHBOARD ---------------- */
function HomeView({ goto, ask, newChat, temas, openConversation }) {
  const [stats, setStats] = React.useState(null);
  const [historico, setHistorico] = React.useState(null);

  const temasList = temas || [];
  const byId = (id) =>
    temasList.find((t) => t.id === id) || { nome: id || "Geral", cor: "#888", id };

  React.useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
    fetch("/api/historico")
      .then((r) => r.json())
      .then((d) => setHistorico(d.conversas || []))
      .catch(() => setHistorico([]));
  }, []);

  const m = stats || {};
  const emFoco = temasList.filter((t) => t.progresso > 0).slice(0, 2);
  const sugestoes = m.sugestoes || [];

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
          <div className="h-eyebrow">Assistente virtual de estudos</div>
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
          onClick={() => newChat()}
        >
          <Icon name="spark" size={18} /> Perguntar ao assistente
        </button>
      </div>

      {/* Sugestões rápidas (3, baseadas nos últimos documentos) */}
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
          <div style={{ fontWeight: 700, fontSize: 15 }}>Tire uma dúvida agora</div>
          <div style={{ fontSize: 13, color: "var(--ink-3)" }}>
            Sugestões com base nos últimos documentos processados:
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
              <Icon name="arrowR" size={13} style={{ color: "var(--accent)" }} /> {s}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="perf-grid" style={{ marginTop: 24 }}>
        <StatCard icon="chat" label="Perguntas feitas" value={m.perguntas || 0} delta={m.perguntasDelta} />
        <StatCard icon="target" label="Confiança média" value={Math.round((m.confiancaMedia || 0) * 100)} suffix="%" tint="var(--high)" />
        <StatCard icon="clock" label="Tempo médio de resposta" value={m.tempoMedio || "—"} tint="var(--accent)" />
        <StatCard icon="layers" label="Cobertura do material" value={Math.round((m.cobertura || 0) * 100)} suffix="%" tint="var(--brand-600)" />
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
            {temas === null ? (
              <Loading label="Carregando documentos…" />
            ) : temasList.length === 0 ? (
              <div
                className="card"
                style={{ padding: 20, color: "var(--ink-3)", textAlign: "center", fontSize: 14 }}
              >
                Nenhum documento indexado ainda.{" "}
                <button
                  className="btn btn-ghost"
                  style={{ marginLeft: 8, padding: "6px 12px", fontSize: 13 }}
                  onClick={() => goto("docs")}
                >
                  Indexar agora
                </button>
              </div>
            ) : (
              emFoco.map((t) => (
                <div
                  className="card"
                  key={t.id}
                  style={{ padding: 16, display: "flex", alignItems: "center", gap: 15, cursor: "pointer" }}
                  onClick={() => goto("temas")}
                >
                  <div className="tema-ic" style={{ background: t.cor, margin: 0, width: 44, height: 44 }}>
                    <Icon name="book" size={20} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", rowGap: 4 }}>
                      <span style={{ fontWeight: 700, fontSize: 15 }}>{t.nome}</span>
                      {t.progresso >= 100 ? (
                        <span className="tag tag-high" style={{ flex: "none" }}>Indexada</span>
                      ) : (
                        <span className="tag tag-mid" style={{ flex: "none" }}>Em progresso</span>
                      )}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--ink-3)", margin: "5px 0 10px" }}>
                      {t.docs} documento(s)
                    </div>
                    <div className="tema-prog">
                      <div className="bar">
                        <span style={{ width: t.progresso + "%", background: t.cor }} />
                      </div>
                      <span className="pct" style={{ color: t.cor }}>{t.progresso}%</span>
                    </div>
                  </div>
                  <Icon name="chevR" size={18} style={{ color: "var(--ink-3)" }} />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Conversas recentes */}
        <div>
          <SectionHead
            title="Conversas recentes"
            action="Histórico →"
            onAction={() => goto("historico")}
          />
          {historico === null ? (
            <Loading label="Carregando conversas…" />
          ) : historico.length === 0 ? (
            <div
              className="card"
              style={{ padding: 28, textAlign: "center", color: "var(--ink-3)", fontSize: 14 }}
            >
              Nenhuma conversa ainda. Comece fazendo uma pergunta!
            </div>
          ) : (
            <div className="card" style={{ padding: "4px 16px" }}>
              {historico.slice(0, 5).map((c) => {
                const t = byId(c.materia || c.tema);
                return (
                  <div
                    className="list-row"
                    key={c.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => openConversation(c.id)}
                  >
                    <div className="list-ic" style={{ background: t.cor + "1A", color: t.cor }}>
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
function TemasView({ goto, temas, openMateria }) {
  const temasList = temas || [];
  const totalProg =
    temasList.length > 0
      ? Math.round(temasList.reduce((s, t) => s + t.progresso, 0) / temasList.length)
      : 0;

  return (
    <div className="page rise">
      <div className="h-eyebrow">Organização por matéria</div>
      <h1 className="h1">Temas da disciplina</h1>
      <p className="sub">
        Cada matéria corresponde a uma subpasta de <code>docs/</code> e pode
        conter vários documentos. Clique numa matéria para abrir um chat com
        escopo apenas nos documentos dela. Progresso médio: <b>{totalProg}%</b>.
      </p>

      {temas === null ? (
        <div style={{ marginTop: 24 }}>
          <Loading label="Carregando matérias…" />
        </div>
      ) : temasList.length === 0 ? (
        <div
          className="card"
          style={{ marginTop: 24, padding: 40, textAlign: "center", color: "var(--ink-3)" }}
        >
          <Icon
            name="docs"
            size={28}
            style={{ marginBottom: 12, display: "block", margin: "0 auto 12px" }}
          />
          Nenhum documento encontrado na pasta{" "}
          <code style={{ fontFamily: "monospace" }}>docs/</code>.
          <br />
          Adicione arquivos .md, .pdf ou .txt e clique em <b>Processar Documentos</b>.
        </div>
      ) : (
        <div className="tema-grid" style={{ marginTop: 24 }}>
          {temasList.map((t) => (
            <div className="card tema-card" key={t.id} onClick={() => openMateria(t)}>
              <div className="tema-top" style={{ background: t.cor }} />
              <div className="tema-in">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div className="tema-ic" style={{ background: t.cor }}>
                    <Icon name="book" size={19} />
                  </div>
                  {t.progresso >= 100 ? (
                    <span className="tag tag-high">
                      <Icon name="check" size={11} style={{ verticalAlign: "-1px" }} /> Indexada
                    </span>
                  ) : t.progresso === 0 ? (
                    <span className="tag tag-muted">Não indexada</span>
                  ) : (
                    <span className="tag tag-mid">Parcial</span>
                  )}
                </div>
                <div className="tema-name">{t.nome}</div>
                <div className="tema-desc">{t.descricao}</div>
                <div className="tema-meta">
                  <span><b>{t.docs}</b> doc(s)</span>
                </div>
                <div className="tema-prog">
                  <div className="bar">
                    <span style={{ width: t.progresso + "%", background: t.cor }} />
                  </div>
                  <span className="pct" style={{ color: t.cor }}>{t.progresso}%</span>
                </div>
                <button
                  className="btn btn-ghost"
                  style={{ marginTop: 12, fontSize: 13, padding: "7px 12px" }}
                  onClick={(e) => { e.stopPropagation(); openMateria(t); }}
                >
                  <Icon name="chat" size={14} /> Perguntar sobre esta matéria
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------- DOCUMENTOS ---------------- */
function DocumentosView({ temas, onIndexed }) {
  const [dados, setDados] = React.useState(null);
  const [q, setQ] = React.useState("");
  const [filtro, setFiltro] = React.useState("todos");
  const [indexando, setIndexando] = React.useState(false);
  const [enviando, setEnviando] = React.useState(false);
  const [resultado, setResultado] = React.useState(null);
  const [uploadMateria, setUploadMateria] = React.useState("");
  const [menuAberto, setMenuAberto] = React.useState(null);   // rel_path do menu aberto
  const [movendo, setMovendo] = React.useState(null);         // {relPath, novaMat}
  const [processando, setProcessando] = React.useState(null); // rel_path em operação
  const [resetZona, setResetZona] = React.useState(false);    // mostra painel de perigo
  const [resetDigitado, setResetDigitado] = React.useState(""); // texto de confirmação
  const [resetando, setResetando] = React.useState(false);    // aguardando resposta da API
  const fileRef = React.useRef(null);

  const temasList = (dados && dados.temas) || temas || [];
  const byId = (id) =>
    temasList.find((t) => t.id === id) || { nome: id || "Geral", cor: "#888", id };
  const tipoCor = { md: "var(--brand-600)", pdf: "var(--accent)", txt: "var(--ink-2)" };

  function fetchDocs() {
    fetch("/api/documentos")
      .then((r) => r.json())
      .then(setDados)
      .catch(() => setDados({ arquivos: [], total: 0, indexados: 0, chunks: 0, temas: [] }));
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
      onIndexed && onIndexed();
    } catch {
      setResultado({ ok: false, erro: "Erro ao conectar ao servidor." });
    } finally {
      setIndexando(false);
    }
  }

  async function enviarArquivo(e) {
    // Aceita VARIOS arquivos (BUG-009): envia um a um e agrega o resultado
    const files = Array.from(e.target.files || []);
    e.target.value = ""; // permite reenviar o mesmo arquivo
    if (files.length === 0) return;

    setEnviando(true);
    setResultado(null);
    const porArquivo = [];
    for (const file of files) {
      try {
        const form = new FormData();
        form.append("file", file);
        form.append("materia", uploadMateria);
        const res = await fetch("/api/upload", { method: "POST", body: form });
        const data = await res.json();
        porArquivo.push({
          arquivo: file.name,
          ok: !!data.ok,
          chunks: data.chunks || 0,
          erro: data.erro || null,
        });
      } catch {
        porArquivo.push({ arquivo: file.name, ok: false, erro: "Falha de conexão com o servidor." });
      }
    }
    setResultado({ ok: porArquivo.every((r) => r.ok), multi: porArquivo });
    fetchDocs();
    onIndexed && onIndexed();
    setEnviando(false);
  }

  async function moverArquivo() {
    if (!movendo || !movendo.novaMat.trim()) return;
    setProcessando(movendo.relPath);
    setMovendo(null);
    try {
      const form = new FormData();
      form.append("rel_path", movendo.relPath);
      form.append("nova_materia", movendo.novaMat.trim());
      const res = await fetch("/api/documentos/mover", { method: "POST", body: form });
      const data = await res.json();
      setResultado(data.ok
        ? { ok: true, arquivo_salvo: movendo.relPath.split("/").pop(), chunks: data.chunks || 0 }
        : { ok: false, erro: data.erro || "Erro ao mover arquivo." }
      );
      fetchDocs();
      onIndexed && onIndexed();
    } catch {
      setResultado({ ok: false, erro: "Falha de conexão com o servidor." });
    } finally {
      setProcessando(null);
    }
  }

  async function resetarSistema() {
    setResetando(true);
    try {
      const res = await fetch("/api/reset", { method: "POST" });
      const data = await res.json();
      if (data.ok) {
        window.location.reload();
      } else {
        setResultado({ ok: false, erro: (data.erros || []).join(" | ") || "Erro ao resetar o sistema." });
        setResetZona(false);
        setResetDigitado("");
      }
    } catch {
      setResultado({ ok: false, erro: "Falha de conexão ao tentar resetar o sistema." });
      setResetZona(false);
      setResetDigitado("");
    } finally {
      setResetando(false);
    }
  }

  async function excluirArquivo(relPath, nome) {
    if (!window.confirm(`Excluir "${nome}" da base de conhecimento?\n\nO arquivo será removido do disco e todos os seus chunks apagados do ChromaDB.`)) return;
    setProcessando(relPath);
    try {
      const res = await fetch(`/api/documentos?rel_path=${encodeURIComponent(relPath)}`, { method: "DELETE" });
      const data = await res.json();
      setResultado(data.ok
        ? { ok: true, chunks: 0, arquivo_salvo: nome, _excluido: true }
        : { ok: false, erro: data.erro || "Erro ao excluir arquivo." }
      );
      fetchDocs();
      onIndexed && onIndexed();
    } catch {
      setResultado({ ok: false, erro: "Falha de conexão com o servidor." });
    } finally {
      setProcessando(null);
    }
  }

  const d0 = dados || { arquivos: [], total: 0, indexados: 0, chunks: 0 };
  let rows = d0.arquivos || [];
  if (filtro === "indexados") rows = rows.filter((d) => d.indexado === true);
  if (filtro === "pendentes") rows = rows.filter((d) => !d.indexado);
  if (q.trim()) rows = rows.filter((d) => d.nome.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="page rise">
      <div className="h-eyebrow">Base de conhecimento</div>
      <h1 className="h1">Documentos de treino</h1>
      <p className="sub">
        Tudo o que o assistente pode consultar, organizado por matéria
        (subpastas de <code>docs/</code>). Cada arquivo é dividido em{" "}
        <b>trechos (chunks)</b> e convertido em vetores no ChromaDB.
        O processamento é <b>incremental</b>: só arquivos novos ou alterados
        são reprocessados.
      </p>

      {/* Stats rápidas */}
      <div className="perf-grid" style={{ marginTop: 22, gridTemplateColumns: "repeat(4,1fr)" }}>
        <StatCard icon="docs" label="Documentos" value={d0.total} />
        <StatCard icon="check" label="Indexados" value={d0.indexados} tint="var(--high)" />
        <StatCard icon="layers" label="Trechos vetorizados" value={d0.chunks} tint="var(--brand-600)" />
        <StatCard icon="clock" label="Pendentes" value={d0.total - d0.indexados} tint="var(--mid)" />
      </div>

      {/* Feedback de indexação / upload */}
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
            {resultado.multi ? (
              /* Resultado de upload multiplo: status por arquivo (BUG-009) */
              <>
                <b>
                  Upload concluído — {resultado.multi.filter((r) => r.ok).length}/
                  {resultado.multi.length} arquivo(s) processado(s).
                </b>
                {resultado.multi.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 13,
                      marginTop: 3,
                      color: r.ok ? "var(--ink-2)" : "var(--low)",
                    }}
                  >
                    {r.ok ? "✓" : "✗"} <b>{r.arquivo}</b>
                    {r.ok
                      ? r.chunks > 0
                        ? ` — ${r.chunks} chunks indexados`
                        : " — já estava indexado"
                      : ` — ${r.erro}`}
                  </div>
                ))}
              </>
            ) : resultado.ok ? (
              <>
                <b>
                  {resultado._excluido
                    ? `Arquivo "${resultado.arquivo_salvo}" excluído da base.`
                    : resultado.arquivo_salvo
                    ? `Arquivo "${resultado.arquivo_salvo}" enviado!`
                    : "Indexação concluída!"}
                </b>{" "}
                {resultado._excluido ? null : resultado.chunks > 0
                  ? `${resultado.chunks} chunks de ${resultado.arquivos} arquivo(s) processados.`
                  : "Nenhum arquivo novo para processar."}
                {resultado.pulados > 0 && (
                  <span className="muted"> {resultado.pulados} arquivo(s) já indexado(s) — pulados.</span>
                )}
                {resultado.falhas > 0 && (
                  <div style={{ color: "var(--low)", marginTop: 4 }}>
                    {resultado.falhas} arquivo(s) com erro:
                    {(resultado.arquivos_com_erro || []).map((e, i) => (
                      <div key={i} style={{ fontSize: 13, marginTop: 2 }}>
                        • <b>{typeof e === "string" ? e : e.arquivo}</b>
                        {typeof e !== "string" && e.erro ? ` — ${e.erro}` : ""}
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <>
                <b>Erro.</b> {resultado.erro || "Verifique o servidor."}
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
          <input placeholder="Buscar arquivo…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="seg">
          {[["todos", "Todos"], ["indexados", "Indexados"], ["pendentes", "Pendentes"]].map(([k, l]) => (
            <button key={k} className={filtro === k ? "on" : ""} onClick={() => setFiltro(k)}>
              {l}
            </button>
          ))}
        </div>

        {/* Upload: matéria de destino + arquivo (BUG-010 + FEAT-002) */}
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {/* input+datalist: permite selecionar matéria existente OU digitar nova */}
          <input
            list="upload-materias-list"
            value={uploadMateria}
            onChange={(e) => setUploadMateria(e.target.value)}
            placeholder="Matéria (vazio = Geral)"
            title="Selecione uma matéria existente ou digite o nome de uma nova"
            style={{
              padding: "9px 11px",
              borderRadius: 11,
              border: "1px solid var(--line-2)",
              background: "var(--surface)",
              fontSize: 13,
              color: "var(--ink-2)",
              fontFamily: "inherit",
              width: 190,
            }}
          />
          <datalist id="upload-materias-list">
            {temasList.map((t) => (
              <option key={t.id} value={t.id}>{t.nome}</option>
            ))}
          </datalist>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.md,.txt"
            multiple
            style={{ display: "none" }}
            onChange={enviarArquivo}
          />
          <button
            className="btn btn-ghost"
            onClick={() => fileRef.current && fileRef.current.click()}
            disabled={enviando}
          >
            <Icon name="plus" size={16} /> {enviando ? "Enviando…" : "Enviar documento"}
          </button>
          <button
            className="btn btn-accent"
            style={{ padding: "9px 16px", fontSize: 14 }}
            onClick={indexar}
            disabled={indexando}
          >
            <Icon name={indexando ? "refresh" : "layers"} size={16} />
            {indexando ? "Processando…" : "Processar Documentos"}
          </button>
        </div>
      </div>

      {/* datalist compartilhado para mover */}
      <datalist id="mover-materias-list">
        {temasList.map((t) => (
          <option key={t.id} value={t.id}>{t.nome}</option>
        ))}
      </datalist>

      {/* Tabela */}
      <div className="card" style={{ overflow: "visible" }}>
        <div className="doc-row head">
          <span>Arquivo</span>
          <span>Matéria</span>
          <span>Trechos</span>
          <span>Status</span>
          <span />
        </div>
        {dados === null ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--ink-3)" }}>
            Carregando documentos…
          </div>
        ) : (
          <>
            {rows.map((d) => {
              const t = byId(d.tema);
              const esteEmMovimento = movendo && movendo.relPath === d.rel_path;
              const esteProcessando = processando === d.rel_path;
              return (
                <React.Fragment key={d.id}>
                  <div className="doc-row" style={{ opacity: esteProcessando ? 0.5 : 1, position: "relative" }}>
                    <div className="doc-file">
                      <div className="doc-fic" style={{ background: tipoCor[d.tipo] || "var(--ink-3)" }}>
                        {(d.tipo || "").toUpperCase()}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div className="doc-fname">{d.nome}</div>
                        <div className="doc-fmeta">{d.tamanho} · adicionado em {d.data}</div>
                      </div>
                    </div>
                    <div>
                      <span className="chip" style={{ borderColor: t.cor + "44", color: t.cor, background: t.cor + "12" }}>
                        {t.nome}
                      </span>
                    </div>
                    <div style={{ fontWeight: 700, fontVariantNumeric: "tabular-nums", color: d.chunks ? "var(--ink)" : "var(--ink-3)" }}>
                      {d.chunks || "—"}{" "}
                      <span className="muted" style={{ fontWeight: 500, fontSize: 12 }}>chunks</span>
                    </div>
                    <div>
                      {d.indexado === true ? (
                        <span className="tag tag-high"><Icon name="check" size={11} style={{ verticalAlign: "-1px" }} /> Indexado</span>
                      ) : (
                        <span className="tag tag-muted"><Icon name="clock" size={11} style={{ verticalAlign: "-1px" }} /> Não indexado</span>
                      )}
                    </div>
                    {/* Botão ··· com menu de ações (FEAT-007 + FEAT-008) */}
                    <div style={{ position: "relative" }}>
                      <button
                        className="icon-btn"
                        style={{ width: 32, height: 32 }}
                        disabled={esteProcessando}
                        onClick={() => {
                          setMenuAberto(menuAberto === d.rel_path ? null : d.rel_path);
                          setMovendo(null);
                        }}
                      >
                        <Icon name="dot3" size={16} />
                      </button>
                      {menuAberto === d.rel_path && (
                        <>
                          {/* overlay transparente para fechar ao clicar fora */}
                          <div
                            style={{ position: "fixed", inset: 0, zIndex: 9 }}
                            onClick={() => setMenuAberto(null)}
                          />
                          <div style={{
                            position: "absolute", right: 0, top: 36, zIndex: 10,
                            background: "var(--surface)", border: "1px solid var(--line-2)",
                            borderRadius: 10, boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
                            minWidth: 180, padding: "6px 0", fontSize: 13,
                          }}>
                            <button
                              style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "9px 14px", background: "none", border: 0, cursor: "pointer", color: "var(--ink-2)", textAlign: "left" }}
                              onClick={() => { setMovendo({ relPath: d.rel_path, novaMat: d.tema }); setMenuAberto(null); }}
                            >
                              <Icon name="arrowR" size={14} /> Mover para matéria
                            </button>
                            <div style={{ height: 1, background: "var(--line-2)", margin: "4px 0" }} />
                            <button
                              style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "9px 14px", background: "none", border: 0, cursor: "pointer", color: "var(--low)", textAlign: "left" }}
                              onClick={() => { setMenuAberto(null); excluirArquivo(d.rel_path, d.nome); }}
                            >
                              <Icon name="alert" size={14} /> Excluir arquivo
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                  {/* Formulário inline de mover (FEAT-007) */}
                  {esteEmMovimento && (
                    <div style={{ padding: "10px 18px 14px", background: "var(--bg)", borderTop: "1px solid var(--line-2)", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 13, color: "var(--ink-3)" }}>Mover <b>{d.nome}</b> para:</span>
                      <input
                        list="mover-materias-list"
                        autoFocus
                        value={movendo.novaMat}
                        onChange={(e) => setMovendo({ ...movendo, novaMat: e.target.value })}
                        placeholder="Nome da matéria"
                        style={{ padding: "7px 11px", borderRadius: 9, border: "1px solid var(--line-2)", background: "var(--surface)", fontSize: 13, fontFamily: "inherit", flex: 1, minWidth: 160, maxWidth: 240 }}
                        onKeyDown={(e) => { if (e.key === "Enter") moverArquivo(); if (e.key === "Escape") setMovendo(null); }}
                      />
                      <button className="btn btn-accent" style={{ padding: "8px 14px", fontSize: 13 }} onClick={moverArquivo}>Confirmar</button>
                      <button className="btn btn-ghost" style={{ padding: "8px 12px", fontSize: 13 }} onClick={() => setMovendo(null)}>Cancelar</button>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
            {rows.length === 0 && (
              <div style={{ padding: 40, textAlign: "center", color: "var(--ink-3)" }}>
                {d0.total === 0
                  ? "Nenhum arquivo encontrado na pasta docs/."
                  : "Nenhum arquivo corresponde ao filtro."}
              </div>
            )}
          </>
        )}
      </div>

      {/* Zona de perigo — Reset do sistema */}
      <div style={{ marginTop: 40, borderTop: "2px solid #FECDD3", paddingTop: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Icon name="alert" size={15} style={{ color: "#DC2626" }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: "#DC2626", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Zona de perigo
          </span>
        </div>

        {!resetZona ? (
          <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
            <p style={{ margin: 0, fontSize: 13, color: "var(--ink-3)", flex: 1 }}>
              Apaga permanentemente todos os documentos, histórico de conversas e métricas de desempenho.{" "}
              <strong style={{ color: "var(--ink-2)" }}>Esta ação não pode ser desfeita.</strong>
            </p>
            <button
              style={{
                padding: "9px 18px", fontSize: 13, borderRadius: 10, cursor: "pointer",
                color: "#DC2626", border: "1px solid #DC2626", background: "transparent",
                fontWeight: 600, fontFamily: "inherit", flexShrink: 0,
              }}
              onClick={() => setResetZona(true)}
            >
              Resetar sistema
            </button>
          </div>
        ) : (
          <div style={{ background: "#FFF1F2", border: "1px solid #FECDD3", borderRadius: 12, padding: "20px 22px" }}>
            <p style={{ margin: "0 0 10px", fontSize: 14, fontWeight: 700, color: "#991B1B" }}>
              O que será apagado permanentemente:
            </p>
            <ul style={{ margin: "0 0 16px 18px", fontSize: 13, color: "#7F1D1D", lineHeight: 1.8 }}>
              <li>Todos os arquivos dentro de <code style={{ background: "#FEE2E2", padding: "1px 5px", borderRadius: 4 }}>docs/</code> — removidos do disco</li>
              <li>Todos os vetores da coleção <code style={{ background: "#FEE2E2", padding: "1px 5px", borderRadius: 4 }}>ChromaDB</code></li>
              <li>Histórico de conversas — <code style={{ background: "#FEE2E2", padding: "1px 5px", borderRadius: 4 }}>data/historico.json</code></li>
              <li>Métricas de desempenho — <code style={{ background: "#FEE2E2", padding: "1px 5px", borderRadius: 4 }}>data/stats.json</code></li>
              <li>Manifesto de indexação — <code style={{ background: "#FEE2E2", padding: "1px 5px", borderRadius: 4 }}>data/index_manifest.json</code></li>
            </ul>
            <p style={{ margin: "0 0 10px", fontSize: 13, color: "#991B1B" }}>
              Para confirmar, digite <strong>RESETAR</strong> no campo abaixo:
            </p>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <input
                autoFocus
                value={resetDigitado}
                onChange={(e) => setResetDigitado(e.target.value)}
                placeholder="Digite RESETAR"
                style={{
                  padding: "9px 12px", borderRadius: 9, border: "1px solid #FECDD3",
                  fontSize: 13, fontFamily: "inherit", background: "#fff", width: 180,
                }}
                onKeyDown={(e) => {
                  if (e.key === "Escape") { setResetZona(false); setResetDigitado(""); }
                }}
              />
              <button
                style={{
                  padding: "9px 18px", fontSize: 13, borderRadius: 10, fontWeight: 600,
                  fontFamily: "inherit", border: "none",
                  cursor: resetDigitado === "RESETAR" && !resetando ? "pointer" : "not-allowed",
                  background: resetDigitado === "RESETAR" ? "#DC2626" : "#E5E7EB",
                  color: resetDigitado === "RESETAR" ? "#fff" : "#9CA3AF",
                  transition: "background .2s, color .2s",
                }}
                disabled={resetDigitado !== "RESETAR" || resetando}
                onClick={resetarSistema}
              >
                {resetando ? "Apagando…" : "Apagar tudo"}
              </button>
              <button
                className="btn btn-ghost"
                style={{ padding: "9px 14px", fontSize: 13 }}
                onClick={() => { setResetZona(false); setResetDigitado(""); }}
                disabled={resetando}
              >
                Cancelar
              </button>
            </div>
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
      <div className="page rise">
        <Loading label="Carregando métricas…" />
      </div>
    );
  }

  const m = stats;
  const maxSerie = Math.max(...(m.serie || [0.001]), 0.001);
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
        <StatCard icon="chat" label="Perguntas feitas" value={m.perguntas} delta={m.perguntasDelta} />
        <StatCard icon="check" label="Respondidas" value={m.respondidas} tint="var(--high)" />
        <StatCard icon="shield" label="Recusadas (fora do escopo)" value={m.recusadas} tint="var(--low)" />
        <StatCard icon="clock" label="Tempo médio" value={m.tempoMedio} tint="var(--brand-600)" />
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
                        height: (v / maxSerie) * 100 + "%",
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
                      <div style={{ fontWeight: 600, fontSize: 13.5 }}>{d.faixa}</div>
                      <div style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{d.sub}</div>
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
function HistoricoView({ goto, newChat, temas, openConversation }) {
  const [conversas, setConversas] = React.useState(null);

  const temasList = temas || [];
  const byId = (id) =>
    temasList.find((t) => t.id === id) || { nome: id || "Geral", cor: "#888", id };

  React.useEffect(() => {
    fetch("/api/historico")
      .then((r) => r.json())
      .then((d) => setConversas(d.conversas || []))
      .catch(() => setConversas([]));
  }, []);

  return (
    <div className="page rise">
      <div className="h-eyebrow">Suas conversas</div>
      <h1 className="h1">Histórico</h1>
      <p className="sub">
        Retome qualquer conversa anterior. Cada uma guarda todas as perguntas,
        respostas e fontes citadas.
      </p>

      {conversas === null ? (
        <div style={{ marginTop: 22 }}>
          <Loading label="Carregando histórico…" />
        </div>
      ) : conversas.length === 0 ? (
        <div
          className="card"
          style={{ marginTop: 22, padding: 48, textAlign: "center", color: "var(--ink-3)" }}
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
            onClick={() => newChat()}
          >
            <Icon name="chat" size={16} /> Iniciar uma conversa
          </button>
        </div>
      ) : (
        <div className="card" style={{ marginTop: 22, padding: "4px 18px" }}>
          {conversas.map((c) => {
            const t = byId(c.materia || c.tema);
            return (
              <div
                className="list-row"
                key={c.id}
                style={{ cursor: "pointer" }}
                onClick={() => openConversation(c.id)}
              >
                <div className="list-ic" style={{ background: t.cor + "1A", color: t.cor }}>
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
                  <div style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 1 }}>
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
                <Icon name="chevR" size={18} style={{ color: "var(--ink-3)" }} />
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
  Loading,
});
