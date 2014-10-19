.. Database

Database
********

Implemented System
==================

The database software used in IRCDD is RethinkDB. For more information on RethinkDB, visit this `link <http://rethinkdb.com/>`_.

Database Tables
===============

The database has # tables to store information related to the IRC server. Those tables are as follows:

**Example table unitl the tables are finalized**

+------------------+---------+-------------+-----------+
|    ChannelID     |  Name   |    Owner    |   Type    |
+==================+=========+=============+===========+
| Contains Channel | Channel | Owner of    | Public or |
| ID               | Name    | the channel | private   |
+------------------+---------+-------------+-----------+