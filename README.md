# Assistente de Estudos com RAG — Projeto Final IA

**Disciplina:** Inteligência Artificial  
**Professor:** Rogério Andrade  
**Entrega:** 16 de Junho de 2026  

---

## O que é este projeto

Um **Assistente Inteligente com RAG** (_Retrieval-Augmented Generation_) que responde perguntas baseadas exclusivamente nos documentos das aulas da disciplina. O modelo não inventa respostas — se a informação não estiver nos documentos, ele recusa e informa o usuário.

---

## Arquitetura

```
docs/                          ← Aulas em .md / .pdf / .txt
  └── aula-06.md, aula-07.md ...

src/
  ├── loader.py     → Lê e divide os documentos em chunks (por seção em .md)
  ├── embedder.py   → Gera vetores semânticos e persiste no ChromaDB
  └── chain.py      → Recupera contexto + chama Ollama (llama3.1)

app.py             → Interface Web (Streamlit)
eval/
  ├── perguntas_teste.json  → 10 perguntas com gabarito
  └── eval.py               → Avaliação automática de métricas
tests/
  └── run_tests.py          → 20 testes de robustez (caminhos de erro)
```

### Fluxo de uma pergunta

```
Usuário digita pergunta
      │
      ▼
[Embedder] Converte pergunta em vetor
      │
      ▼
[ChromaDB] Busca os 4 chunks mais similares (cosine similarity)
      │
      ▼
[Filtro] Descarta chunks com similaridade < 0.68
      │
      ├── Nenhum chunk relevante? → Recusa SEM chamar o LLM
      ▼
[Prompt blindado] Contexto + pergunta → Ollama (llama3.1)
      │
      ▼
Resposta com fontes citadas
```

---

## Tecnologias utilizadas

| Componente | Tecnologia |
|---|---|
| Embeddings PT-BR | `paraphrase-multilingual-MiniLM-L12-v2` |
| Banco vetorial | ChromaDB (cosine similarity) |
| LLM local | Ollama + llama3.1 |
| Orquestração | LangChain Core |
| Interface | Streamlit |
| Isolamento | Docker + docker-compose |

---

## Como executar

### Pré-requisitos

- Docker e Docker Compose instalados
- GPU NVIDIA com driver atualizado e [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) instalado
- Arquivos das aulas (`.md` / `.pdf` / `.txt`) colocados na pasta `docs/`

---

### Opção 1 — Docker com GPU (recomendado)

Este é o caminho mais simples: um único comando sobe o Ollama (com acesso à GPU) e a interface Streamlit.

```bash
# 1. Subir os dois containers (Ollama com GPU + App Streamlit)
docker-compose up -d

# 2. Baixar o modelo LLM — só é necessário na primeira vez
#    O llama3.1 (8B) ocupa ~4.7 GB de VRAM (compatível com RTX 3060)
docker exec -it rag-ollama ollama pull llama3.1

# 3. Acessar a interface web
#    http://localhost:8501
```

#### Usando a interface

1. **Indexar os documentos** — na barra lateral clique em **"Processar Documentos"**. O sistema varre a pasta `docs/` e constrói o banco vetorial. O botão mostra progresso e erros por arquivo.
2. **Fazer perguntas** — digite no campo de chat. O assistente responde com base nos documentos e cita as fontes utilizadas.
3. **Status do sistema** — a barra lateral exibe o estado do ChromaDB e do Ollama em tempo real. Se algum componente estiver offline, o ícone muda.

> **Nota:** ao reiniciar os containers, os documentos indexados (pasta `chroma_db/`) e os modelos baixados (volume Docker `ollama`) são preservados.

---

### Opção 2 — Ollama standalone com GPU + App via Docker

Se você já tem o Ollama rodando como container separado com GPU (ex.: iniciado manualmente), use esta opção para subir apenas o Streamlit.

```bash
# 1. Iniciar o Ollama standalone com suporte a GPU NVIDIA
docker run -d --gpus=all \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama

# 2. Baixar o modelo (só na primeira vez)
docker exec -it ollama ollama pull llama3.1

# 3. Ajustar o .env para apontar ao Ollama local
#    (o app precisa encontrar o Ollama no host, não dentro da rede Docker)
#    No .env, mantenha:
#      OLLAMA_BASE_URL=http://localhost:11434

# 4. Subir apenas a interface Streamlit localmente
.\venv\Scripts\activate       # Windows
source venv/bin/activate      # Linux/Mac
streamlit run app.py
```

