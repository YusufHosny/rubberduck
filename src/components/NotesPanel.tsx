import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Save, RefreshCw } from "lucide-react"
import { api } from "@/lib/api"
import MDEditor from '@uiw/react-md-editor'
import { toast } from "sonner"
import { useTheme } from "./ThemeProvider"

export default function NotesPanel({ projectId }: { projectId: string }) {
  const [content, setContent] = useState("")
  const [saving, setSaving] = useState(false)
  const { theme } = useTheme()
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('dark')

  useEffect(() => {
    if (theme === 'system') {
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      setResolvedTheme(isDark ? 'dark' : 'light')
    } else {
      setResolvedTheme(theme as 'light' | 'dark')
    }
  }, [theme])

  const fetchNotes = async () => {
    try {
      const data = await api.projects.notes.get(projectId)
      setContent(data.content || "")
    } catch(e) { console.error(e) }
  }

  useEffect(() => {
    fetchNotes()
  }, [projectId])

  const saveNotes = async () => {
    setSaving(true)
    const promise = api.projects.notes.save(projectId, content).finally(() => setSaving(false))
    
    toast.promise(promise, {
      loading: 'Saving notes...',
      success: 'Notes saved!',
      error: 'Failed to save notes'
    })
  }

  return (
    <div className="flex flex-col h-full bg-background border-l relative" data-color-mode={resolvedTheme}>
      <div className="h-14 border-b flex items-center justify-between px-4 shrink-0 shadow-sm bg-background/95 backdrop-blur z-10">
        <h3 className="font-medium text-sm flex items-center gap-2">
          Notes
        </h3>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={fetchNotes}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" className="h-8 gap-2 text-xs" onClick={saveNotes} disabled={saving}>
            <Save className="h-3 w-3" />
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>
      
      <div className="flex-1 overflow-hidden" data-color-mode={resolvedTheme}>
        <MDEditor
          value={content}
          onChange={(val) => setContent(val || "")}
          preview="edit"
          height="100%"
          className="h-full border-0 !rounded-none !shadow-none"
          visibleDragbar={false}
          textareaProps={{
            placeholder: "Write your research notes here, or ask rubberduck to consolidate findings into this document..."
          }}
        />
      </div>
    </div>
  )
}
