import { Checkbox } from "../ui/checkbox";

type Props = {
    optionalEvent: boolean;
    setOptionalEvent: (newState: boolean) => void;
};

export default function OptionalEvent({ optionalEvent, setOptionalEvent }: Props) {
    return (
        <div className="w-fit">
            <label htmlFor="optional-event" className="flex gap-2 items-center">
                <Checkbox id="optional-event" checked={optionalEvent} onCheckedChange={() => setOptionalEvent(!optionalEvent)} />
                <span className="text-lg font-medium shrink-0">Use Optional Event</span>
            </label>
        </div>
    );
}