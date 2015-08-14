#!/usr/bin/env python
# -*- coding: latin-1 -*-
import locale, datetime
import os, sys
from operator import itemgetter
from DebugSettings import Debug
from Chars import getAppdataAO
import re, sqlite3, Chars
from urllib import urlopen

import urllib2

def getItemnameFromXyphos(id):
    request = urllib2.Request("https://aoitems.com/item/{0}/".format(id))
    request.add_header('User-Agent','OpenAnything/1.0 +http://diveintopython.org/')
    opener = urllib2.build_opener()
    data = opener.open(request).read()
    
    result = re.search("<h1>([^<]*)</h1>", data, re.I)
    
    if result:
        return result.groups()[0]
    else:
        return "?"
    
def getFmtDates(dates):
    s,e = dates[0], dates[1]
    start = s.strftime("%y-%m-%d %H:%M:%S")
    end = e.strftime("%H:%M:%S")
    duration = "%dm:%ds" % ((e-s).seconds/60, (e-s).seconds%60)
    return start, end, duration

def damageSort(a, b):
    """Sort function for damage, input (Name, Dmg), deprioritizes toons with : in their name."""
    if ':' in a[0] and not ':' in b[0]: return 1
    if ':' in b[0] and not ':' in a[0]: return -1
    return b[1] - a[1]

# Get a list of toons, sorted by damage done
def sortByDamage(data):
    # Sort by damage here
    dataset = []
    for P in data:
        if '?' in P:
            continue
        dataset.append( (P, data[P]["dmg"]) )
    
    # Sort by damage done
    dataset.sort(damageSort)
    return dataset

def number_format(num):
    """
    @param num: Integer
    @return: Formatted string 
    Formats numbers to a NNN NNN NNN format.
    Does not use python locale. due to some issues with invalid output etc (not worth it)"""
    data = "%d" % num
    out = ""
    i = 0
    for C in reversed(data):
        if i == 3:
            i = 0
            out = " " + out
        out = C + out
        i += 1
    return out
    
