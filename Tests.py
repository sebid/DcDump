import os, sys, platform
import Chars

# Sets stdout to runtime.txt, does not restore stdout on complete!
def enableLogging():
    sys.stdout = open("runtime.log.txt", "w", 0)
    #logfile = open("runtime.txt", 'w', 0)
    #sys.stdout = os.fdopen(sys.__stdout__.fileno(), 'w', 0)
    #os.dup2(logfile.fileno(), sys.__stdout__.fileno())

def runTests():
    # Redirect stdout to logfile 
    restore = sys.stdout
    logfile = open("parser.txt", 'w', 0)
    sys.stdout = os.fdopen(sys.__stdout__.fileno(), 'w', 0)
    os.dup2(logfile.fileno(), sys.__stdout__.fileno())

    def getAppdataAO(path):
        for root, dirs, files in os.walk(path):
            a = os.path.basename(root).lower() == "prefs"
            b = os.access(os.path.join(root, "prefs.xml"), os.R_OK)
            if a and b:
                return root
        return "Prefs not found"

    appdata = os.environ['appdata']
    pathA = os.path.join(appdata, "..", "Local", "VirtualStore", "Program Files (x86)", "")
    pathB = os.path.join(appdata, "..", "Local", "VirtualStore", "")
    print "Appdata Path:"
    print "Code in use:",
    print getAppdataAO(pathA)
    print "Test code:",
    print getAppdataAO(pathB)
    # AO path and AO prefs
    aoPath = Chars.AutodetectAO()
    if aoPath == "-1": print "Could not detect AO running, skipping AO:Prefs"
    else:
        print "AO Path: %s" % aoPath

    # List number of toons and accounts
    dataset = Chars.GetAccFromID(aoPath)
    dictID = {}
    dictAcc = {}
    for ID in dataset:
        ACC = dataset[ID]
        dictID[ID] = 0
        dictAcc[ACC] = 0
    print "Accounts detected: %d" % len(dictAcc)
    print "Toons detected: %d" % len(dictID)

    #for K in os.environ:
        #print K, os.environ[K]

    print "Appdata:", os.environ['LOCALAPPDATA']
    print "Progfiles:", os.environ['PROGRAMFILES(X86)']
    print "OS: ",platform.system(), platform.win32_ver()[0], "(%s)" % platform.win32_ver()[1]
    
    from DebugSettings import Build_Version, Build_ID
    print "Parser v%s build %d" % (Build_Version, Build_ID)

    sys.stdout = restore
    logfile.close()