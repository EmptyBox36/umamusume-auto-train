import { Input } from "../ui/input";

type Props = {
  hintPoint: number;
  setHintPoint: (val: number) => void;
};

export default function HintPoint({ hintPoint, setHintPoint }: Props) {
  return (
    <label htmlFor="hint-point" className="flex flex-col gap-2">
      <span className="text-lg font-medium">Hint Point</span>
      <div className="flex items-center gap-2">
        <Input
          className="w-24"
          type="number"
          id="hint-point"
          min={0}
          step={0.05}
          value={Number.isFinite(hintPoint) ? hintPoint : 0}
          onChange={(e) => setHintPoint(e.currentTarget.valueAsNumber || 0)}
        />
      </div>
    </label>
  );
}
