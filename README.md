**Now the code is very messy, i will clean them when i have time just make it run for now**

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
- Handle debuffs, if debuffed and mood is below threshold bot will pick recreation to try to get temple date
- Rest
- Selectable races in the race schedule
- Stat target feature, if a stat already hits the target, skip training that one
- Auto-purchase skill
- Web Interface for easier configuration
- Select running style position and select specific position for specific race
- Detailed config
- Auto pick event choice choice base on energy, desire skill, and stats
- Can custom pick event choice
- URA and Unity cup support (i still didn't have assets for some team name, it only work with team sunny runner, blue bloom and carrots for now)
- Can manual update the events database (/scraper/main.py or /scraper/start.bat)
- Smart recreation, if mood is below prefered mood by 1 level it will try to recreation with friend first but if mood is too low it will use the normal recration to try to get karaoke or claw machine. And it can also detect when friend recreation is available
- Can view the log from webui and other device if change host to `0.0.0.0`. But other device can **view-only** only local device can change the setting.
- Can deal with training restriction like Gold Ship event
- Can deal with lose the debut race situation
  
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

- The training logic between URA and Unity cup are different, feel free to try to edit it.
- There are many config that wasn't show on webui or config.json (like Select prefer graded race for auto race (In /core/logic.py), weight for blue flame and white flame, weight on each year etc. ). You can edit it to your preferences.

### Known Issue

- Some Uma that has special event/target goals (like ~~Restricted Train Goldship~~ or ~~2 G1 Race Oguri Cap~~) may not working. For Oguri Cap G1 race event goal, you need to set the races in the race schedule that match the dates of her G1 goal events. It can deal with training resticted now but sometimes it not selected a good choice.
- OCR might misread failure chance (e.g., reads 33% as 3%) and proceeds with training anyway. Now i should be better i add on more step to failure check.
- If you bring multiple friend support cards (like Tazuna/Aoi Kiryuin) and do recreation, the bot always date with the friend support card in order.
- The bot is very slow because it have to read and process many thing. so, i will improve it later.

### Contribute

If you run into any issues or something doesn’t work as expected, feel free to open an issue.
Contributions are very welcome!
