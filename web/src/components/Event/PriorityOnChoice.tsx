import { Checkbox } from "../ui/checkbox";

type Props = {
    priorityOnChoice: boolean;
    setPriorityOnChoice: (newState: boolean) => void;
};

export default function PriorityOnChoice({ priorityOnChoice, setPriorityOnChoice }: Props) {
    return (
        <div className="w-fit">
            <label htmlFor="priority-on-choice" className="flex gap-2 items-center">
                <Checkbox id="priority-on-choice" checked={priorityOnChoice} onCheckedChange={() => setPriorityOnChoice(!priorityOnChoice)} />
                <span className="text-lg font-medium shrink-0">Use Priority Weight on Choice.</span>
            </label>
        </div>
    );
}