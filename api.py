# -*- coding: utf-8 -*-
"""
Backend FastAPI — Assistente RAG
Substitui o Streamlit como servidor HTTP.
Serve a interface React em /frontend/ e expoe a API RAG em /api/.

Convencao de materias: subpastas de docs/ sao materias
(docs/<materia>/arquivo.md). Arquivos na raiz de docs/ → materia 'geral'.
"""
import hashlib
import json
import mimetypes
import os
import re
import threading
import time
import unicodedata
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()
mimetypes.add_type("text/javascript", ".jsx")

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

STATS_FILE = DATA_DIR / "stats.json"
HISTORICO_FILE = DATA_DIR / "historico.json"
MANIFEST_FILE = DATA_DIR / "index_manifest.json"

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}

app = FastAPI(title="Assistente RAG — API")


# ---------------------------------------------------------------------------
# Lazy singletons + warmup no startup
# ---------------------------------------------------------------------------
_embedder = None
_chain = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from src.embedder import DocumentEmbedder
        _embedder = DocumentEmbedder()
    return _embedder


def get_chain():
    global _chain
    if _chain is None:
        from src.chain import RAGChain
        _chain = RAGChain(
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            embedder=get_embedder(),
        )
    return _chain


@app.on_event("startup")
def warmup():
    # Carrega os modelos pesados em background para que a primeira chamada de
    # API nao trave: embeddings (BUG-001) e o cross-encoder de reranking
    # (FEAT-009), que so carregaria na 1a pergunta do chat.
    def _aquecer():
        get_embedder()
        try:
            from src.reranker import get_reranker
            get_reranker().rerank("aquecimento", [{"content": "texto de aquecimento"}])
        except Exception:
            pass  # se o reranker falhar, a chain cai no fallback de cosseno

    threading.Thread(target=_aquecer, daemon=True).start()


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------
def _load(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def _save(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_CORES = ["#4F46E5", "#D5603A", "#059669", "#D97706", "#7C3AED", "#0891B2"]


def _cor(idx: int) -> str:
    return _CORES[idx % len(_CORES)]


def _docs_dir() -> Path:
    return ROOT / os.getenv("DOCS_DIR", "docs")


def _materia_de(rel_path: Path) -> str:
    """Materia = primeira subpasta de docs/; arquivos na raiz → 'geral'."""
    return rel_path.parts[0] if len(rel_path.parts) > 1 else "geral"


def _materia_nome(materia_id: str) -> str:
    return materia_id.replace("-", " ").replace("_", " ").title()


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _limpa_citacao_inline(answer: str) -> str:
    """Remove citacoes '(Fonte: ...)' que o LLM ainda inclua no texto.

    As fontes sao exibidas estruturadas pela interface (BUG-003)."""
    answer = re.sub(r"\s*\(Fontes?:[^)]*\)", "", answer)
    return answer.strip()


def _titulo_doc(path: Path) -> str:
    """Extrai o titulo ('# ...') de um .md; fallback para o nome do arquivo."""
    try:
        if path.suffix.lower() == ".md":
            for ln in path.read_text(encoding="utf-8", errors="ignore").split("\n"):
                if ln.strip().startswith("# "):
                    return ln.strip().lstrip("#").strip()
    except Exception:
        pass
    return path.stem.replace("-", " ").replace("_", " ").title()


def _sem_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    ).lower()


# Cabecalhos genericos/administrativos que NAO sao conceitos de estudo (FEAT-005).
_SECOES_GENERICAS = (
    "visao geral", "fluxo", "sintese", "destaque", "alerta", "desafio", "atividade",
    "quiz", "entrega", "validac", "mercado de trabalho", "vagas", "pratica tecnica",
    "interface", "transic", "entendimento do cenario", "casos de mercado", "evoluc",
    "referencia", "sumario", "introducao", "conclusao",
)


def _conceitos_de_doc(path: Path, limite: int = 6) -> list:
    """Extrai conceitos de estudo dos cabecalhos de secao (##/###) de um .md/.txt.

    O conteudo (e nao o titulo do arquivo) e a melhor fonte de perguntas
    especificas e respondiveis pelo RAG. Perguntas sobre o documento inteiro
    ("pontos principais de X") nao funcionam bem porque o RAG recupera
    fragmentos, nao resume o documento todo (FEAT-005 melhorado)."""
    if path.suffix.lower() not in (".md", ".txt"):
        return []
    conceitos = []
    try:
        for ln in path.read_text(encoding="utf-8", errors="ignore").split("\n"):
            s = ln.strip()
            if not s.startswith("##"):     # so secoes (##/###); pula titulo (#) do doc
                continue
            t = s.lstrip("#").strip()
            # remove rotulo em CAIXA ALTA com emoji (ex: "⚠️ ATENCAO:", "💡 INSIGHT:")
            t = re.sub(r"^[^\wÀ-ÿ]*[A-ZÀ-Ý]{3,}\s*:\s*", "", t)
            # remove numeracao de secao ("1. ", "2. ") e enfase markdown (*...*)
            t = re.sub(r"^\d+\.\s*", "", t).replace("*", "").strip()
            # remove emojis/simbolos residuais no inicio
            t = re.sub(r"^[^\wÀ-ÿ(]+", "", t).strip()
            low = _sem_acentos(t)
            if len(t) < 5 or len(t) > 70:
                continue
            if any(g in low for g in _SECOES_GENERICAS):
                continue
            if t not in conceitos:
                conceitos.append(t)
            if len(conceitos) >= limite:
                break
    except Exception:
        pass
    return conceitos


def _run_indexing(force: bool = False) -> dict:
    """Indexacao incremental: pula arquivos cujo hash nao mudou (FEAT-004)."""
    from src.loader import load_documents

    docs_dir = _docs_dir()
    chunks, summary = load_documents(str(docs_dir))

    manifest = _load(MANIFEST_FILE, {})
    por_arquivo: dict = defaultdict(list)
    for c in chunks:
        por_arquivo[c["source_path"]].append(c)

    novos = []
    pulados = 0
    for source_path, cs in por_arquivo.items():
        try:
            h = _file_hash(docs_dir / source_path)
        except OSError:
            h = None
        if not force and h is not None and manifest.get(source_path) == h:
            pulados += 1
            continue
        novos.extend(cs)
        if h is not None:
            manifest[source_path] = h

    if novos:
        result = get_embedder().embed_and_store(novos)
    else:
        result = {"stored": 0, "failed": 0, "total": 0}

    _save(MANIFEST_FILE, manifest)

    return {
        "ok": True,
        "chunks": result["stored"],
        "arquivos": summary["total_sucesso"] - pulados,
        "pulados": pulados,
        "falhas": summary["total_falhas"],
        # Inclui o MOTIVO de cada falha (BUG-008) — a UI exibe arquivo + erro
        "arquivos_com_erro": [
            {"arquivo": f["arquivo"], "erro": f["erro"]}
            for f in summary.get("arquivos_falhados", [])
        ],
    }


# ---------------------------------------------------------------------------
# Endpoints de API
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def status():
    chromadb_ok = False
    docs_indexados = 0
    ollama_ok = False
    try:
        e = get_embedder()
        s = e.get_stats()
        chromadb_ok = True
        docs_indexados = s.get("total_documentos", 0)
    except Exception:
        pass
    try:
        get_chain().llm.invoke("ping")
        ollama_ok = True
    except Exception:
        pass
    return {
        "chromadb": chromadb_ok,
        "ollama": ollama_ok,
        "docs_indexados": docs_indexados,
        "modelo": os.getenv("OLLAMA_MODEL", "llama3.1"),
        "pronto": chromadb_ok and ollama_ok and docs_indexados > 0,
    }


@app.post("/api/indexar")
async def indexar(force: bool = False):
    return _run_indexing(force=force)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), materia: str = Form("")):
    """Recebe um documento, salva em docs/<materia>/ e indexa (FEAT-002)."""
    nome = Path(file.filename or "").name  # remove qualquer caminho embutido
    if not nome:
        return JSONResponse({"ok": False, "erro": "Arquivo sem nome."}, status_code=400)

    ext = Path(nome).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return JSONResponse(
            {"ok": False, "erro": f"Formato '{ext}' nao suportado. Use .pdf, .md ou .txt."},
            status_code=400,
        )

    # Sanitiza a materia (vira nome de pasta)
    materia = re.sub(r"[^a-zA-Z0-9_\- ]", "", materia.strip()).replace(" ", "-").lower()

    destino_dir = _docs_dir() / materia if materia and materia != "geral" else _docs_dir()
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / nome

    conteudo = await file.read()
    destino.write_bytes(conteudo)

    # Indexa apenas o que mudou (o arquivo novo)
    resultado = _run_indexing()

    # Se o arquivo ENVIADO falhou ao processar, remove-o de docs/ e
    # devolve o motivo — senao ele geraria o mesmo erro em toda
    # indexacao futura (BUG-008)
    falha = next(
        (f for f in resultado.get("arquivos_com_erro", []) if f["arquivo"] == nome),
        None,
    )
    if falha:
        try:
            destino.unlink()
        except OSError:
            pass
        return JSONResponse(
            {"ok": False, "erro": f"'{nome}' nao pode ser processado: {falha['erro']}"},
            status_code=422,
        )

    resultado["arquivo_salvo"] = str(destino.relative_to(_docs_dir()))
    return resultado


