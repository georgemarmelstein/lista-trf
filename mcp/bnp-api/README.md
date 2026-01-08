# MCP Server: BNP-API

Servidor MCP para acesso ao Banco Nacional de Precedentes (BNP/PAGEA) do CNJ.

## Funcionalidades

Permite buscar precedentes vinculantes de todos os tribunais brasileiros:
- Repercussão Geral (STF)
- Recursos Repetitivos (STJ)
- Súmulas Vinculantes
- Súmulas STF/STJ
- IRDRs, IACs, PUILs

## Tools Disponíveis

### `buscar_precedentes`

Busca precedentes e retorna dados estruturados.

```
Parâmetros:
- busca: Termo de busca (ex: "pensão por morte")
- orgaos: Órgãos separados por vírgula (default: "STF,STJ")
- tipos: Tipos de precedente (default: "RG,RR,SV,SUM")
- max_resultados: Máximo de resultados (default: 10)
```

### `gerar_relatorio_precedentes`

Busca precedentes e gera relatório formatado em Markdown.

```
Parâmetros:
- busca: Termo de busca
- orgaos: Órgãos (default: "STF,STJ")
- tipos: Tipos (default: "RG,RR,SV,SUM")
- max_resultados: Máximo (default: 10)
```

### `listar_tipos_precedentes`

Lista todos os tipos de precedentes disponíveis com suas descrições.

## Tipos de Precedentes

| Código | Descrição |
|--------|-----------|
| RG | Repercussão Geral (STF) |
| RR | Recurso Repetitivo (STJ) |
| SV | Súmula Vinculante |
| SUM | Súmula |
| IRDR | Incidente de Resolução de Demandas Repetitivas |
| IAC | Incidente de Assunção de Competência |
| PUIL | Pedido de Uniformização de Interpretação de Lei |

## Configuração

Registrado em `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "bnp-api": {
      "command": "python",
      "args": ["C:\\Users\\georg\\.claude\\mcp-servers\\bnp-api\\server.py"]
    }
  }
}
```

## Dependências

- Python 3.10+
- mcp (fastmcp)
- requests

## Exemplos de Uso

No Claude Code, após reiniciar:

```
"Busque precedentes sobre pensão por morte no BNP"

"Gere um relatório de precedentes sobre auxílio-doença e demora do INSS"

"Quais são os tipos de precedentes disponíveis no BNP?"
```

## API Fonte

Endpoint: `POST https://pangeabnp.pdpj.jus.br/api/v1/precedentes`

Fonte: PAGEA - Plataforma de Gestão de Precedentes do CNJ
