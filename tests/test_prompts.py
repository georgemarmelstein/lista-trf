"""Testes para os templates de prompts."""

import pytest
from lista_trf.prompts import (
    build_analyst_prompt,
    build_consolidator_prompt,
    build_conversation_prompt
)
from lista_trf.schemas import Processo, AnaliseProcesso, NivelAlerta


class TestAnalystPrompt:
    """Testes do prompt do agente analista."""

    def test_prompt_contains_processo_info(self):
        """Prompt deve conter informacoes do processo."""
        processo = Processo(
            ordem=1,
            numero="0800307-06.2025.4.05.8103",
            tipo_acao="Apelacao Civel",
            ementa="ADMINISTRATIVO. PASEP. PRESCRICAO.",
            metadata={"turma": "4a Turma"}
        )

        prompt = build_analyst_prompt(processo)

        assert "0800307-06.2025.4.05.8103" in prompt
        assert "PASEP" in prompt
        assert "4a Turma" in prompt

    def test_prompt_contains_instructions(self):
        """Prompt deve conter instrucoes de analise."""
        processo = Processo(
            ordem=1,
            numero="001",
            ementa="TESTE"
        )

        prompt = build_analyst_prompt(processo)

        assert "BNP" in prompt or "precedentes" in prompt.lower()
        assert "JULIA" in prompt or "TRF5" in prompt
        assert "alerta" in prompt.lower()

    def test_prompt_contains_three_phases(self):
        """Prompt deve conter as 3 fases: Classificacao, Pesquisa, Comparacao."""
        processo = Processo(
            ordem=1,
            numero="001",
            ementa="TESTE"
        )

        prompt = build_analyst_prompt(processo)

        assert "Classificacao" in prompt or "CLASSIFICACAO" in prompt or "classificacao" in prompt
        assert "Pesquisa" in prompt or "PESQUISA" in prompt
        assert "Comparacao" in prompt or "Comparativa" in prompt or "COMPARATIVA" in prompt

    def test_prompt_contains_mcp_tools(self):
        """Prompt deve conter instrucoes sobre ferramentas MCP."""
        processo = Processo(
            ordem=1,
            numero="001",
            ementa="TESTE"
        )

        prompt = build_analyst_prompt(processo)

        assert "mcp__bnp-api__buscar_precedentes" in prompt
        assert "mcp__julia-trf5__buscar_julia" in prompt
        assert "mcp__cjf-jurisprudencia__buscar_jurisprudencia_cjf" in prompt

    def test_prompt_contains_alert_levels(self):
        """Prompt deve explicar os niveis de alerta."""
        processo = Processo(
            ordem=1,
            numero="001",
            ementa="TESTE"
        )

        prompt = build_analyst_prompt(processo)

        assert "VERMELHO" in prompt or "vermelho" in prompt
        assert "AMARELO" in prompt or "amarelo" in prompt
        assert "VERDE" in prompt or "verde" in prompt


class TestConsolidatorPrompt:
    """Testes do prompt do agente consolidador."""

    def test_prompt_contains_analyses(self):
        """Prompt deve conter analises para consolidar."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                tema_central="Tema teste",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Divergencia",
                recomendacao="Revisar"
            )
        ]

        prompt = build_consolidator_prompt(
            analises=analises,
            metadata={"turma": "4a Turma", "sessao": "09/12/2025"}
        )

        assert "001" in prompt
        assert "vermelho" in prompt.lower() or "VERMELHO" in prompt

    def test_prompt_contains_metadata(self):
        """Prompt deve conter metadados da sessao."""
        analises = [
            AnaliseProcesso(
                processo_numero="001",
                tema_central="Tema teste",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="OK",
                recomendacao="Nenhuma"
            )
        ]

        prompt = build_consolidator_prompt(
            analises=analises,
            metadata={"turma": "4a Turma", "sessao": "09/12/2025", "gabinete": "Des. Teste"}
        )

        assert "4a Turma" in prompt
        assert "09/12/2025" in prompt

    def test_prompt_contains_report_format(self):
        """Prompt deve conter formato do relatorio."""
        analises = []

        prompt = build_consolidator_prompt(
            analises=analises,
            metadata={"turma": "1a Turma", "sessao": "01/01/2026"}
        )

        assert "Markdown" in prompt or "markdown" in prompt
        assert "ATENCAO" in prompt or "Atencao" in prompt or "vermelhos" in prompt.lower()


class TestConversationPrompt:
    """Testes do prompt do modo conversa."""

    def test_prompt_contains_question(self):
        """Prompt deve conter a pergunta do usuario."""
        pergunta = "Qual o status do processo 001?"
        contexto = {
            "sessao": "09/12/2025",
            "turma": "4a Turma",
            "processos": []
        }

        prompt = build_conversation_prompt(pergunta, contexto)

        assert "Qual o status do processo 001?" in prompt

    def test_prompt_contains_session_context(self):
        """Prompt deve conter contexto da sessao."""
        pergunta = "Detalhe o processo vermelho"
        contexto = {
            "sessao": "09/12/2025",
            "turma": "4a Turma",
            "processos": [
                {"ordem": 1, "numero": "001", "tema_central": "PASEP", "alerta": "vermelho"}
            ]
        }

        prompt = build_conversation_prompt(pergunta, contexto)

        assert "09/12/2025" in prompt
        assert "4a Turma" in prompt

    def test_prompt_mentions_mcp_capabilities(self):
        """Prompt deve mencionar capacidade de usar ferramentas MCP."""
        pergunta = "Pesquise mais sobre esse tema"
        contexto = {
            "sessao": "09/12/2025",
            "turma": "4a Turma",
            "processos": []
        }

        prompt = build_conversation_prompt(pergunta, contexto)

        assert "MCP" in prompt or "pesquisa" in prompt.lower() or "BNP" in prompt or "JULIA" in prompt
