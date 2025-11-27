import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { useEffect, useState, useRef } from "react";
import type {
  RaceScheduleType,
  PositionForSpecificRace,
} from "@/types";
import { Settings } from "lucide-react";
import PreferredPositionDialog from "./PreferredPositionDialog";

type RaceType = {
  id: number;
  date: string;
  racetrack: string;
  terrain: "Turf" | "Dirt";
  distance: { type: "Short" | "Mile" | "Medium" | "Long"; meters: number };
  grade?: string;
  sparks?: string[];
  fans?: { required?: number; gained?: number };
};

type RaceScheduleDataType = {
  "Junior Year": Record<string, RaceType>;
  "Classic Year": Record<string, RaceType>;
  "Senior Year": Record<string, RaceType>;
};

type Props = {
  raceSchedule: RaceScheduleType[];
  addRaceSchedule: (newList: RaceScheduleType) => void;
  deleteRaceSchedule: (name: string, year: string) => void;
  clearRaceSchedule: () => void;

  positionForSpecificRace: PositionForSpecificRace[];
  setPositionForSpecificRace: (next: PositionForSpecificRace[]) => void;
  clearPositionForSpecificRace: () => void;
};

export default function RaceSchedule({
  raceSchedule,
  addRaceSchedule,
  deleteRaceSchedule,
  clearRaceSchedule,
  positionForSpecificRace,
  setPositionForSpecificRace,
  clearPositionForSpecificRace,
}: Props) {
  const [data, setData] = useState<RaceScheduleDataType | null>(null);

  type TerrainT = "Turf" | "Dirt";
  type DistT = "Short" | "Mile" | "Medium" | "Long";
  type GradeT = "G1" | "G2" | "G3" | "OP" | "Pre-OP";

  const [fltTerrain, setFltTerrain] = useState<Set<TerrainT>>(new Set());
  const [fltDist, setFltDist] = useState<Set<DistT>>(new Set());
  const [fltGrade, setFltGrade] = useState<Set<GradeT>>(new Set());

  const toggleSet = <T,>(
    setter: React.Dispatch<React.SetStateAction<Set<T>>>,
    v: T,
  ) => {
    setter((prev) => {
      const s = new Set(prev);
      if (s.has(v)) {
        s.delete(v);
      } else {
        s.add(v);
      }
      return s;
    });
  };

  const clearFilters = () => {
    setFltTerrain(new Set());
    setFltDist(new Set());
    setFltGrade(new Set());
  };

  useEffect(() => {
    const getRaceData = async () => {
      try {
        const res = await fetch("/scraper/data/races.json");
        const races: RaceScheduleDataType = await res.json();
        setData(races);
      } catch (error) {
        console.error("Failed to fetch races:", error);
      }
    };

    getRaceData();
  }, []);

  const scheduledSorted = data
    ? raceSchedule
        .map((r) => {
          const yearData = (data as Record<string, Record<string, RaceType>>)[
            r.year
          ];
          const raceData = yearData?.[r.name];
          return {
            ...r,
            _id: raceData?.id ?? Number.MAX_SAFE_INTEGER,
          };
        })
        .sort((a, b) => a._id - b._id)
    : raceSchedule;

  const passes = (r: RaceType) =>
    (fltTerrain.size === 0 || fltTerrain.has(r.terrain as TerrainT)) &&
    (fltDist.size === 0 || fltDist.has(r.distance.type as DistT)) &&
    (fltGrade.size === 0 ||
      (r.grade ? fltGrade.has(r.grade as GradeT) : false));

  const filteredData: RaceScheduleDataType | null = data
    ? (Object.fromEntries(
        Object.entries(data).map(([year, list]) => [
          year,
          Object.fromEntries(
            Object.entries(list).filter(([, v]) => passes(v)),
          ),
        ]),
      ) as RaceScheduleDataType)
    : null;

  const bookedDates = new Set(
    raceSchedule.map((r) => `${r.year}::${r.date}`),
  );

  const [search, setSearch] = useState("");
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value.toLowerCase());
  };

  const stickyRef = useRef<HTMLDivElement>(null);
  const [filtersH, setFiltersH] = useState(0);

  const [positionEditorRace, setPositionEditorRace] =
    useState<RaceScheduleType | null>(null);

  const keyYear = (year: string, date: string) => `${year} ${date}`;

  const getSpecific = (race: RaceScheduleType) =>
    positionForSpecificRace.find(
      (p) =>
        p.race_name === race.name && p.year === keyYear(race.year, race.date),
    );

  const handleSelectPosition = (race: RaceScheduleType, position: string) => {
    const kYear = keyYear(race.year, race.date);
    const idx = positionForSpecificRace.findIndex(
      (p) => p.race_name === race.name && p.year === kYear,
    );

    // toggle off if same position clicked
    if (
      idx !== -1 &&
      positionForSpecificRace[idx].position === position
    ) {
      const next = positionForSpecificRace.filter((_, i) => i !== idx);
      setPositionForSpecificRace(next);
      return;
    }

    const others = positionForSpecificRace.filter(
      (p) => !(p.race_name === race.name && p.year === kYear),
    );
    setPositionForSpecificRace([
      ...others,
      { race_name: race.name, year: kYear, position },
    ]);
  };

  useEffect(() => {
    if (!stickyRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const h = entries[0].contentRect.height;
      setFiltersH(h);
    });
    ro.observe(stickyRef.current);
    return () => ro.disconnect();
  }, []);

  return (
    <div>
      <Dialog onOpenChange={(open) => {if (!open) {setPositionEditorRace(null);}}}>
        <DialogTrigger asChild>
          <Button className="cursor-pointer font-semibold">
            Select Race
          </Button>
        </DialogTrigger>
        <DialogContent className="min-h-[512px] max-w-5xl">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle>Race Schedule</DialogTitle>
              <Button
                size="sm"
                variant="ghost"
                onClick={clearFilters}
              >
                Reset
              </Button>
            </div>
          </DialogHeader>

          <div className="grid grid-cols-3 gap-6">
            {/* LEFT */}
            <div className="col-span-2 border rounded-xl p-4 flex flex-col h-[70vh]">
              <div
                ref={stickyRef}
                className="sticky top-0 z-40 bg-background pb-3"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {/* Terrain */}
                  <fieldset className="bg-card rounded-lg border border-border p-3 h-full">
                    <legend className="text-sm font-semibold px-1">
                      Terrain
                    </legend>
                    <div className="mt-2 grid grid-cols-2 gap-y-1">
                      {(["Turf", "Dirt"] as const).map((t) => (
                        <label
                          key={t}
                          className="flex items-center gap-2 text-sm"
                        >
                          <input
                            type="checkbox"
                            checked={fltTerrain.has(t)}
                            onChange={() => toggleSet(setFltTerrain, t)}
                          />
                          <span>{t}</span>
                        </label>
                      ))}
                    </div>
                  </fieldset>

                  {/* Distance */}
                  <fieldset className="bg-card rounded-lg border border-border p-3 h-full">
                    <legend className="text-sm font-semibold px-1">
                      Distance
                    </legend>
                    <div className="mt-2 grid grid-cols-2 gap-y-1">
                      {(["Short", "Mile", "Medium", "Long"] as const).map(
                        (d) => (
                          <label
                            key={d}
                            className="flex items-center gap-2 text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={fltDist.has(d)}
                              onChange={() => toggleSet(setFltDist, d)}
                            />
                            <span>{d}</span>
                          </label>
                        ),
                      )}
                    </div>
                  </fieldset>

                  {/* Grade */}
                  <fieldset className="bg-card rounded-lg border border-border p-3 h-full">
                    <legend className="text-sm font-semibold px-1">
                      Grade
                    </legend>
                    <div className="mt-2 grid grid-cols-3 gap-y-1 gap-x-2">
                      {(
                        ["G1", "G2", "G3", "OP", "Pre-OP"] as const
                      ).map((g) => (
                        <label
                          key={g}
                          className="flex items-center gap-2 text-sm whitespace-nowrap"
                        >
                          <input
                            type="checkbox"
                            checked={fltGrade.has(g)}
                            onChange={() => toggleSet(setFltGrade, g)}
                          />
                          <span>{g}</span>
                        </label>
                      ))}
                    </div>
                  </fieldset>
                </div>

                {/* Search */}
                <div className="mt-3 bg-card">
                  <Input
                    placeholder="Search..."
                    type="search"
                    value={search}
                    onChange={handleSearch}
                    className="rounded-lg"
                  />
                </div>
              </div>

              {/* Scrollable list */}
              <div className="mt-3 flex-1 overflow-y-auto pr-1 relative">
                {filteredData &&
                  Object.entries(filteredData).map(([year, raceList]) => (
                    <div
                      key={year}
                      className="flex flex-col gap-2 relative"
                    >
                      <p
                        className="text-xl font-semibold sticky z-10 bg-background pb-2"
                        style={{ top: filtersH }}
                      >
                        {year}
                      </p>
                      <div className="flex flex-col gap-2 px-4">
                        {Object.entries(raceList)
                          .filter(([name]) =>
                            name.toLowerCase().includes(search),
                          )
                          .map(([name, detail]) => {
                            const isSelected = raceSchedule.some(
                              (r) =>
                                r.name === name && r.year === year,
                            );
                            const isDisabled =
                              !isSelected &&
                              bookedDates.has(
                                `${year}::${detail.date}`,
                              );
                            return (
                              <div
                                key={`${year}::${name}`}
                                className={`border-2 rounded-md px-4 py-2 flex justify-between transition relative z-0
                                ${
                                  isSelected
                                    ? "border-primary bg-primary/10"
                                    : isDisabled
                                    ? "border-border/50 cursor-not-allowed opacity-40"
                                    : "border-border cursor-pointer hover:border-primary/50"
                                }`}
                                onClick={() => {
                                  if (isDisabled) return;
                                  if (isSelected) {
                                    deleteRaceSchedule(name, year);
                                  } else {
                                    addRaceSchedule({
                                      name,
                                      date: detail.date,
                                      year,
                                    });
                                  }
                                }}
                                title={
                                  isDisabled
                                    ? `Date already scheduled: ${year} ${detail.date}`
                                    : undefined
                                }
                              >
                                <div>
                                  <p className="font-semibold mb-2">
                                    {name}
                                    {detail.grade
                                      ? ` (${detail.grade})`
                                      : ""}{" "}
                                    - {detail.racetrack}
                                  </p>
                                  {(detail.sparks?.length ?? 0) >
                                    0 && (
                                    <p>
                                      Sparks:{" "}
                                      {detail.sparks!.join(", ")}
                                    </p>
                                  )}
                                  <p>
                                    Fans required:{" "}
                                    {(
                                      detail.fans?.required ?? 0
                                    ).toLocaleString()}
                                  </p>
                                  <p>
                                    Fans gained:{" "}
                                    {(
                                      detail.fans?.gained ?? 0
                                    ).toLocaleString()}
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p className="mb-2">
                                    {detail.date}
                                  </p>
                                  <p>{detail.distance.type}</p>
                                  <p>{detail.distance.meters}</p>
                                  <p>{detail.terrain}</p>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            {/* RIGHT */}
            <div className="border rounded-xl p-4 flex flex-col h-[70vh]">
              <div className="flex justify-between items-center">
                <p className="text-md font-semibold">
                  Race to schedule
                </p>
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={clearPositionForSpecificRace}
                  >
                    Clear positions
                  </Button>
                  <Button
                    size="sm"
                    className="cursor-pointer"
                    onClick={clearRaceSchedule}
                  >
                    Clear
                  </Button>
                </div>
              </div>

              <div className="mt-3 space-y-2 overflow-y-auto max-h-[62vh] pr-1">
                {scheduledSorted.map((race) => {
                  const specific = getSpecific(race);
                  const hasSpecific = !!specific;
                  const cardKey = `${race.year}::${race.date}::${race.name}`;

                  return (
                    <div
                      key={cardKey}
                      className="
                        relative
                        px-4 py-2
                        border-2 border-border
                        rounded-md
                        flex items-center justify-between
                        hover:border-primary/50
                        transition
                        cursor-pointer
                      "
                      onClick={() =>
                        deleteRaceSchedule(race.name, race.year)
                      }
                    >
                      <div className="flex flex-col">
                        <p className="font-semibold">{race.name}</p>
                        <p className="text-sm opacity-80">
                          {race.year} &middot; {race.date}
                        </p>
                        {specific && (
                          <p className="text-xs text-green-600 mt-1">
                            Position: {specific.position}
                          </p>
                        )}
                      </div>

                      <div className="ml-3">
                        <button
                          type="button"
                          className={
                            "h-8 w-8 flex items-center justify-center rounded-md border " +
                            (hasSpecific
                              ? "bg-green-500 border-green-600 text-white"
                              : "bg-white border-black text-black")
                          }
                          onClick={(e) => {
                            e.stopPropagation();
                            setPositionEditorRace(race);
                          }}
                        >
                          <Settings className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <PreferredPositionDialog
            race={positionEditorRace}
            getSpecific={getSpecific}
            onSelectPosition={handleSelectPosition}
            onClose={() => setPositionEditorRace(null)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}