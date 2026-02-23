from database import get_db

def delete_rows():
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM downloads where id in (225,226,231,232)")
    con.commit()
    con.close()

if __name__ == "__main__":
    delete_rows()