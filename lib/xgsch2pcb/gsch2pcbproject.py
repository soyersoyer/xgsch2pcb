# -*-Python-*-

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

import os, gobject

class Gsch2PCBProject(gobject.GObject):

    __gsignals__ = { 'dirty-flag-changed' :
                            ( gobject.SIGNAL_NO_RECURSE,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_BOOLEAN, )),
                     'page-added' :
                            ( gobject.SIGNAL_NO_RECURSE,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_STRING, )),
                     'page-removed' :
                            ( gobject.SIGNAL_NO_RECURSE,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_STRING, )),
                   }
                   
    def __init__(self, filename=None, output_name=None):
        gobject.GObject.__init__(self)

        self.filename = filename
        self.dirty = False
        self.pages = []

        if output_name != None:
            self.output_name = output_name
        elif filename != None:
            # Try something clever...
            self.output_name = filename.rsplit('.', 1)[0]
            if self.output_name == "":
                self.output_name = filename
        else:
            self.output_name = None

        if os.path.exists(self.filename):
            self.load()

    def set_dirty(self, flag=True):
        if (self.dirty != flag):
            self.dirty = flag
            self.emit('dirty-flag-changed', flag)

    def load(self, fromfile=None):
        if fromfile == None:
            fromfile = self.filename
        if fromfile == None:
            raise Exception, 'No filename specified to load'

        fp = open(fromfile, 'rb')
        for line in fp:
            parts = line.strip().split(None, 1)
            opt = parts[0]
            if opt == 'schematics':
                if len(parts) > 1:
                    self.pages = parts[1].split()
                else:
                    self.pages = []
            elif opt == 'output-name':
                self.output_name = parts[1]
            else:
                raise Exception, 'Unsupported project file option: %s' % line
        fp.close()
        if fromfile == self.filename:
            self.set_dirty(False)

    def save(self, destfile=None):
        if destfile == None:
            destfile = self.filename
        if destfile == None:
            raise Exception, 'No filename specified for project'

        fp = open(destfile, 'wb')
        fp.write('schematics %s\n' % ' '.join(self.pages))
        fp.write('output-name %s\n' % self.output_name)
        fp.close()
        if destfile == self.filename:
            self.set_dirty(False)

    def add_page(self, filename):
        if not filename in self.pages:
            self.pages.append(filename)
            self.emit('page-added', filename)
            self.set_dirty()

    def remove_page(self, filename):
        if filename in self.pages:
            self.pages.remove(filename)
            self.emit('page-removed', filename)
            self.set_dirty()

gobject.type_register( Gsch2PCBProject )

