OmniMarkupPreviewer
===================

OmniMarkupPreviewer is a [Sublime Text 2](http://www.sublimetext.com/2) plugin
that preview markup languages in web browsers. OmniMarkupPreviewer renders markup
files to htmls and send them to web brwosers in the backgound, in order to preview
them in realtime.

OmniMarkupPreviewer has builtin support following markups:

* [Markdown](http://daringfireball.net/projects/markdown/)
* [reStructuredText](http://docutils.sourceforge.net/rst.html)
* [WikiCreole](http://wikicreole.org/)
* [Textile](http://www.textism.com/tools/textile/)
* [Pod](http://search.cpan.org/dist/perl/pod/perlpod.pod)
(Requires Perl >= 5.10 and can be found in `PATH`, if the perl version < 5.10, 
Pod::Simple should be installed from CPAN.)
* [RDoc](http://rdoc.sourceforge.net/) (Requires ruby in your `PATH`)


Installation
------------

### With the Package Control plugin
The easiest way to install OmniMarkupPreviewer is through [Package Control](http://wbond.net/sublime_packages/package_control).

Once you have Package Control installed, restart Sublime Text 2.

1. Bring up the Command Palette (<kbd>Ctrl+Shift+P</kbd> on Windows and Linux. 
<kbd>Command+Shift+P</kbd> on OS X).
2. Type "Install" and select "Package Control: Install Package".
3. Select "OmniMarkupPreviewer" from list.

The advantage of using Package Control is that it will keep OmniMarkupPreviewer up to date automatically.


### Manual Install
**Without Git:**
[Download](https://github.com/timonwong/OmniMarkupPreviewer) the latest source code, and extract to the Packages directory.

**With Git:**
Type the following command in your Sublime Text 2 Packages directory:

`git clone git://github.com/timonwong/OmniMarkupPreviewer.git`

The "Packages" directory is located at:

* **Windows:**  `%APPDATA%\Sublime Text 2\Packages\`
* **Linux:**    `~/.config/sublime-text-2/Packages/`
* **OS X:**     `~/Library/Application Support/Sublime Text 2/Packages/`


Usage
-----

### Key Bindings

The default key bindings for this plugin:

**Windows, Linux:**

* <kbd>Ctrl+Alt+O</kbd>: Preview current file.

**OSX:**

* <kbd>Super+Alt+O</kbd>: Preview current file.


### Command Palette

Open the command palette, it apperas as `OmniMarkupPreviewer: Preview Current File`.


What's New
----------

v1.2 (10/16/2012)

* OmniMarkupPreviewer now can be installed from Package Control under Linux.

v1.1 (10/16/2012)

* Added support for [RDoc](http://rdoc.sourceforge.net/) (Requires ruby).
* Added support for [Pod](http://search.cpan.org/dist/perl/pod/perlpod.pod) (Requires perl).
* Auto scroll while text added/deleted.

v1.0.1 (10/14/2012)

* OSX support added to Package Control.
* Added ability to clean cache.

v1.0 (10/14/2012)

* First release.


License
-------

This plugin is using MIT License

    Copyright (c) 2012 Timon Wong

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is furnished to do
    so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
