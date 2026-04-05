from langchain_core.tools import tool
from duckduckgo_search import DDGS
from core.db import DATA_DIR
from models.domain import Project


def get_project_notes(project_id: str) -> str:
    notes_path = DATA_DIR / "projects" / project_id / "notes.md"
    if notes_path.exists():
        with open(notes_path, "r", encoding="utf-8") as f:
            return f.read()
    return "No notes currently saved."


def create_project_tools(project: Project):
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
    def edit_notes(old_text: str, new_text: str) -> str:
        """Edit the project's notes document. Replaces old_text with new_text in the note document."""
        notes_path = DATA_DIR / "projects" / project.id / "notes.md"
        try:
            with open(notes_path, "r") as f:
                content = f.read()

            occurrence_count = content.count(old_text)
            if occurrence_count == 0:
                return f"Error: Could not find '{old_text}' in {notes_path} . No changes made."
            elif occurrence_count > 1:
                return (
                    f"Error: Found {occurrence_count} matches for '{old_text}'. "
                    "To avoid accidental changes, please provide more surrounding context "
                    "to uniquely identify the block you want to replace."
                )
            else:
                new_content = content.replace(old_text, new_text)
                with open(notes_path, "w") as f:
                    f.write(new_content)
                return f"Successfully replaced the unique occurrence of text in {notes_path}."
        except FileNotFoundError:
            return f"Error: File not found at {notes_path}."
        except Exception as e:
            return f"Error: {str(e)}"

    @tool
    def overwrite_notes(content: str) -> str:
        """Overwrite the text content of the project's notes document. Use to replace the content of the note file entirely with new text."""
        try:
            notes_path = DATA_DIR / "projects" / project.id / "notes.md"
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(f"\n{content}")
            return "Notes appended successfully."
        except Exception as e:
            return f"Error: {str(e)}"

    return [web_search, read_notes, edit_notes, overwrite_notes]
