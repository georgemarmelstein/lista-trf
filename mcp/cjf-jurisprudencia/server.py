"""
MCP Server: CJF Jurisprudência Unificada

Acesso à jurisprudência unificada do Conselho da Justiça Federal.
Inclui decisões de: STF, STJ, TRF1, TRF2, TRF3, TRF4, TRF5, TRF6.

Arquitetura baseada nos padrões do anthropic-tools:
- Descrições ricas com instruções de uso
- Formatação XML estruturada
- Retry com backoff exponencial
"""

from mcp.server.fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
import html
from tenacity import retry, wait_exponential, stop_after_attempt
import sys
from pathlib import Path

# Adicionar módulo compartilhado ao path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.base_juridica import (
    BaseResultadoJuridico,
    formatar_resultados_xml,
    truncar_por_tokens,
    limpar_texto_html,
    TRIBUNAIS,
)

# Criar servidor MCP
mcp = FastMCP("cjf-jurisprudencia")

# Configuração
CJF_URL = "https://jurisprudencia.cjf.jus.br/unificada/index.xhtml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/xml, text/xml, */*; q=0.01",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Faces-Request": "partial/ajax",
    "X-Requested-With": "XMLHttpRequest"
}


class CJFSession:
    """Gerencia sessão com o portal CJF."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": HEADERS["User-Agent"],
            "Accept-Language": HEADERS["Accept-Language"]
        })
        self.viewstate = None

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def obter_viewstate(self) -> str:
        """Obtém ViewState da página inicial."""
        resp = self.session.get(CJF_URL, timeout=30)
        resp.raise_for_status()

        match = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', resp.text)
        if match:
            self.viewstate = match.group(1)
            return self.viewstate

        match = re.search(r'ViewState:([^"]+)"', resp.text)
        if match:
            self.viewstate = match.group(1)
            return self.viewstate

        raise ValueError("ViewState não encontrado na página")

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def buscar(self, termo: str, tribunais: List[str]) -> str:
        """Faz busca e retorna HTML dos resultados."""
        if not self.viewstate:
            self.obter_viewstate()

        form_data = []
        form_data.append(("javax.faces.partial.ajax", "true"))
        form_data.append(("javax.faces.source", "formulario:actPesquisar"))
        form_data.append(("javax.faces.partial.execute", "@all"))
        form_data.append(("javax.faces.partial.render", "formulario:resultado"))
        form_data.append(("formulario:actPesquisar", "formulario:actPesquisar"))
        form_data.append(("formulario", "formulario"))
        form_data.append(("formulario:textoLivre", termo))

        for trib in tribunais:
            form_data.append(("formulario:j_idt51", trib))

        form_data.append(("javax.faces.ViewState", self.viewstate))

        resp = self.session.post(
            CJF_URL,
            data=form_data,
            headers=HEADERS,
            timeout=60
        )
        resp.raise_for_status()
        return resp.text


def extrair_totais(html_content: str) -> Dict[str, int]:
    """Extrai totais de documentos por tribunal."""
    totais = {}
    pattern = r'<td[^>]*>(\w+)</td>\s*<td[^>]*>.*?(\d+)\s*Documento'
    matches = re.findall(pattern, html_content, re.DOTALL)

    for tribunal, count in matches:
        if tribunal in TRIBUNAIS:
            totais[tribunal] = int(count)

    return totais


def extrair_documentos(html_content: str) -> List[Dict[str, Any]]:
    """Extrai documentos detalhados da resposta."""
    documentos = []
    content = html.unescape(html_content)

    cdata_matches = re.findall(r'<!\[CDATA\[(.*?)\]\]>', content, re.DOTALL)
    if cdata_matches:
        content = ''.join(cdata_matches)

    doc_indices = set(re.findall(r'tabelaDocumentos:(\d+):', content))

    for idx in sorted(doc_indices, key=int):
        doc = {"indice": int(idx)}

        # Extrair campos
        campos = [
            ("numero", "Número"),
            ("classe", "Classe"),
            ("relator", r"Relator\(a\)"),
            ("orgao_julgador", "Órgão julgador"),
            ("data_julgamento", "Data"),
            ("data_publicacao", "Data da publicação"),
            ("fonte_publicacao", "Fonte da publicação"),
        ]

        for campo, label in campos:
            pattern = rf'tabelaDocumentos:{idx}:.*?label_pontilhada[^>]*>{label}</span>.*?<td[^>]*>([^<]+)</td>'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                doc[campo] = match.group(1).strip()

        # Decisão (pode ter tags internas)
        decisao_match = re.search(
            rf'tabelaDocumentos:{idx}:.*?label_pontilhada[^>]*>Decisão</span>.*?<td[^>]*>\s*([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*?)\s*</td>',
            content, re.DOTALL
        )
        if decisao_match:
            decisao = decisao_match.group(1)
            decisao = re.sub(r'<[^>]+>', '', decisao).strip()
            decisao = re.sub(r'\s+', ' ', decisao)
            doc["decisao"] = decisao

        documentos.append(doc)

    # Extrair ementas
    ementa_pattern = re.compile(r'painel_ementa-([^"]+)"[^>]*>(.*?)</div>', re.DOTALL)
    ementas = []
    for match in ementa_pattern.finditer(content):
        ementa_raw = match.group(2)
        ementa = re.sub(r'<[^>]+>', '', ementa_raw).strip()
        ementa = re.sub(r'\s+', ' ', ementa)
        if len(ementa) > 50:
            ementas.append(ementa)

    # Associar ementas
    for i, doc in enumerate(documentos):
        if i < len(ementas):
            doc["ementa"] = ementas[i]

    return [d for d in documentos if d.get("numero") or d.get("ementa")]


@mcp.tool()
def buscar_jurisprudencia_cjf(
    busca: str,
    tribunais: str = "STF,STJ,TRF1,TRF2,TRF3,TRF4,TRF5,TRF6",
    max_resultados: int = 30
) -> str:
    """
    Busca jurisprudência unificada no portal do CJF (Conselho da Justiça Federal).
    Esta é a base MAIS PODEROSA - inclui STF, STJ e todos os TRFs com operadores avançados.

    IMPORTANTE - SINTAXE DO CJF:
    O CJF usa operadores em PORTUGUÊS e MAIÚSCULO. Diferente das outras bases!

    OPERADORES BOOLEANOS (sempre MAIÚSCULO):
    ┌──────────┬────────────────────────────────┬──────────────────────────────────┐
    │ Operador │ Descrição                      │ Exemplo                          │
    ├──────────┼────────────────────────────────┼──────────────────────────────────┤
    │ E        │ Ambos termos obrigatórios      │ pensão E morte                   │
    │ OU       │ Qualquer um dos termos         │ aposentadoria OU benefício       │
    │ NAO      │ Exclui o segundo termo         │ servidor NAO militar             │
    │ XOU      │ Um ou outro, não ambos         │ pensão XOU aposentadoria         │
    └──────────┴────────────────────────────────┴──────────────────────────────────┘

    OPERADORES DE PROXIMIDADE (muito úteis!):
    ┌────────────┬────────────────────────────────┬────────────────────────────────┐
    │ Operador   │ Descrição                      │ Exemplo                        │
    ├────────────┼────────────────────────────────┼────────────────────────────────┤
    │ ADJ[n]     │ Adjacentes NA ordem, até n     │ Repartição ADJ Pública         │
    │ PROX[n]    │ Próximos QUALQUER ordem, até n │ aposentadoria PROX3 invalidez  │
    │ COM        │ Na mesma SENTENÇA              │ pensão COM dependente          │
    │ MESMO      │ No mesmo PARÁGRAFO             │ benefício MESMO previdenciário │
    └────────────┴────────────────────────────────┴────────────────────────────────┘

    OPERADORES DE NEGAÇÃO COMPOSTOS:
    - NAO ADJ[n]  → Não adjacente
    - NAO PROX[n] → Não próximo
    - NAO COM     → Não na mesma sentença
    - NAO MESMO   → Não no mesmo parágrafo

    BUSCA POR CAMPO ESPECÍFICO (recurso exclusivo do CJF):
    Sintaxe: termo[CAMPO] ou (expressão)[CAMPO]

    ┌───────┬────────────────────────┬─────────────────────────────────────────┐
    │ Campo │ Descrição              │ Exemplo                                 │
    ├───────┼────────────────────────┼─────────────────────────────────────────┤
    │ EMEN  │ Ementa                 │ aposentadoria[EMEN]                     │
    │ DECI  │ Decisão                │ procedente[DECI]                        │
    │ REL   │ Relator                │ Silva[REL]                              │
    │ TRIB  │ Tribunal               │ STJ[TRIB]                               │
    │ ORGA  │ Órgão julgador         │ "primeira turma"[ORGA]                  │
    │ REFL  │ Legislação citada      │ Lei-8112[REFL]                          │
    │ INDE  │ Indexação              │ previdenciário[INDE]                    │
    │ ITEO  │ Inteiro teor           │ "dano moral"[ITEO]                      │
    │ DTDP  │ Data da decisão        │ 20240315[DTDP]                          │
    │ DTPP  │ Data da publicação     │ 202401$[DTPP]                           │
    └───────┴────────────────────────┴─────────────────────────────────────────┘

    WILDCARDS:
    ┌──────────┬────────────────────────────────┬──────────────────────────────────┐
    │ Operador │ Descrição                      │ Exemplo                          │
    ├──────────┼────────────────────────────────┼──────────────────────────────────┤
    │ $        │ Qualquer sufixo                │ aposentad$ → aposentadoria, etc  │
    │ $[n]     │ Máximo n caracteres            │ A$3Z → máx 5 chars               │
    │ ?        │ Exatamente 1 caractere         │ MA?? → MAIO, MAPA, MATA          │
    └──────────┴────────────────────────────────┴──────────────────────────────────┘

    ESTRATÉGIA DE BUSCA - SIGA ESTES PASSOS:
    1. Identifique o INSTITUTO JURÍDICO central
    2. Escolha o CAMPO mais relevante ([EMEN] para ementas, [INDE] para indexação)
    3. Liste SINÔNIMOS e conecte com OU
    4. Adicione QUALIFICADORES com E
    5. Use PROX/ADJ quando a relação entre termos importa

    EXEMPLOS DE TRANSFORMAÇÃO (pergunta → query):

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ Pergunta: "Pensão por morte para companheiro homoafetivo"                   │
    │ ❌ Ruim: pensão por morte para companheiro homoafetivo                      │
    │ ✅ Boa:  (pensão E morte)[EMEN] E (homoafetivo OU "mesmo sexo")[EMEN]       │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "O INSS pode negar auxílio-doença sem perícia?"                   │
    │ ❌ Ruim: INSS pode negar auxílio-doença sem perícia                         │
    │ ✅ Boa:  "auxílio-doença"[EMEN] E (cessação OU indeferimento) E perícia     │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Jurisprudência do Ministro Fux sobre previdenciário"             │
    │ ✅ Boa:  Fux[REL] E previdenciário[INDE]                                    │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Decisões de 2024 sobre BPC"                                      │
    │ ✅ Boa:  (BPC OU LOAS)[EMEN] E 2024$[DTDP]                                  │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Aposentadoria especial e uso de EPI"                             │
    │ ✅ Boa:  "aposentadoria especial"[EMEN] E EPI PROX3 neutralização           │
    └─────────────────────────────────────────────────────────────────────────────┘

    REGRAS IMPORTANTES:
    - NÃO usar: preposições, conjunções, artigos (de, para, o, a, que, com)
    - NÃO usar: sinais de pontuação (exceto aspas para frase exata)
    - Case INSENSITIVE: maiúsculas = minúsculas nos termos
    - Acentos IGNORADOS: aposentadoria = aposentadória

    DICA - PRIORIDADE DE TRIBUNAIS:
    - STF: Questões constitucionais, repercussão geral
    - STJ: Uniformização de lei federal, repetitivos
    - TRF4: Referência em direito previdenciário
    - TRF1: Grande volume, Brasília
    - TRF3: São Paulo, grande volume

    Args:
        busca: Query com sintaxe CJF (operadores MAIÚSCULOS, campos [EMEN], etc).
               NÃO passe perguntas diretas. Use a estratégia acima.
        tribunais: Tribunais separados por vírgula. Default: todos
                   Opções: STF, STJ, TRF1, TRF2, TRF3, TRF4, TRF5, TRF6
        max_resultados: Máximo de resultados (1-100). Default: 30

    Returns:
        XML estruturado com documentos: ementa, relator, órgão julgador, data
    """

    lista_tribunais = [t.strip().upper() for t in tribunais.split(",")]

    try:
        session = CJFSession()
        html_resultado = session.buscar(busca, lista_tribunais)

        totais = extrair_totais(html_resultado)
        documentos = extrair_documentos(html_resultado)[:max_resultados]

        # Converter para BaseResultadoJuridico
        resultados: List[BaseResultadoJuridico] = []

        for doc in documentos:
            ementa = doc.get("ementa", "")
            ementa = truncar_por_tokens(ementa, max_tokens=1500)

            resultado = BaseResultadoJuridico(
                conteudo=ementa,
                fonte="",
                tipo=doc.get("classe", ""),
                orgao=doc.get("tribunal", ""),
                numero=doc.get("numero", ""),
                relator=doc.get("relator", ""),
                data=doc.get("data_julgamento", ""),
            )
            resultados.append(resultado)

        # Formatar como XML
        xml_resultado = formatar_resultados_xml(resultados, "jurisprudencia_cjf")

        # Adicionar metadados
        totais_str = ", ".join([f"{k}:{v}" for k, v in totais.items()])
        meta = f'<!-- Busca: "{busca}" | Totais: {totais_str} -->\n'

        return meta + xml_resultado

    except Exception as e:
        return f'<erro>Falha na busca CJF: {str(e)}</erro>'


@mcp.tool()
def gerar_relatorio_cjf(
    busca: str,
    tribunais: str = "STF,STJ,TRF1,TRF2,TRF3,TRF4,TRF5,TRF6",
    max_resultados: int = 10
) -> str:
    """
    Busca jurisprudência no CJF e gera relatório com ementas completas.

    USE ESTA TOOL quando precisar de um relatório formatado para apresentar.
    Para análise programática, prefira buscar_jurisprudencia_cjf que retorna XML.

    A sintaxe é a MESMA de buscar_jurisprudencia_cjf:
    - Operadores MAIÚSCULOS: E, OU, NAO, ADJ, PROX, COM, MESMO
    - Campos específicos: termo[EMEN], termo[REL], etc
    - Wildcards: termo$, termo?

    Args:
        busca: Query com sintaxe CJF. Veja buscar_jurisprudencia_cjf para detalhes.
        tribunais: Tribunais separados por vírgula
        max_resultados: Máximo de resultados

    Returns:
        Relatório em Markdown com ementas e metadados
    """

    lista_tribunais = [t.strip().upper() for t in tribunais.split(",")]

    try:
        session = CJFSession()
        html_resultado = session.buscar(busca, lista_tribunais)

        totais = extrair_totais(html_resultado)
        documentos = extrair_documentos(html_resultado)[:max_resultados]
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        linhas = [
            "# Relatório de Jurisprudência - CJF",
            "",
            f"**Busca realizada:** `{busca}`",
            f"**Data/Hora:** {data_hora}",
            f"**Documentos extraídos:** {len(documentos)}",
            ""
        ]

        if totais:
            linhas.extend([
                "## Totais por Tribunal",
                "",
                "| Tribunal | Documentos |",
                "|----------|------------|"
            ])
            for trib, count in sorted(totais.items()):
                linhas.append(f"| {trib} | {count} |")
            linhas.append("")

        linhas.extend(["---", ""])

        if not documentos:
            linhas.append("*Nenhum documento encontrado ou erro na extração.*")
            return "\n".join(linhas)

        for i, doc in enumerate(documentos, 1):
            numero = doc.get("numero", "N/I")
            classe = doc.get("classe", "")
            relator = doc.get("relator", "N/I")
            orgao = doc.get("orgao_julgador", "")
            data = doc.get("data_julgamento", "N/I")

            linhas.extend([
                f"## {i}. {numero}",
                ""
            ])

            if classe:
                linhas.append(f"**Classe:** {classe}")
            linhas.append(f"**Relator:** {relator}")
            if orgao:
                linhas.append(f"**Órgão Julgador:** {orgao}")
            linhas.append(f"**Data:** {data}")
            linhas.append("")

            ementa = doc.get("ementa", "")
            if ementa:
                linhas.extend([
                    "### Ementa",
                    "",
                    f"> {ementa}",
                    ""
                ])

            decisao = doc.get("decisao", "")
            if decisao:
                linhas.extend([
                    "### Decisão",
                    "",
                    f"> {decisao}",
                    ""
                ])

            linhas.extend(["---", ""])

        linhas.extend([
            "",
            f"*Relatório gerado via MCP CJF-Jurisprudência em {data_hora}*"
        ])

        return "\n".join(linhas)

    except Exception as e:
        return f"**Erro na busca:** {str(e)}"


@mcp.tool()
def listar_tribunais_cjf() -> str:
    """
    Lista todos os tribunais disponíveis para busca no CJF.

    Returns:
        XML com código e nome de cada tribunal
    """
    linhas = ['<tribunais_cjf>']
    for codigo, nome in TRIBUNAIS.items():
        linhas.append(f'  <tribunal codigo="{codigo}">{nome}</tribunal>')
    linhas.append('</tribunais_cjf>')

    return "\n".join(linhas)


if __name__ == "__main__":
    mcp.run()
