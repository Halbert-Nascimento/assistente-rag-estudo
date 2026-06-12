"""
Modulo de Embeddings e Indexacao Vetorial
Gera embeddings PT-BR e persiste no ChromaDB com cosine similarity.
"""

import logging
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentEmbedder:
    """Gerencia embeddings e armazenamento vetorial com ChromaDB."""

    MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
    DB_PATH = 'chroma_db'
    COLLECTION_NAME = 'documentos_estudo'

    def __init__(self, db_path: str = DB_PATH, model_name: str = MODEL_NAME):
        self.db_path = Path(db_path)
        self.model_name = model_name

        logger.info(f"Carregando modelo de embeddings: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Modelo carregado: {model_name}")
        except Exception as e:
            raise RuntimeError(
                f"Falha ao carregar modelo '{model_name}'. "
                f"Verifique a conexao com a internet na primeira execucao. Erro: {e}"
            )

        logger.info(f"Inicializando ChromaDB em '{self.db_path}'")
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Obtem colecao existente ou cria uma nova com distancia cosseno."""
        try:
            collection = self.client.get_collection(name=self.COLLECTION_NAME)
            count = collection.count()
            logger.info(f"Colecao existente '{self.COLLECTION_NAME}': {count} documentos")
            return collection
        except Exception as get_err:
            logger.debug(f"Colecao nao encontrada ({get_err}), criando nova...")
            try:
                return self.client.create_collection(
                    name=self.COLLECTION_NAME,
                    # cosine: valores em [0,1] onde 1 = identico, mais interpretavel
                    metadata={
                        'hnsw:space': 'cosine',
                        'modelo': self.model_name,
                    }
                )
            except Exception as create_err:
                raise RuntimeError(
                    f"Nao foi possivel criar colecao no ChromaDB: {create_err}"
                )

    def embed_and_store(self, chunks: List[Dict]) -> Dict:
        """
        Gera embeddings e armazena no ChromaDB.

        Retorna dict com 'stored', 'failed', 'total' mesmo em caso de erro parcial.
        Nunca lanca excecao — registra tudo em log.
        """
        if not chunks:
            logger.warning("Nenhum chunk recebido para indexar")
            return {'stored': 0, 'failed': 0, 'total': 0}

        logger.info(f"Gerando embeddings para {len(chunks)} chunks...")

        valid_chunks: List[Dict] = []
        embeddings_list: List[List[float]] = []
        failed_count = 0

        for i, chunk in enumerate(chunks):
            content = chunk.get('content', '').strip()
            if not content:
                logger.warning(f"Chunk {i} (id={chunk.get('chunk_id')}) vazio, pulando")
                failed_count += 1
                continue

            try:
                vec = self.model.encode(content, convert_to_numpy=True)
                embeddings_list.append(vec.tolist())  # ChromaDB aceita list[float]
                valid_chunks.append(chunk)
            except Exception as e:
                logger.error(f"Erro ao gerar embedding do chunk {i}: {e}")
                failed_count += 1

            if (i + 1) % 20 == 0:
                logger.info(f"  {i + 1}/{len(chunks)} embeddings processados...")

        logger.info(f"{len(embeddings_list)} embeddings gerados | {failed_count} falharam")

        if not valid_chunks:
            logger.error("Nenhum chunk valido para armazenar")
            return {'stored': 0, 'failed': failed_count, 'total': len(chunks)}

        stored_count = self._store_in_chromadb(valid_chunks, embeddings_list)
        return {
            'stored': stored_count,
            'failed': failed_count + (len(valid_chunks) - stored_count),
            'total': len(chunks),
        }

    def _store_in_chromadb(
        self, chunks: List[Dict], embeddings: List[List[float]]
    ) -> int:
        """
        Persiste chunks no ChromaDB via upsert (idempotente).

        Retorna quantidade efetivamente armazenada.
        """
        try:
            ids       = [c['chunk_id'] for c in chunks]
            documents = [c['content']  for c in chunks]
            metadatas = [
                {
                    'source':      c['source'],
                    'source_path': c['source_path'],
                    'materia':     c.get('materia', 'geral'),
                    'timestamp':   c['timestamp'],
                    'char_count':  str(c.get('char_count', '')),
                }
                for c in chunks
            ]

            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"{len(chunks)} documentos gravados no ChromaDB (upsert)")
            return len(chunks)

        except Exception as e:
            logger.error(f"Erro ao gravar no ChromaDB: {e}")
            # Nao relanca: retorna 0 para que o chamador registre a falha
            return 0

    def search(self, query: str, n_results: int = 5, where: Dict = None) -> List[Dict]:
        """
        Busca documentos por similaridade semantica.

        Args:
            where: filtro opcional de metadados do ChromaDB,
                   ex: {'materia': 'machine-learning'} restringe a busca
                   aos chunks daquela materia.

        Retorna lista vazia (nao lanca excecao) em qualquer caso de falha.
        """
        total = self.collection.count()
        if total == 0:
            logger.warning("Colecao vazia — execute o pipeline de indexacao primeiro")
            return []

        effective_n = min(n_results, total)

        try:
            query_vec = self.model.encode(query, convert_to_numpy=True).tolist()

            results = self.collection.query(
                query_embeddings=[query_vec],
                n_results=effective_n,
                where=where,
                include=['documents', 'metadatas', 'distances'],
            )

            output: List[Dict] = []
            ids       = results.get('ids',       [[]])[0]
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
                # Cosine distance: 0 = identico, 2 = oposto
                # Convertemos para similarity 0..1
                similarity = max(0.0, 1.0 - (dist / 2.0))
                output.append({
                    'id':         doc_id,
                    'content':    doc,
                    'metadata':   meta,
                    'similarity': round(similarity, 4),
                })

            logger.info(f"Busca retornou {len(output)} resultado(s) para: '{query}'")
            return output

        except Exception as e:
            logger.error(f"Erro na busca semantica: {e}")
            return []

    def get_stats(self) -> Dict:
        """Retorna estatisticas do banco de dados."""
        try:
            return {
                'total_documentos': self.collection.count(),
                'colecao':  self.COLLECTION_NAME,
                'modelo':   self.model_name,
                'db_path':  str(self.db_path),
            }
        except Exception as e:
            logger.error(f"Erro ao obter stats: {e}")
            return {}

    def clear_collection(self) -> bool:
        """Apaga e recria a colecao (usar com cuidado)."""
        try:
            self.client.delete_collection(name=self.COLLECTION_NAME)
            self.collection = self._get_or_create_collection()
            logger.info("Colecao limpa e recriada")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar colecao: {e}")
            return False


def embed_and_index(chunks: List[Dict]) -> Dict:
    """Funcao de conveniencia para embedar e indexar documentos."""
    embedder = DocumentEmbedder()
    result = embedder.embed_and_store(chunks)
    return {**result, **embedder.get_stats()}


if __name__ == '__main__':
    from loader import load_documents

    print("=" * 60)
    print("PIPELINE RAG: Loader -> Embedder")
    print("=" * 60)

    chunks, load_summary = load_documents()
    print(f"\nLoader: {load_summary['total_sucesso']} arquivo(s) | {len(chunks)} chunks")

    if not chunks:
        print("Nenhum documento carregado. Adicione arquivos em docs/")
        raise SystemExit(1)

    embedder = DocumentEmbedder()
    embed_result = embedder.embed_and_store(chunks)
    stats = embedder.get_stats()

    print(f"\nIndexacao: {embed_result['stored']} gravados | "
          f"{embed_result['failed']} falharam | "
          f"{stats['total_documentos']} total no DB")

    print("\nTeste de busca semantica:")
    test_query = "Como funciona a inteligencia artificial?"
    results = embedder.search(test_query, n_results=3)

    if results:
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {r['similarity']:.0%} similaridade | {r['metadata']['source']}")
            print(f"       {r['content'][:120]}...")
    else:
        print("  Nenhum resultado encontrado")
