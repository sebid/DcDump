import sqlite3, re, os, sys
from operator import itemgetter
from DebugSettings import Build_Version, Build_ID
import threading, time


def GetXMLContents(enabled = True):
    return """<Archive code="0">
    <Array name="selected_group_ids">
        <Int64 value="1107296267" />
        <Int64 value="1107296266" />
        <Int64 value="1107296265" />
        <Int64 value="1107296264" />
        <Int64 value="1107296263" />
        <Int64 value="1107296262" />
        <Int64 value="1107296261" />
        <Int64 value="1107296260" />
        <Int64 value="1107296259" />
        <Int64 value="1107296258" />
        <Int64 value="1090519041" />
        <Int64 value="1090519040" />
        <Int64 value="1073741825" />
        <Int64 value="1107296284" />
        <Int64 value="1107296268" />
        <Int64 value="1107296257" />
        <Int64 value="1107296273" />
        <Int64 value="1107296274" />
        <Int64 value="1107296275" />
        <Int64 value="1107296276" />
        <Int64 value="1107296277" />
        <Int64 value="1107296278" />
        <Int64 value="1107296279" />
    </Array>
    <Array name="selected_group_names">
        <String value='&quot;Me got XP&quot;' />
        <String value='&quot;Other hit by other&quot;' />
        <String value='&quot;Your pet hit by other&quot;' />
        <String value='&quot;You hit other&quot;' />
        <String value='&quot;Me hit by player&quot;' />
        <String value='&quot;Me hit by monster&quot;' />
        <String value='&quot;You hit other with nano&quot;' />
        <String value='&quot;Other hit by nano&quot;' />
        <String value='&quot;Your pet hit by nano&quot;' />
        <String value='&quot;Me hit by nano&quot;' />
        <String value='&quot;Other Pets&quot;' />
        <String value='&quot;Your Pets&quot;' />
        <String value='&quot;System&quot;' />
        <String value='&quot;Research&quot;' />
        <String value='&quot;Me got SK&quot;' />
        <String value='&quot;Me hit by environment&quot;' />
        <String value='&quot;Your pet hit by monster&quot;' />
        <String value='&quot;Your misses&quot;' />
        <String value='&quot;Other misses&quot;' />
        <String value='&quot;You gave health&quot;' />
        <String value='&quot;Me got health&quot;' />
        <String value='&quot;Me got nano&quot;' />
        <String value='&quot;You gave nano&quot;' />
    </Array>
    <Archive code="0" name="log_window_config">
        <Rect name="WindowFrame" value="Rect(533.000000,415.000000,1090.000000,717.000000)" />
        <Bool name="WindowPinButtonState" value="false" />
    </Archive>
    <Archive code="0" name="chat_window_config">
        <Bool name="WindowPinButtonState" value="true" />
        <Rect name="WindowFrame" value="Rect(260.000000,483.000000,1141.000000,728.000000)" />
        <Bool name="is_backmost" value="false" />
        <Bool name="is_frontmost" value="false" />
    </Archive>
    <Archive code="0" name="chat_view_config" />
    <Int32 name="visual_mode" value="0" />
    <String name="output_group" value='&quot;&quot;' />
    <Float name="window_transparency_inactive" value="0.300000" />
    <Float name="window_transparency_active" value="0.800000" />
    <Bool name="show_timestamps" value="false" />
    <Bool name="hide_input_when_inactive" value="true" />
    <Bool name="deactivate_on_send" value="true" />
    <Bool name="is_textinput_enabled" value="false" />
    <Bool name="is_clickthrough" value="false" />
    <Bool name="is_logged" value="%s" />
    <Bool name="is_message_fading_enabled" value="false" />
    <Bool name="is_autosubscribe_window" value="false" />
    <Bool name="is_window_open" value="false" />
    <Int32 name="tab_index" value="0" />
    <String name="window_name" value='&quot;WindowDCDump&quot;' />
    <Bool name="is_default_window" value="false" />
    <Bool name="is_startup_window" value="false" />
    <String name="name" value='&quot;dcDump&quot;' />
</Archive>""" % True


def AutodetectAO(args = ""):
    """
    Autodetects anarchy online client
    @return: Full path to AO, or -1
    """
    pipe = os.popen("find.exe"+args)
    output = pipe.readlines()
    pipe.close()

    if len(output) == 1 and not "-1" in output:
        return os.path.dirname(output[0])+"\\"
    return "-1"


