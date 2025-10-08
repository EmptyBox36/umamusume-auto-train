import { Input } from "../ui/input";

type Props = {
    customLowCondition: {
        point: number;
        failure: number;
    };
    setLowCondition: (keys: string, value: number) => void;
    LowFailChanceEnabled: boolean;
};

export default function CustomLowFailChance({ customLowCondition, setLowCondition, LowFailChanceEnabled }: Props) {
    return (
        <div className="flex flex-col gap-2 w-fit">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {Object.entries(customLowCondition).map(([condition, val]) => (
                    <label key={condition} className="flex items-center gap-4">
                        <span className="inline-block w-16">{condition.toUpperCase()}</span>
                        <Input disabled={!LowFailChanceEnabled} type="number" value={val} min={0} onChange={(e) => setLowCondition(condition, e.target.valueAsNumber)} />
                    </label>
                ))}
            </div>
        </div>
    );
}