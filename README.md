# DND Beyond Scraper


this scrapes character data from D&D Beyond by character id and returns clean, structured json for usage.

questions? discord: eric.cpp  
i created this due to the lack of resources, if you want to improve or happen to make changes feel free to reach out i'll gladly merge

---

## Features

- fetches and parses live D&D Beyond characters
- returns all stats, saves, attacks, spells, inventory, features

---

## Installation

```bash
git clone https://github.com/yourusername/dndbeyond-scraper.git
cd dndbeyond-scraper
pip install requests beautifulsoup4
```

```py
from dnd_scraper import dnd_character

char = dnd_character("142137194")  # replace with your d&d beyond character id
data = char.parse()

print(data)
```

```json
{
  "name": "Xesht",
  "level": 3,
  "race": "Half-Elf",
  "class": ["Wizard"],
  "hp": 20,
  "ac": 13,
  "initiative": 3,
  "proficiency_bonus": 2,
  "stats": {
    "strength": 8,
    "dexterity": 16,
    "constitution": 14,
    "intelligence": 19,
    "wisdom": 10,
    "charisma": 8
  },
  "saving_throws": {
    "strength": -1,
    "dexterity": 3,
    "constitution": 2,
    "intelligence": 5,
    "wisdom": 0,
    "charisma": -1
  },
  "skills": {
    "arcana": 8,
    "history": 6,
    "investigation": 4,
    "sleight-of-hand": 5
  },
  "attacks": [
    {
      "name": "Quarterstaff",
      "range": 5,
      "hit_bonus": 1,
      "damage": "1d6-1",
      "damage_type": "Bludgeoning",
      "notes": "Simple, Versatile, Topple"
    },
    {
      "name": "Shocking Grasp",
      "range": "Touch",
      "hit_bonus": 6,
      "damage": "1d8",
      "notes": "V/S"
    }
  ],
  "spells": [
    {
      "name": "Magic Missile",
      "level": 1,
      "school": "Evocation",
      "range": 120,
      "time": 1,
      "damage": "1d4+1",
      "save_dc": 4,
      "attack_bonus": 5,
      "description": "You create three glowing darts of magical force...",
      "components": "V/S"
    }
  ],
  "inventory": [
    {
      "name": "Potion of Healing",
      "type": "Potion",
      "quantity": 1,
      "equipped": false,
      "damage": null,
      "properties": [],
      "description": "You regain 2d4+2 hit points when you drink this potion..."
    }
  ],
  "features": [
    {
      "name": "Fey Ancestry",
      "description": "You have advantage on saving throws against being charmed, and magic can’t put you to sleep."
    }
  ]
}
```

