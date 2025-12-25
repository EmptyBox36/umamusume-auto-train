import { Checkbox } from "../ui/checkbox";

type Props = {
  enableRaceSchedule: boolean;
  setEnableRaceSchedule: (val: boolean) => void;
};

export default function EnableRaceSchedule({
  enableRaceSchedule,
  setEnableRaceSchedule,
}: Props) {
  return (
    <div className="w-fit">
      <label htmlFor="enable-race-schedule" className="flex gap-2 items-center">
        <Checkbox id="enable-race-schedule" checked={enableRaceSchedule} onCheckedChange={() => setEnableRaceSchedule(!enableRaceSchedule)} />
        <span className="text-lg font-medium shrink-0">Run Race Schedule?</span>
      </label>
    </div>
  );
}