def getAppdataFolders():
    """
    Gets AO /prefs/ path from Appdata
    @return: Path(s) or None
    """
    appdata = os.environ['appdata']
    path = os.path.join(appdata, "..", "Local", "Funcom", "")
    folders = []
    for root, dirs, files in os.walk(path):
        path = os.access(os.path.join(root, "Prefs", "prefs.xml"), os.R_OK)
        if path:
            folders.append(root)
    return folders


'''
class AnonStats (threading.Thread):
    """Opens site for logging anonymous user statistics..
        A hash is made from PC name"""
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        from platform import node
        from urllib import urlopen
        
        # No need to go apeshit just because it doesn't work, its just statistics.
        try:
            hashStr = node()
            v = "%s.%d" % (Build_Version, Build_ID)
            if not '.exe' in sys.argv[0]:
                #data = urlopen("http://ribbs.dreamcrash.org/stats.php?hash=%d&version=%s&debug=1" % (hashStr.__hash__(), v) )
                pass
            else:
                data = urlopen("http://ribbs.dreamcrash.org/stats.php?hash=%d&version=%s" % (hashStr.__hash__(), v) )
                print data
        except:
            print "Failed to report anonymous stats", sys.exc_info()[0]

        return

'''


def AutodetectAOIA():
    return AutodetectAO(" -aoia")


def VerifyAOIA(path):
    return os.access( os.path.join(path, "ItemAssistant.db") , os.F_OK)


def VerifyAO(path):
    return os.access( os.path.join(path, "Anarchy.exe"), os.F_OK)


def Initialize(aopath):
    # Get account names from IDs etc [used below]
    # Also detects new IDs and initializes the damage window, cleans old logs.
    d = GetAccFromID(True)

    'Attempt to access the database, if successful, just bail here. [otherwise initialize database]' 
    try: 
        __SQL.execute("select dimension from chars limit 1")
        return False
    except: 
        pass

    #if not aopath:
    #   aopath = AutodetectAO()

    if not VerifyAO(aopath):
        return False

    __CONN = sqlite3.connect("SQDB")
    __SQL = __CONN.cursor()
    # Insert and update the locally maintained list of toons

    d2 = {}
    for Key in d:
        acc = d[Key]
        try: 
            __SQL.execute("insert into chars (id, nick, active, account, dimension) values (?, ?, ?, ?, ?)", (key, '', 0, acc, 'RK1'))
        except: 
            __CONN.commit()
            __SQL.close()
            return False

    __CONN.commit()
    __SQL.close()
    return True


def __verifyToonsDB(__SQL):
    # Make sure the chars table exists, and is correct.
    #__SQL.execute("CREATE TABLE if not exists chars (id INTEGER NOT NULL PRIMARY KEY UNIQUE, nick TEXT, active INTEGER, account TEXT)")
    #try: __SQL.execute("select account from chars limit 1")
    #except:    __SQL.execute("alter table chars add account TEXT")

    __SQL.execute("CREATE TABLE if not exists chars (id INTEGER NOT NULL PRIMARY KEY UNIQUE, nick TEXT, active INTEGER, account TEXT, dimension TEXT)")
    try: __SQL.execute("select dimension from chars limit 1")
    except: 
        __SQL.execute("alter table chars add dimension TEXT")


class DBThread (threading.Thread):
    """SaveToonsDB can take a while, do it threaded.."""
    def __init__(self, data):
        threading.Thread.__init__(self)
        self.data = data
    def run(self):
        SaveToonsDB( self.data )
        return


def UpdateToonsDB(ID, nick):
    __CONN = sqlite3.connect("SQDB")
    __SQL = __CONN.cursor()
    __verifyToonsDB(__SQL)
    __SQL.execute("update chars set nick=? where id = ?", (nick, ID))
    aff = __SQL.rowcount
    #print "update chars set nick=%s where id = %d" % (nick, ID)
    __CONN.commit()
    __SQL.close()
    return aff != 0


