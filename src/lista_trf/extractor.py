"""Extrator de processos de documentos Word (listas de julgamento)."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from docx import Document


@dataclass
class ProcessoExtraido:
    """Processo extraído do documento."""

    ordem: int
    numero: str
    tipo_acao: Optional[str] = None
    partes: dict = field(default_factory=dict)
    ementa: str = ""
    metadata: dict = field(default_factory=dict)


def extract_processes_from_docx(file_path: Path) -> list[ProcessoExtraido]:
    """
    Extrai processos de um documento Word de lista de julgamento.

    Args:
        file_path: Caminho para o arquivo .docx

    Returns:
        Lista de ProcessoExtraido
    """
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # Extrair metadados do cabeçalho
    metadata = _extract_metadata(paragraphs)

    # Identificar e extrair cada processo
    processes = _extract_processes(paragraphs, metadata)

    return processes


def _extract_metadata(paragraphs: list[str]) -> dict:
    """Extrai metadados do cabeçalho do documento."""
    metadata = {}

    for p in paragraphs[:5]:  # Cabeçalho geralmente nas primeiras linhas
        p_upper = p.upper()

        # Turma
        turma_match = re.search(r'(\d+)[ªª]?\s*TURMA', p_upper)
        if turma_match:
            metadata["turma"] = f"{turma_match.group(1)}ª Turma"

        # Sessão
        sessao_match = re.search(r'SESS[ÃA]O[^:]*:\s*(\d{2}/\d{2}/\d{4})', p_upper)
        if sessao_match:
            metadata["sessao"] = sessao_match.group(1)

        # Gabinete
        gab_match = re.search(r'GAB[^\-]*-?\s*(DES\.?\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ\s]+)', p, re.IGNORECASE)
        if gab_match:
            metadata["gabinete"] = gab_match.group(1).strip()

    return metadata


def _extract_processes(paragraphs: list[str], metadata: dict) -> list[ProcessoExtraido]:
    """Extrai lista de processos do documento."""
    processes = []
    current_process = None
    current_text = []
    ordem = 0

    # Padrão para identificar início de novo processo
    # Ex: "1 - 0800307-06.2025.4.05.8103 - APELAÇÃO CÍVEL"
    process_pattern = re.compile(
        r'^(\d+)\s*-\s*(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\s*-\s*(.+)$'
    )

    # Padrão alternativo (número CNJ em linha separada)
    cnj_pattern = re.compile(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})')

    in_ementa = False

    for p in paragraphs:
        # Verificar se é início de novo processo
        match = process_pattern.match(p)

        if match:
            # Salvar processo anterior se existir
            if current_process:
                current_process.ementa = _clean_ementa('\n'.join(current_text))
                processes.append(current_process)

            # Iniciar novo processo
            ordem = int(match.group(1))
            numero = match.group(2)
            tipo_acao = match.group(3).strip()

            current_process = ProcessoExtraido(
                ordem=ordem,
                numero=numero,
                tipo_acao=tipo_acao,
                metadata=metadata.copy()
            )
            current_text = []
            in_ementa = False
            continue

        # Se estamos em um processo, acumular texto
        if current_process:
            # Detectar seção de partes
            if 'APELANTE:' in p.upper() or 'APELADO:' in p.upper():
                _extract_partes(p, current_process)

            # Detectar início da ementa
            if p.upper().strip() == 'EMENTA':
                in_ementa = True
                continue

            # Acumular texto da ementa
            if in_ementa:
                current_text.append(p)

    # Não esquecer o último processo
    if current_process:
        current_process.ementa = _clean_ementa('\n'.join(current_text))
        processes.append(current_process)

    return processes


def _extract_partes(text: str, processo: ProcessoExtraido):
    """Extrai informações das partes do processo."""
    text_upper = text.upper()

    if 'APELANTE:' in text_upper:
        match = re.search(r'APELANTE:\s*(.+?)(?=APELADO|ADVOGADO|$)', text, re.IGNORECASE)
        if match:
            processo.partes['apelante'] = match.group(1).strip()

    if 'APELADO:' in text_upper:
        match = re.search(r'APELADO:\s*(.+?)(?=ADVOGADO|$)', text, re.IGNORECASE)
        if match:
            processo.partes['apelado'] = match.group(1).strip()


def _clean_ementa(text: str) -> str:
    """Limpa e normaliza o texto da ementa."""
    # Remover linhas vazias duplicadas
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]

    # Juntar em texto único
    return '\n'.join(lines)