@app.post("/api/documentos/mover")
async def mover_documento(rel_path: str = Form(...), nova_materia: str = Form(...)):
    """Move um arquivo para outra materia, atualizando ChromaDB e manifest (FEAT-007)."""
    docs_dir = _docs_dir()
    origem = docs_dir / rel_path

    if not origem.exists():
        return JSONResponse({"ok": False, "erro": "Arquivo não encontrado."}, status_code=404)

    nova_materia = re.sub(r"[^a-zA-Z0-9_\- ]", "", nova_materia.strip()).replace(" ", "-").lower()
    destino_dir = docs_dir / nova_materia if nova_materia and nova_materia != "geral" else docs_dir
    destino = destino_dir / origem.name

    if destino.resolve() == origem.resolve():
        return {"ok": True, "chunks": 0, "msg": "Arquivo já está nesta matéria."}

    # Remove chunks antigos do ChromaDB (source_path = caminho relativo atual).
    # Se falhar, aborta ANTES de mover/reindexar: senao o arquivo seria
    # reindexado no novo caminho e os chunks antigos ficariam como duplicata
    # (fantasma na materia anterior).
    try:
        get_embedder().collection.delete(where={"source_path": rel_path})
    except Exception as e:
        return JSONResponse(
            {"ok": False, "erro": f"Falha ao remover vetores antigos do ChromaDB: {e}"},
            status_code=500,
        )

    # Remove entrada antiga do manifest
    manifest = _load(MANIFEST_FILE, {})
    manifest.pop(rel_path, None)
    _save(MANIFEST_FILE, manifest)

    # Move o arquivo
    destino_dir.mkdir(parents=True, exist_ok=True)
    origem.rename(destino)

    # Remove a subpasta de origem se ficou vazia (exceto a raiz de docs/)
    pasta_origem = origem.parent
    if pasta_origem != docs_dir and pasta_origem.exists() and not any(pasta_origem.iterdir()):
        pasta_origem.rmdir()

    # Reindexar (só o arquivo movido vai aparecer como novo no manifest)
    resultado = _run_indexing()
    return {"ok": True, "chunks": resultado.get("chunks", 0)}


