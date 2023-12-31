# -*- Makefile -*-
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

SUBDIRS = po data

bin_SCRIPTS = xgsch2pcb

python_PYTHON = lib/xgsch2pcb/pcbmanager.py \
 lib/xgsch2pcb/gsch2pcbproject.py \
 lib/xgsch2pcb/gui.py \
 lib/xgsch2pcb/new_project_gui.py \
 lib/xgsch2pcb/templates.py \
 lib/xgsch2pcb/funcs.py

nodist_python_PYTHON = config.py

INTLTOOL_FILES = intltool-extract.in \
                 intltool-merge.in \
                 intltool-update.in

EXTRA_DIST = xgsch2pcb.in lib/xgsch2pcb/config.py.in \
             $(INTLTOOL_FILES) icon-theme-installer
CLEANFILES = xgsch2pcb config.py
DISTCLEANFILES = intltool-extract \
                 intltool-merge \
                 intltool-update \
                 po/.intltool-merge-cache
MAINTAINERCLEANFILES = Makefile.in configure config.h.in \
                       config.status aclocal.m4 libgeda.pc config.guess \
                       config.sub depcomp install-sh missing mkinstalldirs \
                       $(INTLTOOL_FILES)

templatesdir = @templatesdir@
pkglibdir = @XDGDATADIR@/xgsch2pcb
pythondir = $(pkglibdir)

do_subst = sed -e 's,[@]prefix[@],$(prefix),g' \
               -e 's,[@]PYTHON[@],$(PYTHON),g' \
				       -e 's,[@]VERSION[@],$(VERSION),g' \
							 -e 's,[@]pkglibdir[@],$(pkglibdir),g' \
							 -e 's,[@]templatesdir[@],$(templatesdir),g' \
							 -e 's,[@]PACKAGE[@],$(PACKAGE),g'

all: $(python_PYTHON) $(nodist_python_PYTHON)

config.py: lib/xgsch2pcb/config.py.in Makefile
	$(do_subst) < $(srcdir)/lib/xgsch2pcb/config.py.in > $@

xgsch2pcb: xgsch2pcb.in Makefile
	$(do_subst) < $(srcdir)/xgsch2pcb.in > $@
	chmod +x xgsch2pcb

DISTCHECK_CONFIGURE_FLAGS = --disable-update-desktop-database
