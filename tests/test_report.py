"""Testes para o gerador de relatório."""

import pytest
from lista_trf.report import generate_markdown_report
from lista_trf.schemas import (
    AnaliseProcesso,
    RelatorioConsolidado,
    NivelAlerta,
    PrecedenteEncontrado
)


class TestGenerateReport:
    """Testes de geração de relatório."""

    def test_report_has_header(self):
        """Relatório deve ter cabeçalho correto."""
        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            gabinete="Des. Fernando Braga",
            total_processos=2,
            analises=[]
        )

        md = generate_markdown_report(relatorio)

        assert "09/12/2025" in md
        assert "4ª Turma" in md

    def test_report_has_sections(self):
        """Relatório deve ter seções por nível de alerta."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                processo_ordem=1,
                tema_central="Tema vermelho",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Divergência",
                recomendacao="Revisar"
            ),
            AnaliseProcesso(
                processo_numero="002",
                processo_ordem=2,
                tema_central="Tema verde",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="OK",
                recomendacao="Nenhuma"
            ),
        ]

        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            total_processos=2,
            analises=analises
        )

        md = generate_markdown_report(relatorio)

        assert "ATENÇÃO IMEDIATA" in md
        assert "SEM ALERTAS" in md

    def test_report_counts_correct(self):
        """Relatório deve mostrar contagens corretas."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                tema_central="T1",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="M1",
                recomendacao="R1"
            ),
            AnaliseProcesso(
                processo_numero="002",
                tema_central="T2",
                alerta=NivelAlerta.AMARELO,
                motivo_alerta="M2",
                recomendacao="R2"
            ),
            AnaliseProcesso(
                processo_numero="003",
                tema_central="T3",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="M3",
                recomendacao="R3"
            ),
        ]

        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            total_processos=3,
            analises=analises
        )

        md = generate_markdown_report(relatorio)

        assert "1 alertas vermelhos" in md or "1 alerta vermelho" in md
        assert "1 amarelo" in md
        assert "1 verde" in md
