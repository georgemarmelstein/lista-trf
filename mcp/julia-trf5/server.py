"""
MCP Server: JULIA - Sistema de Jurisprudência do TRF5

Acesso ao sistema JULIA do TRF5 para busca de jurisprudência.
Permite buscar em 1º grau (Seções Judiciárias) e 2º grau (TRF5).

Arquitetura baseada nos padrões do anthropic-tools:
- Descrições ricas com instruções de uso
- Formatação XML estruturada
- Truncagem inteligente de conteúdo
- Retry com backoff exponencial
"""

from mcp.server.fastmcp import FastMCP
import requests
import json
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt
import sys

# Adicionar módulo compartilhado ao path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.base_juridica import (
    BaseResultadoJuridico,
    formatar_resultados_xml,
    truncar_por_tokens,
    extrair_ementa,
    limpar_texto_html,
)

# Criar servidor MCP
mcp = FastMCP("julia-trf5")

# Configuração
JULIA_API_URL = "https://julia.trf5.jus.br/julia/api/v1"
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"

# Seções Judiciárias (1º grau)
SECOES_JUDICIARIAS = {
    "JFCE": "Seção Judiciária do Ceará",
    "JFRN": "Seção Judiciária do Rio Grande do Norte",
    "JFPB": "Seção Judiciária da Paraíba",
    "JFPE": "Seção Judiciária de Pernambuco",
    "JFAL": "Seção Judiciária de Alagoas",
    "JFSE": "Seção Judiciária de Sergipe"
}

# Órgãos julgadores do TRF5 (2º grau)
ORGAOS_TRF5 = [
    "PLENO", "1ª SEÇÃO", "2ª SEÇÃO", "3ª SEÇÃO",
    "1ª TURMA", "2ª TURMA", "3ª TURMA", "4ª TURMA"
]

TIPOS_DOCUMENTO = {
    "sentenca": "Sentença",
    "acordao": "Acórdão",
    "decisao": "Decisão",
    "despacho": "Despacho"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9"
}


