"""
Main processing module
Loads a given file, parses it in reverse via a regex search.
Module assumes input file is small enough to fit in main memory.
"""

from sys import argv, exit
import re, WhoIs, time

patterns = (    r'\S#0000000042000009.+,(?P<TS>\d+)](?P<name>.+) hit (?P<target>.+) for (?P<amount>\d+) points of (.+) damage.$',                                # 0 Pet hit + add timestamp
                r"\S#0000000042000009.+,(?P<TS>\d+)](?P<name>.+) hit (?P<target>.+) for (?P<amount>\d+) points of (.+) damage\.\s*Critical hit.$",               # 1 Pet critical hit + add timestamp
                r"(?P<TS>\d+)]You hit (?P<target>.+) with nanobots for (?P<amount>.+) points of .+ damage\.$",                                                   # 2 You hit nano dmg..
                r"(?P<TS>\d+)](?P<target>.+) was attacked with nanobots from (?P<name>.+) for (?P<amount>\d+) points of (.+) damage\.$",                         # 3 Nano dmg
                r"(?P<TS>\d+)]You were attacked with nanobots from (?P<name>.+) for (?P<amount>\d+) points of (.+) damage\.$",                                   # 4 Someone hit you with a nano
                r"(?P<TS>\d+)](?P<name>.+) hit (?P<target>.+) for (?P<amount>\d+) points of (?P<type>.+) damage\.$",                                             # 5 Normal hit<-
                r"(?P<TS>\d+)](?P<name>.+)'s reflect shield hit (?P<target>.+) for (?P<amount>\d+) points of damage\.$",                                         # 6 Reflect shield
                r"You healed (.+) for (\d+) points of health\.$",                                                                                                # 7 You healed someone
                r"(?P<TS>\d+)](?P<name>.+) hit (?P<target>.+) for (?P<amount>\d+) points of (.+) damage\.\s*Critical hit.$",                                     # 8 Critical hit
                r"(?P<TS>\d+)](?P<name>.+)'s damage shield hit (?P<target>.+) for (?P<amount>\d+) points of damage\.$",                                          # 9 Damage shield
                r"(?P<TS>\d+)]Your damage shield hit (?P<target>.+) for (?P<amount>\d+) points of damage\.$",                                                    # 10 Damage shield
                r"(?P<TS>\d+)]Your reflect shield hit (?P<target>.+) for (?P<amount>\d+) points of damage\.$",                                                   # 11 Reflect shield
                r"You gained (?P<amount>\d+) points of Shadowknowledge\.$",                                                                                      # 12 Got SK
                r"(?P<amount>\d+) of your (.+) were allocated to your personal research\.",                                                                      # 13 Research ( .... to your personal research.<br> ) because bug.
                r"You gained (?P<amount>\d+) new Alien Experience Points\.$",                                                                                    # 14 Got AXP
                r"You received (?P<amount>\d+) xp\.$",                                                                                                           # 15 Got XP
                r"(.+) tried to hit you, but missed!$",                                                                                                          # 16 You evaded a hit
                r"You got healed by (?P<name>.+) for (?P<amount>\d+) points of health\.$",                                                                       # 17 You got healed
                r"\S#0000000040000001.+,(\d+)](?P<name>.+) attacked by (?P<target>.+).$",                                                                        # 18 Ignore mobs attacking our pets!
                r"\S#0000000041000000.+,(\d+)](.+)'s pet, (?P<name>.+): .*",                                                                                     # 19 Unless the mob is now our charm!
                r"\S#0000000041000001.+,(\d+)](?P<target>.+)'s pet, (?P<name>.+): .*",                                                                           # 20 Someone else's pet
                r"\S#0000000042000009.+,(?P<TS>\d+)](?P<name>.+) hit (?P<target>.+) for (?P<amount>\d+) points of (.+) damage\.\s*Glancing hit.$",               # 21 Pet glancing hit + add timestamp 
                r"(?P<TS>\d+)](?P<name>.+) hit (?P<target>.+) for (?P<amount>\d+) points of (.+) damage\.\s*Glancing hit.$"                                      # 22, Glancing hit
                )

