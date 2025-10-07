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
};

export type RaceScheduleType = {
  name: string;
  year: string;
  date: string;
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

export type Config = {
  config_name: string;
  trainee: string;
  priority_stat: string[];
  priority_weights: number[];
  hint_point: number;
  use_optimal_event_choices: boolean;
  choice_weight: ChoiceWeight;
  use_priority_on_choice: boolean;
  sleep_time_multiplier: number;
  skip_training_energy: number;
  skip_infirmary_unless_missing_energy: number;
  priority_weight: string;
  never_rest_energy: number;
  minimum_mood: string;
  minimum_mood_junior_year: string;
  maximum_failure: number;
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
  stat_caps: Stat;
  skill: Skill;
  window_name: string;
};
