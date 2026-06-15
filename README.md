# Assistente de Estudos com RAG — Projeto Final IA

**Disciplina:** Inteligência Artificial  
**Professor:** Rogério Andrade  
**Entrega:** 16 de Junho de 2026  

---

## O que é este projeto

Um **Assistente Inteligente com RAG** (_Retrieval-Augmented Generation_) que responde perguntas baseadas exclusivamente nos documentos das aulas da disciplina. O modelo não inventa respostas — se a informação não estiver nos documentos, ele recusa e informa o usuário.

A interface web (React) organiza o material **por matéria**, mantém **histórico de conversas**, permite **upload de documentos** e mostra **métricas de desempenho** das respostas.

---

## Arquitetura

```
docs/                       ← Documentos organizados por matéria (subpastas)
  ├── machine-learning/        aula-06.md, aula-07.md
  ├── redes-neurais/           aula-08.md
  ├── ia-generativa/           aula-09.md
  └── <qualquer-materia>/      .md / .pdf / .txt

src/                        ← Pipeline RAG (backend puro, sem UI)
  ├── loader.py     → Lê e divide os documentos em chunks (por seção em .md)
  ├── embedder.py   → Gera vetores semânticos e persiste no ChromaDB
  └── chain.py      → Recupera contexto + chama Ollama (llama3.1)

api.py                      ← Servidor FastAPI: API REST + frontend estático
frontend/                   ← Interface React (servida pelo FastAPI em /)
  ├── index.html, app.jsx, chat.jsx, views.jsx, components.jsx
  └── styles.css, components.css

data/                       ← Persistência de runtime (gitignored)
  ├── historico.json           conversas completas (perguntas, respostas, fontes)
  ├── stats.json                métricas por pergunta (latência, similaridade)
  └── index_manifest.json       hash por arquivo (indexação incremental)

eval/                       ← Avaliação automática (10 perguntas com gabarito)
tests/                      ← 21 testes de robustez (caminhos de erro)
```

### Fluxo de uma pergunta

```
Usuário digita pergunta (escopo geral OU de uma matéria)
      │
      ▼
[Embedder] Converte pergunta em vetor
      │
      ▼
[Recall — ChromaDB] Busca os 20 candidatos mais similares (cosine)
      │       └── se o chat tem escopo: filtra where={"materia": ...}
      ▼
[Rerank — cross-encoder] Reordena por relevância real pergunta↔chunk
      │       e mantém só os top-4 acima da porta de relevância
      │
      ├── Nenhum chunk relevante? → Recusa SEM chamar o LLM (~30 ms)
      ▼
[Prompt blindado] Contexto (top-4 reordenados) + pergunta → Ollama (llama3.1)
      │
      ▼
Resposta + fontes consultadas (seção retrátil na interface)
```

---

## Tecnologias utilizadas

| Componente | Tecnologia |
|---|---|
| Embeddings PT-BR | `paraphrase-multilingual-MiniLM-L12-v2` |
| Reranking (relevância) | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilíngue) |
| Banco vetorial | ChromaDB (cosine similarity + filtro por metadado) |
| LLM local | Ollama + llama3.1 |
| Orquestração | LangChain Core |
| Backend / API | FastAPI + Uvicorn |
| Interface | React 18 (servida como estático, sem bundler) |
| Isolamento | Docker + docker-compose (GPU NVIDIA) |

---

## Como executar

### Pré-requisitos

- Docker e Docker Compose instalados
- GPU NVIDIA com driver atualizado e [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) instalado
- Documentos das aulas em `docs/` — **organize por matéria em subpastas** (`docs/<materia>/arquivo.md`); arquivos na raiz caem na matéria "Geral"

---

### Opção 1 — Docker com GPU (recomendado)

```bash
# 1. Subir os dois containers (Ollama com GPU + App FastAPI/React)
docker-compose up -d --build

# 2. Baixar o modelo LLM — só é necessário na primeira vez
#    O llama3.1 (8B) ocupa ~4.7 GB de VRAM (compatível com RTX 3060)
docker exec -it rag-ollama ollama pull llama3.1

# 3. Acessar a interface web
#    http://localhost:8000
```

> **Nota:** ao reiniciar os containers, os documentos indexados (`chroma_db/`), o histórico (`data/`) e os modelos baixados (volume Docker `ollama`) são preservados.

---

### Opção 2 — Ollama standalone com GPU + App local (desenvolvimento)

Se você já tem o Ollama rodando como container separado com GPU:

