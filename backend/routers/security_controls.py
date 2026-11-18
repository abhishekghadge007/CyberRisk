from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import SecurityControl
from schemas import SecurityControlCreate, SecurityControlResponse

router = APIRouter(
    prefix="/api/security-controls",
    tags=["Security Controls"]
)


# GET ALL SECURITY CONTROLS
@router.get("/", response_model=list[SecurityControlResponse])
def get_security_controls(db: Session = Depends(get_db)):

    controls = db.query(SecurityControl).order_by(
        SecurityControl.control_id
    ).all()

    return controls


# CREATE A SECURITY CONTROL
@router.post(
    "/",
    response_model=SecurityControlResponse,
    status_code=status.HTTP_201_CREATED
)
def create_security_control(
    control: SecurityControlCreate,
    db: Session = Depends(get_db)
):

    existing_control = db.query(SecurityControl).filter(
        SecurityControl.control_key == control.control_key
    ).first()

    if existing_control:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A security control with this control key already exists."
        )

    new_control = SecurityControl(
        control_key=control.control_key,
        control_name=control.control_name,
        category=control.category,
        description=control.description,
        framework=control.framework
    )

    db.add(new_control)
    db.commit()
    db.refresh(new_control)

    return new_control


# GET SECURITY CONTROL BY ID
@router.get("/{control_id}", response_model=SecurityControlResponse)
def get_security_control(
    control_id: int,
    db: Session = Depends(get_db)
):

    control = db.query(SecurityControl).filter(
        SecurityControl.control_id == control_id
    ).first()

    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security control not found."
        )

    return control
