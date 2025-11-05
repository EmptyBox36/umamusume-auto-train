import { Button } from "@/components/ui/button";
import ImportConfig from "./ImportConfig";
import ExportConfig from "./ExportConfig";
import ResetConfig from "./ResetConfig";

export default function ConfigManager({
    config,
    setConfig,
    saveConfig,
    savePreset,
    setNamePreset,
    activeIndex,
    presetName,
}: any) {
    return (
        <div className="flex flex-col items-center gap-2">
            {/* Large Save */}
            <Button
                size="lg"
                className="w-90 h-12 text-white text-lg font-semibold bg-primary hover:bg-primary/90 shadow-lg shadow-primary/30"
                onClick={() => {
                    setNamePreset(activeIndex, presetName);
                    savePreset(config);
                    saveConfig();
                }}
            >
                Save Configuration
            </Button>

            {/* Bottom row */}
            <div className="flex gap-3">
                <ImportConfig setConfig={setConfig} />
                <ExportConfig config={config} />
                <ResetConfig setConfig={setConfig} />
            </div>
        </div>
    );
}