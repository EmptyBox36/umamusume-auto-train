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
            <Tooltips>Rainbow Friendship = 2 points<br />Friendship If Not Maxed After Junior Year = 1.5 point<br />Normal Friendship = 1 Point<br />If Have Skill Hint = Hint Point</Tooltips>
        </label>
    );
}