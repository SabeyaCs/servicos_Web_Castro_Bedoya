from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas.medicion import MedicionCreate, MedicionUpdate, MedicionResponse
import crud.medicion as crud_medicion

router = APIRouter(
    prefix="/mediciones",
    tags=["Mediciones"]
)

@router.get("/", response_model=List[MedicionResponse])
def listar_mediciones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_medicion.get_mediciones(db, skip=skip, limit=limit)

@router.get("/{id}", response_model=MedicionResponse)
def consultar_medicion(id: int, db: Session = Depends(get_db)):
    medicion = crud_medicion.get_medicion(db, medicion_id=id)
    if not medicion:
        raise HTTPException(status_code=404, detail="Medición no encontrada")
    return medicion

@router.post("/", response_model=MedicionResponse, status_code=status.HTTP_201_CREATED)
def crear_medicion(medicion: MedicionCreate, db: Session = Depends(get_db)):
    return crud_medicion.create_medicion(db=db, medicion=medicion)

@router.patch("/{id}", response_model=MedicionResponse)
def actualizar_medicion(id: int, medicion: MedicionUpdate, db: Session = Depends(get_db)):
    db_medicion = crud_medicion.update_medicion(db, medicion_id=id, medicion_data=medicion)
    if not db_medicion:
        raise HTTPException(status_code=404, detail="Medición no encontrada")
    return db_medicion

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_medicion(id: int, db: Session = Depends(get_db)):
    db_medicion = crud_medicion.delete_medicion(db, medicion_id=id)
    if not db_medicion:
        raise HTTPException(status_code=404, detail="Medición no encontrada")
    return None