@app.delete("/api/documentos")
async def excluir_documento(rel_path: str):
    """Remove um arquivo de docs/, apaga seus chunks do ChromaDB e atualiza o manifest (FEAT-008)."""
    docs_dir = _docs_dir()
    arquivo = docs_dir / rel_path

    if not arquivo.exists():
        return JSONResponse({"ok": False, "erro": "Arquivo não encontrado."}, status_code=404)

    # Remove chunks do ChromaDB ANTES de apagar o arquivo. Se falhar, aborta:
    # apagar o arquivo deixaria os vetores orfaos (fantasma na busca).
    try:
        get_embedder().collection.delete(where={"source_path": rel_path})
    except Exception as e:
        return JSONResponse(
            {"ok": False, "erro": f"Falha ao remover vetores do ChromaDB: {e}"},
            status_code=500,
        )

    # Remove do manifest
    manifest = _load(MANIFEST_FILE, {})
    manifest.pop(rel_path, None)
    _save(MANIFEST_FILE, manifest)

    # Apaga o arquivo
    try:
        arquivo.unlink()
        pasta = arquivo.parent
        if pasta != docs_dir and pasta.exists() and not any(pasta.iterdir()):
            pasta.rmdir()
    except OSError as e:
        return JSONResponse({"ok": False, "erro": str(e)}, status_code=500)

    return {"ok": True}