```bash
# 1. Iniciar o Ollama standalone com suporte a GPU NVIDIA (uma vez)
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama3.1

# 2. Ambiente Python local
python -m venv venv
.\venv\Scripts\activate          # Windows  (source venv/bin/activate no Linux/Mac)
pip install -r requirements.txt
copy .env.example .env           # OLLAMA_BASE_URL=http://localhost:11434

# 3. Subir o servidor (API + interface)
uvicorn api:app --reload --port 8000
#    http://localhost:8000
```

---

### Usando a interface

| Aba | O que faz |
|---|---|
| **Início** | Dashboard: métricas, sugestões de perguntas (baseadas nos últimos documentos), conversas recentes |
| **Assistente** | Chat geral — busca em **todos** os documentos |
| **Temas & Matérias** | Uma matéria por subpasta de `docs/`. Clicar abre um chat **com escopo**: só busca nos documentos daquela matéria |
| **Documentos** | Tabela de arquivos por matéria; **upload** (vários arquivos, com matéria de destino); botão **Processar Documentos** (incremental — só processa novos/alterados) |
| **Desempenho** | Confiança média por dia, distribuição alta/média/recusada |
| **Histórico** | Todas as conversas; clicar **reabre a conversa completa** (perguntas, respostas e fontes) |

Detalhes do chat:
- Fontes consultadas aparecem em **seção retrátil** abaixo de cada resposta, com a similaridade
- Perguntas fora do escopo são recusadas em ~30 ms com a similaridade exibida
- PDFs sem texto extraível (escaneados/imagem) são recusados com aviso — exigiriam OCR (backlog)

---

### Testes e avaliação

```bash
# 21 testes de robustez — não requer Ollama
python tests/run_tests.py

# Avaliação de recuperação de contexto — não requer Ollama
python eval/eval.py

# Avaliação completa com geração de resposta — requer Ollama rodando
python eval/eval.py --full
```

---

## Benchmark de Avaliação

### Configuração do Teste

- **Data:** 12/06/2026  
- **Modelo de embeddings:** `paraphrase-multilingual-MiniLM-L12-v2`  
- **Métrica de distância:** Cosine similarity  
- **LLM:** llama3.1 (8B) via Ollama com GPU (RTX 3060)  
- **Perguntas:** 10 (8 in-scope + 2 fora do escopo)  

### Resultados do Pipeline Completo _(`eval.py --full`, com LLM)_

| ID | Dificuldade | Escopo | Fonte | Keywords | Latência | Resultado |
|:--:|-------------|--------|:-----:|:--------:|:--------:|:---------:|
| 1  | Fácil | Dentro | ✅ | 100% | 2.5 s | ✅ |
| 2  | Fácil | Dentro | ✅ | 80% | 1.9 s | ✅ |
| 3  | Fácil | Dentro | ✅ | 100% | 2.0 s | ✅ |
| 4  | Médio | Dentro | ✅ | 83% | 3.2 s | ✅ |
| 5  | Médio | Dentro | ✅ | 100% | 2.2 s | ✅ |
| 6  | Médio | Dentro | ✅ | 100% | 6.2 s | ✅ |
| 7  | Difícil | Dentro | ✅ | 60% | 2.2 s | ✅ |
| 8  | Difícil | Dentro | ✅ | 60% | 3.5 s | ✅ |
| 9  | Fora escopo | Fora | — | N/A | 40 ms | recusada ✅ |
| 10 | Fora escopo | Fora | — | N/A | 40 ms | recusada ✅ |

**Pipeline completo: 8/8 perguntas in-scope aprovadas (100%)**  
**Recusa fora do escopo: 2/2 (100%, determinística — sem chamar o LLM)**

- Latência média (com geração): **2.4 s** | recuperação isolada: **~20 ms**
- Critério de aprovação: fonte correta **e** cobertura de keywords ≥ 40%

### Testes de Robustez (21/21 ✅)

| Grupo | O que é validado |
|-------|------------------|
| Loader | Diretório vazio, arquivo vazio, PDF corrompido, biblioteca pypdf disponível, encoding latin-1, IDs únicos |
| Chunking | Sem fragmentos-lixo, limite de tamanho, sobreposição, fusão de seções-título, contextualização |
| Embedder | Coleção vazia, lista vazia, chunk vazio, idempotência do upsert, similaridade válida |
| Chain | Pergunta vazia, recusa determinística fora do escopo, LLM offline vira mensagem amigável |

---

## Decisões de Arquitetura

### Por que RAG e não Fine-Tuning?

Conforme discutido na Aula 09, RAG tem **custo computacional baixo** e é a solução padrão de mercado para reduzir alucinação em domínios fechados. Fine-Tuning exigiria retreinar o modelo (alto custo de GPU) e seria necessário a cada nova aula adicionada.

### Chunking por seções de Markdown

