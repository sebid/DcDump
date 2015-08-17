"""
Provides a Whois service for the application
Available modes are: Regular, Limited
 Regular mode will maintain a connection to the KAZE whois database, and object is assumed to be destroyed when done.
 Limited mode will disable connection to the KAZE whois database, unless limitedMassWhois is called.
 
 The whois works as follows:
    A whois check is done against the local database, record returned if not outdated
    A whois check is done against the KAZE database, record returned and local DB updated, if not outdated
    A whois check is done against the Funcom database, record returned and local DB updated, if not outdated
"""
import re
from urllib import urlopen
import time
from DebugSettings import Debug


class WhoIs():
    # Limited made for GUI mode: attempts not to use T.o's database


    def __init__(self, ignored, limited = False): 
        import sqlite3
        self.CONN = sqlite3.connect("SQDB", isolation_level=None)
        self.SQL = self.CONN.cursor()
        #self.expIsPlayer = re.compile(r"^[A-Z][a-z]{3,}[a-z]*[0-9]*$")
        self.expIsPlayer = re.compile(r"^[A-Z][a-z]{3,}[a-z]*[0-9]*(-\d+)?$")
        self.limited = limited
    
        # Program is not intended to run on an empty database, but it still CAN.
        #self.SQL.execute("CREATE TABLE if not exists whois (name TEXT PRIMARY KEY, class TEXT, level INTEGER, age INTEGER)")
        self.SQL.execute("CREATE TABLE if not exists whois (name, class TEXT, level INTEGER, age INTEGER, dimension TEXT, PRIMARY KEY(name, dimension))")
        self.Professions = ['Adventurer', 'Agent', 'Bureaucrat', 'Doctor', 'Enforcer', 'Engineer', 'Fixer', 'Keeper', 'Martial Artist', 'Meta-Physicist', 'Nano-Technician', 'Shade', 'Soldier', 'Trader']

        # Handle old SQLs
        try:
            self.SQL.execute('SELECT * from whois where dimension=0 limit 1')
        except:
            self.SQL.execute("drop table whois")
            self.SQL.execute("CREATE TABLE if not exists whois (name, class TEXT, level INTEGER, age INTEGER, dimension TEXT, PRIMARY KEY(name, dimension))")   

        # Connect to mysql if not limited-mode
        if not self.limited:
            try:
                import _mysql
                self.mysql = _mysql.connect("nexus.dreamcrash.org", "xiremote")
                self.mysql.query("use xi")
            except: self.mysql = 0; self.limited = True
        else:
            self.mysql = 0


    def cleanup(self):
        try:
            self.CONN.commit()
        except AttributeError:
            if Debug: print "[WhoIs  ]: Cleanup failed"
            return

        self.SQL.close()
        if not self.limited:
            self.mysql.close()


    def limitedMassWhois(self, users):
        """
        @param users: Tuple/List of users to whois
        @return: nothing 
        Does a mass whois on all given toons, does not return any results.
        Primary goal is to update the local whois database.
        Intended use for function is a mass-update of all registered toons.
        """

        return False # No longer available

        if not self.limited: return False;

        self.limited = False
        try:
            import _mysql
            self.mysql = _mysql.connect("nexus.dreamcrash.org", "xiremote")
            self.mysql.query("use xi")
        except:
            if Debug: print "[Whois  ] Failed connecting to t.o's database (LMW)"
            return

        for Toon, Dim in users:
            self.whois(Toon, Dim)

        self.limited = True
        self.mysql.close()


    def updateRecordsX(self, name, profession, level, dimension):
        padding = int(time.time())+60*60*24
        if level == 220: padding *= 10
        try: 
            self.SQL.execute("insert into whois(name, class, level, age, dimension) values (?, ?, ?, ?, ?)", (name, profession, level, padding, dimension))
        except: 
            try: 
                self.SQL.execute("update whois set class=?, level=?, age=? where name=? and dimension=?", (profession, level, padding, name, dimension))
            except: pass

        self.CONN.commit()


    def __updateRecord(self, name, profession, level, dimension):
        """
        @param name: Character name
        @param profession: Character profession
        @param level: Character level
        @param dimension: RK1 or RK2
        Updates the local whois record
        Level 220 toons are only rechecked once every 10 days    
        """
        padding = int(time.time())+60*60*24
        if level == 220: padding *= 10
        #print "[Whois  ] Inserting into local database for toon %s.." % name
        try: 
            self.SQL.execute("insert into whois(name, class, level, age, dimension) values (?, ?, ?, ?, ?)", (name, profession, level, padding, dimension))
            print "[Whois  ] Adding to whois for character '%s'.." % name
        except: 
            try: 
                #print "[Whois  ] Insert failed.. doing update.."
                self.SQL.execute("update whois set class=?, level=?, age=? where name=? and dimension=?", (profession, level, padding, name, dimension))
                print "[Whois  ] Updating whois for character '%s'.." % name
            except: print "[Whois  ] Update failed... (???)"

        self.CONN.commit()


    def __assertProf(self, prof):
        if not prof in self.Professions:
            return self.Professions[0]
        return prof


    def whois(self, user, dimension="RK1"):
        output = ("Mob?", "Unknown", 0) #: Standard output on failure
        age = 0                         #: Timestamp of current record
        updated = False                 #: Whetever the local database should be updated

        # Skip whois if the name can't possibly be a player.
        if self.expIsPlayer.search(user) == None:
            return output

        # Step 1: Check local database
        self.SQL.execute('SELECT age, name, class, level from whois where name=? and dimension=? COLLATE NOCASE', (user,dimension))
        res = self.SQL.fetchone()
        if res != None:
            output = (res[1], res[2], res[3])
            age = res[0]
            #print "[WhoIs  ] Local:", age, output

            # Record not outdated, just return it.
            if time.time() <= age:
                return output

        # Step 2
        # If this record is more than a day old, request a new one from T.o's database
        # Note: Local records are stored with a 24-hour padding
        #       Remote records are stored with a 6-hour padding
        # Also if no record exists.
        if not self.limited and dimension == 'RK1':
            padding = 18*60*60
            self.mysql.query("select updated, name, profession, level from whois where name='%s'" % user)
            r = self.mysql.use_result()
            try: 
                # Fetch data, and only use if new data is newer
                # 2D tuple / Tuple of tuples
                res = r.fetch_row()
                if res and int(res[0][0])+padding > age:
                    age = int(res[0][0])
                    output = (res[0][1], res[0][2], int(res[0][3]))
                    print "[WhoIs  ] T.o: ", age, output

                    self.__updateRecord(output[0], output[1], output[2], dimension)
                    return output

            # No entry found
            except: 
                print "exception", sys.exc_info();

        # Step 3:
        # If t.o's record is more than 1 day old, request from funcoms server.
        url = """http://people.anarchy-online.com/character/bio/d/%s/name/%s/bio.xml""" % (dimension[2:], user)
        print "[WhoIs  ] URL: %s" % url

        prof, level, nick = "", 0, ""
        try: data = urlopen(url)
        except: data = ()

        for L in data:
            # Grab nickname (for verification)
            match = re.match("\s*<nick>(?P<nick>.+)</nick>", L, re.I)
            try: nick = match.group("nick")
            except AttributeError: pass

            # Grab level
            match = re.match("\s*<level>(?P<level>\d+)</level>", L, re.I)
            try: level = int(match.group("level"))
            except AttributeError: pass

            # Grab profession
            match = re.match("\s*<profession>(?P<prof>.+)</profession>", L, re.I)
            try: prof = match.group("prof")
            except AttributeError: pass

        # Check if we got the right user
        if (level > 0 and nick == user):
            output = (nick, prof, level)
            self.__updateRecord(output[0], self.__assertProf(output[1]), output[2], dimension)
        else:
            print "[Whois  ] Could not find user %s in Funcom database" % user
            self.__updateRecord(user, "Adventurer", 0, dimension) # Store to prevent spam

        return output


"""
def test(n):
    p = re.compile(r"^[A-Z][a-z]{3,}[a-z]*[0-9]*$")
    if p.search(n) == None:
        print "False:", n
    else:
        print "True:",n
    """

if __name__ == "__main__":
    import sys

    """
    print "-- False --"
    test("fake name")
    test("Fake name")
    test("maren1")
    test("AlienBot")
    test("enfo777")
    test("SinSlayer")
    test("SinslayeR")
    test("Enfox7x77")
    test("Enfozo0k")
    test("Mob?")

    print "-- Trues --"
    test("Maren1")
    test("Eviltrox")
    test("Leetycakes")
    test("Solistaire15")
    test("Enfo777")
    test("Sinslayer")
    test("Zlipperypete")
    """

    mod = WhoIs(True)
    print mod.whois("maren1")
    print mod.whois("Enfo777")
    print mod.whois("Fake name")
    print mod.whois("eviltrox")

    mod.limitedMassWhois( ("maren1", "eviltrox", "sinslayer") )

    mod.cleanup()