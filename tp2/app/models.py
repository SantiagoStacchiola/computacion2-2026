"""Contratos de entrada/salida y estados de tareas."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, ValidationError, model_validator


class Estado(str, Enum):
    PENDIENTE = "pendiente"
    EJECUTANDO = "ejecutando"
    COMPLETADA = "completada"
    FALLIDA = "fallida"
    CANCELADA = "cancelada"


class ParametrosDescargar(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=20)
    # Solo para comparar contra el caso concurrente en el benchmark.
    modo: Literal["concurrente", "secuencial"] = "concurrente"


class ParametrosHashear(BaseModel):
    texto: str = Field(min_length=1, max_length=100_000)
    iteraciones: int = Field(ge=1, le=30_000_000)


class ParametrosEsperar(BaseModel):
    segundos: float = Field(ge=0, le=300)


class CrearTarea(BaseModel):
    tipo: Literal["descargar", "hashear", "esperar"]
    parametros: dict[str, Any]
    timeout: float = Field(default=30.0, gt=0, le=600)

    @model_validator(mode="after")
    def validar_parametros(self) -> "CrearTarea":
        modelos = {
            "descargar": ParametrosDescargar,
            "hashear": ParametrosHashear,
            "esperar": ParametrosEsperar,
        }
        try:
            validado = modelos[self.tipo].model_validate(self.parametros)
        except ValidationError as exc:
            raise ValueError(f"Parámetros inválidos para '{self.tipo}': {exc}") from exc
        self.parametros = validado.model_dump(mode="json")
        return self


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class RegistroTarea(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tipo: Literal["descargar", "hashear", "esperar"]
    parametros: dict[str, Any]
    timeout: float
    estado: Estado = Estado.PENDIENTE
    resultado: Any | None = None
    error: str | None = None
    creado_en: datetime = Field(default_factory=ahora)
    iniciado_en: datetime | None = None
    finalizado_en: datetime | None = None
    worker_id: int | None = None
    cancelacion_solicitada: bool = False

    @property
    def duracion_segundos(self) -> float | None:
        if self.iniciado_en is None or self.finalizado_en is None:
            return None
        return (self.finalizado_en - self.iniciado_en).total_seconds()
