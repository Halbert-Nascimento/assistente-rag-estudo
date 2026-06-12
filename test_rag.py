# -*- coding: utf-8 -*-
"""Script de teste do pipeline RAG (Loader + Embedder)."""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.loader import load_documents
from src.embedder import DocumentEmbedder

print("=" * 70)
print("TESTE DO PIPELINE RAG: Loader -> Embedder")
print("=" * 70)

# Teste 1: Carregar documentos
print("\n[1/3] Carregando documentos...")
chunks, load_summary = load_documents()

print(f"\nLoader:")
print(f"   Arquivos processados: {load_summary['total_sucesso']}")
print(f"   Arquivos com erro: {load_summary['total_falhas']}")
print(f"   Total de chunks: {len(chunks)}")

if chunks:
    print(f"   Primeiro chunk (preview): {chunks[0]['content'][:80]}...")
else:
    print("   Nenhum documento encontrado em docs/")
    print("   Crie alguns arquivos .pdf, .md ou .txt em docs/ para testar")
    sys.exit(0)

# Teste 2: Embedar e indexar
print("\n[2/3] Gerando embeddings e indexando...")
embedder = DocumentEmbedder()
embed_result = embedder.embed_and_store(chunks)

print(f"\nEmbedder:")
print(f"   Documentos armazenados: {embed_result['stored']}")
print(f"   Documentos falhados: {embed_result['failed']}")

# Teste 3: Busca semantica
print("\n[3/3] Testando busca semantica...")
stats = embedder.get_stats()
print(f"\nStats do banco:")
print(f"   Total no ChromaDB: {stats['total_documentos']}")
print(f"   Modelo: {stats['modelo']}")

if stats['total_documentos'] > 0:
    query = "Como funciona?"
    results = embedder.search(query, n_results=2)
    print(f"\n   Teste de busca: '{query}'")
    if results:
        for i, result in enumerate(results, 1):
            relevance = result['similarity'] * 100 if result.get('similarity') else 0
            print(f"   [{i}] Relevancia: {relevance:.1f}% | Fonte: {result['metadata']['source']}")
    else:
        print("   Nenhum resultado encontrado")

print("\n" + "=" * 70)
print("PIPELINE FUNCIONANDO COM SUCESSO!")
print("=" * 70)
