# ⚔️ Bot For Sign-Up 

A clean Discord bot designed to organize events with role/build sign-ups.
Users can create events using a slash command, and participants can claim specific roles through an interactive and persistent interface.

## ✨ Features
- Slash command `/create_event` for quick event creation
- Persistent interactive view untill the end of the event (even after restart)
- Role selection via dropdown menu
- Live updating composition embed
- Sign-Up / Sign-Off functionality
- Creator-only/Admin **Ping** button (mentions all participants)
- Creator-only/Admin **End Event** button
- **Multiple** events simultaneously
- Uses **UTC** timezone for timestamps

## 🚀 Installation
### 1. Clone the repository
```bash
git clone https://github.com/volante-seriale/bot_sign_up
```
### 2. Install dependencies
```bash
pip install -r requirements.txt
```
### 3. Set up environment variables
```bash
BOT_TOKEN=your_bot_token_here
```
### 4. Run the bot
```bash
python bot.py
```
## Requirements (requirements.txt)
```bash
discord.py>=2.4.0
python-dotenv>=1.0.0
tzdata>=2025.1
```

## 📋 How to Use
### Create an Event
```bash
    /create_event name: "Evening Raid" 
             date: "10/05/2026" 
             time_utc: "19:00" 
             build: "Tank;Healer;DPS1;DPS2;DPS3;etc"
```
### Available Buttons
- **Sing-Up** (Green) → Chose your role from the dropdown
- **Sing-Off** (Red) → Remove your self from the list
- **Sing-UP** (Blurple) → Ping all signed-up members (Only for event creator and admin)
- **Sing-UP** (Gray) → Close the event (Only for event creator and admin)

## 📁 Project Structure
```bash
eventbot/
├── bot.py # Main file (rename as you prefer)
├── .env   # ← Add this to .gitignore
├── requirements.txt
├── README.md
└── data/
    └── events.json
```
