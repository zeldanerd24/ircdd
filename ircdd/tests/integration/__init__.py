import rethinkdb as r

DB = "test_ircdd"
HOST = "127.0.0.1"
PORT = 28015

USERS_TABLE = "users"
GROUPS_TABLE = "groups"


def setUp():
    conn = r.connect(db=DB, host=HOST, port=PORT)
    r.db_create(DB).run(conn)
    conn.close()


def tearDown():
    conn = r.connect(db=DB, host=HOST, port=PORT)
    r.db_drop(DB).run(conn)
    conn.close()
