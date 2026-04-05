from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from core.config import settings_manager


class ProviderFactory:
    @staticmethod
    def get_llm() -> BaseChatModel:
        settings = settings_manager.get()
        provider = settings.provider.lower()
        model_name = settings.model

        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name, api_key=settings.openai_key, temperature=0.3 # type: ignore
            )

        elif provider == "vertexai":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.3,
                project=settings.vertex_project,
                location=settings.vertex_location,
                vertexai=True,

                thinking_level='high',
                include_thoughts=True,
            )

        elif provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=model_name, base_url=settings.ollama_url, temperature=0.3
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def get_embeddings() -> Embeddings:
        settings = settings_manager.get()
        provider = settings.embedding_provider.lower()
        model_name = settings.embedding_model

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(model=model_name, api_key=settings.openai_key)

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


def get_llm() -> BaseChatModel:
    return ProviderFactory.get_llm()


def get_embeddings() -> Embeddings:
    return ProviderFactory.get_embeddings()
