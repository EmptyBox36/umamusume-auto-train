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
            <Tooltips>Rainbow Friendship = 2 points<br />Friendship If Not Maxed After Junior Year = 1.5 point<br />Normal Friendship = 1 Point<br />If Have Skill Hint = Hint Point</Tooltips>
        </label>
    );
}