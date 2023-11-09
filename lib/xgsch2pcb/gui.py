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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject

import os, sys, shutil

import config, funcs

# i18n
import gettext
t = gettext.translation(config.PACKAGE, config.localedir, fallback=True)
_ = t.gettext

# xgsch2pcb-specific modules
from funcs import *
from gsch2pcbproject import Gsch2PCBProject
from pcbmanager import PCBManager
from new_project_gui import NewProjectAssistant

try:
    import gnomevfs
except:
    # We won't be able to launch URLs
    pass

class MonitorWindow(Gtk.Window):

    # ======================================================================== #
    # Initialisers
    # ======================================================================== #
    
    def __init__(self, project=None, **kvargs):
        super().__init__(title="xgsch2pcb", width_request=400, height_request=300, events=Gdk.EventMask.FOCUS_CHANGE_MASK, **kvargs)

        self.project = None
        self.pcbmanager = None

        self.connect("focus-in-event", self.event_focused)
        self.connect("delete_event", self.event_delete)

        mainvbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.add(mainvbox)

        # Initialize toolbar
        self.__init_toolbar__(mainvbox)

        # Hbox contains two vboxes, one for page editing widgets, one
        # for layout editing widgets
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True, spacing=5, margin=5)
        mainvbox.pack_start(hbox, True, True, 0)

        # Page editing widgets
        # --------------------
        frame = Gtk.Frame(label=_("Schematic pages"), shadow_type=Gtk.ShadowType.ETCHED_IN)
        hbox.add(frame)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, border_width=5)
        frame.add(vbox)

        scrollwin = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.ETCHED_IN, hscrollbar_policy=Gtk.PolicyType.AUTOMATIC, vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrollwin, True, True, 0)
        
        # Treeview showing available schematic pages
        self.pagelist = Gtk.TreeView(model=Gtk.ListStore(str), headers_visible=False)
        self.pagelist.connect('row-activated',
                              self.event_pagelist_row_activated)
        scrollwin.add(self.pagelist)
        column = Gtk.TreeViewColumn(None, Gtk.CellRendererText(), text=0)
        self.pagelist.append_column(column)
        selection = self.pagelist.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect('changed', self.event_pagelist_selection_changed)
        
        # Horizontal box containing 'add page' and 'remove page' buttons
        addremovebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True, spacing=3)
        vbox.pack_start(addremovebox, False, True, 0)

        self.addpagebutton = Gtk.Button(label="_Add", use_underline=True)
        addremovebox.pack_start(self.addpagebutton, True, True, 0)
        self.addpagebutton.connect("clicked",
                       self.event_addpage_button_clicked)
        
        self.removepagebutton = Gtk.Button(label="_Remove", use_underline=True)
        self.removepagebutton.connect("clicked",
                                      self.event_removepage_button_clicked)
        addremovebox.pack_start(self.removepagebutton, True, True, 0)
        
        # Buttons to run gschem/gattrib
        self.editpagebutton = Gtk.Button(label=_("Edit schematic"))
        vbox.pack_start(self.editpagebutton, False, True, 0)

        self.editpagebutton.connect("clicked",
                       self.event_schematic_button_clicked,
                       "gschem")

        self.attribpagebutton = Gtk.Button(label=_("Edit attributes"))
        vbox.pack_start(self.attribpagebutton, False, True, 0)

        self.attribpagebutton.connect("clicked",
                       self.event_schematic_button_clicked,
                       "gattrib")


        # Layout editing widgets
        # ----------------------
        frame = Gtk.Frame(label=_("Layout"), shadow_type=Gtk.ShadowType.ETCHED_IN)
        hbox.add(frame)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, border_width=5)
        frame.add(vbox)

        self.pcbentry = Gtk.Entry(editable=False)
        vbox.pack_start(self.pcbentry, False, True, 0)

        self.editpcbbutton = Gtk.Button(label=_("Edit layout"))
        vbox.pack_start(self.editpcbbutton, False, False, 0)
        self.editpcbbutton.connect("clicked",
                       self.event_editpcb_button_clicked)

        self.updatepcbbutton = Gtk.Button(label=_("Update layout"))
        vbox.pack_start(self.updatepcbbutton, False, False, 0)
        self.updatepcbbutton.connect("clicked",
                       self.event_updatepcb_button_clicked)

        """
        self.changepcbbutton = Gtk.Button(label=_("Change layout file"))
        vbox.pack_start(self.changepcbbutton, False, False, 0)
        self.changepcbbutton.connect("clicked",
                       self.event_changepcb_button_clicked)
        """



        # About dialog
        # ------------
        self.aboutdialog = Gtk.AboutDialog(
            name=_("xgsch2pcb"),
            comments=_("a GUI for gsch2pcb"),
            version=config.VERSION,
            copyright="University of Cambridge 2006\nxgsch2pcb Contributors 2006-2009 (See ChangeLog)",
            authors=['Peter Brett', 'Peter Clifton', 'Andrey Smirnov'],
            website='http://www.geda-project.org/',
            license_type=Gtk.License.GPL_2_0,
            translator_credits=_('translator-credits'),
            transient_for=self,
        )

        self.pcbmanager = None
        self.set_project(project)

    def __init_toolbar__(self, box):
        toolbar = Gtk.Toolbar()
        box.pack_start(toolbar, False, True, 0)
        self.toolbar_buttons = {}

        button = Gtk.ToolButton(icon_name="application-exit", tooltip_text=_("Quit"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_quit_button_clicked)
        self.toolbar_buttons['quit'] = button

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        button = Gtk.ToolButton(icon_name="document-new", tooltip_text=_("New project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_new_button_clicked)
        self.toolbar_buttons['new'] = button

        button = Gtk.ToolButton(icon_name="document-open", tooltip_text=_("Open project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_open_button_clicked)
        self.toolbar_buttons['open'] = button

        button = Gtk.ToolButton(icon_name="document-save", tooltip_text=_("Save project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_save_button_clicked)
        self.toolbar_buttons['save'] = button

        #button = Gtk.ToolButton(icon_name="document-save-as", tooltip_text=_("Save project as..."))
        #toolbar.insert(button, -1)
        #button.connect("clicked", self.event_saveas_button_clicked)
        #self.toolbar_buttons['saveas'] = button

        button = Gtk.ToolButton(icon_name="window-close", tooltip_text=_("Close project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_close_button_clicked)
        self.toolbar_buttons['close'] = button

#        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        button = Gtk.ToolButton(icon_name="document-properties", label=_("Options"), tooltip_text=_("Project options"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_options_button_clicked)
        self.toolbar_buttons['options'] = button

        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        button = Gtk.ToolButton(icon_name="help-about", tooltip_text=_("About xgsch2pcb"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_about_button_clicked)
        self.toolbar_buttons['about'] = button


    # ======================================================================== #
    # Signal handlers
    # ======================================================================== #

    def event_project_dirty_changed(self, project, dirty):
        self.update_title()

    def event_project_page_added(self, project, page):
        model = self.pagelist.get_model()
        model.append([page])
        self.set_pcbsensitivities()

    def event_project_page_removed(self, project, page):
        model = self.pagelist.get_model()
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 0) == page:
                model.remove(iter)
                break
            iter = model.iter_next(iter)
        self.set_pcbsensitivities()

    def event_pagelist_row_activated(self, treeview, path, view_column):
        # Prod the "Open schematic" button if it is sensitive
        if self.editpagebutton.get_property("sensitive"):
            self.editpagebutton.clicked()

    def event_pagelist_selection_changed(self, selection):
        page_selected = selection.count_selected_rows()
        self.removepagebutton.set_sensitive(page_selected)
        self.editpagebutton.set_sensitive(page_selected)
        self.attribpagebutton.set_sensitive(page_selected)
        
    def event_addpage_button_clicked(self, button):
        numpages = len(self.project.pages)
        pagename = '%s-page%s.sch' % (self.project.output_name,
                                      numpages+1)

        add_dialog = AddPageDialog(self, pagename)
        while (True):
            add_dialog.show_all()
            r = add_dialog.run()

            if r != Gtk.ResponseType.OK:
                break

            from_file = add_dialog.is_from_existing()
            filename = add_dialog.get_filename()
            if filename == None:
                md = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True, destroy_with_parent=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=_('You must select either an existing schematic file or enter a filename for a new file.'),
                )
                md.show_all()
                md.run()
                md.hide()
                continue

            # If the user's specified a schematic that's not in a
            # subdirectory of the project directory, complain.
            if funcs.rel_path(filename).startswith('../'):
                md = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True, destroy_with_parent=True,
                    message_type=Gtk.MessageType.WARNING,
                    text=_('<span weight="bold" size="larger">Selected file is outside the project directory\nAdd anyway?</span>\n\nProjects are best kept in self contained directories. Ensure that you don\'t move or delete any external files, or the project will be incomplete.'),
                    use_markup=True,   
                    border_width=6                 
                )
                md.vbox.set_spacing( 12 )

                md.add_button('_Cancel', Gtk.ResponseType.CANCEL)
                md.add_button(_("_Add anyway"), Gtk.ResponseType.OK)

                md.show_all()
                r = md.run()
                md.hide()
                
                if r != Gtk.ResponseType.OK:
                    continue

            filename = funcs.rel_path(filename)

            if not os.path.exists(filename):
                # Create a new zero-length file in place
                try:
                    open(filename, 'w').close()
                except IOError as err:
                    md = Gtk.MessageDialog(
                        transient_for=self,
                        modal=True, destroy_with_parent=True,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text=_('<span weight="bold" size="larger">Could not create schematic</span>\n\nError %i: %s') % (err.errno, err.strerror),
                        use_markup=True,
                    )
                    md.show_all()
                    md.run()
                    md.hide()
                    continue
                except:
                    #TODO: Provide a GUI Dialog for this
                    md = Gtk.MessageDialog(
                        transient_for=self,
                        modal=True, destroy_with_parent=True,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text=_('<span weight="bold" size="larger">Could not create schematic</span>'),
                        use_markup=True,
                    )
                    md.show_all()
                    md.run()
                    md.hide()
                    continue

            self.project.add_page(filename)
            break

        add_dialog.hide()


    def event_removepage_button_clicked(self, button):
        # Because we're modifying the treeview at the same time as
        # reading from it, we need to make a list of
        # Gtk.TreeRowReferences (which are persistent over
        # modification of a treemodel) and then iterate over that.
        (model, paths) = self.pagelist.get_selection().get_selected_rows()
        refs = map(Gtk.TreeRowReference, [model]*len(paths), paths)
        for ref in refs:
            page = model.get_value(model.get_iter(ref.get_path()), 0)
            self.project.remove_page(page)


    def event_schematic_button_clicked(self, button, tool):
        
        # Call a private helper function defined above for each
        # selected schematic page in order to build a list of pages.
        pages = []
        def buildpagelist_func(model, path, iter):
            pages.append(model.get_value(iter, 0))
        self.pagelist.get_selection().selected_foreach(buildpagelist_func)

        # Launch the requested tool
        # FIXME does this work for gattrib?
        toolpath = funcs.find_tool_path(tool)
        if toolpath == None:
            md = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_('Could not locate tool: %s') % tool,
            )
            md.show_all()
            md.run()
            md.hide()
            return

        subprocess.Popen([toolpath] + pages)
            
    def event_editpcb_button_clicked(self, button):
        
        # Check if the layout might need updating
        if self.pcbmanager.needs_updating( self.project.pages ):
        
            # Ask if the user wants to update the layout
            d = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text=_("Your schematic has changed.\n\nWould you like to update your PCB layout?")
            )
            d.add_button(_("Leave layout unchanged"), Gtk.ResponseType.CANCEL)
            d.add_button(_("Update layout"), Gtk.ResponseType.YES)
            d.show_all()
            do_update = (d.run() == Gtk.ResponseType.YES)
            d.hide()

            if do_update:
                # Update the layout (leaving PCB open)
                self.update_layout()
                return
        
        # TODO: Catch any exceptions which might prevent this working
        self.pcbmanager.open_layout()

    def event_updatepcb_button_clicked(self, button):
        # Update the layout (leaving PCB open)
        self.update_layout()
    
    # TODO: Implement me
    """
    def event_changepcb_button_clicked(self, button):

        d = Gtk.MessageDialog(
            transient_for=self,
            modal=True, destroy_with_parent=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=_('<span weight="bold" size="larger">Unimplemented feature</span>\n\nRenaming the layout file not implemented'),
            use_markup=True,
        )
        d.show_all()
        d.run()
        d.hide()
    """


    def event_new_button_clicked( self, button ):

        def new_project_apply( assistant, filename ):
            self.set_project( filename )

        if self.close_project( _("creating a new project")):
            # User cancelled out of creating a new project
            return

        assistant = NewProjectAssistant(self)
        assistant.connect( 'project-apply', new_project_apply )
        assistant.show_all()

    def event_open_button_clicked( self, button ):
       
        reason = _("opening a new project")

        # If tools are open there is no point asking the user a filename
        if self.check_no_tools( reason ):
            return

        filter = Gtk.FileFilter()
        filter.add_pattern('*.gsch2pcb')
        
        fcd = Gtk.FileChooserDialog(
            title=_('Open Project...'),
            transient_for=self,
            modal=True, destroy_with_parent=True,
            show_hidden=False,
            filter=filter,
            action=Gtk.FileChooserAction.OPEN,
            local_only=True,
        )
        fcd.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        fcd.add_button("_Open", Gtk.ResponseType.OK)
        fcd.show_all()
        r = fcd.run()
        fcd.hide()

        if r != Gtk.ResponseType.OK:
            return
        
        filename = fcd.get_filename()
        
        # The user has an option to cancel here
        if self.close_project( reason ):
            return
       
        self.set_project( filename )


    def event_save_button_clicked( self, button ):
        self.project.save()
        
    ## TODO: Implement me
    #def event_saveas_button_clicked( self, button ):
    #    pass

    def event_close_button_clicked( self, button ):
        self.close_project( _("closing the project") )

    def event_quit_button_clicked(self, button):
        self.handle_quit()

    def event_options_button_clicked(self, button):
        options_dialog = ProjectOptionsDialog(parent=self, name=_("Options dialog"))

        options_dialog.show_all()
        options_dialog.run()
        options_dialog.hide()

        self.project.elements_dir = []
        options_dialog.path_chooser.path_model.foreach(
            lambda m, p, i, ud: self.project.elements_dir.append(m.get_value(i, 0)),
            None)

        self.project.m4_command   = options_dialog.m4_command_entry.get_text()
        self.project.m4_pcbdir    = options_dialog.m4_pcbpath_entry.get_text()
        self.project.m4_file      = options_dialog.m4_extra_file_entry.get_text()
        self.project.gnetlist_arg = options_dialog.gnetlist_arg_entry.get_text()


    def event_about_button_clicked(self, button):
        self.aboutdialog.show_all()
        self.aboutdialog.run()
        self.aboutdialog.hide()

    def event_focused(self, window, direction):
        self.set_pcbsensitivities()

    def event_delete(self, window, event):
        return self.handle_quit()

    # ======================================================================== #
    # General utility methods
    # ======================================================================== #

    def update_title( self ):

        if self.project:
            title = os.path.split(self.project.filename)[1]
            if self.project.dirty:
                title += _(' [modified]')
            title += " - "
    
        else:
            title = ''
        
        title += "xgsch2pcb"
        self.set_title(title)


    def set_projectsensitivities(self):

        projectman = not ( self.project == None )

        widget_list = ( self.toolbar_buttons['save'],
                        #self.toolbar_buttons['saveas'],
                        self.toolbar_buttons['close'],
                        self.toolbar_buttons['options'],
                        self.pagelist,
                        self.addpagebutton )

        for widget in widget_list:
            widget.set_sensitive( projectman )


    def set_pcbsensitivities(self):
        
        projectman = not ( self.project == None )
        pcbmanager = not ( self.pcbmanager == None )

        if pcbmanager and self.pcbmanager.is_layout_open():
            pcbrunning = True
        else:
            pcbrunning = False

        if self.project and len( self.project.pages ) > 0:
            pages_available = True
        else:
            pages_available = False

        managers = projectman and pcbmanager

        self.pcbentry.set_sensitive( managers )
        self.editpcbbutton.set_sensitive( managers and (not pcbrunning) )
        self.updatepcbbutton.set_sensitive( managers and pages_available )
        #self.changepcbbutton.set_sensitive( managers )


    def handle_quit (self):
        if self.close_project( _("exiting") ):
            return True
        Gtk.main_quit()


    def set_project(self, filename):
        assert self.pcbmanager == None
        
        if filename == None:
            self.project = None
        else:
            
            dirname = os.path.dirname(filename)
            if dirname:
                os.chdir(dirname)

            basename = os.path.basename(filename)

            self.project = Gsch2PCBProject(basename)
            self.project.connect('dirty-flag-changed',
                                 self.event_project_dirty_changed)
            self.project.connect('page-added',
                                 self.event_project_page_added)
            self.project.connect('page-removed',
                                 self.event_project_page_removed)

            # TODO FIXME mangle for i18n support
            self.pcbentry.set_text(funcs.rel_path(self.project.output_name + ".pcb"))

            try:
                self.pcbmanager = PCBManager(self.project)
            # TODO: Subclass Exception to be more specific in PCBManager
            except Exception as instance:
                message = str( instance )
                md = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True, destroy_with_parent=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=_('<span weight="bold" size="larger">Problem initialising</span>\n%s') % message,
                    use_markup=True,
                )
                md.show_all()
                md.run()
                md.hide()
            
        # TODO set model for self.pagelist
        pagelistmodel = self.pagelist.get_model()
        pagelistmodel.clear()

        if self.project:
            for page in self.project.pages:
                pagelistmodel.append([page])

        selection = self.pagelist.get_selection()
        selection.unselect_all()
        selection.emit('changed')

        self.set_projectsensitivities()
        self.set_pcbsensitivities()

        # TODO: Could this trigger on a signal?
        self.update_title()

    def check_no_tools( self, reason = None ):
        """
        Prompts the user, and teturns true if there is still a tool open
        """

        # If the layout is still open, don't allow the project to close
        if self.pcbmanager and self.pcbmanager.is_layout_open():
            d = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                border_width=6,
            )
            if reason:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor before %s.') % reason)
            else:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor first.'))
               
            d.vbox.set_spacing( 12 )
            d.show_all()
            d.run()
            d.hide()

            return True

        return False

    def close_project( self, reason = None ):
        """
        Returns true if for some reason we wish to cancel the close operation
        """
        
        # If the layout is still open, don't allow the project to close
        if self.pcbmanager and self.pcbmanager.is_layout_open():
            d = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                border_width=6,
            )
            if reason:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor before %s.') % reason)
            else:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor first.'))
               
            d.vbox.set_spacing( 12 )
            d.show_all()
            d.run()
            d.hide()

            return True

        # Check if any tools are open, prompting the user if so
        if self.check_no_tools( reason ):
            return True

        # TODO: Where should this go? in check_no_tools perhaps?
        self.pcbmanager = None

        if self.project and self.project.dirty:
            md = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.NONE,
                text=_('<span weight="bold" size="larger">Save the changes to project "%s" before closing?</span>\n\nAny changes made since the last save will be lost.') % self.project.filename,
                use_markup=True,
                border_width=6,
            )

            md.vbox.set_spacing( 12 )
            md.add_button( _("Close _without Saving"), Gtk.ResponseType.CLOSE)
            md.add_button("_Cancel", Gtk.ResponseType.CANCEL)
            md.add_button("_Save", Gtk.ResponseType.OK)

            md.show_all()
            r = md.run()
            md.hide()
            if r == Gtk.ResponseType.OK:
                # TODO: Need to attempt a save, possibly using a save box
                # if the save is cancelled, we must also cancel the close

                # Save the project
                self.project.save()

            elif r != Gtk.ResponseType.CLOSE:
                # User doesn't cancelled the dialog
                return True

        # TODO: ACTUALLY CLOSE THE PROJECT
        self.set_project( None )

        return False

    def update_layout( self ):
        # TODO: Catch any exceptions which might prevent this working
        unfound = self.pcbmanager.update_layout( self.project.pages )
        if len(unfound) > 0:
            results_string = '<span weight="bold" size="larger">' + \
                             _('Elements missing from layout') + '</span>\n\n' + \
                             _('The footprints for the following elements were not found.\nPlease check the \'footprint\' attribute for these elements:\n')

            for [ refdes, footprint ] in unfound:
                results_string = results_string + '\n  ' + refdes + ' (footprint=' + footprint + ')'

            md = Gtk.MessageDialog(
                transient_for=self,
                modal=True, destroy_with_parent=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=results_string,
                use_markup=True,
                border_width=6,
            )

            md.vbox.set_spacing( 12 )

            md.show_all()
            md.run()
            md.hide()


GObject.type_register( MonitorWindow )

class AddPageDialog(Gtk.Dialog):
    def __init__(self, parent, defaultfilename="untitled.sch"):
        super().__init__(
            title=_('Add schematic page...'),
            transient_for=parent,
            modal=True, destroy_with_parent=True,
            window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
            border_width=0,
        )
        self.add_button('_Cancel', Gtk.ResponseType.CANCEL)
        self.add_button('_OK', Gtk.ResponseType.OK)

        grid = Gtk.Grid(row_spacing=6, margin_top=12, margin_bottom=18, margin_start=6, margin_end=6)
        self.vbox.pack_start( grid , False, False, 0)

        # Two radio buttons allow you to select whether to use an
        # existing file or create a new file
        self.fileradio = Gtk.RadioButton(label=_('From file:'), margin_end=12, active=True)
        self.fileradio.connect('toggled', self.event_radio_toggled)

        grid.attach(self.fileradio, 0, 0, 1, 1)

        self.newradio = Gtk.RadioButton(label=_('Create new:'), group=self.fileradio, margin_end=12)
        self.newradio.connect('toggled', self.event_radio_toggled)

        grid.attach(self.newradio, 0, 1, 1, 1)

        # File chooser button to select and existing file.  Currently
        # limited to local files 'cos gsch2pcb can't handle remote
        # files.
        schfilter = Gtk.FileFilter()
        schfilter.add_pattern('*.sch')
        self.filebutton = Gtk.FileChooserButton(
            title=_('Select schematic page...'),
            filter=schfilter,
            local_only=True,
            action=Gtk.FileChooserAction.OPEN,
        )
        self.filebutton.connect( "selection-changed", self.event_filebutton_selection_changed )
        grid.attach(self.filebutton, 1, 0, 1, 1)

        # Text entry field to enter the filename of a new schematic
        # page to create
        self.newentry = Gtk.Entry(text=defaultfilename)
        grid.attach(self.newentry, 1, 1, 1, 2)

        self.fileradio.emit('toggled')

        # TODO: Get bug fixed in GTK+, or find proper solution

        # Workaround possible bug in GTK+
        self.last_filename = None

    def event_filebutton_selection_changed( self, filebutton ):
        
        # Unfortunatly (a bug in GTK+ perhaps?), where the 
        # "selection-changed" event is sometimes fired when 
        # the user CANCELS from the file-chooser (if an existing
        # filename was present when we started)

        filename = self.filebutton.get_filename()

        # Workaround the bug if the filename hasn't changed

        if filename == self.last_filename:
            # Still isn't perfect, if the user selects opening
            # the same file, they must then click "Ok" on our
            # dialog.
            return

        self.last_filename = filename

        self.response( Gtk.ResponseType.OK )
        
    
    def event_radio_toggled(self, button):
        is_file = self.is_from_existing()
        self.filebutton.set_sensitive(is_file)
        self.newentry.set_sensitive(not is_file)
        
    def is_from_existing(self):
        return self.fileradio.get_active()
    
    def get_filename(self):
        if self.is_from_existing():
            return self.filebutton.get_filename()
        else:
            return self.newentry.get_text()

GObject.type_register ( AddPageDialog )

class PathChooser(Gtk.Box):
    def remove_clicked_cb(self, button, treeview):
        [model, iter] = treeview.get_selection().get_selected()

        if not iter:
            return

        model.remove(iter)

    def add_clicked_cb(self, button, pathmodel):
        filedialog = Gtk.FileChooserDialog(
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        filedialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        filedialog.add_button("_Add", Gtk.ResponseType.OK)

        filedialog.show_all()
        response = filedialog.run()
        filedialog.hide()

        if response == Gtk.ResponseType.OK:
            for path in filedialog.get_filenames():
                it   = pathmodel.get_iter_first()
                unique = True
                while it is not None:
                    if pathmodel.get_value(it, 0) == path:
                        unique = False
                        break
                    it = pathmodel.iter_next(it)
                if unique:
                    pathmodel.append([path, "black"])



    def selection_changed_cb(self, treeselection):
        [model, iter] = treeselection.get_selected()
        self.remove_button.set_sensitive(True if iter else False)


    def __init__(self, directories, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, **kwargs)

        frame = Gtk.Frame(shadow_type=Gtk.ShadowType.IN)
        self.pack_start(frame, True, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        frame.add(hbox)

        pathmodel = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        for path in directories:
            pathmodel.append([path, "black"])
        self.path_model = pathmodel

        scrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)
        treeview = Gtk.TreeView(
            model=pathmodel,
            headers_visible=False,
            height_request=1, width_request=1,
            vadjustment=scrollbar.get_adjustment(),
        )
        hbox.pack_start(treeview, True, True, 0)
        hbox.pack_start(scrollbar, False, True, 0)

        renderer = Gtk.CellRendererText()
        treeview.insert_column_with_attributes(0, "", renderer, text=0, foreground=1)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pack_start(hbox, False, True, 0)

        self.add_button = Gtk.Button(image=Gtk.Image(icon_name="list-add", icon_size=Gtk.IconSize.BUTTON))
        hbox.pack_start(self.add_button, False, True, 0)

        self.remove_button = Gtk.Button(image=Gtk.Image(icon_name="list-remove", icon_size=Gtk.IconSize.BUTTON), sensitive=False)
        hbox.pack_start(self.remove_button, False, True, 0)


        treeview.get_selection().connect("changed", self.selection_changed_cb)
        self.remove_button.connect("clicked", self.remove_clicked_cb, treeview)
        self.add_button.connect("clicked", self.add_clicked_cb, pathmodel)

GObject.type_register( PathChooser )

class ProjectOptionsDialog(Gtk.Dialog):
    def __init__(self, parent, **kwargs):
        super().__init__(
            title=_('Project options'),
            transient_for=parent,
            modal=True, destroy_with_parent=True,
            **kwargs
        )
        self.add_button("_Close", Gtk.ResponseType.CLOSE)

        self.project = parent.project

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=12, spacing=6)
        self.vbox.pack_start(vbox, False, False, 0)

        label = Gtk.Label(label=_("<b>General</b>"), use_markup=True, xalign=0)
        vbox.pack_start(label, False, True, 0)

        generalvbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=12)
        vbox.pack_start(generalvbox, False, True, 0)
        
        checkbutton = Gtk.CheckButton(label=_("Preserve PCB elements not in the schematic"), active=parent.project.preserve_unfound)
        generalvbox.pack_start(checkbutton, False, True, 0)
        checkbutton.connect('toggled', self.preserve_pcb_checkbox_toggled)

        radiobutton = None
        for choice, label in [(Gsch2PCBProject.PREFER_M4_FOOTPRINTS, _("Prefer M4 footprints to file footprints")),
                              (Gsch2PCBProject.PREFER_FILE_FOOTPRINTS, _("Prefer file footprints to M4 footprints")),
                              (Gsch2PCBProject.USE_ONLY_FILE_FOOTPRINTS, _("Only use file footprints"))]:
            radiobutton = Gtk.RadioButton(label=label, group=radiobutton, active=parent.project.footprint_type_choice == choice)
            generalvbox.pack_start(radiobutton, False, True, 0)
            radiobutton.connect('toggled', self.footprints_radio_toggled, choice)

        label = Gtk.Label(label=_("<b>Footprint search paths</b>"), use_markup=True, xalign=0)
        vbox.pack_start(label, False, True, 0)

        self.path_chooser = PathChooser(parent.project.elements_dir, margin_top=6, margin_bottom=6, margin_start=12)
        vbox.pack_start(self.path_chooser, True, True, 0)

        advancedoptions = Gtk.Expander(label_widget=Gtk.Label(label=_("Advanced options"), margin=6))
        vbox.pack_start(advancedoptions, False, True, 0)

        advancedvbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        advancedoptions.add(advancedvbox)

        label = Gtk.Label(label=_("<b>M4 Options</b>"), use_markup=True, xalign=0)
        advancedvbox.pack_start(label, False, False, 0)

        grid = Gtk.Grid(margin_start=12, column_spacing=6, row_spacing=6)
        advancedvbox.pack_start(grid, False, False, 0)

        self.m4_command_entry = Gtk.Entry()
        self.m4_pcbpath_entry = Gtk.Entry()
        self.m4_extra_file_entry = Gtk.Entry()

        for i, (entry, label_text, entry_contents) in enumerate([
                (self.m4_command_entry,    _("M4 command :"),    parent.project.m4_command),
                (self.m4_pcbpath_entry,    _("M4 PCB path :"),   parent.project.m4_pcbdir),
                (self.m4_extra_file_entry, _("M4 extra file :"), parent.project.m4_file)]):
            label = Gtk.Label(label=label_text, xalign=0)
            grid.attach (label, 0, i, 1, 1)

            if entry_contents:
                entry.set_text(entry_contents)

            grid.attach (entry, 1, i, 1, 1)

        label = Gtk.Label(label=_("<b>Extra gnetlist arguments</b>"), use_markup=True, xalign=0)
        advancedvbox.pack_start(label, False, True, 0)

        self.gnetlist_arg_entry = Gtk.Entry()
        if parent.project.gnetlist_arg:
            self.gnetlist_arg_entry.set_text(parent.project.gnetlist_arg)

        advancedvbox.pack_start(self.gnetlist_arg_entry, False, True, 0)

    def preserve_pcb_checkbox_toggled(self, widget, data=None):
        self.project.preserve_unfound = widget.get_active()
        # self.parent.project.set_dirty(True)
    def footprints_radio_toggled(self, widget, data=None):
        self.project.footprint_type_choice = data
        # self.parent.project.set_dirty(True)

GObject.type_register( ProjectOptionsDialog )
