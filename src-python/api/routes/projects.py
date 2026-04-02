import os
import shutil
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from core.db import get_session, DATA_DIR
from models.domain import Project
from models.schemas import ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/")
def list_projects(session: Session = Depends(get_session)):
    projects = session.exec(select(Project)).all()
    return projects


@router.get("/{project_id}")
def get_project(project_id: str, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/")
def create_project(project_in: ProjectCreate, session: Session = Depends(get_session)):
    project = Project(name=project_in.name)
    session.add(project)
    session.commit()
    session.refresh(project)

    project_dir = DATA_DIR / "projects" / project.id
    os.makedirs(project_dir / "resources", exist_ok=True)

    with open(project_dir / "notes.md", "w") as f:
        f.write(f"# {project.name}\n\n")

    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session.delete(project)
    session.commit()

    project_dir = DATA_DIR / "projects" / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)

    return {"status": "deleted"}


@router.get("/{project_id}/notes")
def get_notes(project_id: str):
    notes_path = DATA_DIR / "projects" / project_id / "notes.md"
    if notes_path.exists():
        with open(notes_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"content": ""}


@router.put("/{project_id}/notes")
def update_notes(project_id: str, payload: dict):
    content = payload.get("content", "")
    notes_path = DATA_DIR / "projects" / project_id / "notes.md"
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "updated"}
