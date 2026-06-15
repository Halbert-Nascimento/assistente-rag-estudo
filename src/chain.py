"""
Modulo RAG Chain
Conecta ChromaDB + Ollama via LangChain com blindagem de prompt.

Fluxo de uma pergunta (metodo ask) — recuperacao em DOIS estagios (FEAT-009):
  1. RECALL: a pergunta vira vetor e busca top-K candidatos no ChromaDB
     (rede ampla, SEM limiar de cosseno — o cosseno e grosseiro e dependente
     do corpus, nao serve como porta de relevancia para PDFs arbitrarios).
  2. RERANK: um cross-encoder multilingue le pergunta+chunk juntos e pontua a
     relevancia real; mantem so os top-N acima de RERANK_MIN_SCORE.
  3. Se nenhum chunk relevante sobrar, recusa SEM chamar o LLM
     (recusa deterministica - nao depende do modelo obedecer o prompt).
  4. Caso contrario, o contexto e injetado no prompt blindado e o LLM responde.

  Se o modelo de reranking nao estiver disponivel, ha fallback automatico para
  o limiar de cosseno (MIN_SIMILARITY) — o sistema nunca fica sem porta de
  relevancia.
"""

import logging
import os
from typing import List, Dict, Optional, Tuple
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from .embedder import DocumentEmbedder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Frase padrao de recusa - usada tanto na recusa deterministica (sem LLM)
# quanto exigida do LLM via prompt. O eval.py verifica esta frase.
REFUSAL_MESSAGE = "Nao encontrei informacao sobre isso nos documentos disponibilizados."

# Prompt blindado: o LLM e proibido de alucinar fora dos documentos
RAG_PROMPT_TEMPLATE = """Voce e um assistente de estudos especializado. Sua unica fonte
de informacao sao os DOCUMENTOS fornecidos abaixo.

REGRAS OBRIGATORIAS:
1. Responda APENAS com base nos DOCUMENTOS. Nao invente, nao suponha.
2. Se a resposta nao estiver nos documentos, diga exatamente:
   "Nao encontrei informacao sobre isso nos documentos disponibilizados."
3. NAO cite o nome dos arquivos na resposta (as fontes sao exibidas
   separadamente pela interface).
4. Responda em portugues do Brasil.
5. Seja claro e objetivo.

DOCUMENTOS:
{context}

PERGUNTA: {question}

RESPOSTA:"""