def SaveToonsDB(dict):
    import time
    __CONN = sqlite3.connect("SQDB")
    __SQL = __CONN.cursor()
    __verifyToonsDB(__SQL)
    s = time.time()
    import sys
    # Insert and update the locally maintained list of toons
    for key in dict:
        if dict[key] == None:
            __SQL.execute("delete from chars where id = ?", (key,))
            print "delete from chars where id = %s" % key
            continue

        nick = dict[key]["Toon"]
        enabled = dict[key]["Enabled"]
        acc = dict[key]["Acc"]
        try: dim = dict[key]["Dimension"]
        except: dim = "RK1"

        try: 
            __SQL.execute("insert into chars (id, nick, active, account, dimension) values (?, ?, ?, ?, ?)", (key, nick, enabled, acc, dim))
            #print "insert into chars (id,nick,active,account,dimension values (%s, %s, %s, %s, %s)" % (key, nick, enabled, acc, dim)
        except: 
            #print "exception", sys.exc_info();
            __SQL.execute("update chars set nick=?, active=?, account=?, dimension=? where id = ?", (nick, enabled, acc, dim, key))
            #print "update chars set nick=%s, active=%s, account=%s, dimension=%s where id =%s" % (nick, enabled, acc, key, dim)

    if time.time()-s > 1:
        print "SaveSQL: Took %g seconds to make %d queries etc.." % (time.time()-s, len(dict)*2)
    s = time.time() 

    __CONN.commit()
    __SQL.close()


# Load all own toons stored in the db 
def LoadToonsDB():
    """
    Loads the ID, Toon name, enable status and accname from SQL database
    If enabled: Verifies account name from AO\prefs folder. 
    """
    __CONN = sqlite3.connect("SQDB")
    __SQL = __CONN.cursor()
    __verifyToonsDB(__SQL)

    __SQL.execute("select id, nick, active, account, dimension from chars")
    results = {}
    for id, nick, active, acc, dimension in __SQL:
        # Check if the acc\id folder really exists, if not: disable it.
        if active:
            for appdatafolders in getAppdataFolders():
                path = "%s\\Prefs\\%s\\Char%d" % (appdatafolders, acc, id)
                if not os.access(path, os.F_OK): active = False

        # Dimension may not be set for older DBs
        if not dimension: dim = "RK1"
        else: dim = dimension
        results[id] = {"Toon":nick, "Enabled": active, "Acc":acc, "Dimension":dim}

    #import pprint
    #pprint.pprint(results)
    __CONN.commit()
    __SQL.close()
    return results


# Loads all toons from AOIA and returns in a dict
# Input: Path to AOIA
# Output: {id} = toon
def GetIdToonFromAOIA(path):
    if not VerifyAOIA(path):
         return {}
        
    __CONN = sqlite3.connect( os.path.join(path, "ItemAssistant.db"))
    __SQL = __CONN.cursor()
    __SQL.execute('SELECT `charname`, `charid` FROM tToons order by `charname`') # Yes, ttoon is correct.
    data = [C for C in __SQL]
    __SQL.close()

    out = {}
    for nick, id in data:
        out[id] = nick
    return out


# Returns the char IDs + accounts
# Walks trough \prefs\ and returns every Acc\Char## combination
def GetAccFromID(initialize, filter = []):
    """
    @param filter: IDs to retreive (all if not specified)
    @return: Dict[id] = "accname"
    Traverses the AO\prefs folder for account names.
    """

    out = {}
    pathList = []
    for appdatafolders in getAppdataFolders():
        #Path = os.path.join(appdatafolders, "prefs")

        dirPrefs = os.listdir(appdatafolders)
		#print "[Chars  ] Loading toons in path: %s" % Path
        for Account in dirPrefs:
            pathToons = os.path.join(appdatafolders,"Prefs", Account)
            if not os.path.isdir( pathToons ): continue
            dirToons = os.listdir(pathToons)

            for ToonID in dirToons:
                if not os.path.isdir( os.path.join(pathToons, ToonID) ): continue
                if ToonID[:4] != 'Char': continue
                try: id = int( ToonID[4:] )
                except ValueError: continue # Damnit, why is this needed?

                # If filtering, make sure its in the list.
                if filter and not id in filter:
                    continue

                out[id] = Account       # Add to list

                if initialize:
					# Install the logger-window if it doesnt exist
                    fullpath = os.path.join(pathToons, ToonID, 'Chat', 'Windows', 'WindowDCDump')
                    if not os.access(os.path.join(fullpath, "Config.xml"), os.F_OK):
                        try: os.makedirs(fullpath)
                        except WindowsError: continue
                        try: f = open( os.path.join(fullpath, "Config.xml"), "w")
                        except IOError: continue

                        # Write the window data
                        f.write( GetXMLContents() )
                        f.close()
                        #print "Enabled:",fullpath

					# It does exist, lets delete any logfiles that may exist (only if 256KB or larger)
                    elif os.access(os.path.join(fullpath, 'Log.txt'), os.W_OK) and os.path.getsize(os.path.join(fullpath, 'Log.txt')) > 256*1024:
                        try: os.remove(os.path.join(fullpath, 'Log.txt'))
                        except:
                            f = open(os.path.join(fullpath, 'Log.txt'), 'w')
                            f.write('')
                            f.close()
                            #print "Trimmed file",os.path.join(fullpath, 'Log.txt')
    return out