# Pets with level restrictions, for limiting pets to players by level
# Care must be taken, as whois database may be outdated!
restrictedPets = {
    'Bureaucrat':(
    (160, "Carlita Desposito"),
    (205, "Corporate Guardian"),
    (215, "CEO Guardian"),
    (220,"Carlo Pinnetti")),
    'Engineer':(
    (100, "Prototype Predator M-30"),
    (150, "Predator M-30"),
    (175, "Upgraded Predator M-30"),
    (175, "Slayerdroid Annihilator"),
    (203, "Advanced Predator M-30"),
    (205, "Devastator Drone"),
    (207, "Semi-Sentient Predator M-30"),
    (209, "Battlefield Devastator Drone"),
    (211, "Military-Grade Predator M-30"),
    (213, "Fieldsweeper Devastator Drone"),
    (215, "Marauder M-45"),
    (215, "Ravening M-60"),
    (217, "Desolator Assault Drone"),
    (219, "Military-Grade Marauder M-45"),
    (220, "Widowmaker Battle Drone")),
    'Meta-Physicist':(
    (25, "Praetorian Legionnaire"),
    (135, "Tormented Revenant"),
    (150, "Biazu the Vile"),
    (175, "Urolok the Rotten"),
    (201, "Ettu the Cursed"), # Bugged in 18.8.2, should not be 201, but possibly 190-195
    (201, "Zhok the Abomination"),
    (220, "The Rihwen")),
    'Trader':(
    (220, "VP - Marketing"),
    (220, "VP - Public Relations"),
    (220, "VP - Operations"),
    (220, "VP - Internal Affairs"))
}

# Default pet names, for connecting pets with professions/players
cratPets = ("Basic Worker-Droid",       "Limited Worker-Droid",           "Faithful Worker-Droid",           "Advanced Worker",                 "Supervisor-Grade Worker-Droid",           "Executive-Grade Worker-Droid",           "Director-Grade Worker-Droid",
            "Basic Helper-Droid",       "Limited Helper-Bot",             "Faithful Helper-Droid",           "Advanced Helper",                 "Supervisor-Grade Helper-Droid",           "Executive-Grade Helper-Droid",           "Director-Grade Helper-Droid",
            "Basic Attendant-Droid",    "Limited Attendant-Droid",        "Faithful Attendant-Droid",        "Advanced Attendant-Droid",        "Supervisor-Grade Attendant-Droid",        "Executive-Grade Attendant-Droid",        "Director-Grade Attendant-Droid",
            "Basic Assistant-Droid",    "Limited Assistant-Droid",        "Faithful Assistant-Droid",        "Advanced Assistant-Droid",        "Supervisor-Grade Assistant-Droid",        "Executive-Grade Assistant-Droid",        "Director-Grade Assistant-Droid",
            "Basic Aide-Droid",         "Limited Aide-Droid",             "Faithful Aide-Droid",             "Advanced Aide-Droid",             "Supervisor-Grade Aide-Droid",             "Executive-Grade Aide-Droid",             "Director-Grade Aide-Droid",
            "Basic Secretary-Droid",    "Limited Secretary-Droid",        "Faithful Secretary-Droid",        "Advanced Secretary-Droid",        "Supervisor-Grade Secretary-Droid",        "Executive-Grade Secretary-Droid",        "Director-Grade Secretary-Droid",
            "Basic Administrator",      "Limited Administrator-Droid",    "Faithful Administrator-Droid",    "Advanced Administrator-Droid",    "Supervisor-Grade Administrator-Droid",    "Executive-Grade Administrator-Droid",    "Director-Grade Administrator-Droid",
            "Basic Minion",             "Limited Minion",                 "Faithful Minion",                 "Advanced Minion",                 "Supervisor-Grade Minion",                 "Executive-Grade Minion",                 "Director-Grade Minion",
            "Basic Bodyguard",          "Limited Bodyguard",              "Faithful Bodyguard",              "Advanced Bodyguard",              "Supervisor-Grade Bodyguard",              "Executive-Grade Bodyguard",              "Director-Grade Bodyguard",
            "Carlita Desposito",        "Corporate Guardian",             "CEO Guardian",                    "Carlo Pinnetti"
            )

