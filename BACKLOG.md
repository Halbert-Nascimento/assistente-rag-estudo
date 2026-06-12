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

### BUG-006 — PDFs nunca sao indexados (pypdf vs PyPDF2)   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Sintoma:** todo upload/indexacao de PDF falha com "pypdf nao esta instalado",
  mesmo com o pacote instalado.
- **Causa raiz:** `src/loader.py` importa `PyPDF2`, mas o `requirements.txt` instala
  `pypdf` (nome novo do pacote, modulo `pypdf`). O import falha silenciosamente
  (`PyPDF2 = None`) e qualquer PDF e rejeitado. Latente desde a Fase 3 — nunca
  apareceu porque so havia arquivos `.md` na base.
- **Correcao:** importar `from pypdf import PdfReader` com fallback para `PyPDF2`;
  teste de regressao garantindo que a biblioteca de PDF esta disponivel.
- **Arquivos:** `src/loader.py`, `tests/run_tests.py`

### BUG-007 — Composer some quando o chat tem muitas mensagens   [status: resolvido em 12/06/2026 | prioridade: alta]
- **Sintoma:** com varias perguntas/respostas, a tela e empurrada para baixo e o campo
  de digitar some; nao da para rolar para cima para ver mensagens anteriores.
- **Causa raiz:** o grid `.app` define `grid-template-columns` mas nao define as linhas —
  a linha implicita tem altura `auto` e cresce com o conteudo alem dos 100vh
  (o `overflow: hidden` corta o excesso, escondendo o composer). O fix do BUG-004
  (`flex:1; min-height:0` no `.chat-wrap`) so funciona se toda a cadeia de altura
  estiver restrita — e a linha do grid nao estava.
- **Correcao:** `grid-template-rows: minmax(0, 1fr)` no `.app` + `min-height: 0` no
  `.main`. O chat rola internamente (para cima inclusive) e o composer fica fixo.
- **Arquivos:** `frontend/styles.css`

### BUG-008 — Erros de indexacao/upload sem o motivo   [status: resolvido em 12/06/2026 | prioridade: media]
- **Sintoma:** a mensagem mostra so o nome do arquivo com erro ("2 arquivo(s) com erro: X.pdf"),
  sem dizer por que falhou; um upload que falha deixa o arquivo quebrado em `docs/`
  gerando o mesmo erro em toda indexacao futura.
- **Correcao:** `arquivos_com_erro` passa a incluir o motivo (`{arquivo, erro}`);
  upload cujo arquivo falha ao processar retorna `ok: false` com o motivo e
  remove o arquivo salvo de `docs/`.
- **Arquivos:** `api.py`, `frontend/views.jsx`

### BUG-009 — Upload aceita apenas 1 arquivo por vez   [status: resolvido em 12/06/2026 | prioridade: media]
- **Sintoma:** usuario seleciona 2 documentos no dialogo, mas apenas 1 e enviado
  (o log do servidor mostra um unico POST /api/upload).
- **Causa raiz:** o `<input type="file">` da DocumentosView nao tem o atributo
  `multiple`; o dialogo do navegador so permite selecionar um arquivo.
- **Correcao:** atributo `multiple` no input; envio sequencial de cada arquivo;
  card de resultado lista cada arquivo com sucesso (chunks) ou erro (motivo).
- **Arquivos:** `frontend/views.jsx`

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

### FEAT-006 — OCR para PDFs de imagem   [status: aberto | prioridade: baixa]
- **Contexto:** PDFs sem texto extraivel (escaneados/imagem-only) sao corretamente
  recusados com aviso, ex: "Manual de Formatacao Markdown - v5.0.pdf". Para indexa-los
  seria preciso OCR (ex: pytesseract + pdf2image), que adiciona dependencias pesadas.
- **Arquivos:** `src/loader.py`, `requirements.txt`

---

## Resolvidos

(mover itens para ca quando concluidos, com data e commit)
