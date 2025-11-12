import { useState, useEffect } from "react";
import type { Config, UnityCfg, SpiritStat } from "../types";
import rawDefault from "../../../config.json";

const STORAGE_KEY = "uma-config";
const MAX_PRESET = 10;

/* ---------- SpiritStat guards ---------- */
const SPIRIT_LIST: readonly SpiritStat[] = ["spd", "sta", "pwr", "guts", "wit"];
const SPIRIT_SET = new Set<SpiritStat>(SPIRIT_LIST);

/* ---------- Normalizers ---------- */
function normalizeUnity(unity: any | undefined): UnityCfg | undefined {
    if (!unity) return undefined;

    const rounds = Array.isArray(unity.prefer_team_race) ? unity.prefer_team_race : [];
    const prefer_team_race = [0, 1, 2, 3].map((i) => {
        const v = Number(rounds[i] ?? 1);
        return Math.min(5, Math.max(1, Number.isFinite(v) ? v : 1));
    });

    const spirit_burst_position: SpiritStat[] = Array.isArray(unity.spirit_burst_position)
        ? unity.spirit_burst_position.filter((x: any): x is SpiritStat => SPIRIT_SET.has(x))
        : [];

    return { prefer_team_race, spirit_burst_position };
}

function normalizeConfig(cfg: any): Config {
    const out = { ...(cfg ?? {}) } as Config;
    out.unity = normalizeUnity(out.unity);
    return out;
}

/* ---------- Deep merge for partials ---------- */
function deepMerge<T extends object>(target: Partial<T>, source: Partial<T>): T {
    const out: any = Array.isArray(target) ? [] : {};
    const keys = new Set([...Object.keys(source || {}), ...Object.keys(target || {})]);
    for (const k of keys) {
        const a: any = (target as any)?.[k];
        const b: any = (source as any)?.[k];
        if (
            a &&
            b &&
            typeof a === "object" &&
            typeof b === "object" &&
            !Array.isArray(a) &&
            !Array.isArray(b)
        ) {
            out[k] = deepMerge(a, b);
        } else {
            out[k] = a !== undefined ? a : b;
        }
    }
    return out as T;
}

/* ---------- Types kept local (unchanged API) ---------- */
type Preset = {
    name: string;
    config: Config;
};

type PresetStorage = {
    index: number;
    presets: Preset[];
};

/* ---------- Build a typed default config ---------- */
const DEFAULT_CONFIG: Config = normalizeConfig(rawDefault as any);

/* ---------- Hook ---------- */
export function useConfigPreset() {
    const [presetStorage, setPresetStorage] = useState<PresetStorage>({ index: 0, presets: [] });
    const [activeIndex, setActiveIndex] = useState(0);

    useEffect(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            const parsed = JSON.parse(saved) as Partial<PresetStorage>;

            const upgradedPresets: Preset[] = (parsed.presets ?? []).map((p: any, i: number) => ({
                name: String(p?.name ?? `Preset ${i + 1}`),
                // Merge with typed default then normalize to satisfy SpiritStat[]
                config: normalizeConfig(deepMerge<Config>(p?.config ?? {}, DEFAULT_CONFIG)),
            }));

            const upgraded: PresetStorage = {
                index: Number.isInteger(parsed.index) ? (parsed.index as number) : 0,
                presets: upgradedPresets,
            };

            setPresetStorage(upgraded);
            setActiveIndex(upgraded.index);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(upgraded));
        } else {
            const defaultPresets: Preset[] = Array.from({ length: MAX_PRESET }, (_, i) => ({
                name: `Preset ${i + 1}`,
                config: DEFAULT_CONFIG,
            }));
            const init: PresetStorage = { index: 0, presets: defaultPresets };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(init));
            setPresetStorage(init);
            setActiveIndex(0);
        }
    }, []);

    const setNamePreset = (i: number, newName: string) => {
        setPresetStorage((prev) => {
            const presets = [...prev.presets];
            if (presets[i]) presets[i] = { ...presets[i], name: newName };
            const next = { ...prev, presets };
            return next;
        });
    };

    const updatePreset = (i: number, newConfig: Config) => {
        setPresetStorage((prev) => {
            const presets = [...prev.presets];
            if (presets[i]) presets[i] = { ...presets[i], config: normalizeConfig(newConfig) };
            const next = { ...prev, presets };
            return next;
        });
    };

    const savePreset = (config: Config) => {
        setPresetStorage((prev) => {
            const presets = [...prev.presets];
            if (presets[activeIndex]) {
                presets[activeIndex] = { ...presets[activeIndex], config: normalizeConfig(config) };
            }
            const next = { ...prev, index: activeIndex, presets };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
            return next;
        });
    };

    return {
        activeIndex,
        activeConfig: presetStorage.presets[activeIndex]?.config,
        presets: presetStorage.presets,
        setActiveIndex,
        setNamePreset,
        updatePreset,
        savePreset,
    };
}