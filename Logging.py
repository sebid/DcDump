
import sqlite3
class History():
    def __init__(self):
        import sqlite3
        self.CONN = sqlite3.connect("SQDB", isolation_level=None)
        self.SQL = self.CONN.cursor()
        
        #self.SQL.execute("Drop table history")
        self.SQL.execute("CREATE TABLE if not exists history (id INTEGER PRIMARY KEY, start INTEGER, end INTEGER, toon TEXT, customname TEXT, DataChunk TEXT, StatsChunk TEXT)")
    
        
    # Add new parse to logfile
    def log(self, start, end, toon, data, stats):
        # Check if an entry already exists for this period and toon
        self.SQL.execute("Select * from history where start=? and end=? and toon=? LIMIT 1", (start, end, toon))
        for result in self.SQL:
            return False
        
        self.SQL.execute("insert into history(start, end, toon, DataChunk, StatsChunk) values (?, ?, ?, ?, ?)", (start, end, toon, data, stats))
        return True
    
    # Gets all entries (excluding data)
    def getAll(self):
        output = []
        self.SQL.execute("select start, end, toon, customname from history order by start")
        output = [L for L in self.SQL]
        return output


    # Gets a specific entry
    def getSingle(self, start, end, toon):
        output = []
        self.SQL.execute("select customname, DataChunk, StatsChunk from history where start=? and end=? and toon=?", (start, end, toon))
        for custom, data, stats in self.SQL:
            try:
                data = eval(data) # from retarded test data
                stats = eval(stats)
            except NameError: pass
            output = {
                  "start": start,
                  "end": end,
                  "toon": toon,
                  "customname": custom,
                  "data": data,
                  "stats": stats}
        return output
    
    # Gets a specific entry
    def getSingleC(self, customname):
        output = []
        self.SQL.execute("select start, end, toon, DataChunk, StatsChunk from history where customname=?", (customname,))
        for start, end, toon, data, stats in self.SQL:
            data = eval(data)
            stats = eval(stats)
            output = {
                  "start": start,
                  "end": end,
                  "toon": toon,
                  "customname": customname,
                  "data": data,
                  "stats": stats}
        return output
    
    
    def setCustomName(self, start, end, toon, customname):
        # Name exists
        self.SQL.execute("select id from history where customname=?", (customname,))
        for L in self.SQL:
            return False
        
        try:
            self.SQL.execute("update history set customname=? where start=? and end=? and toon=?", (customname, start, end, toon))
            return True

        # Name already exists
        except sqlite3.IntegrityError:
            return False
        
    def deleteEntry(self, start, end, toon):
        self.SQL.execute("delete from history where start=? and end=? and toon=?", (start, end, toon))
        
    def deleteEntryCN(self, customname):
        self.SQL.execute("delete from history where customname=?", (customname,))
        
        
        
if __name__ == "__main__":
    P = History()
    print P.log(0, 0, "evil", "nodata", "stats")
    print P.log(0, 0, "evil13", "nodata", "stats")
    print P.setCustomName(0, 0, "evil", "1Tezt!")
    print P.getAll()
    P.deleteEntryCN("1Tezt!")
    P.deleteEntry(0, 0, "evil13")
    P.deleteEntry(0, 0, "evil13")
    print P.getAll()
    #print P.getSingle(0, 0, "evil")
    #print P.getSingleC("Tezt!")
    
    #print P.getSingleC("ME")
#SQLite:
#Table: History
#Start, End, Toon, CustomName, DATACHUNK, DATACHUNK_STAT