import sys, threading, os
import ctypes
import win32gui, win32api, win32con, ctypes.wintypes
from Chars import UpdateToonsDB, getDimension
import Scripts, re


import WhoIs
class COPYDATASTRUCT(ctypes.Structure):
    _fields_ = [
        ('dwData', ctypes.wintypes.LPARAM),
        ('cbData', ctypes.wintypes.DWORD),
        ('lpData', ctypes.c_void_p)
    ]
PCOPYDATASTRUCT = ctypes.POINTER(COPYDATASTRUCT)

# Ref: http://stackoverflow.com/questions/5249903/receiving-wm-copydata-in-python
# Ref http://docs.python.org/library/ctypes.html?highlight=ctypes
class Listener:
    def __init__(self, feedback_control):
        message_map = { win32con.WM_COPYDATA: self.OnCopyData }
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = message_map
        wc.lpszClassName = 'DCDumpLogger'
        self.pathToAO = ""
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        classAtom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow (
            classAtom,
            "win32gui test",
            0, 0, 0,
            win32con.CW_USEDEFAULT, 
            win32con.CW_USEDEFAULT,
            0, 0, hinst, None)
        print "[Listen.] HWND:",self.hwnd

        self.targetWindow = 'Default'
        
        self.feedback = feedback_control # must have a .SetLabel()

        # Remote DLL
        dllname = self.GetDllPath("Listener.dll")
        if dllname == None:
                print "[Listen.] Could not find Listener.dll"
                raise Exception("File not found: Listener.dll")
        c_dll = ctypes.cdll.LoadLibrary(dllname)

        # Set function return types
        #c_dll.isPlayer.restype          = ctypes.c_int
        c_dll.getPlayerName.restype     = ctypes.c_int
        c_dll.GetAOProcID.restype       = ctypes.c_char_p
        c_dll.InjectDLL.restype         = ctypes.c_bool
        c_dll.GetLevelID.restype        = ctypes.c_bool
        c_dll.getMessageID_s.restype    = ctypes.c_uint
        c_dll.getLootInfo.restype       = ctypes.c_char_p
        self.c_dll = c_dll

        self.previouslyInjected = [] # AO process IDs
        self.previouslyListened = [] # AO toon IDs

        self.whoisNames         = {}
        self.whoisIDs           = {}

        self.professions = ('?0', 'Soldier', 'Martial Artist', 'Engineer', 'Fixer', 'Agent', 'Adventurer', 'Trader', 'Bureaucrat', 
                                    'Enforcer', 'Doctor', 'Nano-Technician', 'Meta-Physicist', '?13', 'Keeper', 'Shade'
                                   )

        self.w = WhoIs.WhoIs('RK1', True)
        self.s = Scripts.Script()

        """	
        { // Allow for messages from lower to higher.. bla bla..
			typedef  BOOL (WINAPI *ChangeWindowMessageFilterFunc)(UINT message, DWORD dwFlag);
      	  ChangeWindowMessageFilterFunc f = (ChangeWindowMessageFilterFunc)GetProcAddress(LoadLibrary("user32.dll"), "ChangeWindowMessageFilter");
      	  if (f) {
           	 (f)(WM_COPYDATA, MSGFLT_ADD);
        	}
    	}"""


    def setAOPath(self, path):
        self.pathToAO = path


    def WhoisCheckOK(self, id):
        if not id in self.whoisNames: return
        if not id in self.whoisIDs: return
        level = self.whoisIDs[id][0]
        prof = self.professions[self.whoisIDs[id][1]]
        dim = getDimension( self.whoisIDs[id][2] )
        name = self.whoisNames[id]
        print "[Listen.] Whois detected: (%d, '%s', '%s', %d)" % (id, name, prof, level)
        if dim == None: print "[Listen.] Could not detect dimension for whois record"
        else: self.w.updateRecordsX(name, prof, level, dim)


    def WhoisAddName(self, id, name):
        if id in self.whoisNames: return
        
        self.whoisNames[id] = name
        self.WhoisCheckOK(id)


    def setTargetWindow(self, target):
        self.targetWindow = target


    def WhoisAddProf(self, id, level, prof, sid):
        if id in self.whoisIDs: return
        try: name = self.whoisNames[id]
        except: name = "Unknown"
        if prof == 13 or prof == 0: 
            print "[Listen.] WHAT CLASS IS THIS?? [%d] is '%s' level %d Prof %s / %s" % (id, name, level, self.professions[prof], prof)
            return
        else:
            print "[Listen.] DEBUG: [id: %d, name: %s, level: %d, Prof: %s]" % (id, name, level, self.professions[prof])

        self.whoisIDs[id] = (level, prof, sid)
        self.WhoisCheckOK(id)


    def OnCopyData(self, hwnd, msg, wparam, lparam):
        c_dll = self.c_dll
        pCDS = ctypes.cast(lparam, PCOPYDATASTRUCT)
        if pCDS.contents.dwData != 1: return 1			# We only want client RECV not SEND

        # Identify message
        messageID = c_dll.getMessageID_s(ctypes.c_void_p(pCDS.contents.lpData), ctypes.c_int(pCDS.contents.cbData))

        # Handle item loot [loot table, not looting]
        if messageID == 1314089334: # itemloot
            bufsize     = ctypes.c_int( 34 * 32 ) # max 32 items for now
            buffer      = ctypes.create_string_buffer( bufsize.value )
            res         = self.c_dll.getLootInfo(ctypes.c_void_p(pCDS.contents.lpData), ctypes.c_int(pCDS.contents.cbData), buffer, bufsize)
            returndata  = buffer.value.strip().split(":")
            charid       = int(returndata[0])
            containerid  = int(returndata[1])
            items        = returndata[2].split("\n")
            if '' in items: items.remove('')

            # Loot
            print "recv contid:",containerid
            if containerid == 0 and len(items) > 0:
                    self.s.AddLootScript(items, self.targetWindow)
            elif containerid != 0 and len(items) > 0:
                self.s.OpenBackpack(charid, containerid, items)            

            #for item in items: print item,":", getItemnameFromID( int(item.split('/')[0]) )

        # Check if this message contains a level / prof
        if messageID == 1295524910:  # SMSG_TBLOB
            id      = ctypes.c_uint()   # Target charid?
            level   = ctypes.c_uint()
            prof    = ctypes.c_uint()
            sid     = ctypes.c_uint()   # Self charid
            res = c_dll.GetLevelID(
                                ctypes.c_void_p(pCDS.contents.lpData), 
                                ctypes.c_int(pCDS.contents.cbData),
                                ctypes.byref(id),
                                ctypes.byref(level),
                                ctypes.byref(prof),
                                ctypes.byref(sid))
            if res:
                self.WhoisAddProf(id.value, level.value, prof.value, sid.value)

        # if messageID != MSG_MOB_SYNC
        if messageID != 656095851: return 1

        # Check if this is a player
        buffLen = 256
        buffer = ctypes.create_string_buffer(buffLen)
        id = ctypes.c_uint()
        res = c_dll.getPlayerName(
							ctypes.c_void_p(pCDS.contents.lpData), 
							ctypes.c_int(pCDS.contents.cbData),
							ctypes.byref(id),
							#ctypes.c_char_p(buffer),
							buffer,
							ctypes.c_int(buffLen))

        if res < 0: return 1 # Unknown message
        elif res == 0:
            if id.value not in self.previouslyListened:
                print "[Listen.] Player detected: ",id.value,"=",buffer.value

                if UpdateToonsDB(id.value, buffer.value):
                    self.previouslyListened.append(id.value)
                    self.feedback.SetLabel('Detected new character: %s' % buffer.value)
                else:
                    self.feedback.SetLabel('Failed to update character: %s (Hit manage?)' % buffer.value)
            else:
                print "[Listen.] Player detected (ignored): ",id.value,"=",buffer.value

        else:
            self.WhoisAddName(id.value, buffer.value)

        return 1


    def InjectDll(self, event=0):
        c_dll = self.c_dll
        # Grab AO process IDs (for injection)
        buffer = ctypes.create_string_buffer(256)
        res = c_dll.GetAOProcID(
        					buffer,
        					256)

        ids = buffer.value.split("\n")

        i = 0
        skip = False
        for sID in ids:
            # Skip empty lines and previously injected
            if not sID: continue
            ID = int(sID)
            if ID in self.previouslyInjected: 
                skip = True
                continue

            i += 1
            #print "ID of AO: %d" % ID

            customDll = self.GetDllPath("Custom.dll")
            if customDll == None:
                print "[Listen.] Could not find custom.dll"
                return

            ret = c_dll.InjectDLL( ctypes.c_int( ID ), 	ctypes.c_char_p(customDll)	)
            if ret: print "[Listen.] Injection successful: %d" % ID 
            else: print "[Listen.] Injection failed: %d" % ID
            self.previouslyInjected.append(ID)

        #if not i and not skip:
        #    print "[Listen.] Could not detect AO"
        #elif skip: print "[Listen.] No new ao clients detected"


    def GetDllPath(self, dllname):
        dir = os.path.realpath(os.path.dirname(sys.argv[0]))
        # Current directory
        if os.access( os.path.join(dir, dllname), os.F_OK):
            return os.path.join(dir, dllname)
        
        # dist\ directory, for testing purposes
        if os.access( os.path.join(dir, "dist", dllname), os.F_OK):
            return os.path.join(dir, "dist", dllname)
        
        return None


    # Toons already known.    
    def AddActives(self, ToonDict):
        for Key in ToonDict:
            if ToonDict[Key]["Toon"]:
                if Key not in self.previouslyListened:
                    self.previouslyListened.append(Key)


if __name__ == '__main__':
    x = Listener()
    x.InjectDll()
    x.Start()
    sys.exit(0)