engPets = ("Feeble Automaton",           "Patchwork Automaton",             "Lesser Automaton",                 "Inferior Automaton",         "Flawed Automaton",               "Common Automaton",                "Automaton",        "Upgraded Automaton",              "Advanced Automaton",       "Perfected Automaton",       "Semi-Sentient Automaton",
           "Feeble Android",             "Patchwork Android",               "Lesser Android",                   "Inferior Android",           "Flawed Android",                 "Common Android",                  "Android",          "Upgraded Android",                "Advanced Android",         "Perfected Android",         "Semi-Sentient Android",
           "Feeble Gladiatorbot",        "Patchwork Gladiatorbot",          "Lesser Gladiatorbot",              "Inferior Gladiatorbot",      "Flawed Gladiatorbot",            "Common Gladiatorbot",             "Gladiatorbot",     "Upgraded Gladiatorbot",           "Advanced Gladiatorbot",    "Perfected Gladiatorbot",    "Semi-Sentient Gladiatorbot",
           "Feeble Guardbot",            "Patchwork Guardbot",              "Lesser Guardbot",                  "Inferior Guardbot",          "Flawed Guardbot",                "Common Guardbot",                 "Guardbot",         "Upgraded Guardbot",               "Advanced Guardbot",        "Perfected Guardbot",        "Semi-Sentient Guardbot",
           "Feeble Warbot",              "Patchwork Warbot",                "Lesser Warbot",                    "Inferior Warbot",            "Flawed Warbot",                  "Common Warbot",                   "Warbot",           "Upgraded Warbot",                 "Advanced Warbot",          "Perfected Warbot",          "Semi-Sentient Warbot",          "Military-Grade Warbot",
           "Feeble Warmachine",          "Patchwork Warmachine",            "Lesser Warmachine",                "Inferior Warmachine",        "Flawed Warmachine",              "Common Warmachine",               "Warmachine",       "Upgraded Warmachine",             "Advanced Warmachine",      "Perfected Warmachine",      "Semi-Sentient Warmachine",      "Military-Grade Warmachine",
           "Decommissioned Wardroid",    "Reactivated Wardroid",            "Semi-Sentient Wardroid",
           "Slayerdroid Protector",      "Slayerdroid Warden",              "Slayerdroid Sentinel",             "Slayerdroid Guardian",       "Slayerdroid Annihilator",
           "Devastator Drone",           "Battlefield Devastator Drone",    "Fieldsweeper Devastator Drone",    "Desolator Assault Drone",    "Widowmaker Battle Drone",
           "Prototype Predator M-30",    "Predator M-30",                   "Upgraded Predator M-30",           "Advanced Predator M-30",     "Semi-Sentient Predator M-30",    "Military-Grade Predator M-30",    "Marauder M-45",    "Military-Grade Marauder M-45",    "Ravening M-60"
           )

# In 18.7 MP pets became scalable, with simplified names, Ex. Fiend -> Metaphysical Demon, Transcendent Enmity Personification -> Enmity Personification
mpPets = ("Anger Manifestation",    "Fury Externalization",    "Rage Materialization",    "Wrath Incarnation",    "Frenzy Embodiment",    "Enmity Personification",
          "Praetorian Legionnaire",    "Tormented Revenant",
          "Metaphysical Demon",
          "Biazu the Vile",    "Urolok the Rotten",    "Ettu the Cursed",    "Zhok the Abomination",    "The Rihwen"
          )

tradPets = ("VP - Marketing",    "VP - Public Relations",    "VP - Operations",    "VP - Internal Affairs"
             )

badNames = ("Guard",                 "Fanatic",                "Bartender",                "Cultist")
allPets = cratPets + engPets + mpPets +tradPets


def getMatch(data):
    """
    @param data: One line of data from an AO logfile
    @return: Dictionary with (some of) [name, target, amount, type, TS, pattern]
    Performs a regex extract on the given line.
    Returns None upon no hit (not an error) 
    """

    i = 0
    output = {}
    for pat in patterns:
        currStamp = 0

        match = re.search(pat, data, re.I) # Case insensitive, greedy

        if match != None:
            try: output["name"] = match.group("name")
            except: pass

            try: output["target"] = match.group("target")
            except: pass

            try: output["amount"] = match.group("amount")
            except: pass

            try: output["type"] = match.group("type")
            except: pass

            try: output["TS"] = int(match.group("TS"))
            except: output["TS"] = 0

            output["pattern"] = i

            return output

        i += 1

    # Trash data, such as "logging out, 30 second timer.."
    return None


