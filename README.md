# d&d beyond scraper

scrapes full character data from d&d beyond by character id and returns clean, structured json.

questions? discord: eric.cpp  
i created this due to the lack of resources — if you improve or change anything feel free to reach out, i’ll gladly merge.

---

## features

- fetches and parses live d&d beyond characters
- returns **all stats, saving throws, skills, initiative, hp, ac, attacks, spells, inventory, features**
- pulls bonuses and proficiencies from all sources (class, race, feats, items, backgrounds)
- handles expertise and skill bonuses correctly
- avoids double-counting constitution in hp
- strips html safely and normalizes text output
- works with multiclass and multi-source spells
- outputs clean json suitable for bots, apps, or exports

---

## installation

```bash
git clone https://github.com/yourusername/dndbeyond-scraper.git
cd dndbeyond-scraper
pip install requests beautifulsoup4
```

```py
from dnd_scraper import ddb_character  # adjust import if file named differently

char = ddb_character("142137194")  # replace with your d&d beyond character id
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
  "current_hp": 18,
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
    "dexterity": 5,
    "constitution": 4,
    "intelligence": 7,
    "wisdom": 0,
    "charisma": -1
  },
  "skills": {
    "arcana": 7,
    "history": 5,
    "investigation": 4,
    "sleight-of-hand": 5
  },
  "attacks": [
    {
      "name": "quarterstaff",
      "range": 5,
      "hit_bonus": 1,
      "damage": "1d6-1",
      "damage_type": "bludgeoning",
      "notes": "simple, versatile, topple"
    }
  ],
  "spells": [
    {
      "name": "magic missile",
      "level": 1,
      "school": "evocation",
      "range": 120,
      "time": 1,
      "damage": "1d4+1",
      "save_dc": 13,
      "attack_bonus": 5,
      "description": "you create three glowing darts of magical force...",
      "components": "v/s",
      "source_class": "wizard"
    }
  ],
  "inventory": [
    {
      "name": "potion of healing",
      "type": "potion",
      "quantity": 1,
      "equipped": false,
      "damage": null,
      "properties": [],
      "description": "you regain 2d4+2 hit points when you drink this potion..."
    }
  ],
  "features": [
    {
      "name": "fey ancestry",
      "description": "you have advantage on saving throws against being charmed, and magic can’t put you to sleep."
    }
  ]
}
```


