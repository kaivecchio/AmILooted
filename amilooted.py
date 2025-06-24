# Use: python amilooted.py [urlfile.txt]
# Reads droptimizer sim urls from urlfile.txt, or from "simlist.txt" if no
# argument is given.
# File should be formatted like so:
#
#     Castymcspell: https://www.raidbots.com/reports/[hash]
#     Foxfrost: https://www.raidbots.com/reports/[hash]
#     etc.
#
# Names in the URL file are not important; the script extracts them from the
# raidbots information.  But having names in said file will be useful for the
# loot council when getting new sims so they can update the correct part of the
# file easily.
#
# In cases where multiple sims are used (e.g., Normal vs. Heroic vs. Mythic),
# simply put all the sims in the file on separate lines.  E.g.,
#
#     Castymcspell: [normal droptimizer URL]
#     Castymcspell: [heroic droptimizer URL]
#     Castymcspell: [mythic droptimizer URL]
#     Foxfrost: [normal droptimizer URL]
#     Foxfrost: [heroic droptimizer URL]
#     Foxfrost: [mythic droptimizer URL]
#     etc.
#
# and this script will automatically do the right thing and have distinct rows
# for items with different maxixmum item level.  So, for example, if Normal,
# Heroic, and Mythic droptimizers for Aberrus are provided, there will be three
# rows in the output spreadsheet for the Ominous Chromatic Essence (one for
# Normal which caps at 437 ilvl, one for Heroic at 441, and one for Mythic at
# 444), but only two for the Elementium Pocket Anvil (becaue Heroic caps at 441,
# and it drops at an unupgradeable 441 on Mythic).

import subprocess
import os
import sys
import time
import datetime
import json
import re
import traceback
import utils.tier_names as tier_names
from models.player import Player, ItemCandidate
from collections import defaultdict
import xml.etree.ElementTree as ET
try:
    import requests
except:
    print("Requests library not installed!  Installing...")
    subprocess.call([sys.executable, "-m", "pip", "install", "requests"])
    print("Requests should be installed; this should only happen once.")
    import requests
import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account


SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Or your service account file

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def write_to_sheet(service, spreadsheet_id, sheet_name, values):
    body = {
        'values': values
    }
    range_name = f"{sheet_name}!A1"
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueInputOption="RAW", body=body).execute()

def clear_sheet(service, spreadsheet_id, sheet_name):
    # Get the sheet ID from the sheet name
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    for s in spreadsheet['sheets']:
        if s['properties']['title'] == sheet_name:
            sheet_id = s['properties']['sheetId']
            break
    if sheet_id is None:
        raise ValueError(f"Sheet '{sheet_name}' not found.")

    # Clear values
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}"
    ).execute()

    # Clear formatting and filters
    requests_body = [
        {"updateCells": {
            "range": {"sheetId": sheet_id},
            "fields": "userEnteredFormat"
        }},
        {"clearBasicFilter": {"sheetId": sheet_id}}
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests_body}
    ).execute()
    
tiernames = tier_names.tiernames

#A dictionary that turns slot name into an appropriate gear name.
#Used to build strings like "Tier Helmet".
slotdict = {"head":"Helmet",
            "shoulder":"Pauldrons",
            "waist":"Belt",
            "wrist":"Bracers",
            "hands":"Gloves",
            "back":"Cloak",
            "legs":"Pants",
            "feet":"Boots",
            "chest":"Chest"}

def can_be_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def slot_to_piece(slot):
    return slotdict[slot]


def tiercheck(itemname):
    for t in tiernames:
        if t in itemname:
            return True
    return False
    
    
#To avoid adding a mess of disparate tier sets, condense all such things
#into, e.g., "Tier Helm 441"
def tierfilter(itemname, key):
    if tiercheck(itemname):
        #Get the slot from the last part of key.
        #Get the ilvl as the last token in item.
        ilvl = itemname.split()[-1]
        slot = key.rstrip("/").split("/")[-1]
        piece = slot_to_piece(slot)
        return "Tier " + piece + " " + ilvl
    return itemname


#The QE/wowhead calls give us verbose details on where the item could go, we want to compare with the best use anyways so we standardize them.
qeWeaponSlots = ["One-Hand", "Ranged", "Two-Hand"]
def standardize_qe_item_slot(inputSlot):
    if inputSlot in qeWeaponSlots:
        return "main_hand"
    if inputSlot == "Off Hand" or inputSlot == "Held In Off-hand":
        return "off_hand"
    return inputSlot


#Dictionary of all the item names (key) being simmed in anyone's droptimizers and their item slots (value).
items = {}
def add_to_items(itemname, itemSlot: str):
    if itemname in items:
            return
    items[itemname] = itemSlot.lower()
    
    