class DataParser():
    def __init__(self, selfname, dimension, allowMobs = False):
        self.globData = {}
        self.globStats = {"TOTALHITS": 0, "TOTALDMG": 0, "TOTALNHITS":0}
        self.globStats["?Prof"] = {'Adventurer':0, 'Agent':0, 'Bureaucrat':0, 'Doctor':0, 'Enforcer':0, 'Engineer':0, 'Fixer':0, 'Keeper':0, 'Martial Artist':0, 'Meta-Physicist':0, 'Nano-Technician':0, 'Shade':0, 'Soldier':0, 'Trader':0, 'Unknown':0}
        self.globStats["xp"] = {"SK":0, "Research":0, "AXP":0, "XP":0}
        self.globData["?Tanks"] = {}

        #self.isPlayer = r"^[A-Z][a-z]{3,}[a-z]*[0-9]*$"
        self.isPlayer = r"^[A-Z][a-z]{3,}[a-z]*[0-9]*(-\d+)?$"
        self.w = WhoIs.WhoIs(dimension, True)

        # Info about the person parsing
        self.dim = dimension
        self.selfname = selfname
        name, prof, level = self.w.whois(selfname, dimension)
        if prof == 'Bureaucrat': self.isSelfCrat = True
        else: self.isSelfCrat = False

        # Time period, must be updated externally
        self.period = []
        self.__petIgnores = {}          # NOT pets
        self.__petExceptions = {}       # Guaranteed pets
        self.allowMobs = allowMobs

    def isMyPet(self, petname):
        return petname in self.__petExceptions

    # Add experience/axp/xp/research
    def addXP(self, amount, type):
        amount = int(amount)
        self.globStats["xp"][type] += amount

    def petException(self, name):
        """Pets excempt from the petIgnores list"""
        self.__petExceptions[name] = 1

    def isPetOther(self, pet):
        """Returns a string (or None) of the pets owner"""
        try: return self.globData[pet]["owner"]
        except: return None

    def petAssignOther(self, pet, owner):
        """Assigns a pet to another player"""

        # Make sure the pet exists
        if not pet in self.globData:
            self.initToon(pet)

        # Check if it already has an owner, if so, skip. (CONFLICT?)
        co = None
        try: co = self.globData[pet]["owner"]
        except KeyError:
            self.globData[pet]["owner"] = owner
            print """[Proces.] Pet "%s" now tied to player "%s" """ % (pet, owner)
            return

        if co != owner:
            print """[Proces.] Warning: Pet "%s" already had owner "%s", can't assign to "%s" """ % (pet, co, owner)
        else:
            print """[Proces.] Info: Pet "%s" already had the same owner (%s) """ % (pet, owner)

    def petBan(self, name):
        """Pets that are banned from dataset (not really your pets)"""
        self.__petIgnores[name] = 1

    def isCharmedMob(self, name, target):
        # Lets check if this is a charm
        # 1. Detect if the attacker is a player -> Fail
        # 2. Detect if its attacking a pet     --> Fail
        # 3. Detect if its attacking a player  --> Fail
        # 4. Check WHOIS to verify target not player
        # 5. If above checks succeded, it's a charm!

        # If its attacking one of our beloved pets, it can't possibly be a charm!
        if target in mpPets or target in cratPets or target in engPets or target in tradPets:
            return False

        # Attacking the logger, not caught by isPlayer
        if target == "?You" or name == "?You":
            return False

        # Check if the attacker has a player name, if so, it's not a charm.
        if re.match(self.isPlayer, name):
            return False

        # Check if it's attacking a player, if so: Fail!
        if re.match(self.isPlayer, target):
            return False

        # Check whois to see if its attacking a player (double-check)
        # If its a player, FAIL
        if self.w.whois(target, self.dim)[0] != "Mob?":
            return False

        # All checks passed
        return True


    def addGotHeal(self, healer, amount):
        pass

    def addDidHeal(self, healer, amount):
        pass

    # Initialize a new toon into the data dictionary
    def initToon(self, name):
        init = {}
        init["reflect"]       = 0
        init["dmgShield"]     = 0
        init["dmg"]           = 0
        init["hits"]          = 0
        init["critAmount"]    = 0
        init["critHits"]      = 0
        init["glanceAmount"]  = 0
        init["glanceHits"]    = 0
        init["nano"]          = 0
        init["nanohits"]      = 0
        init["pets"]          = 0
        init["highnum"]       = 0
        init["lownum"]        = 0
        init["hightype"]      = "?"
        init["lowtype"]       = "?"
        init["spec"]          = {}
        init["specdmg"]       = {}
        init["whois"]         = ("Mob?", "?", 0)    # Wanna store it when passing data to UI
                                                    # Avoids calling whois in too many threads

        self.globData[name] = init

    def isBadPet(self, petname):
        if petname in self.__petExceptions: return False    # Marked as safe
        if petname in self.__petIgnores: return True           # Marked as bad
        return False                                        # No info

    def addDamage(self, name, target, amount, type = "Unknown", selfPet = False):
        isCharm = False
        isPet = False

        if amount == "1" and type == "nano": return # Ignore mongo, etc
        if name == "Someone": return                # Can't be assigned to anyone

        # If this is a pet, set the damage dealer as self.
        # If this is a charm, also store the {..?}
        # Note: selfPet and isPet are distinct pet types, as "isPet" is of unknown owner.
        if selfPet:
            # Crats, detect charmed "selfpets"
            if not name in allPets and name != self.selfname and self.isSelfCrat: # Charms renamed to self, are pets. 
                charmName = name
                isCharm = True
                #print "Detected %s as a charmed pet" % name

            # Detect invalid pet damage (pet hit by enemy)
            # Debug output only!
            if not name in allPets and name != self.selfname:
                if self.isBadPet(name):
                    #print "REMOVED: selfpet '%s' is bad data (attacking %s)" % (name, target)
                    return

            # if selfPet:
            name = "?You"
            isPet = True

        # Correct the 'You' to internal '?You'
        if name == "You": name = "?You"
        if target.lower() == "you":
            target = "?You"

        # List of specials for type comparison
        amount = int(amount)
        specials = ('Backstab', 'Full Auto', 'Brawling', 'Burst', 'Fast Attack', 'Sneak Attack', 'Dimach', 'Fling Shot', 'Aimed Shot')

        # ######################    
        # Deal with pets here
        # Skip charm if its already detected
        if name in mpPets: isPet = True
        elif name in cratPets: isPet = True
        elif name in engPets: isPet = True
        elif name in tradPets: isPet = True
        elif not isCharm: isCharm = self.isCharmedMob(name, target)

        # Record tanking stats
        if re.match(self.isPlayer, target) or target == '?You':
            try:                self.globData["?Tanks"][target] += amount
            except KeyError:    self.globData["?Tanks"][target] = amount
            #print "Unit:{0} got hit for:{1}, now taken:{2} damage.".format(target, amount, self.globData["?Tanks"][target])

        # For the rest of the function, a player or pet is assumed.
        # Return now if this is a mob
        if not re.match(self.isPlayer, name) and name != '?You' and not isPet and not isCharm:
            if not self.allowMobs:
                return

        # Iitialize a new user if needed
        if not name in self.globData:
            self.initToon(name)

        # Add to global statistics, and pet data if needed
        # NOTE: selfPet is not the same as isPet (others)
        if selfPet and isCharm:
            try:                self.globData[name]["charms"] += amount
            except KeyError:    self.globData[name]["charms"] = amount
            self.globData[name]["dmg"] += amount
            self.globStats["TOTALDMG"] += amount
            #print "yarrr", name, target

        elif selfPet:
            self.globData[name]["pets"] += amount
            self.globData[name]["dmg"] += amount
            self.globStats["TOTALDMG"] += amount
            return # Rest of stats are for players only.
        else:
            self.globData[name]["dmg"] += amount
            self.globStats["TOTALDMG"] += amount            # Total damage dealt by all players
            self.globStats["TOTALHITS"] += 1                # Number of hits dealt by all players (including reflect/ddshield)

        # Track how many times you've been hit
        if target == "You" or target == "?You":
            try:                self.globStats["GOTHIT"] += 1
            except KeyError:    self.globStats["GOTHIT"] = 1

        # Track statistics when specials used
        # TODO: It seems it detects fling, but not fling+FA? doesnt he burst?
        if type in specials:
            # Initialize first! try/except
            try:
                self.globData[name]["spec"][type] += 1
                self.globData[name]["specdmg"][type] += amount
            except KeyError:
                self.globData[name]["spec"][type] = 1
                self.globData[name]["specdmg"][type] = amount                

        # Grab min/max damage dealt in single hits for statistical purposes
        if type not in ('reflect', 'dmgShield'):
            if amount > self.globData[name]["highnum"]:
                self.globData[name]["highnum"] = amount
                self.globData[name]["hightype"] = type
            elif amount < self.globData[name]["lownum"] or self.globData[name]["lownum"] == 0:
                self.globData[name]["lownum"] = amount
                self.globData[name]["lowtype"] = type
        else:
            # Store reflect and dmg shield data
            if type in self.globData[name]:
                self.globData[name][type] += amount
            else:
                self.globData[name][type] = amount 

        # Grab number of weapon hits (includes crits)
        hitIncrease = ("crit", "normal",'glancing', 'fire', 'cold', 'chemical', 'radiation', 'melee', 'projectile', 'energy', 'poison')
        if type in hitIncrease:
            self.globData[name]["hits"] += 1

        # Nano hit stats (seperate from weapons)
        if type == 'nano':
            self.globData[name]["nano"] += amount
            self.globData[name]["nanohits"] += 1
            self.globStats['TOTALNHITS'] += 1

        # Crit stats, number of crits etc.
        if type == 'crit':
            self.globData[name]["critAmount"] += amount
            self.globData[name]["critHits"] += 1

        # Glancing stats, number of glances etc.
        if type == 'glancing':
            self.globData[name]["glanceAmount"] += amount
            self.globData[name]["glanceHits"] += 1


    # Toons % Damage of team-total
    def toPercToonDmg(self, Toon):
        return (self.globData[Toon]["dmg"]*100) / self.globStats["TOTALDMG"]


    # Exclude trash data from tanking stats
    def fixTankData(self):
        tankdmg = 1.0 #Div0
        dlist = [] # Exclude mobs and calc total sustained
        for Toon in self.globData["?Tanks"]:
            if Toon == '?You':
                tankdmg += self.globData["?Tanks"][Toon]
                continue

            # Remove mobs, don't want their tanking stats (nor charms)
            w = self.w.whois(Toon, self.dim)
            if w[0] == "Mob?":
                dlist.append(Toon)
                #print w[0], "is obviously a mob",Toon
                continue

            # Count up total damage taken on all toons
            tankdmg += self.globData["?Tanks"][Toon]
        #print self.globData['?Tanks']
        #print "[Proces.] Total tank dmg: {0}".format(tankdmg)

        # Doing it after mob-check, not to include mob sustained dmg
        for Toon in self.globData["?Tanks"]: 
            if (self.globData["?Tanks"][Toon] / tankdmg)*100 < 5:
                print "[Proces.] Removed toon {0} from tanking stats.. taken {1} of {2} dmg.".format(Toon, self.globData["?Tanks"][Toon], tankdmg)
                print ">>>", (self.globData["?Tanks"][Toon] / tankdmg)*100
                dlist.append(Toon)

        # Remove toons from tanklist    
        for Toon in dlist: 
            try: del self.globData["?Tanks"][Toon]
            except: pass


    def postProcess(self, data):
        """
        Postprocessing on regex parsed data
        Converts regex output into 'per player' etc data.
        """
        for ret in data:
        
            # Pets
            if (ret["pattern"] == 0):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "normal", True)
            elif (ret["pattern"] == 1):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "crit", True)
            elif (ret["pattern"] == 21):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "glancing", True) # Glancing!
            # Player
            elif (ret["pattern"] == 2):
                self.addDamage("?You", ret["target"], ret["amount"], "nano")
            elif (ret["pattern"] == 3):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "nano")
            elif (ret["pattern"] == 4):
                self.addDamage(ret["name"], "?You", ret["amount"], "nano")
            elif (ret["pattern"] == 5):
                self.addDamage(ret["name"], ret["target"], ret["amount"], ret["type"])
            elif (ret["pattern"] == 6):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "reflect")
            elif (ret["pattern"] == 8):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "crit")
            elif (ret["pattern"] == 9):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "dmgShield")
            elif (ret["pattern"] == 10 or ret["pattern"] == 11):
                self.addDamage("?You", ret["target"], ret["amount"], "reflect")
            elif (ret["pattern"] > 11 and ret["pattern"] < 16):
                self.xptypes = ("SK", "Research", "AXP", "XP")                          # TODO: Move to a more global location
                self.addXP(ret["amount"], self.xptypes[ ret["pattern"]-12 ])               # Direct array access to avoid if-statements
            #elif (ret["pattern"] == 7):
            #    pass # didHeal
            #elif ret["pattern"] == 16:
            #    pass # addEvade
            elif ret["pattern"] == 17:
                self.addGotHeal(ret["name"], ret["amount"])
                
            elif ret["pattern"] == 18:
                self.petBan(ret["target"])
                #print "NotAPet: ", ret["target"]
                
            elif ret["pattern"] == 19:
                self.petException(ret["name"])
                #print "ExceptionList: ", ret["name"]
                
            elif ret["pattern"] == 20:
                self.petAssignOther(ret["name"], ret["target"])
            
            elif (ret["pattern"] == 22):
                self.addDamage(ret["name"], ret["target"], ret["amount"], "glancing") # Glancing!


