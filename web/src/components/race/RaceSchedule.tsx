import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "../ui/button";
import { useEffect, useState } from "react";
import type { RaceScheduleType } from "@/types";

type RaceType = {
    id: number;
    date: string;
    racetrack: string;
    terrain: "Turf" | "Dirt";
    distance: { type: "Sprint" | "Mile" | "Medium" | "Long"; meters: number };
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
};

export default function RaceSchedule({ raceSchedule, addRaceSchedule, deleteRaceSchedule, clearRaceSchedule }: Props) {
  const [data, setData] = useState<RaceScheduleDataType | null>(null);

  type TerrainT = "Turf" | "Dirt";
  type DistT = "Sprint" | "Mile" | "Medium" | "Long";
  type GradeT = "G1" | "G2" | "G3" | "OP" | "Pre-OP";

  const [showFilter, setShowFilter] = useState(false);
  const [fltTerrain, setFltTerrain] = useState<Set<TerrainT>>(new Set());
  const [fltDist, setFltDist] = useState<Set<DistT>>(new Set());
  const [fltGrade, setFltGrade] = useState<Set<GradeT>>(new Set());

  const toggleSet = <T,>(setter: React.Dispatch<React.SetStateAction<Set<T>>>, v: T) => {
  setter(prev => {const s = new Set(prev);if (s.has(v)) { s.delete(v);} else {s.add(v);}return s;});};

  const clearFilters = () => { setFltTerrain(new Set()); setFltDist(new Set()); setFltGrade(new Set()); };

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
          .map(r => {
              const yearData = (data as Record<string, Record<string, RaceType>>)[r.year];
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
      (fltGrade.size === 0 || (r.grade ? fltGrade.has(r.grade as GradeT) : false));

  const filteredData: RaceScheduleDataType | null = data
      ? (Object.fromEntries(
          Object.entries(data).map(([year, list]) => [
              year,
              Object.fromEntries(Object.entries(list).filter(([, v]) => passes(v))),
          ])
      ) as RaceScheduleDataType)
      : null;

  const bookedDates = new Set(
      raceSchedule.map(r => `${r.year}::${r.date}`)
  );

  return (
    <div>
      <Dialog>
        <DialogTrigger asChild>
          <Button className="cursor-pointer font-semibold">Select Race</Button>
        </DialogTrigger>
        <DialogContent className="min-h-[512px] max-w-4xl">
          <DialogHeader>
              <div className="flex items-center justify-between">
              <DialogTitle>Race Schedule</DialogTitle>
              <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setShowFilter(v => !v)}>Filter</Button>
                  <Button size="sm" variant="ghost" onClick={clearFilters}>Reset</Button>
              </div>
              </div>

              {showFilter && (
              <div className="mt-3 grid grid-cols-3 gap-3">
                  {/* Terrain */}
                  <div>
                  <p className="text-sm font-semibold mb-1">Terrain</p>
                  {(["Turf","Dirt"] as TerrainT[]).map(t => (
                      <label key={t} className="mr-3 text-sm">
                      <input type="checkbox"
                          checked={fltTerrain.has(t)}
                          onChange={() => toggleSet(setFltTerrain, t)} /> {t}
                      </label>
                  ))}
                  </div>

                  {/* Distance */}
                  <div>
                  <p className="text-sm font-semibold mb-1">Distance</p>
                  {(["Sprint","Mile","Medium","Long"] as DistT[]).map(d => (
                      <label key={d} className="mr-3 text-sm">
                      <input type="checkbox"
                          checked={fltDist.has(d)}
                          onChange={() => toggleSet(setFltDist, d)} /> {d}
                      </label>
                  ))}
                  </div>

                  {/* Grade */}
                  <div>
                  <p className="text-sm font-semibold mb-1">Grade</p>
                  {(["G1","G2","G3","OP","Pre-OP"] as GradeT[]).map(g => (
                    <label key={g} className="mr-3 text-sm">
                      <input
                        type="checkbox"
                        checked={fltGrade.has(g)}
                        onChange={() => toggleSet(setFltGrade, g)}
                      /> {g}
                    </label>
                  ))}
                  </div>
              </div>
              )}
          </DialogHeader>
          <div className="flex gap-6 min-h-[400px]">
            <div className="w-9/12 flex flex-col gap-4 max-h-[420px] overflow-auto">
              {/* <Input placeholder="Search..." type="search" value={search} onChange={handleSearch} /> */}
              {filteredData &&
                Object.entries(filteredData).map(([year, raceList]) => (
                  <div key={year} className="flex flex-col gap-2 relative">
                    <p className="text-xl font-semibold sticky top-0 bg-card pb-2">{year}</p>
                    <div className="flex flex-col gap-2 px-4">
                      {Object.entries(raceList).map(([name, detail]) => {
                        const isSelected = raceSchedule.some(r => r.name === name && r.year === year);
                        const isDisabled = !isSelected && bookedDates.has(`${year}::${detail.date}`);

                        return (
                          <div
                            key={`${year}::${name}`}
                            className={`border-2 rounded-md px-4 py-2 flex justify-between transition
                              ${isSelected ? "border-primary bg-primary/10"
                                           : isDisabled ? "border-border/50 opacity-60 cursor-not-allowed"
                                                        : "border-border cursor-pointer hover:border-primary/50"}`}
                            onClick={() => {
                              if (isDisabled) return;                          // block double-booking same date
                              if (isSelected) deleteRaceSchedule(name, year);  // toggle off
                              else addRaceSchedule({ name, date: detail.date, year});
                            }}
                            title={isDisabled ? `Date already scheduled: ${detail.date}` : undefined}
                          >
                            <div>
                              <p className="font-semibold mb-2">
                                {name}{detail.grade ? ` (${detail.grade})` : ""} - {detail.racetrack}
                              </p>
                              {(detail.sparks?.length ?? 0) > 0 && (
                                <p>Sparks: {detail.sparks!.join(", ")}</p>
                              )}
                              <p>Fans required: {(detail.fans?.required ?? 0).toLocaleString()}</p>
                              <p>Fans gained: {(detail.fans?.gained ?? 0).toLocaleString()}</p>
                            </div>
                            <div className="text-right">
                              <p className="mb-2">{detail.date}</p>
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
            <div className="w-3/12 flex flex-col">
              <div className="flex justify-between items-center">
                <p className="text-lg font-semibold">Race to schedule</p>
                <Button size={"sm"} className="cursor-pointer" onClick={() => clearRaceSchedule()}>
                  Clear
                </Button>
              </div>
              <div className="flex flex-col gap-2 overflow-auto pr-2 max-h-[395px] mt-2">
                {scheduledSorted.map((race) => (
                  <div key={`${race.year}::${race.name}`}
                       className="px-4 py-2 border-2 border-border rounded-md hover:border-primary/50 transition cursor-pointer"
                       onClick={() => deleteRaceSchedule(race.name, race.year)}>
                    <p className="font-semibold">{race.name}</p>
                    <p>{race.year} {race.date}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}