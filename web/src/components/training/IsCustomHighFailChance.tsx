import { Checkbox } from "../ui/checkbox";
import Tooltips from "../_c/Tooltips";

type Props = {
    CustomFailureEnabled: boolean;
    enableCustomHighFailure: boolean;
    setCustomHighFailChance: (newState: boolean) => void;
};

export default function IsCustomHighFailChance({ CustomFailureEnabled, enableCustomHighFailure, setCustomHighFailChance}: Props) {
    return (
        <label htmlFor="is-custom-high-failure" className="flex gap-2 items-center">
            <Checkbox disabled={!CustomFailureEnabled} id="is-custom-high-failure" checked={enableCustomHighFailure} onCheckedChange={() => setCustomHighFailChance(!enableCustomHighFailure)} />
            <span className="text-lg font-medium shrink-0">Use High Point Condition?</span>
            <Tooltips>Recommend High Point: 4 (For URA), 5 (For Unity)<br />These Score Use to Set Condition Only Not Final Score</Tooltips>
        </label>
    );
}