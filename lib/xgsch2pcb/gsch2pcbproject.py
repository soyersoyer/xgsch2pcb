# -*-Python-*-

# xgsch2pcb - a GUI for gsch2pcb
# Copyright (C) 2006 University of Cambridge
# Copyright (C) 2006-2009 xgsch2pcb contributors (See ChangeLog for details)
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

class Gsch2PCBOption(object):
    """Gsch2PCBOption - class representing project's option

This class represents single option which can be added to the gsch2pcb's
project file. Each option created must have at least two attributes:
`name` - name of the option that is used in project file,
`attr_name` - name of the corresponding attribute of Gsch2PCBProject instance
which holds option's value. Additional three parameters `read_func`, `write_func` and
`default_value` which are function to read option's value from config,
function to write option's value to the config and default option's value correspondingly.
"""
    def __init__(self, **kwargs):
        def default_read_function(option, project, parts):
            value = getattr(project, option.attr_name)
            if value == option.default_value and len(parts) > 1:
                setattr(project, option.attr_name, parts[1])

        def default_write_function(option, project, save_file):
            value = getattr(project, option.attr_name)
            if value:
                save_file.write(option.name + ' %s\n' % value)

        self.name=kwargs['name']
        self.attr_name=kwargs['attr_name']
        self.read_func=kwargs.get('read_func', default_read_function)
        self.write_func=kwargs.get('write_func', default_write_function)
        self.default_value=kwargs.get('default_value', None)
        self.emitted = False

    # Each write function must have following signature:
    # write_function(option, project, save_file)
    # where `option` is instance of the option that is being written by that function,
    # `project` is instance of a project which this option is used in, and
    # `save_file` is the file the aforementioned project is saved to.

    @staticmethod
    def join_then_write(option, project, save_file):
        values = getattr(project, option.attr_name)
        if values:
            save_file.write(option.name + ' %s\n' % ' '.join(values))
    @staticmethod
    def write_if_equal(value):
        def func(option, project, save_file):
            if getattr(project, option.attr_name) == value:
                save_file.write(option.name + '\n')
        return func

    # Every read function must have the following signatue:
    # read_function(option, project, parts)
    # where `option` is instance of the option that is being read by that function,
    # `project` is instance of a project which this option is used in, and
    # `parts` is the array that have option's name as its first value and
    # for some commands string corresponding to option as second(see Gsch2PCBProject's load function).

    @staticmethod
    def read_multiple_values(option, project, parts):
        if len(parts) > 1:
            value = parts[1].split()
        else:
            value = []
        setattr(project, option.attr_name, value)
    @staticmethod
    def read_and_set_value(value):
        def func(option, project, parts):
            setattr(project, option.attr_name, value)
        return func


class Gsch2PCBOptionStore(dict):
    """Gsch2PCBOptionStore - slightly augmented dictionary class

This is augmented dictionary class. The only difference
between it and standrad `dict` class is in added `add` function
which is used to create and add options to associative array that
this class represents.
"""
    def add(self, **kwargs):
        option = Gsch2PCBOption(**kwargs)
        self[option.name] = option

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

    PREFER_M4_FOOTPRINTS     = 0
    PREFER_FILE_FOOTPRINTS   = 1
    USE_ONLY_FILE_FOOTPRINTS = 2

    options = Gsch2PCBOptionStore()
    options.add(name='schematics', attr_name= 'pages',
                read_func=Gsch2PCBOption.read_multiple_values,
                write_func=Gsch2PCBOption.join_then_write,
                default_value=[])

    options.add(name='output-name', attr_name='output_name')

    options.add(name='preserve', attr_name='preserve_unfound',
                read_func=Gsch2PCBOption.read_and_set_value(True),
                write_func=Gsch2PCBOption.write_if_equal(True),
                default_value=False)

    options.add(name='skip-m4', attr_name='footprint_type_choice',
                read_func=Gsch2PCBOption.read_and_set_value(USE_ONLY_FILE_FOOTPRINTS),
                write_func=Gsch2PCBOption.write_if_equal(USE_ONLY_FILE_FOOTPRINTS),
                default_value=PREFER_M4_FOOTPRINTS)

    options.add(name='use-files', attr_name='footprint_type_choice',
                read_func=Gsch2PCBOption.read_and_set_value(PREFER_FILE_FOOTPRINTS),
                write_func=Gsch2PCBOption.write_if_equal(PREFER_FILE_FOOTPRINTS),
                default_value=PREFER_M4_FOOTPRINTS)

    options.add(name='elements-dir', attr_name='elements_dir',
                read_func=Gsch2PCBOption.read_multiple_values,
                write_func=Gsch2PCBOption.join_then_write,
                default_value=[])

    options.add(name='m4-command', attr_name='m4_command')
    options.add(name='m4-file', attr_name='m4_file')
    options.add(name='m4-pcbdir', attr_name='m4_pcbdir')
    options.add(name='gnetlist-arg', attr_name='gnetlist_arg')

    def __init__(self, filename=None, output_name=None):
        gobject.GObject.__init__(self)

        for _, option in self.options.items():
            setattr(self, option.attr_name, option.default_value)

        self.filename = filename
        self.dirty = False
        self.lines = []

        if output_name != None:
            self.output_name = output_name
        elif filename != None:
            # Try something clever...
            self.output_name = filename.rsplit('.', 1)[0]
            if self.output_name == "":
                self.output_name = filename
        else:
            self.output_name = None

        if self.filename and os.path.exists(self.filename):
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
            self.lines.append(line)
            parts = line.strip().split(None, 1)

            option_name = None
            if parts:
                option_name = parts[0]

            # Skip blank lines and comment lines (like gsch2pcb)
            if not option_name or option_name in ('#', '/', ';'):
                pass
            else:
                try:
                    option = self.options[option_name]
                    option.read_func(option, self, parts)
                except KeyError:
                    print 'Warning: Unsupported project file line "%s"' % line.strip()
        fp.close()
        if fromfile == self.filename:
            self.set_dirty(False)

    def save(self, destfile=None):
        if destfile == None:
            destfile = self.filename
        if destfile == None:
            raise Exception, 'No filename specified for project'
        # Write values of options that were previously found
        # in project file
        fp = open(destfile, 'wb')
        for line in self.lines:
            parts = line.strip().split(None, 1)

            option_name = None
            if parts:
                option_name = parts[0]

            try:
                option = self.options[option_name]
                # If project file contains more than one line corresponding to the
                # same option first one will be overwritten and all the rest ones will be
                # left unchanged
                if not option.emitted:
                    option.write_func(option, self, fp)
                    option.emitted = True
                else:
                    fp.write(line)
            except KeyError:
                fp.write(line)
        # Write values of newly added options
        for _, option in self.options.items():
            if not option.emitted:
                option.write_func(option, self, fp)
            option.emitted = False # Reset emitted field for next save() call

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

