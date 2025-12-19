import { Checkbox } from "../ui/checkbox";

type Props = {
  runRaceOnPoorTraining: boolean;
  setRunRaceOnPoorTraining: (val: boolean) => void;
};

export default function RunRaceOnPoorTraining({
  runRaceOnPoorTraining,
  setRunRaceOnPoorTraining,
}: Props) {
  return (
    <div className="w-fit">
      <label htmlFor="run-race-on-poor-training" className="flex gap-2 items-center">
        <Checkbox id="run-race-on-poor-training" checked={runRaceOnPoorTraining} onCheckedChange={() => setRunRaceOnPoorTraining(!runRaceOnPoorTraining)} />
        <span className="text-lg font-medium shrink-0">Run Race on Poor Training?</span>
      </label>
    </div>
  );
}
