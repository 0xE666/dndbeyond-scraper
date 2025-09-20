import requests, time, random, socket, unicodedata
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

ABIL_ID_TO_NAME = {1:"strength",2:"dexterity",3:"constitution",4:"intelligence",5:"wisdom",6:"charisma"}
NAME_TO_ABIL_ID = {v:k for k,v in ABIL_ID_TO_NAME.items()}
SKILL_TO_ABILITY = {
    "acrobatics":"dexterity","animal-handling":"wisdom","arcana":"intelligence","athletics":"strength",
    "deception":"charisma","history":"intelligence","insight":"wisdom","intimidation":"charisma",
    "investigation":"intelligence","medicine":"wisdom","nature":"intelligence","perception":"wisdom",
    "performance":"charisma","persuasion":"charisma","religion":"intelligence","sleight-of-hand":"dexterity",
    "stealth":"dexterity","survival":"wisdom"
}
ALL_SOURCES = ("class","race","feat","item","background")

def _strip_html(s):
    return BeautifulSoup(s or "", "html.parser").get_text(separator=" ").strip()

def _clean(s):
    if not s: return ""
    try:
        dec = bytes(s, "utf-8").decode("unicode_escape")
        txt = unicodedata.normalize("NFKC", _strip_html(dec))
    except Exception:
        txt = _strip_html(s)
    return " ".join(txt.replace("\r"," ").split())

