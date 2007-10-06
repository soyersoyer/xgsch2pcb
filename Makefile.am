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

bin_SCRIPTS = xgsch2pcb

pkglib_PYTHON = lib/xgsch2pcb/pcbmanager.py \
 lib/xgsch2pcb/gsch2pcbproject.py \
 lib/xgsch2pcb/gui.py \
 lib/xgsch2pcb/new_project_gui.py \
 lib/xgsch2pcb/assistant.py \
 lib/xgsch2pcb/templates.py \
 lib/xgsch2pcb/funcs.py

nodist_pkglib_PYTHON = config.py

dist_noinst_SCRIPTS = tools/pygettext.py \
 tools/msgfmt.py
 
EXTRA_DIST = xgsch2pcb.in lib/xgsch2pcb/config.py.in
CLEANFILES = xgsch2pcb config.py

templatesdir = @templatesdir@

do_subst = sed -e 's,[@]prefix[@],$(prefix),g' \
               -e 's,[@]PYTHON[@],$(PYTHON),g' \
				       -e 's,[@]VERSION[@],$(VERSION),g' \
							 -e 's,[@]pkglibdir[@],$(pkglibdir),g' \
							 -e 's,[@]templatesdir[@],$(templatesdir),g' \
							 -e 's,[@]PACKAGE[@],$(PACKAGE),g'

all: $(pkglib_PYTHON) $(nodist_pkglib_PYTHON)

config.py: lib/xgsch2pcb/config.py.in Makefile
	$(do_subst) < $(srcdir)/lib/xgsch2pcb/config.py.in > $@

xgsch2pcb: xgsch2pcb.in Makefile
	$(do_subst) < $(srcdir)/xgsch2pcb.in > $@
	chmod +x xgsch2pcb


