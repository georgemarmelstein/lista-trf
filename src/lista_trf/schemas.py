"""Esquemas de dados para o sistema de análise de listas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class NivelAlerta(str, Enum):
    """Níveis de alerta para análise de processos."""

    VERMELHO = "vermelho"  # Atenção imediata
    AMARELO = "amarelo"    # Análise recomendada
    VERDE = "verde"        # Sem alertas


class Processo(BaseModel):
    """Processo extraído da lista de julgamento."""

    ordem: int = Field(description="Ordem do processo na lista")
    numero: str = Field(description="Número CNJ do processo")
    tipo_acao: Optional[str] = Field(default=None, description="Tipo de ação")
    partes: dict = Field(default_factory=dict, description="Partes do processo")
    ementa: str = Field(description="Texto completo da ementa")
    metadata: dict = Field(default_factory=dict, description="Metadados (turma, sessão, etc)")


class PrecedenteEncontrado(BaseModel):
    """Precedente encontrado na pesquisa."""

    identificador: str = Field(description="Ex: Tema 1150/STJ, Súmula 123")
    fonte: str = Field(description="BNP, JULIA, CJF")
    tese: str = Field(description="Texto da tese ou súmula")
    status: str = Field(default="vigente", description="vigente, superado, pendente")
    alinhamento: str = Field(description="compativel, divergente, parcial")
    observacao: Optional[str] = Field(default=None, description="Observações adicionais")


class AnaliseProcesso(BaseModel):
    """Resultado da análise de um processo."""

    processo_numero: str = Field(description="Número do processo analisado")
    processo_ordem: int = Field(default=0, description="Ordem na lista")
    tema_central: str = Field(description="Tema jurídico identificado")
    alerta: NivelAlerta = Field(description="Nível de alerta")
    motivo_alerta: str = Field(description="Explicação do alerta")
    precedentes_relevantes: list[PrecedenteEncontrado] = Field(
        default_factory=list,
        description="Precedentes encontrados"
    )
    flags_sensibilidade: list[str] = Field(
        default_factory=list,
        description="Flags: improbidade, ambiental, etc"
    )
    complexidade_fatica: str = Field(
        default="baixa",
        description="baixa, media, alta"
    )
    recomendacao: str = Field(description="Recomendação de ação")
    analise_completa: Optional[str] = Field(
        default=None,
        description="Texto completo da análise para modo conversa"
    )


class RelatorioConsolidado(BaseModel):
    """Relatório consolidado de análise da lista."""

    sessao: str = Field(description="Data da sessão")
    turma: str = Field(description="Turma julgadora")
    gabinete: str = Field(default="", description="Gabinete de origem")
    total_processos: int = Field(description="Total de processos analisados")
    analises: list[AnaliseProcesso] = Field(description="Análises individuais")
    falhas: list[dict] = Field(default_factory=list, description="Processos com falha")

    @computed_field
    @property
    def total_vermelhos(self) -> int:
        """Conta processos com alerta vermelho."""
        return sum(1 for a in self.analises if a.alerta == NivelAlerta.VERMELHO)

    @computed_field
    @property
    def total_amarelos(self) -> int:
        """Conta processos com alerta amarelo."""
        return sum(1 for a in self.analises if a.alerta == NivelAlerta.AMARELO)

    @computed_field
    @property
    def total_verdes(self) -> int:
        """Conta processos com alerta verde."""
        return sum(1 for a in self.analises if a.alerta == NivelAlerta.VERDE)

    @property
    def vermelhos(self) -> list[AnaliseProcesso]:
        """Retorna análises com alerta vermelho."""
        return [a for a in self.analises if a.alerta == NivelAlerta.VERMELHO]

    @property
    def amarelos(self) -> list[AnaliseProcesso]:
        """Retorna análises com alerta amarelo."""
        return [a for a in self.analises if a.alerta == NivelAlerta.AMARELO]

    @property
    def verdes(self) -> list[AnaliseProcesso]:
        """Retorna análises com alerta verde."""
        return [a for a in self.analises if a.alerta == NivelAlerta.VERDE]


class SessaoAnalise(BaseModel):
    """Estado completo de uma sessão de análise (para modo conversa)."""

    processos_originais: list[Processo] = Field(description="Processos extraídos")
    relatorio: RelatorioConsolidado = Field(description="Relatório gerado")
    historico_conversa: list[dict] = Field(
        default_factory=list,
        description="Histórico de perguntas/respostas"
    )
