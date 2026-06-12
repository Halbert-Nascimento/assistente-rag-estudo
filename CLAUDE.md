# Roadmap do Projeto: Assistente RAG (IA Generativa)

> **Antes de iniciar qualquer trabalho:** consulte o `BACKLOG.md` (bugs e melhorias
> pendentes, com causa raiz e correcao proposta) e a fase atual neste arquivo.
> Ao encontrar novos problemas ou ideias de melhoria, **registre-os no `BACKLOG.md`
> antes de corrigir** — ele e o registro vivo do andamento do projeto.
    
## Fase 1: Setup Isolado (✅ Concluído)
- [x] Criação da estrutura de pastas (`src`, `eval`, `docs`).
- [x] Cópia dos documentos base da disciplina (aulas) para a pasta `docs/`.
- [x] Configuração do `.gitignore` (incluindo exclusão da pasta `docs/` e `venv/`).
- [x] Geração dos aquivos `.env` e `requirements.txt`.
- [x] Inicialização do repositório Git.

## Fase 2: Ambiente e Dependências (✅ Concluído)
- [x] Criar ambiente virtual Python (`venv`) para validações locais.
- [x] Ativar o ambiente virtual e instalar dependências atráves do `requirements.txt` (`langchain`, `chromadb`, `sentence-transformers`, `streamlit`, `pypdf`, `python-dotenv`).
- [x] **Configuração Docker (Isolamento Total):** Criar `Dockerfile` e `docker-compose.yml` para executar o modelo (Ollama com `llama3.1`) e a aplicação Streamlit em containers isolados, garantindo reprodutibilidade e ambiente limpo.

## Fase 3: Pipeline RAG (Backend) (✅ Concluído)
- [x] `src/loader.py`: Script para leitura profunda dos PDFs/MDs alocados em `docs/` e aplicação do chunking dos textos. Chunking por caracteres com sobreposição correta (CHUNK_SIZE=512, OVERLAP=50). IDs anti-colisão via hash MD5 do caminho.
- [x] `src/embedder.py`: Embeddings PT-BR (`paraphrase-multilingual-MiniLM-L12-v2`) + ChromaDB com cosine similarity. Busca retorna similaridade 0-100% correta. Nunca lança exceção.
- [x] `src/chain.py`: RAGChain via LangChain + Ollama (llama3.1). Prompt blindado contra alucinações. Método `check_health()` para diagnóstico. Método `ask()` sempre retorna dict (nunca lança). `requirements.txt` atualizado com `langchain-core` e `langchain-ollama`.

### Arquitetura de Ingestão de Documentos
**Objetivo:** Forma simples, automática e resiliente para o usuário adicionar seus documentos.

**Diretório de Ingestão:** `docs/` (raiz)
- Suporta: `.pdf`, `.md`, `.txt`
- **Recursivo:** Varre subpastas automaticamente
- **Sem limite:** Processa quantos arquivos o usuário adicionar

**Fluxo Automático:**
1. **Detecção:** Loader varre `docs/` a cada execução
2. **Validação:** Verifica integridade e formato do arquivo
3. **Processamento:** Carrega conteúdo e aplica chunking (tamanho: 512 caracteres, sobreposição: 50)
4. **Erro Isolado:** Falha de UM arquivo não interrompe os outros (logging claro)
5. **Metadata:** Cada chunk rastreia `arquivo`, `caminho`, `timestamp`

**Tratamento de Erros:**
- Arquivos corrompidos → Registram erro + continuam
- Encoding invalido → Auto-detecta UTF-8 com fallback
- PDFs sem texto (imagens) → Skipa com aviso
- Disco cheio/permissões → Exceção clara com instrução

**Garantias:**
- ✅ Idempotente: Pode rodar múltiplas vezes sem duplicação (upsert por chunk_id)
- ✅ Observável: Logs estruturados (arquivo, chunks gerados, erros)
- ✅ Testado: `tests/run_tests.py` valida todos os caminhos de erro (18 testes)

