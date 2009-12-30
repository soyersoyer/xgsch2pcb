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

import gtk, gtk.gdk, gobject, os, sys, commands, shutil
from stat import *
from subprocess import *

import config

# i18n
import gettext
t = gettext.translation(config.PACKAGE, config.localedir, fallback=True)
_ = t.ugettext

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

class MonitorWindow(gtk.Window):

    # ======================================================================== #
    # Initialisers
    # ======================================================================== #
    
    def __init__(self, project=None):
        gtk.Window.__init__(self)

        self.project = None
        self.pcbmanager = None

        self.set_title("xgsch2pcb")
        self.set_size_request(400,300)
        self.set_events(gtk.gdk.FOCUS_CHANGE_MASK)
        self.connect("focus-in-event", self.event_focused)
        self.connect("delete_event", self.event_delete)

        mainvbox = gtk.VBox(False, 5)
        self.add(mainvbox)

        # Initialize toolbar
        self.__init_toolbar__(mainvbox)

        # Hbox contains two vboxes, one for page editing widgets, one
        # for layout editing widgets
        
        hbox = gtk.HBox(True, 5)
        mainvbox.pack_start(hbox)

        # Page editing widgets
        # --------------------
        frame = gtk.Frame(_("Schematic pages"))
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        hbox.add(frame)

        vbox = gtk.VBox(False, 3)
        vbox.set_border_width(5)
        frame.add(vbox)

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy (gtk.POLICY_AUTOMATIC,
                              gtk.POLICY_AUTOMATIC)
        vbox.pack_start(scrollwin, True, True)
        
        # Treeview showing available schematic pages
        self.pagelist = gtk.TreeView(gtk.ListStore(str))
        self.pagelist.connect('row-activated',
                              self.event_pagelist_row_activated)
        scrollwin.add_with_viewport(self.pagelist)
        column = gtk.TreeViewColumn(None, gtk.CellRendererText(), text=0)
        self.pagelist.append_column(column)
        selection = self.pagelist.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed',
                          self.event_pagelist_selection_changed)
        self.pagelist.set_headers_visible(False)
        
        # Horizontal box containing 'add page' and 'remove page' buttons
        addremovebox = gtk.HBox()
        addremovebox.set_homogeneous(True)
        vbox.pack_start(addremovebox, False, True)

        self.addpagebutton = gtk.Button(stock=gtk.STOCK_ADD)
        addremovebox.pack_start(self.addpagebutton, True, True)
        self.addpagebutton.connect("clicked",
                       self.event_addpage_button_clicked)
        
        self.removepagebutton = gtk.Button(stock=gtk.STOCK_REMOVE)
        self.removepagebutton.connect("clicked",
                                      self.event_removepage_button_clicked)
        addremovebox.pack_start(self.removepagebutton, True, True)
        
        # Buttons to run gschem/gattrib
        self.editpagebutton = gtk.Button(_("Edit schematic"))
        vbox.pack_start(self.editpagebutton, False, True)

        # TODO: Is this wanted? The padding seems wrong
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_EDIT,gtk.ICON_SIZE_BUTTON)
        self.editpagebutton.set_image(image)

        self.editpagebutton.connect("clicked",
                       self.event_schematic_button_clicked,
                       "gschem")

        self.attribpagebutton = gtk.Button(_("Edit attributes"))
        vbox.pack_start(self.attribpagebutton, False, True)

        # TODO: Is this wanted? The padding seems wrong
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_EDIT,gtk.ICON_SIZE_BUTTON)
        self.attribpagebutton.set_image(image)

        self.attribpagebutton.connect("clicked",
                       self.event_schematic_button_clicked,
                       "gattrib")


        # Layout editing widgets
        # ----------------------
        frame = gtk.Frame(_("Layout"))
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        hbox.add(frame)

        vbox = gtk.VBox(False, 3)
        vbox.set_border_width(5)
        frame.add(vbox)

        self.pcbentry = gtk.Entry()
        self.pcbentry.set_property('editable', False)
        vbox.pack_start(self.pcbentry, False, True)

        self.editpcbbutton = gtk.Button(_("Edit layout"))
        vbox.pack_start(self.editpcbbutton, False, False)
        self.editpcbbutton.connect("clicked",
                       self.event_editpcb_button_clicked)

        self.updatepcbbutton = gtk.Button(_("Update layout"))
        vbox.pack_start(self.updatepcbbutton, False, False)
        self.updatepcbbutton.connect("clicked",
                       self.event_updatepcb_button_clicked)

        """
        self.changepcbbutton = gtk.Button(_("Change layout file"))
        vbox.pack_start(self.changepcbbutton, False, False)
        self.changepcbbutton.connect("clicked",
                       self.event_changepcb_button_clicked)
        """


        def about_url_cb(dialog, link, user_data):
            try:
      			    gnomevfs.url_show( link )
            except:
                pass

        # About dialog
        # ------------
        self.aboutdialog = gtk.AboutDialog()
        self.aboutdialog.set_name(_("xgsch2pcb"))
        self.aboutdialog.set_comments(_("a GUI for gsch2pcb"))
        self.aboutdialog.set_version(config.VERSION)
        self.aboutdialog.set_copyright("University of Cambridge 2006\nxgsch2pcb Contributors 2006-2009 (See ChangeLog)")
        self.aboutdialog.set_authors(['Peter Brett', 'Peter Clifton', 'Andrey Smirnov'])
        gtk.about_dialog_set_url_hook(about_url_cb, None)
        self.aboutdialog.set_website('http://www.gpleda.org/')
        self.aboutdialog.set_translator_credits(_('translator-credits'))
        self.aboutdialog.set_transient_for( self )


        self.pcbmanager = None
        self.set_project(project)

    def __init_toolbar__(self, box):
        toolbar = gtk.Toolbar()
        box.pack_start(toolbar, False, True)
        self.toolbar_buttons = {}

        button = gtk.ToolButton(gtk.STOCK_QUIT)
        button.set_tooltip_text(_("Quit"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_quit_button_clicked)
        self.toolbar_buttons['quit'] = button

        toolbar.insert(gtk.SeparatorToolItem(), -1)

        button = gtk.ToolButton(gtk.STOCK_NEW)
        button.set_tooltip_text(_("New project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_new_button_clicked)
        self.toolbar_buttons['new'] = button

        button = gtk.ToolButton(gtk.STOCK_OPEN)
        button.set_tooltip_text(_("Open project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_open_button_clicked)
        self.toolbar_buttons['open'] = button

        button = gtk.ToolButton(gtk.STOCK_SAVE)
        button.set_tooltip_text(_("Save project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_save_button_clicked)
        self.toolbar_buttons['save'] = button

        #button = gtk.ToolButton(gtk.STOCK_SAVE_AS)
        #button.set_tooltip_text(_("Save project as..."))
        #toolbar.insert(button, -1)
        #button.connect("clicked", self.event_saveas_button_clicked)
        #self.toolbar_buttons['saveas'] = button

        button = gtk.ToolButton(gtk.STOCK_CLOSE)
        button.set_tooltip_text(_("Close project"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_close_button_clicked)
        self.toolbar_buttons['close'] = button

#        toolbar.insert(gtk.SeparatorToolItem(), -1)

        icon = gtk.Image()
        icon.set_from_stock(gtk.STOCK_PROPERTIES, toolbar.get_icon_size())
        button = gtk.ToolButton(icon, _("Options"))
        button.set_tooltip_text(_("Project options"))
        toolbar.insert(button, -1)
        button.connect("clicked", self.event_options_button_clicked)
        self.toolbar_buttons['options'] = button

        toolbar.insert(gtk.SeparatorToolItem(), -1)

        button = gtk.ToolButton(gtk.STOCK_ABOUT)
        button.set_tooltip_text(_("About xgsch2pcb"))
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

            if r != gtk.RESPONSE_ACCEPT:
                break

            from_file = add_dialog.is_from_existing()
            filename = add_dialog.get_filename()
            if filename == None:
                md = gtk.MessageDialog(self,
                                       (gtk.DIALOG_MODAL |
                                        gtk.DIALOG_DESTROY_WITH_PARENT),
                                       gtk.MESSAGE_ERROR,
                                       gtk.BUTTONS_OK,
                                       _('You must select either an existing schematic file or enter a filename for a new file.'))
                md.show_all()
                md.run()
                md.hide_all()
                continue

            # If the user's specified a schematic that's not in a
            # subdirectory of the project directory, complain.
            if rel_path(filename).startswith('../'):
                md = gtk.MessageDialog(self,
                                       (gtk.DIALOG_MODAL |
                                        gtk.DIALOG_DESTROY_WITH_PARENT),
                                       gtk.MESSAGE_WARNING,
                                       gtk.BUTTONS_NONE)

                md.set_markup(_('<span weight="bold" size="larger">Selected file is outside the project directory\nAdd anyway?</span>\n\nProjects are best kept in self contained directories. Ensure that you don\'t move or delete any external files, or the project will be incomplete.'))

                # Set GUI spacings
                md.set_border_width( 6 )
                md.vbox.set_spacing( 12 )
                #md.hbox.border_width( 6 )
                #md.hbox.set_spacing( 12 )

                md.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)
                button = gtk.Button(_("_Add anyway"))
                image = gtk.Image()
                image.set_from_stock( gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON )
                button.set_image( image )
                md.add_action_widget(button, gtk.RESPONSE_ACCEPT)

                md.show_all()
                r = md.run()
                md.hide_all()
                
                if r != gtk.RESPONSE_ACCEPT:
                    continue

            filename = rel_path(filename)

            if not os.path.exists(filename):
                # Create a new zero-length file in place
                try:
                    open(filename, 'w').close()
                except IOError, (errno, strerror):
                    md = gtk.MessageDialog(self,
                                           (gtk.DIALOG_MODAL |
                                            gtk.DIALOG_DESTROY_WITH_PARENT),
                                           gtk.MESSAGE_ERROR,
                                           gtk.BUTTONS_OK )

                    md.set_markup( _('<span weight="bold" size="larger">Could not create schematic</span>\n\nError %i: %s') % (errno, strerror) )
                    md.show_all()
                    md.run()
                    md.hide_all()
                    continue
                except:
                    #TODO: Provide a GUI Dialog for this
                    md = gtk.MessageDialog(self,
                                           (gtk.DIALOG_MODAL |
                                            gtk.DIALOG_DESTROY_WITH_PARENT),
                                           gtk.MESSAGE_ERROR,
                                           gtk.BUTTONS_OK )

                    md.set_markup( _('<span weight="bold" size="larger">Could not create schematic</span>') )
                    md.show_all()
                    md.run()
                    md.hide_all()
                    continue

            self.project.add_page(filename)
            break

        add_dialog.hide_all()


    def event_removepage_button_clicked(self, button):
        # Because we're modifying the treeview at the same time as
        # reading from it, we need to make a list of
        # gtk.TreeRowReferences (which are persistent over
        # modification of a treemodel) and then iterate over that.
        (model, paths) = self.pagelist.get_selection().get_selected_rows()
        refs = map(gtk.TreeRowReference, [model]*len(paths), paths)
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
        toolpath = find_tool_path(tool)
        if toolpath == None:
            md = gtk.MessageDialog(self,
                                   (gtk.DIALOG_MODAL |
                                    gtk.DIALOG_DESTROY_WITH_PARENT),
                                   gtk.MESSAGE_ERROR,
                                   gtk.BUTTONS_OK,
                                   _('Could not locate tool: %s') % tool)
            md.show_all()
            md.run()
            md.hide_all()
            return
        
        Popen([toolpath] + pages)
            
    def event_editpcb_button_clicked(self, button):
        
        # Check if the layout might need updating
        if self.pcbmanager.needs_updating( self.project.pages ):
        
            # Ask if the user wants to update the layout
            d = gtk.MessageDialog(self,
                                  (gtk.DIALOG_MODAL | 
                                   gtk.DIALOG_DESTROY_WITH_PARENT),
                                  gtk.MESSAGE_QUESTION,
                                  gtk.BUTTONS_NONE,
                                  _("Your schematic has changed.\n\nWould you like to update your PCB layout?"))
            d.add_buttons(_("Leave layout unchanged"), gtk.RESPONSE_REJECT,
                          _("Update layout"), gtk.RESPONSE_ACCEPT)
            d.show_all()
            do_update = (d.run() == gtk.RESPONSE_ACCEPT)
            d.hide_all()

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

        d = gtk.MessageDialog(self,
                              (gtk.DIALOG_MODAL | 
                               gtk.DIALOG_DESTROY_WITH_PARENT),
                              gtk.MESSAGE_INFO,
                              gtk.BUTTONS_OK)
        d.set_markup(_('<span weight="bold" size="larger">Unimplemented feature</span>\n\nRenaming the layout file not implemented'))
        d.show_all()
        d.run()
        d.hide_all()
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

        filter = gtk.FileFilter()
        filter.add_pattern('*.gsch2pcb')
        
        fcd = gtk.FileChooserDialog(_('Open Project...'), self,
                                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                     gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
        fcd.set_show_hidden (False)
        fcd.set_filter (filter)
        fcd.set_action (gtk.FILE_CHOOSER_ACTION_OPEN)
        fcd.set_local_only (True)

        fcd.show_all()
        r = fcd.run()
        fcd.hide_all()

        if r != gtk.RESPONSE_ACCEPT:
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
        options_dialog = ProjectOptionsDialog( self )
        options_dialog.set_name(_("Options dialog"))
        options_dialog.set_transient_for( self )

        options_dialog.show_all()
        options_dialog.run()
        options_dialog.hide_all()

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
        self.aboutdialog.hide_all()

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
        gtk.main_quit()


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
            self.pcbentry.set_text(rel_path(self.project.output_name + ".pcb"))

            try:
                self.pcbmanager = PCBManager(self.project)
            # TODO: Subclass Exception to be more specific in PCBManager
            except Exception, (instance):
                message = str( instance )
                md = gtk.MessageDialog(self,
                                       (gtk.DIALOG_MODAL |
                                        gtk.DIALOG_DESTROY_WITH_PARENT),
                                       gtk.MESSAGE_ERROR,
                                       gtk.BUTTONS_OK )

                md.set_markup( _('<span weight="bold" size="larger">Problem initialising</span>\n%s') % message )
                md.show_all()
                md.run()
                md.hide_all()
            
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
            d = gtk.MessageDialog(self,
                              (gtk.DIALOG_MODAL | 
                               gtk.DIALOG_DESTROY_WITH_PARENT),
                              gtk.MESSAGE_ERROR,
                              gtk.BUTTONS_OK)
            if reason:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor before %s.') % reason)
            else:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor first.'))
               
            # Set GUI spacings
            d.set_border_width( 6 )
            d.vbox.set_spacing( 12 )
            d.show_all()
            d.run()
            d.hide_all()

            return True

        return False

    def close_project( self, reason = None ):
        """
        Returns true if for some reason we wish to cancel the close operation
        """
        
        # If the layout is still open, don't allow the project to close
        if self.pcbmanager and self.pcbmanager.is_layout_open():
            d = gtk.MessageDialog(self,
                              (gtk.DIALOG_MODAL | 
                               gtk.DIALOG_DESTROY_WITH_PARENT),
                              gtk.MESSAGE_ERROR,
                              gtk.BUTTONS_OK)
            if reason:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor before %s.') % reason)
            else:
                d.set_markup( 
                    _('<span weight="bold" size="larger">Layout editor still open</span>\n\nClose the layout editor first.'))
               
            # Set GUI spacings
            d.set_border_width( 6 )
            d.vbox.set_spacing( 12 )
            d.show_all()
            d.run()
            d.hide_all()

            return True

        # Check if any tools are open, prompting the user if so
        if self.check_no_tools( reason ):
            return True

        # TODO: Where should this go? in check_no_tools perhaps?
        self.pcbmanager = None

        if self.project and self.project.dirty:
            md = gtk.MessageDialog(self,
                                   (gtk.DIALOG_MODAL |
                                    gtk.DIALOG_DESTROY_WITH_PARENT),
                                   gtk.MESSAGE_WARNING,
                                   gtk.BUTTONS_NONE)

            md.set_markup(_('<span weight="bold" size="larger">Save the changes to project "%s" before closing?</span>\n\nAny changes made since the last save will be lost.') % self.project.filename)

            # Set GUI spacings
            md.set_border_width( 6 )
            md.vbox.set_spacing( 12 )
            md.add_buttons( _("Close _without Saving"), gtk.RESPONSE_CLOSE,
                                      gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                      gtk.STOCK_SAVE, gtk.RESPONSE_OK )
            md.show_all()
            r = md.run()
            md.hide_all()
            if r == gtk.RESPONSE_OK:
                # TODO: Need to attempt a save, possibly using a save box
                # if the save is cancelled, we must also cancel the close

                # Save the project
                self.project.save()

            elif r != gtk.RESPONSE_CLOSE:
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

            md = gtk.MessageDialog(self,
                                   (gtk.DIALOG_MODAL |
                                    gtk.DIALOG_DESTROY_WITH_PARENT),
                                   gtk.MESSAGE_WARNING,
                                   gtk.BUTTONS_OK)

            md.set_markup( results_string )

            # Set GUI spacings
            md.set_border_width( 6 )
            md.vbox.set_spacing( 12 )
            #md.hbox.border_width( 6 )
            #md.hbox.set_spacing( 12 )

            md.show_all()
            md.run()
            md.hide_all()


gobject.type_register( MonitorWindow )

class AddPageDialog(gtk.Dialog):
    def __init__(self, parent, defaultfilename="untitled.sch"):
        gtk.Dialog.__init__(self, _('Add schematic page...'), parent,
                            (gtk.DIALOG_MODAL |
                             gtk.DIALOG_DESTROY_WITH_PARENT),
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                             gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.set_position( gtk.WIN_POS_CENTER_ON_PARENT )

        table = gtk.Table(2,2)
        
        # GUI Spacing
        self.set_has_separator( False )
        self.set_border_width( 0 )
        table.set_row_spacings( 6 )
        
        # GUI Spacing
        alignment = gtk.Alignment( 0, 0, 0, 0 )
        alignment.set_padding( 12, 18, 6, 6 )
        alignment.add( table )
        
        self.vbox.pack_start( alignment )

        # Two radio buttons allow you to select whether to use an
        # existing file or create a new file
        self.fileradio = gtk.RadioButton(label=_('From file:'))
        self.fileradio.connect('toggled', self.event_radio_toggled)
        
        # GUI Spacing
        alignment = gtk.Alignment( 0, 0, 0, 0 )
        alignment.set_padding( 0, 0, 0, 12 )
        alignment.add( self.fileradio )

        table.attach(alignment, 0, 1, 0, 1, gtk.FILL, 0)

        self.newradio = gtk.RadioButton(self.fileradio, _('Create new:'))
        self.newradio.connect('toggled', self.event_radio_toggled)
        
        # GUI Spacing
        alignment = gtk.Alignment( 0, 0, 0, 0 )
        alignment.set_padding( 0, 0, 0, 12 )
        alignment.add( self.newradio )

        table.attach(alignment, 0, 1, 1, 2, gtk.FILL, 0)

        # File chooser button to select and existing file.  Currently
        # limited to local files 'cos gsch2pcb can't handle remote
        # files.
        self.filebutton = gtk.FileChooserButton(_('Select schematic page...'))
        self.filebutton.connect( "selection-changed", self.event_filebutton_selection_changed )
        self.filebutton.set_local_only(True)
        self.filebutton.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
        schfilter = gtk.FileFilter()
        schfilter.add_pattern('*.sch')
        self.filebutton.set_filter(schfilter)
        table.attach(self.filebutton, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0)

        # Text entry field to enter the filename of a new schematic
        # page to create
        self.newentry = gtk.Entry()
        self.newentry.set_text(defaultfilename)
        table.attach(self.newentry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0)

        self.fileradio.set_active(True)
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

        self.response( gtk.RESPONSE_ACCEPT )
        
    
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

gobject.type_register ( AddPageDialog )

# TODO: Need a mechanism to open a new project as a "NEW" project, when a
#       project with that filename already exists on disk. This is for
#       over-writing an existing project of the same name.

class NewProjectDialog(gtk.FileChooserDialog):
    def __init__(self, parent):
        gtk.FileChooserDialog.__init__(self, _('New project...'), parent,
                            gtk.FILE_CHOOSER_ACTION_SAVE,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                             gtk.STOCK_NEW, gtk.RESPONSE_ACCEPT))
        
        # TODO: Might add a more complex interface for a generic project manager

        # TODO: Decide if this is worth the high dependancy of PyGTK 2.8+
        self.set_do_overwrite_confirmation( True )

        # TODO: Decide if this is worth the high dependancy of PyGTK 2.8+
        self.connect( "confirm-overwrite", self.signal_confirm_overwrite )

	filter = gtk.FileFilter()
        filter.add_pattern('*.gsch2pcb')
        self.set_filter(filter)

    
    # TODO: Decide if this is worth the high dependancy of PyGTK 2.8+
    # TODO: Implement a dialog to prompt about
    #       over-writing an existing project
    def signal_confirm_overwrite( self, filechooser ):
        
        md = gtk.MessageDialog(self,
                               (gtk.DIALOG_MODAL |
                                gtk.DIALOG_DESTROY_WITH_PARENT),
                               gtk.MESSAGE_WARNING,
                               gtk.BUTTONS_NONE)

        # TODO: Split to just give the filename
        filename = self.get_filename()
        dirname = self.get_current_folder()

        md.set_markup(_('<span weight="bold" size="larger">A project named "%s" already exists. Do you want to replace it?</span>\n\nThe project already exists in directory "%s". Replacing it will overwrite its contents.') % ( filename, dirname ))

        # Set GUI spacings
        md.set_border_width( 6 )
        md.vbox.set_spacing( 12 )
        #md.hbox.border_width( 6 )
        #md.hbox.set_spacing( 12 )

        md.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)
        
        button = gtk.Button( _("_Replace") )
        image = gtk.Image()
        image.set_from_stock( gtk.STOCK_SAVE_AS, gtk.ICON_SIZE_BUTTON )
        button.set_image( image )
        md.add_action_widget(button, gtk.RESPONSE_ACCEPT)

        md.show_all()
        r = md.run()
        md.hide_all()
        
        if r != gtk.RESPONSE_ACCEPT:
            return gtk.FILE_CHOOSER_CONFIRMATION_SELECT_AGAIN
        
        return gtk.FILE_CHOOSER_CONFIRMATION_ACCEPT_FILENAME

gobject.type_register( NewProjectDialog )


class PathChooser(gtk.VBox):
    def remove_clicked_cb(self, button, treeview):
        [model, iter] = treeview.get_selection().get_selected()

        if not iter:
            return

        model.remove(iter)

    def add_clicked_cb(self, button, pathmodel):
        filedialog = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                           buttons= (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                                     gtk.STOCK_ADD, gtk.RESPONSE_ACCEPT))

        filedialog.show_all()
        response = filedialog.run()
        filedialog.hide_all()

        if response == gtk.RESPONSE_ACCEPT:
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


    def __init__(self, directories):
        gtk.VBox.__init__(self, False, 0)

        # GUI Spacing
        self.set_spacing(6)

        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_IN)
        self.pack_start(frame, True, True)

        hbox = gtk.HBox()
        frame.add(hbox)

        pathmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        for path in directories:
            pathmodel.append([path, "black"])
        self.path_model = pathmodel

        treeview = gtk.TreeView(pathmodel)
        hbox.pack_start(treeview, True, True)

        scrollbar = gtk.VScrollbar()
        hbox.pack_start(scrollbar, False, True)

        renderer = gtk.CellRendererText()
        treeview.insert_column_with_attributes(0, "", renderer, text=0, foreground=1)
        treeview.set_headers_visible(False)

        treeview.set_vadjustment(scrollbar.get_adjustment())
        treeview.set_headers_visible(False)
        treeview.set_size_request(1,1)

        hbox = gtk.HBox()
        self.pack_start(hbox, False, True)

        # GUI Spacing
        hbox.set_spacing(6)

        addbutton = gtk.Button(stock=gtk.STOCK_ADD)
        hbox.pack_start(addbutton, False, True)
        self.add_button = addbutton

        removebutton = gtk.Button(stock=gtk.STOCK_REMOVE)
        removebutton.set_sensitive(False)
        hbox.pack_start(removebutton, False, True)
        self.remove_button = removebutton


        treeview.get_selection().connect("changed", self.selection_changed_cb)
        self.remove_button.connect("clicked", self.remove_clicked_cb, treeview)
        self.add_button.connect("clicked", self.add_clicked_cb, pathmodel)

gobject.type_register( PathChooser )

class ProjectOptionsDialog(gtk.Dialog):
    def __init__(self, parent):
        gtk.Dialog.__init__(self, _('Project options'), parent,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            ( gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE ))

        self.project = parent.project

        # GUI Spacing
        self.set_has_separator(False)
        #self.set_border_width(12)

        alignment = gtk.Alignment( 0, 0, 1, 1 )
        alignment.set_padding( 12, 12, 12, 12 )
        self.vbox.pack_start(alignment)

        vbox = gtk.VBox()
        alignment.add(vbox)
        vbox.set_spacing(6)

        label = gtk.Label(_("<b>General</b>"))
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        vbox.pack_start(label, False, True)

        alignment = gtk.Alignment( 0, 0, 0, 0 )
        alignment.set_padding( 6, 6, 12, 0 )
        vbox.pack_start(alignment, False, True)

        generalvbox = gtk.VBox()
        alignment.add(generalvbox)
        generalvbox.set_spacing(6)

        checkbutton = gtk.CheckButton(_("Preserve PCB elements not in the schematic"))
        checkbutton.set_active(parent.project.preserve_unfound)
        generalvbox.pack_start(checkbutton, False, True)
        checkbutton.connect('toggled', self.preserve_pcb_checkbox_toggled)

        radiobutton = None
        for choice, label in [(Gsch2PCBProject.PREFER_M4_FOOTPRINTS, _("Prefer M4 footprints to file footprints")),
                              (Gsch2PCBProject.PREFER_FILE_FOOTPRINTS, _("Prefer file footprints to M4 footprints")),
                              (Gsch2PCBProject.USE_ONLY_FILE_FOOTPRINTS, _("Only use file footprints"))]:
            radiobutton = gtk.RadioButton(radiobutton, label)
            radiobutton.set_active(parent.project.footprint_type_choice == choice)
            generalvbox.pack_start(radiobutton, False, True)
            radiobutton.connect('toggled', self.footprints_radio_toggled, choice)

        label = gtk.Label(_("<b>Footprint search paths</b>"))
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        vbox.pack_start(label, False, True)

        alignment = gtk.Alignment( 0, 0, 1, 1 )
        alignment.set_padding( 6, 6, 12, 0 )
        vbox.pack_start(alignment, True, True)

        pathchooser = PathChooser(parent.project.elements_dir)
        alignment.add (pathchooser)
        self.path_chooser = pathchooser

        advancedoptions = gtk.Expander(_("Advanced options"))
        advancedoptions.set_spacing(6)
        label = advancedoptions.get_label_widget()
        label.set_padding(6,6)
        vbox.pack_start(advancedoptions, False, True)

        advancedvbox = gtk.VBox()
        advancedoptions.add(advancedvbox)

        # GUI Spacing
        advancedvbox.set_spacing(6)

        label = gtk.Label(_("<b>M4 Options</b>"))
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        advancedvbox.pack_start(label)

        alignment = gtk.Alignment( 0, 0, 1, 0 )
        alignment.set_padding( 0, 0, 12, 0 )
        advancedvbox.pack_start(alignment)

        table = gtk.Table(3, 2)
        alignment.add( table )

        # GUI Spacing
        table.set_row_spacings(6)
        table.set_col_spacings(6)

        self.m4_command_entry = gtk.Entry()
        self.m4_pcbpath_entry = gtk.Entry()
        self.m4_extra_file_entry = gtk.Entry()

        for i, (entry, label_text, entry_contents) in enumerate([
                (self.m4_command_entry,    _("M4 command :"),    parent.project.m4_command),
                (self.m4_pcbpath_entry,    _("M4 PCB path :"),   parent.project.m4_pcbdir),
                (self.m4_extra_file_entry, _("M4 extra file :"), parent.project.m4_file)]):
            label = gtk.Label(label_text)
            label.set_alignment(0, 0.5)
            table.attach (label, 0, 1, i, i + 1, gtk.FILL)

            if entry_contents:
                entry.set_text(entry_contents)

            table.attach (entry, 1, 2, i, i + 1)

        label = gtk.Label(_("<b>Extra gnetlist arguments</b>"))
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        advancedvbox.pack_start(label, False, True)

        self.gnetlist_arg_entry = gtk.Entry()
        if parent.project.gnetlist_arg:
            self.gnetlist_arg_entry.set_text(parent.project.gnetlist_arg)

        advancedvbox.pack_start(self.gnetlist_arg_entry, False, True)

    def preserve_pcb_checkbox_toggled(self, widget, data=None):
        self.project.preserve_unfound = widget.get_active()
        # self.parent.project.set_dirty(True)
    def footprints_radio_toggled(self, widget, data=None):
        self.project.footprint_type_choice = data
        # self.parent.project.set_dirty(True)

gobject.type_register( ProjectOptionsDialog )
