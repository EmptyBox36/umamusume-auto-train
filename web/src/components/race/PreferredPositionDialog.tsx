import { Button } from "@/components/ui/button";
import type { RaceScheduleType, PositionForSpecificRace } from "@/types";
import { X } from "lucide-react";

type Props = {
  race: RaceScheduleType | null;
  getSpecific: (race: RaceScheduleType) => PositionForSpecificRace | undefined;
  onSelectPosition: (race: RaceScheduleType, position: string) => void;
  onClose: () => void;
};

export default function PreferredPositionDialog({
  race,
  getSpecific,
  onSelectPosition,
  onClose,
}: Props) {
  if (!race) return null;

  const specific = getSpecific(race);

  const handleClick = (pos: string) => {
    onSelectPosition(race, pos);
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30"
      onClick={onClose}
    >
      <div
        className="relative bg-background border border-border rounded-lg shadow-lg p-5 w-72"
        onClick={(e) => e.stopPropagation()}
      >
        {/* X button */}
        <button
          onClick={onClose}
          className="absolute top-2 right-2 p-1 rounded-full hover:bg-muted transition"
        >
          <X size={16} />
        </button>

        <p className="text-sm font-semibold mb-2">Preferred position</p>
        <p className="text-xs text-muted-foreground mb-4 leading-tight">
          {race.name} &middot; {race.year} {race.date}
        </p>

        <div className="grid grid-cols-2 gap-3">
          {["front", "pace", "late", "end"].map((pos) => {
            const selected = specific?.position === pos;
            return (
              <Button
                key={pos}
                size="sm"
                variant={selected ? "default" : "outline"}
                className="text-xs capitalize"
                onClick={() => handleClick(pos)}
              >
                {pos}
              </Button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
