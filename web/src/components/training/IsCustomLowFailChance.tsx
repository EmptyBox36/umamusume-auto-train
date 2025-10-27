import { Checkbox } from "../ui/checkbox";
import Tooltips from "../_c/Tooltips";

type Props = {
    CustomFailureEnabled: boolean;
    enableCustomLowFailure: boolean;
    setCustomLowFailChance: (newState: boolean) => void;
};

export default function IsCustomLowFailChance({ CustomFailureEnabled, enableCustomLowFailure, setCustomLowFailChance}: Props) {
    return (
        <label htmlFor="is-custom-low-failure" className="flex gap-2 items-center">
            <Checkbox disabled={!CustomFailureEnabled} id="is-custom-low-failure" checked={enableCustomLowFailure} onCheckedChange={() => setCustomLowFailChance(!enableCustomLowFailure)} />
            <span className="text-lg font-medium shrink-0">Use Low Point Condition?</span>
            <Tooltips>Each Rainbow Friendship = 1.5 points<br />Each Non-Maxed Friendship = 1 point<br />Each Orange or Maxed Friendship = 0 Point<br />If have hint, point + 1<br />Recommend Low Point = 1<br />These Score Use to Set Condition Only Not Final Score</Tooltips>
        </label>
    );
}