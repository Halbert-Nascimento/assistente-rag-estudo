# -*- coding: utf-8 -*-
"""
Testes de Robustez do Pipeline RAG
Valida que os caminhos de erro funcionam de verdade (nao apenas no papel).

Uso:
    python tests/run_tests.py

Nao requer pytest nem Ollama rodando. Usa diretorios temporarios para
nao poluir o banco vetorial real (chroma_db/).
"""

import sys
import io
import shutil
import tempfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Garante que a raiz do projeto esteja no path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Silencia logs durante os testes (so falhas aparecem)
import logging
logging.disable(logging.CRITICAL)

PASSED = 0
FAILED = 0
FAILURES = []


def check(name: str, condition: bool, detail: str = ''):
    """Registra resultado de um teste."""
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  [OK]    {name}")
    else:
        FAILED += 1
        FAILURES.append(f"{name} -- {detail}")
        print(f"  [FALHA] {name} -- {detail}")


# ===========================================================================
# Grupo 1: Loader — caminhos de erro
# ===========================================================================

def test_loader():
    print("\n--- Loader: tratamento de erros ---")
    from src.loader import DocumentLoader

    tmp = Path(tempfile.mkdtemp(prefix='rag_test_'))
    try:
        # 1. Diretorio vazio: nao pode quebrar, retorna lista vazia
        loader = DocumentLoader(str(tmp / 'vazio'))
        chunks, summary = loader.load_all_documents()
        check("Diretorio vazio retorna [] sem quebrar",
              chunks == [] and summary['total_falhas'] == 0)

        # 2. Arquivo vazio: registrado como falha, nao derruba o processo
        docs = tmp / 'docs1'
        docs.mkdir()
        (docs / 'vazio.txt').write_text('', encoding='utf-8')
        (docs / 'valido.md').write_text('Conteudo valido de teste. ' * 30, encoding='utf-8')
        loader = DocumentLoader(str(docs))
        chunks, summary = loader.load_all_documents()
        check("Arquivo vazio vira falha isolada (outros continuam)",
              summary['total_falhas'] == 1 and summary['total_sucesso'] == 1,
              f"falhas={summary['total_falhas']}, sucesso={summary['total_sucesso']}")

        # 2b. Regressao BUG-006: a biblioteca de PDF precisa estar importavel.
        # O loader importava 'PyPDF2' mas o requirements instala 'pypdf'
        # (modulo pypdf) - todo PDF falhava com "pypdf nao esta instalado".
        from src.loader import PdfReader
        check("Biblioteca de PDF (pypdf) disponivel no loader",
              PdfReader is not None,
              "import pypdf/PyPDF2 falhou - PDFs nunca serao indexados")

        # 3. PDF corrompido: registrado como falha, nao derruba o processo
        docs2 = tmp / 'docs2'
        docs2.mkdir()
        (docs2 / 'corrompido.pdf').write_bytes(b'isto nao e um PDF de verdade')
        (docs2 / 'ok.txt').write_text('Texto normal para teste. ' * 30, encoding='utf-8')
        loader = DocumentLoader(str(docs2))
        chunks, summary = loader.load_all_documents()
        check("PDF corrompido vira falha isolada (outros continuam)",
              summary['total_falhas'] == 1 and summary['total_sucesso'] == 1,
              f"falhas={summary['total_falhas']}, sucesso={summary['total_sucesso']}")

        # 4. Encoding latin-1: deve carregar via fallback
        docs3 = tmp / 'docs3'
        docs3.mkdir()
        (docs3 / 'latin.txt').write_bytes(
            ('Educação e ciência são a base. ' * 30).encode('latin-1')
        )
        loader = DocumentLoader(str(docs3))
        chunks, summary = loader.load_all_documents()
        check("Arquivo latin-1 carrega via fallback de encoding",
              summary['total_sucesso'] == 1 and len(chunks) > 0)

        # 5. IDs unicos com nomes de arquivo repetidos em subpastas
        docs4 = tmp / 'docs4'
        (docs4 / 'a').mkdir(parents=True)
        (docs4 / 'b').mkdir(parents=True)
        (docs4 / 'a' / 'aula.md').write_text('Conteudo A. ' * 100, encoding='utf-8')
        (docs4 / 'b' / 'aula.md').write_text('Conteudo B. ' * 100, encoding='utf-8')
        loader = DocumentLoader(str(docs4))
        chunks, _ = loader.load_all_documents()
        ids = [c['chunk_id'] for c in chunks]
        check("chunk_ids unicos mesmo com nomes de arquivo repetidos",
              len(ids) == len(set(ids)),
              f"{len(ids) - len(set(ids))} colisao(oes)")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# Grupo 2: Chunking — regressao do bug dos fragmentos
