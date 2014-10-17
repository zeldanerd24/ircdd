.. How to contribute to the project

Contributing To IRCDD
*********************

How to contribute to the project.

Fork & Clone
============

1. Contact Kiril Zvezdarov (`email <mailto:kzvezdarov@gmail.com>`_) to become a contributor to the project
#. Fork the main repository (found `here <github.com/kzvezdarov/ircdd>`_)
#. Clone your fork:

.. code-block:: shell-session

	git clone git@github.com:yourname/ircdd

4. CD to the created directory. Set up a remote to the main repo:

.. code-block:: shell-session

	git remote add project-origin https://github.com/kzvezdarov/ircdd

Working & Contributing
======================

1. Pick an unsassigned issue on Git, and assign it to yourself.
2. In your local repository, pull the latest changes:

.. code-block:: shell-session

	git pull project-origins master

3. Checkout a new branch for the issue:

.. code-block:: shell-session

	git checkout -b my-issue

4. Do some work. Test, add, commit changes. When ready to submit, push the branch to your fork:

.. code-block:: shell-session
	
	git push origin my-issue

5. Go to GitHub and create a pull request.

Updating a Pull Request
=======================

If you have created a pull request, but need to add more commits to it, simply push the changes to your remote branch.

Updating Work Branch From Master
================================

1. Checkout your master branch and pull the latest changes from the main repo:

.. code-block:: shell-session

	git checkout master
	git pull project-origin master

2. Checkout your working branch and rebase on top of master to update

.. code-block:: shell-session

	git checkout my-issue
	git rebase master