NORMAL_RAID_SOURCE = "Normal Raid"
HEROIC_RAID_SOURCE = "Heroic Raid"
MYTHIC_RAID_SOURCE = "Mythic Raid"
DUNGEON_SOURCE = "Mythic +10 Vault"
DUNGEON_DROP_SOURCE = "Mythic+ Dungeon Drop"
DELVES_SOURCE = "Delves"
CRAFTED_SOURCE = "Crafted Item"
BIS_REASON = "Best in slot"
UPGRADE_PCT_REASON = "Upgrade percent"

#Dictionary of all the item names (key) being simmed in anyone's droptimizers and their source (value).
itemSources = {}
sourcesLookup = { 
                 "raid-normal": NORMAL_RAID_SOURCE,
                 "raid-heroic": HEROIC_RAID_SOURCE,
                 "raid-mythic": MYTHIC_RAID_SOURCE,
                 "dungeon-mythic-weekly10": DUNGEON_SOURCE
}

qeSourcesLookup = {
    "Raid 3": NORMAL_RAID_SOURCE,
    "Raid 5": HEROIC_RAID_SOURCE,
    "Raid 7": MYTHIC_RAID_SOURCE,
    "Dungeon 10": DUNGEON_SOURCE,
    "Dungeon 6": DUNGEON_DROP_SOURCE,
    "Crafted ": CRAFTED_SOURCE,
    "Delves ": DELVES_SOURCE
}

def find_item_source(inputString):
    for substring, mapped in sourcesLookup.items():
        if substring in inputString:
            return mapped
   

def add_to_item_sources(itemname, itemSource):
    if itemname in itemSources:
            return
    itemSources[itemname] = itemSource
    
#Dictionary of all the item names (key) being simmed in anyone's droptimizers and the boss they drop from (value).
itemBosses = {}
bossesList = [
    "Mythic+ Dungeons",
    "Trash Drop",
    "Ulgrax the Devourer",
    "The Bloodbound Horror",
    "Sikran, Captain of the Sureki",
    "Rasha'nan",
    "Broodtwister Ovi'nax",
    "Nexus-Princess Ky'veza",
    "The Silken Court",
    "Queen Ansurek",
    "Vexie and the Geargrinders",
    "Cauldron of Carnage",
    "Rik Reverb",
    "Stix Bunkjunker",
    "Sprocketmonger Lockenstock",
    "The One-Armed Bandit",
    "Mug'Zee, Heads of Security",
    "Chrome King Gallywix"
]

def find_item_boss(inputString):
    for boss in bossesList:
        if boss in inputString:
            return boss  # Return the substring that is found
    print("Boss drop for item not found, inputString:" + inputString)


def resolve_qe_item_boss(inputString: str):
    # 1. Remove the last 3 digits from input_string, if present
    #    Regex finds 3 digits (\d{3}) at the very end of the string ($)
    truncated_input = re.sub(r'\d{3}$', '', inputString).rstrip()
    
    # 2. Iterate over itemBosses' keys, removing last 3 digits from each key
    for key, value in itemBosses.items():
        truncated_key = re.sub(r'\d{3}$', '', key).rstrip()

        # 3. Compare the truncated forms
        if truncated_key == truncated_input:
            return value

    # 4. If no match was found
    return "Unkown Boss"


def add_to_item_bosses(itemName, bossName):
    if itemName in itemBosses:
        return
    itemBosses[itemName] = bossName

#List of players with droptimizers.
players: list[Player] = []

#Check to see if there's already a player by that name.  If not, we'll add
#a new player object to the players list.  If yes, add this droptimizer data
#to the existing player.
#If someone submitted sims for multiple specs, treat the specs as different
#players with the same name.
def add_player(charname, spec):
    pindex = -1
    multispec = False
    for i in range(len(players)):
        if charname == players[i].name:
            if spec == players[i].spec:
                pindex = i
                break
            else:
                players[i].multispec = True
                multispec = True
    
    if pindex == -1:
        players.append(Player(charname, spec, multispec))
   
    return pindex
    
#Key function used to sort the player list by role.
def rolekey(p):
    if p.spec == "Protection" or \
       p.spec == "Blood" or \
       p.spec == "Guardian" or \
       p.spec == "Brewmaster" or \
       p.spec == "Vengenace":
        return 0
    if p.spec == "Holy" or \
       p.spec == "Restoration" or \
       p.spec == "Discipline" or \
       p.spec == "Mistweaver" or \
       p.spec == "Healer" or \
       p.spec == "Preservation":
        return 2
    return 1

