# MCP Server: JULIA - Sistema de Jurisprudencia do TRF5

Servidor MCP para acesso ao JULIA, sistema de jurisprudencia unificada do TRF5.

## Funcionalidades

Acesso a decisoes de 1o e 2o grau da Justica Federal da 5a Regiao:

**2o Grau (TRF5):**
- Acordaos, decisoes, votos
- Relatorios qualitativos com ementas completas

**1o Grau (Secoes Judiciarias):**
- JFCE, JFRN, JFPB, JFPE, JFAL, JFSE
- Sentencas e decisoes
- Relatorios quantitativos por juiz e vara

## Operadores Booleanos

O JULIA suporta operadores booleanos **em portugues**:

| Operador | Funcao | Exemplo |
|----------|--------|---------|
| `e` | Ambos termos obrigatorios | `precatorio e compensacao` |
| `ou` | Pelo menos um termo | `tributario ou fiscal` |
| `nao` | Exclusao de termo | `precatorio nao alimentar` |
| `prox` | Ate 5 palavras de distancia (mesma ordem) | `compensacao prox debito` |
| `adj` | Ate 5 palavras (qualquer ordem) | `precatorio adj quitacao` |
| `$` | Truncamento/wildcard | `compens$` (compensacao, compensar, etc.) |

### Exemplos de Busca

```
# Busca simples com AND
"pensao e morte e militar"

# Busca com truncamento
"aposentadoria e invalid$"

# Busca com exclusao
"precatorio e tributario nao alimentar"

# Busca com proximidade
"compensacao prox parcelamento"
```

## Tools Disponiveis

### `buscar_julia`

Busca generica com todos os parametros.

```
Parametros:
- termo: Termo de busca COM operadores booleanos
- orgao: TRF5 (2o grau) ou JFCE, JFRN, etc. (1o grau)
- instancia: G1 (1o grau) ou G2 (2o grau)
- tipos_documento: Sentenca, Acordao, Decisao, etc.
- orgao_julgador: 1a TURMA, PLENO, etc.
- relator: Nome do relator
- assinador: Nome de quem assinou (juiz em 1o grau)
- numero_processo: Numero do processo
- data_inicial/data_final: Filtro de data (YYYY-MM-DD)
- campo_busca: ementa, acordao, inteiro_teor, sentenca, voto, todos
- max_resultados: Maximo de resultados (default: 30)
```

### `relatorio_segundo_grau`

Relatorio qualitativo do TRF5 com ementas completas.

```
Parametros:
- termo: Termo de busca com operadores booleanos
- orgao_julgador: Filtro de turma/orgao
- relator: Filtro de relator
- max_resultados: Maximo (default: 10)
- extrair_ementas: Se True, extrai ementa completa
```

### `relatorio_primeiro_grau`

Relatorio quantitativo de sentencas por juiz e secao judiciaria.

```
Parametros:
- termo: Termo de busca com operadores booleanos
- secoes_judiciarias: SJs separadas por virgula (default: todas)
- max_resultados: Maximo por SJ (default: 100)
```

### `listar_parametros_julia`

Lista todos os parametros disponiveis.

## Autenticacao

O servidor usa credenciais armazenadas em `credentials.json`:

```json
{
  "usuario": "<base64>",
  "senha": "<base64>",
  "orgao": "JFCE"
}
```

A autenticacao e feita automaticamente via API `/api/v1/usuario`.

## Configuracao

Registrado em `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "julia-trf5": {
      "command": "python",
      "args": ["C:\\Users\\georg\\.claude\\mcp-servers\\julia-trf5\\server.py"]
    }
  }
}
```

## Dependencias

- Python 3.10+
- mcp (fastmcp)
- requests

## Exemplos de Uso

No Claude Code, apos reiniciar:

```
"Busque jurisprudencia sobre pensao e morte no JULIA"

"Pesquise precatorio e compensacao e tributario no TRF5"

"Gere relatorio do 2o grau sobre auxilio-doenca e incapacidade"

"Gere relatorio quantitativo de sentencas sobre BPC nas secoes CE e PE"
```

## Historico de Correcoes

### v1.1 (2025-12-17)

**Correcao critica**: O parametro de busca estava errado.

- **Antes (errado)**: `search[value]: termo` - retornava resultados genericos
- **Depois (correto)**: `termo: termo` - filtra corretamente pelos operadores booleanos

Essa correcao foi descoberta analisando o arquivo HAR da interface web do JULIA.

**Novos recursos**:
- Parametro `campo_busca` para filtrar tipo de documento na busca
- Parametro `tiposDocumento` agora usa formato correto (separador `#`)

## URL Fonte

`https://julia.trf5.jus.br/julia/`
