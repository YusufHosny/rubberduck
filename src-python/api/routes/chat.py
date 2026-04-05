from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from sqlmodel import Session, column, select
from pydantic import BaseModel

from core.db import get_session
from models.domain import Project, Chat, Message
from models.schemas import ChatCreate, MessageCreate
from services.chat_service import stream_chat, generate_chat_name
from utils.parser import count_tokens

router = APIRouter(prefix="/projects", tags=["chat"])


@router.get("/{project_id}/chats")
def list_chats(project_id: str, session: Session = Depends(get_session)):
    chats = session.exec(select(Chat).where(Chat.project_id == project_id)).all()
    return chats


@router.post("/{project_id}/chats")
def create_chat(
    project_id: str, payload: ChatCreate, session: Session = Depends(get_session)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chat = Chat(project_id=project_id, name=payload.name)
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


@router.get("/{project_id}/chats/{chat_id}")
def get_chat_messages(
    project_id: str, chat_id: str, session: Session = Depends(get_session)
):
    chat = session.get(Chat, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    db_messages = session.exec(
        select(Message).where(Message.chat_id == chat_id).order_by(column("created_at"))
    ).all()

    result = []
    for m in db_messages:
        if m.role == "tool":
            continue
        result.append(
            {
                "id": m.id,
                "role": m.role,
                "type": m.type,
                "content": m.content,
                "name": m.name,
                "parent_id": m.parent_id,
                "created_at": m.created_at,
            }
        )

    return result


@router.get("/{project_id}/chats/{chat_id}/tokens")
def get_chat_tokens(
    project_id: str, chat_id: str, session: Session = Depends(get_session)
):
    project = session.get(Project, project_id)
    if not project:
        return {"tokens": 0}

    chat = session.get(Chat, chat_id)
    if not chat or chat.project_id != project_id:
        return {"tokens": 0}

    res_tokens = sum((r.token_count or 0) for r in project.resources)
    msg_tokens = sum(count_tokens(m.content) for m in chat.messages)

    return {"tokens": res_tokens + msg_tokens}


@router.post("/{project_id}/chats/{chat_id}/messages")
async def send_message(
    project_id: str,
    chat_id: str,
    payload: MessageCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chat = session.get(Chat, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    total_tokens = 0
    for res in project.resources:
        total_tokens += res.token_count

    def generate_sse_message(content: str) -> str:
        return content

    if chat.name == "New Chat":
        background_tasks.add_task(
            generate_chat_name, project_id, chat_id, payload.content
        )

    return EventSourceResponse(
        stream_chat(
            session=session,
            project=project,
            chat_id=chat_id,
            query=payload.content,
            total_tokens=total_tokens,
            yield_func=generate_sse_message,
        )
    )


class ChatUpdate(BaseModel):
    name: str


@router.put("/{project_id}/chats/{chat_id}")
def update_chat(
    project_id: str,
    chat_id: str,
    payload: ChatUpdate,
    session: Session = Depends(get_session),
):
    chat = session.get(Chat, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat.name = payload.name
    session.add(chat)
    session.commit()
    return {"status": "updated"}


@router.delete("/{project_id}/chats/{chat_id}")
def delete_chat(project_id: str, chat_id: str, session: Session = Depends(get_session)):
    chat = session.get(Chat, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    session.delete(chat)
    session.commit()
    return {"status": "deleted"}
