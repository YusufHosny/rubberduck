import { invoke } from "@tauri-apps/api/core";

export interface Project {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export interface Resource {
  id: string
  project_id: string
  name: string
  type: "pdf" | "link" | "text"
  token_count: number
  file_path: string | null
  url: string | null
  created_at: string
}

export interface Chat {
  id: string
  project_id: string
  name: string
  created_at: string
}

export interface Message {
  id?: string
  chat_id?: string
  role: "user" | "assistant" | "system"
  content: string
  created_at?: string
  tools?: {name: string, input?: any, completed?: boolean}[]
}

export interface Notes {
  content: string
}

export interface Settings {
  theme: string
  provider: string
  model: string
  embedding_provider: string
  embedding_model: string
  rag_threshold: number
  chunk_size: number
  chunk_overlap: number
  openai_key: string
  vertex_project: string
  vertex_location: string
  ollama_url: string
  primary_port: number
  fallback_port: number
  debug_logging: boolean
}

export interface LogEntry {
  time: string
  level: string
  message: string
  name: string
  file: string
  line: number
}

class ApiClient {
  private baseUrl: string | null = null;
  private primaryPort = 38438;
  private fallbackPort = 38439;

  async initialize(retries = 3): Promise<void> {
    try {
      const settingsStr = await invoke<string>("get_settings");
      if (settingsStr) {
        const settings = JSON.parse(settingsStr);
        if (settings.primary_port) this.primaryPort = settings.primary_port;
        if (settings.fallback_port) this.fallbackPort = settings.fallback_port;
      }
    } catch (e) {
      console.warn("Failed to load settings via tauri, using default ports", e);
    }

    for (let i = 0; i < retries; i++) {
      try {
        const url = `http://localhost:${this.primaryPort}`;
        const res = await fetch(`${url}/health`);
        if (res.ok) {
          const data = await res.json().catch(() => ({}));
          if (data.verify_rubberduck === true) {
            this.baseUrl = url;
            return;
          }
        }
      } catch (e) {
        // Fall through
      }

      try {
        const url = `http://localhost:${this.fallbackPort}`;
        const res = await fetch(`${url}/health`);
        if (res.ok) {
          const data = await res.json().catch(() => ({}));
          if (data.verify_rubberduck === true) {
            this.baseUrl = url;
            return;
          }
        }
      } catch (e) {
        // Fall through
      }

      if (i < retries - 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }

    throw new Error("couldnt initialize (ports are in use by other processes, set a custom port)");
  }

  private getUrl(path: string): string {
    if (!this.baseUrl) {
      throw new Error("API client not initialized");
    }
    return `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  }

  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const url = this.getUrl(path);
    const res = await fetch(url, options);

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Unknown error");
      throw new Error(`API Error (${res.status}): ${errorText}`);
    }

    if (res.status === 204 || res.headers.get("content-length") === "0") {
      return {} as T;
    }

    return res.json() as Promise<T>;
  }

  public readonly settings = {
    get: () => this.fetch<Settings>("/settings/"),
    update: (settings: Partial<Settings>) =>
      this.fetch<Settings>("/settings/", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      }),
  };

  public readonly projects = {
    list: () => this.fetch<Project[]>("/projects"),
    create: (name: string) =>
      this.fetch<Project>("/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      }),
    delete: (id: string) =>
      this.fetch<void>(`/projects/${id}`, { method: "DELETE" }),

    resources: {
      list: (projectId: string) =>
        this.fetch<Resource[]>(`/projects/${projectId}/resources`),
      addLink: (projectId: string, url: string, name: string) =>
        this.fetch<Resource>(`/projects/${projectId}/resources/link`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, name, type: "link" }),
        }),
      addPdf: (projectId: string, file: File) => {
        const formData = new FormData();
        formData.append("file", file);
        return this.fetch<Resource>(`/projects/${projectId}/resources/upload`, {
          method: "POST",
          body: formData,
        });
      },
      delete: (projectId: string, resourceId: string) =>
        this.fetch<void>(`/projects/${projectId}/resources/${resourceId}`, {
          method: "DELETE",
        }),
    },

    chats: {
      list: (projectId: string) =>
        this.fetch<Chat[]>(`/projects/${projectId}/chats`),
      create: (projectId: string, name: string) =>
        this.fetch<Chat>(`/projects/${projectId}/chats`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        }),
      getHistory: (projectId: string, chatId: string) =>
        this.fetch<Message[]>(`/projects/${projectId}/chats/${chatId}`),
      getTokens: (projectId: string, chatId: string) =>
        this.fetch<{tokens: number}>(`/projects/${projectId}/chats/${chatId}/tokens`),
      update: (projectId: string, chatId: string, name: string) =>
        this.fetch<void>(`/projects/${projectId}/chats/${chatId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        }),
      delete: (projectId: string, chatId: string) =>
        this.fetch<void>(`/projects/${projectId}/chats/${chatId}`, {
          method: "DELETE",
        }),
      send: (
        projectId: string,
        chatId: string,
        content: string,
        signal?: AbortSignal
      ) => {
        return fetch(this.getUrl(`/projects/${projectId}/chats/${chatId}/messages`), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: "user", content }),
          signal,
        });
      },
    },

    notes: {
      get: (projectId: string) =>
        this.fetch<Notes>(`/projects/${projectId}/notes`),
      save: (projectId: string, content: string) =>
        this.fetch<void>(`/projects/${projectId}/notes`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
        }),
    },
  };

  public readonly logs = {
    history: () => this.fetch<LogEntry[]>("/logs/history"),
    streamUrl: () => this.getUrl("/logs/stream"),
  };
}

export const api = new ApiClient();
