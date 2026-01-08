# MCP Server: CJF Jurisprudência Unificada

Servidor MCP para acesso à jurisprudência unificada do Conselho da Justiça Federal.

## Funcionalidades

Busca decisões de todos os tribunais federais:
- STF (Supremo Tribunal Federal)
- STJ (Superior Tribunal de Justiça)
- TRF1, TRF2, TRF3, TRF4, TRF5, TRF6

## Tools Disponíveis

### `buscar_jurisprudencia_cjf`

Busca jurisprudência e retorna dados estruturados.

```
Parâmetros:
- busca: Termo de busca (ex: "pensão por morte")
- tribunais: Tribunais separados por vírgula (default: todos)
- max_resultados: Máximo de resultados (default: 30)
```

### `gerar_relatorio_cjf`

Busca e gera relatório formatado em Markdown com ementas completas.

```
Parâmetros:
- busca: Termo de busca
- tribunais: Tribunais (default: todos)
- max_resultados: Máximo (default: 10)
```

### `listar_tribunais_cjf`

Lista todos os tribunais disponíveis.

## Metadados Extraídos

Para cada documento:

| Campo | Descrição |
|-------|-----------|
| numero | Número/classe do processo |
| classe | Tipo de processo (AC, REsp, etc.) |
| relator | Nome do relator |
| orgao_julgador | Turma/Câmara |
| data_julgamento | Data do julgamento |
| data_publicacao | Data da publicação |
| fonte_publicacao | Fonte (DJE, página) |
| ementa | **Texto completo da ementa** |
| decisao | Resultado (unânime, etc.) |

## Tecnologia

Este servidor faz scraping do site JSF/PrimeFaces do CJF:
- Mantém sessão HTTP com cookies
- Obtém ViewState da página
- Faz requisições AJAX para buscar
- Parseia respostas XML/HTML

## Configuração

Registrado em `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "cjf-jurisprudencia": {
      "command": "python",
      "args": ["C:\\Users\\georg\\.claude\\mcp-servers\\cjf-jurisprudencia\\server.py"]
    }
  }
}
```

## Dependências

- Python 3.10+
- mcp (fastmcp)
- requests
- beautifulsoup4

## Exemplos de Uso

No Claude Code, após reiniciar:

```
"Busque jurisprudência sobre pensão por morte no TRF5"

"Gere relatório de jurisprudência do STJ sobre auxílio-doença"

"Quais tribunais estão disponíveis no CJF?"
```

## URL Fonte

`https://jurisprudencia.cjf.jus.br/unificada/`
