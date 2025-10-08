import { Checkbox } from "../ui/checkbox";

type Props = {
    enableCustomFailure: boolean;
    setCustomFailChance: (newState: boolean) => void;
};

export default function IsCustomFailChance({ enableCustomFailure, setCustomFailChance}: Props) {
    return (
        <label htmlFor="is-custom-failure" className="flex gap-2 items-center">
            <Checkbox id="is-custom-failure" checked={enableCustomFailure} onCheckedChange={() => setCustomFailChance(!enableCustomFailure)} />
            <span className="text-lg font-medium shrink-0">Set Custom Failure Chance?</span>
        </label>
    );
}