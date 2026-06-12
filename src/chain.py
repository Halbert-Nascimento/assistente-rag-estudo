"""
Modulo RAG Chain
Conecta ChromaDB + Ollama via LangChain com blindagem de prompt.

Fluxo de uma pergunta (metodo ask):
  1. A pergunta e convertida em vetor e buscada no ChromaDB (1 unica busca).
  2. Chunks com similaridade abaixo de MIN_SIMILARITY sao descartados.
  3. Se nenhum chunk relevante sobrar, recusa SEM chamar o LLM
     (recusa deterministica - nao depende do modelo obedecer o prompt).
  4. Caso contrario, o contexto e injetado no prompt blindado e o LLM responde.
"""

import logging
from typing import List, Dict, Optional
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
3. Cite sempre a fonte entre parenteses, ex: (Fonte: aula-06.md)
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

    # Limiar de similaridade para considerar um chunk relevante.
    # Medido empiricamente com eval/perguntas_teste.json (chunks
    # contextualizados com titulo do documento, banco de 12/06/2026):
    #   - perguntas dentro do escopo: top-1 entre 0.727 e 0.875
    #   - perguntas fora do escopo:   top-1 entre 0.539 e 0.630
    # 0.68 fica no meio da zona de separacao entre os dois grupos.
    MIN_SIMILARITY = 0.68

    def __init__(
        self,
        model: str = 'llama3.1',
        ollama_base_url: str = 'http://localhost:11434',
        n_results: int = 4,
        min_similarity: float = MIN_SIMILARITY,
        embedder: Optional[DocumentEmbedder] = None,
    ):
        self.n_results = n_results
        self.min_similarity = min_similarity

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

    def _retrieve(self, question: str) -> List[Dict]:
        """
        Busca chunks no ChromaDB e filtra pelo limiar de similaridade.
        Retorna lista vazia (nao lanca excecao) em caso de falha.
        """
        try:
            results = self.embedder.search(question, n_results=self.n_results)
        except Exception as e:
            logger.error(f"Erro na recuperacao de contexto: {e}")
            return []

        relevant = [r for r in results if r.get('similarity', 0) >= self.min_similarity]

        if results and not relevant:
            best = max(r.get('similarity', 0) for r in results)
            logger.info(
                f"Nenhum chunk passou do limiar {self.min_similarity} "
                f"(melhor: {best:.3f}) - pergunta provavelmente fora do escopo"
            )

        return relevant

    def _format_context(self, results: List[Dict]) -> str:
        """Formata lista de resultados em bloco de contexto para o prompt."""
        parts: List[str] = []
        for i, r in enumerate(results, start=1):
            source = r['metadata'].get('source', 'desconhecido')
            sim    = r.get('similarity', 0)
            parts.append(
                f"[Documento {i} | Fonte: {source} | Similaridade: {sim:.0%}]\n"
                f"{r['content']}"
            )
        return "\n\n---\n\n".join(parts)

    def ask(self, question: str) -> Dict:
        """
        Responde uma pergunta usando RAG.

        Returns:
            Dict com 'answer', 'sources', 'context_chunks'
            Nunca lanca excecao - retorna mensagem de erro em 'answer'.
        """
        if not question or not question.strip():
            return {
                'answer': "Por favor, faca uma pergunta valida.",
                'sources': [],
                'context_chunks': 0,
            }

        question = question.strip()
        logger.info(f"Pergunta recebida: '{question}'")

        # Busca unica: os mesmos chunks alimentam o LLM e o campo 'sources'
        results = self._retrieve(question)

        if not results:
            # Recusa deterministica: nao gasta chamada de LLM
            return {
                'answer': REFUSAL_MESSAGE,
                'sources': [],
                'context_chunks': 0,
            }

        context = self._format_context(results)
        prompt_text = self.prompt.format(context=context, question=question)

        try:
            answer = self.llm.invoke(prompt_text)
        except Exception as e:
            logger.error(f"Erro ao chamar o LLM: {e}")
            return {
                'answer': (
                    f"Erro ao gerar resposta. Verifique se o Ollama esta rodando. "
                    f"Detalhe: {e}"
                ),
                'sources': [],
                'context_chunks': len(results),
            }

        sources = sorted({r['metadata']['source'] for r in results})

        return {
            'answer':         answer.strip(),
            'sources':        sources,
            'context_chunks': len(results),
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
