"""Gerador de relatório Markdown."""

from lista_trf.schemas import RelatorioConsolidado, AnaliseProcesso, NivelAlerta


def generate_markdown_report(relatorio: RelatorioConsolidado) -> str:
    """
    Gera relatório em formato Markdown.

    Args:
        relatorio: Relatório consolidado com análises

    Returns:
        String com relatório em Markdown
    """
    lines = []

    # Header
    lines.append("# Análise da Lista de Julgamento")
    lines.append(f"## Sessão: {relatorio.sessao} | {relatorio.turma} | {relatorio.gabinete}")

    # Contagens
    v = relatorio.total_vermelhos
    a = relatorio.total_amarelos
    g = relatorio.total_verdes

    vermelho_str = f"{v} alerta vermelho" if v == 1 else f"{v} alertas vermelhos"
    amarelo_str = f"{a} amarelo" if a == 1 else f"{a} amarelos"
    verde_str = f"{g} verde" if g == 1 else f"{g} verdes"

    lines.append(f"## Total: {relatorio.total_processos} processos | {vermelho_str} | {amarelo_str} | {verde_str}")
    lines.append("")
    lines.append("━" * 60)
    lines.append("")

    # Seção Vermelhos
    vermelhos = relatorio.vermelhos
    lines.append(f"## ATENÇÃO IMEDIATA ({len(vermelhos)} processos)")
    lines.append("")

    if vermelhos:
        for i, analise in enumerate(sorted(vermelhos, key=lambda x: x.processo_ordem), 1):
            lines.extend(_format_detailed_analysis(i, analise))
    else:
        lines.append("*Nenhum processo com alerta vermelho.*")
        lines.append("")

    lines.append("━" * 60)
    lines.append("")

    # Seção Amarelos
    amarelos = relatorio.amarelos
    lines.append(f"## ANÁLISE RECOMENDADA ({len(amarelos)} processos)")
    lines.append("")

    if amarelos:
        for i, analise in enumerate(sorted(amarelos, key=lambda x: x.processo_ordem), 1):
            lines.extend(_format_detailed_analysis(i, analise))
    else:
        lines.append("*Nenhum processo com alerta amarelo.*")
        lines.append("")

    lines.append("━" * 60)
    lines.append("")

    # Seção Verdes
    verdes = relatorio.verdes
    lines.append(f"## SEM ALERTAS ({len(verdes)} processos)")
    lines.append("")

    if verdes:
        lines.append("| # | Processo | Tema |")
        lines.append("|---|----------|------|")
        for analise in sorted(verdes, key=lambda x: x.processo_ordem):
            lines.append(f"| {analise.processo_ordem} | {analise.processo_numero} | {analise.tema_central} |")
    else:
        lines.append("*Nenhum processo sem alertas.*")

    lines.append("")

    # Falhas se houver
    if relatorio.falhas:
        lines.append("━" * 60)
        lines.append("")
        lines.append(f"## FALHAS DE ANÁLISE ({len(relatorio.falhas)} processos)")
        lines.append("")
        for falha in relatorio.falhas:
            lines.append(f"- **{falha.get('processo', 'N/A')}**: {falha.get('motivo', 'Erro desconhecido')}")
        lines.append("")

    return "\n".join(lines)


def _format_detailed_analysis(index: int, analise: AnaliseProcesso) -> list[str]:
    """Formata análise detalhada para processos vermelho/amarelo."""
    lines = []

    lines.append(f"### {index}. Processo {analise.processo_numero}")
    lines.append(f"**Tema**: {analise.tema_central}")
    lines.append(f"**Alerta**: {analise.motivo_alerta}")

    if analise.flags_sensibilidade:
        flags_str = ", ".join(analise.flags_sensibilidade)
        lines.append(f"**Flags**: {flags_str}")

    if analise.complexidade_fatica != "baixa":
        lines.append(f"**Complexidade Fática**: {analise.complexidade_fatica}")

    # Precedentes
    if analise.precedentes_relevantes:
        lines.append("**Precedentes**:")
        for p in analise.precedentes_relevantes:
            status = f" ({p.status})" if p.status != "vigente" else ""
            alinhamento_icon = {
                "compativel": "✓",
                "divergente": "✗",
                "parcial": "~"
            }.get(p.alinhamento, "?")
            lines.append(f"- {alinhamento_icon} {p.identificador}{status}: {p.tese[:100]}...")

    lines.append(f"**Recomendação**: {analise.recomendacao}")
    lines.append("")
    lines.append("---")
    lines.append("")

    return lines


def save_report(relatorio: RelatorioConsolidado, output_path: str) -> str:
    """
    Gera e salva relatório em arquivo.

    Args:
        relatorio: Relatório consolidado
        output_path: Caminho para salvar

    Returns:
        Caminho do arquivo salvo
    """
    from pathlib import Path

    md_content = generate_markdown_report(relatorio)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md_content, encoding="utf-8")

    return str(path)
