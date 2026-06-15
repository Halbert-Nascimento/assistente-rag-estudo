"""
Modulo de Reranking (cross-encoder)
Reordena os candidatos da busca vetorial por RELEVANCIA real pergunta<->chunk.

Por que existe (FEAT-009):
  A similaridade do cosseno do modelo de embeddings (bi-encoder) e um sinal
  grosseiro e DEPENDENTE DO CORPUS — um limiar fixo (ex: 0.68) que funciona
  para um conjunto de PDFs nao funciona para outro. Como o app e distribuido e
  cada usuario coloca os PDFs que quiser, precisamos de um sinal de relevancia
  estavel entre corpora.

  O cross-encoder le a pergunta E o chunk JUNTOS e devolve um score de
  relevancia calibrado. E mais caro que o bi-encoder (nao da pra pre-indexar),
  por isso roda so sobre os top-K candidatos do recall — padrao "retrieve & rerank".

  O CrossEncoder ja vem em sentence-transformers: sem nova dependencia pip.
  O modelo (~470MB) e baixado uma vez e cacheado (mesmo volume hf_cache do Docker).
"""

import logging
import math
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Multilingue treinado em mMARCO (inclui portugues). Sweet spot tamanho/qualidade.
# Trocavel via env RERANK_MODEL (ex: BAAI/bge-reranker-base para mais qualidade).
DEFAULT_RERANK_MODEL = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'


def _sigmoid(x: float) -> float:
    """Normaliza o logit do cross-encoder para [0,1] (relevancia interpretavel)."""
    # clamp evita overflow em math.exp para logits extremos
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


class CrossEncoderReranker:
    """
    Reordena candidatos por relevancia usando um cross-encoder multilingue.

    Carregamento preguicoso: o modelo so e baixado/carregado na 1a chamada de
    rerank(), para nao penalizar o import nem os testes que nao usam rerank.
    """

    def __init__(self, model_name: str = DEFAULT_RERANK_MODEL):
        self.model_name = model_name
        self._model = None  # lazy

    def _ensure_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info(f"Carregando cross-encoder de reranking: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder de reranking pronto")
        return self._model

    def rerank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        Recebe a pergunta e os candidatos do recall (cada um com 'content').
        Devolve a MESMA lista com o campo 'rerank_score' (0..1) adicionado,
        ordenada por relevancia decrescente.

        Nao lanca excecao: em caso de falha, devolve os candidatos sem alterar
        a ordem (o chamador decide o fallback).
        """
        if not candidates:
            return []

        try:
            model = self._ensure_model()
            pairs = [(query, c['content']) for c in candidates]
            raw_scores = model.predict(pairs)  # logits (numpy array)
            for c, s in zip(candidates, raw_scores):
                c['rerank_score'] = round(_sigmoid(float(s)), 4)
            return sorted(candidates, key=lambda c: c['rerank_score'], reverse=True)
        except Exception as e:
            logger.error(f"Falha no reranking ({e}); mantendo ordem do recall")
            return candidates


# Singleton preguicoso compartilhado (o modelo e pesado; carrega 1 vez por processo)
_reranker: Optional[CrossEncoderReranker] = None


def get_reranker(model_name: str = DEFAULT_RERANK_MODEL) -> CrossEncoderReranker:
    global _reranker
    if _reranker is None or _reranker.model_name != model_name:
        _reranker = CrossEncoderReranker(model_name)
    return _reranker