## Fase 4: Interface Visual (Frontend) (✅ Concluído)
- [x] `app.py`: UI de Chat via Streamlit com 3 painéis: status do sistema (ChromaDB + Ollama), indexação de documentos com feedback de erros, e chat com histórico de conversa e fontes consultadas. `@st.cache_resource` para embedder e chain (não recarrega a cada interação). Lê `OLLAMA_BASE_URL`, `OLLAMA_MODEL` e `DOCS_DIR` do `.env`.

## Fase 5: Testes e Avaliação em Massa (✅ Concluído)
- [x] `eval/perguntas_teste.json`: 10 perguntas (3 fácil, 3 médio, 2 difícil, 2 fora do escopo) com gabarito, palavras-chave e fonte esperada por pergunta.
- [x] `eval/eval.py`: Avalia recuperação de contexto (sem LLM) e pipeline completo (`--full`). Mede latência, cobertura de keywords, fonte correta e recusa (comparação sem acentos). Salva `eval/resultados.json`. Resultado real: **100% de acerto na recuperação de fonte (8/8)**, latência ~20 ms (pós warm-up).
- [x] `README.md`: Documentação completa com arquitetura, instruções de execução (Docker e local), benchmark com dados reais coletados e justificativa das decisões técnicas.

## Fase 6: Auditoria e Hardening (✅ Concluído em 12/06/2026)
Validação completa do sistema com correções aplicadas:
- [x] **Bug crítico no chunking corrigido:** o loop gerava ~50 fragmentos-lixo por arquivo ("2026", "026", "26"...) — 200 dos 251 chunks eram lixo. Banco reconstruído.
- [x] **Chunking por seções de Markdown:** cada seção (`#`) vira um chunk concentrado. Recuperação subiu de 87.5% para 100% (corrigiu a pergunta do Epsilon Decay).
- [x] **Recusa determinística:** limiar de similaridade 0.68 (medido: in-scope 0.718–0.870, fora 0.569–0.641). Perguntas fora do escopo são recusadas sem chamar o LLM.
- [x] **Busca dupla eliminada no chain.py:** `ask()` fazia retrieval 2x por pergunta (uma para fontes, outra dentro da LCEL chain). Agora 1 busca alimenta ambos.
- [x] **eval.py:** verificação de recusa robusta a acentos (LLM responde "Não encontrei informação..." com acentos).
- [x] **docker-compose:** variável `MODEL_NAME` corrigida para `OLLAMA_MODEL` (nome que o app.py lê); volume restrito a `docs/` e `chroma_db/`.
- [x] **`.gitignore`:** removida linha `claude.md` que (case-insensitive no Windows) impedia o versionamento deste roadmap.
- [x] **`.dockerignore` e `.env.example`** criados.
- [x] **`tests/run_tests.py`:** 18 testes de robustez cobrindo todos os caminhos de erro — 18/18 passando.

## Fase 7: Calibracao da Geracao com LLM (✅ Concluído em 12/06/2026)
Primeira rodada do `eval.py --full` (com Ollama + GPU) revelou 6/8 e 3 bugs no relatorio. Correcoes:
- [x] **Chunks contextualizados:** titulo do documento prefixado em cada chunk de `.md`. A pergunta dos "4 pilares do RL" nao recuperava o chunk certo (nem no top-10) porque o texto diz "quatro pilares" sem citar "Reinforcement Learning". Com o prefixo, o chunk foi ao 1º lugar (0.813).
- [x] **Secoes so-de-titulo fundidas** (`MIN_CHUNK=120` no loader): chunks "# Aula 7 | Video: ..." pontuavam alto sem carregar informacao, roubando vagas do top-4.
- [x] **eval.py — 3 bugs do relatorio:** (1) contador "Passou" incluia as recusas fora do escopo (mostrava 8/8 quando era 6/8); (2) variavel `passou` sobrescrita no loop da tabela imprimia "SCORE FINAL: SIM/8"; (3) latencia sem arredondar (2435.6000000000004). Modo recuperacao-apenas agora mostra "Fonte correta" em vez de metricas que exigem LLM.
- [x] **Keywords da pergunta 2 realinhadas** ao vocabulario do documento ("esmag", "grandezas") — a resposta correta do LLM era reprovada por usar as palavras do proprio doc.
- [x] **Limiar 0.68 revalidado** apos recontextualizacao: in-scope 0.727–0.875, fora 0.539–0.630.
- [x] **Resultado final (`eval.py --full`): 8/8 in-scope + 2/2 recusas (100%).** Latencia media 2.6 s, recusa em ~30 ms. Banco com 62 chunks. Testes: 20/20 (2 novos de regressao).
- [x] **docker-compose com GPU NVIDIA** (`deploy.resources`) e volume `ollama` compativel com o container standalone do usuario. README com 3 opcoes de execucao e instrucoes de uso da interface.

