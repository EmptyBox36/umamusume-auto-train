import { useEffect, useState } from "react";
import rawConfig from "../../config.json";
import { useConfigPreset } from "./hooks/useConfigPreset";
import { useConfig } from "./hooks/useConfig";
import type { Config } from "./types";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import Tooltips from "./components/_c/Tooltips";
import SkillList from "./components/skill/SkillList";
import PriorityStat from "./components/training/PriorityStat";
import StatCaps from "./components/training/StatCaps";
import Mood from "./components/Mood";
import FailChance from "./components/FailChance";
import PrioritizeG1 from "./components/race/PrioritizeG1";
import CancelConsecutive from "./components/race/CancelConsecutive";
import PriorityWeight from "./components/training/PriorityWeight";
import PriorityWeights from "./components/training/PriorityWeights";
import EnergyInput from "./components/energy/EnergyInput";
import IsAutoBuy from "./components/skill/IsAutoBuy";
import SkillPtsCheck from "./components/skill/SkillPtsCheck";
import IsPositionSelectionEnabled from "./components/race/IsPositionSelectionEnabled";
import PreferredPosition from "./components/race/PreferredPosition";
import IsPositionByRace from "./components/race/IsPositionByRace";
import PositionByRace from "./components/race/PositionByRace";
import WindowName from "./components/WindowName";
import SleepMultiplier from "./components/SleepMultiplier";
import RaceSchedule from "./components/race/RaceSchedule";
import HintPoint from "./components/training/HintPoint";
import TraineeSelect from "./components/setting/TraineeSelect";
import OptionalEvent from "./components/Event/OptionalEvent";
import ChoiceWeight from "./components/Event/ChoiceWeight";
import PriorityOnChoice from "./components/Event/PriorityOnChoice";
import IsCustomFailChance from "./components/training/IsCustomFailChance";
import IsCustomLowFailChance from "./components/training/IsCustomLowFailChance";
import IsCustomHighFailChance from "./components/training/IsCustomHighFailChance";
import CustomLowFailChance from "./components/training/CustomLowFailChance";
import CustomHighFailChance from "./components/training/CustomHighFailChance";
import JuniorPrioritize from "./components/training/PrioritizeWeightOnJunior";
import { BarChart3, BrainCircuit, ChevronsRight, Cog, Trophy, MessageCircleMore } from "lucide-react";
import ScenarioSelect from "./components/setting/ScenarioSelect";
import ConfigManager from "./components/config/ConfigManager";