# ===========================================================================

def test_chunking():
    print("\n--- Chunking: qualidade dos chunks ---")
    from src.loader import DocumentLoader

    tmp = Path(tempfile.mkdtemp(prefix='rag_test_'))
    try:
        docs = tmp / 'docs'
        docs.mkdir()
        texto = ('Esta e uma frase de teste com palavras razoaveis. ' * 60).strip()
        (docs / 'doc.txt').write_text(texto, encoding='utf-8')

        loader = DocumentLoader(str(docs))
        chunks, _ = loader.load_all_documents()

        # Regressao: o bug original gerava ~50 fragmentos de 1-6 chars no
        # final de cada arquivo ("2026", "026", "26", "6"...)
        tiny = [c for c in chunks if c['char_count'] < 50]
        check("Sem fragmentos-lixo no final do arquivo (regressao)",
              len(tiny) <= 1,  # no maximo o ultimo chunk pode ser menor
              f"{len(tiny)} chunks com <50 chars")

        # Tamanho dos chunks respeita o limite configurado
        oversized = [c for c in chunks if c['char_count'] > DocumentLoader.CHUNK_SIZE + 1]
        check("Todos os chunks respeitam CHUNK_SIZE",
              len(oversized) == 0,
              f"{len(oversized)} chunks acima do limite")

        # Sobreposicao: o fim de um chunk deve reaparecer no inicio do proximo
        if len(chunks) >= 2:
            tail = chunks[0]['content'][-20:]
            check("Sobreposicao preserva continuidade entre chunks",
                  tail in chunks[1]['content'] or chunks[1]['content'][:20] in chunks[0]['content'])

        # Regressao: secao so-de-titulo nao pode virar chunk isolado
        # (chunks sem conteudo roubavam vagas do top-N na busca vetorial)
        md = (
            "# Aula X - Tema da Aula\n\n**Video:** aula.mp4\n\n---\n\n"
            "## Conteudo\n\n" + ("Explicacao detalhada do conceito. " * 40)
        )
        (docs / 'aula.md').write_text(md, encoding='utf-8')
        loader = DocumentLoader(str(docs))
        chunks_md, _ = loader.load_all_documents()
        md_chunks = [c for c in chunks_md if c['source'] == 'aula.md']
        so_titulo = [
            c for c in md_chunks
            if 'Explicacao' not in c['content'] and 'Conteudo' not in c['content']
        ]
        check("Secao so-de-titulo e fundida ao conteudo (nao vira chunk)",
              len(so_titulo) == 0,
              f"{len(so_titulo)} chunk(s) so com titulo")

        # Contextualizacao: todo chunk de .md carrega o titulo do documento
        # (sem isso, chunks nao casam com perguntas que citam o tema da aula)
        sem_titulo = [c for c in md_chunks if '# Aula X' not in c['content']]
        check("Chunks de .md carregam o titulo do documento (contexto)",
              len(sem_titulo) == 0,
              f"{len(sem_titulo)} chunk(s) sem titulo")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# Grupo 3: Embedder — banco vetorial
# ===========================================================================

