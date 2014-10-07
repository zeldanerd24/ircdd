.. Sample reST code, so that we know can reference
   this for how to do certain things in reST

Sample reST code
****************

Below is some example reST code so that you can know how to write the documentation
   Note that reST is indent sensitive just like Python.

Bold and Italics
================

Bold and italics are done like this::

   **bold** and *italics*

This renders as **bold** and *italics*

Bullets and Lists
=================

For bullets, you can do::

   * bullet item 1
   * bullet item 2
      * bullet item 3
      * bullet item 4

Which renders as:
   * bullet item 1
   * bullet item 2
      * bullet item 3
      * bullet item 4

For numbered lists, you can do::

   1. Item 1
   2. Item 2
   3. Item 3

Which renders as:

   1. Item 1
   2. Item 2
   3. Item 3

Headers
=======

reST is flexible in that if you underline with either *, =, -, or +, then
it treats what is above it as a header. For example::

   H1 -- Top of Page Header
   ************************
   H2 -- Page Sections
   ===================
   H3 -- Subsection
   ----------------
   H4 -- Subsubsection
   +++++++++++++++++++

This page's headers already use * for Sample reST code at top of page, and
= for each subsection such as this Headers section. The further subsections look like this:

H3 -- Subsection
----------------

H4 -- Subsubsection
+++++++++++++++++++

Tables
======

Here is an example table::

   COMPLEX TABLE:

   +------------+------------+-----------+
   | Header 1   | Header 2   | Header 3  |
   +============+============+===========+
   | body row 1 | column 2   | column 3  |
   +------------+------------+-----------+
   | body row 2 | Cells may span columns.|
   +------------+------------+-----------+
   | body row 3 | Cells may  | - Cells   |
   +------------+ span rows. | - contain |
   | body row 4 |            | - blocks. |
   +------------+------------+-----------+

   SIMPLE TABLE:

   =====  =====  ======
      Inputs     Output
   ------------  ------
     A      B    A or B
   =====  =====  ======
   False  False  False
   True   False  True
   False  True   True
   True   True   True
   =====  =====  ======

This renders as:

COMPLEX TABLE:

+------------+------------+-----------+
| Header 1   | Header 2   | Header 3  |
+============+============+===========+
| body row 1 | column 2   | column 3  |
+------------+------------+-----------+
| body row 2 | Cells may span columns.|
+------------+------------+-----------+
| body row 3 | Cells may  | - Cells   |
+------------+ span rows. | - contain |
| body row 4 |            | - blocks. |
+------------+------------+-----------+

SIMPLE TABLE:

=====  =====  ======
   Inputs     Output
------------  ------
  A      B    A or B
=====  =====  ======
False  False  False
True   False  True
False  True   True
True   True   True
=====  =====  ======

Links
=====

Urls are automatically linked, such as https://github.com/kzvezdarov/ircdd

For other links, you surround something in ` characters, then end it with _
For example::

   `Installation guide <install.html>`_

Which renders as:

`Installation guide <install.html>`_

In page links can be made for headers. For example::

   `Bullets and Lists`_

Renders as a link to `Bullets and Lists`_

Paragraph Markup
================

To bring attention to a section of text, use paragraphs level markups.

Important constructs include::

   .. note::

   .. warning::

   .. versionadded:: version

   .. versionchanged:: version

   .. seealso::

Here is an example warning::

   .. warning::

      Don't ever break master or else Kiril will hunt you down!

Which renders as:

.. warning::

   Don't ever break master or else Kiril will hunt you down!

Python Code
===========





