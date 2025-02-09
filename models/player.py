
#Store all droptimizer results for a player in a dict associated with that
#player.
class Player:
    def __init__(self, name, spec, multispec):
        self.name = name
        self.spec = spec
        self.sims = {}
        self.multispec = multispec