# Gets start, stop, duration of a dataset
def GetPeriod(data):
    """
    @param data: Dataset
    @return: (start, stop, duration) 
    """
    if len(data) < 1: return 0, 1, 1
    
    start = -1
    for D in reversed(data):
        try: start = D["TS"]
        except KeyError: continue
        
    if start == -1: return 0, 1, 1
    stop = int(time.time())
        
    # You never know..
    if start > stop:
        start, stop = stop, start
        
    return start, stop, (stop-start)


# Assign petnames to owners, if possible
def AssignPetDmg(Petlist, Professions, DPClass, Class, IgnoreName = "??Invalid??Name??"): 

    # Make a copy and remove 'self'.
    # Self pets has already been assigned.
    ProflistCopy = Professions[Class][:]
    if IgnoreName in ProflistCopy:
        ProflistCopy.remove(IgnoreName)

    # One [petprof], assign as the owner
    if len(ProflistCopy) != 1: 
        return Petlist

    # Grab the remaining pet-prof and assign the pet damage to him.    
    Toon = ProflistCopy[0]
    for pet in Petlist:
        DPClass.globData[Toon]["pets"] += DPClass.globData[pet]["dmg"] 
        DPClass.globData[Toon]["dmg"]  += DPClass.globData[pet]["dmg"]
        print "[Proces.] Assigned Pet '%s' to player '%s'" % (pet, Toon)

    # Drop pet from damage dump, since it has an owner
    for Pet in Petlist:
        del DPClass.globData[Pet]
    Petlist = []
        
    return Petlist


