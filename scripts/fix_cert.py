
mp = pathlib.Path('roster/ui/messages.py')
raw = mp.read_bytes()
# Find and replace certificate_signer second line
idx1 = raw.find(b'certificate_signer')
if idx1 > 0:
    # Find the two occurrences of the zh/en value
    target = b'\xe9\xa6\x96\xe5\xb8\xad\xe5\xb0\x8e\xe5\xad\xb8\xe9\xa2\xa8\xe7\xb4\x80 26-27 LI Chuangjie Jacky'
    first = raw.find(target, idx1)
    if first > 0:
        second = raw.find(target, first + 1)
        if second > 0:
            replacement = b'Head Study Prefect (\xe9\xa6\x96\xe5\xb8\xad\xe5\xb0\x8e\xe5\xad\xb8\xe9\xa2\xa8\xe7\xb4\x80) 26-27 LI Chuangjie Jacky'
            raw = raw[:second] + replacement + raw[second + len(target):]
            mp.write_bytes(raw)
            print('messages.py: fixed')
        else:
            print('Second occurrence not found')
pp = pathlib.Path('roster/utils/pdf.py')
praw = pp.read_bytes()
old = b'<strong>\xe9\xa6\x96\xe5\xb8\xad\xe5\xb0\x8e\xe5\xad\xb8\xe9\xa2\xa8\xe7\xb4\x80</strong><br>Sing Yin Secondary School</p>'
new = b'<strong>Head Study Prefect (\xe9\xa6\x96\xe5\xb8\xad\xe5\xb0\x8e\xe5\xad\xb8\xe9\xa2\xa8\xe7\xb4\x80)</strong><br>Sing Yin Secondary School</p>'
if old in praw:
    praw = praw.replace(old, new, 1)
    pp.write_bytes(praw)
    print('pdf.py: fixed')
else:
    print('pdf.py: pattern not found')