def escape_csv_field(field):
    # First, escape any existing double quotes by doubling them
    field = field.replace('"', '""')
    
    # If the field contains a comma, a double quote, or a newline,
    # enclose it in double quotes.
    if any(c in field for c in [',', '"', '\n']):
        field = f'"{field}"'
    return field

def grabraidbots(url):
    #Add a trailing / if we didn't already have one
    if not url[-1] == "/":
        url = url + "/"
    inputurl = url + "input.txt"
    outputurl = url + "data.csv"
    
    inputdata = requests.get(inputurl).text.split("\n")
    outputdata = requests.get(outputurl).text.split("\n")
    
    #If input came from the simc addon:
    #   Line 2 of inputdata looks like:
    #   # Foxfrost - Enhancement - 2023-05-23 19:18 - US/Thrall
    #If input came from the armory:
    #   Line 2 of inputdata looks like:
    #   armory=us,thrall,Foxfrost
    #Either way, get the character name from line 2.
    #But we can only get the specialization from input.txt if the simc addon
    #was used; if armory data was used, we have to dig into data.json.
    if len(inputdata) < 2:
        raise ValueError(f"input.txt is missing expected lines: {inputdata}")
    
    charname = ""
    spec = ""
    if inputdata[1][0] == "#":
        charname = inputdata[1].split()[1]
        spec = inputdata[1].split()[3]
    else:
        charname = inputdata[1].split(",")[-1]
        #Get spec from data.json.  We could do this in all cases,
        #but I've chosen to only do it when necessary because data.json
        #is quite large and I'd prefer to avoid downloading the whole thing.
        jsondata = json.loads(requests.get(url+"data.json").text)
        spec = jsondata["sim"]["players"][0]["specialization"].split()[0]
    

    pindex = add_player(charname, spec)
    
    #Extract the names of the items simmed, as well as their profileset names
    #Item name example: Harlan's Loaded Dice 441
    #Profileset name example: -1/1001/dungeon-mythic-weekly16/155881/0/trinket1/
    #Note that items will often have multiple profilesets associated with them.
    #Especially rings and trinkets, which get simmed multiple times in different
    #slots.
    #However, profileset names will uniquely identify an item.
    #
    #The relevant information in the input file is between the "# Actors" line
    #and the "# Simulation Options" line.  So scan for those lines and use them
    #to bound where we look.
    relevant = False
    itemname = ""
    gearnames = {}
    for i in range(len(inputdata)- 1):
        line = inputdata[i]
        if line == "# Actors":
            relevant = True
            continue
        if not relevant:
            continue
        if line == "# Simulation Options":
            break
        
        #If we've gotten this far, every line will either be blank, or a comment
        #with the item name, or a profileset line immediately following the
        #relevant comment.  If it's a comment, store the item name and the next
        #iteration of the loop will use it.
        if line == "":
            continue
        if line[0] == "#":
            itemname = line.split(" - ")[0][1:].strip()
            pattern = r'\+=([A-Za-z_]+)(?:[12])?=,'

            match = re.search(pattern, inputdata[i+1])
            if match:
                itemslot = match.group(1)
            else:
                # Handle the case where no match is found.
                # Example line we're looking for:
                # 'profileset."1273/2607/raid-normal/212388/597/3368/main_hand//"+=main_hand=,id=212388,enchant_id=3368,bonus_id=4822/4786/1498/10273'
                itemslot = "weapon/off-hand/shield"
                print("No match found in line:", inputdata[i+1])
            #Ugly: if itemname is a tier piece, don't add it to the list of
            #items just yet.  Instead, we'll be changing itemname on the next
            #pass through this loop before we add it; we need the additional
            #context of the next line to figure out how to do this properly 
            #without hardcoding a lot of names.
            if not tiercheck(itemname):
                add_to_items(itemname, itemslot)
                add_to_item_sources(itemname, find_item_source(inputdata[i+1]))
                add_to_item_bosses(itemname, find_item_boss(inputdata[i]))
            continue
        
        key = line.split("\"")[1]
        if tiercheck(itemname):
            itemname = tierfilter(itemname, key)
            add_to_items(itemname, itemslot)
            add_to_item_sources(itemname, find_item_source(key))
            add_to_item_bosses(itemname, find_item_boss(inputdata[i-1]))
        gearnames.update({line.split("\"")[1].removesuffix("swap_mh"):itemname})
    
    #XXX: TODO: Sanity-check the input.  Make sure people are simming on
    #Patchwerk instead of HecticAddCleave or DungeonSlice.
    
    
    #Now to start extracting the relevant information from the output.
    #Line 2 of data.csv has baseline DPS in its second column.
    #Further lines have profileset names in first column, new DPS in second.
    baselinedps = float(outputdata[1].split(",")[1])
    for line in outputdata[2:]:
        if line == "":
            continue
        last_slash_index = line.rfind('/')
        key = line[:last_slash_index] + "/" if last_slash_index != -1 else line
        key = key.replace('"', '')
        item = gearnames[key]
        
        if can_be_float(line.split(",")[1]):
            newdps = float(line.split(",")[1])
        else:
            newdps = float(line.split(",")[2])
        
        percentupgrade = round(int(10000 * (newdps - baselinedps)/baselinedps) * 0.01, 3)
        if item in players[pindex].sims:
            #This means we already added the item to the player's sims at some
            #point, probably because this is a ring or trinket and we simmed it
            #in the first slot before and this is the second slot.  Check to see
            #if this is better; only update if it is.
            if percentupgrade > players[pindex].sims[item]:
                players[pindex].sims.update({item:percentupgrade})
        else:
            players[pindex].sims.update({item:percentupgrade})


