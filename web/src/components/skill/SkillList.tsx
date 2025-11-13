import { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

type Skill = {
    name: string;
    description: string;
    // id?: number | string; // keep if you later need a stable key per row
};

type Props = {
    list: string[];
    addSkillList: (newList: string) => void;
    deleteSkillList: (newList: string) => void;
};

export default function SkillList({ list, addSkillList, deleteSkillList }: Props) {
    const [open, setOpen] = useState(false);
    const [data, setData] = useState<Skill[]>([]);
    const [search, setSearch] = useState("");

    // Reset search each time the dialog opens so the initial render uses a clean query
    useEffect(() => {
        if (open) setSearch("");
    }, [open]);

    // Load skills once
    useEffect(() => {
        (async () => {
            try {
                const res = await fetch("/scraper/data/skills.json");
                const skills: Skill[] = await res.json();
                setData(skills);
            } catch (err) {
                console.error("Failed to fetch skills:", err);
            }
        })();
    }, []);

    // Filter by name OR description; re-compute whenever data OR search changes
    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        if (!q) return data;
        return data.filter(
            (s) =>
                (s.name ?? "").toLowerCase().includes(q) ||
                (s.description ?? "").toLowerCase().includes(q)
        );
    }, [data, search]);

    return (
        <div>
            <p className="text-lg font-medium mb-2">Select skill you want to buy</p>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                    <Button className="cursor-pointer font-semibold">Open</Button>
                </DialogTrigger>

                <DialogContent className="min-h-[512px] max-w-4xl">
                    <DialogHeader>
                        <DialogTitle>Skills List</DialogTitle>
                    </DialogHeader>

                    <div className="flex gap-6 min-h-[400px]">
                        {/* LEFT SIDE */}
                        <div className="w-9/12 flex flex-col">
                            <Input
                                placeholder="Search..."
                                type="search"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />

                            <div className="mt-4 grid grid-cols-2 gap-4 overflow-auto pr-2 max-h-[420px]">
                                {filtered.map((skill, idx) => (
                                    // if different skills can share the same name, keep a composite key
                                    <div
                                        key={`${skill.name}-${idx}`}
                                        className="w-full border-2 border-border rounded-lg px-3 py-2 cursor-pointer hover:border-primary/50 transition"
                                        onClick={() => addSkillList(skill.name)}
                                    >
                                        <p className="text-lg font-semibold">{skill.name}</p>
                                        <p className="text-sm text-muted-foreground">{skill.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* RIGHT SIDE */}
                        <div className="w-3/12 flex flex-col">
                            <p className="font-semibold mb-2">Skills to buy</p>
                            <div className="flex flex-col gap-2 overflow-auto pr-2 max-h-[420px]">
                                {list.map((item, i) => (
                                    <div
                                        key={`${item}-${i}`}
                                        className="px-4 py-2 cursor-pointer border-2 border-border rounded-lg flex justify-between items-center hover:border-destructive/50 transition"
                                        onClick={() => deleteSkillList(item)}
                                    >
                                        <p>{item}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}