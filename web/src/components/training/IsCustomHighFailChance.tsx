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
            <Tooltips>Each Rainbow Friendship = 1.5 points<br />Each Non-Maxed Friendship = 1 point<br />Each Orange or Maxed Friendship = 0 Point<br />If have hint, point + 1<br />Recommend High Point = 3<br />These Score Use to Set Condition Only Not Final Score</Tooltips>
        </label>
    );
}