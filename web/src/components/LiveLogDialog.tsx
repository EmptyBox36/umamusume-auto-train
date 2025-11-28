import { useEffect, useRef, useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

type LogEntry = {
  id: number;
  ts: number;
  level: string;
  message: string;
};

type LogResponse = {
  next: number;
  entries: LogEntry[];
};

export default function LiveLogDialog() {
  const [open, setOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [query, setQuery] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const cursorRef = useRef<number>(-1);

  const formatTime = (ts: number) =>
    new Date(ts * 1000).toLocaleTimeString([], {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

  const levelClass = (level: string) => {
    switch (level.toUpperCase()) {
      case "ERROR":
        return "text-red-300";
      case "WARNING":
      case "WARN":
        return "text-amber-300";
      case "DEBUG":
        return "text-sky-300";
      default:
        return "text-emerald-300";
    }
  };

  const levelBadgeClass = (level: string) => {
    switch (level.toUpperCase()) {
      case "ERROR":
        return "bg-red-500/15 text-red-300 border-red-500/40";
      case "WARNING":
      case "WARN":
        return "bg-amber-500/15 text-amber-300 border-amber-500/40";
      case "DEBUG":
        return "bg-sky-500/15 text-sky-300 border-sky-500/40";
      default:
        return "bg-emerald-500/15 text-emerald-300 border-emerald-500/40";
    }
  };

  // Reset logs + cursor whenever dialog opens
  useEffect(() => {
    if (!open) return;
    setLogs([]);
    cursorRef.current = -1;
  }, [open]);

  // Poll /api/logs while dialog is open
  useEffect(() => {
    if (!open) return;

    let active = true;

    const wait = (ms: number) =>
      new Promise<void>((resolve) => setTimeout(resolve, ms));

    const loop = async () => {
      while (active) {
        if (!paused) {
          try {
            const res = await fetch(`/api/logs?since=${cursorRef.current}`, {
              cache: "no-cache",
            });
            if (res.ok) {
              const data: LogResponse = await res.json();
              const entries = data.entries || [];

              if (entries.length > 0) {
                cursorRef.current = data.next;
                setLogs((prev) =>
                  [...prev, ...entries].slice(-800) // keep last 800 lines
                );
              } else {
                cursorRef.current = data.next;
              }
            }
          } catch {
            // ignore; retry later
          }
        }

        await wait(1000);
      }
    };

    loop();
    return () => {
      active = false;
    };
  }, [open, paused]);

  // Auto-scroll to bottom when new logs arrive (only when not searching)
  useEffect(() => {
    if (!open || query.trim() !== "") return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [logs, open, query]);

  const clearLogs = () => setLogs([]);

  // Filter logs by search query
  const visibleLogs = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return logs;
    return logs.filter(
      (entry) =>
        entry.message.toLowerCase().includes(q) ||
        entry.level.toLowerCase().includes(q)
    );
  }, [logs, query]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="ml-2"
      >
        View Log
      </Button>

      {/* Bigger dialog */}
      <DialogContent className="max-w-7xl p-0 overflow-hidden">
        {/* Header with extra right padding so it doesn't collide with the X button */}
        <div className="border-b border-border/60 bg-muted/30 px-8 pt-5 pb-4 pr-16">
          <DialogHeader className="flex flex-row items-center justify-between space-y-0">
            <DialogTitle className="text-lg font-semibold">
              Live Log
            </DialogTitle>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span
                className={`inline-flex h-2 w-2 rounded-full ${
                  paused ? "bg-amber-400" : "bg-emerald-400 animate-pulse"
                }`}
              />
              <span>{paused ? "Paused" : "Streaming"}</span>
            </div>
          </DialogHeader>
        </div>

        {/* Controls row */}
        <div className="px-8 pt-3 pb-3 flex items-center justify-between gap-4 border-b border-border/60 bg-muted/20">
          <div className="flex items-center gap-3">
            <Button
              variant={paused ? "outline" : "secondary"}
              size="sm"
              className="px-5 py-2 text-sm font-medium rounded-md"
              onClick={() => setPaused((p) => !p)}
            >
              {paused ? "Resume" : "Pause"}
            </Button>

            <Button
              variant="outline"
              size="sm"
              className="px-5 py-2 text-sm font-medium rounded-md"
              onClick={clearLogs}
            >
              Clear
            </Button>
          </div>

          <div className="relative w-80">
            <Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search in log..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-8 h-9 text-xs"
            />
          </div>
        </div>

        {/* Bigger log area */}
        <div className="px-8 pb-8 pt-4">
          <div
            ref={scrollRef}
            className="h-[560px] w-full overflow-auto rounded-lg bg-black/95 px-3 py-2 font-mono text-xs text-slate-100 border border-border/70"
          >
            {visibleLogs.length === 0 && (
              <div className="text-[11px] text-slate-400">
                {logs.length === 0
                  ? "No logs yet. Start the bot to see live output."
                  : "No log lines match your search."}
              </div>
            )}

            {visibleLogs.map((entry) => (
              <div
                key={entry.id}
                className="flex gap-2 whitespace-pre-wrap border-b border-white/5 last:border-0 py-[2px]"
              >
                <span className="shrink-0 text-[11px] text-slate-500">
                  [{formatTime(entry.ts)}]
                </span>
                <span
                  className={`shrink-0 text-[10px] uppercase tracking-wide px-2 py-[1px] rounded-full border ${levelBadgeClass(
                    entry.level
                  )}`}
                >
                  {entry.level}
                </span>
                <span className={`flex-1 text-[11px] ${levelClass(entry.level)}`}>
                  {entry.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}