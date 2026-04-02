import { useState, useRef, useEffect } from "react"
import { PanelImperativeHandle, PanelSize } from "react-resizable-panels"
import { ChevronLeft, ChevronRight, Loader2, AlertCircle } from "lucide-react"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import Sidebar from "@/components/Sidebar"
import ChatArea from "@/components/ChatArea"
import NotesPanel from "@/components/NotesPanel"
import { Toaster } from "sonner"
import { api } from "@/lib/api"

function App() {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)
  const [initError, setInitError] = useState<string | null>(null)

  const leftPanelRef = useRef<PanelImperativeHandle>(null)
  const rightPanelRef = useRef<PanelImperativeHandle>(null)

  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false)
  const [isRightCollapsed, setIsRightCollapsed] = useState(false)

  useEffect(() => {
    api.initialize()
      .then(() => {
        setIsInitializing(false)
      })
      .catch((err: Error) => {
        console.error("Failed to initialize API:", err)
        setInitError(err.message)
        setIsInitializing(false)
      })
  }, [])

  const toggleLeftPanel = () => {
    const panel = leftPanelRef.current
    if (panel) {
      if (panel.isCollapsed()) {
        panel.expand()
      } else {
        panel.collapse()
      }
    }
  }

  const toggleRightPanel = () => {
    const panel = rightPanelRef.current
    if (panel) {
      if (panel.isCollapsed()) {
        panel.expand()
      } else {
        panel.collapse()
      }
    }
  }

  if (isInitializing) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-background text-foreground">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Starting local services...</p>
      </div>
    )
  }

  if (initError) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-background text-foreground p-4">
        <div className="flex flex-col items-center max-w-md text-center">
          <AlertCircle className="h-12 w-12 text-destructive mb-4" />
          <h2 className="text-xl font-semibold mb-2">Initialization Failed</h2>
          <p className="text-muted-foreground">{initError}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-background text-foreground overflow-hidden">
      <Toaster position="bottom-right" richColors />
      <ResizablePanelGroup orientation="horizontal" className="flex h-full w-full">
        <ResizablePanel
          ref={leftPanelRef}
          collapsible={true}
          collapsedSize={0}
          onResize={(size: PanelSize) => setIsLeftCollapsed(size.asPercentage === 0)}
          defaultSize={"20%"}
          minSize={"15%"}
          maxSize={"25%"}
          className="bg-sidebar min-w-0 transition-all duration-300 ease-in-out z-10"
        >
          <Sidebar
            activeProjectId={activeProjectId}
            setActiveProjectId={setActiveProjectId}
          />
        </ResizablePanel>

        <ResizableHandle className="w-1.5 hover:bg-muted/50 transition-colors z-10" />

        <ResizablePanel minSize={"30%"} className="min-w-0 relative">
          <button
            onClick={toggleLeftPanel}
            className="fixed left-0 top-1/2 -translate-y-1/2 z-10 flex h-12 w-4 items-center justify-center rounded-r-md border border-l-0 bg-background shadow-sm hover:bg-accent hover:text-accent-foreground text-muted-foreground transition-all focus:outline-hidden"
            aria-label={isLeftCollapsed ? "Expand project sidebar" : "Collapse project sidebar"}
          >
            {isLeftCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>

          <button
            onClick={toggleRightPanel}
            className="fixed right-0 top-1/2 -translate-y-1/2 z-10 flex h-12 w-4 items-center justify-center rounded-l-md border border-r-0 bg-background shadow-sm hover:bg-accent hover:text-accent-foreground text-muted-foreground transition-all focus:outline-hidden"
            aria-label={isRightCollapsed ? "Expand notes" : "Collapse notes"}
          >
            {isRightCollapsed ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
          </button>

          {activeProjectId ? (
            <ChatArea key={activeProjectId} projectId={activeProjectId} />
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground p-4 text-center">
              Select or create a project to start
            </div>
          )}
        </ResizablePanel>

        <ResizableHandle className="w-1.5 hover:bg-muted/50 transition-colors" />

        <ResizablePanel
          ref={rightPanelRef}
          collapsible={true}
          collapsedSize={0}
          onResize={(size: PanelSize) => setIsRightCollapsed(size.asPercentage === 0)}
          defaultSize={"30%"}
          minSize={"20%"}
          maxSize={"40%"}
          className="bg-sidebar min-w-0 transition-all duration-300 ease-in-out"
        >
          {activeProjectId ? (
            <NotesPanel projectId={activeProjectId} />
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground border-l">
              Notes
            </div>
          )}
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}

export default App
