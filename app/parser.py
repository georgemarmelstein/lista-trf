"""
Parser para extracao de processos de listas de julgamento.
Suporta DOCX, PDF e TXT.
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Processo:
    """Representa um processo extraido da lista."""
    numero: str
    tipo: str
    partes: str
    ementa: str
    ordem: int


def extrair_texto_docx(caminho: Path) -> str:
    """Extrai texto de arquivo DOCX."""
    try:
        from docx import Document
        doc = Document(str(caminho))

        paragrafos = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragrafos.append(para.text)

        # Tambem extrair texto de tabelas
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragrafos.append(cell.text)

        return "\n".join(paragrafos)
    except ImportError:
        raise Exception("Biblioteca python-docx nao instalada. Execute: pip install python-docx")


def extrair_texto_pdf(caminho: Path) -> str:
    """Extrai texto de arquivo PDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(caminho))
        texto = ""
        for page in doc:
            texto += page.get_text()
        doc.close()
        return texto
    except ImportError:
        raise Exception("Biblioteca PyMuPDF nao instalada. Execute: pip install pymupdf")


def extrair_texto_arquivo(caminho: Path) -> str:
    """Extrai texto de arquivo baseado na extensao."""
    extensao = caminho.suffix.lower()

    if extensao == ".docx":
        return extrair_texto_docx(caminho)
    elif extensao == ".pdf":
        return extrair_texto_pdf(caminho)
    elif extensao in [".txt", ".md"]:
        return caminho.read_text(encoding="utf-8")
    else:
        raise Exception(f"Formato nao suportado: {extensao}")


def limpar_texto(texto: str) -> str:
    """Remove caracteres problematicos e normaliza o texto."""
    # Substituir caracteres mal codificados
    replacements = {
        "�": "a",
        "\x00": "",
    }
    for old, new in replacements.items():
        texto = texto.replace(old, new)

    return texto


def extrair_processos(texto: str) -> List[Processo]:
    """
    Extrai processos do texto da lista de julgamento.

    Padrao esperado:
    1 - 0800307-06.2025.4.05.8103 - APELACAO CIVEL
    ...
    EMENTA
    ...texto da ementa...

    2 - 0007508-25.2015.4.05.8300 - APELACAO CIVEL
    ...
    """
    texto = limpar_texto(texto)
    processos = []

    # Padrao para identificar inicio de processo
    # Numero sequencial + numero CNJ + tipo
    padrao_processo = re.compile(
        r'(\d+)\s*[-–]\s*(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\s*[-–]\s*([A-ZAAOAAAAEEIOOOOUUUUÇ\s/]+?)(?=\n|PODER)',
        re.IGNORECASE
    )

    # Encontrar todas as ocorrencias
    matches = list(padrao_processo.finditer(texto))

    for i, match in enumerate(matches):
        ordem = int(match.group(1))
        numero = match.group(2).strip()
        tipo = match.group(3).strip()

        # Determinar onde termina este processo (inicio do proximo ou fim do texto)
        inicio = match.end()
        if i + 1 < len(matches):
            fim = matches[i + 1].start()
        else:
            fim = len(texto)

        conteudo = texto[inicio:fim]

        # Extrair ementa
        ementa = extrair_ementa(conteudo)

        # Extrair partes (texto antes da ementa)
        partes = extrair_partes(conteudo)

        processos.append(Processo(
            numero=numero,
            tipo=tipo,
            partes=partes,
            ementa=ementa,
            ordem=ordem
        ))

    return processos


def extrair_ementa(conteudo: str) -> str:
    """Extrai o texto da ementa do conteudo do processo."""
    # Procurar por "EMENTA" e pegar o texto apos
    padrao = re.compile(r'EMENTA\s*\n(.*?)(?=\d+\s*[-–]\s*\d{7}|$)', re.DOTALL | re.IGNORECASE)
    match = padrao.search(conteudo)

    if match:
        ementa = match.group(1).strip()
        # Limpar linhas vazias excessivas
        ementa = re.sub(r'\n{3,}', '\n\n', ementa)
        return ementa

    # Se nao encontrar marcador EMENTA, pegar todo o conteudo apos as partes
    linhas = conteudo.split('\n')
    ementa_linhas = []
    iniciou = False

    for linha in linhas:
        # Pular linhas de partes/advogados
        if any(x in linha.upper() for x in ['APELANTE:', 'APELADO:', 'ADVOGADO', 'AUTOR:', 'REU:', 'REU:']):
            continue
        if linha.strip():
            iniciou = True
        if iniciou:
            ementa_linhas.append(linha)

    return '\n'.join(ementa_linhas).strip()


def extrair_partes(conteudo: str) -> str:
    """Extrai informacoes das partes do processo."""
    linhas = []

    for linha in conteudo.split('\n'):
        linha_upper = linha.upper()
        if any(x in linha_upper for x in ['APELANTE', 'APELADO', 'AUTOR', 'REU', 'REU', 'ADVOGADO', 'IMPETRANTE', 'IMPETRADO']):
            linhas.append(linha.strip())
        if 'EMENTA' in linha_upper:
            break

    return '\n'.join(linhas)


def extrair_tema(ementa: str) -> str:
    """Extrai um tema resumido da ementa."""
    # Pegar as primeiras palavras-chave da ementa (geralmente em maiusculas)
    # Padrao: "ADMINISTRATIVO. PASEP. PRESCRICAO."

    linhas = ementa.split('\n')
    for linha in linhas:
        linha = linha.strip()
        if linha and not linha.startswith('Trata-se'):
            # Pegar primeira linha que geralmente tem os temas
            # Limitar a 50 caracteres
            temas = linha[:80]
            # Cortar no ultimo ponto se passar
            if '.' in temas:
                partes = temas.split('.')
                if len(partes) > 2:
                    temas = '.'.join(partes[:3]) + '.'
            return temas

    return ""


def processar_arquivo(caminho: str) -> List[Dict[str, Any]]:
    """
    Processa um arquivo de lista e retorna os processos extraidos.

    Args:
        caminho: Caminho do arquivo (DOCX, PDF ou TXT)

    Returns:
        Lista de dicts com dados dos processos
    """
    path = Path(caminho)

    if not path.exists():
        raise Exception(f"Arquivo nao encontrado: {caminho}")

    texto = extrair_texto_arquivo(path)
    processos = extrair_processos(texto)

    return [
        {
            "numero": p.numero,
            "tipo": p.tipo,
            "partes": p.partes,
            "ementa": p.ementa,
            "ordem": p.ordem,
            "tema": extrair_tema(p.ementa),
        }
        for p in processos
    ]


def processar_texto(texto: str) -> List[Dict[str, Any]]:
    """
    Processa texto colado diretamente.

    Args:
        texto: Texto da lista de julgamento

    Returns:
        Lista de dicts com dados dos processos
    """
    processos = extrair_processos(texto)

    return [
        {
            "numero": p.numero,
            "tipo": p.tipo,
            "partes": p.partes,
            "ementa": p.ementa,
            "ordem": p.ordem,
            "tema": extrair_tema(p.ementa),
        }
        for p in processos
    ]