class dnd_character:
    def __init__(self, character_id: str, timeout=12):
        self.character_id = character_id
        self.timeout = timeout
        self.data = self._fetch()

    def _fetch(self):
        url = f"https://character-service.dndbeyond.com/character/v5/character/{self.character_id}"
        headers = {"User-Agent":"ddb-scraper/compact-1","Referer":f"https://www.dndbeyond.com/characters/{self.character_id}"}
        for attempt in range(1,4):
            try:
                r = requests.get(url, headers=headers, timeout=self.timeout)
                r.raise_for_status()
                j = r.json()
                return j["data"] if isinstance(j,dict) and "data" in j else j
            except (RequestException, socket.gaierror) as e:
                if attempt==3:
                    return {"error":"failed to fetch character data","character_id":self.character_id,"details":str(e)}
                time.sleep(0.6 + 0.6*(attempt-1) + random.uniform(0,0.2))
        return {"error":"unknown fetch error","character_id":self.character_id}

    # -------- helpers
    def _mods(self):
        m = self.data.get("modifiers",{}) or {}
        out = []
        for src in ALL_SOURCES:
            lst = m.get(src,[]) or []
            if isinstance(lst,list): out.extend(lst)
        return out

    def _prof_bonus(self):
        # trust ddb if present, else derive from level
        pb = self.data.get("proficiencyBonus")
        if isinstance(pb,int): return pb
        lvl = sum(c.get("level",0) for c in self.data.get("classes",[]))
        return 2 + max(0,(lvl-1)//4)

    def _base_stats(self):
        stats = {}
        for s in self.data.get("stats",[]) or []:
            sid, val = s.get("id"), s.get("value",10)
            if sid in ABIL_ID_TO_NAME: stats[ABIL_ID_TO_NAME[sid]] = int(val)
        # fill any missing with 10
        for n in ABIL_ID_TO_NAME.values(): stats.setdefault(n,10)
        return stats

    def _final_stats(self):
        stats = self._base_stats()
        for mod in self._mods():
            if mod.get("type")=="bonus":
                st = (mod.get("subType") or "")
                if st.endswith("-score"):
                    abil = st.replace("-score","")
                    if abil in stats:
                        v = mod.get("value") or 0
                        try: v = int(v)
                        except: 
                            try: v = float(v)
                            except: v = 0
                        stats[abil] += int(v)
        return stats

    def _abil_mod(self, score): return (score-10)//2

    # -------- public api
    def parse(self):
        if isinstance(self.data,dict) and "error" in self.data: return self.data

        name = self.data.get("name","unknown")
        race_name = (self.data.get("race") or {}).get("fullName") or (self.data.get("race") or {}).get("name","unknown")
        level = sum(c.get("level",0) for c in self.data.get("classes",[]))
        classes = [ (c.get("definition") or {}).get("name","unknown") for c in self.data.get("classes",[]) ]

        # hp: never double-count con; never coerce 0 → max
        base_hp = int(self.data.get("baseHitPoints") or 0)
        bonus_hp = int(self.data.get("bonusHitPoints") or 0)
        override_hp = self.data.get("overrideHitPoints")
        max_hp = int(override_hp) if override_hp is not None else base_hp + bonus_hp
        current_hp = self.data.get("currentHitPoints")
        if current_hp is None:
            current_hp = max_hp - int(self.data.get("removedHitPoints") or 0)

        stats = self._final_stats()
        pb = self._prof_bonus()

        initiative = self._abil_mod(stats["dexterity"])
        for m in self._mods():
            if m.get("type")=="bonus" and m.get("subType")=="initiative":
                try: initiative += int(m.get("value") or 0)
                except: pass

        saving_throws = {}
        prof_saves = { (m.get("subType") or "").replace("-saving-throws","")
                       for m in self._mods() if m.get("type")=="proficiency" and "saving-throws" in (m.get("subType") or "") }
        save_bonuses = {}  # explicit bonuses to saves
        for m in self._mods():
            if m.get("type")=="bonus" and (m.get("subType") or "").endswith("-saving-throws"):
                abil = m["subType"].replace("-saving-throws",""); 
                try: save_bonuses[abil]=save_bonuses.get(abil,0)+int(m.get("value") or 0)
                except: pass
        for abil in ABIL_ID_TO_NAME.values():
            saving_throws[abil] = self._abil_mod(stats[abil]) + (pb if abil in prof_saves else 0) + save_bonuses.get(abil,0)

        skills = {}
        prof_skills = { m.get("subType") for m in self._mods() if m.get("type")=="proficiency" and m.get("subType") in SKILL_TO_ABILITY }
        expert_skills = { m.get("subType") for m in self._mods() if m.get("type")=="expertise" and m.get("subType") in SKILL_TO_ABILITY }
        skill_bonuses = {}
        for m in self._mods():
            if m.get("type")=="bonus" and m.get("subType") in SKILL_TO_ABILITY:
                try: skill_bonuses[m["subType"]] = skill_bonuses.get(m["subType"],0)+int(m.get("value") or 0)
                except: pass
        for sk, abil in SKILL_TO_ABILITY.items():
            base = self._abil_mod(stats[abil])
            bonus = (2*pb if sk in expert_skills else (pb if sk in prof_skills else 0)) + skill_bonuses.get(sk,0)
            skills[sk] = base + bonus

        attacks = []
        for it in self.data.get("inventory",[]) or []:
            d = it.get("definition") or {}
            if not d: continue
            if it.get("displayAsAttack") or it.get("equipped") or it.get("isAttuned"):
                dmg = (d.get("damage") or {}).get("diceString")
                attacks.append({
                    "name": d.get("name"), "range": d.get("range",5),
                    "hit_bonus": d.get("attackBonus",0), "damage": dmg,
                    "damage_type": ((d.get("damage") or {}).get("damageType") or {}).get("name"),
                    "notes": _clean(d.get("description",""))
                })
        for a in (self.data.get("actions") or {}).get("attack",[]) or []:
            dmg = ((a.get("damage") or {}).get("diceString"))
            attacks.append({"name":a.get("name"),"range":a.get("range"),
                            "hit_bonus":a.get("toHitBonus"),"damage":dmg,"notes":_clean(a.get("notes",""))})

        # spells grouped by class (from classSpells)
        spells = []
        class_by_id = { c.get("id"): c for c in self.data.get("classes",[]) }
        for entry in self.data.get("classSpells",[]) or []:
            cid = entry.get("characterClassId")
            cls = class_by_id.get(cid) or {}
            spell_abil_id = ((cls.get("definition") or {}).get("spellcastingAbilityId")) or self.data.get("spellCastingAbilityId") or 4
            spell_abil_name = ABIL_ID_TO_NAME.get(spell_abil_id,"intelligence")
            mod = self._abil_mod(stats.get(spell_abil_name,10))
            dc = 8 + pb + mod
            atk_bonus = pb + mod
            for s in entry.get("spells",[]) or []:
                d = s.get("definition") or {}
                if not d: continue
                save_abil_id = d.get("saveDcAbilityId") or spell_abil_id
                save_dc = 8 + pb + self._abil_mod(stats.get(ABIL_ID_TO_NAME.get(save_abil_id,"intelligence"),10))
                rng = (d.get("range") or {}).get("rangeValue")
                time_val = (d.get("activation") or {}).get("activationTime")
                higher = next((m.get("dice",{}).get("diceString") for m in (d.get("atHigherLevels") or {}).get("higherLevelDefinitions",[]) if m.get("typeId")==15), None)
                comp = d.get("componentsDescription","")
                spells.append({
                    "name": d.get("name"), "level": d.get("level",0), "school": d.get("school"),
                    "range": rng, "time": time_val, "damage": higher,
                    "save_dc": save_dc, "attack_bonus": (atk_bonus if d.get("requiresAttackRoll") else None),
                    "description": _clean(d.get("description","")), "components": comp,
                    "source_class": (cls.get("definition") or {}).get("name","unknown")
                })

        inventory = []
        for it in self.data.get("inventory",[]) or []:
            d = it.get("definition") or {}
            dmg = (d.get("damage") or {}).get("diceString")
            props = [p.get("name") for p in (d.get("properties") or []) if isinstance(p,dict)]
            inventory.append({
                "name": d.get("name","unknown"),
                "type": d.get("type") or d.get("filterType","Misc"),
                "quantity": it.get("quantity",1), "equipped": it.get("equipped",False),
                "damage": dmg, "properties": props, "description": _clean(d.get("description",""))
            })

        features = []
        for f in (self.data.get("race") or {}).get("racialTraits",[]) or []:
            d = f.get("definition") or {}
            features.append({"name":d.get("name"),"description":_clean(d.get("description",""))})
        for f in self.data.get("feats",[]) or []:
            d = f.get("definition") or {}
            features.append({"name":d.get("name"),"description":_clean(d.get("description",""))})

        return {
            "name": name,
            "level": level,
            "race": race_name,
            "class": classes,
            "hp": max_hp,
            "current_hp": current_hp,
            "ac": self.data.get("armorClass",10),
            "initiative": initiative,
            "proficiency_bonus": pb,
            "stats": stats,
            "saving_throws": saving_throws,
            "skills": skills,
            "attacks": attacks,
            "spells": spells,
            "inventory": inventory,
            "features": features
        }


