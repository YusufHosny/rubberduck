import { PlusCircle, Folder, Settings, FileText, Link as LinkIcon, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useState, useEffect } from "react"
import SettingsDialog from "@/components/SettingsDialog"
import { api, Project, Resource } from "@/lib/api"
import { toast } from "sonner"

export default function Sidebar({ activeProjectId, setActiveProjectId }: { activeProjectId: string | null, setActiveProjectId: (id: string | null) => void }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [isAddResourceOpen, setIsAddResourceOpen] = useState(false)
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")

  const fetchProjects = async () => {
    try {
      const data = await api.projects.list()
      setProjects(data)
    } catch (e) { console.error(e) }
  }

  const fetchResources = async () => {
    if (!activeProjectId) {
      setResources([])
      return
    }
    try {
      const data = await api.projects.resources.list(activeProjectId)
      setResources(data)
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  useEffect(() => {
    fetchResources()
  }, [activeProjectId])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return
    const promise = api.projects.create(newProjectName).then(() => {
      fetchProjects()
      setIsNewProjectOpen(false)
      setNewProjectName("")
    })
    
    toast.promise(promise, {
      loading: 'Creating project...',
      success: 'Project created!',
      error: 'Failed to create project'
    })
  }

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm("Are you sure you want to delete this project?")) return
    const promise = api.projects.delete(id).then(() => {
      if (activeProjectId === id) setActiveProjectId(null)
      fetchProjects()
    })

    toast.promise(promise, {
      loading: 'Deleting project...',
      success: 'Project deleted!',
      error: 'Failed to delete project'
    })
  }

  const handleDeleteResource = async (id: string) => {
    if (!activeProjectId) return;
    const promise = api.projects.resources.delete(activeProjectId, id).then(() => {
      fetchResources()
    })
    
    toast.promise(promise, {
      loading: 'Deleting resource...',
      success: 'Resource deleted!',
      error: 'Failed to delete resource'
    })
  }

  const handleAddLink = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!activeProjectId) return;
    const formData = new FormData(e.currentTarget)
    const url = formData.get("url") as string
    const name = formData.get("name") as string

    const promise = api.projects.resources.addLink(activeProjectId, url, name).then(() => {
      setIsAddResourceOpen(false)
      fetchResources()
    })

    toast.promise(promise, {
      loading: 'Fetching and processing link...',
      success: 'Link added to context!',
      error: 'Failed to process link'
    })
  }

  const handleAddFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !activeProjectId) return

    const promise = api.projects.resources.addPdf(activeProjectId, file).then(() => {
      setIsAddResourceOpen(false)
      fetchResources()
    })

    toast.promise(promise, {
      loading: 'Uploading and parsing PDF...',
      success: 'PDF added to context!',
      error: 'Failed to upload PDF'
    })
  }

  const totalTokens = resources.reduce((acc, r) => acc + (r.token_count || 0), 0)

  return (
    <div className="flex flex-col h-full bg-muted/20 border-r">
      <div className="p-4 border-b flex items-center justify-between shrink-0">
        <h2 className="font-bold font-ancola flex items-center gap-2">
          <img src="/rubberduck.png" alt="Rubberduck" className="w-6 h-6 object-contain drop-shadow-sm" />
          rubberduck
        </h2>
        <Dialog open={isNewProjectOpen} onOpenChange={setIsNewProjectOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <PlusCircle className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New Project</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4 pt-4">
              <div className="grid gap-2">
                <Label>Project Name</Label>
                <Input 
                  value={newProjectName} 
                  onChange={(e) => setNewProjectName(e.target.value)} 
                  placeholder="e.g. My Awesome Research" 
                  autoFocus
                  required 
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={!newProjectName.trim()}>Create</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <ScrollArea className="flex-1 p-2">
        <div className="space-y-1 mb-6">
          <h3 className="text-xs font-semibold text-muted-foreground px-2 py-1 uppercase tracking-wider">Projects</h3>
          {projects.map(p => (
            <div key={p.id} className="flex items-center group">
              <Button
                variant={activeProjectId === p.id ? "secondary" : "ghost"}
                className="flex-1 justify-start gap-2 h-9 text-sm truncate px-2"
                onClick={() => setActiveProjectId(p.id)}
              >
                <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{p.name}</span>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                onClick={(e) => handleDeleteProject(p.id, e)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>

        {activeProjectId && (
          <div className="space-y-1">
            <div className="flex items-center justify-between px-2 py-1 mb-1">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Context</h3>
              <Dialog open={isAddResourceOpen} onOpenChange={setIsAddResourceOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-5 w-5">
                    <PlusCircle className="h-3.5 w-3.5" />
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Context</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 pt-4">
                    <div className="grid gap-2">
                      <Label>Upload PDF</Label>
                      <Input type="file" accept=".pdf" onChange={handleAddFile} />
                    </div>
                    <div className="relative">
                      <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
                      <div className="relative flex justify-center text-xs uppercase"><span className="bg-background px-2 text-muted-foreground">Or</span></div>
                    </div>
                    <form onSubmit={handleAddLink} className="grid gap-4">
                      <div className="grid gap-2">
                        <Label>Add Web Link</Label>
                        <Input name="url" placeholder="https://arxiv.org/abs/..." required />
                      </div>
                      <div className="grid gap-2">
                        <Label>Name / Label</Label>
                        <Input name="name" placeholder="Attention is all you need" required />
                      </div>
                      <Button type="submit">Fetch Link</Button>
                    </form>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {resources.length === 0 ? (
              <div className="text-xs text-muted-foreground px-2 py-4 text-center border border-dashed rounded-md mx-2">
                Empty context.<br />Add PDFs or Links.
              </div>
            ) : (
              resources.map(r => (
                <div key={r.id} className="flex items-center justify-between px-2 py-1.5 text-xs group hover:bg-muted/50 rounded-md mx-1 transition-colors">
                  <div className="flex items-center gap-2 truncate">
                    {r.type === 'pdf' ? <FileText className="h-3 w-3 text-blue-500" /> : <LinkIcon className="h-3 w-3 text-green-500" />}
                    <span className="truncate">{r.name}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 shrink-0 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                    onClick={() => handleDeleteResource(r.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))
            )}

            <div className="px-3 pt-2 text-[10px] text-muted-foreground flex justify-between items-center">
              <span>Tokens</span>
              <span className={totalTokens > 100000 ? "text-amber-500 font-medium" : ""}>~{totalTokens.toLocaleString()}</span>
            </div>
          </div>
        )}
      </ScrollArea>

      <div className="p-2 border-t shrink-0">
        <SettingsDialog>
          <Button variant="ghost" className="w-full justify-start gap-2 h-9 text-sm text-muted-foreground">
            <Settings className="h-4 w-4" />
            Global Settings
          </Button>
        </SettingsDialog>
      </div>
    </div>
  )
}
