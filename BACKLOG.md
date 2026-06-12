# BACKLOG — Bugs e Melhorias

Registro vivo de problemas e melhorias do projeto. **Consulte este arquivo antes de
iniciar qualquer trabalho** e registre aqui novos problemas antes de corrigi-los.

Formato: cada item tem ID (`BUG-NNN` / `FEAT-NNN`), status (`aberto` | `em andamento` | `resolvido`),
prioridade (`alta` | `media` | `baixa`), sintoma/causa raiz e correcao proposta.

---

## Bugs

### BUG-001 — Loading state ausente no carregamento inicial   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Sintoma:** ao abrir a interface, "Continue estudando" mostra "Nenhum documento indexado ainda"
  por ~2s e depois as aulas aparecem.
- **Causa raiz:** o embedder (SentenceTransformer) carrega lazy na 1ª chamada de `/api/documentos`,
  e o frontend trata `temas=[]` (ainda carregando) igual a "vazio de verdade".
- **Correcao:** warmup do embedder em thread no startup do FastAPI; estado `temas` inicia `null`
  (= carregando) e as views mostram "Carregando documentos…" ate o fetch responder.
- **Arquivos:** `api.py`, `frontend/app.jsx`, `frontend/views.jsx`

### BUG-002 — Clicar em conversa nao reabre a conversa   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Sintoma:** clicar numa conversa recente (home) ou no historico abre um chat limpo.
- **Causa raiz:** `HomeView`/`HistoricoView` chamam `goto("chat")` sem passar o id da conversa;
  o endpoint `GET /api/historico/{id}` existe mas nunca e usado pelo frontend.
- **Correcao:** estado `resumeId` no app; `ChatView` carrega as mensagens da conversa e reutiliza
  o mesmo `session_id` (o backend ja faz append por id).
- **Arquivos:** `frontend/app.jsx`, `frontend/chat.jsx`

### BUG-003 — Resposta desconfigurada com fonte inline   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Sintoma:** a resposta vem com "(Fonte: aula-06.md)" no meio do texto, sem formatacao;
  fontes devem aparecer apenas na secao "Fontes consultadas", retratil e discreta.
- **Causa raiz:** regra 3 do prompt em `src/chain.py` manda o LLM citar fonte inline;
  `chat.jsx` renderiza texto cru sem markdown.
- **Correcao:** remover regra 3 do prompt; regex de limpeza `\(Fonte:[^)]*\)` no `api.py`;
  renderizador markdown leve no `chat.jsx`; secao de fontes retratil (fechada por padrao).
  Revalidar com `eval.py --full` apos mudar o prompt.
- **Arquivos:** `src/chain.py`, `api.py`, `frontend/chat.jsx`

### BUG-004 — Scroll do chat empurra a pagina inteira   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Sintoma:** com varias mensagens, a interface toda desce (sidebar some) e o corpo do chat
  fica travado na ultima mensagem, sem rolagem propria.
- **Causa raiz:** `.chat-wrap{height:100%}` nao restringe altura num flex item
  (precisa `flex:1; min-height:0`); `scrollIntoView()` rola ancestrais ate o `<body>`.
- **Correcao:** CSS `flex:1; min-height:0` no `.chat-wrap`; rolar o container interno via
  `scrollTop = scrollHeight` em vez de `scrollIntoView`.
- **Arquivos:** `frontend/components.css`, `frontend/chat.jsx`

### BUG-005 — Clique no tema dispara pergunta automatica   [status: resolvido em 12/06/2026 | prioridade: media]
- **Sintoma:** clicar num card de tema envia "Me de um resumo de <tema>" automaticamente.
- **Causa raiz:** `TemasView` chama `ask("Me de um resumo de " + t.nome)`.
- **Correcao:** clique abre chat limpo **com escopo da materia** (depende de FEAT-003).
- **Arquivos:** `frontend/views.jsx`, `frontend/app.jsx`

---

## Melhorias

### FEAT-001 — Materias por subpasta (varios arquivos por materia)   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Hoje:** cada arquivo vira um "tema" (`f.stem`); tudo misturado.
- **Proposta:** convencao `docs/<materia>/arquivo.md`; arquivos na raiz de `docs/` → materia "geral".
  Campo `materia` em cada chunk (loader) e nos metadatas do ChromaDB (embedder);
  `/api/documentos` agrupa por subpasta. **Requer reindexacao** (conteudo nao muda,
  limiar 0.68 permanece valido).
- **Arquivos:** `src/loader.py`, `src/embedder.py`, `api.py`

### FEAT-002 — Upload de documentos pela interface   [status: resolvido em 12/06/2026 | prioridade: media]
- **Proposta:** `POST /api/upload` (multipart + campo materia); valida extensao;
  salva em `docs/<materia>/`; dispara indexacao incremental. Botao "Enviar documento"
  da `DocumentosView` ligado a input de arquivo + seletor de materia.
- **Arquivos:** `api.py`, `frontend/views.jsx`

### FEAT-003 — Chat com escopo por materia   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Proposta:** chat aberto por um tema busca apenas nas fontes daquela materia
  (`where={"materia": ...}` no ChromaDB); aba Assistente (geral) busca em tudo.
  Chip "Escopo: <materia>" visivel no composer.
- **Arquivos:** `src/embedder.py`, `src/chain.py`, `api.py`, `frontend/chat.jsx`

### FEAT-004 — Indexacao incremental   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Hoje:** "Processar documentos" re-embeda todos os chunks a cada clique.
- **Proposta:** manifest `data/index_manifest.json` com hash md5 por arquivo;
  pula arquivos inalterados; `?force=true` reprocessa tudo; resposta informa `pulados: N`.
- **Arquivos:** `api.py`

### FEAT-005 — Sugestoes dinamicas baseadas nos ultimos documentos   [status: resolvido em 12/06/2026 | prioridade: baixa]
- **Hoje:** sugestoes hard-coded no `api.py`.
- **Proposta:** gerar 3 sugestoes a partir dos titulos (`# ...`) dos 3 documentos mais
  recentes (mtime); fallback para lista fixa.
- **Arquivos:** `api.py`

---

## Resolvidos

(mover itens para ca quando concluidos, com data e commit)
