"""
Gerenciador de arquivos para processos.
Lida com pastas de processos, metadados e movimentacao entre estados.
"""
from pathlib import Path
from typing import Dict, List, Any
import shutil
import json

from app import config


def listar_processos() -> Dict[str, List[Dict[str, Any]]]:
    """
    Lista todos os processos organizados por estado.

    Returns:
        Dict com chave = estado, valor = lista de processos
    """
    resultado = {}

    for estado_key, estado_pasta in config.ESTADOS.items():
        pasta_estado = config.BASE_PATH / estado_pasta
        processos = []

        if pasta_estado.exists():
            for proc_dir in pasta_estado.iterdir():
                if proc_dir.is_dir():
                    # Ler metadados se existirem
                    meta = ler_metadados(proc_dir)
                    processos.append({
                        "numero": proc_dir.name,
                        "estado": estado_key,
                        "caminho": str(proc_dir),
                        "tema": meta.get("tema", ""),
                        "tema_vinculante": meta.get("tema_vinculante", ""),  # Ex: "Tema 1285/STJ"
                        "risco": meta.get("risco", ""),  # verde, amarelo, vermelho
                        "tipo": meta.get("tipo", ""),
                        "ordem": meta.get("ordem", 0),  # Numero na lista de julgamento
                    })

        # Ordenar por risco (vermelho primeiro) e depois por numero
        ordem_risco = {"vermelho": 0, "amarelo": 1, "verde": 2, "": 3}
        processos.sort(key=lambda p: (ordem_risco.get(p["risco"], 3), p["numero"]))
        resultado[estado_key] = processos

    return resultado


def ler_metadados(pasta: Path) -> Dict[str, Any]:
    """
    Le o arquivo de metadados de um processo.
    """
    meta_file = pasta / "meta.json"
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def salvar_metadados(pasta: Path, meta: Dict[str, Any]) -> None:
    """
    Salva metadados de um processo.
    """
    meta_file = pasta / "meta.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def mover_processo(numero: str, estado_origem: str, estado_destino: str) -> Dict[str, Any]:
    """
    Move um processo de um estado para outro.

    Args:
        numero: Numero do processo (nome da pasta)
        estado_origem: Estado atual (key, ex: "a-analisar")
        estado_destino: Novo estado (key, ex: "de-acordo")

    Returns:
        Dict com sucesso=True/False e mensagem de erro se houver
    """
    try:
        pasta_origem = config.BASE_PATH / config.ESTADOS[estado_origem] / numero
        pasta_destino = config.BASE_PATH / config.ESTADOS[estado_destino] / numero

        if not pasta_origem.exists():
            return {"sucesso": False, "erro": f"Processo nao encontrado: {numero}"}

        if pasta_destino.exists():
            return {"sucesso": False, "erro": f"Ja existe processo no destino: {numero}"}

        # Criar pasta de destino se nao existir
        pasta_destino.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(pasta_origem), str(pasta_destino))

        return {"sucesso": True, "novo_caminho": str(pasta_destino)}

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def ler_arquivos_preview(numero: str, estado: str) -> Dict[str, str]:
    """
    Le os arquivos de ementa e analise de um processo.

    Args:
        numero: Numero do processo
        estado: Estado atual do processo

    Returns:
        Dict com chaves "ementa" e "analise" contendo o texto
    """
    resultado = {"ementa": "", "analise": ""}

    try:
        pasta = config.BASE_PATH / config.ESTADOS[estado] / numero

        if not pasta.exists():
            return resultado

        # Buscar arquivos
        ementa_file = pasta / "ementa.md"
        analise_file = pasta / "analise.md"

        if ementa_file.exists():
            resultado["ementa"] = ementa_file.read_text(encoding="utf-8")
        if analise_file.exists():
            resultado["analise"] = analise_file.read_text(encoding="utf-8")

        return resultado

    except Exception:
        return resultado


def criar_processo(numero: str, ementa: str, tipo: str = "", tema: str = "", ordem: int = 0) -> Dict[str, Any]:
    """
    Cria um novo processo na pasta a-analisar.

    Args:
        numero: Numero do processo (CNJ)
        ementa: Texto da ementa
        tipo: Tipo do processo (APELACAO, REMESSA, etc)
        tema: Tema resumido
        ordem: Ordem na lista de julgamento

    Returns:
        Dict com sucesso e caminho
    """
    try:
        pasta = config.BASE_PATH / config.ESTADOS["a-analisar"] / numero

        if pasta.exists():
            return {"sucesso": False, "erro": f"Processo ja existe: {numero}"}

        pasta.mkdir(parents=True, exist_ok=True)

        # Salvar ementa
        ementa_file = pasta / "ementa.md"
        ementa_file.write_text(ementa, encoding="utf-8")

        # Salvar metadados
        meta = {
            "numero": numero,
            "tipo": tipo,
            "tema": tema,
            "risco": "",  # Sera preenchido apos analise
            "ordem": ordem,  # Numero na lista de julgamento
        }
        salvar_metadados(pasta, meta)

        return {"sucesso": True, "caminho": str(pasta)}

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def atualizar_risco(numero: str, estado: str, risco: str) -> Dict[str, Any]:
    """
    Atualiza o nivel de risco de um processo.

    Args:
        numero: Numero do processo
        estado: Estado atual
        risco: verde, amarelo ou vermelho
    """
    try:
        pasta = config.BASE_PATH / config.ESTADOS[estado] / numero

        if not pasta.exists():
            return {"sucesso": False, "erro": "Processo nao encontrado"}

        meta = ler_metadados(pasta)
        meta["risco"] = risco
        salvar_metadados(pasta, meta)

        return {"sucesso": True}

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def salvar_analise(numero: str, estado: str, analise: str, risco: str = "", tema_vinculante: str = "") -> Dict[str, Any]:
    """
    Salva a analise de um processo.

    Args:
        numero: Numero do processo
        estado: Estado atual
        analise: Texto da analise
        risco: Nivel de risco (verde, amarelo, vermelho)
        tema_vinculante: Tema vinculante identificado (ex: "Tema 1066/STF")
    """
    try:
        pasta = config.BASE_PATH / config.ESTADOS[estado] / numero

        if not pasta.exists():
            return {"sucesso": False, "erro": "Processo nao encontrado"}

        # Salvar analise
        analise_file = pasta / "analise.md"
        analise_file.write_text(analise, encoding="utf-8")

        # Atualizar metadados se fornecidos
        meta = ler_metadados(pasta)
        if risco:
            meta["risco"] = risco
        if tema_vinculante:
            meta["tema_vinculante"] = tema_vinculante
        salvar_metadados(pasta, meta)

        return {"sucesso": True}

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
