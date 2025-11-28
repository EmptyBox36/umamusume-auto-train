import { useEffect, useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

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
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // auto-scroll when new logs arrive
  useEffect(() => {
    if (!open || !autoScroll) return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [logs, open, autoScroll]);

  // polling loop
  useEffect(() => {
    if (!open) return;

    let active = true;
    let cursor = -1;

    const wait = (ms: number) =>
      new Promise<void>((resolve) => setTimeout(resolve, ms));

    const loop = async () => {
      while (active) {
        try {
          if (paused) {
            await wait(500);
            continue;
          }

          const res = await fetch(`/api/logs?since=${cursor}`);
          if (!res.ok) {
            await wait(1000);
            continue;
          }

          const data: LogResponse = await res.json();
          const entries = data.entries || [];

          if (entries.length > 0) {
            cursor = data.next;
            setLogs((prev) => {
              const merged = [...prev, ...entries];
              return merged.slice(-500); // keep last 500 lines
            });
          } else {
            cursor = data.next;
          }

          await wait(1000);
        } catch {
          // on error wait slightly longer
          await wait(2000);
        }
      }
    };

    loop();
    return () => {
      active = false;
    };
  }, [open, paused]);

  const formatTime = (ts: number) =>
    new Date(ts * 1000).toLocaleTimeString([], {
      hour12: false,
    });

  const clearLogs = () => setLogs([]);

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

      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Live Log</DialogTitle>
        </DialogHeader>

        <div className="mb-4 flex items-center gap-3">
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

        <div
          ref={scrollRef}
          className="h-80 w-full overflow-auto rounded-md bg-black/90 p-2 font-mono text-xs text-green-200"
          onMouseEnter={() => setAutoScroll(false)}
          onMouseLeave={() => setAutoScroll(true)}
        >
          {logs.length === 0 && (
            <div className="text-neutral-400">No logs yet.</div>
          )}

          {logs.map((entry) => (
            <div key={entry.id} className="whitespace-pre-wrap">
              [{formatTime(entry.ts)}]{" "}
              <span className="font-semibold">{entry.level}</span>{" "}
              {entry.message}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