class JuliaSession:
    """Gerencia sessão autenticada com o JULIA."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.session = None
        return cls._instance

    def _carregar_credenciais(self) -> Dict[str, str]:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}")

        with open(CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)

        return {
            "usuario": base64.b64decode(creds["usuario"]).decode(),
            "senha": base64.b64decode(creds["senha"]).decode(),
            "orgao": creds["orgao"]
        }

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def obter_sessao(self) -> requests.Session:
        if self.session is not None:
            return self.session

        session = requests.Session()
        session.headers.update(HEADERS)

        creds = self._carregar_credenciais()

        # Acessar página de login
        session.get("https://julia.trf5.jus.br/julia/entrar", timeout=30)

        # Fazer login
        login_data = {
            "usuario": creds["usuario"],
            "orgao": creds["orgao"],
            "senha": creds["senha"],
            "token": "",
            "action": "login"
        }

        resp = session.post(f"{JULIA_API_URL}/usuario", data=login_data, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Falha no login: {resp.status_code}")

        data = resp.json()
        if data.get("status") != "OK":
            raise Exception(f"Login inválido: {data.get('mensagem', 'Erro desconhecido')}")

        self.session = session
        return session

    def resetar(self):
        self.session = None

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def buscar_documentos(self, params: Dict) -> Dict:
        session = self.obter_sessao()
        resp = session.get(f"{JULIA_API_URL}/documentos:dt", params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def obter_documento(self, identificador: str) -> Dict:
        session = self.obter_sessao()
        resp = session.get(f"{JULIA_API_URL}/documentos/{identificador}", timeout=60)
        resp.raise_for_status()
        return resp.json().get("resultado", {})


# Instância global
_julia = JuliaSession()


def montar_params_busca(
    termo: str,
    orgao: str = "TRF5",
    instancia: str = "G2",
    tipos_documento: List[str] = None,
    orgao_julgador: str = "",
    relator: str = "",
    assinador: str = "",
    numero_processo: str = "",
    data_inicial: str = "",
    data_final: str = "",
    campo_busca: str = "",
    start: int = 0,
    length: int = 30
) -> Dict:
    """Monta parâmetros para busca no JULIA."""
    params = {
        "draw": 1,
        "start": start,
        "length": length,
        "search[value]": "",
        "search[regex]": "false",
        "termo": termo,
        "orgao": orgao,
        "instancia": instancia,
        "todosOsTemas": "true",
        "localizacao": ""
    }

    if campo_busca:
        mapa_campos = {
            "ementa": "Ementa",
            "acordao": "Acórdão",
            "inteiro_teor": "Inteiro Teor do Acórdão",
            "sentenca": "Sentença"
        }
        if campo_busca.lower() in mapa_campos:
            params["tiposDocumento"] = mapa_campos[campo_busca.lower()]

    if tipos_documento and not campo_busca:
        params["tiposDocumento"] = "#".join(tipos_documento) + "#" if len(tipos_documento) > 1 else tipos_documento[0]

    if orgao_julgador:
        params["orgaoJulgador"] = orgao_julgador
    if relator:
        params["relator"] = relator
    if assinador:
        params["assinador"] = assinador
    if numero_processo:
        params["numeroProcesso"] = numero_processo
    if data_inicial:
        params["dataInicial"] = data_inicial
    if data_final:
        params["dataFinal"] = data_final

    # Colunas do DataTables
    colunas = ["processo.numero", "tipo.descricao", "nomeAssinatura", "dataAssinatura"]
    for i, col in enumerate(colunas):
        params[f"columns[{i}][data]"] = col
        params[f"columns[{i}][searchable]"] = "true"
        params[f"columns[{i}][orderable]"] = "false"
        params[f"columns[{i}][search][value]"] = ""
        params[f"columns[{i}][search][regex]"] = "false"

    return params


@mcp.tool()
def buscar_julia(
    termo: str,
    orgao: str = "TRF5",
    instancia: str = "G2",
    tipos_documento: str = "",
    orgao_julgador: str = "",
    relator: str = "",
    assinador: str = "",
    numero_processo: str = "",
    data_inicial: str = "",
    data_final: str = "",
    campo_busca: str = "",
    max_resultados: int = 30
) -> str:
    """
    Busca jurisprudência no sistema JULIA do TRF5 (Tribunal Regional Federal da 5ª Região).
    Cobre 2º grau (TRF5) e 1º grau (Seções Judiciárias: CE, RN, PB, PE, AL, SE).

    IMPORTANTE - SINTAXE DO JULIA:
    O JULIA usa operadores em PORTUGUÊS e MINÚSCULO. Diferente do CJF!

    OPERADORES DISPONÍVEIS (sempre minúsculo):
    ┌──────────┬─────────────────────────────────────────┬────────────────────────────┐
    │ Operador │ Descrição                               │ Exemplo                    │
    ├──────────┼─────────────────────────────────────────┼────────────────────────────┤
    │ e        │ Ambos termos obrigatórios               │ pensão e morte             │
    │ ou       │ Qualquer um dos termos                  │ aposentadoria ou benefício │
    │ nao      │ Primeiro termo, exclui segundo          │ servidor nao militar       │
    │ prox     │ Próximos (até 5 palavras, mesma ordem)  │ processo prox físico       │
    │ adj      │ Adjacentes (até 5 palavras, qq ordem)   │ auxílio adj doença         │
    │ $        │ Wildcard (qualquer sufixo)              │ aposentad$                 │
    └──────────┴─────────────────────────────────────────┴────────────────────────────┘

    PARTICULARIDADES DO JULIA:
    1. Operadores SEMPRE em minúsculo (e, ou, nao) - MAIÚSCULO não funciona!
    2. Distância FIXA de 5 palavras para prox/adj (não permite prox[3])
    3. Wildcard $ apenas no FINAL do termo (aposentad$, não $adoria)
    4. NÃO suporta busca por campo via sintaxe - use os FILTROS
    5. Frase exata com aspas: "pensão por morte"

    ESTRATÉGIA DE BUSCA - SIGA ESTES PASSOS:
    1. Identifique o INSTITUTO JURÍDICO central
    2. Liste SINÔNIMOS e conecte com "ou"
    3. Adicione QUALIFICADORES com "e"
    4. Use WILDCARDS para variações (aposentad$ pega aposentadoria, aposentado)
    5. Use os FILTROS para refinar (orgao_julgador, relator, tipos_documento)

    EXEMPLOS DE TRANSFORMAÇÃO (pergunta → query):

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ Pergunta: "Pensão por morte para companheiro homoafetivo"                   │
    │ ❌ Ruim: pensão por morte para companheiro homoafetivo                      │
    │ ✅ Boa:  pensão e morte e (homoafetivo ou "mesmo sexo" ou "união estável")  │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Aposentadoria especial para eletricista"                         │
    │ ❌ Ruim: aposentadoria especial para eletricista                            │
    │ ✅ Boa:  aposentad$ e especial e (eletricista ou "energia elétrica")        │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "O INSS pode cessar auxílio-doença sem perícia?"                  │
    │ ❌ Ruim: INSS pode cessar auxílio-doença sem perícia                        │
    │ ✅ Boa:  "auxílio-doença" e (cessação ou alta) e perícia e ilegalidade      │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "BPC para idoso estrangeiro"                                      │
    │ ✅ Boa:  (bpc ou loas) e idoso e (estrangeiro ou nacionalidade)             │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │ Pergunta: "Prescrição em ação previdenciária"                               │
    │ ✅ Boa:  prescrição e previdenciári$ nao penal                              │
    └─────────────────────────────────────────────────────────────────────────────┘

    TERMOS TÉCNICOS - USE EM VEZ DE LINGUAGEM COLOQUIAL:
    ┌─────────────────────────────┬───────────────────────────────────────────────┐
    │ Coloquial                   │ Técnico no JULIA                              │
    ├─────────────────────────────┼───────────────────────────────────────────────┤
    │ aposentar por doença        │ aposentadoria e invalidez                     │
    │ pensão da viúva             │ pensão e morte e (cônjuge ou viúv$)           │
    │ auxílio para deficiente     │ bpc ou loas ou "benefício assistencial"       │
    │ tempo de roça               │ rural e "segurado especial"                   │
    │ revisar valor               │ revisão e (rmi ou "salário benefício")        │
    └─────────────────────────────┴───────────────────────────────────────────────┘

    USO INTELIGENTE DOS FILTROS:
    - tipos_documento: "Acórdão" para 2º grau, "Sentença" para 1º grau
    - orgao_julgador: "1ª TURMA", "2ª TURMA", "PLENO" para TRF5
    - relator: Nome do desembargador para jurisprudência específica
    - instancia: "G2" para TRF5, "G1" para Seções Judiciárias
    - orgao: "TRF5" ou "JFCE", "JFPE", "JFPB", "JFRN", "JFAL", "JFSE"

    Args:
        termo: Query com sintaxe JULIA (operadores minúsculos: e, ou, nao, prox, adj, $).
               NÃO passe perguntas diretas. Use a estratégia acima.
        orgao: Órgão. Default: "TRF5"
               2º grau: TRF5
               1º grau: JFCE, JFRN, JFPB, JFPE, JFAL, JFSE
        instancia: "G2" (2º grau/TRF5) ou "G1" (1º grau/Seções). Default: "G2"
        tipos_documento: Separados por vírgula: Sentença, Acórdão, Decisão
        orgao_julgador: Ex: "1ª TURMA", "PLENO", "3ª TURMA"
        relator: Nome do magistrado relator
        assinador: Nome de quem assinou (útil para 1º grau = juiz)
        numero_processo: Número do processo específico
        data_inicial: Formato YYYY-MM-DD
        data_final: Formato YYYY-MM-DD
        campo_busca: "ementa", "acordao", "inteiro_teor" ou vazio para todos
        max_resultados: Máximo de resultados (1-100). Default: 30

    Returns:
        XML estruturado com documentos: texto, magistrado, órgão julgador, data
    """

    try:
        tipos = [t.strip() for t in tipos_documento.split(",")] if tipos_documento else None

        params = montar_params_busca(
            termo=termo,
            orgao=orgao,
            instancia=instancia,
            tipos_documento=tipos,
            orgao_julgador=orgao_julgador,
            relator=relator,
            assinador=assinador,
            numero_processo=numero_processo,
            data_inicial=data_inicial,
            data_final=data_final,
            campo_busca=campo_busca,
            length=min(max_resultados, 100)
        )

        resultado = _julia.buscar_documentos(params)

        if resultado.get("error"):
            return f'<erro>{resultado["error"]}</erro>'

        # Converter para BaseResultadoJuridico
        resultados: List[BaseResultadoJuridico] = []

        for doc in resultado.get("data", []):
            processo = doc.get("processo", {})
            texto = doc.get("texto", "")
            texto = truncar_por_tokens(limpar_texto_html(texto), max_tokens=1000)

            resultado_obj = BaseResultadoJuridico(
                conteudo=texto,
                fonte=doc.get("url", ""),
                tipo=doc.get("tipo", {}).get("descricao", ""),
                orgao=processo.get("orgao", ""),
                numero=processo.get("numero", ""),
                relator=processo.get("nomeMagistrado", "") or doc.get("nomeAssinatura", ""),
                data=doc.get("dataAssinatura", "")[:10] if doc.get("dataAssinatura") else "",
            )
            resultados.append(resultado_obj)

        # Formatar como XML
        xml_resultado = formatar_resultados_xml(resultados, "jurisprudencia_julia")

        # Adicionar metadados
        total = resultado.get("recordsTotal", len(resultados))
        meta = f'<!-- Busca: "{termo}" | Órgão: {orgao} | Total: {total} -->\n'

        return meta + xml_resultado

    except Exception as e:
        _julia.resetar()
        return f'<erro>Falha na busca JULIA: {str(e)}</erro>'


@mcp.tool()
def relatorio_segundo_grau(
    termo: str,
    orgao_julgador: str = "",
    relator: str = "",
    max_resultados: int = 10,
    extrair_ementas: bool = True
) -> str:
    """
    Gera relatório qualitativo de jurisprudência do TRF5 (2º grau) com ementas completas.

    USE ESTA TOOL para análise aprofundada de precedentes regionais do Nordeste.
    Extrai ementas completas (mais lento, mais útil) para análise qualitativa.

    QUANDO USAR:
    - Precisa de EMENTAS COMPLETAS para análise
    - Quer jurisprudência do TRF5 especificamente
    - Precisa identificar TENDÊNCIA de uma turma ou relator
    - Quer relatório formatado para apresentar ao cliente

    SINTAXE DO TERMO (mesma do buscar_julia):
    Operadores em MINÚSCULO: e, ou, nao, prox, adj, $

    Exemplos de termos bem formulados:
    - pensão e morte e (homoafetivo ou "união estável")
    - aposentad$ e especial e (epi ou insalubridade)
    - "auxílio-doença" e cessação e (ilegalidade ou nulidade)

    USO DOS FILTROS:
    - orgao_julgador: Filtre por turma para ver tendência
      Opções: "1ª TURMA", "2ª TURMA", "3ª TURMA", "4ª TURMA", "PLENO"
    - relator: Nome do desembargador para jurisprudência específica
    - extrair_ementas: True para ementas completas (mais lento)

    Args:
        termo: Query com sintaxe JULIA (operadores minúsculos)
        orgao_julgador: Turma específica. Ex: "1ª TURMA", "PLENO"
        relator: Nome do desembargador relator
        max_resultados: Quantidade de acórdãos (1-50). Default: 10
        extrair_ementas: Se True, extrai ementa completa de cada documento

    Returns:
        Relatório em Markdown com ementas, metadados e tabela de conferência
    """

    try:
        params = montar_params_busca(
            termo=termo,
            orgao="TRF5",
            instancia="G2",
            tipos_documento=["Acórdão"],
            orgao_julgador=orgao_julgador,
            relator=relator,
            length=min(max_resultados, 50)
        )

        resultado = _julia.buscar_documentos(params)

        if resultado.get("error"):
            return f"**Erro na busca:** {resultado['error']}"

        documentos = resultado.get("data", [])
        total = resultado.get("recordsTotal", 0)
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        linhas = [
            "# Relatório de Jurisprudência - TRF5 (2º Grau)",
            "",
            f"**Busca realizada:** `{termo}`",
            f"**Data/Hora:** {data_hora}",
            f"**Total encontrado:** {total}",
            f"**Documentos analisados:** {len(documentos)}",
            ""
        ]

        if orgao_julgador:
            linhas.append(f"**Filtro - Órgão julgador:** {orgao_julgador}")
        if relator:
            linhas.append(f"**Filtro - Relator:** {relator}")

        linhas.extend(["", "---", ""])

        if not documentos:
            linhas.append("*Nenhum documento encontrado.*")
            return "\n".join(linhas)

        for i, doc in enumerate(documentos, 1):
            processo = doc.get("processo", {})
            tipo = doc.get("tipo", {}).get("descricao", "N/I")
            numero = processo.get("numero", "N/I")
            classe = processo.get("classeJudicial", {}).get("descricao", "")
            relator_doc = processo.get("nomeMagistrado", "") or doc.get("nomeAssinatura", "N/I")
            colegiado = processo.get("orgaoJulgadorColegiado", {})
            turma = colegiado.get("descricao", "") if colegiado else ""
            data = doc.get("dataAssinatura", "")[:10] if doc.get("dataAssinatura") else "N/I"

            linhas.extend([
                f"## {i}. {tipo} - {numero}",
                "",
                f"**Classe:** {classe}" if classe else "",
                f"**Relator:** {relator_doc}",
                f"**Turma/Órgão:** {turma}" if turma else "",
                f"**Data:** {data}",
                ""
            ])

            if extrair_ementas:
                identificador = doc.get("identificador")
                if identificador:
                    try:
                        doc_completo = _julia.obter_documento(identificador)
                        texto = doc_completo.get("texto", "")
                        ementa = extrair_ementa(texto)
                        ementa = truncar_por_tokens(ementa, max_tokens=1500)
                        if ementa:
                            linhas.extend([
                                "### Ementa",
                                "",
                                f"> {ementa}",
                                ""
                            ])
                    except:
                        pass

            linhas.extend(["---", ""])

        # Tabela de conferência
        linhas.extend([
            "## Metadados para Conferência",
            "",
            "| # | Processo | Relator | Turma | Data |",
            "|---|----------|---------|-------|------|"
        ])

        for i, doc in enumerate(documentos, 1):
            processo = doc.get("processo", {})
            numero = processo.get("numero", "N/I")
            relator_doc = (processo.get("nomeMagistrado") or doc.get("nomeAssinatura") or "N/I")[:25]
            colegiado = processo.get("orgaoJulgadorColegiado", {})
            turma = colegiado.get("descricao", "") if colegiado else ""
            data = (doc.get("dataAssinatura") or "")[:10]
            linhas.append(f"| {i} | {numero} | {relator_doc} | {turma} | {data} |")

        linhas.extend([
            "",
            "---",
            "",
            f"*Relatório gerado via MCP JULIA-TRF5 em {data_hora}*"
        ])

        return "\n".join([l for l in linhas if l or l == ""])

    except Exception as e:
        _julia.resetar()
        return f"**Erro na busca:** {str(e)}"


@mcp.tool()
def relatorio_primeiro_grau(
    termo: str,
    secoes_judiciarias: str = "JFCE,JFRN,JFPB,JFPE,JFAL,JFSE",
    max_resultados: int = 100
) -> str:
    """
    Gera relatório quantitativo de sentenças do 1º grau.

    Analisa sentenças das Seções Judiciárias do TRF5 para identificar
    tendências decisórias por juiz e por seção.

    USE ESTA TOOL quando precisar:
    - Identificar TENDÊNCIA de juízes específicos
    - Comparar posicionamento entre SEÇÕES JUDICIÁRIAS
    - Análise QUANTITATIVA (volume de sentenças)

    A sintaxe é a MESMA do buscar_julia:
    Operadores em MINÚSCULO: e, ou, nao, prox, adj, $

    Args:
        termo: Termo de busca com sintaxe JULIA
        secoes_judiciarias: SJs separadas por vírgula. Default: todas
                           Opções: JFCE, JFRN, JFPB, JFPE, JFAL, JFSE
        max_resultados: Máximo de resultados por SJ. Default: 100

    Returns:
        Relatório quantitativo com análise por juiz e seção
    """

    sjs = [sj.strip().upper() for sj in secoes_judiciarias.split(",")]
    data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    resultados_por_sj = {}
    total_geral = 0

    for sj in sjs:
        if sj not in SECOES_JUDICIARIAS:
            continue

        try:
            params = montar_params_busca(
                termo=termo,
                orgao=sj,
                instancia="G1",
                tipos_documento=["Sentença"],
                length=min(max_resultados, 100)
            )

            resultado = _julia.buscar_documentos(params)

            if not resultado.get("error"):
                documentos = resultado.get("data", [])
                total = resultado.get("recordsTotal", 0)
                total_geral += total

                por_juiz = defaultdict(lambda: {"total": 0, "varas": set()})

                for doc in documentos:
                    assinador = doc.get("nomeAssinatura", "Não identificado")
                    processo = doc.get("processo", {})
                    vara = processo.get("orgaoJulgador", {}).get("descricao", "")

                    por_juiz[assinador]["total"] += 1
                    if vara:
                        por_juiz[assinador]["varas"].add(vara)

                resultados_por_sj[sj] = {
                    "total_encontrado": total,
                    "total_analisado": len(documentos),
                    "por_juiz": dict(por_juiz)
                }
        except:
            continue

    # Gerar relatório
    linhas = [
        "# Relatório Quantitativo - Sentenças 1º Grau",
        "",
        f"**Busca realizada:** `{termo}`",
        f"**Data/Hora:** {data_hora}",
        f"**Total geral encontrado:** {total_geral}",
        "",
        "---",
        "",
        "## Resumo por Seção Judiciária",
        "",
        "| Seção | Total Encontrado | Analisadas |",
        "|-------|------------------|------------|"
    ]

    for sj, dados in sorted(resultados_por_sj.items()):
        linhas.append(f"| {sj} | {dados['total_encontrado']} | {dados['total_analisado']} |")

    linhas.extend(["", "---", ""])

    for sj, dados in sorted(resultados_por_sj.items()):
        nome_sj = SECOES_JUDICIARIAS.get(sj, sj)

        linhas.extend([
            f"## {sj} - {nome_sj}",
            "",
            f"**Total encontrado:** {dados['total_encontrado']}",
            "",
            "### Sentenças por Magistrado",
            "",
            "| Magistrado | Sentenças | Vara(s) |",
            "|------------|-----------|---------|"
        ])

        juizes = sorted(
            dados["por_juiz"].items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )

        for juiz, info in juizes[:20]:
            varas = ", ".join(sorted(info["varas"]))[:50]
            linhas.append(f"| {juiz[:40]} | {info['total']} | {varas} |")

        if len(juizes) > 20:
            linhas.append(f"| *... e mais {len(juizes) - 20} magistrados* | | |")

        linhas.extend(["", "---", ""])

    linhas.extend([
        "",
        f"*Relatório gerado via MCP JULIA-TRF5 em {data_hora}*"
    ])

    return "\n".join(linhas)


@mcp.tool()
def listar_parametros_julia() -> str:
    """
    Lista todos os parâmetros disponíveis para busca no JULIA.

    Returns:
        XML com parâmetros, valores possíveis e descrições
    """
    linhas = [
        '<parametros_julia>',
        '  <orgaos>',
        '    <grau2>TRF5</grau2>',
    ]
    for codigo, nome in SECOES_JUDICIARIAS.items():
        linhas.append(f'    <grau1 codigo="{codigo}">{nome}</grau1>')
    linhas.append('  </orgaos>')

    linhas.append('  <instancias>')
    linhas.append('    <instancia codigo="G1">1º grau (Seções Judiciárias)</instancia>')
    linhas.append('    <instancia codigo="G2">2º grau (TRF5)</instancia>')
    linhas.append('  </instancias>')

    linhas.append('  <orgaos_julgadores_trf5>')
    for org in ORGAOS_TRF5:
        linhas.append(f'    <orgao>{org}</orgao>')
    linhas.append('  </orgaos_julgadores_trf5>')

    linhas.append('  <tipos_documento>')
    for codigo, nome in TIPOS_DOCUMENTO.items():
        linhas.append(f'    <tipo codigo="{codigo}">{nome}</tipo>')
    linhas.append('  </tipos_documento>')

    linhas.append('</parametros_julia>')

    return "\n".join(linhas)


if __name__ == "__main__":
    mcp.run()
