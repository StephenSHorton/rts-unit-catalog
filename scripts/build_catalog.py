#!/usr/bin/env python3
"""Ingest TA + Supreme Commander unit data into a local visual catalog."""

from __future__ import annotations

import csv
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_TA = ROOT / "vendor" / "reference-ta"
VENDOR_FA = ROOT / "vendor" / "fa"
VENDOR_BAR = ROOT / "vendor" / "bar-units-db"
SC_JSON = ROOT / "data" / "sc-index.json"
BAR_JSON = VENDOR_BAR / "src" / "_data" / "units.json"
BAR_LOCALE = VENDOR_BAR / "src" / "_locales" / "en.yml"
CATALOG = ROOT / "catalog"
IMG_TA = CATALOG / "img" / "ta"
IMG_SC = CATALOG / "img" / "sc"
IMG_BAR = CATALOG / "img" / "bar"
DATA_DIR = ROOT / "data"

GAMES = [
    {"id": "ta", "year": 1997, "short": "TA", "name": "Total Annihilation"},
    {"id": "sc", "year": 2007, "short": "SC", "name": "Supreme Commander"},
    {"id": "bar", "year": 2023, "short": "BAR", "name": "Beyond All Reason"},
]

LINEAGE = [
    ("commander", "Commander / ACU"),
    ("t1_engineer", "T1 Engineer"),
    ("t2_engineer", "T2 / Adv. Engineer"),
    ("t3_engineer", "T3 Engineer"),
    ("t1_land_scout", "Land Scout"),
    ("t1_light_bot", "T1 Light Assault"),
    ("t1_tank", "T1 Tank"),
    ("t1_arty", "T1 Mobile Artillery"),
    ("t1_aa", "T1 Mobile AA"),
    ("t1_air_scout", "Air Scout"),
    ("t1_interceptor", "T1 Fighter / Interceptor"),
    ("t1_bomber", "T1 Bomber"),
    ("t1_transport", "T1 Air Transport"),
    ("t1_frigate", "T1 Frigate / Scout Ship"),
    ("t1_sub", "T1 Submarine"),
    ("t1_factory_land", "T1 Land Factory"),
    ("t1_factory_air", "T1 Air Factory"),
    ("t1_factory_naval", "T1 Naval Factory"),
    ("t1_mex", "Metal / Mass Extractor"),
    ("t1_energy", "T1 Energy"),
    ("t1_fab", "T1 Metal Maker / Mass Fab"),
    ("t1_pd", "T1 Point Defense"),
    ("t1_aa_turret", "T1 AA Turret"),
    ("t1_radar", "Radar / Sonar"),
    ("t2_tank", "T2 Heavy Tank / Assault"),
    ("t2_mml", "T2 Mobile Missile"),
    ("t2_flak", "T2 Flak"),
    ("t2_amphib", "T2 Amphibious"),
    ("t2_gunship", "T2 Gunship"),
    ("t2_fighter", "T2 Fighter"),
    ("t2_bomber", "T2 Bomber"),
    ("t2_destroyer", "T2 Destroyer"),
    ("t2_cruiser", "T2 Cruiser"),
    ("t2_pd", "T2 Point Defense"),
    ("t2_arty", "T2 Static Artillery"),
    ("t2_energy", "T2 Energy / Fusion"),
    ("t2_mex", "T2 Mex / Moho"),
    ("t2_factory_land", "T2 Land Factory"),
    ("t2_factory_air", "T2 Air Factory"),
    ("t2_factory_naval", "T2 Naval Factory"),
    ("t3_assault", "T3 Assault Bot"),
    ("t3_arty", "T3 Mobile Artillery"),
    ("t3_asf", "T3 Air Superiority"),
    ("t3_strat_bomber", "T3 Strategic Bomber"),
    ("t3_battleship", "T3 Battleship"),
    ("t3_energy", "T3 Power Generator"),
    ("t3_arty_static", "T3 Artillery / Big Bertha"),
    ("nuke", "Nuclear Missile"),
    ("antinuke", "Anti-Nuke"),
    ("experimental", "Experimental / Krogoth"),
    ("shield", "Shield"),
    ("tml", "Tactical Missile"),
    ("wall", "Wall / Dragon's Teeth"),
    ("other", "Other"),
]

