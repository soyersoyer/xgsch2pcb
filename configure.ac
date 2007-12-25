#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.
#
# xgsch2pcb - a GUI for gsch2pcb
# Copyright (C) 2006 University of Cambridge
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#



AC_PREREQ(2.59)
AC_INIT([geda-xgsch2pcb], [0.1.1.90], BUG-REPORT-ADDRESS)

AM_INIT_AUTOMAKE([foreign])


PYTHON_WANTVERSION=2.4
PYTHON_WANTMODULES="commands gettext os os.path re shutil stat subprocess dbus dbus.glib dbus.service"
GTK_WANTVERSION=2.8


# Checks for programs.
AC_PROG_INSTALL
AM_PATH_PYTHON($PYTHON_WANTVERSION)
IT_PROG_INTLTOOL(0.35.0)

AC_DEFUN([AC_PYTHON_MODULE],[
    AC_MSG_CHECKING([for python module $1])
    $PYTHON -c "import $1" > /dev/null 2>&1
    if test $? -eq 0; then
        AC_MSG_RESULT(yes)
    else
        AC_MSG_RESULT(no)
        if test -n "$2"; then
            AC_MSG_ERROR([python module $1 is required])
        fi
    fi
])


############################################################################
# Update desktop database utility start
#

AC_ARG_ENABLE(update-desktop-database,
   AC_HELP_STRING([--disable-update-dektop-database],
                   [do not update desktop file database after installation]),,
                   enable_update_desktop_database=yes)

AM_CONDITIONAL(ENABLE_UPDATE_DESKTOP_DATABASE,
               test x$enable_update_desktop_database = xyes)

if test x$enable_update_desktop_database = xyes ; then
  AC_PATH_PROG(UPDATE_DESKTOP_DATABASE, [update-desktop-database], no)
  if test $UPDATE_DESKTOP_DATABASE = no; then
     AC_MSG_ERROR([Cannot find update-desktop-database, make sure it is installed and in your PATH, or configure with --disable-update-desktop-database])
  fi
fi

#
# Update desktop database utility end
############################################################################

# Set USE_NLS
AM_NLS

# Find GMSGFMT
AC_PATH_PROG(GMSGFMT, msgfmt)

# Set package name for translations
GETTEXT_PACKAGE=$PACKAGE
AC_SUBST(GETTEXT_PACKAGE)

##########################################################################
# Command line flags start
#

# Change default location for rc files
AC_ARG_WITH(templatesdir, [  --with-templatesdir=path       Change where the template projects are found], [templatesdir=$withval],[templatesdir=$datarootdir/$PACKAGE/templates])

AC_SUBST(templatesdir)

#
# Command line flags end
##########################################################################

##########################################################################
# Look for PyGTK
#

AC_PYTHON_MODULE(pygtk, t)

AC_MSG_CHECKING(for pygtk 2.0)
cat > conftest.py <<[EOF
import pygtk
pygtk.require("2.0")
EOF]

if $PYTHON conftest.py > /dev/null 2>&1; then
    AC_MSG_RESULT(yes)
else
    AC_MSG_RESULT(no)
    AC_MSG_ERROR([pygtk 2.0 is required])
fi

for module in gobject gtk gtk.gdk; do
    AC_PYTHON_MODULE($module, t)
done

AC_MSG_CHECKING(for gtk+ >= $GTK_WANTVERSION)
cat > conftest.py <<[EOF
import sys
try:
    import gtk
    ver = gtk.gtk_version
    sys.stdout.write(".".join(map(str, ver)))
    if len(sys.argv) > 1:
        wantver = sys.argv[1].split(".")
        wantver = map(int, wantver)
        for i in range(len(wantver)):
            if i > len(ver):
                break
            if wantver[i] > ver[i]:
                sys.exit(1)
except:
    sys.exit(1)
sys.exit(0)
EOF]

GTK_VERSION=`$PYTHON conftest.py $GTK_WANTVERSION 2> /dev/null`
haveversion=$?
AC_MSG_RESULT($GTK_VERSION)
if test $haveversion -ne 0; then
  AC_MSG_ERROR([GTK+ >= $GTK_WANTVERSION is required])
fi

#
#
##########################################################################


##########################################################################
# Look for other Python modules
#

for module in $PYTHON_WANTMODULES; do
    AC_PYTHON_MODULE($module, t)
done

#
#
##########################################################################

# Checks for system services
AC_SYS_INTERPRETER
if test $interpval == 'no'; then
  AC_MSG_ERROR([Your system must support the shell bang syntax]);
fi

AC_CONFIG_FILES([Makefile
                 data/Makefile
                 po/Makefile.in
                 po/Makefile])
AC_OUTPUT

