import { memo, useEffect, useMemo, useState, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type SkillEventChoice = { event_name: string; chosen: number };

type Props = {
    trainee: string;
    scenario: string;
    eventChoices: SkillEventChoice[] | undefined;
    setEventChoices: (next: SkillEventChoice[]) => void;
};

type ChoiceRow = { id: number; label: string; stats?: Record<string, unknown> };
type EventRow = {
    key: string;
    name: string;
    source: "Character" | "Scenario" | "Support";
    choices: ChoiceRow[];
};

const normalize = (s: string) =>
    s
        .toLowerCase()
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9\s]/gi, " ")
        .replace(/\s+/g, " ")
        .trim();

const filterBySearch = (rows: EventRow[], q: string) => {
    const nq = normalize(q);
    if (!nq) return rows;
    const tokens = nq.split(" ");
    return rows.filter((r) => {
        const h = normalize(r.name);
        return tokens.every((t) => h.includes(t));
    });
};

function ChoicePill({
    label,
    selected,
    onClick,
}: {
    label: number | string;
    selected: boolean;
    onClick: () => void;
}) {
    return (
        <Button
            type="button"
            onClick={onClick}
            variant={selected ? "default" : "secondary"}
            className={["h-8 w-8 p-0", "rounded-md", "text-sm font-semibold", "shadow-sm", selected ? "" : "opacity-90"].join(" ")}
        >
            {label}
        </Button>
    );
}

