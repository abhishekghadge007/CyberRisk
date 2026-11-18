
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from services.openvas_service import import_openvas_report


router = APIRouter(
    prefix="/api/openvas",
    tags=["OpenVAS Integration"]
)


# ==========================================
# IMPORT OPENVAS XML REPORT
# ==========================================

@router.post("/import")
async def import_report(
    organization_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid OpenVAS XML report."
        )

    if file.content_type not in (
        "application/xml",
        "text/xml",
        "application/octet-stream",
        None
    ):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file content type. Upload an XML file."
        )

    try:

        content = await file.read(10 * 1024 * 1024 + 1)

        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="XML report exceeds the 10 MB upload limit."
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded XML file is empty."
            )

        try:
            xml_content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="XML report must use UTF-8 encoding."
            )

        return import_openvas_report(
            db=db,
            organization_id=organization_id,
            xml_content=xml_content
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"OpenVAS import failed: {str(error)[:300]}"
        )

    finally:
        await file.close()
