.. Security

Security
********

Security is largely handled by the host operating system because the application runs in a virtual environment.

Inherent Security Features
==========================

The system does have some security features built into its design.

Compartmentalized System
------------------------

Every application the system requires is run in an isolated container. This means that if something were to obtain root access on the IRC server itself, for example, it would not have access to the Database.

Encrypted Database Components
-----------------------------

Documents and tables in the database are encrypted. More specifically, each password is encrypted, and other sensitive information is as well.