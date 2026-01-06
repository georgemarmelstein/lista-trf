"""Testes para os esquemas de dados."""

import pytest
from lista_trf.schemas import (
    Processo,
    PrecedenteEncontrado,
    AnaliseProcesso,
    NivelAlerta,
    RelatorioConsolidado
)


class TestProcesso:
    """Testes do schema Processo."""

    def test_processo_criacao_minima(self):
        """Processo pode ser criado com campos mínimos."""
        p = Processo(
            ordem=1,
            numero="0800307-06.2025.4.05.8103",
            ementa="ADMINISTRATIVO. PASEP."
        )
        assert p.numero == "0800307-06.2025.4.05.8103"

    def test_processo_campos_opcionais(self):
        """Campos opcionais têm valores padrão."""
        p = Processo(
            ordem=1,
            numero="0800307-06.2025.4.05.8103",
            ementa="EMENTA"
        )
        assert p.tipo_acao is None
        assert p.partes == {}
        assert p.metadata == {}


class TestAnaliseProcesso:
    """Testes do schema AnaliseProcesso."""

    def test_analise_criacao(self):
        """AnaliseProcesso pode ser criada."""
        analise = AnaliseProcesso(
            processo_numero="0800307-06.2025.4.05.8103",
            tema_central="Prescrição PASEP",
            alerta=NivelAlerta.VERDE,
            motivo_alerta="Alinhado com jurisprudência",
            recomendacao="Sem necessidade de revisão"
        )
        assert analise.alerta == NivelAlerta.VERDE

    def test_nivel_alerta_valores(self):
        """NivelAlerta tem valores corretos."""
        assert NivelAlerta.VERMELHO.value == "vermelho"
        assert NivelAlerta.AMARELO.value == "amarelo"
        assert NivelAlerta.VERDE.value == "verde"


class TestRelatorioConsolidado:
    """Testes do schema RelatorioConsolidado."""

    def test_relatorio_contagem(self):
        """Relatório calcula contagens corretamente."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                tema_central="Tema 1",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Divergência",
                recomendacao="Revisar"
            ),
            AnaliseProcesso(
                processo_numero="002",
                tema_central="Tema 2",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="OK",
                recomendacao="Nenhuma"
            ),
        ]

        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            gabinete="Des. Fernando Braga",
            total_processos=2,
            analises=analises
        )

        assert relatorio.total_vermelhos == 1
        assert relatorio.total_amarelos == 0
        assert relatorio.total_verdes == 1
