import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { decodeConfig } from "@/lib/configCodec";

export default function ImportConfig({ setConfig }: { setConfig: (cfg: any) => void }) {
    const [open, setOpen] = useState(false);
    const [code, setCode] = useState("");
    const [err, setErr] = useState<string | null>(null);

    const handleImport = () => {
        try {
            const cfg = decodeConfig(code.trim());
            setConfig(cfg);
            setOpen(false);
            setErr(null);
        } catch (e: any) {
            setErr(e?.message ?? "Invalid code");
        }
    };

    return (
        <>
            <Button variant="outline" className="w-28 h-10" onClick={() => setOpen(true)}>
                Import
            </Button>

            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader><DialogTitle>Import Preset</DialogTitle></DialogHeader>
                    <textarea
                        placeholder="Paste share code here"
                        value={code}
                        onChange={(e) => { setCode(e.target.value); setErr(null); }}
                        className="w-full h-40 font-mono text-xs rounded-md border p-2 bg-background"
                    />
                    {err && <p className="text-sm text-red-600">{err}</p>}
                    <DialogFooter>
                        <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
                        <Button onClick={handleImport}>Import</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}