# Famous TA codes → lineage role (overrides heuristics).
TA_ROLE = {
    "ARMCOM": "commander", "CORCOM": "commander",
    "ARMDECOM": "commander", "CORDECOM": "commander",
    "ARMCK": "t1_engineer", "ARMCV": "t1_engineer", "ARMCA": "t1_engineer",
    "ARMCS": "t1_engineer", "ARMCH": "t1_engineer", "ARMCSA": "t1_engineer",
    "CORCK": "t1_engineer", "CORCV": "t1_engineer", "CORCA": "t1_engineer",
    "CORCS": "t1_engineer", "CORCH": "t1_engineer", "CORCSA": "t1_engineer",
    "ARMACK": "t2_engineer", "ARMACV": "t2_engineer", "ARMACA": "t2_engineer",
    "ARMACSUB": "t2_engineer", "ARMFARK": "t2_engineer",
    "CORACK": "t2_engineer", "CORACV": "t2_engineer", "CORACA": "t2_engineer",
    "CORACSUB": "t2_engineer",
    "ARMFAV": "t1_land_scout", "CORFAV": "t1_land_scout",
    "ARMFLEA": "t1_land_scout",
    "ARMPW": "t1_light_bot", "CORAK": "t1_light_bot",
    "ARMFLASH": "t1_tank", "CORGATOR": "t1_tank",
    "ARMSTUMP": "t1_tank", "CORRAID": "t1_tank",
    "ARMHAM": "t1_arty", "CORTHUD": "t1_arty",
    "ARMROCK": "t1_arty", "CORSTORM": "t1_arty",
    "ARMJETH": "t1_aa", "CORCRASH": "t1_aa",
    "ARMSAM": "t1_aa", "CORMIST": "t1_aa",
    "ARMPEEP": "t1_air_scout", "CORFINK": "t1_air_scout",
    "ARMFIG": "t1_interceptor", "CORVENG": "t1_interceptor",
    "ARMTHUND": "t1_bomber", "CORSHAD": "t1_bomber",
    "ARMATLAS": "t1_transport", "CORVALK": "t1_transport",
    "ARMPT": "t1_frigate", "CORPT": "t1_frigate",
    "ARMSUB": "t1_sub", "CORSUB": "t1_sub",
    "ARMLAB": "t1_factory_land", "ARMVP": "t1_factory_land",
    "CORLAB": "t1_factory_land", "CORVP": "t1_factory_land",
    "ARMAP": "t1_factory_air", "CORAP": "t1_factory_air",
    "ARMSY": "t1_factory_naval", "CORSY": "t1_factory_naval",
    "ARMMEX": "t1_mex", "CORMEX": "t1_mex",
    "ARMUWMEX": "t1_mex", "CORUWMEX": "t1_mex",
    "ARMSOLAR": "t1_energy", "ARMWIN": "t1_energy", "ARMTIDE": "t1_energy",
    "CORSOLAR": "t1_energy", "CORWIN": "t1_energy", "CORTIDE": "t1_energy",
    "ARMMAKR": "t1_fab", "CORMAKR": "t1_fab",
    "ARMFMKR": "t1_fab", "CORFMKR": "t1_fab",
    "ARMLLT": "t1_pd", "CORLLT": "t1_pd",
    "ARMRL": "t1_aa_turret", "CORRL": "t1_aa_turret",
    "ARMFRT": "t1_aa_turret", "CORFRT": "t1_aa_turret",
    "ARMRAD": "t1_radar", "CORRAD": "t1_radar",
    "ARMSONAR": "t1_radar", "CORSONAR": "t1_radar",
    "ARMBULL": "t2_tank", "CORREAP": "t2_tank", "CORGOL": "t2_tank",
    "ARMFIDO": "t2_tank", "ARMZEUS": "t2_tank", "ARMWAR": "t2_tank",
    "CORCAN": "t2_tank", "CORSUMO": "t2_tank", "CORPYRO": "t2_tank",
    "ARMMERL": "t2_mml", "CORVROC": "t2_mml", "CORHRK": "t2_mml",
    "ARMFLAK": "t2_flak", "CORFLAK": "t2_flak",
    "ARMYORK": "t2_flak", "CORSENT": "t2_flak",
    "ARMCROC": "t2_amphib", "CORSEAL": "t2_amphib",
    "ARMAMPH": "t2_amphib", "CORAMPH": "t2_amphib",
    "ARMBRAWL": "t2_gunship", "CORAPE": "t2_gunship",
    "ARMHAWK": "t2_fighter", "CORVAMP": "t2_fighter",
    "ARMPNIX": "t2_bomber", "CORHURC": "t2_bomber",
    "ARMROY": "t2_destroyer", "CORROY": "t2_destroyer",
    "ARMCRUS": "t2_cruiser", "CORCRUS": "t2_cruiser",
    "ARMHLT": "t2_pd", "CORHLT": "t2_pd",
    "ARMFHLT": "t2_pd", "CORFHLT": "t2_pd",
    "ARMGUARD": "t2_arty", "CORPUN": "t2_arty",
    "ARMAMB": "t2_arty", "CORTOAST": "t2_arty",
    "ARMFUS": "t2_energy", "CORFUS": "t2_energy",
    "ARMCKFUS": "t2_energy", "CORCKFUS": "t2_energy",
    "ARMGEO": "t2_energy", "CORGEO": "t2_energy",
    "ARMUWFUS": "t2_energy", "CORUWFUS": "t2_energy",
    "ARMMOHO": "t2_mex", "CORMOHO": "t2_mex",
    "ARMMMKR": "t2_fab", "CORMMKR": "t2_fab",
    "ARMALAB": "t2_factory_land", "ARMAVP": "t2_factory_land",
    "CORALAB": "t2_factory_land", "CORAVP": "t2_factory_land",
    "ARMAAP": "t2_factory_air", "CORAAP": "t2_factory_air",
    "ARMASY": "t2_factory_naval", "CORASY": "t2_factory_naval",
    "ARMMAV": "t3_assault", "ARMSNIPE": "t3_assault",
    "ARMMART": "t3_arty", "CORMART": "t3_arty", "CORMORT": "t3_arty",
    "ARMBATS": "t3_battleship", "CORBATS": "t3_battleship",
    "ARMBRTHA": "t3_arty_static", "CORINT": "t3_arty_static",
    "ARMANNI": "t3_arty_static", "CORDOOM": "t3_arty_static",
    "ARMSILO": "nuke", "CORSILO": "nuke",
    "ARMAMD": "antinuke", "CORFMD": "antinuke",
    "ARMSCAB": "antinuke", "CORMABM": "antinuke",
    "CORKROG": "experimental", "CORGANT": "experimental",
    "ARMVULC": "experimental", "CORBUZZ": "experimental",
    "ARMDRAG": "wall", "CORDRAG": "wall",
    "ARMFDRAG": "wall", "CORFDRAG": "wall",
    "ARMFORT": "wall", "CORFORT": "wall",
}