# Assign charms to owners, if possible
def AssignCharmDmg(Moblist, Bureaucrats, DPClass, IgnoreName = "??Invalid??Name??"):
    """
    @param Moblist: List of mobs/possible charms
    @param Bureaucrats: List of bureaucrats (Professions["Bureaucrat"])
    @param DPClass: DataParser instance
    @param IgnoreName: Name of player/owner, ignored for charms.
    Assigns charm damage to bureaucrats, when possible.
    Limitation: One crat that isnt the player/parser
    """  
    if not len(Moblist): return Moblist

    # Remove self, if the list contains the user.
    # User-charms are listed as real pets.
    Toonlist = Bureaucrats[:]
    if IgnoreName in Toonlist: Toonlist.remove(IgnoreName)
    if 'Bartender' in Toonlist: Toonlist.remove(IgnoreName)
    if 'Guard' in Toonlist: Toonlist.remove(IgnoreName)

    # Can only handle charms for a single bureaucrat
    if len(Toonlist) != 1:
        return Moblist

    # Charms are not initialized for most players
    Toon = Toonlist[0]
    try: DPClass.globData[Toon]["charms"]
    except KeyError: DPClass.globData[Toon]["charms"] = 0

    for charm in Moblist:
        DPClass.globData[Toon]["charms"] += DPClass.globData[charm]["dmg"] 
        DPClass.globData[Toon]["dmg"]  += DPClass.globData[charm]["dmg"]
        print "[Proces.] Assigned charm damage to '%s'" % Toon

    for Charm in Moblist:
        del DPClass.globData[Charm]
    Moblist = []
        
    return Moblist

    