class ChatRequest(BaseModel):
    pergunta: str
    session_id: Optional[str] = None
    materia: Optional[str] = None


@app.post("/api/chat")
async def chat(req: ChatRequest):
    pergunta = req.pergunta.strip()
    session_id = req.session_id or str(uuid.uuid4())
    materia = (req.materia or "").strip() or None

    if not pergunta:
        return JSONResponse({"erro": "pergunta vazia"}, status_code=400)

    t0 = time.perf_counter()

    # Pipeline RAG completo (recall + rerank, com escopo de materia se informado).
    # A propria chain faz a busca uma unica vez e devolve a similaridade por fonte
    # — nao ha mais busca top-1 separada (que aplicava o mesmo % a todas as fontes).
    result = get_chain().ask(pergunta, materia=materia)
    latencia_ms = round((time.perf_counter() - t0) * 1000)

    recusou = result["context_chunks"] == 0
    answer = _limpa_citacao_inline(result["answer"]) if not recusou else result["answer"]

    # Similaridade REAL por arquivo (maior cosseno dos chunks daquela fonte)
    fontes = [
        {"doc": d["doc"], "sim": round(d["sim"], 3)}
        for d in result.get("sources_detail", [])
    ]
    # Confianca exibida no cabecalho/medidor = melhor cosseno entre os candidatos
    top_sim = round(result.get("top_similarity", 0.0), 3)
    # Relevancia do reranker (sinal que DECIDE a recusa). None no fallback de cosseno.
    # A UI usa isso para explicar a recusa sem a contradicao "71% < 68%" (cosseno alto
    # mas relevancia baixa e exatamente o caso de casamento espurio).
    rel = result.get("top_relevance")
    relevancia = round(rel, 3) if rel is not None else None

    # Persistir stats
    stats_data = _load(STATS_FILE, {"perguntas": []})
    stats_data["perguntas"].append({
        "id": str(uuid.uuid4()),
        "pergunta": pergunta,
        "recusou": recusou,
        "sim": top_sim,
        "latencia_ms": latencia_ms,
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "materia": materia,
        "fontes": result.get("sources", []),
    })
    _save(STATS_FILE, stats_data)

    # Persistir historico (mensagens completas, incluindo fontes — BUG-002)
    hist_data = _load(HISTORICO_FILE, {"conversas": []})
    conv = next((c for c in hist_data["conversas"] if c["id"] == session_id), None)
    if conv is None:
        conv = {
            "id": session_id,
            "titulo": pergunta[:80],
            "quando": datetime.now().strftime("%d/%m/%Y"),
            "msgs": 0,
            "confianca": 0.0,
            "materia": materia or "geral",
            "mensagens": [],
        }
        hist_data["conversas"].insert(0, conv)

    conv["mensagens"].append({"role": "user", "content": pergunta})
    conv["mensagens"].append({
        "role": "assistant",
        "content": answer,
        "sim": top_sim,
        "relevancia": relevancia,
        "recusou": recusou,
        "fontes": fontes,
    })
    conv["msgs"] = len(conv["mensagens"])
    sims = [
        m["sim"] for m in conv["mensagens"]
        if m.get("role") == "assistant" and not m.get("recusou") and m.get("sim")
    ]
    conv["confianca"] = round(sum(sims) / len(sims), 3) if sims else 0.0
    _save(HISTORICO_FILE, hist_data)

    return {
        "resposta": answer,
        "fontes": fontes,
        "sim": top_sim,
        "relevancia": relevancia,
        "recusou": recusou,
        "latencia_ms": latencia_ms,
        "session_id": session_id,
    }


