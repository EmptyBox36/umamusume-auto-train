import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import Tooltips from "../_c/Tooltips";

type Props = {
    trainee: string;
    setTrainee: (val: string) => void;
    options?: string[];
};

export default function TraineeSelect({ trainee, setTrainee, options = []}: Props) {
    return (
        <div className="flex items-center gap-2">
            <Select value={trainee ?? ""} onValueChange={setTrainee}>
                <SelectTrigger className="mt-2 w-full bg-card border-2 border-primary/20">
                    <SelectValue placeholder="Select Trainee" />
                </SelectTrigger>
                <SelectContent className="max-h-72 overflow-y-auto">
                    {options.map((name) => (
                        <SelectItem key={name} value={name}>{name}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
            <Tooltips>Choose the character to train. Used by event and hint logic.</Tooltips>
        </div>
    );
}

