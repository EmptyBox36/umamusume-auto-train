import { useMemo, useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Config, UnityCfg } from "@/types/index";

/* Scenario name → config key */
function scenarioKey(name?: string): "unity" | null {
    const n = (name ?? "").toLowerCase().trim();
    if (!n) return null;
    if (n.includes("unity")) return "unity"; // “Unity Cup”, etc.
    return null;
}

/* Spirit-burst stats (unordered) */
const STATS = ["spd", "sta", "pwr", "guts", "wit"] as const;
type Stat = typeof STATS[number];

/* Defaults */
const UNITY_DEFAULT: UnityCfg = {
    prefer_team_race: [1, 1, 1, 1],
    spirit_burst_position: ["spd", "sta", "pwr", "guts", "wit"],
};

/* Unity settings panel */
function UnityPanel({
    value,
    onChange,
}: {
    value?: Partial<UnityCfg>;
    onChange: (next: UnityCfg) => void;
}) {
    const [local, setLocal] = useState<UnityCfg>({
        prefer_team_race:
            value?.prefer_team_race?.slice(0, 4) ?? UNITY_DEFAULT.prefer_team_race,
        spirit_burst_position:
            (value?.spirit_burst_position?.length
                ? (value!.spirit_burst_position as Stat[])
                : UNITY_DEFAULT.spirit_burst_position) as Stat[],
    });

    const setRound = (i: number, v: number) =>
        setLocal((s) => ({
            ...s,
            prefer_team_race: s.prefer_team_race.map((x, idx) =>
                idx === i ? Math.min(5, Math.max(1, v)) : x
            ),
        }));

    const toggle = (p: Stat) =>
        setLocal((s) => {
            const has = s.spirit_burst_position.includes(p);
            const next: Stat[] = has
                ? (s.spirit_burst_position.filter((x) => x !== p) as Stat[])
                : ([...s.spirit_burst_position, p] as Stat[]);
            return { ...s, spirit_burst_position: next };
        });

    const handleSave = () => {
        onChange(local);
        window.alert("Settings saved");
    };

    return (
        <div className="space-y-5">
            <div>
                <div className="font-semibold mb-2">Prefer Team Race</div>
                <div className="grid grid-cols-4 gap-3">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="flex items-center gap-2">
                            <span className="w-16 text-sm text-muted-foreground">
                                Round {i + 1}
                            </span>
                            <Input
                                type="number"
                                min={1}
                                max={5}
                                value={local.prefer_team_race[i]}
                                onChange={(e) => setRound(i, Number(e.target.value) || 1)}
                                className="h-9 w-20"
                            />
                        </div>
                    ))}
                </div>
            </div>

            <div className="space-y-2">
                <label className="font-semibold">Spirit Burst Position</label>
                <div className="flex gap-2 flex-wrap">
                    {STATS.map((stat: Stat) => (
                        <Button
                            key={stat}
                            type="button"
                            variant={
                                local.spirit_burst_position.includes(stat)
                                    ? "default"
                                    : "secondary"
                            }
                            onClick={() => toggle(stat)}
                            className="w-16 capitalize"
                        >
                            {stat}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={() => setLocal(UNITY_DEFAULT)}>
                    Reset
                </Button>
                <Button type="button" onClick={handleSave}>
                    Save
                </Button>
            </div>
        </div>
    );
}

/* Router dialog */
export default function ScenarioConfig({
    scenarioName,
    cfg,
    onChange,
}: {
    scenarioName?: string;
    cfg: Config;
    onChange: (key: "unity", next: UnityCfg) => void; // only valid key today
}) {
    const key = useMemo(() => scenarioKey(scenarioName), [scenarioName]);

    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button type="button" variant="secondary" className="ml-2 h-9">
                    Config
                </Button>
            </DialogTrigger>

            <DialogContent className="w-[min(96vw,720px)]">
                <DialogHeader>
                    <DialogTitle>
                        Scenario Settings — {scenarioName || "Unknown"}
                    </DialogTitle>
                </DialogHeader>

                {key === "unity" ? (
                    <UnityPanel value={cfg.unity} onChange={(next) => onChange("unity", next)} />
                ) : (
                    <div className="text-sm text-muted-foreground">
                        No scenario-specific settings for “{scenarioName}”.
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}