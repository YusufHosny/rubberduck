import os
from typing import Optional
from sqlmodel import Session, select
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.db import DATA_DIR
from models.domain import Resource, Project
from core.config import settings_manager
from services.llm_provider import get_embeddings
from utils.parser import count_tokens, parse_pdf, parse_url


def get_vectorstore(project_id: str) -> Chroma:
    persist_dir = str(DATA_DIR / "projects" / project_id / "vectordb")
    os.makedirs(persist_dir, exist_ok=True)
    embeddings = get_embeddings()
    return Chroma(
        collection_name=f"proj_{project_id}",
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


def _append_to_consolidated_context(project_id: str, resource_name: str, content: str):
    project_dir = DATA_DIR / "projects" / project_id
    context_file = project_dir / "_consolidated_context.txt"
    os.makedirs(project_dir, exist_ok=True)

    with open(context_file, "a", encoding="utf-8") as f:
        f.write(f"--- Document: {resource_name} ---\n\n")
        f.write(content)
        f.write("\n\n")


def ingest_text_to_vectorstore(project_id: str, resource_id: str, text: str):
    settings = settings_manager.get()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = text_splitter.create_documents(
        [text], metadatas=[{"resource_id": resource_id, "project_id": project_id}]
    )

    vectorstore = get_vectorstore(project_id)
    if chunks:
        vectorstore.add_documents(chunks)


def add_resource(
    session: Session,
    project: Project,
    name: str,
    resource_type: str,
    content: Optional[str] = None,
    url: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Resource:
    if resource_type == "pdf" and file_path:
        text = parse_pdf(file_path)
    elif resource_type == "link" and url:
        text = parse_url(url)
    elif resource_type == "text" and content:
        text = content
    else:
        raise ValueError("Invalid resource parameters")

    tokens = count_tokens(text)

    resource = Resource(
        project_id=project.id,
        name=name,
        type=resource_type,
        token_count=tokens,
        file_path=file_path,
        url=url,
    )
    session.add(resource)
    session.commit()
    session.refresh(resource)

    # Save extracted text to cache
    project_dir = DATA_DIR / "projects" / project.id
    text_dir = project_dir / "extracted_texts"
    os.makedirs(text_dir, exist_ok=True)
    text_file_path = text_dir / f"{resource.id}.txt"
    with open(text_file_path, "w", encoding="utf-8") as f:
        f.write(text)

    _append_to_consolidated_context(project.id, name, text)

    ingest_text_to_vectorstore(project.id, resource.id, text)

    return resource


def delete_resource_data(
    session: Session, resource: Resource, rebuild_context: bool = True
):
    project_id = resource.project_id

    vectorstore = get_vectorstore(project_id)
    # Chroma doesn't have an easy delete by metadata yet in basic langchain,
    # but we can try to get collection and delete where metadata matches
    try:
        collection = vectorstore._collection
        collection.delete(where={"resource_id": resource.id})
    except Exception as e:
        print(f"Error deleting vectors for {resource.id}: {e}")

    if resource.file_path and os.path.exists(resource.file_path):
        os.remove(resource.file_path)

    # Delete cached text file if it exists
    text_file_path = (
        DATA_DIR / "projects" / project_id / "extracted_texts" / f"{resource.id}.txt"
    )
    if os.path.exists(text_file_path):
        os.remove(text_file_path)

    if rebuild_context:
        _rebuild_consolidated_context(session, project_id)


def _rebuild_consolidated_context(session: Session, project_id: str):
    project_dir = DATA_DIR / "projects" / project_id
    context_file = project_dir / "_consolidated_context.txt"
    text_dir = project_dir / "extracted_texts"
    os.makedirs(text_dir, exist_ok=True)

    if os.path.exists(context_file):
        os.remove(context_file)

    resources = session.exec(
        select(Resource).where(Resource.project_id == project_id)
    ).all()
    for res in resources:
        try:
            text_file_path = text_dir / f"{res.id}.txt"

            if os.path.exists(text_file_path):
                with open(text_file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                if res.type == "pdf" and res.file_path:
                    text = parse_pdf(res.file_path)
                elif res.type == "link" and res.url:
                    text = parse_url(res.url)
                elif res.type == "text" and res.file_path:
                    with open(res.file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                else:
                    continue

                with open(text_file_path, "w", encoding="utf-8") as f:
                    f.write(text)

            _append_to_consolidated_context(project_id, res.name, text)
        except Exception as e:
            print(f"Error rebuilding context for {res.id}: {e}")
