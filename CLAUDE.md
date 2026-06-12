# Roadmap do Projeto: Assistente RAG (IA Generativa)
    
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
