import json
from typing import AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from sqlmodel import Session
from duckduckgo_search import DDGS
from langgraph.prebuilt import create_react_agent

from core.db import DATA_DIR
from models.domain import Message as DBMessage, Project
from services.llm_provider import get_llm
from services.ingestion_service import get_vectorstore
from core.config import settings_manager
from prompts.chat_prompts import SYSTEM_PROMPT


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
            print(f"Error during RAG retrieval: {e}")
            return "No context retrieved due to an error."
    else:
        context_file = DATA_DIR / "projects" / project_id / "_consolidated_context.txt"
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                return f.read()
        return "No resources uploaded yet."


def get_chat_history(session: Session, chat_id: str) -> list:
    db_messages = (
        session.query(DBMessage)
        .filter(DBMessage.chat_id == chat_id)
        .order_by(DBMessage.created_at)
        .all()
    )

    langchain_history = []
    for msg in db_messages:
        if msg.role == "user":
            langchain_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_history.append(AIMessage(content=msg.content))

    return langchain_history


def generate_chat_name(project_id: str, chat_id: str, first_message: str):
    llm = get_llm()
    prompt = f"Summarize this message into a short 2 to 4 word chat title. Return ONLY the title text, nothing else. Message: {first_message}"
    try:
        response = llm.invoke(prompt)
        title = str(response.content).strip().strip('"').strip("'")

        from core.db import engine
        from sqlmodel import Session

        with Session(engine) as session:
            from models.domain import Chat

            chat = session.get(Chat, chat_id)
            if chat and chat.name == "New Chat":
                chat.name = title
                session.add(chat)
                session.commit()
    except Exception as e:
        print(f"Error generating chat name: {e}")


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

    @tool
    def web_search(search_query: str) -> str:
        """Search the web using DuckDuckGo to find up-to-date information."""
        try:
            results = DDGS().text(search_query, max_results=3)
            if not results:
                return "No results found."
            return "\n\n".join(
                [
                    f"Title: {r['title']}\nLink: {r['href']}\nSnippet: {r['body']}"
                    for r in results
                ]
            )
        except Exception as e:
            return f"Error: {str(e)}"

    @tool
    def read_notes() -> str:
        """Read the current content of the project's notes document."""
        return get_project_notes(project.id)

    @tool
    def append_notes(content: str) -> str:
        """Append text to the end of the project's notes document. Use to save important findings."""
        try:
            notes_path = DATA_DIR / "projects" / project.id / "notes.md"
            with open(notes_path, "a", encoding="utf-8") as f:
                f.write(f"\n{content}")
            return "Notes appended successfully."
        except Exception as e:
            return f"Error: {str(e)}"

    tools = [web_search, read_notes, append_notes]

    agent = create_react_agent(llm, tools)

    history = get_chat_history(session, chat_id)

    system_message = SystemMessage(
        content=SYSTEM_PROMPT.format(notes=notes, context=context)
    )
    messages = [system_message] + history + [HumanMessage(content=query)]

    user_msg = DBMessage(chat_id=chat_id, role="user", content=query)
    session.add(user_msg)
    session.commit()

    full_response = ""
    try:
        async for event in agent.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    content = chunk.content
                    if isinstance(content, list):
                        content = "".join(
                            str(c.get("text", "")) if isinstance(c, dict) else str(c)
                            for c in content
                        )
                    full_response += str(content)
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

    except Exception as e:
        import traceback

        traceback.print_exc()
        error_msg = f"\n\nError generating response: {str(e)}"
        full_response += error_msg
        yield yield_func(json.dumps({"type": "content", "content": error_msg}))

    if full_response:
        assistant_msg = DBMessage(
            chat_id=chat_id, role="assistant", content=full_response
        )
        session.add(assistant_msg)
        session.commit()
