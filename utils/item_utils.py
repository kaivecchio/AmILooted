from utils.constants import tiernames, sourcesLookup, slotdict, bossesList

qeWeaponSlots = ["One-Hand", "Ranged", "Two-Hand"]
items = {}
itemSources = {}
itemBosses = {}

def tierfilter(itemname, key):
    if tiercheck(itemname):
        ilvl = itemname.split()[-1]
        slot = key.rstrip("/").split("/")[-1]
        piece = slot_to_piece(slot)
        return "Tier " + piece + " " + ilvl
    return itemname

def add_to_items(itemname, itemSlot: str):
    if itemname in items:
        return
    items[itemname] = itemSlot.lower()

def find_item_source(inputString):
    for substring, mapped in sourcesLookup.items():
        if substring in inputString:
            return mapped

def add_to_item_sources(itemname, itemSource):
    if itemname in itemSources:
        return
    itemSources[itemname] = itemSource

def find_item_boss(inputString):
    for boss in bossesList:
        if boss in inputString:
            return boss
    print("Boss drop for item not found, inputString:" + inputString)

def resolve_qe_item_boss(inputString: str):
    import re
    truncated_input = re.sub(r'\d{3}$', '', inputString).rstrip()
    for key, value in itemBosses.items():
        truncated_key = re.sub(r'\d{3}$', '', key).rstrip()
        if truncated_key == truncated_input:
            return value
    return "Unkown Boss"

def add_to_item_bosses(itemName, bossName):
    if itemName in itemBosses:
        return
    itemBosses[itemName] = bossName

def escape_csv_field(field):
    field = field.replace('"', '""')
    if any(c in field for c in [',', '"', '\n']):
        field = f'"{field}"'
    return field

def standardize_qe_item_slot(slot: str) -> str:
    """Standardizes QE/wowhead slot names to your internal slot naming."""
    slot = slot.lower()
    mapping = {
        "head": "head",
        "shoulder": "shoulder",
        "waist": "waist",
        "wrist": "wrist",
        "hands": "hands",
        "back": "back",
        "legs": "legs",
        "feet": "feet",
        "chest": "chest",
        "main hand": "main_hand",
        "off hand": "off_hand",
        "held in off-hand": "off_hand",
        "one-hand": "main_hand",
        "two-hand": "main_hand",
        "ranged": "ranged",
        # Add more mappings as needed
    }
    # Try to match by key, fallback to original
    return mapping.get(slot, slot)

def tiercheck(itemname):
    for t in tiernames:
        if t in itemname:
            return True
    return False

def slot_to_piece(slot):
    return slotdict[slot]

def can_be_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False