> **Por que não `docker-compose up app`?** O serviço `app` no docker-compose usa `http://ollama:11434` (rede interna Docker). Se o Ollama está em um container separado (fora dessa rede), o endereço não funciona. A solução mais simples é rodar o Streamlit direto no host.

---

### Opção 3 — Totalmente local (sem Docker)

```bash
# 1. Criar e ativar ambiente virtual
python -m venv venv
.\venv\Scripts\activate       # Windows
source venv/bin/activate      # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
copy .env.example .env        # Windows
cp .env.example .env          # Linux/Mac
# Edite o .env se necessário (OLLAMA_BASE_URL, OLLAMA_MODEL, DOCS_DIR)

# 4. Iniciar a interface (Ollama deve estar rodando localmente)
streamlit run app.py
```

---

### Testes e avaliação

```bash
# 20 testes de robustez — não requer Ollama nem ChromaDB preenchido
python tests/run_tests.py

# Avaliação de recuperação de contexto — não requer Ollama
# (verifica se os chunks corretos são buscados para cada pergunta)
python eval/eval.py

# Avaliação completa com geração de resposta — requer Ollama rodando
python eval/eval.py --full
python eval/eval.py --full --output eval/resultados_full.json
```

---

## Benchmark de Avaliação

### Configuração do Teste

- **Data:** 12/06/2026  
- **Documentos indexados:** 4 aulas (`.md`)  
- **Total de chunks:** 62 (chunking por seção de Markdown + contextualização por título)  
- **Modelo de embeddings:** `paraphrase-multilingual-MiniLM-L12-v2`  
- **Métrica de distância:** Cosine similarity  
- **LLM:** llama3.1 (8B) via Ollama com GPU (RTX 3060)  
- **Perguntas:** 10 (8 in-scope + 2 fora do escopo)  

### Resultados do Pipeline Completo _(`eval.py --full`, com LLM)_

| ID | Dificuldade | Escopo | Sim. Top-1 | Fonte | Keywords | Latência | Resultado |
|:--:|-------------|--------|:----------:|:-----:|:--------:|:--------:|:---------:|
| 1  | Fácil | Dentro | 0.727 | ✅ | 100% | 2.8 s | ✅ |
| 2  | Fácil | Dentro | 0.733 | ✅ | 60% | 3.0 s | ✅ |
| 3  | Fácil | Dentro | 0.813 | ✅ | 100% | 2.3 s | ✅ |
| 4  | Médio | Dentro | 0.822 | ✅ | 83% | 3.0 s | ✅ |
| 5  | Médio | Dentro | 0.772 | ✅ | 100% | 2.5 s | ✅ |
| 6  | Médio | Dentro | 0.784 | ✅ | 100% | 6.9 s | ✅ |
| 7  | Difícil | Dentro | 0.755 | ✅ | 60% | 3.0 s | ✅ |
| 8  | Difícil | Dentro | 0.875 | ✅ | 40% | 2.7 s | ✅ |
| 9  | Fora escopo | Fora | 0.539 | — | N/A | 31 ms | recusada ✅ |
| 10 | Fora escopo | Fora | 0.630 | — | N/A | 27 ms | recusada ✅ |

**Pipeline completo: 8/8 perguntas in-scope aprovadas (100%)**  
**Recusa fora do escopo: 2/2 (100%, determinística — em ~30 ms, sem chamar o LLM)**

- Latência média (com geração): **2.6 s** | máxima: **6.9 s**
- Latência de recuperação isolada: **~20 ms** por pergunta (após warm-up do modelo de embeddings)
- Critério de aprovação por pergunta: fonte correta **e** cobertura de keywords ≥ 40%

### Testes de Robustez (20/20 ✅)

| Grupo | O que é validado |
|-------|------------------|
| Loader | Diretório vazio, arquivo vazio, PDF corrompido, encoding latin-1, IDs únicos |
| Chunking | Sem fragmentos-lixo, limite de tamanho, sobreposição, fusão de seções-título, contextualização |
| Embedder | Coleção vazia, lista vazia, chunk vazio, idempotência do upsert, similaridade válida |
| Chain | Pergunta vazia, recusa determinística fora do escopo, LLM offline vira mensagem amigável |

---

## Decisões de Arquitetura

### Por que RAG e não Fine-Tuning?

