import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import DEFAULT_CONFIG from "../../../../config.template.json";

export default function ResetConfig({ setConfig }: { setConfig: (cfg: any) => void }) {
    const [open, setOpen] = useState(false);

    const handleConfirm = () => {
        setConfig(DEFAULT_CONFIG as any);
        setOpen(false);
    };

    return (
        <>
            {/* Main Reset button */}
            <Button
                variant="destructive"
                className="w-28 h-10 text-white"
                onClick={() => setOpen(true)}
            >
                Reset
            </Button>

            {/* Confirmation dialog */}
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle>Confirm Reset</DialogTitle>
                    </DialogHeader>
                    <p className="text-sm text-muted-foreground">
                        Are you sure you want to reset all settings?
                        This will permanently restore the default configuration.
                    </p>
                    <DialogFooter className="mt-4">
                        <Button variant="secondary" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button variant="destructive" onClick={handleConfirm}>
                            Confirm Reset
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}