O loader divide arquivos `.md` respeitando os cabeçalhos (`#`, `##`, `###`): cada seção vira um chunk semanticamente concentrado. Decisão tomada com base em medição: com chunking puramente por caracteres, a pergunta sobre _Epsilon Decay_ recuperava a fonte errada. Com chunking por seção, a recuperação foi de 87.5% para **100%**. Seções com menos de 120 caracteres (ex.: só o título da aula) nunca viram chunk próprio — são fundidas à seção seguinte.

### Chunks contextualizados (título do documento em cada chunk)

O modelo de embeddings só enxerga o texto do chunk. A pergunta _"Quais são os 4 pilares estruturais do Reinforcement Learning?"_ não recuperava o chunk certo, porque o texto dele diz "quatro pilares" sem mencionar "Reinforcement Learning" (nome que só aparece no título da aula). Prefixar o título do documento em cada chunk levou esse chunk do **fora do top-10** para o **1º lugar** — versão simplificada do _contextual retrieval_ usado em produção.

### Recuperação em dois estágios: recall + rerank

O app é distribuído e **cada usuário coloca os PDFs que quiser** — não dá para fixar um limiar de cosseno mágico, porque a similaridade do bi-encoder é grosseira e **dependente do corpus**. Um limiar fixo (a versão anterior usava `0.68`) deixava PDFs genéricos rasparem o corte e **diluírem o contexto**: a aula certa entrava junto com dois documentos irrelevantes e o LLM, preso ao prompt, recusava uma pergunta válida.

A solução é o padrão _retrieve & rerank_:

1. **Recall** — a busca vetorial traz os **20** candidatos mais próximos (rede ampla, sem limiar de cosseno).
2. **Rerank** — um **cross-encoder multilíngue** (`mmarco-mMiniLMv2-L12`) lê pergunta **e** chunk juntos e devolve um score de relevância **calibrado e estável entre corpora**. Mantemos só os **top-4** acima da porta de relevância (`RERANK_MIN_SCORE`, calibrado em **0.15**).
3. **Recusa determinística** — se nenhum candidato passa do score (ex.: "receita de pão de queijo" → ~0.02), recusa **sem chamar o LLM** (~30 ms). Casos-limite com casamento espúrio (ex.: "Copa 2022" casa com um chunk que cita o ano) passam ao LLM, que recusa via prompt blindado por não achar a resposta — o reranker garante que só os 4 chunks mais relevantes cheguem lá.

O `CrossEncoder` já vem em `sentence-transformers` (sem nova dependência pip); o modelo é baixado uma vez e cacheado no mesmo volume `hf_cache`. Se ele não carregar, há **fallback automático** para o limiar de cosseno. Calibração revalidável com `python eval/eval.py --full`.

### Matérias por subpasta + chat com escopo

Cada subpasta de `docs/` é uma matéria; cada chunk carrega o metadado `materia`. O chat aberto a partir de uma matéria filtra a busca no ChromaDB (`where={"materia": ...}`) — as fontes vêm **somente** daquela matéria, e perguntas de outros assuntos são recusadas. O chat geral busca em tudo.

### Indexação incremental

`data/index_manifest.json` guarda o hash MD5 de cada arquivo. "Processar Documentos" pula arquivos inalterados — com a base atual, a segunda execução é instantânea (`pulados: N`). Evita reprocessamento e lentidão quando a base cresce.

### Cosine similarity vs L2

O ChromaDB foi configurado com `hnsw:space: cosine`: a distância cosseno independe da magnitude dos vetores, tornando os scores diretamente interpretáveis como porcentagem (0–100%).

### Prompt blindado contra alucinação

O prompt exige: responder **apenas** com base nos documentos; recusar com frase exata quando não souber; não citar nomes de arquivo no texto (as fontes são exibidas estruturadas pela interface). Em conjunto com o reranker, são **duas camadas de defesa** contra alucinação: o reranker garante contexto relevante e sem diluição; o prompt blindado recusa quando mesmo o melhor contexto não contém a resposta.

### Tratamento de erros em todas as camadas

- **Loader:** a falha de um arquivo (corrompido, vazio, imagem-only) é registrada **com o motivo** e não interrompe os demais
- **Embedder:** busca em coleção vazia e falhas de gravação retornam valores seguros em vez de lançar exceção
- **Chain:** `ask()` **nunca lança exceção** — Ollama offline vira mensagem amigável
- **API/UI:** status de cada componente no topo da interface; upload que falha é removido e reporta o motivo

### Processo de desenvolvimento — BACKLOG.md

Todos os bugs e melhorias são registrados em **`BACKLOG.md`** (sintoma, causa raiz, correção, arquivos) **antes** de serem corrigidos — 9 bugs e 5 melhorias resolvidos até aqui, com 1 item aberto (OCR para PDFs de imagem). O roadmap por fases está em `CLAUDE.md`.
