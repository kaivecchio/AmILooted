from models.player import Player

players: list[Player] = []

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
        pindex = len(players) - 1  # Ensure pindex is set for new player

    return pindex

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