## Fase 8: Migracao para Interface React (🔄 Planejada — branch `nova-interface`)

Substituicao da interface Streamlit (`app.py`) pela interface React prototipatada em `interface/`.
Executar na branch `nova-interface` (nunca no main ate estar completa).

### Etapa 0 — Documentar plano no CLAUDE.md (este item) ✅
### Etapa 1 — Criar branch git
```
git checkout -b nova-interface
```

### Etapa 2 — Reorganizar arquivos de interface
- Renomear `interface/` → `frontend/`
- Remover `frontend/data.js` (dados mock, substituido por API real)
- Adicionar `data/` ao `.gitignore` (pasta de persistencia em runtime)

### Etapa 3 — Criar `api.py` (FastAPI — substitui Streamlit como servidor)
Endpoints a implementar (backend usa `src/loader.py`, `src/embedder.py`, `src/chain.py` sem modificacao):
- `GET  /`                  → serve `frontend/index.html`
- `GET  /frontend/{file}`   → arquivos estaticos CSS/JS
- `GET  /api/status`        → `{ chromadb, ollama, docs_indexados, modelo, pronto }`
- `POST /api/indexar`       → `{ ok, chunks, arquivos, falhas, arquivos_com_erro }`
- `POST /api/chat`          → `{ resposta, fontes:[{doc,sim}], sim, recusou }`
- `GET  /api/documentos`    → `{ total, indexados, chunks, arquivos:[{nome,tipo,status,chunks}] }`
- `GET  /api/stats`         → `{ total_perguntas, confianca_media, historico_7dias, distribuicao }`
- `GET  /api/historico`     → lista de conversas salvas
- `GET  /api/historico/{id}`→ mensagens de uma conversa
Persistencia simples: `data/stats.json` e `data/historico.json` (atualizados a cada `/api/chat`).

### Etapa 4 — Criar `frontend/chat.jsx` (componente faltante)
ChatView com: input + lista de mensagens + SourceCard por resposta + ConfidenceMeter.
Integra via `fetch('/api/chat', {method:'POST', body: JSON.stringify({pergunta})})`.
Recebe props `seed` (pergunta inicial da HomeView) e `onNewChat`.

### Etapa 5 — Atualizar `frontend/views.jsx`
Substituir `DATA.*` por `fetch('/api/...')` com `useEffect` em cada view:
- `HomeView`       → `GET /api/stats` + `GET /api/historico`
- `DocumentosView` → `GET /api/documentos` + botao `POST /api/indexar` com feedback por arquivo
- `DesempenhoView` → `GET /api/stats`
- `HistoricoView`  → `GET /api/historico`
- `TemasView`      → derivar temas de `/api/documentos` (agrupar por prefixo do nome do arquivo)

### Etapa 6 — Atualizar `frontend/app.jsx`
- Adicionar `useEffect` para `GET /api/status` ao montar (atualiza badge do topbar)
- Importar `ChatView` de `chat.jsx` (ja referenciado, faltava o arquivo)
- Remover import de `data.js`

### Etapa 7 — Atualizar `frontend/index.html`
- Remover `<script src="data.js">`
- Adicionar `<script src="chat.jsx" type="text/babel">`
- Manter CDN React + Babel (sem bundler)

