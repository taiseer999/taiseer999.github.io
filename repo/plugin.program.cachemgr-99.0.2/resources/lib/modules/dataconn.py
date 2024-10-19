import xbmcgui
import xbmc, xbmcaddon
import xbmcvfs
import sqlite3 as sqlt
from resources.lib.modules import var

def create_conn(db_file):
    #Create a database connection
    conn = None
    try:
        conn = sqlt.connect(db_file)
    except Error as e:
        print(e)
    return conn

def clear_db(conn, sql):
    #Clear database
    cur = conn.cursor()
    table_list = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'"% str(sql)).fetchall()
    if table_list == []:
        pass
    else:
        cur.execute("DELETE FROM '%s'"% str(sql))
        conn.commit()

def clear_h1_db(conn, sql, tbl):
    #Clear database
    cur = conn.cursor()
    table_list = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'"% str(tbl)).fetchall()
    if table_list == []:
        pass
    else:
        cur.execute("DELETE FROM maincache WHERE id LIKE '%s'"% str(sql))
        conn.commit()

def clear_h2_db(conn, sql, tbl):
    #Clear database
    cur = conn.cursor()
    table_list = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'"% str(tbl)).fetchall()
    if table_list == []:
        pass
    else:
        cur.execute("DELETE FROM sqlite_sequence WHERE name LIKE '%s'"% str(sql))
        conn.commit()

def clear_h3_db(conn, sql):
    #Clear database
    cur = conn.cursor()
    table_list = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'"% str(sql)).fetchall()
    if table_list == []:
        pass
    else:
        cur.execute("DELETE FROM simple_cache WHERE name LIKE '%s'"% str(sql))
        conn.commit()

def clear_h4_db(conn, sql, tbl):
    #Clear database
    cur = conn.cursor()
    table_list = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'"% str(tbl)).fetchall()
    if table_list == []:
        pass
    else:
        cur.execute("DELETE FROM search_string2 WHERE tv_movie LIKE '%s'"% str(sql))
        conn.commit()
        
def optimize_db(conn, sql):
    #Optimize Database
    cur = conn.cursor()
    conn.execute('VACUUM')