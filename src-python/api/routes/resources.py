import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from core.db import get_session, DATA_DIR
from models.domain import Project, Resource
from models.schemas import ResourceCreate
from services.ingestion_service import (
    add_resource,
    delete_resource_data,
    _rebuild_consolidated_context,
)

router = APIRouter(prefix="/projects", tags=["resources"])


@router.get("/{project_id}/resources")
def list_resources(project_id: str, session: Session = Depends(get_session)):
    resources = session.exec(
        select(Resource).where(Resource.project_id == project_id)
    ).all()
    return resources


@router.post("/{project_id}/resources/upload")
def upload_pdf(
    project_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported here")

    resources_dir = DATA_DIR / "projects" / project_id / "resources"
    os.makedirs(resources_dir, exist_ok=True)

    file_path = resources_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        resource = add_resource(
            session=session,
            project=project,
            name=file.filename,
            resource_type="pdf",
            file_path=str(file_path),
        )
        return resource
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/resources/link")
def add_link(
    project_id: str, payload: ResourceCreate, session: Session = Depends(get_session)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.type != "link":
        raise HTTPException(status_code=400, detail="Invalid resource type")

    try:
        resource = add_resource(
            session=session,
            project=project,
            name=payload.name,
            resource_type="link",
            url=payload.url,
        )
        return resource
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/resources/text")
def add_text(
    project_id: str, payload: ResourceCreate, session: Session = Depends(get_session)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.type != "text":
        raise HTTPException(status_code=400, detail="Invalid resource type")

    resources_dir = DATA_DIR / "projects" / project_id / "resources"
    os.makedirs(resources_dir, exist_ok=True)
    file_path = resources_dir / f"{payload.name}.txt"

    content = payload.content or ""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        resource = add_resource(
            session=session,
            project=project,
            name=payload.name,
            resource_type="text",
            content=content,
            file_path=str(file_path),
        )
        return resource
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/resources/{resource_id}")
def delete_resource(
    project_id: str, resource_id: str, session: Session = Depends(get_session)
):
    resource = session.get(Resource, resource_id)
    if not resource or resource.project_id != project_id:
        raise HTTPException(status_code=404, detail="Resource not found")

    delete_resource_data(session, resource, rebuild_context=False)

    session.delete(resource)
    session.commit()

    _rebuild_consolidated_context(session, project_id)

    return {"status": "deleted"}
