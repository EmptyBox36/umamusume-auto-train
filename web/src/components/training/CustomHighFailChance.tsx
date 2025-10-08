import { Input } from "../ui/input";

type Props = {
    customHighCondition: {
        point: number;
        failure: number;
    };
    setHighCondition: (keys: string, value: number) => void;
    HighFailChanceEnabled: boolean;
};

export default function CustomHighFailChance({ customHighCondition, setHighCondition, HighFailChanceEnabled }: Props) {
    return (
        <div className="flex flex-col gap-2 w-fit">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {Object.entries(customHighCondition).map(([condition, val]) => (
                    <label key={condition} className="flex items-center gap-4">
                        <span className="inline-block w-16">{condition.toUpperCase()}</span>
                        <Input disabled={!HighFailChanceEnabled} type="number" value={val} min={0} onChange={(e) => setHighCondition(condition, e.target.valueAsNumber)} />
                    </label>
                ))}
            </div>
        </div>
    );
}