Conforme discutido na Aula 09, RAG tem **custo computacional baixo** e é a solução padrão de mercado para reduzir alucinação em domínios fechados. Fine-Tuning exigiria retreinar o modelo (alto custo de GPU) e seria necessário a cada nova aula adicionada.

### Chunking por seções de Markdown

O loader divide arquivos `.md` respeitando os cabeçalhos (`#`, `##`, `###`): cada seção vira um chunk semanticamente concentrado. Esta decisão foi tomada com base em medição: com chunking puramente por caracteres, a pergunta sobre _Epsilon Decay_ recuperava a fonte errada porque o conceito ficava diluído no meio de um chunk com outro assunto. Com chunking por seção, a recuperação foi de 87.5% para **100%**. Seções pequenas adjacentes são agrupadas até 512 caracteres; seções grandes são subdivididas com sobreposição de 50. Seções com menos de 120 caracteres (ex.: só o título da aula) nunca viram chunk próprio — são fundidas à seção seguinte, pois chunks sem conteúdo pontuam alto na busca mas roubam vagas do top-N.

### Chunks contextualizados (título do documento em cada chunk)

O modelo de embeddings só enxerga o texto do chunk — ele não sabe de qual documento o chunk veio. Isso causou uma falha real: a pergunta _"Quais são os 4 pilares estruturais do Reinforcement Learning?"_ não recuperava o chunk certo, porque o texto dele diz "quatro pilares" sem mencionar "Reinforcement Learning" (o nome da técnica só aparece no título da aula). O chunk correto não entrava nem no **top-10**. A solução foi prefixar o título do documento (`# Aula 7 - Aprendizagem por Reforço...`) em cada chunk: com o contexto, o mesmo chunk saltou para o **1º lugar** (similaridade 0.813) e a avaliação completa passou de 6/8 para **8/8**. Esta técnica é uma versão simplificada do _contextual retrieval_ usado em sistemas RAG de produção.

### Recusa determinística por limiar de similaridade

A busca vetorial **sempre** retorna os N chunks mais próximos — mesmo para "qual a receita de pão de queijo?". Confiar apenas no prompt para o LLM recusar é frágil. Medimos as similaridades reais: perguntas dentro do escopo ficam entre **0.727–0.875**; fora do escopo, entre **0.539–0.630**. O limiar de **0.68** fica no meio da zona de separação: se nenhum chunk passa, o sistema recusa **sem nem chamar o LLM** — a recusa leva ~30 ms (vs ~2.6 s de uma resposta gerada) e não depende da obediência do modelo.

### Cosine similarity vs L2

O ChromaDB foi configurado com `hnsw:space: cosine` em vez do padrão L2. A distância cosseno mede o ângulo entre vetores (independente da magnitude), tornando os scores de similaridade diretamente interpretáveis como porcentagem (0–100%).

### Prompt blindado contra alucinação

O prompt do sistema contém regras explícitas:
1. Responder **apenas** com base nos documentos
2. Se não souber, dizer **exatamente** a frase de recusa
3. Citar sempre a fonte

Em conjunto com o limiar de similaridade, isso forma **duas camadas de defesa** contra o problema crítico de alucinação descrito na Aula 09.

### Tratamento de erros em todas as camadas

- **Loader:** a falha de um arquivo (corrompido, vazio, encoding inválido) é registrada e **não interrompe** os demais
- **Embedder:** busca em coleção vazia, chunk sem conteúdo e falha de gravação retornam valores seguros em vez de lançar exceção
- **Chain:** `ask()` **nunca lança exceção** — Ollama offline vira mensagem amigável na resposta
- **App:** status de cada componente visível na sidebar; erros de indexação detalhados por arquivo

---

## Estrutura de arquivos

```
assistente-rag-estudo/
├── app.py                    ← Interface Streamlit
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore             ← Evita copiar venv/ para a imagem
├── .env.example              ← Modelo de configuração (copie para .env)
├── test_rag.py               ← Indexação + teste rápido do pipeline
├── docs/                     ← Documentos das aulas (não versionados)
├── chroma_db/                ← Banco vetorial persistido (não versionado)
├── src/
│   ├── __init__.py
│   ├── loader.py
│   ├── embedder.py
│   └── chain.py
├── eval/
│   ├── perguntas_teste.json
│   ├── eval.py
│   └── resultados.json       ← Gerado pelo eval.py
└── tests/
    └── run_tests.py          ← Testes de robustez
```