TA_TECH2 = {
    "ARMACK", "ARMACV", "ARMACA", "ARMACSUB", "ARMFARK",
    "CORACK", "CORACV", "CORACA", "CORACSUB",
    "ARMALAB", "ARMAVP", "ARMAAP", "ARMASY", "ARMHP", "ARMPLAT",
    "CORALAB", "CORAVP", "CORAAP", "CORASY", "CORHP", "CORPLAT", "CORGANT",
    "ARMFUS", "ARMCKFUS", "ARMGEO", "ARMMOHO", "ARMMMKR", "ARMUWFUS",
    "CORFUS", "CORCKFUS", "CORGEO", "CORMOHO", "CORMMKR", "CORUWFUS",
    "ARMFIDO", "ARMZEUS", "ARMFAST", "ARMMAV", "ARMSNIPE", "ARMSPY",
    "ARMAMPH", "ARMASER", "ARMMARK", "ARMVADER",
    "CORCAN", "CORSUMO", "CORPYRO", "CORFAST", "CORHRK", "CORMORT",
    "CORAMPH", "CORNECRO", "CORROACH", "CORSPEC", "CORSPY", "CORVOYR",
    "ARMBULL", "ARMCROC", "ARMLATNK", "ARMMART", "ARMMERL", "ARMYORK",
    "ARMSCAB", "ARMSEER", "ARMSPID", "ARMANAC", "ARMAH", "ARMMH", "ARMTHOVR",
    "CORREAP", "CORGOL", "CORLEVLR", "CORSEAL", "CORMART", "CORVROC",
    "CORSENT", "CORMABM", "CORVRAD", "CORETER", "CORSNAP", "CORAH", "CORMH",
    "CORTHOVR",
    "ARMHAWK", "ARMPNIX", "ARMBRAWL", "ARMLANCE", "ARMAWAC",
    "CORVAMP", "CORHURC", "CORAPE", "CORTITAN", "CORAWAC",
    "ARMBATS", "ARMCRUS", "ARMCARRY", "ARMMSHIP", "ARMAAS", "ARMSUBK",
    "CORBATS", "CORCRUS", "CORCARRY", "CORMSHIP", "CORARCH", "CORSHARK",
    "CORSSUB",
    "ARMAMB", "ARMAMD", "ARMANNI", "ARMATL", "ARMBRTHA", "ARMFLAK",
    "ARMGUARD", "ARMHLT", "ARMFHLT", "ARMMANNI",
    "CORTOAST", "CORFMD", "CORDOOM", "CORATL", "CORINT", "CORFLAK",
    "CORPUN", "CORHLT", "CORFHLT", "CORVIPE", "CORPLAS",
    "ARMARAD", "ARMASON", "CORARAD", "CORASON",
    "ARMASP", "CORASP", "ARMTARG", "CORTARG",
    "ARMEMP", "CORTRON",
}

TA_TECH3 = {"CORKROG", "CORGANT", "ARMVULC", "CORBUZZ", "ARMBRTHA", "CORINT", "ARMANNI", "CORDOOM"}


def loc_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<LOC\s+[^>]+>", "", value).strip()
    return value


def parse_cost(raw: str) -> tuple[float | None, float | None]:
    raw = raw.replace(",", "").replace("—", "-").strip()
    if not raw or raw == "-":
        return None, None
    parts = [p.strip() for p in raw.split("/")]
    def num(s: str) -> float | None:
        s = s.strip()
        if not s or s in {"-", "—"}:
            return None
        s = re.sub(r";.*", "", s)
        try:
            return float(s)
        except ValueError:
            return None
    if len(parts) == 1:
        return num(parts[0]), None
    return num(parts[0]), num(parts[1])


def parse_hp(raw: str) -> int | None:
    raw = re.sub(r";.*", "", raw).replace(",", "").strip()
    try:
        return int(float(raw))
    except ValueError:
        return None


def ta_domain(ted: str, category: str) -> str:
    ted = (ted or "").upper()
    cat = (category or "").lower()
    if ted == "COMMANDER" or "commander" in cat:
        return "commander"
    if ted == "PLANT" or "production" in cat:
        return "structure"
    if ted in {"ENERGY", "METAL", "FORT"} or "resource" in cat or "defensive" in cat or "sensor" in cat:
        return "structure"
    if ted == "VTOL" or "aircraft" in cat:
        return "air"
    if ted in {"SHIP", "WATER"} or "ship" in cat or "submarine" in cat:
        return "navy"
    if ted in {"KBOT", "TANK", "CNSTR"} or "kbot" in cat or "vehicle" in cat or "construction" in cat:
        return "land"
    if "misc" in cat:
        return "structure"
    return "other"


