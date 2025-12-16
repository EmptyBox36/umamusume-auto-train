import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

type Props = {
    scenario: string;
    setScenario: (val: string) => void;
    options?: string[];
};

export default function ScenarioSelect({ scenario, setScenario, options = [] }: Props) {
    return (
        <div className="flex gap-2 items-center">
            <Select value={scenario ?? ""} onValueChange={setScenario}>
                <SelectTrigger className="mt-2 w-full bg-card border-2 border-primary/20">
                    <SelectValue placeholder="Select Scenario" />
                </SelectTrigger>
                <SelectContent className="max-h-72 overflow-y-auto">
                    {options.map((name) => (
                        <SelectItem key={name} value={name}>{name}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}

