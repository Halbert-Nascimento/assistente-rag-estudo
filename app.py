"""
Assistente RAG de Estudos — Interface Streamlit
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# Garante que src/ seja encontrado quando rodado a partir da raiz
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL    = os.getenv('OLLAMA_MODEL', 'llama3.1')
DOCS_DIR        = os.getenv('DOCS_DIR', 'docs')

# Silencia logs HTTP verbosos do HuggingFace/httpx na UI
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('huggingface_hub').setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Cache de recursos pesados (1 instância por sessão de servidor)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner='Carregando modelo de embeddings...')
def get_embedder():
    from src.embedder import DocumentEmbedder
    return DocumentEmbedder()


@st.cache_resource(show_spinner='Conectando ao Ollama...')
def get_chain(_embedder):
    """
    Usa _embedder como argumento para que o cache seja invalidado
    se o embedder mudar; o underscore evita que o Streamlit tente
    fazer hash do objeto.
    """
    from src.chain import RAGChain
    return RAGChain(
        model=OLLAMA_MODEL,
        ollama_base_url=OLLAMA_BASE_URL,
        embedder=_embedder,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_icon(ok: bool) -> str:
    return ':white_check_mark:' if ok else ':x:'


def _check_health(chain) -> dict:
    """Verifica status sem travar a UI (erros viram False silencioso)."""
    health = {'chromadb': False, 'ollama': False, 'docs_indexados': 0, 'pronto': False}
    try:
        stats = chain.embedder.get_stats()
        health['chromadb'] = True
        health['docs_indexados'] = stats.get('total_documentos', 0)
    except Exception:
        pass
    try:
        chain.llm.invoke('ping')
        health['ollama'] = True
    except Exception:
        pass
    health['pronto'] = (
        health['chromadb'] and health['ollama'] and health['docs_indexados'] > 0
    )
    return health


def _run_indexing(embedder) -> dict:
    """Executa loader + embedder e retorna resumo para exibir na UI."""
    from src.loader import load_documents

    chunks, load_summary = load_documents(DOCS_DIR)

    if not chunks:
        return {
            'ok': False,
            'msg': f'Nenhum arquivo encontrado em `{DOCS_DIR}/`. '
                   'Adicione arquivos .pdf, .md ou .txt e tente novamente.',
            'chunks': 0,
            'falhas': load_summary.get('total_falhas', 0),
            'arquivos': 0,
        }

    result = embedder.embed_and_store(chunks)

    return {
        'ok': result['stored'] > 0,
        'msg': (
            f"{result['stored']} chunks indexados de "
            f"{load_summary['total_sucesso']} arquivo(s)."
            + (f" {result['failed']} chunk(s) falharam." if result['failed'] else '')
            + (f" {load_summary['total_falhas']} arquivo(s) com erro." if load_summary['total_falhas'] else '')
        ),
        'chunks':   result['stored'],
        'falhas':   load_summary['total_falhas'],
        'arquivos': load_summary['total_sucesso'],
        'arquivos_com_erro': load_summary.get('arquivos_falhados', []),
    }


# ---------------------------------------------------------------------------
# Componentes de UI
# ---------------------------------------------------------------------------

def render_sidebar(chain):
    with st.sidebar:
        st.title('Assistente RAG')
        st.caption(f'Modelo: `{OLLAMA_MODEL}` | Ollama: `{OLLAMA_BASE_URL}`')

        st.divider()

        # --- Status ---
        st.subheader('Status do sistema')

        if st.button('Verificar status', use_container_width=True):
            st.session_state['health'] = _check_health(chain)

        health = st.session_state.get('health')
        if health is None:
            st.info('Clique em **Verificar status** para checar os componentes.')
        else:
            col1, col2 = st.columns(2)
            col1.metric('ChromaDB', _status_icon(health['chromadb']))
            col2.metric('Ollama',   _status_icon(health['ollama']))
            st.metric('Documentos indexados', health['docs_indexados'])

            if not health['ollama']:
                st.warning(
                    'Ollama nao esta respondendo. '
                    'Inicie o servico com `ollama serve` ou via Docker.',
                    icon='⚠️',
                )
            if health['docs_indexados'] == 0:
                st.warning('Nenhum documento indexado. Use o painel abaixo.', icon='⚠️')

        st.divider()

        # --- Indexacao ---
        st.subheader('Indexar documentos')
        st.caption(
            f'Adicione arquivos `.pdf`, `.md` ou `.txt` na pasta `{DOCS_DIR}/` '
            'e clique no botao abaixo.'
        )

        if st.button('Processar documentos', type='primary', use_container_width=True):
            with st.spinner('Carregando e indexando...'):
                idx_result = _run_indexing(chain.embedder)
                st.session_state['last_index'] = idx_result
                # Invalida cache de health para forcar nova leitura
                st.session_state.pop('health', None)

        idx = st.session_state.get('last_index')
        if idx:
            if idx['ok']:
                st.success(idx['msg'])
            else:
                st.error(idx['msg'])

            if idx.get('arquivos_com_erro'):
                with st.expander('Arquivos com erro'):
                    for f in idx['arquivos_com_erro']:
                        st.text(f"- {f['arquivo']}: {f['erro']}")

        st.divider()

        # --- Limpar conversa ---
        if st.button('Limpar conversa', use_container_width=True):
            st.session_state['messages'] = []
            st.rerun()


def render_chat(chain):
    st.header('Assistente de Estudos de IA')
    st.caption(
        'Faça perguntas sobre os documentos indexados. '
        'O assistente responde apenas com base nas suas aulas.'
    )

    # Inicializa histórico
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    # Exibe histórico
    for msg in st.session_state['messages']:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
            if msg.get('sources'):
                with st.expander('Fontes consultadas', expanded=False):
                    for src in msg['sources']:
                        st.markdown(f'- `{src}`')
                    st.caption(f"{msg.get('context_chunks', 0)} trecho(s) usados como contexto")

    # Input do usuário
    question = st.chat_input('Digite sua pergunta...')
    if not question:
        return

    # Exibe mensagem do usuário imediatamente
    st.session_state['messages'].append({'role': 'user', 'content': question})
    with st.chat_message('user'):
        st.markdown(question)

    # Gera resposta
    with st.chat_message('assistant'):
        with st.spinner('Buscando nos documentos e gerando resposta...'):
            result = chain.ask(question)

        answer  = result.get('answer', '')
        sources = result.get('sources', [])
        n_chunks = result.get('context_chunks', 0)

        st.markdown(answer)

        if sources:
            with st.expander('Fontes consultadas', expanded=False):
                for src in sources:
                    st.markdown(f'- `{src}`')
                st.caption(f'{n_chunks} trecho(s) usados como contexto')
        elif n_chunks == 0:
            st.caption('Nenhum documento relevante foi encontrado para esta pergunta.')

    # Salva no histórico
    st.session_state['messages'].append({
        'role':           'assistant',
        'content':        answer,
        'sources':        sources,
        'context_chunks': n_chunks,
    })


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title='Assistente RAG de Estudos',
        page_icon='📚',
        layout='wide',
        initial_sidebar_state='expanded',
    )

    # Inicializa recursos (cached)
    try:
        embedder = get_embedder()
    except Exception as e:
        st.error(f'Erro ao carregar modelo de embeddings: {e}')
        st.stop()

    try:
        chain = get_chain(embedder)
    except Exception as e:
        st.error(f'Erro ao inicializar a chain: {e}')
        st.stop()

    render_sidebar(chain)
    render_chat(chain)


if __name__ == '__main__':
    main()
