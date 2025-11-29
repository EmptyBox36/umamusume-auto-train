import { useEffect, useRef, useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Filter } from "lucide-react";

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

const LEVELS = ["INFO", "DEBUG", "WARNING", "ERROR"] as const;
type Level = (typeof LEVELS)[number];

export default function LiveLogDialog() {
  const [open, setOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [query, setQuery] = useState("");
  const [activeLevels, setActiveLevels] = useState<Level[]>([...LEVELS]);

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

  // reset logs when dialog opens
  useEffect(() => {
    if (!open) return;
    setLogs([]);
    cursorRef.current = -1;
  }, [open]);

  // polling loop
  useEffect(() => {
    if (!open) return;

    let active = true;
    const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

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
            // ignore network errors
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

  // auto-scroll when not searching
  useEffect(() => {
    if (!open || query.trim() !== "") return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [logs, open, query]);

  const clearLogs = () => setLogs([]);

  // severity multi-select
  const toggleLevel = (level: Level) => {
    setActiveLevels((prev) =>
      prev.includes(level) ? prev.filter((l) => l !== level) : [...prev, level]
    );
  };

  const allSelected = activeLevels.length === LEVELS.length;
  const setAllLevels = () => setActiveLevels([...LEVELS]);

  const visibleLogs = useMemo(() => {
    let filtered = logs;

    if (activeLevels.length > 0 && activeLevels.length < LEVELS.length) {
      const set = new Set(activeLevels.map((l) => l.toUpperCase()));
      filtered = filtered.filter((l) => set.has(l.level.toUpperCase() as Level));
    } else if (activeLevels.length === 0) {
      filtered = [];
    }

    const q = query.trim().toLowerCase();
    if (q) {
      filtered = filtered.filter(
        (l) =>
          l.message.toLowerCase().includes(q) ||
          l.level.toLowerCase().includes(q)
      );
    }

    return filtered;
  }, [logs, query, activeLevels]);

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

      <DialogContent
        className="
          flex flex-col rounded-2xl
          w-[90vw] max-w-[1100px]
          h-[70vh] max-h-[90vh]
          min-h-0
          overflow-hidden
          p-0
        "
      >
        {/* Header */}
        <div className="border-b border-border/60 bg-muted/30 px-4 md:px-8 pt-4 md:pt-5 pb-3 md:pb-4 pr-14 md:pr-16">
          <DialogHeader className="flex flex-row items-center justify-between space-y-0">
            <DialogTitle className="text-base md:text-lg font-semibold">
              Live Log
            </DialogTitle>

            <div className="flex items-center gap-3 text-[11px] md:text-xs text-muted-foreground">
              <span
                className={`inline-flex h-2 w-2 rounded-full ${
                  paused ? "bg-amber-400" : "bg-emerald-400 animate-pulse"
                }`}
              />
              <span>{paused ? "Paused" : "Streaming"}</span>
            </div>
          </DialogHeader>
        </div>

        {/* Controls */}
        <div className="px-4 md:px-8 pt-3 pb-2 md:pb-3 flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-border/60 bg-muted/20">
          <div className="flex flex-wrap items-center gap-2 md:gap-3">
            <Button
              variant={paused ? "outline" : "secondary"}
              size="sm"
              className="px-4 md:px-5 py-2 text-xs md:text-sm font-medium rounded-md"
              onClick={() => setPaused((p) => !p)}
            >
              {paused ? "Resume" : "Pause Log"}
            </Button>

            <Button
              variant="outline"
              size="sm"
              className="px-4 md:px-5 py-2 text-xs md:text-sm font-medium rounded-md"
              onClick={clearLogs}
            >
              Clear
            </Button>

            <div className="flex flex-wrap items-center gap-1.5 md:gap-2">
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground mr-1">
                <Filter className="h-3 w-3" />
                Levels:
              </span>

              <Button
                type="button"
                variant={allSelected ? "secondary" : "outline"}
                size="sm"
                className="h-8 px-3 text-[11px]"
                onClick={setAllLevels}
              >
                ALL
              </Button>

              {LEVELS.map((lvl) => {
                const active = activeLevels.includes(lvl);
                return (
                  <Button
                    key={lvl}
                    type="button"
                    variant={active ? "secondary" : "outline"}
                    size="sm"
                    className="h-8 px-3 text-[11px]"
                    onClick={() => toggleLevel(lvl)}
                  >
                    {lvl}
                  </Button>
                );
              })}
            </div>
          </div>

          <div className="relative w-full md:w-80">
            <Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search in log..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-8 h-9 text-xs"
            />
          </div>
        </div>

        {/* Log section */}
        <div className="px-4 md:px-8 pb-4 md:pb-6 pt-3 md:pt-4 flex-1 min-h-0">
          <div
            ref={scrollRef}
            className="
              w-full h-full min-h-0
              overflow-y-auto
              rounded-lg bg-black/95 px-3 py-2
              font-mono text-xs text-slate-100
              border border-border/70
            "
          >
            {visibleLogs.length === 0 && (
              <div className="text-[11px] text-slate-400">
                {logs.length === 0
                  ? "No logs yet. Start the bot."
                  : activeLevels.length === 0
                  ? "No levels selected. Enable at least one severity."
                  : "No log lines match your filter/search."}
              </div>
            )}

            {visibleLogs.map((entry) => (
              <div
                key={entry.id}
                className="flex gap-2 whitespace-pre-wrap border-b border-white/5 last:border-0 py-[2px]"
              >
                <span className="shrink-0 text-[10px] md:text-[11px] text-slate-500">
                  [{formatTime(entry.ts)}]
                </span>

                <span
                  className={`shrink-0 text-[9px] md:text-[10px] uppercase tracking-wide px-2 py-[1px] rounded-full border ${levelBadgeClass(
                    entry.level
                  )}`}
                >
                  {entry.level}
                </span>

                <span
                  className={`flex-1 text-[10px] md:text-[11px] ${levelClass(
                    entry.level
                  )}`}
                >
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