def test_embedder():
    print("\n--- Embedder: banco vetorial (carrega modelo, ~15s) ---")
    from src.embedder import DocumentEmbedder

    tmp = Path(tempfile.mkdtemp(prefix='rag_test_db_'))
    try:
        embedder = DocumentEmbedder(db_path=str(tmp / 'db'))

        # 1. Busca em colecao vazia: nao pode quebrar
        results = embedder.search("qualquer pergunta")
        check("Busca em colecao vazia retorna [] sem quebrar", results == [])

        # 2. Lista vazia de chunks: nao pode quebrar
        r = embedder.embed_and_store([])
        check("embed_and_store([]) retorna zeros sem quebrar",
              r == {'stored': 0, 'failed': 0, 'total': 0})

        # 3. Chunk sem conteudo: contado como falha, nao quebra
        fake = [
            {'chunk_id': 'x_0001', 'content': '', 'source': 's', 'source_path': 's',
             'timestamp': 't', 'char_count': 0},
            {'chunk_id': 'x_0002', 'content': 'Aprendizado de maquina supervisionado',
             'source': 's.md', 'source_path': 's.md', 'timestamp': 't', 'char_count': 37},
        ]
        r = embedder.embed_and_store(fake)
        check("Chunk vazio e pulado; valido e gravado",
              r['stored'] == 1 and r['failed'] == 1,
              f"stored={r['stored']}, failed={r['failed']}")

        # 4. Idempotencia: indexar 2x nao duplica
        r = embedder.embed_and_store(fake)
        total = embedder.collection.count()
        check("Reindexar nao duplica documentos (upsert idempotente)",
              total == 1, f"total no DB: {total}")

        # 5. Busca retorna o documento com similaridade em [0,1]
        results = embedder.search("machine learning supervisionado", n_results=1)
        ok = (len(results) == 1
              and 0.0 <= results[0]['similarity'] <= 1.0)
        check("Busca retorna similaridade valida entre 0 e 1",
              ok,
              f"results={len(results)}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# Grupo 4: Chain — recusa deterministica (sem Ollama)
# ===========================================================================

def test_chain_refusal():
    print("\n--- Chain: recusa sem depender do LLM ---")
    from src.chain import RAGChain, REFUSAL_MESSAGE
    from src.embedder import DocumentEmbedder

    # Usa o banco REAL (51 chunks das aulas) pois o limiar foi calibrado nele.
    # O construtor de OllamaLLM nao abre conexao, entao funciona sem Ollama.
    real_db = ROOT / 'chroma_db'
    if not real_db.exists():
        print("  [PULADO] chroma_db nao existe; rode test_rag.py antes")
        return

    embedder = DocumentEmbedder(db_path=str(real_db))
    if embedder.collection.count() == 0:
        print("  [PULADO] chroma_db vazio; rode test_rag.py antes")
        return

    chain = RAGChain(embedder=embedder)

    # 1. Pergunta vazia
    r = chain.ask("")
    check("Pergunta vazia tratada sem quebrar", 'pergunta valida' in r['answer'])

    # 2. Fora do escopo (claramente sem relacao): recusa SEM chamar o LLM.
    #    O reranker pontua ~0 esses chunks, entao a recusa e deterministica
    #    (Ollama nem esta rodando aqui).
    r = chain.ask("Qual e a receita tradicional do pao de queijo mineiro?")
    check("Pergunta fora do escopo recusada deterministicamente",
          r['answer'] == REFUSAL_MESSAGE and r['context_chunks'] == 0,
          f"answer={r['answer'][:60]}")
    check("Fora do escopo: recusou=True, motivo='fora_escopo'",
          r.get('recusou') is True and r.get('motivo') == 'fora_escopo',
          f"recusou={r.get('recusou')}, motivo={r.get('motivo')}")

    r = chain.ask("Qual e a capital da Mongolia?")
    check("Segunda pergunta fora do escopo tambem recusada",
          r['answer'] == REFUSAL_MESSAGE and r['context_chunks'] == 0,
          f"answer={r['answer'][:60]}")

    # NOTA: casos-limite onde um chunk casa espuriamente (ex: "Copa 2022" casa
    # com algum chunk que cita o ano e pontua alto no reranker) NAO sao recusados
    # deterministicamente — passam ao LLM, que recusa via prompt blindado por nao
    # achar a resposta. O reranker garante que so os top-N reordenados cheguem ao
    # LLM, eliminando a diluicao de contexto (FEAT-009).

    # 3. Dentro do escopo: chunks passam da porta de relevancia (LLM falharia,
    #    mas o erro e capturado e vira mensagem amigavel — testa o caminho de erro)
    r = chain.ask("O que e o Metodo do Cotovelo no K-Means?")
    check("Pergunta in-scope recupera contexto relevante (recall+rerank)",
          r['context_chunks'] > 0,
          f"chunks={r['context_chunks']}")
    check("Erro de LLM offline vira mensagem amigavel (nao excecao)",
          'Erro ao gerar resposta' in r['answer'] or len(r.get('sources', [])) > 0)

    # 3b. Regressao FEAT-009: ask() devolve similaridade REAL por fonte
    #     (antes a UI mostrava o mesmo % para todas as fontes) e top_similarity.
    check("ask() devolve sources_detail e top_similarity",
          'sources_detail' in r and 'top_similarity' in r,
          f"chaves={list(r.keys())}")
    detail_ok = all(
        isinstance(d, dict) and 'doc' in d and 'sim' in d and 0.0 <= d['sim'] <= 1.0
        for d in r.get('sources_detail', [])
    )
    check("sources_detail bem-formado (doc + sim por arquivo em [0,1])",
          detail_ok and len(r.get('sources_detail', [])) >= 1,
          f"sources_detail={r.get('sources_detail')}")
    # As fontes vem ordenadas por similaridade decrescente
    sims = [d['sim'] for d in r.get('sources_detail', [])]
    check("sources_detail ordenado por similaridade desc",
          sims == sorted(sims, reverse=True),
          f"sims={sims}")

    # 3c. Regressao: a recusa deterministica nao recupera contexto mas ainda
    #     reporta top_similarity (melhor cosseno) para diagnostico na UI.
    r_fora = chain.ask("Qual e a previsao do tempo para amanha em Toquio?")
    check("Recusa nao retorna fontes mas reporta top_similarity e top_relevance",
          r_fora['context_chunks'] == 0
          and 'top_similarity' in r_fora
          and 'top_relevance' in r_fora
          and r_fora['sources_detail'] == [],
          f"chunks={r_fora['context_chunks']}, top_sim={r_fora.get('top_similarity')}, "
          f"top_rel={r_fora.get('top_relevance')}")
    check("Fora do escopo reporta motivo='fora_escopo'",
          r_fora.get('motivo') == 'fora_escopo', f"motivo={r_fora.get('motivo')}")

    # 3d. Detector de recusa do LLM (material insuficiente) — sem Ollama.
    #     Identifica recusas geradas pelo LLM mesmo quando ele parafraseia.
    from src.chain import _looks_like_refusal, INSUFFICIENT_MESSAGE
    check("Detecta a frase de recusa padrao do LLM",
          _looks_like_refusal(INSUFFICIENT_MESSAGE))
    check("Detecta parafrase de recusa do LLM",
          _looks_like_refusal("Não encontrei informação sobre 'Gerência de Projetos' nos documentos."))
    check("NAO marca uma resposta normal como recusa",
          not _looks_like_refusal("O StandardScaler coloca as variáveis na mesma escala antes do K-Means."))


# ===========================================================================
# Grupo 5: Operacoes de documento — excluir, mover, reset (estado do ChromaDB)
# ===========================================================================

def test_doc_operations():
    """Valida que excluir/mover/reset deixam o ChromaDB consistente: sem
    fantasma (vetor de algo removido), sem duplicata e sem arquivo orfao.

    Espelha a logica dos endpoints em api.py (DELETE /api/documentos,
    POST /api/documentos/mover, POST /api/reset) usando os mesmos blocos
    (collection.delete por source_path, clear_collection, manifest incremental).
    Roda num banco/docs temporarios — nao toca em chroma_db/ real.
    """
    print("\n--- Operacoes de documento: excluir, mover, reset ---")
    import json
    import hashlib
    from src.embedder import DocumentEmbedder
    from src.loader import load_documents

    tmp = Path(tempfile.mkdtemp(prefix='rag_docops_'))
    try:
        docs = tmp / 'docs'
        (docs / 'ml').mkdir(parents=True)
        (docs / 'rl').mkdir(parents=True)
        (docs / 'ml' / 'silhouette.md').write_text(
            "# Aula 06 | Nao Supervisionado\n\n## Silhouette Score\n\n"
            "O Silhouette Score mede a qualidade dos clusters de -1 a 1. " * 10,
            encoding='utf-8')
        (docs / 'rl' / 'epsilon.md').write_text(
            "# Aula 07 | Reinforcement Learning\n\n## Epsilon Decay\n\n"
            "O Epsilon Decay reduz a taxa de exploracao do agente. " * 10,
            encoding='utf-8')
        (docs / 'notas.txt').write_text(
            "Anotacoes gerais sobre overfitting e regularizacao. " * 10, encoding='utf-8')

        emb = DocumentEmbedder(db_path=str(tmp / 'db'))
        manifest = tmp / 'manifest.json'

        def _md5(p):
            return hashlib.md5(Path(p).read_bytes()).hexdigest()

        def indexar():
            """Espelha _run_indexing (api.py): indexacao incremental por hash."""
            chunks, _ = load_documents(str(docs))
            man = json.loads(manifest.read_text()) if manifest.exists() else {}
            por = {}
            for c in chunks:
                por.setdefault(c['source_path'], []).append(c)
            novos = []
            for sp, cs in por.items():
                h = _md5(docs / sp)
                if man.get(sp) == h:
                    continue
                novos.extend(cs)
                man[sp] = h
            if novos:
                emb.embed_and_store(novos)
            manifest.write_text(json.dumps(man))

        def conta(**w):
            return len(emb.collection.get(where=w if w else None)['ids'])

        indexar()
        sp_ml = str(Path('ml') / 'silhouette.md')
        sp_geral = 'notas.txt'

        # --- EXCLUIR (espelha DELETE /api/documentos) ---
        ml_antes = conta(source_path=sp_ml)
        emb.collection.delete(where={'source_path': sp_geral})
        man = json.loads(manifest.read_text()); man.pop(sp_geral, None)
        manifest.write_text(json.dumps(man))
        (docs / sp_geral).unlink()
        check("Excluir: chunks do arquivo somem (sem fantasma)",
              conta(source_path=sp_geral) == 0)
        check("Excluir: outros arquivos ficam intactos",
              conta(source_path=sp_ml) == ml_antes,
              f"ml antes={ml_antes}, depois={conta(source_path=sp_ml)}")

        # --- MOVER ml -> rl (espelha POST /api/documentos/mover) ---
        total_antes = conta(source_path=sp_ml)
        emb.collection.delete(where={'source_path': sp_ml})
        man = json.loads(manifest.read_text()); man.pop(sp_ml, None)
        manifest.write_text(json.dumps(man))
        (docs / sp_ml).rename(docs / 'rl' / 'silhouette.md')
        if not any((docs / 'ml').iterdir()):
            (docs / 'ml').rmdir()
        indexar()
        sp_novo = str(Path('rl') / 'silhouette.md')
        check("Mover: some da materia antiga (sem fantasma)",
              conta(source_path=sp_ml) == 0 and conta(materia='ml') == 0)
        check("Mover: aparece na materia nova", conta(source_path=sp_novo) >= 1)
        check("Mover: sem duplicata (total de chunks igual ao original)",
              conta(source_path=sp_novo) == total_antes,
              f"antes={total_antes}, agora={conta(source_path=sp_novo)}")
        metas = emb.collection.get(where={'source_path': sp_novo})['metadatas']
        check("Mover: metadado 'materia' atualizado para a nova",
              all(m.get('materia') == 'rl' for m in metas),
              f"materias={set(m.get('materia') for m in metas)}")

        # --- RESET (espelha clear_collection de POST /api/reset) ---
        ok = emb.clear_collection()
        check("Reset: clear_collection() retorna True e zera o banco",
              ok and emb.collection.count() == 0,
              f"ok={ok}, count={emb.collection.count()}")
        # Apos o reset, o manifest e apagado: re-indexar repovoa do zero
        manifest.unlink()
        indexar()
        check("Reset: re-indexacao apos reset repovoa o banco (sem skip indevido)",
              emb.collection.count() >= 1, f"count={emb.collection.count()}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================

if __name__ == '__main__':
    print("=" * 60)
    print(" TESTES DE ROBUSTEZ DO PIPELINE RAG")
    print("=" * 60)

    test_loader()
    test_chunking()
    test_embedder()
    test_chain_refusal()
    test_doc_operations()

    print("\n" + "=" * 60)
    print(f" RESULTADO: {PASSED} passaram | {FAILED} falharam")
    if FAILURES:
        print("\n Falhas:")
        for f in FAILURES:
            print(f"   - {f}")
    print("=" * 60)

    sys.exit(1 if FAILED else 0)
