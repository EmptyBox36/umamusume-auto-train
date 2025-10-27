import { Checkbox } from "../ui/checkbox";
import Tooltips from "../_c/Tooltips";

type Props = {
    enableCustomFailure: boolean;
    setCustomFailChance: (newState: boolean) => void;
};

export default function IsCustomFailChance({ enableCustomFailure, setCustomFailChance}: Props) {
    return (
        <label htmlFor="is-custom-failure" className="flex gap-2 items-center">
            <Checkbox id="is-custom-failure" checked={enableCustomFailure} onCheckedChange={() => setCustomFailChance(!enableCustomFailure)} />
            <span className="text-lg font-medium shrink-0">Set Custom Failure Chance?</span>
            <Tooltips>It was if point MORE or LESS than NOT EQUAL</Tooltips>
        </label>
    );
}