.. Backup and Recovery

Backup and Recovery
*******************

Backup and Recovery is automatically managed by the IRC system.

Database
========

The database is replicated across every machine listening in on a channel. This redundancy allows it to backup and recover itself if ever there is a failure.

System Recovery
===============

If there is a failure anywhere in the system, Fleet automatically will restart the faulty component.