def ta_role(code: str, ted: str, category: str, name: str) -> str:
    if code in TA_ROLE:
        return TA_ROLE[code]
    ted = (ted or "").upper()
    n = (name or "").lower()
    cat = (category or "").lower()
    if ted == "COMMANDER":
        return "commander"
    if "adv" in n or "advanced" in n:
        if ted == "CNSTR":
            return "t2_engineer"
        if "aircraft" in n or "air" in n:
            return "t2_factory_air"
        if "ship" in n:
            return "t2_factory_naval"
        if ted == "PLANT":
            return "t2_factory_land"
    if ted == "CNSTR":
        return "t1_engineer"
    if ted == "PLANT":
        if "air" in n:
            return "t1_factory_air"
        if "ship" in n:
            return "t1_factory_naval"
        return "t1_factory_land"
    if "dragon" in n or "fortification" in n or "wall" in n:
        return "wall"
    if "fusion" in n or "geo" in n:
        return "t2_energy"
    if ted == "ENERGY":
        return "t1_energy"
    if "moho" in n:
        return "t2_mex" if "maker" not in n else "t2_fab"
    if "maker" in n:
        return "t1_fab"
    if ted == "METAL":
        return "t1_mex"
    if "nuke" in n or "silencer" in n or "retaliator" in n:
        return "nuke"
    if "anti missile" in n or "protector" in n or "fortitude" in n:
        return "antinuke"
    if ted == "FORT" and ("laser" in n or "l.l.t" in n or "llt" in n):
        return "t1_pd"
    return "other"


def ta_tech(code: str, name: str) -> int:
    if code in TA_TECH3 or "krogoth" in name.lower():
        return 3
    if code in TA_TECH2 or name.lower().startswith("adv") or "advanced" in name.lower() or "moho" in name.lower() or "fusion" in name.lower():
        return 2
    if code in {"ARMCOM", "CORCOM", "ARMDECOM", "CORDECOM"}:
        return 0
    return 1


def parse_ta() -> list[dict]:
    md = (VENDOR_TA / "ta-units.md").read_text(encoding="utf-8")
    units: list[dict] = []
    faction = "arm"
    category = "Misc"
    heading_re = re.compile(r"^### (ARM|CORE) — (.+)$")
    row_re = re.compile(
        r"^\| (?:<img src=\"img/ta-units/([^\"]+)\".*?/>|—) \| `([^`]+)` \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|\s*$"
    )
    for line in md.splitlines():
        h = heading_re.match(line)
        if h:
            faction = "arm" if h.group(1) == "ARM" else "core"
            category = h.group(2).strip()
            continue
        m = row_re.match(line)
        if not m:
            continue
        portrait, code, name, desc, ted, cost, hp, weapons = m.groups()
        name = name.strip()
        desc = desc.strip()
        ted = ted.strip()
        metal, energy = parse_cost(cost)
        wlist = []
        wraw = weapons.strip()
        if wraw and wraw not in {"—", "-"}:
            wlist = [w.strip() for w in wraw.split(",") if w.strip() and w.strip() != "—"]
        img_name = (portrait or f"{code.lower()}.png").lower()
        src = IMG_TA / img_name
        image = f"img/ta/{img_name}" if src.exists() else None
        units.append({
            "id": f"ta-{code.lower()}",
            "game": "ta",
            "code": code,
            "name": name,
            "aka": None,
            "faction": faction,
            "domain": ta_domain(ted, category),
            "kind": category,
            "tech": ta_tech(code, name),
            "description": desc,
            "hp": parse_hp(hp),
            "cost_metal": metal,
            "cost_energy": energy,
            "build_time": None,
            "speed": None,
            "weapons": wlist,
            "role": ta_role(code, ted, category, name),
            "image": image,
            "ted": ted,
            "categories": [ted, category],
        })
    return units


def sc_tech(cats: set[str]) -> int:
    if "EXPERIMENTAL" in cats:
        return 4
    if "TECH3" in cats:
        return 3
    if "TECH2" in cats:
        return 2
    if "TECH1" in cats:
        return 1
    if "COMMAND" in cats:
        return 0
    return 1


def sc_domain(cats: set[str]) -> str:
    if "COMMAND" in cats:
        return "commander"
    if "STRUCTURE" in cats:
        return "structure"
    if "AIR" in cats:
        return "air"
    if "NAVAL" in cats or "SUBMERSIBLE" in cats:
        return "navy"
    if "LAND" in cats or "HOVER" in cats:
        return "land"
    return "other"


