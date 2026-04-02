import { useState, useEffect, useRef } from "react"
import { Send, Plus, Trash2, Edit2, Check, X, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { api, Chat, Message } from "@/lib/api"
import { toast } from "sonner"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export default function ChatArea({ projectId }: { projectId: string }) {
  const [chats, setChats] = useState<Chat[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [isWaiting, setIsWaiting] = useState(false)
  const [totalTokens, setTotalTokens] = useState(0)

  // Rename state
  const [isEditingName, setIsEditingName] = useState(false)
  const [editNameValue, setEditNameValue] = useState("")

  const scrollRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const fetchChats = async () => {
    try {
      const data = await api.projects.chats.list(projectId)
      setChats(data)
      if (data.length > 0 && !activeChatId) {
        setActiveChatId(data[0].id)
      } else if (data.length === 0) {
        const newChat = await api.projects.chats.create(projectId, "New Chat")
        setActiveChatId(newChat.id)
        setChats([newChat])
      }
    } catch (e) { console.error(e) }
  }

  const fetchHistory = async () => {
    if (!activeChatId) return
    try {
      const data = await api.projects.chats.getHistory(projectId, activeChatId)
      setMessages(data)
    } catch (e) { console.error(e) }
  }

  const fetchTokens = async () => {
    if (!activeChatId) {
      try {
        const res = await api.projects.resources.list(projectId)
        const tokens = res.reduce((acc, r) => acc + (r.token_count || 0), 0)
        setTotalTokens(tokens)
      } catch (e) { console.error(e) }
      return;
    }

    try {
      const res = await api.projects.chats.getTokens(projectId, activeChatId)
      setTotalTokens(res.tokens)
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    fetchChats()
  }, [projectId])

  useEffect(() => {
    fetchHistory()
    fetchTokens()
  }, [activeChatId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, isWaiting])

  const createNewChat = async () => {
    try {
      const newChat = await api.projects.chats.create(projectId, "New Chat")
      setActiveChatId(newChat.id)
      setMessages([])
      setChats([newChat, ...chats])
    } catch (e) {
      toast.error("Failed to create chat")
    }
  }

  const handleDeleteChat = async () => {
    if (!activeChatId) return
    if (!confirm("Delete this chat?")) return
    try {
      await api.projects.chats.delete(projectId, activeChatId)
      setActiveChatId(null)
      setMessages([])
      fetchChats()
      toast.success("Chat deleted")
    } catch (e) {
      toast.error("Failed to delete chat")
    }
  }

  const handleRenameChat = async () => {
    if (!activeChatId || !editNameValue.trim()) return
    try {
      await api.projects.chats.update(projectId, activeChatId, editNameValue)
      setIsEditingName(false)
      fetchChats()
    } catch (e) {
      toast.error("Failed to rename chat")
    }
  }

  const stopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setIsGenerating(false)
      setIsWaiting(false)
    }
  }

  const handleSubmit = async () => {
    if (isGenerating) {
      stopGenerating()
      return
    }
    if (!input.trim() || !activeChatId) return

    const userMsg = input
    setInput("")
    setMessages(prev => [...prev, { role: "user", content: userMsg }])
    setIsGenerating(true)
    setIsWaiting(true)

    abortControllerRef.current = new AbortController()

    try {
      const response = await api.projects.chats.send(
        projectId,
        activeChatId,
        userMsg,
        abortControllerRef.current.signal
      )

      if (!response.ok) {
        throw new Error(`API Error (${response.status})`)
      }

      if (!response.body) throw new Error("No response body")

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let assistantMsg = ""
      let activeTools: { name: string, input?: any, completed?: boolean }[] = []

      setMessages(prev => [...prev, { role: "assistant", content: "", tools: [] }])

      let buffer = ""
      let isDone = false
      let firstChunkReceived = false

      while (!isDone) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true }).replace(/\r/g, '')

        let boundaryIndex
        while ((boundaryIndex = buffer.indexOf("\n\n")) >= 0) {
          const chunk = buffer.slice(0, boundaryIndex).trim()
          buffer = buffer.slice(boundaryIndex + 2)

          const lines = chunk.split("\n")
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              if (!firstChunkReceived) {
                setIsWaiting(false)
                firstChunkReceived = true
              }

              const data = line.slice(6)
              if (data === "[DONE]") {
                isDone = true
                break
              }

              try {
                const parsed = JSON.parse(data)
                if (parsed.type === "content") {
                  assistantMsg += parsed.content
                } else if (parsed.type === "tool_start") {
                  activeTools.push({ name: parsed.tool, input: parsed.input, completed: false })
                } else if (parsed.type === "tool_end") {
                  let toolIndex = -1;
                  for (let i = activeTools.length - 1; i >= 0; i--) {
                    if (activeTools[i].name === parsed.tool) {
                      toolIndex = i;
                      break;
                    }
                  }
                  if (toolIndex >= 0) {
                    activeTools[toolIndex].completed = true
                  }
                }

                setMessages(prev => {
                  const newMsgs = [...prev]
                  newMsgs[newMsgs.length - 1] = {
                    ...newMsgs[newMsgs.length - 1],
                    content: assistantMsg,
                    tools: [...activeTools]
                  }
                  return newMsgs
                })
              } catch (e) { }
            }
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        console.error("Chat error:", e)
        setMessages(prev => [...prev, { role: "system", content: `Error: ${e.message}` }])
      }
    } finally {
      setIsGenerating(false)
      setIsWaiting(false)
      abortControllerRef.current = null
      fetchChats()
    }
  }

  return (
    <div className="flex flex-col w-full h-screen bg-background overflow-hidden">
      {/* Header */}
      <div className="w-full h-14 border-b flex items-center justify-between px-4 shrink-0 bg-background/95 backdrop-blur z-10">
        <div className="flex items-center gap-2 flex-1 min-w-0 mr-4">
          {isEditingName ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={editNameValue}
                onChange={e => setEditNameValue(e.target.value)}
                className="text-sm font-medium bg-transparent border-b focus:outline-none focus:border-primary px-1"
                autoFocus
                onKeyDown={e => {
                  if (e.key === 'Enter') handleRenameChat()
                  if (e.key === 'Escape') setIsEditingName(false)
                }}
              />
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleRenameChat}><Check className="h-3 w-3 text-green-500" /></Button>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setIsEditingName(false)}><X className="h-3 w-3" /></Button>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <select
                className="text-sm border-none bg-transparent focus:ring-0 cursor-pointer outline-none font-medium truncate max-w-[200px]"
                value={activeChatId || ""}
                onChange={(e) => setActiveChatId(e.target.value)}
              >
                {chats.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              {activeChatId && (
                <>
                  <Button variant="ghost" size="icon" className="h-6 w-6 ml-1 opacity-50 hover:opacity-100" onClick={() => {
                    const chat = chats.find(c => c.id === activeChatId)
                    if (chat) {
                      setEditNameValue(chat.name)
                      setIsEditingName(true)
                    }
                  }}>
                    <Edit2 className="h-3 w-3" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-6 w-6 opacity-50 hover:opacity-100 hover:text-destructive" onClick={handleDeleteChat}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </>
              )}
            </div>
          )}
          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full shrink-0" onClick={createNewChat} title="New Chat">
            <Plus className="h-3 w-3" />
          </Button>
        </div>
        <div className="text-xs text-muted-foreground flex gap-4 shrink-0">
          <span title="Tokens in Context">Tokens: ~{totalTokens.toLocaleString()}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden relative">
        <ScrollArea className="h-full w-full">
          <div className="max-w-3xl mx-auto p-4 space-y-8 pb-32 pt-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground text-sm mt-10">
                Send a message to start researching.
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.role === "user" ? (
                    <div className="flex gap-3 max-w-[85%]">
                      <div className="bg-primary text-primary-foreground rounded-2xl px-5 py-3 shadow-sm">
                        <div className="whitespace-pre-wrap font-sans text-sm">{msg.content}</div>
                      </div>
                    </div>
                  ) : msg.role === "system" ? (
                    <div className="w-full flex justify-center">
                      <div className="bg-destructive/10 text-destructive border border-destructive/20 rounded-lg px-4 py-2 text-sm max-w-[85%]">
                        {msg.content}
                      </div>
                    </div>
                  ) : (
                    <div className="flex gap-4 w-full">
                      <div className="flex-1 min-w-0 space-y-3">
                        {msg.tools && msg.tools.length > 0 && (
                          <div className="flex flex-col gap-1.5 mb-3">
                            {msg.tools.map((t, idx) => (
                              <div key={idx} className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 px-3 py-1.5 rounded-md w-fit border border-border/50">
                                {t.completed ? <Check className="h-3 w-3 text-green-500" /> : <Loader2 className="h-3 w-3 animate-spin text-blue-500" />}
                                <span className="font-mono">{t.name}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {(() => {
                          const thinkMatch = msg.content.match(/<think>([\s\S]*?)(?:<\/think>|$)/);
                          const thinkingText = thinkMatch ? thinkMatch[1].trim() : null;
                          const contentText = msg.content.replace(/<think>[\s\S]*?(?:<\/think>|$)/g, '').trim();

                          return (
                            <>
                              {thinkingText && (
                                <details className="mb-3 text-xs text-muted-foreground bg-muted/30 p-2.5 rounded-md border border-border/50 max-w-full">
                                  <summary className="cursor-pointer font-mono font-medium select-none flex items-center gap-2">Thinking...</summary>
                                  <div className="mt-2 whitespace-pre-wrap opacity-80 pl-4 border-l-2 border-primary/20">{thinkingText}</div>
                                </details>
                              )}
                              {contentText && (
                                <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:whitespace-pre-wrap prose-pre:break-words prose-pre:bg-muted/50 prose-pre:border overflow-x-hidden w-full break-words">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {contentText}
                                  </ReactMarkdown>
                                </div>
                              )}
                            </>
                          )
                        })()}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}

            {isWaiting && (
              <div className="flex gap-4 w-full">
                <div className="flex items-center gap-1 bg-muted/30 px-4 py-3 rounded-2xl w-fit">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={scrollRef} className="h-1" />
          </div>
        </ScrollArea>
      </div>

      {/* Input */}
      <div className="absolute bottom-0 inset-x-0 shrink-0 z-10 bg-gradient-to-t from-background via-background/95 to-transparent pt-24 pb-4 px-4 pointer-events-none">
        <div className="max-w-3xl mx-auto pointer-events-auto">
          <div className="relative rounded-2xl border bg-background shadow-lg focus-within:ring-1 focus-within:ring-ring focus-within:border-primary/50 transition-all overflow-hidden">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit()
                }
              }}
              placeholder="Ask rubberduck anything..."
              className="min-h-[60px] max-h-[200px] resize-y border-0 focus-visible:ring-0 shadow-none py-4 px-4 pr-14 text-sm bg-transparent"
              rows={1}
            />
            <div className="absolute bottom-2.5 right-2.5 flex items-center">
              <Button
                size="icon"
                className={`h-8 w-8 rounded-xl shrink-0 transition-all ${isGenerating ? 'bg-destructive hover:bg-destructive/90 text-destructive-foreground' : 'bg-primary hover:bg-primary/90 text-primary-foreground'}`}
                onClick={handleSubmit}
                disabled={!input.trim() && !isGenerating}
              >
                {isGenerating ? <div className="h-3 w-3 bg-current rounded-sm" /> : <Send className="h-4 w-4 ml-0.5" />}
              </Button>
            </div>
          </div>
          <div className="text-center mt-2.5 text-[11px] text-muted-foreground">
            rubberduck can make mistakes. Verify important information.
          </div>
        </div>
      </div>
    </div>
  )
}
