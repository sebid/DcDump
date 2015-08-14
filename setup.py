"""
Dependencies: 
py2exe, www.py2exe.org
_mysql, www.codegood.com/downloads
wxPython, www.wxpython.org
DLL, msvcp90.dll
win32gui, http://sourceforge.net/projects/pywin32/files/pywin32/Build216/

Optional: wxGlade, wxglade.sourceforge.net
"""
from DebugSettings import Build_ID, Build_Version
from distutils.core import setup
import py2exe, sys, win32gui
inc = ["_mysql","MySQLdb","_mysql_exceptions", "wx"]

Debug = False
data = "Debug = True\n" # Being phased out
if len(sys.argv) > 1 and sys.argv[1] == 'debug':
    Debug = True
else:
    Build_ID += 1
    
    
# Write the new settings file
h = open("DebugSettings.py", "w")
data += "Build_ID = %d\n" % Build_ID
data += 'Build_Version = "%s"\n' % Build_Version
h.write(data)
h.close()

# Clean up arguments
sys.argv = [sys.argv[0], "py2exe"]

if Debug:
    setup(
          console=[ {"script":'UI.py', "icon_resources": [(1, "Client0.ico"), (0, "Client0.ico")] }],
          options = {'py2exe': {'bundle_files': 1,  "includes":inc,  'dll_excludes': [ "mswsock.dll", "powrprof.dll", "MSVCP90.dll" ]}},
          zipfile = "data1.dat",
          data_files=[(".", ["find.exe"])]
          )
else:
    setup(
          windows=[ {"script":'UI.py', "icon_resources": [(1, "Client0.ico"), (0, "Client0.ico")]} ], 
          options = {'py2exe': {'bundle_files': 1,  "includes":inc, 'dll_excludes': [ "mswsock.dll", "powrprof.dll", "MSVCP90.dll" ]}},
          zipfile = "data1.dat",
          data_files=[(".", ["find.exe"])]
          )
    
# Compress to rar file
import os
if Debug: 
	outname = 'dcdump_v%s.%dd' % (Build_Version, Build_ID)
	rarcmd = "rar.exe a -m5 %s.rar data1.dat find.exe UI.exe w9xpopen.exe Listener.dll Custom.dll Guide.txt itemdb" % outname
else: 
	outname = 'dcdump_v%s.%d' % (Build_Version, Build_ID)
	rarcmd = "winrar.exe a -m5 -afzip %s.zip data1.dat find.exe UI.exe w9xpopen.exe Listener.dll Custom.dll Guide.txt itemdb" % outname
print "Compressing.."
os.chdir("dist")
pipe = os.popen(rarcmd)
for L in pipe.readlines(): print L,
pipe.close()