def sc_role(cats: set[str], desc: str, name: str) -> str:
    d = f"{desc} {name}".lower()
    tech = sc_tech(cats)
    t = {0: "t1", 1: "t1", 2: "t2", 3: "t3", 4: "t4"}[tech]

    if "COMMAND" in cats and "STRUCTURE" not in cats:
        return "commander"
    if "EXPERIMENTAL" in cats:
        return "experimental"
    if "ENGINEER" in cats and "STRUCTURE" not in cats:
        if tech >= 3:
            return "t3_engineer"
        if tech == 2:
            return "t2_engineer"
        return "t1_engineer"
    if "FACTORY" in cats:
        if "GATE" in cats:
            return "other"
        if "AIR" in cats:
            return f"{t}_factory_air" if t in {"t1", "t2"} else "t2_factory_air"
        if "NAVAL" in cats:
            return f"{t}_factory_naval" if t in {"t1", "t2"} else "t2_factory_naval"
        return f"{t}_factory_land" if t in {"t1", "t2"} else "t2_factory_land"
    if "MASSEXTRACTION" in cats:
        return "t2_mex" if tech >= 2 else "t1_mex"
    if "MASSFABRICATION" in cats:
        return "t1_fab"
    if "ENERGYPRODUCTION" in cats:
        if tech >= 3:
            return "t3_energy"
        if tech == 2:
            return "t2_energy"
        return "t1_energy"
    if "SHIELD" in cats and "STRUCTURE" in cats:
        return "shield"
    if "STRUCTURE" in cats and (
        "strategic missile defense" in d
        or ("ANTIMISSILE" in cats and "nuke" in d)
    ):
        return "antinuke"
    if "STRUCTURE" in cats and ("NUKE" in cats or "strategic missile launcher" in d):
        return "nuke"
    if "tactical missile" in d and "STRUCTURE" in cats:
        return "tml"
    if "WALL" in cats:
        return "wall"
    if "ARTILLERY" in cats and "STRUCTURE" in cats:
        return "t3_arty_static" if tech >= 3 else "t2_arty"
    if "DIRECTFIRESTRUCTURE" in cats or ("STRUCTURE" in cats and "DIRECTFIRE" in cats and "ANTIAIR" not in cats):
        return "t2_pd" if tech >= 2 else "t1_pd"
    if "STRUCTURE" in cats and "ANTIAIR" in cats:
        return "t2_flak" if tech >= 2 else "t1_aa_turret"
    if "RADAR" in cats or "SONAR" in cats or "OMNI" in cats or "INTELLIGENCE" in cats:
        if "STRUCTURE" in cats:
            return "t1_radar"
        if "SCOUT" in cats and "AIR" in cats:
            return "t1_air_scout"
        if "SCOUT" in cats:
            return "t1_land_scout"

    if "AIR" in cats:
        if "SCOUT" in cats or "INTELLIGENCE" in cats:
            return "t1_air_scout"
        if "TRANSPORTATION" in cats:
            return "t1_transport"
        if "BOMBER" in cats:
            if tech >= 3:
                return "t3_strat_bomber"
            return "t2_bomber" if tech == 2 else "t1_bomber"
        if "GROUNDATTACK" in cats or "gunship" in d:
            return "t2_gunship"
        if "ANTIAIR" in cats:
            if tech >= 3:
                return "t3_asf"
            return "t2_fighter" if tech == 2 else "t1_interceptor"
        return "other"

    if "NAVAL" in cats or ("SUBMERSIBLE" in cats and "STRUCTURE" not in cats):
        if "battleship" in d or "battlecruiser" in d:
            return "t3_battleship"
        if "carrier" in d:
            return "experimental" if tech >= 4 else "t3_battleship"
        if "cruiser" in d:
            return "t2_cruiser"
        if "destroyer" in d:
            return "t2_destroyer"
        if "frigate" in d or "attack boat" in d:
            return "t1_frigate"
        if "submarine" in d or "submersible" in d or ("SUBMERSIBLE" in cats and "destroyer" not in d):
            return "t1_sub"
        return "other"

    if "LAND" in cats or "HOVER" in cats:
        if "SCOUT" in cats:
            return "t1_land_scout"
        if "ANTIAIR" in cats:
            return "t2_flak" if tech >= 2 else "t1_aa"
        if "ARTILLERY" in cats or "mobile light artillery" in d or "mobile heavy artillery" in d:
            return "t3_arty" if tech >= 3 else "t1_arty"
        if "SILO" in cats or "missile launcher" in d:
            return "t2_mml"
        if "AMPHIBIOUS" in cats:
            return "t2_amphib"
        if tech >= 3:
            return "t3_assault"
        if tech == 2:
            return "t2_tank"
        if "BOT" in cats and ("light" in d or "assault bot" in d):
            return "t1_light_bot"
        if "TANK" in cats or "BOT" in cats:
            return "t1_tank" if "light" not in d else "t1_light_bot"
        return "t1_light_bot" if tech == 1 else "t2_tank"

    return "other"


