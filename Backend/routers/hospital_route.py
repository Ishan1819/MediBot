from fastapi import APIRouter
from ..models.hospital_finder import get_maternity_hospitals_nearby

router = APIRouter()

@router.get("/find_hospital/")
def find_hospital(location: str):
    hospitals = get_maternity_hospitals_nearby(location)
    return {"nearest_hospitals": hospitals}