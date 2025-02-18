#Store all droptimizer results for a player in a dict associated with that
#player.
class Player:
    def __init__(self, name, spec, multispec):
        self.name = name
        self.spec = spec
        self.sims = {}
        self.multispec = multispec
        self.normal_bis = BestInSlot()
        self.normal_delta_matrix = {}
        self.heroic_bis = BestInSlot()
        self.heroic_delta_matrix = {}
        self.mythic_bis = BestInSlot()
        self.mythic_delta_matrix = {}
    
    def __repr__(self):
        return f"{self.name} playing {self.spec}"

        
class BestInSlot:
    VALID_SLOTS = [ 
                   "neck", "trinket", "waist", "finger", "off_hand", "shoulder", "main_hand", "back", "feet",
                   "wrist", "head", "hands", "legs", "chest"
                   ]
    
    def __init__(self):
        """Initialize all BiS slots with None (unknown initially)."""
        self.bis_gear = {slot: None for slot in self.VALID_SLOTS}

    def set_bis(self, slot: str, item_name: str):
        """Set the BiS item for a specific slot."""
        if slot not in self.VALID_SLOTS:
            raise ValueError(f"Invalid gear slot: {slot}")
        self.bis_gear[slot] = item_name

    def get_bis(self, slot: str) -> str:
        """Retrieve the BiS item for a given slot."""
        if slot not in self.VALID_SLOTS:
            raise ValueError(f"Invalid gear slot: {slot}")
        return self.bis_gear[slot]

    def __repr__(self):
        """String representation of the BiS gear."""
        return "\n".join([f"{slot}: {item or 'Not Set'}" for slot, item in self.bis_gear.items()])
    
class ItemCandidate:
    def __init__(self, player: Player, item_val: float, item_delta: float, next_best_val: float, candidate_reason: str):
        self.player = player
        self.item_val = item_val
        self.item_delta = item_delta
        self.next_best_val = next_best_val
        self.candidate_reason = candidate_reason
        
    def __repr__(self):
        return f"{self.player} for {self.candidate_reason}, value is {self.item_val}."