### Etapa 8 — Atualizar infra
- `requirements.txt`: adicionar `fastapi` e `uvicorn[standard]`
- `Dockerfile`: trocar `streamlit run app.py --server.port=8501` por `uvicorn api:app --host 0.0.0.0 --port 8000`
- `docker-compose.yml`: porta `8000:8000`, container renomeado `rag-app`

### Verificacao final
```bash
uvicorn api:app --reload --port 8000     # dev local
python tests/run_tests.py                # backend Python intacto (20/20)
# Acessar http://localhost:8000 e testar: status, indexar, chat, historico
docker-compose up -d --build             # teste em container
```

### Features adicionadas vs Streamlit atual
| Feature nova | Origem |
|---|---|
| Historico persistente entre sessoes | `data/historico.json` |
| Graficos de desempenho por dia | `data/stats.json` |
| Visualizacao por temas/aulas | derivado dos nomes dos arquivos |
| Dashboard home com sugestoes | HomeView + dados de stats |

### Features do Streamlit garantidas na nova interface
| Feature | Como preservada |
|---|---|
| Erros por arquivo na indexacao | coluna de status em DocumentosView |
| Status ChromaDB + Ollama em tempo real | badge no topbar via `/api/status` |
| Recusa deterministica (sem LLM) | logica permanece em `src/chain.py` |
| Limpar conversa | botao "Nova conversa" em `app.jsx` |

## Fase 9: Correcoes e Melhorias da Interface React (✅ Concluído em 12/06/2026 — branch `nova-interface`)

O uso real da interface (Fase 8) revelou 5 bugs e 5 melhorias, todos documentados e
**resolvidos** em **`BACKLOG.md`** (BUG-001 a BUG-005, FEAT-001 a FEAT-005). Resumo:
- [x] **BUG-001 Loading state:** warmup do embedder em thread no startup; `temas=null`
  = carregando (views mostram "Carregando documentos…" em vez de "Nenhum documento").
- [x] **BUG-002 Retomar conversa:** clicar numa conversa (home/historico) reabre as
  mensagens via `GET /api/historico/{id}` e continua no mesmo `session_id`.
- [x] **BUG-003 Formatacao:** prompt nao pede mais citacao inline (regra 3 trocada);
  regex de limpeza no api.py; markdown leve no chat; fontes em secao retratil fechada.
  Revalidado: `eval.py --full` = **8/8 + 2/2** apos a mudanca do prompt.
- [x] **BUG-004 Scroll:** `.chat-wrap{flex:1;min-height:0}` + rolagem do container
  interno (`scrollTop`) em vez de `scrollIntoView` — sidebar nao some mais.
- [x] **BUG-005 + FEAT-003 Escopo por materia:** clique no tema abre chat limpo com
  filtro `where={"materia": ...}` no ChromaDB (so fontes daquela materia); aba
  Assistente busca em tudo. Chip "Escopo: <materia>" no composer.
- [x] **FEAT-001 Materias por subpasta:** `docs/<materia>/arquivo.md`; raiz → "geral".
  Campo `materia` no loader e nos metadatas; `/api/documentos` agrupa por subpasta.
  Banco reindexado (62 chunks, limiar 0.68 inalterado).
- [x] **FEAT-004 Indexacao incremental:** manifest `data/index_manifest.json` (md5 por
  arquivo); segunda indexacao pula tudo (`pulados: 4`, instantanea); `?force=true` disponivel.
- [x] **FEAT-002 Upload:** `POST /api/upload` (multipart, valida extensao, salva em
  `docs/<materia>/`, indexa incrementalmente). Botao + seletor de materia na DocumentosView.
  Requer `python-multipart` (adicionado ao requirements).
- [x] **FEAT-005 Sugestoes dinamicas:** 3 sugestoes geradas dos titulos dos documentos
  mais recentes.
- [x] Testes 20/20 | eval 8/8 + 2/2 | upload e2e testado e limpo.
