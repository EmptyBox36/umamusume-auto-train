import { Input } from "../ui/input";

type Props = {
  summerPriorityWeights: number[];
  setSummerPriorityWeights: (weight: number, index: number) => void;
};

export default function SummerPriorityWeights({ summerPriorityWeights, setSummerPriorityWeights }: Props) {
  return (
    <div className="flex flex-col gap-2 w-fit">
      <p className="text-lg font-medium">Summer Weight Multiplier</p>
      <div className="flex flex-col gap-2">
        {Array.from({ length: 5 }, (_, i) => (
          <Input type="number" key={i} step={0.05} value={summerPriorityWeights[i]} onChange={(e) => setSummerPriorityWeights(e.target.valueAsNumber, i)} />
        ))}
      </div>
    </div>
  );
}