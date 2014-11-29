import rethinkdb as r

DB = "test_ircdd"
HOST = "127.0.0.1"
PORT = 28015

USERS_TABLE = "users"
GROUPS_TABLE = "groups"


def setUp():
    conn = r.connect(db=DB, host=HOST, port=PORT)
    r.db_create(DB).run(conn)
    r.db(DB).table_create("users").run(conn)
    r.db(DB).table_create("groups").run(conn)
    r.db(DB).table_create("user_sessions").run(conn)
    r.db(DB).table_create("group_states").run(conn)
    conn.close()


def tearDown():
    conn = r.connect(db=DB, host=HOST, port=PORT)
    r.db_drop(DB).run(conn)
    conn.close()


def cleanTables():
    conn = r.connect(db=DB,
                     host=HOST,
                     port=PORT)
    r.db(DB).table("users").delete().run(conn)
    r.db(DB).table("groups").delete().run(conn)
    r.db(DB).table("user_sessions").delete().run(conn)
    r.db(DB).table("group_states").delete().run(conn)
    conn.close()
