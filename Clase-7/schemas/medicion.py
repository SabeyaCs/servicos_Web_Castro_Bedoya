from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Base común para atributos compartidos
class MedicionBase(BaseModel):
    estudiante_id: int
    variable: str
    valor: float
    unidad: str
    fecha_hora: datetime

# Schema para crear una medición (Asegúrate de que este nombre esté escrito así)
class MedicionCreate(MedicionBase):
    pass

# Schema para actualización parcial
class MedicionUpdate(BaseModel):
    estudiante_id: Optional[int] = None
    variable: Optional[str] = None
    valor: Optional[float] = None
    unidad: Optional[str] = None
    fecha_hora: Optional[datetime] = None

# Schema de respuesta
class MedicionResponse(MedicionBase):
    id: int

    class Config:
        from_attributes = True