def parse_sc() -> list[dict]:
    payload = json.loads(SC_JSON.read_text(encoding="utf-8"))
    units: list[dict] = []
    skip_factions = {"nomads", "none", ""}
    for raw in payload.get("units", []):
        general = raw.get("General") or {}
        faction = (general.get("FactionName") or "").strip()
        if faction.lower() in skip_factions:
            continue
        cats = set(raw.get("Categories") or [])
        if "CIVILIAN" in cats or "OPERATION" in cats:
            continue
        code = raw.get("Id") or ""
        desc = loc_text(raw.get("Description"))
        aka = loc_text(general.get("UnitName"))
        name = aka or desc or code
        defense = raw.get("Defense") or {}
        economy = raw.get("Economy") or {}
        physics = raw.get("Physics") or {}
        air = raw.get("Air") or {}
        weapons = []
        for w in raw.get("Weapon") or []:
            label = loc_text(w.get("DisplayName") or w.get("Label"))
            if not label or w.get("DummyWeapon") or (w.get("WeaponCategory") == "Death"):
                continue
            weapons.append(label)
        img_name = f"{code.lower()}.png"
        image = f"img/sc/{img_name}" if (IMG_SC / img_name).exists() else None
        speed = air.get("MaxAirspeed") or physics.get("MaxSpeed")
        units.append({
            "id": f"sc-{code.lower()}",
            "game": "sc",
            "code": code,
            "name": name,
            "aka": desc if aka and desc and desc != aka else None,
            "faction": faction.lower(),
            "domain": sc_domain(cats),
            "kind": desc or name,
            "tech": sc_tech(cats),
            "description": desc,
            "hp": defense.get("Health") or defense.get("MaxHealth"),
            "cost_metal": economy.get("BuildCostMass"),
            "cost_energy": economy.get("BuildCostEnergy"),
            "build_time": economy.get("BuildTime"),
            "speed": speed,
            "weapons": weapons,
            "role": sc_role(cats, desc, name),
            "image": image,
            "ted": None,
            "categories": sorted(cats),
        })
    return units


BAR_SKIP_PREFIX = ("critter_", "dbg_")
BAR_SKIP_EXACT = {
    "dice", "chip", "freefusion", "comeffigy", "dummycom",
}


