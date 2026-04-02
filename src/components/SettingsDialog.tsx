import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useTheme } from "@/components/ThemeProvider"
import { api, Settings } from "@/lib/api"
import { Loader2 } from "lucide-react"

const CONFIG = {
  providers: [
    { id: "vertexai", name: "Vertex AI" },
    { id: "openai", name: "OpenAI" },
    { id: "ollama", name: "Ollama" },
  ] as const,
  defaults: {
    provider: "vertexai",
    models: {
      vertexai: "gemini-3-flash",
      openai: "gpt-5-mini",
      ollama: "llama3",
    },
    embeddings: {
      vertexai: "text-embedding-004",
      openai: "text-embedding-3-large",
      ollama: "nomic-embed-text",
    },
    urls: {
      ollama: "http://localhost:11434",
    },
    locations: {
      vertexai: "global",
    },
    ragThreshold: 100000,
  },
  modelOptions: {
    vertexai: [
      { id: "gemini-3-flash", name: "Gemini 3.0 Flash" },
      { id: "gemini-3.1-pro-preview", name: "Gemini 3.1 Pro" },
    ],
    openai: [
      { id: "gpt-5-mini", name: "GPT-5 Mini" },
      { id: "gpt-5.4", name: "GPT-5.4" },
    ],
  } as Record<string, { id: string; name: string }[]>,
}

export default function SettingsDialog({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useTheme()
  const [settings, setSettings] = useState<Partial<Settings>>({
    provider: CONFIG.defaults.provider,
    model: CONFIG.defaults.models.vertexai,
    ollama_url: CONFIG.defaults.urls.ollama,
    openai_key: "",
    vertex_project: "",
    vertex_location: CONFIG.defaults.locations.vertexai,
    rag_threshold: CONFIG.defaults.ragThreshold
  })
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true)
      api.settings.get()
        .then(data => {
          setSettings(data)
          if (data.theme) {
            setTheme(data.theme as any)
          }
        })
        .catch(console.error)
        .finally(() => setIsLoading(false))
    }
  }, [isOpen])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // Auto-configure embedding models based on provider selection
      const updates = { ...settings, theme }
      if (updates.provider === "vertexai") {
        updates.embedding_provider = "vertexai"
        updates.embedding_model = CONFIG.defaults.embeddings.vertexai
      } else if (updates.provider === "openai") {
        updates.embedding_provider = "openai"
        updates.embedding_model = CONFIG.defaults.embeddings.openai
      } else if (updates.provider === "ollama") {
        updates.embedding_provider = "ollama"
        updates.embedding_model = CONFIG.defaults.embeddings.ollama
      }

      await api.settings.update(updates)
      setIsOpen(false)
    } catch (e) {
      console.error("Failed to save settings:", e)
      alert("Failed to save settings")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen} modal={false}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Global Settings</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto pr-2">

            <div className="grid gap-2 mb-2 pb-4 border-b">
              <Label>Theme</Label>
              <Select value={theme} onValueChange={(v: any) => setTheme(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="system">System Default</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2 mb-2">
              <Label>Provider</Label>
              <div className="flex bg-muted p-1 rounded-md gap-1">
                {CONFIG.providers.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSettings({
                      ...settings,
                      provider: p.id,
                      model: p.id === "vertexai" ? CONFIG.defaults.models.vertexai
                        : p.id === "openai" ? CONFIG.defaults.models.openai
                          : CONFIG.defaults.models.ollama
                    })}
                    className={`flex-1 text-xs py-1.5 px-2 rounded-sm font-medium transition-colors ${settings.provider === p.id
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-background/50 hover:text-foreground"
                      }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {settings.provider === "vertexai" && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-1 duration-200">
                <div className="grid gap-2">
                  <Label>Model</Label>
                  <Select value={settings.model || CONFIG.defaults.models.vertexai} onValueChange={(v) => { if (v) setSettings({ ...settings, model: v }) }}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONFIG.modelOptions.vertexai.map(m => (
                        <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label>GCP Project ID</Label>
                  <Input
                    value={settings.vertex_project || ""}
                    onChange={e => setSettings({ ...settings, vertex_project: e.target.value })}
                    placeholder="my-gcp-project-123"
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Location</Label>
                  <Input
                    value={settings.vertex_location || CONFIG.defaults.locations.vertexai}
                    onChange={e => setSettings({ ...settings, vertex_location: e.target.value })}
                    placeholder="us-central1"
                  />
                </div>
              </div>
            )}

            {settings.provider === "openai" && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-1 duration-200">
                <div className="grid gap-2">
                  <Label>Model</Label>
                  <Select value={settings.model || CONFIG.defaults.models.openai} onValueChange={(v) => { if (v) setSettings({ ...settings, model: v }) }}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONFIG.modelOptions.openai.map(m => (
                        <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    value={settings.openai_key || ""}
                    onChange={e => setSettings({ ...settings, openai_key: e.target.value })}
                    placeholder="sk-..."
                  />
                </div>
              </div>
            )}

            {settings.provider === "ollama" && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-1 duration-200">
                <div className="grid gap-2">
                  <Label>Model Name</Label>
                  <Input
                    value={settings.model || CONFIG.defaults.models.ollama}
                    onChange={e => setSettings({ ...settings, model: e.target.value })}
                    placeholder="llama3, mistral..."
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Base URL</Label>
                  <Input
                    value={settings.ollama_url || CONFIG.defaults.urls.ollama}
                    onChange={e => setSettings({ ...settings, ollama_url: e.target.value })}
                  />
                </div>
              </div>
            )}

            <div className="grid gap-2 mt-2 pt-4 border-t">
              <Label>RAG Threshold (Tokens)</Label>
              <p className="text-[10px] text-muted-foreground mb-1 leading-tight">Switch from full-text to vector search when context exceeds this size.</p>
              <Input
                type="number"
                value={settings.rag_threshold || CONFIG.defaults.ragThreshold}
                onChange={e => setSettings({ ...settings, rag_threshold: parseInt(e.target.value) || CONFIG.defaults.ragThreshold })}
              />
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2 border-t">
          <Button onClick={handleSave} disabled={isLoading || isSaving}>
            {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