# Calls addDamage() etc on pre-processed data
# TODO: Remove if statements (no real performance gains)
# TUDO: Move much of this into the DataParser class
def SumParsedData(data, selfname, dimension, startTime, allowMobs = False, allowLowdmg = False):
    print "[Proces.] Processing %d items " % len(data)

    P = DataParser(selfname, dimension, allowMobs)
    P.period = (startTime, int(time.time()), int(time.time())-startTime)
    P.postProcess(data)

    # At this point the globData dict should be fully populated
    # Time for linking pets to players, counting profs and excluding bad data.
    Professions = {'Adventurer':[], 'Agent':[], 'Bureaucrat':[], 'Doctor':[], 'Enforcer':[], 'Engineer':[], 'Fixer':[], 'Keeper':[], 'Martial Artist':[], 'Meta-Physicist':[], 'Nano-Technician':[], 'Shade':[], 'Soldier':[], 'Trader':[], 'Unknown':[]}
    NPC = []
    CratPets = []       # Warning similarly named lists! (name lists vs actual pets)
    MPPets = []
    EngPets = []
    TradPets = []
    LowPlayers = []     # Did not meet minimum damage req

    # Set a name to self, allowing for whois and such.
    # Mainly needed for charms :: There is a chance you did no hits!
    try:
        P.globData[selfname] = P.globData["?You"]
        del P.globData["?You"]

        P.globData['?Tanks'][selfname] = P.globData['?Tanks']['?You']
        del P.globData['?Tanks']['?You']
        #print globData[selfname]
    except KeyError:
        pass

    # Ignore certain mob names such as "Guard" and "Fanatic"
    # Otherwise detected as players.
    for name in badNames:
        if name in P.globData:
            del P.globData[name]

    for Toon in P.globData:
        if Toon == "?Tanks":
            continue

        # Seperate mobs(charms) from the players
        if Toon in cratPets:            CratPets.append(Toon)
        elif Toon in mpPets:            MPPets.append(Toon)
        elif Toon in engPets:           EngPets.append(Toon)
        elif Toon in tradPets:         TradPets.append(Toon)

        # Player
        else:
            """
            import pprint
            print "\n"
            pprint.pprint(P.globData)
            pprint.pprint(P.globStats)"""
            w = P.w.whois(Toon, dimension)
            P.globData[Toon]["whois"] = w       # Store whois 
            # Either NPC or charm
            if w[0] == "Mob?" and not allowMobs:
                print "[Proces.] Classify(Mob): '%s'" % Toon
                NPC.append(Toon)

            # Only grab players who's done at least x% of total damage
            # Always grab the parsing player.
            elif (P.toPercToonDmg(Toon) >= 2 or allowLowdmg) or Toon == selfname:
                Professions[w[1]].append(Toon)  # Increase profession count
                print "[Proces.] Classify(AddPlayer): %s with %g%% damage" % (Toon, P.toPercToonDmg(Toon))

            else:
                print "[Proces.] Classify(IgnoredPlayer): %s with only %g%% damage" % (Toon, P.toPercToonDmg(Toon)) 
                LowPlayers.append(Toon)
    # End: For Toon

    # Exclude NPCs from tanks, and people with too low sustained damage.
    P.fixTankData()

    # Sum up profession damage
    for Prof in Professions:
        for Toon in Professions[Prof]:
            P.globStats["?Prof"][Prof] += P.globData[Toon]["dmg"]

    # Assign pet damage to their respective owners, and remove them as a seperate player
    print "[Proces.] Assigning pets to owners:", EngPets, CratPets, MPPets, TradPets
    EngPets  = AssignPetDmg(EngPets, Professions, P, "Engineer", selfname) 
    CratPets = AssignPetDmg(CratPets, Professions, P, "Bureaucrat", selfname)
    MPPets = AssignPetDmg(MPPets, Professions, P, "Meta-Physicist", selfname)
    TradPets = AssignPetDmg(TradPets, Professions, P, "Trader", selfname)

    """
    # Raid test, etc
    for i in xrange(32):
        P.initToon("TestToon%d"%i)
        P.globData["TestToon%d"%i]["hits"] = 1300
        P.globData["TestToon%d"%i]["dmg"] = 300000
        P.globData["TestToon%d"%i]["nanoHits"] = 1300
        P.globData["TestToon%d"%i]["nano"] = 500000
   """

    # Assign charm damage to crats
    # Any unhandled NPCs will be listed as player "Charms" (if there are any crats)
    NPC = AssignCharmDmg(NPC, Professions['Bureaucrat'], P, selfname)
    if len(NPC):
        for C in NPC:
            if P.isBadPet(C): continue  # Skip bad pets
            if P.isMyPet(C): # and len(Professions['Bureaucrat']):
                amount = P.globData[C]["dmg"]  
                print "[Proces.] Assigning ''%s'' as my pet (%d dmg)" % (C, amount)
                
                # Consider making a function call for this
                P.globData[P.selfname]["pets"] += amount
                P.globData[P.selfname]["dmg"] += amount
                del P.globData[C]
                continue
            
            owner = P.isPetOther(C)
            if owner != None:
                print '[Proces.] Pet "%s" assigned to "%s" (%d dmg)' % (C, owner, P.globData[C]["dmg"])
                try:
                    P.globData[owner]["pets"] += P.globData[C]["dmg"]
                    P.globData[owner]["dmg"] += P.globData[C]["dmg"]
                except KeyError: pass # Could be we don't actually have this person stored
                del P.globData[C]
                continue

            print "[Proces.] Renamed: Charm/OddPet: %s (%d dmg)" % (C, P.globData[C]["dmg"])
            P.globData[":%s:" % C] = P.globData[C]
            del P.globData[C]

    # Delete anyone that has not yet been processed (hopefully mobs)
    for C in NPC:
        if C in P.globData:
            print "[Proces.] Deleting mob: %s (%d dmg)" % (C, P.globData[C]["dmg"])
            del P.globData[C]

    print "[Proces.] Number of pets (other): %d" % (len(EngPets)+len(CratPets)+len(MPPets)+len(TradPets))
    for Prof in Professions:
        if len(Professions[Prof]):
            print "[Proces.] %ss" % Prof , Professions[Prof]

    # Remove players who did not meet the minimum requirements
    # Re-check just to make sure, since pet damage has been added.
    for Player in LowPlayers:
        if P.toPercToonDmg(Player) >= 2:
            print "[Proces.] ReClassify(AddPlayer): %s (%d dmg)" % (Player, P.globData[Player]["dmg"])
            continue 
        del P.globData[Player]

    print "[Proces.] Entries: ",
    for Player in P.globData:
        print "'%s'," % Player, 
    print

    return P