def parse_bar_locale(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        head = re.match(r"^    ([a-zA-Z0-9_]+):\s*$", line)
        if head:
            current = head.group(1).lower()
            out[current] = {}
            continue
        if not current:
            continue
        field = re.match(r"^      (name|description):\s*(.*)$", line)
        if not field:
            continue
        val = field.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        out[current][field.group(1)] = val
    return out


def bar_skip(code: str) -> bool:
    c = code.lower()
    if any(c.startswith(p) for p in BAR_SKIP_PREFIX):
        return True
    if "_hat_" in c or c.startswith("cor_hat"):
        return True
    if "comlvl" in c or "comboss" in c:
        return True
    if c.endswith("_old"):
        return True
    return c in BAR_SKIP_EXACT


def bar_faction(code: str, subfolder: str) -> str | None:
    c = code.lower()
    if c.startswith("leg"):
        return "legion"
    if c.startswith("arm"):
        return "arm"
    if c.startswith("cor"):
        return "core"
    sf = (subfolder or "").lower()
    if "legion" in sf or sf.startswith("leg"):
        return "legion"
    if sf.lower().startswith("arm"):
        return "arm"
    if sf.lower().startswith("cor"):
        return "core"
    return None


def bar_domain(subfolder: str, desc: str) -> str:
    sf = (subfolder or "").lower()
    d = (desc or "").lower()
    if "commander" in d:
        return "commander"
    if any(x in sf for x in ("aircraft", "seaplane")):
        return "air"
    if "ship" in sf:
        return "navy"
    if "building" in sf:
        return "structure"
    if any(x in sf for x in ("bot", "vehicle", "hover", "gantry", "kbot")):
        return "land"
    return "other"


def bar_role(code: str, desc: str, name: str, subfolder: str, unitgroup: str, tech: int) -> str:
    up = code.upper()
    if up in TA_ROLE:
        return TA_ROLE[up]
    d = f"{desc} {name} {subfolder} {unitgroup}".lower()
    if "commander" in d:
        return "commander"
    if tech >= 3 or "experimental" in d or "gantry" in d:
        if "constructor" in d or "engineer" in d:
            return "t3_engineer"
        if any(x in d for x in ("lab", "plant", "shipyard", "factory")):
            return "t2_factory_land"
        return "experimental"
    if "constructor" in d or "engineer" in d or unitgroup == "builder":
        return "t2_engineer" if tech >= 2 else "t1_engineer"
    if "aircraft plant" in d:
        return "t2_factory_air" if tech >= 2 else "t1_factory_air"
    if "shipyard" in d:
        return "t2_factory_naval" if tech >= 2 else "t1_factory_naval"
    if any(x in d for x in ("bot lab", "vehicle plant", "hovercraft platform")):
        return "t2_factory_land" if tech >= 2 else "t1_factory_land"
    if "metal extractor" in d:
        return "t2_mex" if tech >= 2 else "t1_mex"
    if "fusion" in d or (tech >= 2 and "energy" in d and "converter" not in d):
        return "t3_energy" if tech >= 3 else "t2_energy" if tech >= 2 else "t1_energy"
    if "solar" in d or "wind" in d or "tidal" in d or unitgroup == "energy":
        return "t2_energy" if tech >= 2 else "t1_energy"
    if "converter" in d or "fabricat" in d:
        return "t1_fab"
    if "anti-nuke" in d or "antinuke" in d:
        return "antinuke"
    if "nuke" in d or "icbm" in d:
        return "nuke"
    if "shield" in d:
        return "shield"
    if "dragon" in d and ("teeth" in d or "fortification" in d or "wall" in d):
        return "wall"
    if "radar" in d or "sonar" in d:
        return "t1_radar"
    if "anti-air" in d or "flak" in d:
        if "tower" in d or "turret" in d or "battery" in d:
            return "t2_flak" if tech >= 2 else "t1_aa_turret"
        return "t2_flak" if tech >= 2 else "t1_aa"
    if "artillery" in d and ("tower" in d or "cannon" in d) and "mobile" not in d:
        return "t3_arty_static" if tech >= 3 else "t2_arty"
    if "laser tower" in d or "point defense" in d or "sentry" in d or "guard" in d:
        return "t2_pd" if tech >= 2 else "t1_pd"
    if "fighter" in d or "interceptor" in d:
        return "t3_asf" if tech >= 3 else "t2_fighter" if tech >= 2 else "t1_interceptor"
    if "bomber" in d:
        return "t3_strat_bomber" if tech >= 3 else "t2_bomber" if tech >= 2 else "t1_bomber"
    if "gunship" in d:
        return "t2_gunship"
    if "scout" in d and ("air" in d or "plane" in d):
        return "t1_air_scout"
    if "transport" in d:
        return "t1_transport"
    if "battleship" in d or "flagship" in d:
        return "t3_battleship"
    if "cruiser" in d:
        return "t2_cruiser"
    if "destroyer" in d:
        return "t2_destroyer"
    if "frigate" in d or "corvette" in d or "patrol boat" in d:
        return "t1_frigate"
    if "submarine" in d or "sub " in d:
        return "t1_sub"
    if "artillery" in d or "mortar" in d:
        return "t3_arty" if tech >= 3 else "t1_arty"
    if "rocket" in d or "missile launcher" in d:
        return "t2_mml" if tech >= 2 else "t1_arty"
    if "infantry" in d or "grunt" in d or "pawn" in d or "goblin" in d:
        return "t1_light_bot"
    if "scout" in d:
        return "t1_land_scout"
    if "tank" in d or "assault" in d or "bot" in d:
        if tech >= 3:
            return "t3_assault"
        if tech >= 2:
            return "t2_tank"
        return "t1_tank"
    return "other"


def parse_bar() -> list[dict]:
    raw_units = json.loads(BAR_JSON.read_text(encoding="utf-8"))
    locale = parse_bar_locale(BAR_LOCALE) if BAR_LOCALE.exists() else {}
    units: list[dict] = []
    for code, raw in raw_units.items():
        if bar_skip(code):
            continue
        loc = locale.get(code.lower(), {})
        name = loc.get("name") or code
        desc = loc.get("description") or ""
        cp = raw.get("customparams") or {}
        sub = cp.get("subfolder") or ""
        faction = bar_faction(code, sub)
        if not faction:
            continue
        try:
            tech = int(cp.get("techlevel") or 1)
        except (TypeError, ValueError):
            tech = 1
        if "commander" in desc.lower() and tech <= 1:
            tech = 0
        weapons = []
        wdefs = raw.get("weapondefs") or {}
        for key, w in wdefs.items():
            label = (w.get("name") if isinstance(w, dict) else None) or key
            weapons.append(str(label))
        img_name = f"{code.lower()}.png"
        image = f"img/bar/{img_name}" if (IMG_BAR / img_name).exists() else None
        units.append({
            "id": f"bar-{code.lower()}",
            "game": "bar",
            "code": code,
            "name": name,
            "aka": desc if desc and desc != name else None,
            "faction": faction,
            "domain": bar_domain(sub, desc),
            "kind": desc or name,
            "tech": tech,
            "description": desc,
            "hp": raw.get("health"),
            "cost_metal": raw.get("metalcost"),
            "cost_energy": raw.get("energycost"),
            "build_time": raw.get("buildtime"),
            "speed": raw.get("speed"),
            "weapons": weapons,
            "role": bar_role(code, desc, name, sub, cp.get("unitgroup") or "", tech),
            "image": image,
            "ted": None,
            "categories": [sub, cp.get("unitgroup") or ""],
        })
    return units


def convert_one(src: Path, dest: Path) -> tuple[str, bool, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src), "-frames:v", "1", "-update", "1", str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return src.name, dest.exists(), ""
    except subprocess.CalledProcessError as e:
        return src.name, False, (e.stderr or b"").decode("utf-8", "ignore")[-200:]


def convert_sc_icons() -> int:
    icon_dir = VENDOR_FA / "textures" / "ui" / "common" / "icons" / "units"
    files = list(icon_dir.glob("*_icon.dds"))
    jobs = []
    for src in files:
        stem = src.name.lower().replace("_icon.dds", "")
        if stem in {"default", "air", "land", "sea", "amph"}:
            continue
        dest = IMG_SC / f"{stem}.png"
        if dest.exists() and dest.stat().st_size > 0:
            continue
        jobs.append((src, dest))
    if not jobs:
        return len(list(IMG_SC.glob("*.png")))
    ok = 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = [pool.submit(convert_one, s, d) for s, d in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            name, success, err = fut.result()
            if success:
                ok += 1
            elif err:
                print(f"  fail {name}: {err[:120]}", file=sys.stderr)
            if i % 80 == 0:
                print(f"  converted {i}/{len(jobs)}")
    return len(list(IMG_SC.glob("*.png")))


def copy_ta_portraits() -> int:
    src = VENDOR_TA / "img" / "ta-units"
    IMG_TA.mkdir(parents=True, exist_ok=True)
    n = 0
    for png in src.glob("*.png"):
        dest = IMG_TA / png.name.lower()
        if not dest.exists():
            shutil.copy2(png, dest)
        n += 1
    return n


def copy_bar_portraits() -> int:
    src = VENDOR_BAR / "src" / "images" / "unitpics"
    IMG_BAR.mkdir(parents=True, exist_ok=True)
    n = 0
    for png in src.glob("*.png"):
        dest = IMG_BAR / png.name.lower()
        if not dest.exists() or dest.stat().st_size != png.stat().st_size:
            shutil.copy2(png, dest)
        n += 1
    return n


def write_sqlite(units: list[dict]) -> None:
    path = DATA_DIR / "units.sqlite"
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE units (
            id TEXT PRIMARY KEY,
            game TEXT,
            code TEXT,
            name TEXT,
            aka TEXT,
            faction TEXT,
            domain TEXT,
            kind TEXT,
            tech INTEGER,
            role TEXT,
            description TEXT,
            hp REAL,
            cost_metal REAL,
            cost_energy REAL,
            build_time REAL,
            speed REAL,
            weapons TEXT,
            image TEXT
        )
        """
    )
    rows = [
        (
            u["id"], u["game"], u["code"], u["name"], u.get("aka"),
            u["faction"], u["domain"], u["kind"], u["tech"], u["role"],
            u.get("description"), u.get("hp"), u.get("cost_metal"),
            u.get("cost_energy"), u.get("build_time"), u.get("speed"),
            ", ".join(u.get("weapons") or []), u.get("image"),
        )
        for u in units
    ]
    con.executemany(
        "INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    con.execute("CREATE INDEX idx_units_game ON units(game)")
    con.execute("CREATE INDEX idx_units_role ON units(role)")
    con.execute("CREATE INDEX idx_units_faction ON units(faction)")
    con.commit()
    con.close()


def write_csv(units: list[dict]) -> None:
    path = DATA_DIR / "units.csv"
    fields = [
        "id", "game", "code", "name", "aka", "faction", "domain", "kind",
        "tech", "role", "description", "hp", "cost_metal", "cost_energy",
        "build_time", "speed", "weapons", "image",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for u in units:
            row = {k: u.get(k) for k in fields}
            row["weapons"] = " | ".join(u.get("weapons") or [])
            w.writerow(row)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG.mkdir(parents=True, exist_ok=True)
    print("Copying TA portraits...")
    print("  TA portraits:", copy_ta_portraits())
    print("Converting SupCom icons (DDS → PNG)...")
    print("  SC icons:", convert_sc_icons())
    print("Copying BAR portraits...")
    print("  BAR portraits:", copy_bar_portraits())
    print("Parsing TA units...")
    ta = parse_ta()
    print(f"  {len(ta)} TA units")
    print("Parsing SupCom units...")
    sc = parse_sc()
    print(f"  {len(sc)} SC units (Nomads excluded)")
    print("Parsing BAR units...")
    bar = parse_bar()
    print(f"  {len(bar)} BAR units (critters/hats/levelled commanders skipped)")
    for u in sc:
        p = IMG_SC / f"{u['code'].lower()}.png"
        u["image"] = f"img/sc/{p.name}" if p.exists() else None
    for u in ta:
        p = IMG_TA / f"{u['code'].lower()}.png"
        if not p.exists() and u.get("image"):
            alt = Path(u["image"]).name
            p = IMG_TA / alt
        u["image"] = f"img/ta/{p.name}" if p.exists() else None
    for u in bar:
        p = IMG_BAR / f"{u['code'].lower()}.png"
        u["image"] = f"img/bar/{p.name}" if p.exists() else None

    units = ta + sc + bar
    catalog = {
        "generated": date.today().isoformat(),
        "games": GAMES,
        "source": {
            "ta": "coreprime/reference-ta (OTA v3.1c + CC + BT)",
            "sc": "FAForever etfreeman-db + FAForever/fa unit icons",
            "bar": "paul/BAR-units-db (Beyond All Reason unitdefs + unitpics)",
        },
        "counts": {
            "ta": len(ta),
            "sc": len(sc),
            "bar": len(bar),
            "total": len(units),
            "with_image": sum(1 for u in units if u.get("image")),
        },
        "lineage": [{"id": i, "label": l} for i, l in LINEAGE],
        "units": units,
    }
    (DATA_DIR / "units.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (CATALOG / "data.js").write_text(
        "window.CATALOG = " + json.dumps(catalog, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    write_csv(units)
    write_sqlite(units)
    print("Wrote:")
    print(" ", DATA_DIR / "units.json")
    print(" ", DATA_DIR / "units.csv")
    print(" ", DATA_DIR / "units.sqlite")
    print(" ", CATALOG / "data.js")
    print("counts", catalog["counts"])


if __name__ == "__main__":
    main()
