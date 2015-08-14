import re, string, os


def trimfile(filename):
	if not os.access(filename, os.W_OK):
		print "No write access to file."
		return False
		
	expr = r"""(?P<TS>\d+)]"""
	try:
		data = open(filename).read().split('\n')
	except: return False

	'Find the newest timestamp'
	i = 0
	match = None
	while match == None and i > -len(data):
		i -= 1
		match = re.search(expr, data[i], re.I)
		
	'No timestamp could be found'
	if not match: 
		return False
	else:
		ts = int(match.group('TS'))
	
	'Loop trough the file until we encounter a 10min+ gap'
	sl = None
	i = 0
	for L in reversed(data):
		match = re.search(expr, L, re.I)
		i -= 1
		if not match: continue
		if int(match.group('TS')) + 10*60 < ts:
			sl = i
			break
		ts = int(match.group('TS'))
	
	# Trim!
	if sl == None:
		return False
	
	data = data[sl:]
	f = open(filename, "w")
	f.write(string.join(data))
	return True
	#print sl, data
		
		
if __name__ == '__main__':
	getLatestTimestamp("log.txt")
	print "Filesize:",os.path.getsize("log.txt") / 1024 / 1024.,"mb"
