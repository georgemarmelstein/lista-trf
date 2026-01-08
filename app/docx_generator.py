"""
Gerador de Relatorios DOCX - Lista TRF
Usa python-docx para criar documentos Word com layout comparativo.
"""

from pathlib import Path
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import re


# Cores do sistema
CORES = {
    "marrom": RGBColor(92, 74, 61),      # #5C4A3D
    "dourado": RGBColor(190, 156, 109),  # #BE9C6D
    "verde": RGBColor(45, 122, 90),      # #2d7a5a
    "amarelo": RGBColor(184, 134, 11),   # #b8860b
    "vermelho": RGBColor(166, 61, 61),   # #a63d3d
    "cinza": RGBColor(102, 102, 102),    # #666666
    "cinza_claro": RGBColor(245, 240, 232),  # #f5f0e8
}


def set_cell_shading(cell, color_hex: str):
    """Define cor de fundo de uma celula."""
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    cell._tc.get_or_add_tcPr().append(shading)


def limpar_markdown(texto: str) -> str:
    """Remove simbolos markdown mantendo formatacao legivel."""
    if not texto:
        return "Conteudo nao disponivel"

    # Headers -> texto em maiusculo
    texto = re.sub(r'^###\s+(.+)$', r'\n\1\n', texto, flags=re.MULTILINE)
    texto = re.sub(r'^##\s+(.+)$', r'\n\1\n', texto, flags=re.MULTILINE)
    texto = re.sub(r'^#\s+(.+)$', r'\n\1\n', texto, flags=re.MULTILINE)

    # Bold e italic -> manter texto
    texto = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto)
    texto = re.sub(r'\*([^*]+)\*', r'\1', texto)
    texto = re.sub(r'__([^_]+)__', r'\1', texto)
    texto = re.sub(r'_([^_]+)_', r'\1', texto)

    # Links
    texto = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto)

    # Blockquotes
    texto = re.sub(r'^>\s*', '', texto, flags=re.MULTILINE)

    # Code blocks
    texto = re.sub(r'```[^`]*```', '', texto, flags=re.DOTALL)
    texto = re.sub(r'`([^`]+)`', r'\1', texto)

    # Linhas horizontais
    texto = re.sub(r'^[\-\*]{3,}$', '\n' + '-' * 50 + '\n', texto, flags=re.MULTILINE)

    # Listas
    texto = re.sub(r'^[\-\*]\s+', '- ', texto, flags=re.MULTILINE)

    # Limpar multiplas quebras
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    # Caracteres especiais
    texto = texto.replace('\u2022', '-')
    texto = texto.replace('\u2013', '-')
    texto = texto.replace('\u2014', '-')
    texto = texto.replace('\u201c', '"')
    texto = texto.replace('\u201d', '"')
    texto = texto.replace('\u2018', "'")
    texto = texto.replace('\u2019', "'")

    return texto.strip()


def get_texto_risco(risco: str) -> str:
    """Retorna texto do risco."""
    textos = {
        "verde": "VERDE - Alinhado",
        "amarelo": "AMARELO - Atencao",
        "vermelho": "VERMELHO - Divergente",
    }
    return textos.get(risco, "Nao avaliado")


def get_cor_risco(risco: str) -> RGBColor:
    """Retorna cor do risco."""
    cores = {
        "verde": CORES["verde"],
        "amarelo": CORES["amarelo"],
        "vermelho": CORES["vermelho"],
    }
    return cores.get(risco, CORES["cinza"])


