# -*- coding: utf-8 -*-
"""
Avaliacao Automatizada do Assistente RAG
Mede latencia, recuperacao de contexto, cobertura de keywords e recusa fora de escopo.

Uso:
    python eval/eval.py                   # Avalia so recuperacao (sem Ollama)
    python eval/eval.py --full            # Avaliacao completa com LLM
    python eval/eval.py --output results.json
"""

import sys
import json
import time
import argparse
import logging
import unicodedata
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Garante que raiz do projeto esteja no path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PERGUNTAS_PATH = Path(__file__).parent / 'perguntas_teste.json'
FRASE_RECUSA   = 'nao encontrei informacao sobre isso nos documentos'


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------

def load_questions() -> List[Dict]:
    with open(PERGUNTAS_PATH, encoding='utf-8') as f:
        data = json.load(f)
    return data['perguntas']


# ---------------------------------------------------------------------------
# Metricas individuais
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Remove acentos e converte para minusculas (comparacao robusta).

    O LLM pode responder 'Não encontrei informação...' com acentos;
    sem normalizacao, recusas corretas seriam contadas como falha.
    """
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower()


def check_keywords(answer: str, keywords: List[str]) -> Dict:
    """Conta quantas palavras-chave aparecem na resposta (ignora caixa e acentos)."""
    if not keywords:
        return {'encontradas': 0, 'total': 0, 'cobertura': None}

    answer_norm = _normalize(answer)
    encontradas = [kw for kw in keywords if _normalize(kw) in answer_norm]
    return {
        'encontradas': len(encontradas),
        'total':       len(keywords),
        'cobertura':   round(len(encontradas) / len(keywords), 2),
        'keywords_ok': encontradas,
    }


def check_refusal(answer: str) -> bool:
    """Verifica se a resposta e uma recusa correta (ignora caixa e acentos)."""
    return FRASE_RECUSA in _normalize(answer)


def check_source(sources: List[str], expected_source: str) -> bool:
    """Verifica se a fonte esperada esta entre as retornadas."""
    if not expected_source:
        return True  # sem fonte esperada (fora do escopo)
    return any(expected_source in s for s in sources)


# ---------------------------------------------------------------------------
# Avaliacao de uma pergunta
# ---------------------------------------------------------------------------

def evaluate_question(
    question: Dict,
    chain,
    full: bool = False,
) -> Dict:
    """
    Avalia uma unica pergunta.
    - A recuperacao SEMPRE passa pelo pipeline real (recall + rerank) via
      chain._retrieve, para validar a robustez mesmo sem o Ollama ligado.
      Chunks selecionados = 0 ja significa recusa correta (fora do escopo).
    - Se full=True: tambem chama o LLM (chain.ask) e mede a geracao.
    """
    result: Dict[str, Any] = {
        'id':          question['id'],
        'pergunta':    question['pergunta'],
        'dificuldade': question['dificuldade'],
        'escopo':      question['escopo'],
    }

    # --- Recuperacao de contexto (recall + rerank) ---
    t0 = time.perf_counter()
    try:
        docs, _top_cosine, _top_rel = chain._retrieve(question['pergunta'])
    except Exception as e:
        docs = []
        logger.error(f"Erro na recuperacao (pergunta {question['id']}): {e}")
    recuperacao_ms = round((time.perf_counter() - t0) * 1000, 1)

    result['recuperacao_ms']    = recuperacao_ms
    result['chunks_encontrados'] = len(docs)
    result['fonte_correta']     = check_source(
        [d['metadata'].get('source', '') for d in docs],
        question.get('fonte_esperada') or '',
    )

    if not full:
        result['modo'] = 'recuperacao_apenas'
        result['aviso'] = 'Ollama indisponivel. Apenas a recuperacao (recall+rerank) foi avaliada.'
        return result

    # --- Geracao com LLM ---
    result['modo'] = 'completo'
    t1 = time.perf_counter()
    try:
        resposta = chain.ask(question['pergunta'])
        answer   = resposta.get('answer', '')
        sources  = resposta.get('sources', [])
    except Exception as e:
        logger.error(f"Erro no LLM (pergunta {question['id']}): {e}")
        answer  = ''
        sources = []
    geracao_ms = round((time.perf_counter() - t1) * 1000, 1)

    result['geracao_ms']      = geracao_ms
    # round() evita artefato de ponto flutuante (ex: 2435.6000000000004)
    result['latencia_total_ms'] = round(recuperacao_ms + geracao_ms, 1)
    result['resposta_preview'] = answer[:200].replace('\n', ' ')
    result['fontes_retornadas'] = sources

    kw = check_keywords(answer, question.get('palavras_chave', []))
    result['keywords'] = kw

    if question['escopo'] == 'fora':
        result['recusou_corretamente'] = check_refusal(answer)
        result['passou'] = result['recusou_corretamente']
    else:
        cobertura = kw.get('cobertura')
        fonte_ok  = check_source(sources, question.get('fonte_esperada') or '')
        result['fonte_correta'] = fonte_ok
        result['passou'] = (cobertura is not None and cobertura >= 0.4) and fonte_ok

    return result


# ---------------------------------------------------------------------------
# Relatorio
# ---------------------------------------------------------------------------

def print_report(results: List[Dict], mode: str):
    sep = '=' * 72
    print(f'\n{sep}')
    print(' RELATORIO DE AVALIACAO DO ASSISTENTE RAG')
    print(f' Modo: {mode.upper()} | {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    print(sep)

    # Conta apenas perguntas DENTRO do escopo (as recusas tem contagem propria)
    passou_in = sum(
        1 for r in results
        if r.get('escopo') == 'dentro' and r.get('passou', False)
    )
    total_in = sum(1 for r in results if r.get('escopo') == 'dentro')
    recusas  = [r for r in results if r.get('escopo') == 'fora']
    recusas_ok = sum(1 for r in recusas if r.get('recusou_corretamente', False))

    if mode == 'completo':
        latencias = [r['latencia_total_ms'] for r in results if 'latencia_total_ms' in r]
        lat_media = round(sum(latencias) / len(latencias), 1) if latencias else 0
        lat_max   = max(latencias) if latencias else 0
        print(f' Latencia media  : {lat_media} ms')
        print(f' Latencia maxima : {lat_max} ms')

    rec_media = round(
        sum(r.get('chunks_encontrados', 0) for r in results) / len(results), 1
    )
    print(f' Chunks/pergunta : {rec_media} (media)')
    if mode == 'completo':
        # 'passou' e 'recusou_corretamente' so existem com LLM
        print(f' Passou (in-scope): {passou_in}/{total_in}')
        print(f' Recusas corretas: {recusas_ok}/{len(recusas)}')
    else:
        fontes_ok = sum(
            1 for r in results
            if r.get('escopo') == 'dentro' and r.get('fonte_correta')
        )
        print(f' Fonte correta   : {fontes_ok}/{total_in} (in-scope)')
    print(sep)

    header = f"{'ID':>3} {'Dific':8} {'Escopo':8} {'Chunks':6} {'Fonte':6}"
    if mode == 'completo':
        header += f" {'Kw%':5} {'Lat(ms)':8} {'OK':4}"
    print(header)
    print('-' * 72)

    for r in results:
        dif    = r.get('dificuldade', '')[:7]
        escopo = r.get('escopo', '')[:7]
        chunks = r.get('chunks_encontrados', '-')
        fonte  = 'SIM' if r.get('fonte_correta') else 'NAO'
        linha  = f"{r['id']:>3} {dif:8} {escopo:8} {str(chunks):6} {fonte:6}"

        if mode == 'completo':
            kw_cob = r.get('keywords', {}).get('cobertura')
            kw_str = f"{kw_cob:.0%}" if kw_cob is not None else ' N/A'
            lat    = r.get('latencia_total_ms')
            lat_str = f"{lat:.0f}" if isinstance(lat, (int, float)) else '-'
            # ok_str: nome distinto de 'passou_in' para nao sobrescrever o contador
            ok_str = 'SIM' if r.get('passou') else 'NAO'
            if r.get('escopo') == 'fora':
                kw_str = ' N/A'
                ok_str = 'SIM' if r.get('recusou_corretamente') else 'NAO'
            linha += f" {kw_str:5} {lat_str:8} {ok_str:4}"

        print(linha)

    print(sep)

    if mode == 'completo':
        print(f'\n SCORE FINAL: {passou_in}/{total_in} in-scope | '
              f'{recusas_ok}/{len(recusas)} recusas')
    print(sep + '\n')


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Avalia o Assistente RAG')
    parser.add_argument(
        '--full', action='store_true',
        help='Avaliacao completa com LLM (requer Ollama rodando)'
    )
    parser.add_argument(
        '--output', default='eval/resultados.json',
        help='Caminho para salvar resultados JSON (default: eval/resultados.json)'
    )
    args = parser.parse_args()

    questions = load_questions()
    logger.info(f"Carregadas {len(questions)} perguntas de avaliacao")

    # Inicializa embedder (sempre necessario)
    logger.info("Inicializando embedder...")
    from src.embedder import DocumentEmbedder
    embedder = DocumentEmbedder()

    stats = embedder.get_stats()
    if stats.get('total_documentos', 0) == 0:
        logger.error(
            "ChromaDB vazio! Execute primeiro: python test_rag.py\n"
            "Isso indexara os documentos em docs/ antes da avaliacao."
        )
        sys.exit(1)

    logger.info(f"ChromaDB: {stats['total_documentos']} chunks indexados")

    # A chain e SEMPRE necessaria: a recuperacao passa pelo recall + rerank.
    # O construtor de OllamaLLM nao abre conexao, entao funciona sem Ollama;
    # o reranker carrega preguicosamente na 1a busca.
    logger.info("Inicializando RAGChain (recall + rerank)...")
    from src.chain import RAGChain
    chain = RAGChain(embedder=embedder)

    full = False
    if args.full:
        try:
            chain.llm.invoke('ping')  # teste rapido de conectividade
            full = True
            logger.info("Ollama conectado")
        except Exception as e:
            logger.warning(
                f"Ollama indisponivel ({e}). "
                "Rodando em modo recuperacao-apenas. Use --full quando o Ollama estiver ativo."
            )

    mode = 'completo' if full else 'recuperacao_apenas'
    logger.info(f"Modo de avaliacao: {mode}")

    # Avalia todas as perguntas
    results = []
    for q in questions:
        logger.info(f"[{q['id']:02d}/10] {q['pergunta'][:60]}...")
        result = evaluate_question(q, chain, full)
        results.append(result)

    # Exibe relatorio no terminal
    print_report(results, mode)

    # Salva JSON completo
    output = {
        'timestamp': datetime.now().isoformat(),
        'modo':      mode,
        'modelo_embeddings': stats.get('modelo'),
        'total_chunks_db':   stats.get('total_documentos'),
        'resultados': results,
        'resumo': {
            'total_perguntas':   len(results),
            'in_scope':          sum(1 for r in results if r.get('escopo') == 'dentro'),
            'out_of_scope':      sum(1 for r in results if r.get('escopo') == 'fora'),
            'passou_in_scope':   sum(
                1 for r in results
                if r.get('escopo') == 'dentro' and r.get('passou', False)
            ),
            'recusas_corretas':  sum(1 for r in results if r.get('recusou_corretamente', False)),
            'lat_media_ms':      round(
                sum(r.get('latencia_total_ms', 0) for r in results) / len(results), 1
            ) if mode == 'completo' else None,
        }
    }

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"Resultados salvos em: {out_path}")


if __name__ == '__main__':
    main()
