.. Installation Guide
   Basic installation, network considerations, uninstalls. Installation
   should be automated and seamless. The system must be
   responsible for determining if minimum requirements are satisfied.
   For a client/server system this includes installation of both the client
   and server software. For a mobile application, it includes build and
   deployment instructions.

Installation Guide
******************

Installation
============

NOTE: Requires an internet connection
-------------------------------------

Pre-installation
----------------

1. Download and install Virtualbox `here <https://www.virtualbox.org/wiki/Downloads>`_
2. Download and install Vagrant `here <https://www.vagrantup.com/downloads.html>`_
3. Download and install Git:

- Command-line Client: `Git <http://git-scm.com/downloads>`_
- Windows GUI Client: `Git for Windows <https://windows.github.com/>`_
- Mac GUI Client: `Git for Mac <https://mac.github.com/>`_

4. Download and install RSync `here <http://rsync.samba.org/>`_

Clone The Repository
--------------------

**Method 1 - Command-line:**

.. code-block:: shell-session

	git clone git@github.com:yourname/ircdd

**Method 2 - GUI Client:**

1. Visit https://github.com/kzvezdarov/ircdd
2. Click the "Clone in Desktop" link on the right side of the page. The link will open the GUI client
3. Click "Clone" to clone the repository

Starting The System
-------------------

1. Open up a command-line client (Terminal, cmd.exe, etc.)
2. Navigate to the cloned repository location using the 'cd' command
3. Execute the following command:

.. code-block:: shell-session

	./scripts/launch-dev-core.sh

Connecting to the System
========================

**Instructions pending implementation of connection config options**


Uninstallation
==============

Simply delete the directory from your system and uninstall any of the additional proprietary software that is no longer needed from the `Required Downloads <quickstart.html#required-downloads>`_ section.