def gerar_relatorio_docx(
    processos: list,
    conteudos: dict,
    output_path: Path,
    titulo: str = "Relatorio Comparativo de Precedentes"
) -> Path:
    """
    Gera um DOCX com relatorio comparativo de todos os processos.
    """
    doc = Document()

    # Configurar pagina paisagem
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    new_width, new_height = section.page_height, section.page_width
    section.page_width = new_width
    section.page_height = new_height
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    # ===== PAGINA DE CAPA =====

    # Titulo
    p_titulo = doc.add_paragraph()
    p_titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_titulo.add_run(titulo)
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = CORES["marrom"]

    # Subtitulo
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_sub.add_run("Lista de Julgamento - TRF")
    run.font.size = Pt(12)
    run.font.color.rgb = CORES["cinza"]

    # Data
    data_geracao = datetime.now().strftime("%d/%m/%Y as %H:%M")
    p_data = doc.add_paragraph()
    p_data.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_data.add_run(f"Gerado em: {data_geracao}")
    run.font.size = Pt(10)
    run.font.color.rgb = CORES["cinza"]

    doc.add_paragraph()

    # ===== RESUMO =====
    p_resumo = doc.add_paragraph()
    run = p_resumo.add_run("RESUMO DA ANALISE")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = CORES["marrom"]

    # Estatisticas
    total = len(processos)
    verdes = sum(1 for p in processos if p.get("risco") == "verde")
    amarelos = sum(1 for p in processos if p.get("risco") == "amarelo")
    vermelhos = sum(1 for p in processos if p.get("risco") == "vermelho")
    pendentes = total - verdes - amarelos - vermelhos

    # Tabela de resumo
    table_resumo = doc.add_table(rows=2, cols=5)
    table_resumo.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Cabecalho
    headers = ["Total", "Verde", "Amarelo", "Vermelho", "Pendentes"]
    valores = [str(total), str(verdes), str(amarelos), str(vermelhos), str(pendentes)]
    cores_valores = [CORES["dourado"], CORES["verde"], CORES["amarelo"], CORES["vermelho"], CORES["cinza"]]

    for i, (header, valor, cor) in enumerate(zip(headers, valores, cores_valores)):
        # Numero
        cell_num = table_resumo.cell(0, i)
        cell_num.text = valor
        p = cell_num.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.runs[0]
        run.bold = True
        run.font.size = Pt(28)
        run.font.color.rgb = cor

        # Label
        cell_label = table_resumo.cell(1, i)
        cell_label.text = header
        p = cell_label.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.runs[0]
        run.font.size = Pt(10)
        run.font.color.rgb = CORES["cinza"]

    doc.add_paragraph()

    # ===== LISTA DE PROCESSOS =====
    p_lista = doc.add_paragraph()
    run = p_lista.add_run("PROCESSOS ANALISADOS")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = CORES["marrom"]

    for proc in processos:
        numero = proc.get("numero", "N/A")
        ordem = proc.get("ordem", "-")
        risco = proc.get("risco", "")

        p = doc.add_paragraph()
        run = p.add_run(f"#{ordem} - {numero}")
        run.font.size = Pt(10)

        if risco:
            run2 = p.add_run(f" ({risco.upper()})")
            run2.font.size = Pt(10)
            run2.font.color.rgb = get_cor_risco(risco)

    # ===== PAGINAS DOS PROCESSOS =====
    for proc in processos:
        doc.add_page_break()

        numero = proc.get("numero", "N/A")
        ordem = proc.get("ordem", "-")
        tipo = proc.get("tipo", "Processo")
        risco = proc.get("risco", "")
        tema = proc.get("tema_vinculante", "")

        conteudo = conteudos.get(numero, {})
        ementa = conteudo.get("ementa", "Ementa nao disponivel")
        analise = conteudo.get("analise", "Analise nao disponivel")

        # Cabecalho do processo
        p_header = doc.add_paragraph()
        run = p_header.add_run(f"#{ordem} - {numero}")
        run.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = CORES["marrom"]

        # Metadados
        meta_parts = [f"Tipo: {tipo}"]
        if risco:
            meta_parts.append(f"Risco: {get_texto_risco(risco)}")
        if tema:
            meta_parts.append(f"Tema: {tema}")

        p_meta = doc.add_paragraph()
        run = p_meta.add_run(" | ".join(meta_parts))
        run.font.size = Pt(9)
        run.font.color.rgb = CORES["cinza"]

        # Tabela comparativa
        table = doc.add_table(rows=2, cols=2)
        table.autofit = False

        # Largura das colunas (metade cada)
        largura_coluna = Cm(13)  # ~50% da largura util em paisagem

        # Cabecalhos
        cell_h1 = table.cell(0, 0)
        cell_h1.text = "EMENTA ORIGINAL"
        cell_h1.width = largura_coluna
        set_cell_shading(cell_h1, "5C4A3D")
        p = cell_h1.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.runs[0]
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(255, 255, 255)

        cell_h2 = table.cell(0, 1)
        cell_h2.text = "ANALISE COMPARATIVA"
        cell_h2.width = largura_coluna
        set_cell_shading(cell_h2, "BE9C6D")
        p = cell_h2.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.runs[0]
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(255, 255, 255)

        # Conteudo
        cell_e = table.cell(1, 0)
        cell_e.text = limpar_markdown(ementa)
        cell_e.width = largura_coluna
        set_cell_shading(cell_e, "FAFAFA")
        for p in cell_e.paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)

        cell_a = table.cell(1, 1)
        cell_a.text = limpar_markdown(analise)
        cell_a.width = largura_coluna
        set_cell_shading(cell_a, "FFFEF5")
        for p in cell_a.paragraphs:
            for run in p.runs:
                run.font.size = Pt(9)

    # Salvar
    doc.save(str(output_path))

    return output_path


def gerar_relatorio_processo_unico(
    processo: dict,
    ementa: str,
    analise: str,
    output_path: Path
) -> Path:
    """
    Gera DOCX de um unico processo.
    """
    return gerar_relatorio_docx(
        processos=[processo],
        conteudos={processo.get("numero", ""): {"ementa": ementa, "analise": analise}},
        output_path=output_path,
        titulo=f"Analise - {processo.get('numero', 'Processo')}"
    )
