"""
Servidor FastAPI para Lista TRF - Analisador de Listas de Julgamento.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import shutil

from app.file_manager import (
    listar_processos,
    mover_processo,
    ler_arquivos_preview,
    criar_processo,
    salvar_analise,
    atualizar_risco
)
from app.parser import processar_arquivo, processar_texto
from app.docx_generator import gerar_relatorio_docx, gerar_relatorio_processo_unico
from app import config

app = FastAPI(title="Lista TRF - Analisador de Listas de Julgamento")

# Servir arquivos estaticos
STATIC_PATH = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")


class MoverRequest(BaseModel):
    numero: str
    estado_origem: str
    estado_destino: str


class FavoritoRequest(BaseModel):
    numero: str
    estado: str
    favorito: bool


class RiscoRequest(BaseModel):
    numero: str
    estado: str
    risco: str  # verde, amarelo, vermelho


class ImportarTextoRequest(BaseModel):
    texto: str


class SalvarAnaliseRequest(BaseModel):
    numero: str
    estado: str
    analise: str
    risco: str = ""
    tema_vinculante: str = ""


@app.get("/")
async def index():
    """Serve a pagina principal."""
    return FileResponse(STATIC_PATH / "index.html")


@app.get("/api/processos")
async def api_listar_processos():
    """Lista todos os processos por estado."""
    return listar_processos()


@app.get("/api/processo/{estado}/{numero:path}")
async def api_ler_processo(estado: str, numero: str):
    """Retorna conteudo dos arquivos de um processo."""
    return ler_arquivos_preview(numero, estado)


@app.post("/api/mover")
async def api_mover_processo(req: MoverRequest):
    """Move processo entre estados."""
    resultado = mover_processo(req.numero, req.estado_origem, req.estado_destino)

    if not resultado["sucesso"]:
        raise HTTPException(status_code=400, detail=resultado["erro"])

    return resultado


@app.post("/api/risco")
async def api_atualizar_risco(req: RiscoRequest):
    """Atualiza nivel de risco de um processo."""
    resultado = atualizar_risco(req.numero, req.estado, req.risco)

    if not resultado["sucesso"]:
        raise HTTPException(status_code=400, detail=resultado["erro"])

    return resultado


@app.post("/api/analise")
async def api_salvar_analise(req: SalvarAnaliseRequest):
    """Salva a analise de um processo."""
    resultado = salvar_analise(
        req.numero,
        req.estado,
        req.analise,
        req.risco,
        req.tema_vinculante
    )

    if not resultado["sucesso"]:
        raise HTTPException(status_code=400, detail=resultado["erro"])

    return resultado


@app.post("/api/importar/arquivo")
async def api_importar_arquivo(file: UploadFile = File(...)):
    """
    Importa lista de julgamento a partir de arquivo (DOCX, PDF, TXT).
    """
    # Salvar arquivo temporariamente
    sufixo = Path(file.filename).suffix
    config.LISTAS_PATH.mkdir(parents=True, exist_ok=True)
    temp_path = config.LISTAS_PATH / f"temp_upload{sufixo}"

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Processar arquivo
        processos = processar_arquivo(str(temp_path))

        # Criar processos no sistema
        criados = []
        erros = []

        for proc in processos:
            # Formatar ementa com metadados
            ementa_completa = f"# {proc['tipo']}\n\n"
            ementa_completa += f"**Processo:** {proc['numero']}\n\n"
            if proc['partes']:
                ementa_completa += f"## Partes\n\n{proc['partes']}\n\n"
            ementa_completa += f"## Ementa\n\n{proc['ementa']}"

            resultado = criar_processo(
                numero=proc['numero'],
                ementa=ementa_completa,
                tipo=proc['tipo'],
                tema=proc['tema'],
                ordem=proc.get('ordem', 0)
            )

            if resultado["sucesso"]:
                criados.append(proc['numero'])
            else:
                erros.append({"numero": proc['numero'], "erro": resultado["erro"]})

        # Salvar arquivo original com nome da lista
        if criados:
            arquivo_final = config.LISTAS_PATH / file.filename
            shutil.move(str(temp_path), str(arquivo_final))
        else:
            temp_path.unlink(missing_ok=True)

        return {
            "sucesso": len(erros) == 0,
            "total": len(processos),
            "criados": len(criados),
            "erros": erros
        }

    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/importar/texto")
async def api_importar_texto(req: ImportarTextoRequest):
    """
    Importa lista de julgamento a partir de texto colado.
    """
    try:
        processos = processar_texto(req.texto)

        if not processos:
            raise HTTPException(
                status_code=400,
                detail="Nenhum processo encontrado no texto. Verifique o formato."
            )

        # Criar processos no sistema
        criados = []
        erros = []

        for proc in processos:
            # Formatar ementa com metadados
            ementa_completa = f"# {proc['tipo']}\n\n"
            ementa_completa += f"**Processo:** {proc['numero']}\n\n"
            if proc['partes']:
                ementa_completa += f"## Partes\n\n{proc['partes']}\n\n"
            ementa_completa += f"## Ementa\n\n{proc['ementa']}"

            resultado = criar_processo(
                numero=proc['numero'],
                ementa=ementa_completa,
                tipo=proc['tipo'],
                tema=proc['tema'],
                ordem=proc.get('ordem', 0)
            )

            if resultado["sucesso"]:
                criados.append(proc['numero'])
            else:
                erros.append({"numero": proc['numero'], "erro": resultado["erro"]})

        return {
            "sucesso": len(erros) == 0,
            "total": len(processos),
            "criados": len(criados),
            "erros": erros
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/estatisticas")
async def api_estatisticas():
    """Retorna estatisticas dos processos."""
    processos = listar_processos()

    stats = {
        "total": 0,
        "por_estado": {},
        "por_risco": {"verde": 0, "amarelo": 0, "vermelho": 0, "sem_risco": 0}
    }

    for estado, lista in processos.items():
        stats["por_estado"][estado] = len(lista)
        stats["total"] += len(lista)

        for proc in lista:
            risco = proc.get("risco", "")
            if risco in stats["por_risco"]:
                stats["por_risco"][risco] += 1
            else:
                stats["por_risco"]["sem_risco"] += 1

    return stats


@app.delete("/api/limpar/{estado}")
async def api_limpar_estado(estado: str):
    """Remove todos os processos de um estado (para testes)."""
    if estado not in config.ESTADOS:
        raise HTTPException(status_code=400, detail=f"Estado invalido: {estado}")

    pasta = config.BASE_PATH / config.ESTADOS[estado]

    if not pasta.exists():
        return {"sucesso": True, "removidos": 0}

    removidos = 0
    for proc_dir in pasta.iterdir():
        if proc_dir.is_dir():
            shutil.rmtree(proc_dir)
            removidos += 1

    return {"sucesso": True, "removidos": removidos}


@app.post("/api/arquivar")
async def api_arquivar_todos():
    """
    Arquiva todos os processos movendo para pasta 'arquivados'.
    Cria subpasta com timestamp para cada arquivamento.
    """
    # Criar pasta de arquivamento com timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pasta_arquivo = config.ARQUIVADOS_PATH / timestamp
    pasta_arquivo.mkdir(parents=True, exist_ok=True)

    arquivados = 0
    erros = []

    # Percorrer todos os estados
    for estado, pasta_nome in config.ESTADOS.items():
        pasta_origem = config.BASE_PATH / pasta_nome

        if not pasta_origem.exists():
            continue

        # Mover cada processo
        for proc_dir in pasta_origem.iterdir():
            if proc_dir.is_dir():
                try:
                    destino = pasta_arquivo / proc_dir.name
                    shutil.move(str(proc_dir), str(destino))
                    arquivados += 1
                except Exception as e:
                    erros.append({"processo": proc_dir.name, "erro": str(e)})

    # Se nao arquivou nada, remove a pasta vazia
    if arquivados == 0:
        pasta_arquivo.rmdir()
        return {
            "sucesso": True,
            "arquivados": 0,
            "mensagem": "Nenhum processo para arquivar"
        }

    return {
        "sucesso": len(erros) == 0,
        "arquivados": arquivados,
        "pasta": str(pasta_arquivo),
        "erros": erros
    }


@app.get("/api/relatorio")
async def api_gerar_relatorio(
    estados: str = Query(default="a-analisar,de-acordo,destacar", description="Estados separados por virgula"),
    apenas_analisados: bool = Query(default=False, description="Apenas processos com analise")
):
    """
    Gera relatorio DOCX comparativo de todos os processos.

    Args:
        estados: Estados a incluir (separados por virgula)
        apenas_analisados: Se True, inclui apenas processos com analise gerada
    """
    try:
        # Listar processos
        todos_processos = listar_processos()
        estados_lista = [e.strip() for e in estados.split(",")]

        # Filtrar por estados solicitados
        processos_selecionados = []
        conteudos = {}

        for estado in estados_lista:
            if estado not in todos_processos:
                continue

            for proc in todos_processos[estado]:
                numero = proc.get("numero", "")

                # Carregar conteudo
                conteudo = ler_arquivos_preview(numero, estado)
                ementa = conteudo.get("ementa", "")
                analise = conteudo.get("analise", "")

                # Filtrar se necessario
                if apenas_analisados and not analise:
                    continue

                processos_selecionados.append(proc)
                conteudos[numero] = {"ementa": ementa, "analise": analise}

        if not processos_selecionados:
            raise HTTPException(
                status_code=404,
                detail="Nenhum processo encontrado com os filtros especificados"
            )

        # Ordenar por ordem na lista
        processos_selecionados.sort(key=lambda p: p.get("ordem", 9999))

        # Gerar DOCX
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        docx_path = config.BASE_PATH / f"relatorio_{timestamp}.docx"

        gerar_relatorio_docx(
            processos=processos_selecionados,
            conteudos=conteudos,
            output_path=docx_path,
            titulo="Relatorio Comparativo de Precedentes"
        )

        # Retornar arquivo
        return FileResponse(
            path=docx_path,
            filename=f"relatorio_lista_trf_{timestamp}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatorio: {str(e)}")


@app.get("/api/relatorio/{estado}/{numero:path}")
async def api_gerar_relatorio_processo(estado: str, numero: str):
    """
    Gera relatorio DOCX de um unico processo.
    """
    try:
        # Carregar dados do processo
        todos_processos = listar_processos()

        if estado not in todos_processos:
            raise HTTPException(status_code=404, detail=f"Estado nao encontrado: {estado}")

        # Encontrar processo
        processo = None
        for proc in todos_processos[estado]:
            if proc.get("numero") == numero:
                processo = proc
                break

        if not processo:
            raise HTTPException(status_code=404, detail=f"Processo nao encontrado: {numero}")

        # Carregar conteudo
        conteudo = ler_arquivos_preview(numero, estado)
        ementa = conteudo.get("ementa", "")
        analise = conteudo.get("analise", "")

        # Gerar DOCX
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        numero_limpo = numero.replace(".", "-").replace("/", "-")
        docx_path = config.BASE_PATH / f"relatorio_{numero_limpo}_{timestamp}.docx"

        gerar_relatorio_processo_unico(
            processo=processo,
            ementa=ementa,
            analise=analise,
            output_path=docx_path
        )

        # Retornar arquivo
        return FileResponse(
            path=docx_path,
            filename=f"analise_{numero_limpo}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatorio: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5002)
