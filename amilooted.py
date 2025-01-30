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
try:
    import requests
except:
    print("Requests library not installed!  Installing...")
    subprocess.call([sys.executable, "-m", "pip", "install", "requests"])
    print("Requests should be installed; this should only happen once.")
    import requests

try:
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
except:
    print("Selenium library not installed!  Installing...")
    subprocess.call([sys.executable, "-m", "pip", "install", "selenium"])
    print("Selenium should be installed; this should only happen once.")
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By


#Substrings that reliably indicate that this is a tier piece.
#This should be the only thing that needs to be updated for new patches,
#unless raidbots changes something about their developer tools.
tiernames = ["Exhumed Centurion's",         #Death Knight
             "of the Hypogeal Nemesis",     #Demon Hunter
             "of the Greatlynx",            #Druid
             "of the Destroyer",            #Evoker
             "Lightless Scavenger's",       #Hunter
             "of Violet Rebirth",           #Mage
             "Gatecrasher's",               #Monk
             "Entombed Seraph's",           #Paladin
             "Living Luster's",             #Priest
             "K'areshi Phantom's",          #Rogue
             "of the Forgotten Reservoir",  #Shaman
             "Hexflame Coven's",            #Warlock
             "Warsculptor's"]               #Warrior

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


#Try to replace tier names with, e.g., "Tier Helm 441", without knowing
#the actual slot.  This might be less reliable than tierfilter, but I'd rather
#not resort to hardcoding every piece name just yet.
def tierfilter_qe(itemname):
    if tiercheck(itemname):
        if "helm" in itemname.lower() or \
           "horns" in itemname.lower() or \
           "hood" in itemname.lower() or \
           "bough" in itemname.lower() or \
           "crown" in itemname.lower() or \
           "face" in itemname.lower() or \
           "cowl" in itemname.lower() or \
           "cover" in itemname.lower() or \
           "mask" in itemname.lower() or \
           "gaze" in itemname.lower() or \
           "scowl" in itemname.lower() or \
           "casque" in itemname.lower() or \
           "coif" in itemname.lower() or \
           "chronocap" in itemname.lower() or \
           "hatsuburi" in itemname.lower() or \
           "barbute" in itemname.lower() or \
           "crest" in itemname.lower() or \
           "jaws" in itemname.lower() or \
           "domeplate" in itemname.lower() or \
           "noetic" in itemname.lower() or \
           "skull" in itemname.lower() or \
           "emptiness" in itemname.lower() or \
           "semblance" in itemname.lower() or \
           "galea" in itemname.lower() or \
           "eye" in itemname.lower() or \
           "impalers" in itemname.lower() or \
           "visage" in itemname.lower():
            return "Tier Helmet"
        if "pauld" in itemname.lower() or \
           "shoulder" in itemname.lower() or \
           "mantle" in itemname.lower() or \
           "wings" in itemname.lower() or \
           "trophy" in itemname.lower() or \
           "aurora" in itemname.lower() or \
           "spines" in itemname.lower() or \
           "devotion" in itemname.lower() or \
           "erpads" in itemname.lower() or \
           "skewers" in itemname.lower() or \
           "horned memento" in itemname.lower() or \
           "wisdom" in itemname.lower() or \
           "sandbrace" in itemname.lower() or \
           "finest hunt" in itemname.lower() or \
           "metronomes" in itemname.lower() or \
           "hopeful effigy" in itemname.lower() or \
           "enduring effigy" in itemname.lower() or \
           "ailettes" in itemname.lower() or \
           "companions" in itemname.lower() or \
           "spikes" in itemname.lower() or \
           "concourse" in itemname.lower() or \
           "plumes" in itemname.lower() or \
           "taxidermy" in itemname.lower() or \
           "dominion" in itemname.lower() or \
           "beacons" in itemname.lower() or \
           "altar" in itemname.lower() or \
           "maw of the greatlynx" in itemname.lower() or \
           "fumaroles" in itemname.lower() or \
           "amice" in itemname.lower():
            return "Tier Pauldrons"
        if "vest" in itemname.lower() or \
           "plackart" in itemname.lower() or \
           "chest" in itemname.lower() or \
           "hauberk" in itemname.lower() or \
           "cuirass" in itemname.lower() or \
           "brigandine" in itemname.lower() or \
           "command" in itemname.lower() or \
           "adornments" in itemname.lower() or \
           "casket" in itemname.lower() or \
           "binding" in itemname.lower() or \
           "raiment" in itemname.lower() or \
           "patchwork" in itemname.lower() or \
           "warplate" in itemname.lower() or \
           "cassock" in itemname.lower() or \
           "harness" in itemname.lower() or \
           "razorhide" in itemname.lower() or \
           "plastron" in itemname.lower() or \
           "breast" in itemname.lower() or \
           ("coat" in itemname.lower() and not "coattails" in itemname.lower())or \
           "nexus wraps" in itemname.lower() or \
           "gatecrasher's gi" in itemname.lower() or \
           "hide of the" in itemname.lower() or \
           "scales of the" in itemname.lower() or \
           "robe" in itemname.lower():
            return "Tier Chest"
        if "grips" in itemname.lower() or \
           "gauntlet" in itemname.lower() or \
           "hand" in itemname.lower() or \
           "claws" in itemname.lower() or \
           "skinners" in itemname.lower() or \
           "glove" in itemname.lower() or \
           "fists" in itemname.lower() or \
           "protectors" in itemname.lower() or \
           "grasp" in itemname.lower() or \
           "thorns" in itemname.lower() or \
           "talons" in itemname.lower() or \
           "clawguards" in itemname.lower() or \
           "touch" in itemname.lower() or \
           "crushers" in itemname.lower() or \
           "castigation" in itemname.lower() or \
           "mitts" in itemname.lower() or \
           "sleeves" in itemname.lower() or \
           "eviscerators" in itemname.lower() or \
           "rippers" in itemname.lower() or \
           "knuckles" in itemname.lower():
            return "Tier Gloves"
        #Check "legg" instead of "leg" because "legendary" might be part of an
        #item name at some point, but this will catch "leggings" and "legguards"
        if "legg" in itemname.lower() or \
           "legpl" in itemname.lower() or \
           "schynbalds" in itemname.lower() or \
           "pant" in itemname.lower() or \
           "chausses" in itemname.lower() or \
           "poleyns" in itemname.lower() or \
           "trousers" in itemname.lower() or \
           "faulds" in itemname.lower() or \
           "breeches" in itemname.lower() or \
           "tights" in itemname.lower() or \
           "blazewraps" in itemname.lower() or \
           "greaves" in itemname.lower() or \
           "waders" in itemname.lower() or \
           "burdens" in itemname.lower() or \
           "cuisses" in itemname.lower() or \
           "kilt" in itemname.lower() or \
           "tassets" in itemname.lower() or \
           "sarong" in itemname.lower() or \
           "stalkings" in itemname.lower() or \
           "coattails" in itemname.lower() or \
           "braies" in itemname.lower():
            return "Tier Pants"
        print("ERROR: Could not resolve " + itemname + " properly!  Left as-is.")
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
        percentupgrade = int(10000 * (newdps - baselinedps)/baselinedps) * 0.01
        if item in players[pindex].sims:
            #This means we already added the item to the player's sims at some
            #point, probably because this is a ring or trinket and we simmed it
            #in the first slot before and this is the second slot.  Check to see
            #if this is better; only update if it is.
            if percentupgrade > players[pindex].sims[item]:
                players[pindex].sims.update({item:percentupgrade})
        else:
            players[pindex].sims.update({item:percentupgrade})
    


