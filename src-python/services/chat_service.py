from loguru import logger
import json
from typing import AsyncGenerator
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)
from sqlmodel import Session, column, select

from core.db import DATA_DIR
from models.domain import Message as DBMessage, Project
from services.llm_provider import get_llm
from services.ingestion_service import get_vectorstore
from core.config import settings_manager
from prompts.chat_prompts import SYSTEM_PROMPT
from tools.project_tools import create_project_tools
from langchain.agents import create_agent


def get_project_notes(project_id: str) -> str:
    notes_path = DATA_DIR / "projects" / project_id / "notes.md"
    if notes_path.exists():
        with open(notes_path, "r", encoding="utf-8") as f:
            return f.read()
    return "No notes currently saved."


def get_project_context(project_id: str, query: str, total_tokens: int) -> str:
    settings = settings_manager.get()
    threshold = settings.rag_threshold

    if total_tokens > threshold and query:
        try:
            vectorstore = get_vectorstore(project_id)
            docs = vectorstore.similarity_search(query, k=5)
            context = "Retrieved Context:\n\n" + "\n\n---\n\n".join(
                [doc.page_content for doc in docs]
            )
            return context
        except Exception as e:
            logger.error(f"Error during RAG retrieval: {e}")
            return "No context retrieved due to an error."
    else:
        context_file = DATA_DIR / "projects" / project_id / "_consolidated_context.txt"
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                return f.read()
        return "No resources uploaded yet."


def get_chat_history(session: Session, chat_id: str) -> list:
    db_messages = session.exec(
        select(DBMessage).filter_by(chat_id=chat_id).order_by(column("created_at"))
    ).all()

    langchain_history = []

    current_ai_blocks = []
    current_ai_tools = []

    def flush_ai_message():
        if current_ai_blocks or current_ai_tools:
            content = []
            kwargs = {}
            for block in current_ai_blocks:
                if block["type"] == "text":
                    content.append({"type": "text", "text": block["content"]})
                elif block["type"] == "reasoning":
                    content.append(
                        {
                            "type": "text",
                            "text": f"<thinking>\n{block['content']}\n</thinking>\n",
                        }
                    )

            if not content:
                content = ""

            langchain_history.append(
                AIMessage(
                    content=content,
                    tool_calls=current_ai_tools,
                    additional_kwargs=kwargs,
                )
            )
            current_ai_blocks.clear()
            current_ai_tools.clear()

    for msg in db_messages:
        try:
            if msg.role != "assistant":
                flush_ai_message()

            if msg.role == "user":
                langchain_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                if msg.type == "text" or msg.type == "reasoning":
                    current_ai_blocks.append({"type": msg.type, "content": msg.content})
                elif msg.type == "tool_call":
                    args = json.loads(msg.content) if msg.content else {}
                    current_ai_tools.append(
                        {
                            "name": msg.name or "",
                            "args": args,
                            "id": msg.parent_id or "",
                            "type": "tool_call",
                        }
                    )
            elif msg.role == "tool":
                langchain_history.append(
                    ToolMessage(content=msg.content, tool_call_id=msg.parent_id or "")
                )
            elif msg.role == "system":
                langchain_history.append(SystemMessage(content=msg.content))
        except Exception as e:
            logger.error(f"Error parsing message {msg.id}: {e}")

    flush_ai_message()
    return langchain_history


def generate_chat_name(project_id: str, chat_id: str, first_message: str):
    llm = get_llm(max_tokens=15, thinking_level=None, include_thoughts=False)
    prompt = f"Summarize this message into a short 2 to 4 word chat title. Return ONLY the title text, nothing else. Message: {first_message}"
    try:
        content = llm.invoke(prompt).content
        if isinstance(content, str):
            title = str(content)
        elif isinstance(content, list) and len(content) >= 1:
            first_block = content[0]
            if isinstance(first_block, str):
                title = first_block
            elif isinstance(first_block, dict) and "text" in first_block:
                title = str(first_block["text"])
            else:
                title = "New Chat"
        else:
            title = "New Chat"

        title = title.strip().strip('"').strip("'").strip()

        if title.lower().startswith("title:"):
            title = title[6:].strip()

        if not title:
            title = "New Chat"

        from core.db import engine
        from sqlmodel import Session

        with Session(engine) as session:
            from models.domain import Chat

            chat = session.get(Chat, chat_id)
            if chat and chat.name == "New Chat":
                chat.name = title
                session.add(chat)
                session.commit()
                logger.info(f"Chat {chat_id} name updated to: {title}")
    except Exception as e:
        logger.error(f"Error generating chat name: {e}")


