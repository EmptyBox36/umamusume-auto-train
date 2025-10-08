import { Input } from "../ui/input";
import Tooltips from "../_c/Tooltips";

type Props = {
    choiceWeight: {
        spd: number;
        sta: number;
        pwr: number;
        guts: number;
        wit: number;
        hp: number;
        max_energy: number;
        skillpts: number;
        bond: number;
        mood: number;
    };
    setChoiceWeight: (keys: string, value: number) => void;
};

export default function ChoiceWeight({ choiceWeight, setChoiceWeight }: Props) {
    return (
        <div className="flex flex-col gap-2">
            <div className="flex gap-2 items-center">
                <p className="text-lg font-medium">Choice Weight</p>
                <Tooltips>Use to weight choice selection by score.</Tooltips>
            </div>
            <div className="flex flex-col gap-2">
                {Object.entries(choiceWeight).map(([stat, val]) => (
                    <label key={stat} className="flex items-center gap-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <span className="inline-block w-16">{stat.toUpperCase()}</span>
                        </div>
                        <Input type="number" value={val} step={0.1} onChange={(e) => setChoiceWeight(stat, e.target.valueAsNumber)} />
                    </label>
                ))}
            </div>
        </div>
    );
}