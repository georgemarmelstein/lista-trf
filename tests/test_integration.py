"""Testes de integração do sistema de análise de listas de julgamento."""

import pytest
from pathlib import Path

from lista_trf.main import prepare_analysis, generate_analyst_prompts
from lista_trf.schemas import AnaliseProcesso, RelatorioConsolidado, NivelAlerta
from lista_trf.report import generate_markdown_report


# Caminho do documento de exemplo para testes
SAMPLE_DOC = Path(r"C:\Users\georg\lista-trf\Lista de Julgamento - GABFBD - Sessão 09.12.2025 - 4ª Turma.docx")


class TestFullExtractionFlow:
    """Testes do fluxo completo de extração."""

    def test_full_extraction_flow(self):
        """Fluxo completo de extração funciona corretamente."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        # Preparar análise
        data = prepare_analysis(str(SAMPLE_DOC))

        # Verificar que processos foram extraídos
        assert data['total_processos'] > 0, "Deve extrair pelo menos um processo"
        assert len(data['processos']) > 0, "Lista de processos não deve estar vazia"
        assert len(data['processos']) == data['total_processos'], "Contagem deve corresponder à lista"

        # Verificar metadados
        assert 'turma' in data['metadata'], "Metadados devem incluir turma"
        assert data['metadata']['turma'] is not None, "Turma não deve ser None"

        # Verificar estrutura dos processos
        for processo in data['processos']:
            assert processo.numero is not None, "Processo deve ter número"
            assert processo.ordem > 0, "Processo deve ter ordem positiva"
            assert processo.ementa is not None, "Processo deve ter ementa"


class TestGeneratePrompts:
    """Testes de geração de prompts para analistas."""

    def test_generate_prompts_for_all(self):
        """Gera prompts para todos os processos extraídos."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        # Preparar análise
        data = prepare_analysis(str(SAMPLE_DOC))

        # Gerar prompts
        prompts = generate_analyst_prompts(data['processos'])

        # Verificar que todos os processos têm prompts
        assert len(prompts) == data['total_processos'], "Deve gerar prompt para cada processo"

        # Verificar estrutura de cada prompt
        for prompt_data in prompts:
            assert 'prompt' in prompt_data, "Deve ter campo 'prompt'"
            assert 'numero' in prompt_data, "Deve ter campo 'numero'"
            assert 'ordem' in prompt_data, "Deve ter campo 'ordem'"
            assert len(prompt_data['prompt']) > 100, "Prompt deve ter conteúdo substancial"

        # Verificar que prompts contêm informações do processo
        primeiro_prompt = prompts[0]
        assert primeiro_prompt['numero'] in primeiro_prompt['prompt'], "Prompt deve conter número do processo"


class TestReportGeneration:
    """Testes de geração de relatório."""

    def test_report_generation_with_mock_analyses(self):
        """Geração de relatório com análises mock funciona corretamente."""
        # Criar análises mock com diferentes níveis de alerta
        analises = [
            AnaliseProcesso(
                processo_numero="0800307-06.2025.4.05.8103",
                processo_ordem=1,
                tema_central="Prescrição PASEP",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="Alinhado com Tema 1150/STJ",
                recomendacao="Sem necessidade de revisão"
            ),
            AnaliseProcesso(
                processo_numero="0007508-25.2015.4.05.8300",
                processo_ordem=2,
                tema_central="Honorários em embargos",
                alerta=NivelAlerta.AMARELO,
                motivo_alerta="Tema com divergência entre turmas",
                flags_sensibilidade=["divergência interna"],
                recomendacao="Verificar posição da turma"
            ),
            AnaliseProcesso(
                processo_numero="0803133-36.2024.4.05.8201",
                processo_ordem=3,
                tema_central="Licença-prêmio",
                alerta=NivelAlerta.VERMELHO,
                motivo_alerta="Diverge do Tema 1086/STJ na base de cálculo",
                recomendacao="Revisar fundamentação"
            ),
        ]

        # Criar relatório consolidado
        relatorio = RelatorioConsolidado(
            sessao="09/12/2025",
            turma="4ª Turma",
            gabinete="Des. Fernando Braga",
            total_processos=3,
            analises=analises
        )

        # Gerar markdown
        md = generate_markdown_report(relatorio)

        # Verificar cabeçalho
        assert "09/12/2025" in md, "Relatório deve conter data da sessão"
        assert "4ª Turma" in md, "Relatório deve conter turma"
        assert "Des. Fernando Braga" in md, "Relatório deve conter gabinete"

        # Verificar seções de alerta
        assert "ATENÇÃO IMEDIATA" in md, "Relatório deve ter seção de atenção imediata"
        assert "ANÁLISE RECOMENDADA" in md, "Relatório deve ter seção de análise recomendada"
        assert "SEM ALERTAS" in md, "Relatório deve ter seção sem alertas"

        # Verificar que processos aparecem nas seções corretas
        assert "0803133-36.2024.4.05.8201" in md, "Processo vermelho deve aparecer"
        assert "0007508-25.2015.4.05.8300" in md, "Processo amarelo deve aparecer"
        assert "Prescrição PASEP" in md, "Tema do processo verde deve aparecer na tabela"

        # Verificar que motivos de alerta aparecem
        assert "Diverge do Tema 1086/STJ" in md, "Motivo do alerta vermelho deve aparecer"
        assert "divergência entre turmas" in md, "Motivo do alerta amarelo deve aparecer"