// Memoized section to prevent remounts on unrelated updates
const Section = memo(function Section({
    label,
    rows,
    search,
    setSearch,
    getSelectedInfo,
    addChoice,
    isOpen,
    toggleOpen,
}: {
    label: "Character" | "Scenario" | "Support";
    rows: EventRow[];
    search: string;
    setSearch: (v: string) => void;
    getSelectedInfo: (row: EventRow) => { key: string; selected: number | undefined };
    addChoice: (row: EventRow, choiceId: number) => void;
    isOpen: boolean;
    toggleOpen: () => void;
}) {
    return (
        <div className="rounded-xl border bg-muted/30 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3">
                <div className="font-semibold">{label} Events</div>
                <Button type="button" size="sm" variant="secondary" onClick={toggleOpen} className="h-8 px-3">
                    {isOpen ? "Hide" : "Show"}
                </Button>
            </div>

            {isOpen && (
                <div className="px-4 pb-4 space-y-3">
                    <Input
                        type="search"
                        autoComplete="off"
                        value={search}
                        placeholder="Search by event name"
                        onChange={(e) => setSearch(e.target.value)}
                        // keep typing inside input; do not bubble to dialog/accordion
                        onClick={(e) => e.stopPropagation()}
                        onMouseDown={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                            if (e.key !== "Enter") e.stopPropagation();
                        }}
                        onKeyUp={(e) => e.stopPropagation()}
                        onCompositionStart={(e) => e.stopPropagation()}
                        className="h-10"
                    />

                    <div className="max-h-[56svh] overflow-auto">
                        <ul className="divide-y">
                            {filterBySearch(rows, search).map((r) => {
                                const { selected } = getSelectedInfo(r);
                                return (
                                    <li
                                        key={r.key}
                                        className="flex items-center justify-between gap-3 py-2.5 px-3 rounded-lg hover:bg-muted/60"
                                    >
                                        <div className="truncate text-sm font-medium">{r.name}</div>
                                        <div className="flex items-center gap-2">
                                            {r.choices.map((c) => (
                                                <ChoicePill
                                                    key={c.id}
                                                    label={c.id}
                                                    selected={selected === c.id}
                                                    onClick={() => addChoice(r, c.id)}
                                                />
                                            ))}
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>

                        {filterBySearch(rows, search).length === 0 && (
                            <div className="text-muted-foreground text-sm px-1 py-6 text-center">No events.</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
});

export default function CustomEventPicker({
    trainee,
    scenario,
    eventChoices,
    setEventChoices,
}: Props) {
    const [open, setOpen] = useState(false);

    // per-section searches
    const [searchChar, setSearchChar] = useState("");
    const [searchScen, setSearchScen] = useState("");
    const [searchSupp, setSearchSupp] = useState("");

    const [openSection, setOpenSection] = useState<Record<string, boolean>>({
        Character: false,
        Scenario: false,
        Support: false,
    });

    // runtime data
    const [characters, setCharacters] = useState<Record<string, any>>({});
    const [scenarios, setScenarios] = useState<Record<string, any>>({});
    const [supports, setSupports] = useState<Record<string, any>>({});

    useEffect(() => {
        async function fetchData() {
            try {
                const [charRes, scenRes, suppRes] = await Promise.all([
                    fetch("/scraper/data/characters.json").then((r) => r.json()),
                    fetch("/data/scenarios.json").then((r) => r.json()),
                    fetch("/scraper/data/supports.json").then((r) => r.json()),
                ]);
                setCharacters(charRes);
                setScenarios(scenRes);
                setSupports(suppRes);
            } catch (err) {
                console.error("Failed to load JSON data", err);
            }
        }
        fetchData();
    }, []);

    const characterRows: EventRow[] = useMemo(() => {
        if (!trainee || !characters[trainee]) return [];
        const bucket = characters[trainee] as Record<string, any>;
        return Object.entries(bucket).map(([evName, ev]) => ({
            key: `Character:${trainee}:${evName}`,
            name: evName,
            source: "Character" as const,
            choices: Object.entries(ev.choices ?? {}).map(([k, label]) => ({
                id: Number(k),
                label: String(label),
                stats: (ev.stats ?? {})[k],
            })),
        }));
    }, [trainee, characters]);

    const scenarioRows: EventRow[] = useMemo(() => {
        if (!scenario || !scenarios[scenario]) return [];
        const bucket = scenarios[scenario] as Record<string, any>;
        return Object.entries(bucket).map(([evName, ev]) => ({
            key: `Scenario:${scenario}:${evName}`,
            name: evName,
            source: "Scenario" as const,
            choices: Object.entries(ev.choices ?? {}).map(([k, label]) => ({
                id: Number(k),
                label: String(label),
                stats: (ev.stats ?? {})[k],
            })),
        }));
    }, [scenario, scenarios]);

    // supports can be flat or nested
    const supportRows: EventRow[] = useMemo(() => {
        const rows: EventRow[] = [];
        Object.entries(supports).forEach(([k, v]) => {
            if (v && typeof v === "object" && ("choices" in v || "stats" in v)) {
                const ev = v as any;
                rows.push({
                    key: `Support:${k}`,
                    name: k,
                    source: "Support",
                    choices: Object.entries(ev.choices ?? {}).map(([id, label]) => ({
                        id: Number(id),
                        label: String(label),
                        stats: (ev.stats ?? {})[id],
                    })),
                });
                return;
            }
            Object.entries(v ?? {}).forEach(([eventName, ev]: any) => {
                rows.push({
                    key: `Support:${k}:${eventName}`,
                    name: `${k} — ${eventName}`,
                    source: "Support",
                    choices: Object.entries(ev?.choices ?? {}).map(([id, label]) => ({
                        id: Number(id),
                        label: String(label),
                        stats: (ev?.stats ?? {})[id],
                    })),
                });
            });
        });
        return rows;
    }, [supports]);

    const keyForRow = useCallback((row: EventRow) => `${row.source}:${row.name}`, []);

    const getSelectedInfo = useCallback(
        (row: EventRow) => {
            const pref = keyForRow(row);
            const plain = row.name;
            const map = new Map((eventChoices ?? []).map((v) => [v.event_name, v.chosen]));
            if (map.has(pref)) return { key: pref, selected: map.get(pref) as number };
            if (map.has(plain)) return { key: plain, selected: map.get(plain) as number };
            return { key: plain, selected: undefined as number | undefined };
        },
        [eventChoices, keyForRow]
    );

    const addChoice = useCallback(
        (row: EventRow, choiceId: number) => {
            const { key, selected } = getSelectedInfo(row);
            const current = eventChoices ?? [];
            const idx = current.findIndex((e) => e.event_name === key);

            if (selected === choiceId) {
                setEventChoices(current.filter((e) => e.event_name !== key));
                return;
            }
            const next = [...current];
            if (idx >= 0) next[idx] = { event_name: key, chosen: choiceId };
            else next.push({ event_name: key, chosen: choiceId });
            setEventChoices(next);
        },
        [eventChoices, getSelectedInfo, setEventChoices]
    );

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button className="font-semibold">Custom Event Choices</Button>
            </DialogTrigger>

            <DialogContent className="w-[min(96vw,1000px)] h-[85svh] p-0">
                <div className="flex h-full flex-col min-h-0">
                    <DialogHeader className="p-6 pb-3 sticky top-0 z-10 bg-background">
                        <DialogTitle>Event Choice Picker</DialogTitle>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-4">
                        <Section
                            label="Character"
                            rows={characterRows}
                            search={searchChar}
                            setSearch={setSearchChar}
                            getSelectedInfo={getSelectedInfo}
                            addChoice={addChoice}
                            isOpen={openSection.Character}
                            toggleOpen={() => setOpenSection((s) => ({ ...s, Character: !s.Character }))}
                        />
                        <Section
                            label="Scenario"
                            rows={scenarioRows}
                            search={searchScen}
                            setSearch={setSearchScen}
                            getSelectedInfo={getSelectedInfo}
                            addChoice={addChoice}
                            isOpen={openSection.Scenario}
                            toggleOpen={() => setOpenSection((s) => ({ ...s, Scenario: !s.Scenario }))}
                        />
                        <Section
                            label="Support"
                            rows={supportRows}
                            search={searchSupp}
                            setSearch={setSearchSupp}
                            getSelectedInfo={getSelectedInfo}
                            addChoice={addChoice}
                            isOpen={openSection.Support}
                            toggleOpen={() => setOpenSection((s) => ({ ...s, Support: !s.Support }))}
                        />
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}