def grabqe(url,charname):
    #QE Live interoperability sucks, so this is really hacky.
    #We can't just do a wget on the URL, because the information we care about
    #is encoded in 7 MB of autogenerated javascript.
    #Load the page in Firefox to run the javascript, and then get the page
    #source after that's been run.
    driver = webdriver.Firefox()
    driver.get(url)
    time.sleep(5) #Delay to let the javascript run
    pagesource = driver.page_source
    driver.close()
    
    #Munge the page source for the information we need.
    #There will be a smattering of "ilvl=" substrings; each will be followed by
    #a three-digit item level.
    #index+5:index+8 gives what we want.
    #XXX: A few expansions from now, ilvl may hit four digits if there isn't
    #another ilvl squish.  This seems unlikely to matter, if only because
    #last time this happened only legendaries were ilvl 1000 (everything
    #else capped at 985), and this was immediately followed by the squish.
    #There will also be a smattering of 'justify-content: center;">'
    #substrings.  Each of these will be followed either by an item name or
    #by the percentage upgrade.  We want the string from there up until the
    #next <.
    #index+26:index+(sourcestring[index+26:].search("<"))+26
    #Since all of these are in order, we can do a couple of passes through
    #the damn thing and assemble the information afterward.
    
    ilvls = []
    itemnames = []
    upgradepercent = []
    
    
    sourcecopy = pagesource
    while True:
        i = pagesource.find("ilvl=")
        
        if i == -1:
            break
        else:
            ilvls.append(pagesource[i+5:i+8])
            pagesource = pagesource[i+8:]
    
    searchindex = 0
    tempresults = []
    while True:
        i = sourcecopy.find('justify-content: center;">')
        
        if i == -1:
            break
        else:
            tempresults.append(sourcecopy[i+26:i+26+sourcecopy[i+26:].find("<")])
            sourcecopy = sourcecopy[i+26:]
    
    itemnames = tempresults[::2]
    upgradepercent = tempresults[1::2]

    #For raidbots droptimizers, we can get the spec directly.
    #QE Live not so much; we can't even figure out the player's name
    #from the link.
    #We can figure out the class by cross-referencing the tier pieces
    #with the set strings, but if the class is Priest we still don't know if
    #it's Holy or Discipline.
    #Best we can do there is "Healer" spec, and if multiple sims are submitted
    #include both results with a slash.
    spec = ""
    for item in itemnames:
        if tiernames[2] in item:
            spec = "Restoration"
            break
        if tiernames[3] in item:
            spec = "Preservation"
            break
        if tiernames[6] in item:
            spec = "Mistweaver"
            break
        if tiernames[7] in item:
            spec = "Holy"
            break
        if tiernames[8] in item:
            spec = "Healer"
            break
        if tiernames[10] in item:
            spec = "Restoration"
            break

    for i in range(len(itemnames)):
        itemnames[i] = tierfilter_qe(itemnames[i])
    
    
    for i in range(len(ilvls)):
        itemnames[i] += " " + ilvls[i]
        add_to_items(itemnames[i])
    
    #Trim leading +, trailing % from QE's prettyprinting
    for i in range(len(upgradepercent)):
        if upgradepercent[i] == "+0":
            upgradepercent[i] = "0"
        else:
            upgradepercent[i] = upgradepercent[i][1:-1]
    
    
    
    pindex = add_player(charname, spec)
    
    for i in range(len(itemnames)):
        if spec == "Healer" and itemnames[i] in players[pindex].sims:
            tempval = players[pindex].sims[itemnames[i]]
            players[pindex].sims.update({itemnames[i]:tempval+"/"+upgradepercent[i]})
        else:
            players[pindex].sims.update({itemnames[i]:upgradepercent[i]})


def graburl(url,name):
    try:
        if "raidbots.com" in url:
            print("Checking " + url)
            grabraidbots(url)
        if "questionablyepic.com" in url:
            print("Checking " + url)
            grabqe(url,name)
    except:
        print("ERROR with URL:")
        print(url)
        print("Either this was malformed or the sim has expired.")

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
            graburl(line.split()[-1],line.split(":")[0])

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
                    graburl(d,name)

        
    #Sort players alphabetically, and by role.  Tanks first, then DPS, then
    #healers.
    #Sort alphabetically first so that the role sorting actually works.
    players.sort(key=lambda p: p.name)
    players.sort(key=rolekey)
            
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

    print("Output written to " + outfilename + ".")
    print("Press Enter to exit.")
    input()











if __name__ == "__main__":
    main()




