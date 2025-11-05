import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { encodeConfig } from "@/lib/configCodec";

export default function ExportConfig({ config }: { config: any }) {
    const [open, setOpen] = useState(false);
    const [shareCode, setShareCode] = useState("");

    const handleOpen = () => {
        const code = encodeConfig(config);
        setShareCode(code);
        setOpen(true);
    };

    const copyShare = async () => {
        try {
            await navigator.clipboard.writeText(shareCode);
            // popup feedback
            window.alert("Copied to clipboard!");
        } catch {
            window.alert("Copy failed. Please try again.");
        }
    };

    return (
        <>
            <Button variant="outline" className="w-28 h-10" onClick={handleOpen}>
                Export
            </Button>

            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader><DialogTitle>Export Preset</DialogTitle></DialogHeader>
                    <p className="text-sm text-muted-foreground">
                        Copy this code to share your configuration.
                    </p>
                    <textarea
                        readOnly
                        value={shareCode}
                        className="w-full h-40 font-mono text-xs rounded-md border p-2 bg-background"
                    />
                    <DialogFooter>
                        <Button variant="secondary" onClick={() => setOpen(false)}>Close</Button>
                        <Button onClick={copyShare}>Copy</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}