def wowhead_item_name(item_id, ilvl):
    url = f"https://www.wowhead.com/item={item_id}?xml"
    resp = requests.get(url)
    if not resp.ok:
        return None

    # Parse XML
    root = ET.fromstring(resp.text)
    # The <wowhead> root usually contains <item> child
    item_elem = root.find("item")
    if item_elem is not None:
        # <name> sub-element typically holds the item name
        name_elem = item_elem.find("name")
        if name_elem is not None:
            itemName = name_elem.text + " " + ilvl
            slot_elem = item_elem.find("inventorySlot")
            add_to_items(itemName, standardize_qe_item_slot(slot_elem.text))
            return itemName
    return None

def get_qe_report_id(url: str) -> str:
    """
    Extracts the QE Live report ID from a URL like:
      https://questionablyepic.com/live/upgradereport/<reportId>
    and returns <reportId>.
    """
    # Strip trailing slash, if present
    url = url.rstrip('/')

    # Split by '/' and return the last chunk
    parts = url.split('/')
    return parts[-1]

def parse_qe_report(report_id):
    url = f"https://questionablyepic.com/api/getUpgradeReport.php?reportID={report_id}"
    resp = requests.get(url)
    
    # First parse
    data = resp.json()

    # data is apparently a string with encoded JSON
    if isinstance(data, str):
        # Do a second decode
        data2 = json.loads(data)
        data = data2
    #else:
        # data is already a dict

    # Basic metadata
    report_id = data["id"]                 # e.g. "chunzqjetpaz"
    date_created = data["dateCreated"]     # e.g. "2024 - 11 - 12"
    charname = data["playername"]       # e.g. "Cynnee"
    realm = data["realm"]                 # e.g. "Thrall"
    region = data["region"]               # e.g. "US"
    spec = data.get("spec", "")           # e.g. "Holy Paladin"
    pindex = add_player(charname, spec)
    # The "results" list holds all item upgrades
    results = data["results"]             # array of dicts

    # Each dict includes:
    #   item            (item ID, e.g. 133286)
    #   dropLoc         (e.g. "Dungeon", "Raid", "Crafted")
    #   dropDifficulty  (integer or "" for crafted)
    #   level           (item level)
    #   score           (QE internal score, e.g. 0.003...)
    #   rawDiff         (raw difference, e.g. 4371)
    #   percDiff        (percentage difference, e.g. 0.273)

    # Do something with that data. For example, let's build a structured list:
    for entry in results:
        ilvl = entry["level"]
        itemName = wowhead_item_name(entry["item"], str(ilvl))
        location = entry["dropLoc"]
        difficulty = entry.get("dropDifficulty")
        
        #Add the item to itemSources if not recognized
        itemSourceRaw = location + " " + str(difficulty)
        if itemSourceRaw in qeSourcesLookup.keys():
            itemSource = qeSourcesLookup[itemSourceRaw]
        else:
            itemSource = "Uknown Item Source"
        add_to_item_sources(itemName, itemSource)
        
        #TODO: Add to itemBosses properly via a mapping for healer exclusive items
        if itemName not in itemBosses.keys():
            add_to_item_bosses(itemName, resolve_qe_item_boss(itemName))
        
        percentage = entry["percDiff"]   # in decimal form (0.273 = 27.3%)
        
        if itemName in players[pindex].sims:
            #This means we already added the item to the player's sims at some
            #point, probably because this is a ring or trinket and we simmed it
            #in the first slot before and this is the second slot.  Check to see
            #if this is better; only update if it is.
            if percentage > players[pindex].sims[itemName]:
                players[pindex].sims[itemName] = (percentage)
            #else: 
                #do nothing
        else:
            players[pindex].sims[itemName] = (percentage)
        
        