class RAGChain:
    """
    Pipeline RAG completo: recuperacao + geracao com Ollama.

    Uso:
        chain = RAGChain()
        resposta = chain.ask("O que e aprendizado supervisionado?")
        print(resposta['answer'])
    """

    # Limiar de cosseno — usado APENAS no fallback (quando o reranker nao
    # carrega). E um sinal grosseiro e dependente do corpus; por isso a porta
    # de relevancia principal e o reranker (rerank_min_score). Mantido por
    # seguranca para o sistema nunca ficar sem criterio de recusa.
    MIN_SIMILARITY = 0.68

    # Recuperacao em dois estagios (FEAT-009)
    RECALL_K = 20            # candidatos trazidos pelo recall (rede ampla)
    TOP_N = 4                # chunks que efetivamente vao ao contexto do LLM
    # Porta de relevancia do reranker (score sigmoid 0..1). Calibrado com
    # eval/perguntas_teste.json (mmarco-mMiniLMv2-L12, banco de 06/2026):
    #   - in-scope top1:        0.31 a 1.00 (piso: pergunta de "atencao")
    #   - fora-escopo (lixo):   0.016 a 0.07 (ex: pao de queijo)
    # 0.15 fica na folga entre os dois grupos: recusa deterministica para
    # perguntas claramente sem relacao, sem reprovar perguntas validas dificeis.
    # NAO tenta separar casos-limite (ex: "Copa 2022" casa com um chunk que cita
    # "2022" e pontua ~0.72): esses passam ao LLM, que recusa via prompt blindado
    # por nao achar a resposta no contexto. O reranker corta a DILUICAO (so top-N
    # reordenados vao ao LLM), que era a causa das recusas indevidas.
    RERANK_MIN_SCORE = 0.15

    def __init__(
        self,
        model: str = 'llama3.1',
        ollama_base_url: str = 'http://localhost:11434',
        recall_k: int = None,
        top_n: int = None,
        min_similarity: float = MIN_SIMILARITY,
        rerank_model: str = None,
        rerank_min_score: float = None,
        use_reranker: bool = True,
        embedder: Optional[DocumentEmbedder] = None,
    ):
        # Parametros configuraveis por env (.env), com fallback para as constantes
        self.recall_k = recall_k or int(os.getenv('RAG_RECALL_K', self.RECALL_K))
        self.top_n = top_n or int(os.getenv('RAG_TOP_N', self.TOP_N))
        self.min_similarity = min_similarity
        self.rerank_min_score = (
            rerank_min_score
            if rerank_min_score is not None
            else float(os.getenv('RERANK_MIN_SCORE', self.RERANK_MIN_SCORE))
        )
        self.rerank_model = rerank_model or os.getenv('RERANK_MODEL', '') or None
        self.use_reranker = use_reranker

        # Reranker carregado preguicosamente na 1a busca; _reranker_failed
        # marca indisponibilidade para cair no fallback de cosseno sem retentar.
        self._reranker = None
        self._reranker_failed = False

        # Reutiliza embedder passado ou cria um novo
        self.embedder = embedder or DocumentEmbedder()

        logger.info(f"Conectando ao Ollama ({ollama_base_url}) com modelo '{model}'")
        try:
            self.llm = OllamaLLM(
                model=model,
                base_url=ollama_base_url,
                temperature=0.1,   # baixo: respostas mais conservadoras e factuais
                num_predict=512,   # limite de tokens na resposta
            )
        except Exception as e:
            raise RuntimeError(
                f"Nao foi possivel conectar ao Ollama em {ollama_base_url}. "
                f"Certifique-se de que o servico esta rodando. Erro: {e}"
            )

        self.prompt = PromptTemplate(
            input_variables=['context', 'question'],
            template=RAG_PROMPT_TEMPLATE,
        )

        logger.info("RAGChain pronta")

    def _get_reranker(self):
        """Carrega o reranker preguicosamente; devolve None se indisponivel."""
        if not self.use_reranker or self._reranker_failed:
            return None
        if self._reranker is None:
            try:
                from .reranker import get_reranker, DEFAULT_RERANK_MODEL
                self._reranker = get_reranker(self.rerank_model or DEFAULT_RERANK_MODEL)
            except Exception as e:
                logger.warning(
                    f"Reranker indisponivel ({e}); usando limiar de cosseno como fallback"
                )
                self._reranker_failed = True
                return None
        return self._reranker

    def _retrieve(
        self, question: str, materia: Optional[str] = None
    ) -> Tuple[List[Dict], float]:
        """
        Recupera contexto em dois estagios (recall + rerank).
        Se materia for informada, restringe a busca aos chunks daquela materia.

        Retorna (chunks_relevantes, melhor_cosseno). Nunca lanca excecao:
        em caso de falha devolve ([], 0.0). 'melhor_cosseno' e a maior
        similaridade de cosseno entre os candidatos do recall (informativo para
        a UI, mesmo quando a pergunta e recusada).
        """
        # RECALL: rede ampla, SEM filtro de cosseno (o reranker decide relevancia)
        try:
            where = {'materia': materia} if materia else None
            candidates = self.embedder.search(
                question, n_results=self.recall_k, where=where
            )
        except Exception as e:
            logger.error(f"Erro na recuperacao de contexto: {e}")
            return [], 0.0

        if not candidates:
            return [], 0.0

        top_cosine = max(c.get('similarity', 0.0) for c in candidates)

        # RERANK: cross-encoder pontua relevancia real pergunta<->chunk
        reranker = self._get_reranker()
        if reranker is not None:
            ranked = reranker.rerank(question, candidates)
            # rerank() so adiciona 'rerank_score' se o modelo realmente rodou;
            # se o download/carregamento falhou, caimos no fallback de cosseno.
            if ranked and all('rerank_score' in c for c in ranked):
                relevant = [
                    c for c in ranked if c['rerank_score'] >= self.rerank_min_score
                ][:self.top_n]
                if not relevant:
                    best = max(c['rerank_score'] for c in ranked)
                    logger.info(
                        f"Nenhum chunk passou do rerank_min_score {self.rerank_min_score} "
                        f"(melhor: {best:.3f}) - pergunta provavelmente fora do escopo"
                    )
                return relevant, top_cosine

        # FALLBACK: limiar de cosseno (reranker indisponivel)
        relevant = [
            c for c in candidates if c.get('similarity', 0) >= self.min_similarity
        ][:self.top_n]
        if not relevant:
            logger.info(
                f"[fallback cosseno] nenhum chunk passou de {self.min_similarity} "
                f"(melhor: {top_cosine:.3f}) - pergunta provavelmente fora do escopo"
            )
        return relevant, top_cosine

    def _format_context(self, results: List[Dict]) -> str:
        """Formata os trechos recuperados em um unico bloco de contexto.

        Sem rotulos como "Documento N" ou nome do arquivo: o LLM as vezes
        copiava esses rotulos para a resposta ("conforme o Documento 3..."),
        poluindo o texto. As fontes ja sao exibidas separadamente pela interface.
        """
        return "\n\n---\n\n".join(r['content'] for r in results)

    @staticmethod
    def _build_sources(results: List[Dict]) -> Tuple[List[str], List[Dict]]:
        """Monta as fontes a partir dos chunks selecionados.

        Retorna (sources, sources_detail):
          - sources: nomes de arquivo ordenados (compat. com eval/testes)
          - sources_detail: [{'doc', 'sim'}] com a similaridade REAL por arquivo
            (maior cosseno entre os chunks daquele arquivo), ordenada por sim
            desc. Antes a UI mostrava o mesmo valor para todas as fontes.
        """
        por_fonte: Dict[str, float] = {}
        for r in results:
            src = r['metadata']['source']
            por_fonte[src] = max(por_fonte.get(src, 0.0), r.get('similarity', 0.0))

        sources_detail = sorted(
            [{'doc': doc, 'sim': round(sim, 4)} for doc, sim in por_fonte.items()],
            key=lambda d: d['sim'],
            reverse=True,
        )
        return sorted(por_fonte.keys()), sources_detail

    def ask(self, question: str, materia: Optional[str] = None) -> Dict:
        """
        Responde uma pergunta usando RAG.

        Args:
            materia: se informada, restringe a busca de contexto aos
                     documentos daquela materia (chat com escopo).

        Returns:
            Dict com 'answer', 'sources', 'sources_detail', 'context_chunks',
            'top_similarity'. Nunca lanca excecao - retorna mensagem de erro
            em 'answer'.
        """
        if not question or not question.strip():
            return {
                'answer': "Por favor, faca uma pergunta valida.",
                'sources': [],
                'sources_detail': [],
                'context_chunks': 0,
                'top_similarity': 0.0,
            }

        question = question.strip()
        logger.info(f"Pergunta recebida: '{question}'"
                    + (f" [escopo: {materia}]" if materia else ""))

        # Recuperacao em dois estagios: os mesmos chunks alimentam o LLM e as fontes
        results, top_cosine = self._retrieve(question, materia=materia)

        if not results:
            # Recusa deterministica: nao gasta chamada de LLM
            return {
                'answer': REFUSAL_MESSAGE,
                'sources': [],
                'sources_detail': [],
                'context_chunks': 0,
                'top_similarity': round(top_cosine, 4),
            }

        context = self._format_context(results)
        prompt_text = self.prompt.format(context=context, question=question)

        sources, sources_detail = self._build_sources(results)

        try:
            answer = self.llm.invoke(prompt_text)
        except Exception as e:
            logger.error(f"Erro ao chamar o LLM: {e}")
            return {
                'answer': (
                    f"Erro ao gerar resposta. Verifique se o Ollama esta rodando. "
                    f"Detalhe: {e}"
                ),
                'sources': sources,
                'sources_detail': sources_detail,
                'context_chunks': len(results),
                'top_similarity': round(top_cosine, 4),
            }

        return {
            'answer':         answer.strip(),
            'sources':        sources,
            'sources_detail': sources_detail,
            'context_chunks': len(results),
            'top_similarity': round(top_cosine, 4),
        }

    def check_health(self) -> Dict:
        """
        Verifica o estado de todos os componentes do pipeline.
        Util para diagnostico na UI.
        """
        health = {
            'chromadb': False,
            'ollama':   False,
            'docs_indexados': 0,
            'pronto': False,
        }

        try:
            stats = self.embedder.get_stats()
            health['chromadb'] = True
            health['docs_indexados'] = stats.get('total_documentos', 0)
        except Exception as e:
            logger.error(f"ChromaDB indisponivel: {e}")

        try:
            self.llm.invoke("ok")
            health['ollama'] = True
        except Exception as e:
            logger.warning(f"Ollama indisponivel: {e}")

        health['pronto'] = (
            health['chromadb'] and health['ollama'] and health['docs_indexados'] > 0
        )
        return health


def build_chain(
    model: str = 'llama3.1',
    ollama_base_url: str = 'http://localhost:11434',
) -> RAGChain:
    """Funcao de conveniencia para instanciar a chain."""
    return RAGChain(model=model, ollama_base_url=ollama_base_url)
