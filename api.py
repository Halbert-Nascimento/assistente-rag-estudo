# -*- coding: utf-8 -*-
"""
Backend FastAPI — Assistente RAG
Substitui o Streamlit como servidor HTTP.
Serve a interface React em /frontend/ e expoe a API RAG em /api/.
"""
import json
import mimetypes
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
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

app = FastAPI(title="Assistente RAG — API")


# ---------------------------------------------------------------------------
# Lazy singletons (nao bloqueiam o startup)
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
async def indexar():
    from src.loader import load_documents
    docs_dir = os.getenv("DOCS_DIR", "docs")
    chunks, summary = load_documents(docs_dir)
    result = get_embedder().embed_and_store(chunks)
    return {
        "ok": True,
        "chunks": result["stored"],
        "arquivos": summary["total_sucesso"],
        "falhas": summary["total_falhas"],
        "arquivos_com_erro": [f["arquivo"] for f in summary.get("arquivos_falhados", [])],
    }


class ChatRequest(BaseModel):
    pergunta: str
    session_id: Optional[str] = None


@app.post("/api/chat")
async def chat(req: ChatRequest):
    pergunta = req.pergunta.strip()
    session_id = req.session_id or str(uuid.uuid4())

    if not pergunta:
        return JSONResponse({"erro": "pergunta vazia"}, status_code=400)

    t0 = time.perf_counter()
    embedder = get_embedder()

    # Similaridade top-1 (busca rapida, sem LLM)
    docs_sim = embedder.search(pergunta, n_results=1)
    top_sim = round(docs_sim[0]["similarity"], 3) if docs_sim else 0.0

    # Pipeline RAG completo
    result = get_chain().ask(pergunta)
    latencia_ms = round((time.perf_counter() - t0) * 1000)

    recusou = result["context_chunks"] == 0
    fontes = [{"doc": s, "sim": top_sim} for s in result.get("sources", [])]

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
        "fontes": result.get("sources", []),
    })
    _save(STATS_FILE, stats_data)

    # Persistir historico
    hist_data = _load(HISTORICO_FILE, {"conversas": []})
    conv = next((c for c in hist_data["conversas"] if c["id"] == session_id), None)
    if conv is None:
        tema_id = Path(result["sources"][0]).stem if result.get("sources") else "geral"
        conv = {
            "id": session_id,
            "titulo": pergunta[:80],
            "quando": datetime.now().strftime("%d/%m/%Y"),
            "msgs": 0,
            "confianca": 0.0,
            "tema": tema_id,
            "mensagens": [],
        }
        hist_data["conversas"].insert(0, conv)

    conv["mensagens"].append({"role": "user", "content": pergunta})
    conv["mensagens"].append({
        "role": "assistant",
        "content": result["answer"],
        "sim": top_sim,
    })
    conv["msgs"] = len(conv["mensagens"])
    sims = [m["sim"] for m in conv["mensagens"] if "sim" in m and not recusou]
    conv["confianca"] = round(sum(sims) / len(sims), 3) if sims else 0.0
    _save(HISTORICO_FILE, hist_data)

    return {
        "resposta": result["answer"],
        "fontes": fontes,
        "sim": top_sim,
        "recusou": recusou,
        "latencia_ms": latencia_ms,
    }


@app.get("/api/documentos")
async def documentos():
    docs_dir = Path(os.getenv("DOCS_DIR", "docs"))
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
    temas = []

    if docs_dir.exists():
        for f in sorted(docs_dir.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix.lower() not in {".pdf", ".md", ".txt"}:
                continue

            tema_id = f.stem
            tema_nome = f.stem.replace("-", " ").replace("_", " ").title()
            chunks_count = chunks_por_source.get(f.name, 0)
            indexado = chunks_count > 0

            if not any(t["id"] == tema_id for t in temas):
                temas.append({
                    "id": tema_id,
                    "nome": tema_nome,
                    "descricao": f"Conteudo de {tema_nome}",
                    "cor": _cor(len(temas)),
                    "progresso": 100 if indexado else 0,
                    "aulas": 1,
                    "docs": 0,
                    "dominado": False,
                })

            for t in temas:
                if t["id"] == tema_id:
                    t["docs"] += 1

            size = f.stat().st_size
            size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"

            arquivos.append({
                "id": str(abs(hash(str(f)))),
                "nome": f.name,
                "tipo": f.suffix.lower().lstrip("."),
                "tamanho": size_str,
                "data": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y"),
                "tema": tema_id,
                "chunks": chunks_count,
                "indexado": indexado,
            })

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

    sugestoes = [
        "O que e aprendizado supervisionado?",
        "Como funciona o K-Means?",
        "Quais sao os 4 pilares do Reinforcement Learning?",
        "Para que serve o StandardScaler?",
        "O que e o Metodo do Cotovelo?",
    ]

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


# ---------------------------------------------------------------------------
# Servir frontend estatico
# ---------------------------------------------------------------------------
app.mount("/frontend", StaticFiles(directory=str(ROOT / "frontend")), name="frontend")


@app.get("/")
async def root():
    return FileResponse(str(ROOT / "frontend" / "index.html"))
