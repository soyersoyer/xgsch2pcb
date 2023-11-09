# -*-Python-*-

# xgsch2pcb - a GUI for gsch2pcb
# Copyright (C) 2006 University of Cambridge
# Copyright (C) 2007 Peter Clifton <pcjc2@cam.ac.uk>
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk, Gdk

import config

import os
import gettext
t = gettext.translation(config.PACKAGE, config.localedir, fallback=True)
_ = t.gettext

# xgsch2pcb-specific modules
from templates import list_templates, gsch2pcb_template
from gsch2pcbproject import Gsch2PCBProject

class NewProjectAssistant(Gtk.Assistant):

    __gsignals__ = { 'project-apply' :
                            ( GObject.SignalFlags.NO_RECURSE,
                              GObject.TYPE_NONE,
                              (GObject.TYPE_STRING, )),
                   }

    template = None

    def assistant_apply(self, assistant):

        # TODO: Why special case testing the writability of just this ONE output file?
        filename = self.get_filename()

        # Create a new zero-length file
        try:
            if self.template:
                # Apply any chosen template
                templ = gsch2pcb_template( self.template )
                templ.apply( self.get_projectname() )
            else:
                # Otherwise just write out a new project file
                # Start with a filename of None to ensure that
                # we don't load an existing project file.
                new_project = Gsch2PCBProject( None,
                                               self.get_projectname() )

                new_project.save(self.get_filename())
        except IOError as err:
            md = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_('<span weight="bold" size="larger">Could not create project</span>\n\nError %i: %s') % (err.errno, err.strerror),
                use_markup=True,
            )

            md.show_all()
            md.run()
            md.hide()
            return
        except Exception as err:
            md = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_('<span weight="bold" size="larger">Could not create project</span>') + "\n\nError: %s" % err,
                use_markup=True,
            )

            md.show_all()
            md.run()
            md.hide()
            return

        self.emit('project-apply', filename)


    def assistant_cancel(self, assistant):
        self.destroy()

    def assistant_close(self, assistant):
        self.destroy()

    def template_radio_toggled(self, button):
        is_blank = self.blankradio.get_active()
        self.templateview.set_sensitive(not is_blank)
        if is_blank:
            self.set_page_complete(self.template_page, True)
        else:
            # Synthesise a selection changed update on the tree-view
            self.template_selection_changed(self.templateview.get_selection())

    def template_selection_changed(self, treeselection):
        [model,iters] = treeselection.get_selected()
        if iters:
            self.set_page_complete(self.template_page, True)
            template_no = model.get_path(iters)[0]
            [self.template, description] = model.get(iters,0,2)   # TODO: Remove magic numbers
            self.description.set_text(description)
        else:
            self.set_page_complete(self.template_page, False)
            self.template = None
            self.description.set_text("")

    def get_path(self):
        path = self.filebutton.get_filename()
        return path

    def get_filename(self):
        filename = self.filename.get_text()
        # TODO: REMOVE HARDCODED EXTENTIONS - SHOULD THIS CODE GO HERE?
        if not filename.endswith('.gsch2pcb'):
            filename += '.gsch2pcb'
        return filename

    def get_projectname(self):
        # TODO: Decide if this is the right way to do this
        filename = self.get_filename()
        # TODO: REMOVE HARDCODED EXTENTIONS - SHOULD THIS CODE GO HERE?
        projectname = filename[0:filename.rfind( '.gsch2pcb' )]
        return projectname

    def __init__(self, parent):
        super().__init__(transient_for=parent, window_position=Gtk.WindowPosition.CENTER_ON_PARENT)


        # ====================
        # Choose template page
        # ====================

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=12, spacing=6)
        label = Gtk.Label(label=_("<b>Choose project template</b>"), use_markup=True, xalign=0)
        page.pack_start(label, False, False, 0)

        options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin=12, spacing=6)
        page.pack_start(options, True, True, 0)

        self.blankradio = Gtk.RadioButton(label=_("Blank"))
        self.templradio = Gtk.RadioButton(group=self.blankradio,
                                          label=_("From template:"))
        options.pack_start(self.blankradio, False, False, 0)
        options.pack_start(self.templradio, False, False, 0)

        self.templatelist = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING)
        templates = list_templates()
        for template in templates:
            self.templatelist.append( template )

        if len(templates) == 0:
            self.templradio.set_sensitive(False)
            self.templatelist.append( ['', _("(No templates found)"),''] )

        textrenderer = Gtk.CellRendererText()
        textcol = Gtk.TreeViewColumn(None, textrenderer, text=1)

        self.templateview = Gtk.TreeView(model=self.templatelist, headers_visible=False, sensitive=False)
        self.templateview.append_column(textcol)

        scrollwin = Gtk.ScrolledWindow(
            hexpand=True, vexpand=True, margin_start=18,
            shadow_type=Gtk.ShadowType.IN,
            hscrollbar_policy=Gtk.PolicyType.NEVER, vscrollbar_policy=Gtk.PolicyType.ALWAYS)
        scrollwin.add(self.templateview)

        options.pack_start(scrollwin, True, True, 0)

        self.description = Gtk.Label(wrap=True, xalign=0, yalign=0, margin_start=18, selectable=True, max_width_chars=0)
        options.pack_start(self.description, False, False, 0)

        self.append_page(page)
        self.set_page_title(page, _("Template"))

        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, True)
        self.template_page = page

        self.blankradio.connect('toggled', self.template_radio_toggled)
        self.templradio.connect('toggled', self.template_radio_toggled)

        treeselection = self.templateview.get_selection()
        treeselection.connect('changed', self.template_selection_changed)

        # ============================
        # Choose project filename page
        # ============================

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=12, spacing=6)
        label = Gtk.Label(label=_("<b>Choose project filename</b>"), use_markup=True, xalign=0)
        page.pack_start(label, False, False, 0)

        options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin=12)
        page.pack_start(options, True, True, 0)
        
        grid = Gtk.Grid(column_spacing=6, row_spacing=6)
        label = Gtk.Label(label=_("Project name:"), xalign=0)
        grid.attach(label, 0, 0, 1, 1)
        self.filename = Gtk.Entry(hexpand=True)
        grid.attach(self.filename, 1, 0, 1, 1)
        label = Gtk.Label(label=_("Location:"), xalign=0)
        grid.attach(label, 0, 1, 1, 1)

        def filebutton_selection_changed_cb(filechooser):
            # Change to the specified location
            os.chdir( self.get_path() )

        self.filebutton = Gtk.FileChooserButton(
            title=_('Select project location...'),
            hexpand=True,
            local_only=True,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        self.filebutton.connect( "selection-changed", filebutton_selection_changed_cb )

        grid.attach(self.filebutton, 1, 1, 1, 1)

        options.pack_start(grid, False, False, 0)

        self.append_page(page)
        self.set_page_title(page, _("Filename"))
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, False)
        self.filename_page = page

        def filename_changed_cb( filename_entry ):
            entrytext = self.filename.get_text()
            self.set_page_complete(self.filename_page, (not entrytext == ""))

        self.filename.connect('changed', filename_changed_cb)

        # ================
        # Creation summary
        # ================

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=12, spacing=6)
        label = Gtk.Label(label=_("<b>Project summary</b>"), use_markup=True, xalign=0)
        page.pack_start(label, False, False, 0)

        explanation = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin=12, valign=Gtk.Align.START)
        page.pack_start(explanation, True, True, 0)

        self.newfiles_frame = Gtk.Frame(
            label_widget=Gtk.Label(label=_("<b>New files to be created:</b>"), use_markup=True),
            shadow_type=Gtk.ShadowType.NONE,
        )
        explanation.pack_start(self.newfiles_frame, False, False, 0)

        self.newfiles_list = Gtk.Label(hexpand=True, vexpand=True, xalign=0, margin=12)
        self.newfiles_frame.add(self.newfiles_list)

        self.overwrite_frame = Gtk.Frame(
            label_widget=Gtk.Label(label=_("<b>The following files would be overwritten:</b>"), use_markup=True),
            shadow_type=Gtk.ShadowType.NONE,
        )
        explanation.pack_start(self.overwrite_frame, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin_end=12, margin_top=12, margin_bottom=12)   
        self.overwrite_frame.add(vbox)

        self.overwrite_list = Gtk.Label(xalign=0, margin_top=12, margin_bottom=12)
        vbox.pack_start(self.overwrite_list, False, False, 0)

        self.confirm_overwrite = Gtk.CheckButton(label=_("Confirm overwrite"))
        vbox.pack_start(self.confirm_overwrite, False, False, 0)

        def confirm_overwrite_toggled_cb( togglebutton ):
            confirmed = togglebutton.get_active()
            self.set_page_complete(self.summary_page, confirmed)

        self.confirm_overwrite.connect( 'toggled', confirm_overwrite_toggled_cb )

        self.append_page(page)
        self.set_page_title(page, _("Summary"))
        self.set_page_type(page, Gtk.AssistantPageType.CONFIRM)
        self.summary_page = page


        def check_overwrites():
            if self.template:
                templ = gsch2pcb_template( self.template )
                file_list = templ.would_create( self.get_projectname() )
            else:
                file_list = [self.get_filename()]
            newfiles_list = []
            overwrite_list = []
            for file in file_list:
                if os.path.exists( file ):
                    overwrite_list.append( file )
                else:
                    newfiles_list.append( file )
            return [newfiles_list, overwrite_list]

        def assistant_prepare_cb(assistant, page):
            if page is self.summary_page:
                # Summary page before creating the new project on disk
                [newfiles_list, overwrite_list] = check_overwrites()
                self.newfiles_list.set_text( '\n'.join( newfiles_list ) )
                self.overwrite_list.set_text( '\n'.join( overwrite_list ) )

                no_newfiles = (newfiles_list == [])
                if no_newfiles:
                    self.newfiles_frame.hide()
                else:
                    self.newfiles_frame.show_all()

                no_overwrite = (overwrite_list == [])
                if no_overwrite:
                    # No files will be overwritten, we are done
                    self.overwrite_frame.hide()
                    self.set_page_complete(self.summary_page, True)
                else:
                    # Need confirmation before overwriting files
                    self.overwrite_frame.show_all()
                    self.confirm_overwrite.set_active(False)

        # GtkAssistant signals
        self.connect('prepare', assistant_prepare_cb  )
        self.connect('apply',   self.assistant_apply  )
        self.connect('cancel',  self.assistant_cancel )
        self.connect('close',   self.assistant_close  )


GObject.type_register( NewProjectAssistant )
