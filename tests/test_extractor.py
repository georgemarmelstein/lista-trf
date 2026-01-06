"""Testes para o extrator de documentos Word."""

import pytest
from pathlib import Path
from lista_trf.extractor import extract_processes_from_docx, ProcessoExtraido


# Fixture com caminho do documento de exemplo
SAMPLE_DOC = Path(r"C:\Users\georg\lista-trf\Lista de Julgamento - GABFBD - Sessão 09.12.2025 - 4ª Turma.docx")


class TestExtractProcesses:
    """Testes de extração de processos."""

    def test_extract_returns_list(self):
        """Extração deve retornar lista de processos."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_extract_processo_has_required_fields(self):
        """Cada processo extraído deve ter campos obrigatórios."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)
        processo = result[0]

        assert isinstance(processo, ProcessoExtraido)
        assert processo.numero is not None
        assert processo.ementa is not None

    def test_extract_primeiro_processo_numero(self):
        """Primeiro processo deve ter número correto."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)

        assert result[0].numero == "0800307-06.2025.4.05.8103"

    def test_extract_metadata_sessao(self):
        """Deve extrair metadados da sessão."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        result = extract_processes_from_docx(SAMPLE_DOC)

        # Verifica se algum processo tem metadata
        assert result[0].metadata is not None
        assert "turma" in result[0].metadata or result[0].metadata.get("turma")
