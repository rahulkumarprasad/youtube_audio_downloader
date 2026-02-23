import sqlite3
con = sqlite3.connect('downloads.db')
cur = con.cursor()
cur.execute('SELECT title, filename, folder FROM downloads ORDER BY id DESC LIMIT 10')
rows = cur.fetchall()
for r in rows:
    print(f'Title: {r[0]}')
    print(f'Filename: {r[1]}')
    print(f'Folder: {r[2]}')
    print('---')
con.close()