async def stream_chat(
    session: Session,
    project: Project,
    chat_id: str,
    query: str,
    total_tokens: int,
    yield_func,
) -> AsyncGenerator[str, None]:
    notes = get_project_notes(project.id)
    context = get_project_context(project.id, query, total_tokens)

    llm = get_llm()

    tools = create_project_tools(project)
    agent = create_agent(llm, tools)

    history = get_chat_history(session, chat_id)

    system_message = SystemMessage(
        content=SYSTEM_PROMPT.format(notes=notes, context=context)
    )
    messages = [system_message] + history + [HumanMessage(content=query)]

    start_new_idx = len(messages)

    user_msg = DBMessage(chat_id=chat_id, role="user", type="text", content=query)
    session.add(user_msg)
    session.commit()

    final_state = None
    try:
        async for event in agent.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]
            name = event["name"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]  # type: ignore
                if hasattr(chunk, "content_blocks") and chunk.content_blocks:
                    for block in chunk.content_blocks:
                        if block.get("type") in ("reasoning", "thinking"):
                            reason_text = (
                                block.get("text")
                                or block.get("reasoning")
                                or block.get("thinking")
                                or ""
                            )
                            if reason_text:
                                yield yield_func(
                                    json.dumps(
                                        {
                                            "type": "reasoning",
                                            "content": str(reason_text),
                                        }
                                    )
                                )
                        elif block.get("type") == "text" and block.get("text"):
                            content_text = block.get("text")
                            yield yield_func(
                                json.dumps(
                                    {"type": "content", "content": str(content_text)}
                                )
                            )
                elif chunk.content:
                    content = chunk.content
                    if isinstance(content, list):
                        content = "".join(
                            str(c.get("text", "")) if isinstance(c, dict) else str(c)
                            for c in content
                        )
                    yield yield_func(
                        json.dumps({"type": "content", "content": str(content)})
                    )
            elif kind == "on_tool_start":
                tool_name = event["name"]
                tool_input = event["data"].get("input", {})
                yield yield_func(
                    json.dumps(
                        {"type": "tool_start", "tool": tool_name, "input": tool_input}
                    )
                )
            elif kind == "on_tool_end":
                tool_name = event["name"]
                yield yield_func(json.dumps({"type": "tool_end", "tool": tool_name}))
            elif kind == "on_chain_end" and name == "LangGraph":
                final_state = event["data"].get("output")

    except Exception as e:
        logger.exception(f"Error generating response: {e}")
        error_msg = f"\n\nError generating response: {str(e)}"
        yield yield_func(json.dumps({"type": "content", "content": error_msg}))

    if final_state and "messages" in final_state:
        new_messages = final_state["messages"][start_new_idx:]
        for msg in new_messages:
            if isinstance(msg, AIMessage):
                content_val = msg.content
                if isinstance(content_val, list):
                    for block in content_val:
                        if isinstance(block, dict):
                            btype = block.get("type")
                            if btype == "text" and block.get("text"):
                                db_msg = DBMessage(
                                    chat_id=chat_id,
                                    role="assistant",
                                    type="text",
                                    content=block.get("text", ""),
                                )
                                session.add(db_msg)
                            elif btype in ("reasoning", "thinking"):
                                rtext = (
                                    block.get("text")
                                    or block.get("reasoning")
                                    or block.get("thinking")
                                )
                                if rtext:
                                    db_msg = DBMessage(
                                        chat_id=chat_id,
                                        role="assistant",
                                        type="reasoning",
                                        content=rtext,
                                    )
                                    session.add(db_msg)
                elif isinstance(content_val, str) and content_val:
                    db_msg = DBMessage(
                        chat_id=chat_id,
                        role="assistant",
                        type="text",
                        content=content_val,
                    )
                    session.add(db_msg)

                if "reasoning" in msg.additional_kwargs:
                    db_msg = DBMessage(
                        chat_id=chat_id,
                        role="assistant",
                        type="reasoning",
                        content=msg.additional_kwargs["reasoning"],
                    )
                    session.add(db_msg)

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        db_msg = DBMessage(
                            chat_id=chat_id,
                            role="assistant",
                            type="tool_call",
                            name=tc.get("name"),
                            parent_id=tc.get("id"),
                            content=json.dumps(tc.get("args", {})),
                        )
                        session.add(db_msg)
            elif isinstance(msg, ToolMessage):
                db_msg = DBMessage(
                    chat_id=chat_id,
                    role="tool",
                    type="tool_result",
                    content=str(msg.content),
                    parent_id=msg.tool_call_id,
                )
                session.add(db_msg)
            elif isinstance(msg, SystemMessage):
                db_msg = DBMessage(
                    chat_id=chat_id,
                    role="system",
                    type="text",
                    content=str(msg.content),
                )
                session.add(db_msg)
            elif isinstance(msg, HumanMessage):
                db_msg = DBMessage(
                    chat_id=chat_id, role="user", type="text", content=str(msg.content)
                )
                session.add(db_msg)
        session.commit()
    elif not final_state:
        # In case of catastrophic failure where final_state wasn't reached, try to capture what we have
        pass
