#!/usr/bin/env python3
"""
Script de entrada para análise de listas de julgamento do TRF5.

Este script carrega um documento Word contendo uma lista de julgamento,
extrai os processos e exibe informações básicas. É o ponto de partida
para a análise completa no Claude Code.

Uso:
    python analyze_list.py "caminho/para/lista.docx"

Ou no Claude Code:
    claude "analisa lista: caminho/para/lista.docx"
"""

import sys
from pathlib import Path


def main():
    """Ponto de entrada principal do CLI."""

    # Verificar argumentos
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    file_path = sys.argv[1]

    # Importar após verificar argumentos (mais rápido se houver erro)
    from lista_trf.main import prepare_analysis, MASTER_PROMPT

    try:
        # Preparar análise
        data = prepare_analysis(file_path)

        # Exibir informações
        print_header(data)
        print_processos_preview(data)
        print_next_steps(file_path)

    except FileNotFoundError as e:
        print(f"\nErro: {e}")
        print("Verifique se o caminho do arquivo está correto.")
        sys.exit(1)
    except ValueError as e:
        print(f"\nErro: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro inesperado: {e}")
        sys.exit(1)


def print_usage():
    """Exibe instruções de uso."""
    print("""
================================================================================
          SISTEMA DE ANÁLISE DE LISTAS DE JULGAMENTO - TRF5
================================================================================

Uso:
    python analyze_list.py <caminho_do_arquivo.docx>

Exemplo:
    python analyze_list.py "Lista de Julgamento - Sessão 09.12.2025.docx"

Ou no Claude Code:
    claude "analisa lista: caminho/para/lista.docx"

O arquivo deve ser um documento Word (.docx) contendo uma lista de julgamento
no formato padrão do TRF5.
""")


def print_header(data: dict):
    """Exibe cabeçalho com informações da lista."""
    metadata = data['metadata']

    print()
    print("=" * 70)
    print("          LISTA DE JULGAMENTO CARREGADA COM SUCESSO")
    print("=" * 70)
    print()
    print(f"  Arquivo:    {data['file_path']}")
    print(f"  Processos:  {data['total_processos']}")
    print()
    print("-" * 70)
    print("  METADADOS DA SESSÃO")
    print("-" * 70)
    print(f"  Turma:      {metadata.get('turma', 'Não identificada')}")
    print(f"  Sessão:     {metadata.get('sessao', 'Não identificada')}")
    print(f"  Gabinete:   {metadata.get('gabinete', 'Não identificado')}")
    print()


def print_processos_preview(data: dict):
    """Exibe prévia dos processos encontrados."""
    processos = data['processos']

    print("-" * 70)
    print("  PROCESSOS ENCONTRADOS")
    print("-" * 70)
    print()

    # Mostrar até 10 processos como prévia
    max_preview = min(10, len(processos))

    for i, processo in enumerate(processos[:max_preview]):
        tipo = processo.tipo_acao or "Tipo não informado"
        # Truncar tipo se muito longo
        if len(tipo) > 30:
            tipo = tipo[:27] + "..."
        print(f"  {processo.ordem:3d}. {processo.numero}  [{tipo}]")

    if len(processos) > max_preview:
        print(f"  ... e mais {len(processos) - max_preview} processos")

    print()


def print_next_steps(file_path: str):
    """Exibe próximos passos para análise."""
    print("=" * 70)
    print("  PRÓXIMOS PASSOS")
    print("=" * 70)
    print()
    print("  Para analisar esta lista no Claude Code, execute:")
    print()
    print(f'    claude "analisa a lista em: {file_path}"')
    print()
    print("  Ou use diretamente no Python:")
    print()
    print("    from lista_trf.main import prepare_analysis, generate_analyst_prompts")
    print(f'    data = prepare_analysis(r"{file_path}")')
    print("    prompts = generate_analyst_prompts(data['processos'])")
    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
