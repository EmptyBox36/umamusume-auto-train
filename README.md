# Umamusume Auto Train

Like the title says, this is a simple auto training for Umamusume.

Original project [samsulpanjul/umamusume-auto-train](https://github.com/samsulpanjul/umamusume-auto-train)

And this project also inspired by [steve1316/uma-android-automation](https://github.com/steve1316/uma-android-automation)

# ⚠️ USE IT AT YOUR OWN RISK ⚠️

I am not responsible for any issues, account bans, or losses that may occur from using it.
Use responsibly and at your own discretion.

## Features

- Automatically trains Uma
- Keeps racing until fan count meets the goal, and always picks races with matching aptitude
- Checks mood
- Handle debuffs
- Rest
- Selectable G1 races in the race schedule
- Stat target feature, if a stat already hits the target, skip training that one
- Auto-purchase skill
- Web Interface for easier configuration
- Select running style position
- Detailed config
- Auto pick event choice
- Automatically picks event choice base on desire skill (skill in auto buy list), and stats.

## Getting Started

### Requirements

- [Python 3.10+](https://www.python.org/downloads/)

### Setup

#### Clone repository

```
git clone https://github.com/EmptyBox36/umamusume-auto-train.git
cd umamusume-auto-train
```

#### Install dependencies

```
pip install -r requirements.txt
```

### BEFORE YOU START

Make sure these conditions are met:

- Screen resolution must be 1920x1080
- The game should be in fullscreen
- Your Uma must have already won the trophy for each race (the bot will skips the race)
- Turn off all confirmation pop-ups in game settings
- The game must be in the career lobby screen (the one with the Tazuna hint icon)

### Start

Run:

```
python main.py
```

Start:
press `f1` to start/stop the bot.

### Configuration

Open your browser and go to: `http://127.0.0.1:8000/` to easily edit the bot's configuration.

### Training Logic



### Known Issue

- Some Uma that has special event/target goals (like Restricted Train Goldship or ~~2 G1 Race Oguri Cap~~) may not working. For Oguri Cap G1 race event goal, you need to set the races in the race schedule that match the dates of her G1 goal events.
- OCR might misread failure chance (e.g., reads 33% as 3%) and proceeds with training anyway.
- If you bring a friend support card (like Tazuna/Aoi Kiryuin) and do recreation, the bot always date with the friend support card.

### Contribute

If you run into any issues or something doesn’t work as expected, feel free to open an issue.
Contributions are very welcome!