function App() {
  const defaultConfig = rawConfig as Config;
  const { activeIndex, activeConfig, presets, setActiveIndex, setNamePreset, savePreset } = useConfigPreset();
  const { config, setConfig, saveConfig } = useConfig(activeConfig ?? defaultConfig);
  const [presetName, setPresetName] = useState<string>("");
  const [traineeOptions, setTraineeOptions] = useState<string[]>([]);
  const [scenarioOptions, setScenarioOptions] = useState<string[]>([]);

  useEffect(() => {
    if (presets[activeIndex]) {
      setPresetName(presets[activeIndex].name);
      setConfig(presets[activeIndex].config ?? defaultConfig);
    } else {
      setPresetName("");
      setConfig(defaultConfig);
    }
  }, [activeIndex, presets, setConfig]);

  useEffect(() => {
    fetch("/scraper/data/characters.json", { cache: "no-store" })
      .then(r => r.json())
      .then(j => setTraineeOptions(Object.keys(j).sort()))
      .catch(() => setTraineeOptions([]));
  }, []);

  useEffect(() => {
    fetch("/data/scenarios.json", { cache: "no-store" })
      .then(r => r.json())
      .then(j => setScenarioOptions(Object.keys(j).sort()))
      .catch(() => setScenarioOptions([]));
  }, []);

  const {
    priority_stat,
    priority_weights,
    sleep_time_multiplier,
    skip_training_energy,
    never_rest_energy,
    skip_infirmary_unless_missing_energy,
    minimum_mood,
    priority_weight,
    hint_point,
    use_optimal_event_choices,
    choice_weight,
    use_priority_on_choice,
    minimum_mood_junior_year,
    prioritize_g1_race,
    cancel_consecutive_race,
    position_selection_enabled,
    enable_positions_by_race,
    preferred_position,
    positions_by_race,
    race_schedule,
    stat_caps,
    trainee,
    scenario,
    skill,
    window_name,
    use_prioritize_on_junior,
    failure,
  } = config;

  const {
    maximum_failure,
    enable_custom_failure,
    enable_custom_low_failure,
    low_failure_condition,
    enable_custom_high_failure,
    high_failure_condition,
  } = failure;
  const { is_auto_buy_skill, skill_pts_check, skill_list, desire_skill } = skill;

  const updateConfig = <K extends keyof typeof config>(key: K, value: (typeof config)[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    if (!failure.enable_custom_failure) {
      updateConfig("failure", {
        ...failure,
        enable_custom_low_failure: false,
        enable_custom_high_failure: false,
      });
    }
  }, [failure.enable_custom_failure]);

  return (
    <div className="min-h-screen w-full bg-background text-foreground p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-10 flex items-center justify-between">
          <div>
            <h1 className="text-5xl font-bold text-primary tracking-tight">Uma Auto Train</h1>
            <p className="text-muted-foreground mt-2 text-lg">Configure your auto-training settings below.</p>
          </div>
          <div className="flex items-center gap-4">
            <p className="text-muted-foreground">
              Press <span className="font-bold text-primary">F1</span> to start/stop the bot.
            </p>
            <ConfigManager
                config={config}
                setConfig={setConfig}
                saveConfig={saveConfig}
                savePreset={savePreset}
                setNamePreset={setNamePreset}
                activeIndex={activeIndex}
                presetName={presetName}
            />
          </div>
        </header>

        <div className="flex flex-wrap gap-4 mb-8">
          {presets.map((_, i) => (
            <Button key={_.name} variant={i === activeIndex ? "default" : "outline"} size="sm" onClick={() => setActiveIndex(i)}>
              Preset {i + 1}
            </Button>
          ))}
        </div>

        {/* Preset Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
              {/* fixed-height label row */}
              <div className="flex items-center gap-2 min-h-[28px]">
                  <span className="text-xl font-semibold text-primary leading-none">Preset Name</span>
              </div>
              <Input
                  className="mt-2 w-full bg-card border-2 border-primary/20 focus:border-primary/50"
                  placeholder="Preset Name"
                  value={presetName}
                  onChange={(e) => {
                      const val = e.target.value;
                      setPresetName(val);
                      updateConfig("config_name", val);
                  }}
              />
          </div>

          <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
            <label className="text-xl font-semibold mb-2 text-primary">Trainee</label>
            <div className="relative flex items-center w-full gap-2">
              <div className="flex-grow">
                <TraineeSelect
                  trainee={trainee ?? ""}
                  setTrainee={(v) => updateConfig("trainee", v)}
                  options={traineeOptions}
                />
              </div>
            </div>
          </div>
          <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
            <label className="text-xl font-semibold mb-2 text-primary">Scenario</label>
            <div className="relative flex items-center w-full gap-2">
              <div className="flex-grow">
                <ScenarioSelect
                  scenario={scenario ?? ""}
                  setScenario={(v) => updateConfig("scenario", v)}
                  options={scenarioOptions}
                />
              </div>
            </div>
          </div>
        </div>

        

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 flex flex-col gap-8">
            <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
              <h2 className="text-3xl font-semibold mb-6 flex items-center gap-3"><BarChart3 className="text-primary"/>Training</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <PriorityStat priorityStat={priority_stat} setPriorityStat={(val) => updateConfig("priority_stat", val)} />
                <PriorityWeights
                  priorityWeights={priority_weights}
                  setPriorityWeights={(val, i) => {
                    const newWeights = [...config.priority_weights];
                    newWeights[i] = isNaN(val) ? 0 : val;
                    updateConfig("priority_weights", newWeights);
                  }}
                />
                <PriorityWeight priorityWeight={priority_weight} setPriorityWeight={(val) => updateConfig("priority_weight", val)} />
                <div className="flex flex-col gap-4">
                    <JuniorPrioritize juniorPrioritize={use_prioritize_on_junior} setJuniorPrioritize={(val) => updateConfig("use_prioritize_on_junior", val)} />
                    <HintPoint hintPoint={hint_point ?? 0} setHintPoint={(val) => updateConfig("hint_point", val)}/>
                </div>
              </div>
              <div className="mt-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <StatCaps statCaps={stat_caps} setStatCaps={(key, val) => updateConfig("stat_caps", { ...stat_caps, [key]: isNaN(val) ? 0 : val })} />
                    <div className="flex flex-col gap-4">
                        <FailChance maximumFailure={maximum_failure} setFail={(val) => updateConfig("failure", { ...failure, maximum_failure: isNaN(val) ? 0 : val })} />
                        <IsCustomFailChance enableCustomFailure={enable_custom_failure} setCustomFailChance={(val) => updateConfig("failure", { ...failure, enable_custom_failure: val })} />
                        <IsCustomLowFailChance CustomFailureEnabled={enable_custom_failure} enableCustomLowFailure={enable_custom_low_failure} setCustomLowFailChance={(val) => updateConfig("failure", { ...failure, enable_custom_low_failure: val })} />
                        <CustomLowFailChance LowFailChanceEnabled={enable_custom_low_failure} customLowCondition={low_failure_condition} setLowCondition={(key, val) => updateConfig("failure", {...failure,low_failure_condition: {...low_failure_condition,[key]: isNaN(val) ? 0 : val,},})} /> 
                        <IsCustomHighFailChance CustomFailureEnabled={enable_custom_failure} enableCustomHighFailure={enable_custom_high_failure} setCustomHighFailChance={(val) => updateConfig("failure", { ...failure, enable_custom_high_failure: val })} />
                                      <CustomHighFailChance HighFailChanceEnabled={enable_custom_high_failure} customHighCondition={high_failure_condition} setHighCondition={(key, val) => updateConfig("failure", { ...failure, high_failure_condition: { ...high_failure_condition, [key]: isNaN(val) ? 0 : val, }, })} /> 
                    </div>
                </div>
              </div>
            </div>

            <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
              <h2 className="text-3xl font-semibold mb-6 flex items-center gap-3"><Cog className="text-primary"/>General</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <WindowName windowName={window_name} setWindowName={(val) => updateConfig("window_name", val)} />
                <Mood minimumMood={minimum_mood} setMood={(val) => updateConfig("minimum_mood", val)} minimumMoodJunior={minimum_mood_junior_year} setMoodJunior={(val) => updateConfig("minimum_mood_junior_year", val)} />
                <div className="flex flex-col gap-6">
                  <EnergyInput name="skip-training-energy" value={skip_training_energy} setValue={(val) => updateConfig("skip_training_energy", val)}>
                    Skip Training Energy
                  </EnergyInput>
                  <EnergyInput name="never-rest-energy" value={never_rest_energy} setValue={(val) => updateConfig("never_rest_energy", val)}>
                    Never Rest Energy
                  </EnergyInput>
                  <EnergyInput name="skip-infirmary-unless_missing-energy" value={skip_infirmary_unless_missing_energy} setValue={(val) => updateConfig("skip_infirmary_unless_missing_energy", val)}>
                    Skip Infirmary
                  </EnergyInput>
                </div>
                <SleepMultiplier sleepMultiplier={sleep_time_multiplier} setSleepMultiplier={(val) => updateConfig("sleep_time_multiplier", val)} />
              </div>
            </div>

            <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
              <h2 className="text-3xl font-semibold mb-6 flex items-center gap-3"><Trophy className="text-primary"/>Race</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="flex flex-col gap-6">
                  <IsPositionSelectionEnabled positionSelectionEnabled={position_selection_enabled} setPositionSelectionEnabled={(val) => updateConfig("position_selection_enabled", val)} />
                  <PreferredPosition
                      preferredPosition={preferred_position}
                      setPreferredPosition={(val) => updateConfig("preferred_position", val)}
                      enablePositionsByRace={enable_positions_by_race}
                      positionSelectionEnabled={position_selection_enabled}
                    />
                </div>
                <div className="flex flex-col gap-6">
                  <IsPositionByRace enablePositionsByRace={enable_positions_by_race} setPositionByRace={(val) => updateConfig("enable_positions_by_race", val)} positionSelectionEnabled={position_selection_enabled} />
                  <PositionByRace
                    positionByRace={positions_by_race}
                    setPositionByRace={(key, val) => updateConfig("positions_by_race", { ...positions_by_race, [key]: val })}
                    enablePositionsByRace={enable_positions_by_race}
                    positionSelectionEnabled={position_selection_enabled}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-8">
            <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
              <h2 className="text-3xl font-semibold mb-6 flex items-center gap-3"><BrainCircuit className="text-primary"/>Skill</h2>
              <div className="flex flex-col gap-6">
                <IsAutoBuy isAutoBuySkill={is_auto_buy_skill} setAutoBuySkill={(val) => updateConfig("skill", { ...skill, is_auto_buy_skill: val })} />
                <SkillPtsCheck skillPtsCheck={skill_pts_check} setSkillPtsCheck={(val) => updateConfig("skill", { ...skill, skill_pts_check: val })} />
                <SkillList
                  list={skill_list}
                  addSkillList={(val) => updateConfig("skill", { ...skill, skill_list: [val, ...skill_list] })}
                  deleteSkillList={(val) => updateConfig("skill", { ...skill, skill_list: skill_list.filter((s) => s !== val) })}
                />
              </div>
            </div>
            <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
              <h2 className="text-3xl font-semibold mb-6 flex items-center gap-3"><ChevronsRight className="text-primary"/>Race Schedule</h2>
              <div className="flex flex-col gap-4">
                <PrioritizeG1 prioritizeG1Race={prioritize_g1_race} setPrioritizeG1={(val) => updateConfig("prioritize_g1_race", val)} />
                <CancelConsecutive cancelConsecutive={cancel_consecutive_race} setCancelConsecutive={(val) => updateConfig("cancel_consecutive_race", val)} />
                <RaceSchedule
                raceSchedule={race_schedule}
                addRaceSchedule={(val) => updateConfig("race_schedule", [...race_schedule, val])}
                deleteRaceSchedule={(name, year) =>
                    updateConfig(
                    "race_schedule",
                    race_schedule.filter((race) => race.name !== name || race.year !== year)
                    )
                }
                clearRaceSchedule={() => updateConfig("race_schedule", [])}
                />
              </div>
            </div>
            <div className="bg-card p-6 rounded-xl shadow-lg border border-border/20">
              <div className="flex flex-col gap-6">
                <div className="flex gap-2 items-center">
                    <h2 className="text-3xl font-semibold flex items-center gap-3"><MessageCircleMore className="text-primary" />Event</h2>
                    <Tooltips>Skill hint → Score System → Custom Choice.</Tooltips> 
                </div>
                <div className="flex flex-col gap-6">
                    <OptionalEvent optionalEvent={use_optimal_event_choices} setOptionalEvent={(val) => updateConfig("use_optimal_event_choices", val)} />
                    <SkillList
                         list={desire_skill}
                         addSkillList={(val) => updateConfig("skill", { ...skill, desire_skill: [val, ...desire_skill] })}
                         deleteSkillList={(val) => updateConfig("skill", { ...skill, desire_skill: desire_skill.filter((s) => s !== val) })}
                    />
                    <PriorityOnChoice priorityOnChoice={use_priority_on_choice} setPriorityOnChoice={(val) => updateConfig("use_priority_on_choice", val)} />
                    <ChoiceWeight choiceWeight={choice_weight} setChoiceWeight={(key, val) => updateConfig("choice_weight", { ...choice_weight, [key]: isNaN(val) ? 0 : val })} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;