class Script():
    def __init__(self):
        self.__SQL = None
        self.__CONN = None
            
        self.backpacks = {}
        self.shoppacks = {}
        self.accids = {}

    
    
    
    def getDcExp(self, stats, dates, pausetime):
        durDiv = (dates[1]-dates[0]).seconds / 60. / 60.    # For "per hour" division
        durDiv -= pausetime / 60. / 60.

        start, end, duration = getFmtDates(dates)
        if durDiv == 0: return "Error, duration was 0 seconds.."
        
        # Grab both XP and SK, since were unlikely to have both
        xp = number_format(stats["xp"]["XP"] + stats["xp"]["SK"])
        durDiv = float(durDiv) #just in case
        if xp > 0:
            xph = " (<font color=#cccc00>%s/hour</font>)" % number_format( (stats["xp"]["XP"]+stats["xp"]["SK"])/durDiv)
    
        axp = number_format(stats["xp"]["AXP"])
        if axp > 0:
            axph = " (<font color=#cccc00>%s/hour</font>)" % number_format(stats["xp"]["AXP"]/durDiv)
        
        res = number_format(stats["xp"]["Research"])
        if res > 0:
            resh = " (<font color=#cccc00>%s/hour</font>)" % number_format(stats["xp"]["Research"]/durDiv) 
        
        return """<a href="text://<font color=#99CCFF>Time %s -> %s (%s)<br><br><font color=#55AA55>Experienced gained: <font color=#cccc00>%s</font>%s<br><font color=#55AA55>AXP:</font> <font color=#cccc00>%s</font>%s<br><font color=#55AA55>Research:</font> <font color=#cccc00>%s</font>%s</font>">Experience</a>""" % (start, end, duration, xp,xph, axp,axph, res,resh)
    
    

        
        
    # dcRaid
    def getRaidData(self, data, dates, pausetime):
        start, end, duration = getFmtDates(dates)
        durDiv = (dates[1]-dates[0]).seconds / 60.    # For "per min" division
        durDiv -= pausetime / 60.
        if durDiv == 0: return ["Error, duration was 0 seconds.."]
    
        numPlayers = 0
        totalDmg = 1    
        for P in data:
            if '?' in P:
                continue
            totalDmg += data[P]["dmg"]
            numPlayers += 1
    
        if numPlayers == 0: return ["Error, no players detected.."]
        avgDpm = number_format(totalDmg/durDiv)
        avgDmg = number_format(totalDmg/numPlayers)
        output = """<a href="text://<font color=#99CCFF>Time %s -> %s (%s)<br>Players: <font color=#cccc00>%d</font><br>Damage: <font color=#cccc00>%s</font> (<font color=#cccc00>%s</font>)<br>Average: <font color=#cccc00>%s</font> dmg/player<br><br>""" % (start, end, duration, numPlayers, number_format(totalDmg), avgDpm, avgDmg)
    
        # Sort by damage here
        dataset = sortByDamage(data)
        outputArr = []

        whoreout = ""

    
        i = 1
        chunkStart = 1      # First player in chunk (for splitting into multiple files)
        for P in dataset:
            dmg = number_format(P[1])
            name = P[0]
            
            who = data[name]["whois"]
            level = who[2]
            prof = who[1]
            
            perc = 100*(P[1]/float(totalDmg))
            tmp = """<font color=#55AA55>%d.</font>  <font color=#cccc00>_ %s</font> <font color=#55AA55><font color=#10a5e5>%s</font> (<font color=#76DAFB>%d %s</font>)</font> - %.0f%% of total<br>""" % (        i, dmg, name, level, prof, perc)
            if len(output+tmp) > 3992-len(whoreout): # Maximum page size is 4096 (link also takes some space)
                output += """{0}<br><a href='chatcmd:///start http://aodevs.com/projects/view/14'>Get parser here</a>">DD {1}-{2}</a>""".format(whoreout, chunkStart, i-1)
                outputArr.append(output)
                output = '<a href="text://'
                chunkStart = i
                
            output += tmp
        
            i += 1
        
        output += """{0}<br><a href='chatcmd:///start http://aodevs.com/projects/view/14'>Get parser here</a>">DD {1}-{2}</a>""".format(whoreout, chunkStart, numPlayers)
        outputArr.append(output)
        return outputArr
    
    
    
    def getDcBothData2(self, data, dates, pausetime):
        return self.getDcDump(data, dates, pausetime)
    
    
    
    def getDcDump(self, data, dates, pausetime):
        start, end, duration = getFmtDates(dates)
        if duration == 0: return "Error, non existing time period"
        durDiv = (dates[1]-dates[0]).seconds / 60.    # For "per hour" division
        durDiv -= pausetime / 60.
        
        whoreout = ""
    
        numPlayers = 0
        totalDmg = 1            # Prevents division by zero, loss of accuracy is minimal    
        for P in data:
            if '?' in P:
                continue
            totalDmg += data[P]["dmg"]
            numPlayers += 1
        if numPlayers == 0: return "No players"
    
        avgDpm = number_format(totalDmg/durDiv)
        avgDmg = number_format(totalDmg/numPlayers)
        output = """<a href="text://<font color=#99CCFF>Time %s -> %s (%s)<br>Players: <font color=#cccc00>%d</font><br>Damage: <font color=#cccc00>%s</font> (<font color=#cccc00>%s</font>)<br>Average: <font color=#cccc00>%s</font> dmg/player<br><br><br>""" % (start, end, duration, numPlayers, number_format(totalDmg), avgDpm, avgDmg)
    
    
        # Sort by damage here
        dataset = sortByDamage(data)
    
        i = 1
        for name, dmg in dataset:
            #if i > 12:
            #    output += "Maximum 12 players on detailed stats."
            #    break
            #dmg = number_format( dmg )
            #name = P[0]
            
            tmpStr = ""
            who = data[name]["whois"]
            level = who[2]
            prof = who[1]
    
            
            percTotal = int(100*(dmg/float(totalDmg)))     # Percentage of total damage done (out of the team)
            
            
            # Calc % of critical hits, may be 0
            if data[name]["hits"] > 0:
                critPerc = data[name]["critHits"]/float(data[name]["hits"])*100
            else:
                critPerc = 0
                
            # Calc how much of total damage (self) done was from crits        
            try:
                critTotal = data[name]["critAmount"]/float(data[name]["dmg"])*100
            except ZeroDivisionError:
                critTotal = 0
            
            nh = data[name]["nanohits"]                     # Number of nano attacks
            nd = number_format(data[name]["nano"])          # Total nano damage
            try:                                            # Percentage of total dmg done
                np = data[name]["nano"] / float(data[name]["dmg"])*100
            except ZeroDivisionError:
                np = 0
            
            # Print out the messy output
            tmpStr += """<font color=#55AA55>%d.</font>  <font color=#cccc00>%s</font> <font color=#55AA55><font color=#10a5e5>%s</font> (<font color=#76DAFB>%d %s</font>)</font> - %d%% of total<br>%d normal hits, %s dpm<br>""" % (i, number_format(dmg), name, level, prof, percTotal, data[name]["hits"], number_format(dmg/durDiv))
            if data[name]["critHits"]:  tmpStr += """%d hits (%d%%) were critical hits, being %d%% of damage.<br>""" % (data[name]["critHits"], critPerc, critTotal)
            else:                       tmpStr += "0 critical hits<br>"
            tmpStr += """%d nanohits (%s dmg - %d%%)<br>""" % (nh, nd, np)
            for S in data[name]["spec"]:
                try:                        perc = data[name]["specdmg"][S]/float(data[name]["dmg"])*100
                except ZeroDivisionError:   perc = 0
                annoyingNum = number_format(data[name]["specdmg"][S])
                tmpStr +=  "%d %s (%s dmg - %.f%%)<br>" % (data[name]["spec"][S], S, annoyingNum, perc)
                
            # Pets
            if data[name]["pets"]:
                tmpStr += "Pets (%s dmg - %.f%%)<br>" % (number_format(data[name]["pets"]), float(data[name]["pets"])/data[name]["dmg"]*100)

            # Charms
            try:
                if data[name]["charms"]:
                    tmpStr += "Charms (%s dmg - %.f%%)<br>" % (number_format(data[name]["charms"]), float(data[name]["charms"])/data[name]["dmg"]*100)
            except KeyError: pass
                
            
            tmpDict = { 'lowtype':data[name]["lowtype"], 
                       'hightype':data[name]["hightype"], 
                       'lownum':number_format(data[name]["lownum"]), 
                       'highnum':number_format(data[name]["highnum"]) }
            tmpStr += """Lowest hit: {lownum} ({lowtype}) Highest hit: {highnum} ({hightype})<br>""".format(**tmpDict)
            
            tmpStr += "<br>"
            
            # If we can't fit everything, simply don't add anything else [no multi-page on detailed stats]
            if len(output + tmpStr) > 3976-len(whoreout): # 4096 byte limit, minus script data
                break
            output += tmpStr
            
            i += 1
        
        if numPlayers != i-1:
            return output + """{0}<br><a href='chatcmd:///start http://aodevs.com/projects/view/14'>Get parser here</a>">Detailed DD 1-{1} ({2})</a>""".format(whoreout, i-1, numPlayers)
        else:
            return output + """{0}<br><a href='chatcmd:///start http://aodevs.com/projects/view/14'>Get parser here</a>">Detailed DD 1-{1}</a>""".format(whoreout, i-1)
    
    
    def getDcHeal(self, data, dates, pausetime):
        return "Not implemented"
        
    def getDcProfs(self, stats, dates, pausetime):
        totalDmg = 1
        numProfs = 0
        for Prof in stats["?Prof"]:
            totalDmg += stats["?Prof"][Prof]
            if stats["?Prof"][Prof]:
                numProfs += 1
            
        start, end, duration = getFmtDates(dates)
        durDiv = (dates[1]-dates[0]).seconds / 60. / 60.    # For "per hour" division
        durDiv -= pausetime / 60.
        output = """<a href="text://<font color=#99CCFF>Time %s -> %s (%s)<br>Professions: <font color=#cccc00>%d</font><br>Damage: <font color=#cccc00>%s</font><br><br>""" % (start, end, duration, numProfs, number_format(totalDmg))
    
    
        # Sort by damage here
        dataset = []
        for P in stats["?Prof"]: dataset.append( (P, stats["?Prof"][P]) )
        dataset = sorted(dataset, key=itemgetter(1), reverse=True)
    
      
            
        i = 1
        for Prof, d in dataset:
            if d == 0: break        # End of sorted list
            dmg = number_format(d)
            perc = 100*(d/float(totalDmg))
            output += """<font color=#55AA55>%d.</font>  <font color=#cccc00>%s</font> <font color=#10a5e5>%ss</font> - %.f%% of total</font><br>""" % (i, dmg, Prof, perc)
            i += 1
        
        #
        
        whoreout = """<br><a href='chatcmd:///start http://aodevs.com/projects/view/14'>Get parser here</a>"""
        return output + '{0}">Profession stats</a>'.format(whoreout)
        
    def getDcTank(self, data, dates, pausetime):
        start, end, duration = getFmtDates(dates)
        totalDmg = 0
        
        # May be empty, god knows..
        try:
            data["?Tanks"]
        except KeyError:
            return "No tanking stats recorded"
        
        for P in data["?Tanks"]:
            totalDmg += data["?Tanks"][P]
            
        output = """<a href="text://<font color=#99CCFF>Time %s -> %s (%s)<br><br>Total <font color=#cccc00>%s</font> dmg to players<br><br>Players that has taken most damage:<br>""" % (start, end, duration, totalDmg)
        
        dataset = sorted(data["?Tanks"].items())
        dataset = sorted(dataset, key=itemgetter(1), reverse=True)
        i = 1
        for name, dmg in dataset:

            # There's a chance we dont have whois info on him, if he never did any damage..!
            try: who = data[name]["whois"]
            except: who = ("Unknown", "Unknown", 0)
            
            perc = 100*(dmg/float(totalDmg))
            output += """<font color=#55AA55>_%d.</font>  <font color=#cccc00>_ _%s</font> <font color=#10a5e5>%s</font> (<font color=#76DAFB>%d %s</font>) - %.f%%<br>""" % (i, number_format(dmg), name, who[2], who[1], perc)
            i += 1
            
        whoreout = """<br><a href='chatcmd:///start http://aodevs.com/projects/view/14'>Get parser here</a>"""
        return output + """</font>{0}">Tankstats</a>""".format(whoreout)
    
    
    def getDcHelp(self, online):
        """Prints the /dc command ingame, small blob of text with links to available commands"""
        wp = ""
        
        if online: activeStr = "<font color=green>(Active)</font>"
        else: activeStr = "(Inactive)"
        
        return """<a href="text://<font color=#99CCFF>--- Announce Stats --- <br>
<a href='chatcmd:///dcDump'>Detailed damage</a><br>
<a href='chatcmd:///dcRaid'>Raid damage</a><br>
<a href='chatcmd:///dcBoth'>Detailed + Raid damage</a><br>
<a href='chatcmd:///dcTank'>Tanking stats</a><br>
<a href='chatcmd:///dcProfs'>Profession stats</a><br><br>

--- View Stats --- <br><a href='chatcmd:///dcDumpe'>Detailed damage</a><br>
<a href='chatcmd:///dcRaide'>Raid damage</a><br>
<a href='chatcmd:///dcBothe'>Detailed + Raid damage</a><br>
<a href='chatcmd:///dcTanke'>Tanking stats</a><br>
<a href='chatcmd:///dcExpe'>Experience gains</a><br>
<a href='chatcmd:///dcProfse'>Profession stats</a><br>
-------<br>
<a href='chatcmd:///loot'>Announce loot</a><br>
<a href='chatcmd:///eloot'>View loot</a><br>
-------<br>
<a href='chatcmd:///shopm'>Open shop menu</a><br>
{0}
">DcDump</a> {1}""".format(wp, activeStr).replace("\n", '')
    
    
    # Write script to file
    def WriteScripts(self, file, data):
        """
        @param file: Full path to filename
        @param data: data to write
        @return: True / False
        Simple wrapper for writing scripts to file
        """ 
        try:
            f = open(file, "w")
            f.write(data)
            f.close()
        except: #IOError, WindowsError (Access denied)
            print "Error writing to file %s" % file
            return False
        return True
        
        
    
    def getPrefix(self, group):
        if group == 'Default': prefix = ""
        #elif group == 'Team': prefix = "/t "
        #elif group == 'Orgchat': prefix = "/o "
        #elif group == 'Raid': prefix = '/ch raid\n'
        #elif group == 'iraid': prefix = '/ch iraid\n'
        else: prefix = '/ch "{0}"\n'.format(group)
        return prefix


    # Input:
    # Full path to AO
    # Data about players
    # Stats about self (xp gain, etc)
    # Tuple with two datetime objects
    def AddScripts_Real(self, pathToAo, data, stats, period, online, group="Default"):
        """
            @param pathToAo: Full path to anarchy online installation (with anarchy.exe)
            @param data: Dictionary with data from Processing module
            @param stats: Dictionary with statistics from Processing module
            @param period: Tuple of two timestamps (epoch)
            
            Writes input data to AOPATH\scripts
            Use /dc ingame to access available commands    
        """
        # Make sure we really have data! (1 is "?Tanks", so need at least 2)
        if len(data) <= 1:
            print "AddScripts() called on zero data, ignored.";
            return
        

        # Make sure the scripts folder exists
        pathToAo = os.path.join(pathToAo, "scripts")
        if not os.access(pathToAo, os.F_OK):
            try: 
                print "[Scripts] Making dir %s" % pathToAo
                os.makedirs( "dcDumps" )
            except:
                print "[Scripts] Failed creating scripts dir at: %s" % pathToAo 
                return False
            
        if not os.access(os.path.join(pathToAo, "dcDumps"), os.F_OK):
            try: 
                print "[Scripts] Making dir %s" % os.path.join(pathToAo, "dcDumps")
                os.makedirs( os.path.join(pathToAo, "dcDumps") )
            except:
                print "[Scripts] Failed creating scripts dir at: %s" % pathToAo 
                return False
            

        dates = ( datetime.datetime.fromtimestamp(period[0]),
                  datetime.datetime.fromtimestamp(period[1]))

        
        if dates[0] > dates[1]:
            dates = (dates[1], dates[0])
            
        # Minimum 1 second duration, prevents all kinds of nasty div-zero
        if dates[0] == dates[1]: 
            #dates = (dates[0], datetime.datetime.fromtimestamp(period[1]+1))
            print "[Scripts] Fight duration is 0 seconds, aborting /dc scripts.."
            return True
        
        'A bit redundant, but backward-compatible'
        try:
            ptime = data['?Paused']
        except:
            ptime = 0
            
        prefix = self.getPrefix(group)

        
        
        #if not os.access(os.path.join(pathToAo, "dcBoth"), os.F_OK):
        if not self.WriteScripts(os.path.join(pathToAo,"dcBoth"),   prefix+"/dcDumps/dcBoth1"):    
            return False
        if not os.access(os.path.join(pathToAo, "dcBothe"), os.F_OK):
            if not self.WriteScripts(os.path.join(pathToAo,"dcBothe"),  "/dcDumps/dcBothe1"):   
                return False
        #if not os.access(os.path.join(pathToAo, "dcRaid"), os.F_OK):
        if not self.WriteScripts(os.path.join(pathToAo,"dcRaid"),   prefix+"/dcDumps/dcRaid1"):    
            return False
        if not os.access(os.path.join(pathToAo, "dcRaide"), os.F_OK):
            if not self.WriteScripts(os.path.join(pathToAo,"dcRaide"),   "/dcDumps/dcRaide1"):  
                return False
        #if not os.access(os.path.join(pathToAo, "dcDump"), os.F_OK):
        if not self.WriteScripts(os.path.join(pathToAo,"dcDump"),   prefix+"/dcDumps/dcDump1"):    
            return False
        
        if not os.access(os.path.join(pathToAo, "dcDumpe"), os.F_OK):
            if not self.WriteScripts(os.path.join(pathToAo,"dcDumpe"),  "/dcDumps/dcDumpe1"):   
                return False
            
        #if not self.WriteScripts(os.path.join(pathToAo,"dcExp"),         self.getDcExp(stats, dates, ptime)):    return False
        if not self.WriteScripts(os.path.join(pathToAo,"dcExpe"),   "/text "+  self.getDcExp(stats, dates, ptime)):    return False
        if not self.WriteScripts(os.path.join(pathToAo,"dcProfs"),   prefix+   self.getDcProfs(stats, dates, ptime)):  return False
        if not self.WriteScripts(os.path.join(pathToAo,"dcProfse"), "/text "+  self.getDcProfs(stats, dates, ptime)):  return False
        if not self.WriteScripts(os.path.join(pathToAo,"dcTank"),   prefix+    self.getDcTank(data, dates, ptime)):    return False
        if not self.WriteScripts(os.path.join(pathToAo,"dcTanke"),  "/text "+  self.getDcTank(data, dates, ptime)):    return False 

        # /dc command    
        if not self.WriteScripts(pathToAo+"\\dc",  "/text "+       self.getDcHelp(online)): return False
        if online:
            if not self.WriteScripts( os.path.join(pathToAo, "dcStatus"),  "/text DCDump is <font color=green>currently parsing!</font>"): return False
        else:
            if not self.WriteScripts( os.path.join(pathToAo, "dcStatus"),  "/text DCDump is <font color=red>not parsing!</font>"): return False
        
        # Subfolder scripts
        pathToDumps = os.path.join(pathToAo, "dcDumps")
        #if not os.access(pathToDumps, os.F_OK):
        #    os.makedirs(pathToDumps)
            
            
        """
        raidData = 
        raidout = ""
        for i in xrange(1, len(raidData)):
            raidout += "/dcDumps/dcRaide%d\n"%i
            """
        #self.WriteScripts(pathToAo+"\\dcRaide", raidout);
            
        i = 1
        scriptData = self.getRaidData(data, dates, ptime)
        scriptData.append(self.getDcDump(data, dates, ptime))
        for Filedata in scriptData:
            if i < len(scriptData):
                if not self.WriteScripts(pathToDumps+"\\dcBoth%d"%i,            Filedata+"\n/dcDumps/dcBoth%d"%(i+1) ): return False
                if not self.WriteScripts(pathToDumps+"\\dcBothe%d"%i, "/text "+ Filedata+"\n/dcDumps/dcBothe%d"%(i+1) ): return False
            else:
                if not self.WriteScripts(pathToDumps+"\\dcBoth%d"%i,            Filedata ): return False
                if not self.WriteScripts(pathToDumps+"\\dcBothe%d"%i, "/text "+ Filedata ): return False
            i += 1
    
        #self.WriteScripts(pathToDumps+"\\dcBoth2",            self.getDcBothData2(data, dates, ptime))
        #self.WriteScripts(pathToDumps+"\\dcBothe2", "/text "+ self.getDcBothData2(data, dates, ptime))
        
        # Detailed stats
        if not self.WriteScripts(pathToDumps+"\\dcDump1",            self.getDcDump(data, dates, ptime)): return False
        if not self.WriteScripts(pathToDumps+"\\dcDumpe1", "/text "+ self.getDcDump(data, dates, ptime)): return False
        
        
        # Raid stats (multi page support)
        i = 1
        scriptData = self.getRaidData(data, dates, ptime)
        for Filedata in scriptData:
            if i < len(scriptData):
                if not self.WriteScripts(pathToDumps+"\\dcRaid%d"%i,            Filedata+"\n/dcDumps/dcRaid%d"%(i+1)): return False
                if not self.WriteScripts(pathToDumps+"\\dcRaide%d"%i, "/text "+ Filedata+"\n/dcDumps/dcRaide%d"%(i+1)): return False
            else:
                if not self.WriteScripts(pathToDumps+"\\dcRaid%d"%i,            Filedata): return False
                if not self.WriteScripts(pathToDumps+"\\dcRaide%d"%i, "/text "+ Filedata): return False

            i += 1
            
        return True
    

        
    
    def AddOnlineStatus(self, pathToAo, online):
        appdata = getAppdataAO()
        if not appdata: appdata = pathToAo
        else: appdata = os.path.join(appdata, "..")
        
        if not os.access(pathToAo, os.F_OK) and not os.access(appdata, os.F_OK):
            print "[Scripts] Error: Could not find a scripts folder with access rights"
            return False
        
        if online:
            od = "/text DCDump is <font color=green>currently parsing!</font>"
        else:
            od = "/text DCDump is <font color=red>not parsing!</font>"
            
        for path in set([appdata]):
            # /dc command    
            if not self.WriteScripts( os.path.join(path, "scripts", "dc"),  "/text "+       self.getDcHelp(online)): 
                print "[Scripts] Could not write /dc"
            
            # /dcStatus
            if not self.WriteScripts( os.path.join(path, "scripts", "dcStatus"),  od): 
                print "[Scripts] Could not write /dcStatus"
    # End of function

        
    
    # Wrapper function for AddScripts_Real
    def AddScripts(self, pathToAo, data, stats, period, online, group):
        # Check if AO folder exists
        appdata = getAppdataAO()
        appdata = os.path.join(appdata, "..")

        if not os.access(pathToAo, os.F_OK) and not os.access(appdata, os.F_OK):
            print "[Scripts] Error: Could not find a scripts folder with access rights"
            return False
        
        # Try adding scripts to both regular AO path and Appdata
        successA = self.AddScripts_Real(pathToAo, data, stats, period, online, group)
        successB = self.AddScripts_Real(appdata, data, stats, period, online, group)
        
        if successA or successB:
            return True
        else:
            print "[Scripts] Error: Could not write scripts to neither AO path nor Appdata"
            return False 
        
        
    def getItemName(self, id):
        __SQL = self.__CONN.cursor()
        __SQL.execute("select name from items where id = ?", (id,))
        
        ret = "?"
        for name in __SQL:
            ret = name[0]

        if ret == '?':
            ret = getItemnameFromXyphos(id)
        __SQL.close()
        return ret

    def OpenBackpack(self, pathToAO, charid, containerid, items):
        print "OpenBackpack called!"
        if len(self.accids) == 0: 
            self.accids = Chars.GetAccFromID(pathToAO, False)
            
        if not charid in self.accids:
            return False
        else:
            accname = self.accids[charid]
        
            
        name = None
        path = os.path.join(getAppdataAO(), accname, "Char{0}".format(charid), "Containers", "Container_51017x{0}.xml".format(containerid))
        
        try: ts = os.stat(path).st_mtime
        except: 
            return False

        
        # Get backpack name
        if not containerid in self.backpacks:
            name = self.getBackpackName(pathToAO, accname, charid, containerid)
            self.backpacks[containerid] = (name, ts)

        # Check if we need to update backpack name
        elif self.backpacks[containerid][1] != ts:
            name = self.getBackpackName(pathToAO, accname, charid, containerid)
            self.backpacks[containerid] = (name, ts)
        else:
            name = self.backpacks[containerid][0] 


        # If the name is None, lets just bail now.
        if not name: 
			return False
           
        if 'shop:' in name.lower() and not containerid in self.shoppacks:
            # Add to shoppacks
            self.shoppacks[containerid] = (name.replace('SHOP:', '').strip(), items)
            print "[Scripts] Adding Shop:",name            
        
        if not 'shop:' in name.lower() and containerid in self.shoppacks:
            # Remove from shoppacks
            print "[Scripts] Removing",name
            del self.shoppacks[containerid]
            
        i = 1
        for entry in self.shoppacks:
            text = ('My stuff for sale:', self.shoppacks[entry][0], 'shop{0}'.format(i))
            self.AddShopLootScript(pathToAO, self.shoppacks[entry][1], text, "Default")
            i += 1
            
        if len(self.shoppacks) == 0:
            shopscript = 'You have no registered shops.<br><br>'
            shopscript += '1) Put everything you want to sell into a backpack<br>'
            shopscript += '2) Rename the backpack to &quot;Shop: Something Here&quot;<br>'
            shopscript += '3) Zone and open the backpack.<br><br>'
            shopscript += 'The backpack names and contents will only update once per zoning.<br>'        
            shopscript += '''It should now be available via /shopm<br>'''
            shopscript += '''If you change the contents of the backpack, please zone then re-open it.<br>'''
            
        else:
            i = 1
            shopscript = "--- Announce shops ---<br>"
            for entry in self.shoppacks:
                shopscript += '''<a href='chatcmd:///shop{1}'>Announce: {0}</a><br>'''.format(self.shoppacks[entry][0], i)
                i += 1
            
            i = 1
            shopscript += "<br>--- View shops ---<br>"
            for entry in self.shoppacks:
                shopscript += '''<a href='chatcmd:///eshop{1}'>View: {0}</a><br>'''.format(self.shoppacks[entry][0], i)
                i += 1
        

        # Write to /shopm
        if not self.WriteScripts( os.path.join(getAppdataAO(), '..', 'scripts', 'shopm'),  '/text <a href="text://<font color=yellow>{0}</font>">Shop details</a>'.format(shopscript)):
            print "[Scripts] Failed to write /shopm"   
            return False
        else:
            print "[Scripts] Debug: OK to write /shopm (shops: {0}, {1}".format(len(self.shoppacks) ,os.path.join(getAppdataAO(), '..', 'scripts', 'shopm'))
            return True
        
        

    '''
    Returns the name of a given container, or None.
    '''
    def getBackpackName(self, pathToAO, accname, charid, containerID):
        path = os.path.join(getAppdataAO(), accname, "Char{0}".format(charid), "Containers", "Container_51017x{0}.xml".format(containerID))
        if not os.access(path, os.F_OK): return None
        try: data = open(path).read()
        except: 
            print "[Scripts] Could not open file Container_51017x{0}.xml".format(containerID)
            return None
        
        try: 
            return re.search(r"""name="container_name" value='&quot;(.*?)&quot;'""", data, re.I).groups()[0]
        except:
            return None


    
    # Adds /loot
    def AddLootScript(self, pathToAo, data, targetWindow):
        text = ('Item drops for last corpse:', 'Click to see drops', 'loot')
        return self.AddShopLootScript(pathToAo, data, text, targetWindow)
    
    # Adds /loot or /shopm
    def AddShopLootScript(self, pathToAo, data, text, targetWindow):
        # Make sure we got SQL access to item DB
        if self.__CONN == None:
            self.__CONN = sqlite3.connect("itemdb")
            __SQL = self.__CONN.cursor()
            __SQL.execute("CREATE TABLE if not exists items (id INTEGER NOT NULL PRIMARY KEY UNIQUE, name TEXT)")
            __SQL.close()
        
        # Check if AO folder exists
        appdata = getAppdataAO()
        appdata = os.path.join(appdata, "..")
        
        if not os.access(pathToAo, os.F_OK) and not os.access(appdata, os.F_OK):
            print "[Scripts] Error: Could not find a scripts folder with access rights"
            return False
        
        filedata = """<a href="text://{0}<br>{1}<br>""".format( datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S"), text[0] )
        for itemdata in data: 
            item = itemdata.split('/')
            #try:
            itemname = self.getItemName( int(item[0]) )
            filedata += "<a href='itemref://%d/%d/%d'>QL%d %s</a><br>" % (int(item[0]), int(item[1]), int(item[2]), int(item[2]), itemname)
            #except:
                #print "[Scripts] Error.. ", sys.exc_info()[0] , " for", item[0],item[1],item[2]
            
        filedata += """<br><a href='chatcmd:///start http://aodevs.com/projects/view/14'>Get parser here</a>">{0}</a>""".format(text[1])
        #print filedata
        
        prefix = self.getPrefix(targetWindow)
        
        
        # Make sure the scripts folder exists
        path = os.path.join(appdata, '..', "scripts")
        if not os.access(appdata, os.F_OK):
			try: 
				print "[Scripts] Making dir %s" % os.path.join(path, "dcDumps")
				os.makedirs( os.path.join(path, "dcDumps") )
			except:
				#print "[Scripts] Failed creating scripts dir at: %s" % pathToAo 
				print "[Scripts] Error: Could not write loot script to neither AO path nor Appdata"
				return False
			
        if self.WriteScripts(os.path.join(appdata, "scripts", text[2]), prefix+filedata):
			success = True
			#print "wrote to {0}".format(os.path.join(appdata, "scripts", "loot"))
			self.WriteScripts(os.path.join(appdata, "scripts", "e{0}".format(text[2])), '/text '+filedata)
			return True
        else:
			print "could not write to {0}".format(os.path.join(appdata, "scripts", text[2]))
			return False

        
__CONN = sqlite3.connect("itemdb")
def getItemName(id):
    __SQL = __CONN.cursor()
    __SQL.execute("select name from items where id = ?", (id,))
    
    ret = "?"
    for name in __SQL:
        ret = name[0]

    if ret == '?':
        ret = getItemnameFromXyphos(id)
    __SQL.close()
    return ret

if __name__ == "__main__":
    print "No test data available"
    print getItemName(293993)    