def graburl(url):
    try:
        if "raidbots.com" in url:
            print("Checking " + url)
            grabraidbots(url)
        if "questionablyepic.com" in url:
            print("Checking " + url)
            parse_qe_report(get_qe_report_id(url))
            
    except Exception as e:
        print("ERROR with URL:")
        print(url)
        print("An unexpected error occurred:", e)
        traceback.print_exc()

def calculate_delta(player: Player, itemName: str, incomingValue: float, slot: str, source: str):
    if source == NORMAL_RAID_SOURCE or source == DUNGEON_SOURCE or source == CRAFTED_SOURCE:
        bis_item = player.normal_bis.get_bis(slot)
        bis_value = player.sims[bis_item]
        delta_value = incomingValue - bis_value
        player.normal_delta_matrix[itemName] = delta_value
    
    if source == HEROIC_RAID_SOURCE or source == DUNGEON_SOURCE or source == CRAFTED_SOURCE:
        bis_item = player.heroic_bis.get_bis(slot)
        bis_value = player.sims[bis_item]
        delta_value = incomingValue - bis_value
        player.heroic_delta_matrix[itemName] = delta_value
        
    if source == MYTHIC_RAID_SOURCE or source == DUNGEON_SOURCE or source == CRAFTED_SOURCE:
        bis_item = player.mythic_bis.get_bis(slot)
        bis_value = player.sims[bis_item]
        delta_value = incomingValue - bis_value
        player.mythic_delta_matrix[itemName] = delta_value

def build_delta_matrices():
    for player in players:
        for item in player.sims:
            val = player.sims[item]
            slot = items[item]
            source = itemSources[item]
            calculate_delta(player, item, val, slot, source)


def check_and_add_bis(player: Player, itemName: str, incomingValue: float, slot: str, source: str):
    #If item is from normal or dungeon, then check and add bis
    if source == NORMAL_RAID_SOURCE or source == DUNGEON_SOURCE or source == CRAFTED_SOURCE:
        if player.normal_bis.get_bis(slot) is None: 
            player.normal_bis.set_bis(slot, itemName)
        else:   
            current_bis = player.normal_bis.get_bis(slot)
            if player.sims[current_bis] < incomingValue:
                player.normal_bis.set_bis(slot, itemName)

    #If item is from normal or dungeon, then check and add bis
    if source == HEROIC_RAID_SOURCE or source == DUNGEON_SOURCE or source == CRAFTED_SOURCE:
        if player.heroic_bis.get_bis(slot) is None: 
            player.heroic_bis.set_bis(slot, itemName)
        else:    
            current_bis = player.heroic_bis.get_bis(slot)
            if player.sims[current_bis] < incomingValue:
                player.heroic_bis.set_bis(slot, itemName)
    
    #If item is from normal or dungeon, then check and add bis
    if source == MYTHIC_RAID_SOURCE or source == DUNGEON_SOURCE or source == CRAFTED_SOURCE:
        if player.mythic_bis.get_bis(slot) is None: 
            player.mythic_bis.set_bis(slot, itemName)
        else:    
            current_bis = player.mythic_bis.get_bis(slot)
            if player.sims[current_bis] < incomingValue:
                player.mythic_bis.set_bis(slot, itemName)        

#Finds the next best item in this slot for this raid difficulty
#This looping is starting to be expensive, there are probably smarter ways to achieve this
def find_next_best(player: Player, item: str, source: str):
    next_best = None
    slot = items[item]
    for key in player.sims:
        thisSource = itemSources[key]
        if thisSource != DUNGEON_SOURCE and thisSource != CRAFTED_SOURCE and thisSource != DELVES_SOURCE and thisSource != source:
            continue
        if items[key] != slot or key == item:
            continue
        if next_best is None:
            next_best = player.sims[key]
            continue
        if player.sims[key] > next_best:
            next_best = player.sims[key]
    return next_best if next_best is not None else 0


def populate_bis_lists():
    for player in players:
        for key in player.sims:
            val = player.sims[key]
            slot = items[key]
            source = itemSources[key] 
            check_and_add_bis(player, key, val, slot, source)

