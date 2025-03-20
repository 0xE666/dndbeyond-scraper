import requests
import unicodedata
import time
import socket
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

ABILITY_NAMES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]

def strip_html(raw_html: str) -> str:
    return BeautifulSoup(raw_html or "", "html.parser").get_text(separator=" ").strip()

def clean(text):
    if not text:
        return ""
    try:
        bytes_decoded = bytes(text, "utf-8").decode("unicode_escape")
        normalized = unicodedata.normalize("NFKC", strip_html(bytes_decoded))
        return normalized.replace("\n", " ").replace("\r", " ").strip()
    except Exception:
        return strip_html(text).replace("\n", " ").replace("\r", " ").strip()

class dnd_character:
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.data = self._fetch_character_data()

    def _fetch_character_data(self) -> dict:
        url = f"https://character-service.dndbeyond.com/character/v5/character/{self.character_id}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://www.dndbeyond.com/characters/{self.character_id}"
        }

        for attempt in range(3):
            try:
                res = requests.get(url, headers=headers, timeout=10)
                res.raise_for_status()
                return res.json()["data"]
            except (RequestException, socket.gaierror) as e:
                time.sleep(1.5)
                if attempt == 2:
                    return {
                        "error": "Failed to fetch character data. Please check your connection or try again later.",
                        "character_id": self.character_id,
                        "details": str(e)
                    }

        return {"error": "Unknown error occurred while fetching character data."}

    def _parse_initiative(self):
        stats = self._parse_stats()
        dex_mod = (stats.get("dexterity", 10) - 10) // 2
        bonus = 0

        for mod in self.data.get("modifiers", {}).get("class", []):
            if mod["type"] == "bonus" and mod["subType"] == "initiative":
                bonus += mod.get("value", 0)

        for mod in self.data.get("modifiers", {}).get("race", []):
            if mod["type"] == "bonus" and mod["subType"] == "initiative":
                bonus += mod.get("value", 0)

        return dex_mod + bonus

    def parse(self):
        if "error" in self.data:
            return self.data

        return {
            "name": self.data["name"],
            "level": sum(cls["level"] for cls in self.data.get("classes", [])),
            "race": self.data["race"]["fullName"],
            "class": [cls["definition"]["name"] for cls in self.data.get("classes", [])],
            "hp": self.data.get("baseHitPoints", 0),
            "ac": self.data.get("armorClass", 10),
            "initiative": self._parse_initiative(),
            "proficiency_bonus": self.data.get("proficiencyBonus", 2),
            "stats": self._parse_stats(),
            "saving_throws": self._parse_saving_throws(),
            "skills": self._parse_skills(),
            "attacks": self._parse_attacks(),
            "spells": self._parse_spells(),
            "inventory": self._parse_inventory(),
            "features": self._parse_features()
        }

    def _parse_stats(self):
        raw_stats = self.data.get("stats", [])
        return {ABILITY_NAMES[i]: stat["value"] for i, stat in enumerate(raw_stats)}

    def _parse_saving_throws(self):
        saves = {}
        profs = {
            mod["subType"].replace("-saving-throws", "")
            for mod in self.data.get("modifiers", {}).get("class", [])
            if mod["type"] == "proficiency" and "saving-throws" in mod["subType"]
        }
        stats = self._parse_stats()
        prof_bonus = self.data.get("proficiencyBonus", 2)
        for ability in ABILITY_NAMES:
            base = (stats.get(ability, 10) - 10) // 2
            saves[ability] = base + (prof_bonus if ability in profs else 0)
        return saves

    def _parse_skills(self):
        stats = self._parse_stats()
        prof_bonus = self.data.get("proficiencyBonus", 2)
        skills = {}
        for mod in self.data.get("modifiers", {}).get("class", []):
            if mod.get("type") in ("proficiency", "expertise") and mod.get("subType") in [
                "acrobatics", "animal-handling", "arcana", "athletics", "deception",
                "history", "insight", "intimidation", "investigation", "medicine",
                "nature", "perception", "performance", "persuasion", "religion",
                "sleight-of-hand", "stealth", "survival"
            ]:
                skill = mod["subType"]
                stat = {
                    "acrobatics": "dexterity", "animal-handling": "wisdom", "arcana": "intelligence",
                    "athletics": "strength", "deception": "charisma", "history": "intelligence",
                    "insight": "wisdom", "intimidation": "charisma", "investigation": "intelligence",
                    "medicine": "wisdom", "nature": "intelligence", "perception": "wisdom",
                    "performance": "charisma", "persuasion": "charisma", "religion": "intelligence",
                    "sleight-of-hand": "dexterity", "stealth": "dexterity", "survival": "wisdom"
                }[skill]
                base = (stats.get(stat, 10) - 10) // 2
                bonus = prof_bonus * (2 if mod["type"] == "expertise" else 1)
                skills[skill] = base + bonus
        return skills

    def _parse_attacks(self):
        attacks = []

        for item in self.data.get("inventory", []):
            if item.get("displayAsAttack") or item.get("isAttuned") or item.get("equipped"):
                defn = item.get("definition", {})
                if not defn:
                    continue
                damage_block = defn.get("damage") or {}
                attacks.append({
                    "name": defn.get("name"),
                    "range": defn.get("range", 5),
                    "hit_bonus": defn.get("attackBonus", 0),
                    "damage": damage_block.get("diceString"),
                    "damage_type": damage_block.get("damageType", {}).get("name"),
                    "notes": clean(defn.get("description", ""))
                })

        for atk in self.data.get("actions", {}).get("attack", []):
            attacks.append({
                "name": atk.get("name"),
                "range": atk.get("range"),
                "hit_bonus": atk.get("toHitBonus"),
                "damage": (atk.get("damage") or {}).get("diceString"),
                "notes": clean(atk.get("notes", ""))
            })

        return attacks

    def _parse_spells(self):
        spells = []
        spell_sources = self.data.get("classSpells", [])
        prof = self.data.get("proficiencyBonus", 2)
        stats = {s["id"]: s["value"] for s in self.data.get("stats", [])}
        spell_mod_id = self.data.get("spellCastingAbilityId", 4)
        mod = (stats.get(spell_mod_id, 10) - 10) // 2
        atk_bonus = mod + prof

        for source in spell_sources:
            for spell in source.get("spells", []):
                defn = spell.get("definition", {})
                if not defn:
                    continue
                spells.append({
                    "name": defn.get("name"),
                    "level": defn.get("level", 0),
                    "school": defn.get("school"),
                    "range": defn.get("range", {}).get("rangeValue"),
                    "time": defn.get("activation", {}).get("activationTime"),
                    "damage": next(
                        (m.get("dice", {}).get("diceString")
                         for m in defn.get("atHigherLevels", {}).get("higherLevelDefinitions", [])
                         if m.get("typeId") == 15),
                        None
                    ),
                    "save_dc": defn.get("saveDcAbilityId", spell_mod_id),
                    "attack_bonus": atk_bonus if defn.get("requiresAttackRoll") else None,
                    "description": clean(defn.get("description", "")),
                    "components": defn.get("componentsDescription", "")
                })
        return spells

    def _parse_inventory(self):
        items = []
        for i in self.data.get("inventory", []):
            definition = i.get("definition", {})
            damage_block = definition.get("damage", {}) or {}
            items.append({
                "name": definition.get("name", "Unknown"),
                "type": definition.get("type") or definition.get("filterType", "Misc"),
                "quantity": i.get("quantity", 1),
                "equipped": i.get("equipped", False),
                "damage": damage_block.get("diceString"),
                "properties": [p["name"] for p in (definition.get("properties") or []) if p],
                "description": clean(definition.get("description", ""))
            })
        return items

    def _parse_features(self):
        feats = []
        for section in ["racialTraits", "feats"]:
            for f in self.data.get("race", {}).get(section, []):
                defn = f.get("definition", {})
                feats.append({
                    "name": defn.get("name"),
                    "description": clean(defn.get("description", ""))
                })
        return feats
