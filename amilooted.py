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

import requests
import os
import sys
import time
import datetime
import json

#Substrings that reliably indicate that this is a tier piece.
#This should be the only thing that needs to be updated for new patches,
#unless raidbots changes something about their developer tools.
tiernames = ["Lingering Phantom's",     #Death Knight
             "Kinslayer's",             #Demon Hunter
             "of the Autumn Blaze",     #Druid
             "of Obsidian Secrets",     #Evoker
             "Ashen Predator's",        #Hunter
             "Underlight Conjurer's",   #Mage
             "of the Vermillion Forge", #Monk
             "Heartfire Sentinel's",    #Paladin
             "of the Furnace Seraph",   #Priest
             "Lurking Specter's",       #Rogue
             "of the Cinderwolf",       #Shaman
             "of the Sinister Savant",  #Warlock
             "of the Onyx Crucible"]    #Warrior

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

def tiercheck(itemname):
    for t in tiernames:
        if t in itemname:
            return True
    return False
    
def slot_to_piece(slot):
    return slotdict[slot]

#To avoid adding a mess of disparate tier sets, condense all such things
#into, e.g., "Tier Helm 441"
def tierfilter(itemname, key):
    if tiercheck(itemname):
        #Get the slot from the last part of key.
        #Get the ilvl as the last token in item.
        ilvl = itemname.split()[-1]
        piece = slot_to_piece(key.split("/")[-2])
        return "Tier " + piece + " " + ilvl
    return itemname

#List of all the item names being simmed in anyone's droptimizers.
items = []
def add_to_items(itemname):
    for i in items:
        if i == itemname:
            return
    items.append(itemname)

#List of players with droptimizers.
players = []

#Store all droptimizer results for a player in a dict associated with that
#player.
class Player:
    def __init__(self, name, spec, multispec):
        self.name = name
        self.spec = spec
        self.sims = {}
        self.multispec = multispec



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
    for line in inputdata:
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
            #Ugly: if itemname is a tier piece, don't add it to the list of
            #items just yet.  Instead, we'll be changing itemname on the next
            #pass through this loop before we add it; we need the additional
            #context of the next line to figure out how to do this properly 
            #without hardcoding a lot of names.
            if not tiercheck(itemname):
                add_to_items(itemname)
            continue
        
        key = line.split("\"")[1]
        if tiercheck(itemname):
            itemname = tierfilter(itemname, key)
            add_to_items(itemname)
        gearnames.update({line.split("\"")[1]:itemname})
    
    #XXX: TODO: Sanity-check the input.  Make sure people are simming on
    #Patchwerk instead of HecticAddCleave or DungeonSlice.
    
    
    #Now to start extracting the relevant information from the output.
    #Line 2 of data.csv has baseline DPS in its second column.
    #Further lines have profileset names in first column, new DPS in second.
    baselinedps = float(outputdata[1].split(",")[1])
    for line in outputdata[2:]:
        if line == "":
            continue
        key = line.split(",")[0]
        item = gearnames[key]
        newdps = float(line.split(",")[1])
        percentupgrade = int(1000 * (newdps - baselinedps)/baselinedps) * 0.1
        if item in players[pindex].sims:
            #This means we already added the item to the player's sims at some
            #point, probably because this is a ring or trinket and we simmed it
            #in the first slot before and this is the second slot.  Check to see
            #if this is better; only update if it is.
            if percentupgrade > players[pindex].sims[item]:
                players[pindex].sims.update({item:percentupgrade})
        else:
            players[pindex].sims.update({item:percentupgrade})
    


