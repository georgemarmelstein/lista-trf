"""
MCP Server: BNP API - Banco Nacional de Precedentes (PAGEA/CNJ)

Este servidor MCP fornece acesso ao Banco Nacional de Precedentes do CNJ,
permitindo buscar precedentes vinculantes de todos os tribunais brasileiros.

Arquitetura baseada nos padrões do anthropic-tools:
- Descrições ricas com instruções de uso
- Formatação XML estruturada
- Truncagem inteligente de conteúdo
"""

from mcp.server.fastmcp import FastMCP
import requests
from typing import Optional, List
from datetime import datetime
from tenacity import retry, wait_exponential, stop_after_attempt
import sys
from pathlib import Path

# Adicionar módulo compartilhado ao path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.base_juridica import (
    BaseResultadoJuridico,
    formatar_resultados_xml,
    truncar_por_tokens,
    TIPOS_PRECEDENTES,
)

# Criar servidor MCP
mcp = FastMCP("bnp-api")

# Configuração da API
BNP_API_URL = "https://pangeabnp.pdpj.jus.br/api/v1/precedentes"


class BNPApi:
    """Cliente da API do BNP com retry automático."""

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def buscar(self, filtro: dict) -> dict:
        """Executa busca com retry automático."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.post(
            BNP_API_URL,
            json={"filtro": filtro},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()


# Instância global do cliente
_api = BNPApi()


@mcp.tool()
def buscar_precedentes(
    busca: str,
    orgaos: str = "STF,STJ",
    tipos: str = "RG,RR,SV,SUM",
    max_resultados: int = 10
) -> str:
    """
    Busca precedentes vinculantes no Banco Nacional de Precedentes (BNP/PAGEA).
    Retorna Repercussão Geral, Recursos Repetitivos, Súmulas Vinculantes e IRDRs.

    IMPORTANTE - SINTAXE DO BNP:
    O BNP usa sintaxe DIFERENTE dos outros sistemas. NÃO use "E", "OU", "NAO" como operadores.

    OPERADORES ACEITOS:
    ┌──────────────┬─────────────────────────────────────────────────────────┐
    │ Operador     │ Descrição                                               │
    ├──────────────┼─────────────────────────────────────────────────────────┤
    │ +termo       │ Palavra OBRIGATÓRIA (equivale a AND)                    │
    │ -termo       │ Palavra EXCLUÍDA (equivale a NOT)                       │
    │ "frase"      │ Expressão EXATA entre aspas                             │
    └──────────────┴─────────────────────────────────────────────────────────┘

    ESTRATÉGIA DE BUSCA - SIGA ESTES PASSOS:
    1. Verifique se existe TEMA VINCULANTE conhecido (ex: Tema 1066, Tema 709)
       → Se sim, busque diretamente: "tema 1066"
    2. Identifique o INSTITUTO JURÍDICO central (não a pergunta inteira)
    3. Use termos TÉCNICOS, não linguagem coloquial
    4. Adicione + para termos obrigatórios
    5. Use - para excluir contextos indesejados

    EXEMPLOS DE TRANSFORMAÇÃO (pergunta → query):

    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Pergunta: "Pensão por morte para companheiro homoafetivo"               │
    │ ❌ Ruim:  pensão por morte para companheiro homoafetivo                 │
    │ ✅ Boa:   +"pensão" +"morte" +homoafetivo                               │
    │ ✅ Melhor: "pensão por morte" +homoafetivo                              │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Aposentadoria especial com uso de EPI"                       │
    │ ❌ Ruim:  aposentadoria especial com uso de EPI neutraliza              │
    │ ✅ Boa:   +"aposentadoria" +"especial" +EPI                             │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Servidor pode acumular aposentadorias?"                      │
    │ ❌ Ruim:  servidor pode acumular aposentadorias                         │
    │ ✅ Boa:   +acumulação +aposentadoria +servidor -militar                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Qual o tema do STF sobre teto previdenciário?"               │
    │ ✅ Direta: "tema 1066"                                                  │
    │ ✅ Alternativa: +teto +previdenciário +"revisão"                        │
    └─────────────────────────────────────────────────────────────────────────┘

    TERMOS TÉCNICOS - USE EM VEZ DE LINGUAGEM COLOQUIAL:
    ┌────────────────────────────┬────────────────────────────────────────────┐
    │ Coloquial                  │ Técnico                                    │
    ├────────────────────────────┼────────────────────────────────────────────┤
    │ aposentar por doença       │ aposentadoria por invalidez                │
    │ auxílio do INSS            │ benefício previdenciário                   │
    │ pensão da viúva            │ pensão por morte                           │
    │ dinheiro para deficiente   │ BPC, LOAS, benefício assistencial          │
    │ tempo de roça              │ atividade rural, segurado especial         │
    │ revisar aposentadoria      │ revisão de benefício                       │
    │ cortar benefício           │ cessação, cancelamento                     │
    └────────────────────────────┴────────────────────────────────────────────┘

    O QUE EVITAR:
    - Operadores E, OU, NAO (não funcionam nesta base)
    - Frases completas como query
    - Artigos e preposições (de, para, o, a, com)
    - Queries muito longas (máx 4-5 termos significativos)

    Args:
        busca: Query com sintaxe BNP (+termo, -termo, "frase").
               NÃO passe perguntas diretas. Use a estratégia acima.
        orgaos: Órgãos separados por vírgula. Default: "STF,STJ"
                Opções: STF, STJ, TST, TSE, STM, TRFs, TJs
        tipos: Tipos de precedente. Default: "RG,RR,SV,SUM"
               RG=Repercussão Geral, RR=Repetitivo, SV=Súmula Vinculante,
               SUM=Súmula, IRDR=Demandas Repetitivas, IAC=Assunção Competência
        max_resultados: Máximo de resultados (1-50). Default: 10

    Returns:
        XML estruturado com precedentes: número, tese, questão jurídica, situação
    """

    # Parse dos parâmetros
    lista_orgaos = [o.strip().upper() for o in orgaos.split(",")]
    lista_tipos = [t.strip().upper() for t in tipos.split(",")]

    # Montar filtro
    filtro = {
        "buscaGeral": busca,
        "todasPalavras": "",
        "quaisquerPalavras": "",
        "semPalavras": "",
        "trechoExato": "",
        "atualizacaoDesde": "",
        "atualizacaoAte": "",
        "cancelados": False,
        "ordenacao": "Text",
        "nr": "",
        "pagina": 1,
        "tamanhoPagina": min(max_resultados, 50),
        "orgaos": lista_orgaos,
        "tipos": lista_tipos
    }

    try:
        data = _api.buscar(filtro)

        # Converter para BaseResultadoJuridico
        resultados: List[BaseResultadoJuridico] = []

        for r in data.get("resultados", []):
            # Montar conteúdo principal
            conteudo_partes = []

            questao = r.get("questao", "")
            if questao:
                conteudo_partes.append(f"QUESTÃO JURÍDICA: {questao}")

            tese = r.get("tese", "")
            if tese:
                conteudo_partes.append(f"TESE: {tese}")

            # Processos paradigma
            paradigmas = r.get("processosParadigma", [])
            if paradigmas:
                procs = [p.get("numero", "") for p in paradigmas if p.get("numero")]
                if procs:
                    conteudo_partes.append(f"PROCESSOS PARADIGMA: {', '.join(procs)}")

            conteudo = "\n\n".join(conteudo_partes)
            conteudo = truncar_por_tokens(conteudo, max_tokens=2000)

            # Montar fonte (URL do primeiro paradigma ou vazio)
            fonte = ""
            if paradigmas and paradigmas[0].get("link"):
                fonte = paradigmas[0]["link"]

            resultado = BaseResultadoJuridico(
                conteudo=conteudo,
                fonte=fonte,
                tipo=TIPOS_PRECEDENTES.get(r.get("tipo"), r.get("tipo", "")),
                orgao=r.get("orgao", ""),
                numero=f"{r.get('tipo', '')} {r.get('nr', '')}",
                situacao=r.get("situacao", ""),
                data=r.get("ultimaAtualizacao", ""),
            )
            resultados.append(resultado)

        # Formatar como XML
        xml_resultado = formatar_resultados_xml(resultados, "precedentes_bnp")

        # Adicionar metadados
        meta = f'<!-- Busca: "{busca}" | Total: {data.get("total", len(resultados))} | Órgãos: {orgaos} -->\n'

        return meta + xml_resultado

    except requests.exceptions.RequestException as e:
        return f'<erro>Falha na comunicação com BNP: {str(e)}</erro>'
    except Exception as e:
        return f'<erro>Erro inesperado: {str(e)}</erro>'


@mcp.tool()
def gerar_relatorio_precedentes(
    busca: str,
    orgaos: str = "STF,STJ",
    tipos: str = "RG,RR,SV,SUM",
    max_resultados: int = 10
) -> str:
    """
    Busca precedentes e gera relatório formatado em Markdown.

    USE ESTA TOOL quando precisar de um relatório para apresentar ao usuário.
    Para análise programática, prefira buscar_precedentes que retorna XML.

    A sintaxe de busca é a MESMA de buscar_precedentes:
    - +termo para obrigatório
    - -termo para excluir
    - "frase" para expressão exata

    Args:
        busca: Query com sintaxe BNP. Veja buscar_precedentes para detalhes.
        orgaos: Órgãos separados por vírgula. Default: "STF,STJ"
        tipos: Tipos de precedente. Default: "RG,RR,SV,SUM"
        max_resultados: Máximo de resultados. Default: 10

    Returns:
        Relatório formatado em Markdown
    """

    # Parse dos parâmetros
    lista_orgaos = [o.strip().upper() for o in orgaos.split(",")]
    lista_tipos = [t.strip().upper() for t in tipos.split(",")]

    # Montar filtro
    filtro = {
        "buscaGeral": busca,
        "todasPalavras": "",
        "quaisquerPalavras": "",
        "semPalavras": "",
        "trechoExato": "",
        "atualizacaoDesde": "",
        "atualizacaoAte": "",
        "cancelados": False,
        "ordenacao": "Text",
        "nr": "",
        "pagina": 1,
        "tamanhoPagina": min(max_resultados, 50),
        "orgaos": lista_orgaos,
        "tipos": lista_tipos
    }

    try:
        data = _api.buscar(filtro)
        precedentes = data.get("resultados", [])
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        # Gerar relatório
        linhas = [
            "# Relatório de Análise de Precedentes",
            "",
            f"**Busca realizada:** `{busca}`",
            f"**Data/Hora:** {data_hora}",
            f"**Total de resultados:** {len(precedentes)}",
            "",
            "---",
            ""
        ]

        if not precedentes:
            linhas.append("*Nenhum precedente encontrado para os termos de busca.*")
            return "\n".join(linhas)

        for i, p in enumerate(precedentes, 1):
            tipo = p.get("tipo", "")
            tipo_desc = TIPOS_PRECEDENTES.get(tipo, tipo)

            linhas.extend([
                f"## {i}. {tipo} {p.get('nr', '')} ({p.get('orgao', '')})",
                "",
                f"**Tipo:** {tipo_desc}",
                f"**Situação:** {p.get('situacao', '')}",
                f"**Última atualização:** {p.get('ultimaAtualizacao', '')}",
                ""
            ])

            if p.get('questao'):
                linhas.extend([
                    "### Questão Jurídica",
                    "",
                    f"> {p['questao']}",
                    ""
                ])

            if p.get('tese'):
                linhas.extend([
                    "### Tese/Entendimento",
                    "",
                    f"> {p['tese']}",
                    ""
                ])

            paradigmas = p.get('processosParadigma', [])
            if paradigmas:
                linhas.extend([
                    "### Processos Paradigma",
                    ""
                ])
                for proc in paradigmas:
                    if proc.get('link'):
                        linhas.append(f"- [{proc.get('numero', 'Link')}]({proc['link']})")
                    else:
                        linhas.append(f"- {proc.get('numero', '')}")
                linhas.append("")

            linhas.extend(["---", ""])

        # Tabela de conferência
        linhas.extend([
            "## Metadados para Conferência",
            "",
            "| # | Tipo | Número | Órgão | Situação |",
            "|---|------|--------|-------|----------|"
        ])

        for i, p in enumerate(precedentes, 1):
            linhas.append(f"| {i} | {p.get('tipo', '')} | {p.get('nr', '')} | {p.get('orgao', '')} | {p.get('situacao', '')} |")

        linhas.extend([
            "",
            "---",
            "",
            f"*Relatório gerado via MCP BNP-API em {data_hora}*"
        ])

        return "\n".join(linhas)

    except requests.exceptions.RequestException as e:
        return f"**Erro na busca:** {str(e)}"
    except Exception as e:
        return f"**Erro inesperado:** {str(e)}"


@mcp.tool()
def listar_tipos_precedentes() -> str:
    """
    Lista todos os tipos de precedentes disponíveis para busca no BNP.

    Returns:
        XML com código e descrição de cada tipo
    """
    linhas = ['<tipos_precedentes>']
    for codigo, descricao in TIPOS_PRECEDENTES.items():
        linhas.append(f'  <tipo codigo="{codigo}">{descricao}</tipo>')
    linhas.append('</tipos_precedentes>')

    return "\n".join(linhas)


if __name__ == "__main__":
    mcp.run()