@app.get("/api/documentos")
async def documentos():
    docs_dir = _docs_dir()
    embedder = get_embedder()

    # Mapear chunks por source (uma unica query no ChromaDB)
    try:
        all_meta = embedder.collection.get(include=["metadatas"])
        chunks_por_source: dict = defaultdict(int)
        for meta in all_meta["metadatas"]:
            src = meta.get("source", "")
            if src:
                chunks_por_source[src] += 1
    except Exception:
        chunks_por_source = {}

    arquivos = []
    materias: dict = {}  # id → dados da materia

    if docs_dir.exists():
        for f in sorted(docs_dir.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            rel = f.relative_to(docs_dir)
            materia_id = _materia_de(rel)
            chunks_count = chunks_por_source.get(f.name, 0)
            indexado = chunks_count > 0

            if materia_id not in materias:
                materias[materia_id] = {
                    "id": materia_id,
                    "nome": _materia_nome(materia_id),
                    "descricao": "",
                    "cor": _cor(len(materias)),
                    "progresso": 0,
                    "aulas": 0,
                    "docs": 0,
                    "dominado": False,
                    "_indexados": 0,
                }
            m = materias[materia_id]
            m["docs"] += 1
            m["aulas"] += 1
            if indexado:
                m["_indexados"] += 1

            size = f.stat().st_size
            size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"

            arquivos.append({
                "id": str(abs(hash(str(f)))),
                "rel_path": str(rel),
                "nome": f.name,
                "tipo": f.suffix.lower().lstrip("."),
                "tamanho": size_str,
                "data": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y"),
                "tema": materia_id,
                "chunks": chunks_count,
                "indexado": indexado,
            })

    # Progresso da materia = % de arquivos dela ja indexados
    temas = []
    for m in materias.values():
        m["progresso"] = round(m["_indexados"] / m["docs"] * 100) if m["docs"] else 0
        m["descricao"] = f"{m['docs']} documento(s) nesta materia"
        m.pop("_indexados")
        temas.append(m)

    stats = embedder.get_stats()
    return {
        "total": len(arquivos),
        "indexados": sum(1 for a in arquivos if a["indexado"]),
        "chunks": stats.get("total_documentos", 0),
        "arquivos": arquivos,
        "temas": temas,
    }


@app.get("/api/stats")
async def api_stats():
    data = _load(STATS_FILE, {"perguntas": []})
    perguntas = data["perguntas"]

    total = len(perguntas)
    respondidas = sum(1 for p in perguntas if not p.get("recusou"))
    recusadas = total - respondidas

    sims = [p["sim"] for p in perguntas if not p.get("recusou") and p.get("sim")]
    confianca_media = round(sum(sims) / len(sims), 3) if sims else 0.0

    lats = [p["latencia_ms"] for p in perguntas if p.get("latencia_ms")]
    tempo_medio = f"{round(sum(lats)/len(lats)/1000, 1)}s" if lats else "—"

    hoje = datetime.now().date()
    dias = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
    por_dia: dict = defaultdict(list)
    for p in perguntas:
        try:
            d = datetime.fromisoformat(p["timestamp"]).date()
            por_dia[d].append(p)
        except Exception:
            pass

    serie = []
    serie_dias = []
    for dia in dias:
        ps = por_dia.get(dia, [])
        s = [p["sim"] for p in ps if not p.get("recusou") and p.get("sim")]
        serie.append(round(sum(s) / len(s), 2) if s else 0.0)
        serie_dias.append(dia.strftime("%a"))

    dist = [
        {"faixa": "Alta confianca", "sub": "sim >= 0.85", "v": sum(1 for p in perguntas if p.get("sim", 0) >= 0.85), "cor": "var(--high)"},
        {"faixa": "Confianca media", "sub": "0.68–0.85",  "v": sum(1 for p in perguntas if 0.68 <= p.get("sim", 0) < 0.85), "cor": "var(--mid)"},
        {"faixa": "Recusadas",       "sub": "sim < 0.68", "v": recusadas, "cor": "var(--low)"},
    ]

    # Sugestoes dinamicas baseadas em CONCEITOS extraidos do conteudo dos
    # documentos mais recentes (FEAT-005 melhorado). Antes era "Me explique os
    # pontos principais de <titulo>", que pede um resumo do documento inteiro —
    # o RAG recupera fragmentos, nao resume o todo, entao o LLM recusava.
    # Perguntas sobre conceitos especificos (secoes ##/###) sao respondiveis.
    docs_dir = _docs_dir()
    sugestoes = []
    if docs_dir.exists():
        recentes = sorted(
            (f for f in docs_dir.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        conceitos = []
        for f in recentes:
            for c in _conceitos_de_doc(f):
                if c not in conceitos:
                    conceitos.append(c)
        templates = ["O que e {}?", "Explique {}."]
        sugestoes = [templates[i % len(templates)].format(c) for i, c in enumerate(conceitos[:3])]
    # Completa (ou substitui, se nao houver conceitos) com sugestoes estaticas
    for estatica in (
        "O que e aprendizado supervisionado?",
        "Como funciona o K-Means?",
        "Quais sao os 4 pilares do Reinforcement Learning?",
    ):
        if len(sugestoes) >= 3:
            break
        if estatica not in sugestoes:
            sugestoes.append(estatica)
    sugestoes = sugestoes[:3]

    return {
        "perguntas": total,
        "perguntasDelta": 0,
        "respondidas": respondidas,
        "recusadas": recusadas,
        "confiancaMedia": confianca_media,
        "confiancaDelta": 0.0,
        "tempoMedio": tempo_medio,
        "cobertura": round(respondidas / total, 2) if total > 0 else 0.0,
        "serie": serie,
        "serieDias": serie_dias,
        "dist": dist,
        "porTema": [],
        "sugestoes": sugestoes,
    }


@app.get("/api/historico")
async def historico():
    data = _load(HISTORICO_FILE, {"conversas": []})
    # Retorna lista sem o campo 'mensagens' (payload menor)
    convs = [{k: v for k, v in c.items() if k != "mensagens"} for c in data["conversas"]]
    return {"conversas": convs}


@app.get("/api/historico/{session_id}")
async def historico_detalhe(session_id: str):
    data = _load(HISTORICO_FILE, {"conversas": []})
    conv = next((c for c in data["conversas"] if c["id"] == session_id), None)
    if conv is None:
        return JSONResponse({"erro": "Conversa nao encontrada"}, status_code=404)
    return conv


@app.post("/api/reset")
async def resetar_sistema():
    """Reset completo: apaga docs, historico, metricas e vetores do ChromaDB."""
    erros = []

    # 1. Limpa colecao do ChromaDB (apaga e recria vazia).
    # clear_collection() engole a excecao e retorna False; checamos o retorno
    # para nao reportar sucesso com o banco ainda populado (fantasma).
    try:
        if not get_embedder().clear_collection():
            erros.append("ChromaDB: clear_collection() falhou (banco pode nao ter sido limpo)")
    except Exception as e:
        erros.append(f"ChromaDB: {e}")

    # 2. Apaga todos os arquivos dentro de docs/ (mantém a pasta raiz)
    docs_dir = _docs_dir()
    try:
        # sorted + reverse garante que arquivos vêm antes das pastas no loop
        for item in sorted(docs_dir.rglob("*"), reverse=True):
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir() and item.resolve() != docs_dir.resolve():
                    item.rmdir()  # só apaga se já estiver vazia (arquivos removidos acima)
            except Exception as e:
                erros.append(f"{item.name}: {e}")
    except Exception as e:
        erros.append(f"docs/: {e}")

    # 3. Apaga arquivos de dados
    for f in [HISTORICO_FILE, STATS_FILE, MANIFEST_FILE]:
        try:
            if f.exists():
                f.unlink()
        except Exception as e:
            erros.append(f"{f.name}: {e}")

    if erros:
        return JSONResponse({"ok": False, "erros": erros}, status_code=500)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Servir frontend estatico
# ---------------------------------------------------------------------------
app.mount("/frontend", StaticFiles(directory=str(ROOT / "frontend")), name="frontend")


@app.get("/")
async def root():
    return FileResponse(str(ROOT / "frontend" / "index.html"))