item_Choices: dict[str, ItemCandidate] = {}
def add_if_bis(item: str, source: str, choices, reason: str):
    for player in players:
            if item in player.sims and player.sims[item] > 0:
                
                if source == NORMAL_RAID_SOURCE:
                    if player.normal_delta_matrix[item] == 0:
                        item_val = player.sims[item]
                        next_best = find_next_best(player, item, source)
                        next_best_delta = item_val - next_best
                        if item_val > next_best:
                            choices.append(ItemCandidate(
                                player,
                                item_val,
                                next_best_delta,
                                next_best,
                                reason))
                        
                if source == HEROIC_RAID_SOURCE:
                    if player.heroic_delta_matrix[item] == 0:
                        item_val = player.sims[item]
                        next_best = find_next_best(player, item, source)
                        next_best_delta = item_val - next_best
                        if item_val > next_best:
                            choices.append(ItemCandidate(
                                player,
                                item_val,
                                next_best_delta,
                                next_best,
                                reason))
                        
                if source == MYTHIC_RAID_SOURCE:
                    if player.mythic_delta_matrix[item] == 0:
                        item_val = player.sims[item]
                        next_best = find_next_best(player, item, source)
                        next_best_delta = item_val - next_best
                        if item_val > next_best:
                            choices.append(ItemCandidate(
                                player,
                                item_val,
                                next_best_delta,
                                next_best,
                                reason))

def add_if_upgrade(item:str, source:str, choices, reason: str):
    for player in players:
        if item in player.sims and player.sims[item] > 0:
            if source == NORMAL_RAID_SOURCE:
                item_val = player.sims[item]
                next_best = find_next_best(player, item, source)
                next_best_delta = item_val - next_best
                choices.append(ItemCandidate(
                    player,
                    item_val,
                    next_best_delta,
                    next_best,
                    reason))
                    
            if source == HEROIC_RAID_SOURCE:
                item_val = player.sims[item]
                next_best = find_next_best(player, item, source)
                next_best_delta = item_val - next_best
                choices.append(ItemCandidate(
                    player,
                    item_val,
                    next_best_delta,
                    next_best,
                    reason))
                    
            if source == MYTHIC_RAID_SOURCE:
                item_val = player.sims[item]
                next_best = find_next_best(player, item, source)
                next_best_delta = item_val - next_best
                choices.append(ItemCandidate(
                    player,
                    item_val,
                    next_best_delta,
                    next_best,
                    reason))

def remove_second_occurrences(choices):
    seen = set()
    filtered_choices = []

    for choice in choices:
        if choice.player.name not in seen:
            seen.add(choice.player.name)
            filtered_choices.append(choice)

    return filtered_choices

def create_choices():
    no_choice_player = Player("No choice", None, None)
    for item in sorted(items.keys()):
        source = itemSources[item]
        if source == DUNGEON_SOURCE or source == CRAFTED_SOURCE or source == DELVES_SOURCE:
            continue
        choices = []
        add_if_bis(item, source, choices, BIS_REASON)
        
        if len(choices) > 4:
            choices.sort(key=lambda x: x.item_delta, reverse=True)
            choices = choices[:5] 
            item_Choices[item] = choices
            continue
        
        non_bis_choices = []
        add_if_upgrade(item, source, non_bis_choices, UPGRADE_PCT_REASON)
        if len(non_bis_choices) > 0:
            non_bis_choices.sort(key=lambda x: (x.item_val, x.item_delta), reverse=True)
            
        choices.sort(key=lambda x: x.item_delta, reverse=True)
        choices.extend(non_bis_choices)
        choices = remove_second_occurrences(choices)
        choices = choices[:5]
        item_Choices[item] = choices
        
        while len(choices) < 5:
            choices.append(ItemCandidate(
                        no_choice_player,
                        0,
                        0,
                        0,
                        "No candidate"))

def nested_dict():
    return defaultdict(nested_dict)

def does_source_boss_match_exist(source, boss):
    for itemSource in itemSources.keys():
        if itemSources[itemSource] == source:
            for itemBoss in itemBosses.keys():
                if itemBosses[itemBoss] == boss:
                    if itemSource == itemBoss:
                        return True
    return False

def create_ev_dictionary():
    ev_dict = nested_dict()
    
    for source in sourcesLookup.values():
        for boss in bossesList:
            if does_source_boss_match_exist(source, boss):
                for player in players:
                    total_count = 0
                    non_negative_sum = 0
                    for item in player.sims.keys():
                        if itemSources[item] == source and itemBosses[item] == boss:
                            total_count += 1
                            if player.sims[item] > 0:
                                non_negative_sum += player.sims[item]
                    ev_dict[source][boss][player.name] = round(non_negative_sum / total_count if total_count > 0 else 0, 3)
    return add_average_to_ev_dictionary(ev_dict)

