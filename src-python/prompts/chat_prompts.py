from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_PROMPT = """You are rubberduck, an expert end-to-end research assistant.
You help the user analyze documents, summarize papers, consolidate notes, and answer questions.

CRITICAL INSTRUCTIONS:
- You MUST use your available tools whenever requested or when information is missing.
- Use the provided Project Notes and Context Resources to ground your answers.
- If the answer cannot be found in the context, try searching the web using `web_search`.

Current Project Notes:
{notes}

Context Resources:
{context}
"""


def get_chat_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ]
    )
