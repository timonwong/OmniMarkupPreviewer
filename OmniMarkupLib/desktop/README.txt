Introduction
------------

The desktop package provides desktop environment detection and resource
opening support for a selection of common and standardised desktop
environments.

Currently, in Python's standard library, there is apparently no coherent,
cross-platform way of getting the user's environment to "open" files or
resources (showing such files in browsers or editors, for example) when
requested by a Python program. There is an os.startfile function which works
for Windows, but no equivalent function for other desktop environments - the
webbrowser module seems to employ alternative mechanisms in choosing and
running external programs and presumably does not seek to provide general
support for non-URL resources anyway.  

Since desktop environments like KDE and GNOME provide mechanisms for running
browsers and editors according to the identified type of a file or resource,
just as Windows "runs" files or resources, it is appropriate to have a module
which accesses these mechanisms. It is this kind of functionality that the
desktop package aims to support. Note that this approach is arguably better
than that employed by the webbrowser module since most desktop environments
already provide mechanisms for configuring and choosing the user's preferred
programs for various activities, whereas the webbrowser module makes
relatively uninformed guesses (for example, opening Firefox on a KDE desktop
configured to use Konqueror as the default browser).

Some ideas for desktop detection (XFCE) and URL opening (XFCE, X11) were
obtained from the xdg-utils project which seeks to implement programs
performing similar functions to those found in the desktop module. The
xdg-utils project can be found here:

http://portland.freedesktop.org/

Other information regarding desktop icons and menus, screensavers and MIME
configuration can also be found in xdg-utils.

Contact, Copyright and Licence Information
------------------------------------------

No Web page has yet been made available for this work, but the author can be
contacted at the following e-mail address:

paul@boddie.org.uk

Copyright and licence information can be found in the docs directory - see
docs/COPYING.txt, docs/lgpl-3.0.txt and docs/gpl-3.0.txt for more information.

Notes
-----

Notes on desktop application/environment support:

KDE           Supports file and URL opening using kfmclient, where the openURL
              command opens the resource and the exec command runs the
              resource.

KDE 4         Similar to KDE but uses kioclient instead of kfmclient.

GNOME         Supports file and URL opening using gnome-open.

XFCE          Supports file and URL opening using exo-open.

ROX-Filer     Supports file opening using "rox <filename>" but not URL
              opening.

New in desktop 0.4.1 (Changes since desktop 0.4)
------------------------------------------------

  * Added KDE 4 and Lubuntu support contributed by Jérôme Laheurte.

New in desktop 0.4 (Changes since desktop 0.3)
----------------------------------------------

  * Improved docstrings.
  * Fixed support for examining the root window.
  * Changed the licence to the LGPL version 3 (or later).

New in desktop 0.3 (Changes since desktop 0.2.4)
------------------------------------------------

  * Made desktop a package.
  * Added support for graphical dialogue boxes through programs such as
    kdialog, zenity and Xdialog.
  * Added support for inspecting desktop windows (currently only for X11).

New in desktop 0.2.4 (Changes since desktop 0.2.3)
--------------------------------------------------

  * Added XFCE support (with advice from Miki Tebeka).
  * Added Ubuntu Feisty (7.04) package support.

New in desktop 0.2.3 (Changes since desktop 0.2.2)
--------------------------------------------------

  * Added Python 2.3 support (using popen2 instead of subprocess).

New in desktop 0.2.2 (Changes since desktop 0.2.1)
--------------------------------------------------

  * Changed the licence to LGPL.

New in desktop 0.2.1 (Changes since desktop 0.2)
------------------------------------------------

  * Added Debian/Ubuntu package support.

New in desktop 0.2 (Changes since desktop 0.1)
----------------------------------------------

  * Added support for waiting for launcher processes.
  * Added a tests directory.

Release Procedures
------------------

Update the desktop __version__ attribute.
Change the version number and package filename/directory in the documentation.
Update the release notes (see above).
Update the package information.
Check the release information in the PKG-INFO file.
Check the setup.py file.
Tag, export.
Archive, upload.
Update PyPI entry.

Making Packages
---------------

To make Debian-based packages:

  1. Create new package directories under packages if necessary.
  2. Make a symbolic link in the distribution's root directory to keep the
     Debian tools happy:

     ln -s packages/ubuntu-hoary/python2.4-desktop/debian/
     ln -s packages/ubuntu-feisty/python-desktop/debian/
     ln -s packages/ubuntu-hardy/python-desktop/debian/

  3. Run the package builder:

     dpkg-buildpackage -rfakeroot

  4. Locate and tidy up the packages in the parent directory of the
     distribution's root directory.
