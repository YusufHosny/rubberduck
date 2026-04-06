from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from core.config import settings_manager
from core.logger import LoguruCallbackHandler


class ProviderFactory:
    @staticmethod
    def get_llm(**kwargs) -> BaseChatModel:
        settings = settings_manager.get()
        provider = settings.provider.lower()
        model_name = settings.model

        callbacks = kwargs.get("callbacks", [])
        if not any(isinstance(cb, LoguruCallbackHandler) for cb in callbacks):
            callbacks.append(LoguruCallbackHandler())
        kwargs["callbacks"] = callbacks

        if provider == "openai":
            from langchain_openai import ChatOpenAI

            openai_kwargs = {
                "model": model_name,
                "api_key": settings.openai_key,
                "temperature": 0.3,
            }
            safe_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k not in ["thinking_level", "include_thoughts"]
            }
            openai_kwargs.update(safe_kwargs)
            return ChatOpenAI(**openai_kwargs)  # type: ignore

        elif provider == "vertexai":
            from langchain_google_genai import ChatGoogleGenerativeAI

            vertex_kwargs = {
                "model": model_name,
                "temperature": 0.3,
                "project": settings.vertex_project,
                "location": settings.vertex_location,
                "vertexai": True,
                "thinking_level": "high",
                "include_thoughts": True,
            }
            vertex_kwargs.update(kwargs)
            return ChatGoogleGenerativeAI(**vertex_kwargs)

        elif provider == "ollama":
            from langchain_ollama import ChatOllama

            ollama_kwargs = {
                "model": model_name,
                "base_url": settings.ollama_url,
                "temperature": 0.3,
            }
            safe_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k not in ["thinking_level", "include_thoughts"]
            }
            ollama_kwargs.update(safe_kwargs)
            return ChatOllama(**ollama_kwargs)

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def get_embeddings() -> Embeddings:
        settings = settings_manager.get()
        provider = settings.embedding_provider.lower()
        model_name = settings.embedding_model

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(model=model_name, api_key=lambda: settings.openai_key)

        elif provider == "vertexai":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            return GoogleGenerativeAIEmbeddings(
                model=model_name,
                project=settings.vertex_project,
                location=settings.vertex_location,
                vertexai=True,
            )

        elif provider == "ollama":
            from langchain_ollama import OllamaEmbeddings

            return OllamaEmbeddings(model=model_name, base_url=settings.ollama_url)

        else:
            raise ValueError(f"Unsupported Embeddings provider: {provider}")


def get_llm(**kwargs) -> BaseChatModel:
    return ProviderFactory.get_llm(**kwargs)


def get_embeddings() -> Embeddings:
    return ProviderFactory.get_embeddings()
