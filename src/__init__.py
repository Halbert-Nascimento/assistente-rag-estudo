"""Pacote RAG: Pipeline de Retrieval-Augmented Generation."""

from .loader import DocumentLoader, load_documents
from .embedder import DocumentEmbedder, embed_and_index
from .chain import RAGChain, build_chain

__all__ = [
    'DocumentLoader',
    'load_documents',
    'DocumentEmbedder',
    'embed_and_index',
    'RAGChain',
    'build_chain',
]