class TestReportCounts:
    """Testes de contagens do relatório."""

    def test_report_counts_are_correct(self):
        """Contagens do relatório estão corretas para diferentes distribuições."""
        # Criar análises com distribuição conhecida:
        # - 2 vermelhos (índices 0, 1)
        # - 3 amarelos (índices 2, 3, 4)
        # - 5 verdes (índices 5, 6, 7, 8, 9)
        analises = []
        for i in range(10):
            if i < 2:
                alerta = NivelAlerta.VERMELHO
            elif i < 5:
                alerta = NivelAlerta.AMARELO
            else:
                alerta = NivelAlerta.VERDE

            analises.append(
                AnaliseProcesso(
                    processo_numero=f"000{i:04d}-00.0000.0.00.0000",
                    processo_ordem=i + 1,
                    tema_central=f"Tema de teste {i}",
                    alerta=alerta,
                    motivo_alerta=f"Motivo de teste {i}",
                    recomendacao=f"Recomendação {i}"
                )
            )

        # Criar relatório
        relatorio = RelatorioConsolidado(
            sessao="01/01/2026",
            turma="1ª Turma",
            gabinete="Teste",
            total_processos=10,
            analises=analises
        )

        # Verificar contagens computadas
        assert relatorio.total_vermelhos == 2, f"Esperado 2 vermelhos, obtido {relatorio.total_vermelhos}"
        assert relatorio.total_amarelos == 3, f"Esperado 3 amarelos, obtido {relatorio.total_amarelos}"
        assert relatorio.total_verdes == 5, f"Esperado 5 verdes, obtido {relatorio.total_verdes}"

        # Verificar que soma bate com total
        soma = relatorio.total_vermelhos + relatorio.total_amarelos + relatorio.total_verdes
        assert soma == 10, f"Soma das contagens ({soma}) deve ser igual ao total (10)"

        # Verificar listas filtradas
        assert len(relatorio.vermelhos) == 2, "Lista de vermelhos deve ter 2 itens"
        assert len(relatorio.amarelos) == 3, "Lista de amarelos deve ter 3 itens"
        assert len(relatorio.verdes) == 5, "Lista de verdes deve ter 5 itens"

    def test_report_counts_with_empty_categories(self):
        """Contagens funcionam corretamente quando categorias estão vazias."""
        # Apenas processos verdes
        analises = [
            AnaliseProcesso(
                processo_numero="0001",
                processo_ordem=1,
                tema_central="Tema verde",
                alerta=NivelAlerta.VERDE,
                motivo_alerta="Tudo OK",
                recomendacao="Nenhuma"
            )
        ]

        relatorio = RelatorioConsolidado(
            sessao="01/01/2026",
            turma="2ª Turma",
            total_processos=1,
            analises=analises
        )

        assert relatorio.total_vermelhos == 0, "Deve ter 0 vermelhos"
        assert relatorio.total_amarelos == 0, "Deve ter 0 amarelos"
        assert relatorio.total_verdes == 1, "Deve ter 1 verde"

        # Verificar que relatório ainda gera corretamente
        md = generate_markdown_report(relatorio)
        assert "0 alertas vermelhos" in md, "Deve indicar 0 vermelhos"
        assert "0 amarelos" in md, "Deve indicar 0 amarelos"
        assert "1 verde" in md, "Deve indicar 1 verde"


class TestEndToEndIntegration:
    """Testes de integração end-to-end completos."""

    def test_extraction_to_report_flow(self):
        """Fluxo completo: extração -> análises mock -> relatório."""
        if not SAMPLE_DOC.exists():
            pytest.skip("Documento de exemplo não encontrado")

        # Fase 1: Extração
        data = prepare_analysis(str(SAMPLE_DOC))
        assert data['total_processos'] > 0

        # Fase 2: Simular análises (em produção, seriam feitas por subagentes)
        analises = []
        for i, processo in enumerate(data['processos'][:5]):  # Limitar a 5 para o teste
            # Distribuir alertas de forma determinística para teste
            if i % 3 == 0:
                alerta = NivelAlerta.VERMELHO
            elif i % 3 == 1:
                alerta = NivelAlerta.AMARELO
            else:
                alerta = NivelAlerta.VERDE

            analises.append(
                AnaliseProcesso(
                    processo_numero=processo.numero,
                    processo_ordem=processo.ordem,
                    tema_central=f"Tema extraído do processo {processo.ordem}",
                    alerta=alerta,
                    motivo_alerta=f"Motivo de teste para processo {processo.ordem}",
                    recomendacao="Recomendação de teste"
                )
            )

        # Fase 3: Gerar relatório
        relatorio = RelatorioConsolidado(
            sessao=data['metadata'].get('sessao', 'N/A'),
            turma=data['metadata'].get('turma', 'N/A'),
            gabinete=data['metadata'].get('gabinete', ''),
            total_processos=len(analises),
            analises=analises
        )

        # Fase 4: Gerar markdown
        md = generate_markdown_report(relatorio)

        # Verificações finais
        assert len(md) > 500, "Relatório deve ter conteúdo substancial"
        assert "ATENÇÃO IMEDIATA" in md
        assert "ANÁLISE RECOMENDADA" in md
        assert "SEM ALERTAS" in md

        # Verificar que números dos processos reais aparecem
        for analise in analises:
            assert analise.processo_numero in md, f"Processo {analise.processo_numero} deve aparecer no relatório"
