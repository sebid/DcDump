import threading
import Queue
import time
import Processing
import WhoIs
from DebugSettings import Debug
from multiprocessing import JoinableQueue, Process, cpu_count


class WhoIsThread (threading.Thread):
    """
    Whois thread, does a mass whois of own characters
    """
    def __init__(self, toonlist):
        threading.Thread.__init__(self)
        self.toonlist = toonlist
    def run(self):
        whoisModule = WhoIs.WhoIs("RK1", True)
        whoisModule.limitedMassWhois( self.toonlist )
        return


def getLatestTimestamp(data):
    import re
    'Find the newest timestamp'
    i = 0
    match = None
    while match == None and i > -len(data):
        i -= 1
        match = re.search(r"""(?P<TS>\d+)]""", data[i], re.I)

    'No timestamp could be found'
    if not match: 
        return -1
    else:
        return int(match.group('TS'))

class WorkerThread (threading.Thread):
    """
    Worker thread to avoid stalling the user interface with blocking commands
    """
    def __init__(self, aoPath, toon, logfile, taskQueue, feedback, dimension, allowMobs, allowLowdmg, targetGroup):
        """
        @param aoPath: Full path to Anarchy Online, for writing to /scripts/
        @param toon: Name of own character, for renaming "You"
        @param logfile: Full path to logfile that needs to be parsed
        @param taskQueue: Input tasks (such as "Quit")
        @param feedback: Messages to GUI, format ("Type", Data)
        @param live: [Optional], Continue live updates of logfile
        """
        threading.Thread.__init__(self)
        self.tasks = taskQueue
        self.feedback = feedback
        
        self.logfilename = logfile
        self.myname         = toon
        self.aopath         = aoPath
        self.dim            = dimension
        self.allowMobs      = allowMobs
        self.allowLowdmg    = allowLowdmg
        self.targetWindow   = targetGroup

    def setTargetWindow(self, targetGroup):
        self.targetWindow   = targetGroup
        #print "New target window is now",targetGroup

    # Pretty much identical to run(), just chopped down to bare minimum..
    # Ret: data, timestamp, +length
    def doLive(self, lastLength):
        """
        @param lastLength: Last length of file (only read newly logged lines)
        @return: Processed data, current timestamp, current file length (-1 if finished)
        Opens the DD logfile and parses all lines up to lastLength
        No multithreading is performed, as its intended for minor(live) updates only.  
        """
        try:
            logfile = open(self.logfilename, "r")
            filedata = logfile.readlines()
            filedata = filedata[lastLength:]
            logfile.close()
        except IOError:
            return [], -1

        processedData = []

        # No reverse, already have the starting point and such.
        for L in filedata:
            data = L.strip()

            # Attempt to match data (no match for chat, petspam, logout messages, etc)
            ret = Processing.getMatch(data)
            if ret == None: continue 

            # Store data and continue loop
            processedData.append(ret)
        
        # END-WHILE
        return processedData, len(filedata)


    def run(self):
        """
        Inputs:     ("Stop",)
        Feedbacks:  ("Info", "Details")
                    ("Error", "Details")
                    ("Data", stats, data, period, myname)
        """
        filedata = []
        try:
            logfile = open(self.logfilename, "r")
            filedata = logfile.readlines()
            logfile.close()
            self.feedback.put(("Info","Parsing.. use /dc ingame for realtime stats"))
        except IOError:
            self.feedback.put(("Error", "Could not open file \"%s\"" % self.logfilename))
            return

        # Script parser
        import Scripts
        s = Scripts.Script()

        # Timestamp chunk
        startTime       = int(time.time())
 
        # Output data
        processedData = []

        filedata.reverse() # Reading from the end (newest)
        dataset = Processing.SumParsedData([], self.myname, self.dim, startTime, self.allowMobs, self.allowLowdmg)

        # If we had no log lines to begin with, the fight starts now!
        if dataset == -1: # WARNING: Never triggers! always processing 
            dataset.period = (startTime, time.time(), 1)
            print "Has hell frozen over? /tell eviltrox asap"

        done                = False
        lastLength          = len(filedata)
        lastCheck           = time.time()       # Prevent spamming I/O
        paused              = False
        pausedDuration      = 0 # Duration of current pause
        pauseDurationTotal  = 0 # Used to fix DPM in scripts

        s.AddOnlineStatus(True)
        while not done:
            # Process messages from GUI thread
            while not self.tasks.empty():
                m = self.tasks.get()
                if m == "Stop":
                    done = True
                    print "[Threadz] Received stop cmd"
                    break

                elif m == 'Pause':
                    paused = not paused
                    print "[Threadz] Got a pause request, new status:", paused
                    # Store the current time [or add to total if unpausing]
                    if paused:
                        pausedDuration = time.mktime(time.gmtime())
                    else:
                        pauseDurationTotal += time.mktime(time.gmtime()) - pausedDuration 

                else:
                    print "Unknown Message:", m # Should never really occur

            # Handle quits [the other break is already inside a while loop]
            if done:
                break

            if paused:
                data, deltaLength = self.doLive(lastLength)
                if deltaLength != -1: lastLength += deltaLength
                continue

            # If N seconds has nor elapsed, or were paused.. skip processing
            if lastCheck+6 >= time.time():
                time.sleep(0.15)
                continue

            print "[Threadz] 6 sec elapsed.. parsing again..",

            # Check file for new data
            data, deltaLength = self.doLive(lastLength)
                
            # Check how many lines we processed
            if deltaLength != -1: lastLength += deltaLength
            else: done = True

            # Append the new data
            for L in data:
                processedData.append(L)

            lastCheck = time.time()
            print "parsed %d new lines.." % deltaLength

            # If we processed more than 1 damage line, update the logs again..
            if deltaLength >= 1:
                dataset = Processing.SumParsedData(processedData, self.myname, self.dim, startTime, self.allowMobs, self.allowLowdmg)
                dataset.globData['?Paused'] = pauseDurationTotal
                dataset.period = (dataset.period[0], time.time())

                s.AddScripts(dataset.globData, dataset.globStats, dataset.period, True, self.targetWindow)
            else:
                s.AddOnlineStatus(True)

        # [End while]

        # Compile new dataset
        dataset = Processing.SumParsedData(processedData, self.myname, self.dim, startTime, self.allowMobs, self.allowLowdmg)
        self.feedback.put(("Info","Finished"))

        # Report whatever data we have, unless PlayerCount == 0 or Date == 1970  (no data)
        # 1=?Tanks, need at least 2.
        if len(dataset.globData) <= 1 or dataset.period[0] == 0:
            print "[Threadz] Finished parse with 0 players, ignoring.."
            self.feedback.put(("Info", "Discarded parse, found no players.."))  
        else:
            self.feedback.put(("Data", dataset.globStats, dataset.globData, dataset.period, self.myname))
            dataset.globData['?Paused'] = pauseDurationTotal
            dataset.period = (dataset.period[0], time.time())
            if not s.AddScripts(dataset.globData, dataset.globStats, dataset.period, False, self.targetWindow):
                self.feedback.put(("Info", "Failed to write /dc scripts"))  
                
            self.feedback.put(("Info", "Parse complete"))   
            print "[Threadz] Parser complete"

        return
"""
if __name__ == "__main__":
    tasks = Queue.Queue()
    feedback = Queue.Queue()
    #tasks.put( ("Stop", 0) )

    thread = WorkerThread(r"path", "toon", r"log", tasks, feedback, False)
    thread.start()


    #gTaskQueue.join()
    while thread.isAlive():
        time.sleep(0.1)
    print "All tasks complete, t=%d" % tasks.qsize()
    print "Thread feedback, f=%d" % feedback.qsize()
    while not feedback.empty():
        n = feedback.get()
        if n[0] != 'Data':
            print "Thread says:",n

        if n[0] == "Data":
            import Scripts
            period = n[3]
            print "Period: ",period
            import datetime
            print datetime.datetime.fromtimestamp(period[0])
            print datetime.datetime.fromtimestamp(period[1])
"""