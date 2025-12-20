export type Stat = {
  spd: number;
  sta: number;
  pwr: number;
  guts: number;
  wit: number;
};

export type Skill = {
  is_auto_buy_skill: boolean;
  skill_pts_check: number;
  skill_list: string[];
  desire_skill: string[];
  max_cost?: number;
  min_discount?: number;
};

export type RaceScheduleType = {
  name: string;
  year: string;
  date: string;
  turnNumber: number;
};

export type PositionForSpecificRace = {
    race_name: string;
    year: string;
    position: string;
};

export type ChoiceWeight = {
    spd: number;
    sta: number;
    pwr: number;
    guts: number;
    wit: number;
    hp: number;
    max_energy: number;
    skillpts: number;
    bond: number;
    mood: number;
};

export type LowFailCondition = {
    point: number;
    failure: number;
}

export type HighFailCondition = {
    point: number;
    failure: number;
}

export type failure = {
    maximum_failure: number;
    enable_custom_failure: boolean;
    enable_custom_low_failure: boolean;
    low_failure_condition: LowFailCondition;
    enable_custom_high_failure: boolean;
    high_failure_condition: HighFailCondition;
}

export type SkillEventChoice = {
    event_name: string;
    chosen: number;
};

export type event = {
    use_optimal_event_choices: boolean;
    event_choices?: SkillEventChoice[];
}

export const SPIRIT_STATS = ["spd", "sta", "pwr", "guts", "wit"] as const;
export type SpiritStat = typeof SPIRIT_STATS[number];

export type UnityCfg = {
    prefer_team_race: number[];
    spirit_burst_position: SpiritStat[];
};

export type Config = {
  config_name: string;
  trainee: string;
  scenario: string;
  priority_stat: string[];
  priority_weights: number[];
  summer_priority_weights: number[];
  hint_point: number;
  use_prioritize_on_junior: boolean;
  choice_weight: ChoiceWeight;
  use_priority_on_choice: boolean;
  sleep_time_multiplier: number;
  skip_training_energy: number;
  skip_infirmary_unless_missing_energy: number;
  priority_weight: string;
  never_rest_energy: number;
  minimum_mood: string;
  minimum_mood_with_friend: string;
  minimum_mood_junior_year: string;
  failure: failure;
  prioritize_g1_race: boolean;
  cancel_consecutive_race: boolean;
  position_selection_enabled: boolean;
  enable_positions_by_race: boolean;
  preferred_position: string;
  positions_by_race: {
    sprint: string;
    mile: string;
    medium: string;
    long: string;
  };
  race_schedule: RaceScheduleType[];
  position_for_specific_race: PositionForSpecificRace[];
  enable_race_schedule: boolean;
  run_race_on_poor_training: boolean;
  stat_caps: Stat;
  skill: Skill;
  window_name: string;
  event: event;
  unity?: UnityCfg;
  stop_bot_before_race: boolean;
};

export type Preset = { name: string; config: Config };
export type PresetStorage = { index: number; presets: Preset[] };