def grabpastebin(url):
    #Check to see if "raw" is in the url; if so, use it as-is
    #if not, generate the "raw" counterpart.
    realurl = ""
    if "raw" in url:
        realurl = url
    else:
        realurl = "https://pastebin.com/raw/" + url.split("/")[-1].strip()
    
    data = requests.get(realurl).text.split("\n")
    for i in range(len(data)):
        data[i] = data[i].strip()
    
    charname = data[0]
    spec = data[1].split()[0]
    
    pindex = add_player(charname, spec)
    
    #Fortunately, we don't have to do as much cursed stuff with figuring out
    #item names as we did with raidbots.
    itemname = ""
    ilvl = ""
    for line in data[3:]:
        #Filter out the junk lines.
        if "Upgrades" in line:
            continue
        if line == "Standard Edition":
            continue
        if "Find your next upgrade!" in line:
            continue
        if line == "img":
            continue
        if line == "QE Live":
            continue
        #Every line that makes it through this filter should be an item name,
        #or an ilvl, or a percentage.  Ilvls will be three digits, percentages
        #will have a %.
        if "%" in line:
            players[pindex].sims.update({itemname + " " + ilvl:line[1:-1]})
        elif line == "+0":
            players[pindex].sims.update({itemname + " " + ilvl:"0"})
        elif len(line) == 3:
            ilvl = line
        else:
            itemname = line
    
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
            if "raidbots.com" in line:
                try:
                    print("Checking " + line.split()[-1])
                    grabraidbots(line.split()[-1])
                except:
                    print("ERROR on line " + str(linenum) + ":")
                    print(line.strip())
                    print("Either this line was malformed or the sim has expired.")
                    print("Press Enter to close the program, or enter 'skip' to skip.")
                    if "skip" in input().lower():
                        continue
                    sys.exit(1)
            if "pastebin.com" in line:
                try:
                    print("Checking " + line.split()[-1])
                    grabpastebin(line.split()[-1])
                except:
                    print("ERROR on line " + str(linenum) + ":")
                    print(line.strip())
                    print("Either this line was malformed or the sim has expired.")
                    print("Press Enter to close the program, or enter 'skip' to skip.")
                    if "skip" in input().lower():
                        continue
                    sys.exit(1)
    else:
        spreadsheeturl = "https://docs.google.com/spreadsheets/d/1Naqk3fXF0z316UQJ5SVVhaZV8CdS1LZoZTVjwJ_RLho/export?format=csv"
        try:
            spreadsheetdata = requests.get(spreadsheeturl).text.split("\n")
        except:
            print("Could not access URL:")
            print(spreadsheeturl)
            print("Press Enter to close the program.")
            sys.exit(1)
        #Check all the cells in the spreadsheet.  If any of them are raidbots links, run grabraidbots on them.
        print(spreadsheetdata)
        for line in spreadsheetdata:
            cells = line.split(",")
            #All entries from this download have quotes surrounding them.
            for cell in cells:
                if "raidbots.com" in cell:
                    try:
                        print("Checking " + cell)
                        grabraidbots(cell)
                    except:
                        print("ERROR with link: " + cell)
                        print("Either this link was malformed or the sim has expired.")
                if "pastebin.com" in cell:
                    try:
                        print("Checking " + cell)
                        grabpastebin(cell)
                    except:
                        print("ERROR with link: " + cell)
                        print("Either this link was malformed or the pastebin has expired.")

        
        
            
    outfilename = "droptimizers-" + \
                  datetime.datetime.fromtimestamp( \
                  time.time()).strftime("%d-%m-%Y") + ".csv"

    output = open(outfilename,"w")
    
    #First, one row with the player names and an initial blank entry.
    #If someone only submitted sims for one spec, no need to specify specs
    #on this line.
    #If they submitted sims for several specs (e.g., both Arcane and Frost
    #Mage), then we have separate columns for the specs and we should name them.
    for p in players:
        if p.multispec:
            output.write(","+p.name+" ("+p.spec+")")
        else:
            output.write(","+p.name)

    output.write("\n")
    #Then, for each item, a row with that item's name and the appropriate sim.
    items.sort()
    for item in items:
        #Some items have commas in them.  Because we're using commas as
        #separators in this spreadsheet, they must be removed in the output.
        output.write(item.replace(",",""))
        for p in players:
            if item in p.sims:
                output.write("," + str(p.sims[item]))
            else:
                output.write(",")
        output.write("\n")













if __name__ == "__main__":
    main()




