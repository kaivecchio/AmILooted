#Substrings that reliably indicate that this is a tier piece.
#This should be the only thing that needs to be updated for new patches,
#unless raidbots changes something about their developer tools.
tiernames = ["Cauldron Champion's",         #Death Knight
             "Fel-Dealer's",                #Demon Hunter
             "of Reclaiming Blight",        #Druid
             "Opulent Treasurescale's",     #Evoker
             "Tireless Collector's",        #Hunter
             "Aspectral Emissary's",        #Mage
             "Ageless Serpent's",           #Monk
             "Aureate Sentry's",            #Paladin
             "Confessor's Unshakable",      #Priest
             "Spectral Gambler's",          #Rogue
             "Gale Sovereign's",            #Shaman
             "Spliced Fiendtrader's",       #Warlock
             "Enforcer's Backalley"]        #Warrior


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
           "domeplate" in itemname.lower() or \
           "noetic" in itemname.lower() or \
           "skull" in itemname.lower() or \
           "emptiness" in itemname.lower() or \
           "semblance" in itemname.lower() or \
           "galea" in itemname.lower() or \
           "eye" in itemname.lower() or \
           "impalers" in itemname.lower() or \
           "pledge" in itemname.lower() or \
           "halo" in itemname.lower() or \
           "transcendence" in itemname.lower() or \
           "mane" in itemname.lower() or \
           "branches" in itemname.lower() or \
           "visor" in itemname.lower() or \
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
           "roaring will" in itemname.lower() or \
           "hunted heads" in itemname.lower() or \
           "radiance" in itemname.lower() or \
           "screamplate" in itemname.lower() or \
           "zephyrs" in itemname.lower() or \
           "vents" in itemname.lower() or \
           "servants" in itemname.lower() or \
           "jaws" in itemname.lower() or \
           "reavers" in itemname.lower() or \
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
           ("coat" in itemname.lower() and not "coattails" in itemname.lower() and not "petticoat" in itemname.lower())or \
           "nexus wraps" in itemname.lower() or \
           "gatecrasher's gi" in itemname.lower() or \
           "hide of the" in itemname.lower() or \
           "scales of the" in itemname.lower() or \
           "encasement" in itemname.lower() or \
           "battlegear" in itemname.lower() or \
           "ribcage" in itemname.lower() or \
           "gown" in itemname.lower() or \
           "inked coils" in itemname.lower() or \
           "soul engine" in itemname.lower() or \
           "tunic" in itemname.lower() or \
           "robe" in itemname.lower():
            return "Tier Chest"
        if "grips" in itemname.lower() or \
           "gauntlet" in itemname.lower() or \
           "hand" in itemname.lower() or \
           "claws" in itemname.lower() or \
           "skinners" in itemname.lower() or \
           "glove" in itemname.lower() or \
           "fist" in itemname.lower() or \
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
           "gold-counters" in itemname.lower() or \
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
           "moccasins of reclaiming blight" in itemname.lower() or \
           "petticoat" in itemname.lower() or \
           "braies" in itemname.lower():
            return "Tier Pants"
        print("ERROR: Could not resolve " + itemname + " properly!  Left as-is.")
    return itemname