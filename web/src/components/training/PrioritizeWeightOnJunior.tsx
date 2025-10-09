import { Checkbox } from "../ui/checkbox";

type Props = {
    juniorPrioritize: boolean;
    setJuniorPrioritize: (newState: boolean) => void;
};

export default function JuniorPrioritize({ juniorPrioritize, setJuniorPrioritize }: Props) {
    return (
        <div className="w-fit">
            <label htmlFor="stat-prioritize-on-junior" className="flex gap-2 items-center">
                <Checkbox id="stat-prioritize-on-junior" checked={juniorPrioritize} onCheckedChange={() => setJuniorPrioritize(!juniorPrioritize)} />
                <span className="text-lg font-medium shrink-0">Use Stat Prioritize on Junior Year</span>
            </label>
        </div>
    );
}