"""
Modulo de Carregamento de Documentos (Loader)
Le PDFs, MDs e TXTs da pasta docs/ com tratamento robusto de erros.
"""

import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentLoader:
    """Carrega e processa documentos de forma robusta e resiliente."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.txt'}
    CHUNK_SIZE = 512       # caracteres por chunk
    CHUNK_OVERLAP = 50     # caracteres de sobreposicao entre chunks
    MIN_CHUNK = 120        # secoes menores que isso (ex: so titulo da aula)
                           # nunca viram chunk proprio - sao fundidas a proxima
                           # secao. Chunks so-de-titulo pontuam alto na busca
                           # vetorial mas nao carregam informacao, roubando
                           # vagas do top-N de chunks com conteudo real.

    def __init__(self, docs_dir: str = 'docs'):
        self.docs_dir = Path(docs_dir)
        self.processed_files: List[str] = []
        self.failed_files: List[Dict] = []

        if not self.docs_dir.exists():
            logger.warning(f"Diretorio {self.docs_dir} nao existe. Criando...")
            self.docs_dir.mkdir(parents=True, exist_ok=True)

    def load_all_documents(self) -> Tuple[List[Dict], Dict]:
        """
        Carrega todos os documentos da pasta docs/.

        Returns:
            Tupla (chunks, resumo)
            - chunks: Lista de dicts com 'content', 'source', 'chunk_id'
            - resumo: Dict com info de sucesso/falhas
        """
        logger.info(f"Iniciando carregamento de documentos de '{self.docs_dir}'")

        all_chunks: List[Dict] = []
        files = self._discover_files()

        if not files:
            logger.warning(f"Nenhum documento encontrado em '{self.docs_dir}'. "
                           "Adicione arquivos .pdf, .md ou .txt para comecar.")
            return [], self._get_summary()

        logger.info(f"Encontrados {len(files)} arquivo(s) para processar")

        for file_path in files:
            try:
                rel = file_path.relative_to(self.docs_dir)
                logger.info(f"Processando: {rel}")
                chunks = self._load_file(file_path)
                all_chunks.extend(chunks)
                self.processed_files.append(str(rel))
                logger.info(f"  OK: {file_path.name} => {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"  FALHA: {file_path.name} => {e}")
                self.failed_files.append({
                    'arquivo': file_path.name,
                    'caminho': str(file_path),
                    'erro': str(e)
                })
            # Nao relanca: um arquivo com erro nao para os demais

        logger.info(
            f"Resumo: {len(all_chunks)} chunks | "
            f"{len(self.processed_files)} ok | "
            f"{len(self.failed_files)} falha(s)"
        )
        return all_chunks, self._get_summary()

    def _discover_files(self) -> List[Path]:
        """Descobre todos os documentos suportados em docs/ recursivamente."""
        files: List[Path] = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(self.docs_dir.rglob(f'*{ext}'))
        return sorted(set(files))  # set() elimina duplicatas em caso de case-insensitive FS

    def _load_file(self, file_path: Path) -> List[Dict]:
        """Carrega um arquivo individual e retorna lista de chunks."""
        ext = file_path.suffix.lower()

        if ext == '.pdf':
            content = self._load_pdf(file_path)
        elif ext in ('.md', '.txt'):
            content = self._load_text(file_path)
        else:
            raise ValueError(f"Formato nao suportado: {ext}")

        if not content or not content.strip():
            raise ValueError("Arquivo vazio ou sem texto extraivel (pode ser imagem-only)")

        return self._chunk_text(content, file_path)

    def _load_pdf(self, file_path: Path) -> str:
        """Extrai texto de PDF com tratamento de erros por pagina."""
        if PyPDF2 is None:
            raise ImportError(
                "pypdf nao esta instalado. Execute: pip install pypdf"
            )

        texts: List[str] = []
        with open(file_path, 'rb') as f:
            try:
                reader = PyPDF2.PdfReader(f)
            except Exception as e:
                raise ValueError(f"Arquivo PDF invalido ou corrompido: {e}")

            if len(reader.pages) == 0:
                raise ValueError("PDF sem paginas")

            for num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text() or ''
                    if page_text.strip():
                        texts.append(page_text)
                    else:
                        logger.warning(f"  Pagina {num} sem texto (provavel imagem)")
                except Exception as e:
                    logger.warning(f"  Pagina {num} ignorada: {e}")

        return '\n'.join(texts)

    def _load_text(self, file_path: Path) -> str:
        """Carrega TXT/MD com tentativa sequencial de encodings."""
        for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
            try:
                return file_path.read_text(encoding=encoding)
            except (UnicodeDecodeError, LookupError):
                continue

        raise ValueError(
            f"Nao foi possivel decodificar '{file_path.name}'. "
            "Salve o arquivo em UTF-8 e tente novamente."
        )

    def _chunk_text(self, text: str, file_path: Path) -> List[Dict]:
        """
        Divide texto em chunks.

        Estrategia:
        - Markdown: divide por secoes (cabecalhos #). Cada secao vira um
          chunk semanticamente concentrado - um conceito por chunk melhora
          a precisao da busca vetorial. Secoes pequenas adjacentes sao
          agrupadas; secoes maiores que CHUNK_SIZE sao subdivididas.
        - Outros formatos: divisao por caracteres com sobreposicao.
        """
        # ID unico por arquivo: usa o caminho relativo para evitar colisoes
        rel = file_path.relative_to(self.docs_dir)
        rel_path = str(rel)
        path_hash = hashlib.md5(rel_path.encode()).hexdigest()[:8]
        file_key = f"{file_path.stem}_{path_hash}"

        # Materia: primeira subpasta de docs/ (docs/<materia>/arquivo.md).
        # Arquivos na raiz de docs/ pertencem a materia 'geral'.
        materia = rel.parts[0] if len(rel.parts) > 1 else 'geral'

        text = text.strip()

        if file_path.suffix.lower() == '.md':
            units = self._split_markdown_sections(text)
        else:
            units = [text]

        # Monta pecas de ate CHUNK_SIZE: agrupa secoes pequenas,
        # subdivide secoes grandes. Buffers minusculos (< MIN_CHUNK, ex: so o
        # titulo da aula) nunca sao emitidos sozinhos - sao fundidos a
        # proxima secao, mesmo que o conjunto estoure CHUNK_SIZE
        # (nesse caso o conjunto e subdividido mantendo o titulo no inicio).
        pieces: List[str] = []
        buffer = ''
        for unit in units:
            if buffer:
                cabe = len(buffer) + len(unit) + 2 <= self.CHUNK_SIZE
                if cabe or len(buffer) < self.MIN_CHUNK:
                    unit = f"{buffer}\n\n{unit}"
                else:
                    pieces.append(buffer)
                buffer = ''
            if len(unit) > self.CHUNK_SIZE:
                pieces.extend(self._split_by_chars(unit))
            else:
                buffer = unit
        if buffer:
            pieces.append(buffer)

        # Contextualizacao: prefixa o titulo do documento em cada chunk.
        # O modelo de embeddings so enxerga o texto do chunk; sem o titulo,
        # um chunk sobre "quatro pilares estruturais" nao casa com perguntas
        # que citam "Reinforcement Learning" (nome que so aparece no titulo
        # da aula). Com o prefixo, todo chunk carrega o tema do documento.
        if file_path.suffix.lower() == '.md':
            title = next(
                (ln.strip() for ln in text.split('\n') if ln.strip().startswith('# ')),
                '',
            )
            if title:
                pieces = [p if title in p else f"{title}\n\n{p}" for p in pieces]

        return [
            {
                'content': piece,
                'source': file_path.name,
                'source_path': rel_path,
                'materia': materia,
                'chunk_id': f"{file_key}_{idx:04d}",
                'timestamp': datetime.now().isoformat(),
                'char_count': len(piece),
            }
            for idx, piece in enumerate(pieces)
        ]

    @staticmethod
    def _split_markdown_sections(text: str) -> List[str]:
        """Divide markdown em secoes, mantendo cada cabecalho com seu corpo."""
        sections: List[str] = []
        current: List[str] = []

        for line in text.split('\n'):
            if line.lstrip().startswith('#') and current:
                section = '\n'.join(current).strip()
                if section:
                    sections.append(section)
                current = [line]
            else:
                current.append(line)

        if current:
            section = '\n'.join(current).strip()
            if section:
                sections.append(section)

        return sections

    def _split_by_chars(self, text: str) -> List[str]:
        """Divide texto longo em pedacos de CHUNK_SIZE com sobreposicao."""
        pieces: List[str] = []
        start = 0
        total_len = len(text)

        while start < total_len:
            end = min(start + self.CHUNK_SIZE, total_len)

            # Evita cortar no meio de uma palavra: recua ate o ultimo espaco
            if end < total_len and not text[end].isspace():
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space

            piece = text[start:end].strip()
            if piece:
                pieces.append(piece)

            # Chegou ao fim do texto: para (evita gerar fragmentos do rabo)
            if end >= total_len:
                break

            # Avanca com sobreposicao
            next_start = end - self.CHUNK_OVERLAP
            if next_start <= start:  # garante progresso minimo
                next_start = start + 1
            start = next_start

        return pieces

    def _get_summary(self) -> Dict:
        return {
            'timestamp': datetime.now().isoformat(),
            'arquivos_processados': self.processed_files,
            'arquivos_falhados': self.failed_files,
            'total_sucesso': len(self.processed_files),
            'total_falhas': len(self.failed_files),
        }


def load_documents(docs_dir: str = 'docs') -> Tuple[List[Dict], Dict]:
    """Funcao de conveniencia para carregar documentos."""
    loader = DocumentLoader(docs_dir)
    return loader.load_all_documents()


if __name__ == '__main__':
    chunks, summary = load_documents()
    print(f"\n{'='*60}")
    print(f"Total de chunks: {len(chunks)}")
    print(f"Sucesso: {summary['total_sucesso']} | Falhas: {summary['total_falhas']}")
    if chunks:
        c = chunks[0]
        print(f"\nPrimeiro chunk:")
        print(f"  ID     : {c['chunk_id']}")
        print(f"  Fonte  : {c['source']}")
        print(f"  Chars  : {c['char_count']}")
        print(f"  Preview: {c['content'][:120]}...")
