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

import gtk, gtk.gdk, gobject, os, sys, commands, shutil
from stat import *
from subprocess import *

# i18n
import gettext
t = gettext.translation('xgsch2pcb', fallback=True)
_ = t.ugettext

# xgsch2pcb-specific modules
from funcs import *
from gsch2pcbproject import Gsch2PCBProject
from pcbmanager import PCBManager

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
        scrollwin.add_with_viewport(self.pagelist)
        column = gtk.TreeViewColumn(None, gtk.CellRendererText(), text=0)
        self.pagelist.append_column(column)
        selection = self.pagelist.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect('changed',
                          self.event_pagelist_selection_changed)
        self.pagelist.set_headers_visible(False)
        
        # Horizontal button box containing 'add page' and 'remove page'
        # buttons
        addremovebox = gtk.HButtonBox()
        addremovebox.set_layout(gtk.BUTTONBOX_SPREAD)
        vbox.pack_start(addremovebox, False, True)

        self.addpagebutton = gtk.Button(stock=gtk.STOCK_ADD)
        addremovebox.pack_start(self.addpagebutton)
        self.addpagebutton.connect("clicked",
                       self.event_addpage_button_clicked)
        
        self.removepagebutton = gtk.Button(stock=gtk.STOCK_REMOVE)
        self.removepagebutton.connect("clicked",
                                      self.event_removepage_button_clicked)
        addremovebox.pack_start(self.removepagebutton)
        
        # Buttons to run gschem/gattrib
        self.editpagebutton = gtk.Button(_("Edit schematic"))
        vbox.pack_start(self.editpagebutton, False, True)

        # TODO: Is this wanted? The padding seems wrong
        #image = gtk.Image()
        #image.set_from_stock(gtk.STOCK_EDIT,gtk.ICON_SIZE_BUTTON)
        #self.editpagebutton.set_image(image)

        self.editpagebutton.connect("clicked",
                       self.event_schematic_button_clicked,
                       "gschem")
        
        self.attribpagebutton = gtk.Button(_("Edit attributes"))
        vbox.pack_start(self.attribpagebutton, False, True)
        
        # TODO: Is this wanted? The padding seems wrong
        #image = gtk.Image()
        #image.set_from_stock(gtk.STOCK_EDIT,gtk.ICON_SIZE_BUTTON)
        #self.attribpagebutton.set_image(image)

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

        self.changepcbbutton = gtk.Button(_("Change layout file"))
        vbox.pack_start(self.changepcbbutton, False, False)
        self.changepcbbutton.connect("clicked",
                       self.event_changepcb_button_clicked)


        def about_url_cb(dialog, link, user_data):
            try:
      			    gnomevfs.url_show( link )
            except:
                pass

        # About dialog
        # ------------
        self.aboutdialog = gtk.AboutDialog()
        self.aboutdialog.set_name(_("xgsch2pcb - a GUI for gsch2pcb"))
        self.aboutdialog.set_version("1.0")
        self.aboutdialog.set_copyright("University of Cambridge 2006")
        self.aboutdialog.set_authors(['Peter Brett', 'Peter Clifton'])
        gtk.about_dialog_set_url_hook(about_url_cb, None)
        self.aboutdialog.set_website('http://geda.seul.org/')

        self.pcbmanager = None
        self.set_project(project)


    def __init_toolbar__(self, box):
        toolbar = gtk.Toolbar()
        box.pack_start(toolbar, False, True)
        self.toolbar_buttons = {}

        button = gtk.ToolButton(gtk.STOCK_QUIT)
        toolbar.insert(button, -1)
        button.connect("clicked",
                       self.event_quit_button_clicked) 
        self.toolbar_buttons['quit'] = button

        toolbar.insert(gtk.SeparatorToolItem(), -1)
        
        button = gtk.ToolButton(gtk.STOCK_NEW)
        toolbar.insert(button, -1)
        button.connect("clicked",
                       self.event_new_button_clicked)
        self.toolbar_buttons['new'] = button

        button = gtk.ToolButton(gtk.STOCK_OPEN)
        toolbar.insert(button, -1)
        button.connect("clicked",
                       self.event_open_button_clicked)
        self.toolbar_buttons['open'] = button

        button = gtk.ToolButton(gtk.STOCK_SAVE)
        toolbar.insert(button, -1)
        button.connect("clicked",
                       self.event_save_button_clicked)
        self.toolbar_buttons['save'] = button

        #button = gtk.ToolButton(gtk.STOCK_SAVE_AS)
        #toolbar.insert(button, -1)
        #button.connect("clicked",
        #               self.event_saveas_button_clicked)
        #self.toolbar_buttons['saveas'] = button

        button = gtk.ToolButton(gtk.STOCK_CLOSE)
        toolbar.insert(button, -1)
        button.connect("clicked",
                       self.event_close_button_clicked)
        self.toolbar_buttons['close'] = button

        #button = gtk.ToolButton(gtk.STOCK_PROPERTIES)
        #toolbar.insert(button, -1)
        #button.connect("clicked",
        #               self.event_properties_button_clicked)
        #self.toolbar_buttons['close'] = button
        #button.set_sensitive(False) #FIXME

        toolbar.insert(gtk.SeparatorToolItem(), -1)
        
        button = gtk.ToolButton(gtk.STOCK_ABOUT)
        toolbar.insert(button, -1)
        button.connect("clicked",
                       self.event_about_button_clicked)
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

    def event_pagelist_selection_changed(self, selection):
        (model, iter) = selection.get_selected()
        page_selected = (iter != None)
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
                open(filename, 'w').close()
            self.project.add_page(filename)
            break

        add_dialog.hide_all()


    def event_removepage_button_clicked(self, button):
        (model, iter) = self.pagelist.get_selection().get_selected()
        if iter == None:
            return
        page = model.get_value(iter, 0)
        self.project.remove_page(page)

    def event_schematic_button_clicked(self, button, tool):
        (model, iter) = self.pagelist.get_selection().get_selected()
        page = model.get_value(iter, 0)

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

        Popen([toolpath, page])

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



    def event_new_button_clicked( self, button ):

        if self.close_project( _("creating a new project")):
            # User cancelled out of creating a new project
            return

        d = gtk.FileChooserDialog(_('New project...'), self,
                              (gtk.DIALOG_MODAL | 
                               gtk.DIALOG_DESTROY_WITH_PARENT),
                              (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                               gtk.STOCK_NEW, gtk.RESPONSE_OK))
        filter = gtk.FileFilter()
        filter.add_pattern('*.gsch2pcb')
        d.set_filter(filter)
        d.set_do_overwrite_confirmation( True )
        d.set_action(gtk.FILE_CHOOSER_ACTION_SAVE)

        d.show_all()
        r = d.run()
        d.hide_all()

        if r != gtk.RESPONSE_OK:
            return

        path = d.get_filename()
        if not path.endswith('.gsch2pcb'):
            path += '.gsch2pcb'

       	self.set_project(path)
        self.project.save()


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
        self.changepcbbutton.set_sensitive( managers )


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

            self.project = Gsch2PCBProject(filename)
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
        self.pcbmanager.update_layout( self.project.pages )
        
gobject.type_register( MonitorWindow )

class AddPageDialog(gtk.Dialog):
    def __init__(self, parent, defaultfilename="untitled.sch"):
        gtk.Dialog.__init__(self, _('Add schematic page...'), parent,
                            (gtk.DIALOG_MODAL |
                             gtk.DIALOG_DESTROY_WITH_PARENT),
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                             gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        

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