def add_average_to_ev_dictionary(ev_dict: defaultdict):
    for source in ev_dict.keys():
        for boss in ev_dict[source].keys():
            total_count = 0
            non_negative_sum = 0
            for player_name, value in ev_dict[source][boss].items():
                total_count += 1
                if value > 0:
                    non_negative_sum += value
            if total_count > 0:
                average_value = non_negative_sum / total_count if total_count > 0 else 0
                ev_dict[source][boss]["Average"] = round(average_value, 3)
            else: 
                ev_dict[source][boss]["Average"] = 0
    return ev_dict

def main():
    #Ugly hack for stupid operating systems:
    #Calling this by double-click on Windows makes us live in a weird directory
    #somewhere.  Extract the real directory from sys.argv[0] and navigate there.
    if not sys.argv[0] == "amilooted.py":
        os.chdir(sys.argv[0][:-13])
    simfile = "simlist.txt"
    
    if len(sys.argv) > 1:
        simfile = sys.argv[1]

    use_local = True
    try:
        simlines = open(simfile,"r").readlines()
    except:
        print(simfile + " could not be read!")
        print("Using Am I Muted's online spreadsheet instead.")
        use_local = False


    if use_local:
        linenum = 0
        for line in simlines:
            linenum += 1
            graburl(line.split()[-1])

    else:
        spreadsheeturl = "https://docs.google.com/spreadsheets/d/1jeBFHraMVA-IiuP-nLD0IWIaQom2av7XgDPa7qt43Ls/gviz/tq?tqx=out:csv&sheet=Droptimizer"
        try:
            spreadsheetdata = requests.get(spreadsheeturl).text.split("\n")
        except:
            print("Could not access URL:")
            print(spreadsheeturl)
            print("Press Enter to close the program.")
            sys.exit(1)
        #Check all the cells in the spreadsheet.  If any of them are raidbots links, run grabraidbots on them.
        for line in spreadsheetdata:
            cells = line.split(",")
            name = ""
            for cell in cells:
                if cell != "":
                    name = cell
            #All entries from this download have quotes surrounding them.
            for cell in cells:
                #Strip leading and trailing quotation marks, then tokenize (this
                #might be necessary if there are notes next to some urls).
                data = cell[1:-1].split()
                for d in data:
                    graburl(d)

    populate_bis_lists()
    build_delta_matrices()
    create_choices()
    ev_dictionary = create_ev_dictionary()
    
    #Sort players alphabetically, and by role.  Tanks first, then DPS, then
    #healers.
    #Sort alphabetically first so that the role sorting actually works.
    players.sort(key=lambda p: p.name)
    players.sort(key=rolekey)
            
    outfilename = "droptimizers-" + \
                  datetime.datetime.fromtimestamp( \
                  time.time()).strftime("%d-%m-%Y") + ".csv"

    output = open(outfilename,"w")
    
    mythicRaidFilename = "mythic-raid-choices-" + \
                  datetime.datetime.fromtimestamp( \
                  time.time()).strftime("%d-%m-%Y") + ".csv"
                  
    mythicRaidOutput = open(mythicRaidFilename,"w")
    
    heroicRaidFilename = "heroic-raid-choices-" + \
                  datetime.datetime.fromtimestamp( \
                  time.time()).strftime("%d-%m-%Y") + ".csv"
                  
    heroicRaidOutput = open(heroicRaidFilename,"w")
    
    normalRaidFilename = "normal-raid-choices-" + \
                  datetime.datetime.fromtimestamp( \
                  time.time()).strftime("%d-%m-%Y") + ".csv"
                  
    normalRaidOutput = open(normalRaidFilename,"w")
    
    
    evFileName = "ev_sheet-"+ \
                  datetime.datetime.fromtimestamp( \
                  time.time()).strftime("%d-%m-%Y") + ".csv"
    
    evOutput = open(evFileName,"w")
    
    #Print headers for item, slot, and sources columns
    output.write("Item Name" + "," + "Slot" + "," + "Source" + "," + "Boss")
    evOutput.write("Source" + "," + "Boss" + "," + "Player" + "," + "EV")
    
    choicesFileHeaders = [
        "Boss", "Item Name",
        "Choice 1", "Choice 1 Reason", "Choice 1 % Upgrade", "Next Best Alternative",
        "Choice 2", "Choice 2 Reason", "Choice 2 % Upgrade", "Next Best Alternative",
        "Choice 3", "Choice 3 Reason", "Choice 3 % Upgrade", "Next Best Alternative",
        "Choice 4", "Choice 4 Reason", "Choice 4 % Upgrade", "Next Best Alternative",
        "Choice 5", "Choice 5 Reason", "Choice 5 % Upgrade", "Next Best Alternative",
    ]
    mythicRaidOutput.write(",".join(choicesFileHeaders) + "\n")
    heroicRaidOutput.write(",".join(choicesFileHeaders) + "\n")
    normalRaidOutput.write(",".join(choicesFileHeaders) + "\n")

    #Instead of opening files, collect rows:
    output_rows = []
    mythicRaid_rows = []
    heroicRaid_rows = []
    normalRaid_rows = []
    ev_rows = []

    #Prepare headers as before, but as lists:
    output_rows.append(["Item Name", "Slot", "Source", "Boss"] + [p.name + (f" ({p.spec})" if p.multispec else "") for p in players])
    choicesFileHeaders = [
        "Boss", "Item Name",
        "Choice 1", "Choice 1 Reason", "Choice 1 % Upgrade", "Next Best Alternative",
        "Choice 2", "Choice 2 Reason", "Choice 2 % Upgrade", "Next Best Alternative",
        "Choice 3", "Choice 3 Reason", "Choice 3 % Upgrade", "Next Best Alternative",
        "Choice 4", "Choice 4 Reason", "Choice 4 % Upgrade", "Next Best Alternative",
        "Choice 5", "Choice 5 Reason", "Choice 5 % Upgrade", "Next Best Alternative",
    ]
    mythicRaid_rows.append(choicesFileHeaders)
    heroicRaid_rows.append(choicesFileHeaders)
    normalRaid_rows.append(choicesFileHeaders)


    for key in sorted(items.keys()):
        row = [
            key,
            items[key],
            itemSources.get(key, ""),
            itemBosses.get(key, "")
        ]
        for p in players:
            row.append(str(p.sims.get(key, "")))
        output_rows.append(row)


    for item in sorted(items.keys()):
        boss = itemBosses.get(item, "")
        item_source = itemSources.get(item, "")
        choices = item_Choices.get(item, [])
        # Build the row for each difficulty
        if item_source == MYTHIC_RAID_SOURCE:
            row = [boss, item]
            for c in choices:
                row.extend([
                    getattr(c.player, "name", ""),
                    c.candidate_reason,
                    c.item_val,
                    c.next_best_val
                ])
            # Pad to 5 choices if needed
            while len(row) < 22:
                row.extend(["", "", "", ""])
            mythicRaid_rows.append(row)
        elif item_source == HEROIC_RAID_SOURCE:
            row = [boss, item]
            for c in choices:
                row.extend([
                    getattr(c.player, "name", ""),
                    c.candidate_reason,
                    c.item_val,
                    c.next_best_val
                ])
            while len(row) < 22:
                row.extend(["", "", "", ""])
            heroicRaid_rows.append(row)
        elif item_source == NORMAL_RAID_SOURCE:
            row = [boss, item]
            for c in choices:
                row.extend([
                    getattr(c.player, "name", ""),
                    c.candidate_reason,
                    c.item_val,
                    c.next_best_val
                ])
            while len(row) < 22:
                row.extend(["", "", "", ""])
            normalRaid_rows.append(row)

    # EV Sheet
    for source in ev_dictionary:
        for boss in ev_dictionary[source]:
            for player in ev_dictionary[source][boss]:
                ev_rows.append([source, boss, player, ev_dictionary[source][boss][player]])

    #Write to Google Sheets
    service = get_sheets_service()
    SPREADSHEET_ID = '1h7UeLR_XygsUpc1-bFN9wCOFAa5-on43JSZ47XJhO4o'  # Replace with your Google Sheet ID

    # Clear each sheet before writing
    clear_sheet(service, SPREADSHEET_ID, 'amilooted.py')
    clear_sheet(service, SPREADSHEET_ID, 'Mythic Raid Choices')
    clear_sheet(service, SPREADSHEET_ID, 'Heroic Raid Choices')
    clear_sheet(service, SPREADSHEET_ID, 'Normal Raid Choices')
    clear_sheet(service, SPREADSHEET_ID, 'Expected Values')

    write_to_sheet(service, SPREADSHEET_ID, 'amilooted.py', output_rows)
    write_to_sheet(service, SPREADSHEET_ID, 'Mythic Raid Choices', mythicRaid_rows)
    write_to_sheet(service, SPREADSHEET_ID, 'Heroic Raid Choices', heroicRaid_rows)
    write_to_sheet(service, SPREADSHEET_ID, 'Normal Raid Choices', normalRaid_rows)
    write_to_sheet(service, SPREADSHEET_ID, 'Expected Values', ev_rows)

    print(f"Output written to Google Sheets workbook: {SPREADSHEET_ID}")
    print("Press Enter to exit.")
    input()

if __name__ == "__main__":
    main()