# Input: Dict
# Saves the program settings to SQL database
def SaveConfig(config):
    __CONN = sqlite3.connect("SQDB")
    __SQL = __CONN.cursor()

    __SQL.execute("CREATE TABLE if not exists settings (id INTEGER PRIMARY KEY, option TEXT, setting TEXT)")

    # Update config table, not very elegant
    # But works for only 1 process accessing DB
    for Key in config:
        __SQL.execute("insert or ignore into settings (option, setting) values (?, ?)", (Key, config[Key]))
        __SQL.execute("update settings set setting=? where option=?", (config[Key], Key))

    __CONN.commit()
    __SQL.close()
    
    return True


# Input: Dict
# Loads the stored program settings from SQL database
def LoadConfig():
    __CONN = sqlite3.connect("SQDB")
    __SQL = __CONN.cursor()

    __SQL.execute("CREATE TABLE if not exists settings (option TEXT PRIMARY KEY, setting TEXT)")

    __SQL.execute("select * from settings")
    out = {}
    for Key, Val in __SQL:
        out[Key] = Val
        #print Key, Val

    __CONN.commit()
    __SQL.close()
    return out

def GetLogfilePath(accname, id):
    pathList = []
    # Regular prefs
    for appdatafolders in getAppdataFolders():
        logPath = os.path.join(appdatafolders, "Prefs", accname, "Char%d"%id, "Chat", "Windows", "WindowDCDump", "log.txt")
        if os.access(logPath, os.F_OK): pathList.append(logPath)
        
    if len(pathList) == 0: return None       
    latest_subdir = max(pathlist, key=os.path.getmtime)
    return latest_subdir


def getLatestLog(toonlist):
    """
    @param toonlist: (Accname, ID) tuple  
    @return: ID of toon with newest logfile
    """
    dataset = []
    # Get the newest logfile ID
    for appdatafolders in getAppdataFolders():
        for accname, id in toonlist:
            path = os.path.join(appdatafolders, "Prefs", accname, "Char%d"%id, "Chat", "Windows", "WindowDCDump", "log.txt")
            dataset.append( (os.path.getmtime(path), id) )

    # Grab highest timestamp
    dataset = sorted(dataset, key=itemgetter(0))

    if len(dataset) > 0:
        return dataset[0][1]
    else:
        return None


def getDimension(id):
    __CONN = sqlite3.connect("SQDB")
    __SQL = __CONN.cursor()

    __SQL.execute("select dimension from chars where id = ?", (id,))
    for x in __SQL:
        __SQL.close()
        return x[0]

    __SQL.close()
    return None

if __name__ == "__main__":
    import sys, pprint
    aopath = "D:\\Program Files (x86)\\Games\\Anarchy Online"
    pprint.pprint(GetAccFromID(False))

    #print getDimension(2774555951)
    sys.exit(0)

    #print CopyFromAOIA("D:\\Program Files (x86)\\Games\\Anarchy Online\\aoia")
    #print CopyFromFolders("D:\\Program Files (x86)\\Games\\Anarchy Online")
    #print Install("D:\\Program Files (x86)\\Games\\Anarchy Online", 3043184575)
    #print Uninstall("D:\\Program Files (x86)\\Games\\Anarchy Online", 555)

    d = GetAccFromID()
    for X in d:
        print X, d[X]

    print "n: ", len(d)
    print "-- end --"

    """
    d2 = GetFromFolders2(aopath)
    for X in d2:
        print X, d2[X]
        
    print "-- end --"
    print "Old:", len(d)
    print "New:", len(d2)
    
    print d["1188094805"]
    print d2["1188094805"]
    for X in d2:
        print (d2[X] == d[X])
    

    d,d2 = d2,d 
    for X in d2:
        print (d2[X] == d[X])"""

    dict = {"AOPath":"c:\\", "AOIAPath":"d:\\"}
    #SaveConfig(dict)
    #LoadConfig()
    #LoadToons()
    print "--- start ----"

    print ".."
    print AutodetectAO()
    print AutodetectAOIA()