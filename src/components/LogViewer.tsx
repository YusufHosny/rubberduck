import { useState, useEffect, useRef } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api, LogEntry } from "@/lib/api"

export default function LogViewer({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [filter, setFilter] = useState("")
  const [levelFilter, setLevelFilter] = useState("ALL")
  const [autoScroll, setAutoScroll] = useState(true)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    api.logs.history()
      .then(history => setLogs(history))
      .catch(console.error)

    const eventSource = new EventSource(api.logs.streamUrl())

    eventSource.onmessage = (event) => {
      try {
        const logData: LogEntry = JSON.parse(event.data)
        setLogs(prev => {
          const next = [...prev, logData]
          if (next.length > 1000) return next.slice(next.length - 1000)
          return next
        })
      } catch (e) {
        console.error("Failed to parse log message", e)
      }
    }

    return () => {
      eventSource.close()
    }
  }, [isOpen])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "instant" })
    }
  }, [logs, autoScroll])

  const handleScroll = () => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10
    setAutoScroll(isAtBottom)
  }

  const getLevelColor = (level: string) => {
    switch (level) {
      case "ERROR": return "text-red-400"
      case "WARNING": return "text-yellow-400"
      case "INFO": return "text-blue-300"
      case "DEBUG": return "text-slate-500"
      default: return "text-slate-300"
    }
  }

  const filteredLogs = logs.filter(log => {
    if (levelFilter !== "ALL" && log.level !== levelFilter) return false
    if (filter) {
      const lowerFilter = filter.toLowerCase()
      return (
        log.message.toLowerCase().includes(lowerFilter) ||
        log.name.toLowerCase().includes(lowerFilter) ||
        log.file.toLowerCase().includes(lowerFilter)
      )
    }
    return true
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-5xl w-[90vw] h-[85vh] flex flex-col gap-0 p-0 overflow-hidden">
        <DialogHeader className="px-4 py-3 border-b shrink-0 flex flex-row items-center justify-between">
          <DialogTitle>Developer Logs</DialogTitle>
          <div className="flex items-center gap-2 pr-6">
            <Input
              placeholder="Filter logs..."
              value={filter}
              onChange={e => setFilter(e.target.value)}
              className="w-48 h-8 text-xs"
            />
            <Select value={levelFilter} onValueChange={(v) => { if (v) setLevelFilter(v) }}>
              <SelectTrigger className="w-32 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Levels</SelectItem>
                <SelectItem value="ERROR">Error</SelectItem>
                <SelectItem value="WARNING">Warning</SelectItem>
                <SelectItem value="INFO">Info</SelectItem>
                <SelectItem value="DEBUG">Debug</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2 text-xs text-muted-foreground whitespace-nowrap ml-2 border-l pl-4">
              <input
                type="checkbox"
                id="autoscroll"
                checked={autoScroll}
                onChange={e => setAutoScroll(e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="autoscroll">Auto-scroll</label>
            </div>
          </div>
        </DialogHeader>

        <div
          className="flex-1 bg-[#09090b] p-4 overflow-y-auto font-mono text-[11px] leading-relaxed relative"
          ref={containerRef}
          onScroll={handleScroll}
        >
          {filteredLogs.map((log, idx) => (
            <div key={idx} className="flex gap-3 hover:bg-white/5 py-0.5 rounded-sm px-1">
              <span className="text-slate-500 shrink-0 select-none">
                {log.time.split("T")[1].substring(0, 12)}
              </span>
              <span className={`shrink-0 w-16 select-none font-semibold ${getLevelColor(log.level)}`}>
                {log.level}
              </span>
              <span className="text-slate-400 shrink-0 select-none w-32 truncate" title={`${log.name}:${log.line}`}>
                {log.name}:{log.line}
              </span>
              <span className="text-slate-200 whitespace-pre-wrap break-all">
                {log.message}
              </span>
            </div>
          ))}
          <div ref={logsEndRef} className="h-1" />
        </div>
      </DialogContent>
    </Dialog>
  )
}
