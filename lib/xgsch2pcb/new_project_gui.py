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
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import gtk, gtk.gdk, gobject

import gettext
t = gettext.translation('xgsch2pcb', fallback=True)
_ = t.ugettext

# xgsch2pcb-specific modules
from templates import *

class NewProjectAssistant(gtk.Assistant):

    __gsignals__ = { 'project-apply' :
                            ( gobject.SIGNAL_NO_RECURSE,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_STRING, )),
                   }

    template = None

    def assistant_apply(self, assistant):

        # Change to the specified location
        os.path.chdir( self.get_path() )

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
        except IOError, (errno, strerror):
            md = gtk.MessageDialog(self,
                                   (gtk.DIALOG_MODAL |
                                    gtk.DIALOG_DESTROY_WITH_PARENT),
                                   gtk.MESSAGE_ERROR,
                                   gtk.BUTTONS_OK )

            md.set_markup( _('<span weight="bold" size="larger">Could not create project</span>\n\nError %i: %s') % (errno, strerror) )
            md.show_all()
            md.run()
            md.hide_all()
            return
        except:
            md = gtk.MessageDialog(self,
                                   (gtk.DIALOG_MODAL |
                                    gtk.DIALOG_DESTROY_WITH_PARENT),
                                   gtk.MESSAGE_ERROR,
                                   gtk.BUTTONS_OK )

            md.set_markup( _('<span weight="bold" size="larger">Could not create project</span>') )
            md.show_all()
            md.run()
            md.hide_all()
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
        gtk.Assistant.__init__(self)
        self.set_transient_for( parent )
        self.set_position( gtk.WIN_POS_CENTER_ON_PARENT )

        # Render a stock "NEW" icon to display on the pages
        image = self.render_icon( gtk.STOCK_NEW, gtk.ICON_SIZE_DIALOG )

        # ====================
        # Choose template page
        # ====================

        page = gtk.VBox()
        page.set_border_width(12)
        page.set_spacing(6)
        label = gtk.Label(_("<b>Choose project template</b>"))
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        page.pack_start(label, False, False);

        align = gtk.Alignment(0, 0, 1, 1)
        page.pack_start(align, True, True)
        align.set_padding(12,12,12,12)
        options = gtk.VBox()
        align.add(options)
        options.set_spacing(6)
        self.blankradio = gtk.RadioButton(label=_("Blank"))
        self.templradio = gtk.RadioButton(group=self.blankradio,
                                          label=_("From template:"))
        options.pack_start(self.blankradio, False, False)
        options.pack_start(self.templradio, False, False)

        self.templatelist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        templates = list_templates()
        for template in templates:
            self.templatelist.append( template )

        if len(templates) == 0:
            self.templradio.set_sensitive(False)
            self.templatelist.append( ['', _("(No templates found)"),''] )

        textrenderer = gtk.CellRendererText()
        textcol = gtk.TreeViewColumn(None, textrenderer, text=1)

        self.templateview = gtk.TreeView(self.templatelist)
        self.templateview.append_column(textcol)
        self.templateview.set_headers_visible(False)
        self.templateview.set_sensitive(False)

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        scrollwin.set_shadow_type(gtk.SHADOW_IN)
        scrollwin.add(self.templateview)

        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(0, 0, 18, 0)
        align.add(scrollwin)
        options.pack_start(align, True, True)

        self.description = gtk.Label()

        self.description.set_line_wrap(True)
        self.description.set_alignment(0, 0)
        self.description.set_padding(18, 0)
        self.description.set_selectable(True)
        self.description.set_max_width_chars(0)
        options.pack_start(self.description, False, False)

        self.append_page(page)
        self.set_page_title(page, _("Create new project"))

        self.set_page_side_image(page,image)

        self.set_page_type(page, gtk.ASSISTANT_PAGE_CONTENT)
        self.set_page_complete(page, True)
        self.template_page = page

        self.blankradio.connect('toggled', self.template_radio_toggled)
        self.templradio.connect('toggled', self.template_radio_toggled)

        treeselection = self.templateview.get_selection()
        treeselection.connect('changed', self.template_selection_changed)

        # ============================
        # Choose project filename page
        # ============================

        page = gtk.VBox()
        page.set_border_width(12)
        page.set_spacing(6)
        label = gtk.Label(_("<b>Choose project filename</b>"))
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        page.pack_start(label, False, False);

        align = gtk.Alignment(0, 0, 1, 1)
        page.pack_start(align, True, True)
        align.set_padding(12,12,12,12)

        options = gtk.VBox()
        align.add(options)

        table = gtk.Table(2,2)
        table.set_col_spacings( 6 ) # TODO: Remove magic numbers
        table.set_row_spacings( 6 ) # TODO: Remove magic numbers
        label = gtk.Label(_("Project name:"))
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0)
        self.filename = gtk.Entry()
        table.attach(self.filename, 1, 2, 0, 1, gtk.EXPAND | gtk.FILL, 0)
        label = gtk.Label(_("Location:"))
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0)
        self.filebutton = gtk.FileChooserButton(_('Select project location...'))
        #self.filebutton.connect( "selection-changed", self.event_filebutton_selection_changed )
        self.filebutton.set_local_only(True)
        self.filebutton.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        table.attach(self.filebutton, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0)

        options.pack_start(table, False, False)

        self.append_page(page)
        self.set_page_title(page, _("Create new project"))
        self.set_page_side_image(page,image)
        self.set_page_type(page, gtk.ASSISTANT_PAGE_CONTENT)
        self.set_page_complete(page, False)
        self.filename_page = page

        def filename_changed_cb( filename_entry ):
            entrytext = self.filename.get_text()
            self.set_page_complete(self.filename_page, (not entrytext == ""))

        self.filename.connect('changed', filename_changed_cb)

        # ================
        # Creation summary
        # ================

        page = gtk.VBox()
        page.set_border_width(12)
        page.set_spacing(6)
        label = gtk.Label(_("<b>Project summary</b>"))
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        page.pack_start(label, False, False);

        align = gtk.Alignment(0, 0, 1, 1)
        page.pack_start(align, True, True)
        align.set_padding(12,12,12,12)

        explanation = gtk.VBox()
        align.add(explanation)

        self.newfiles_frame = gtk.Frame(_("<b>New files to be created:</b>"))
        self.newfiles_frame.get_label_widget().set_use_markup(True)
        self.newfiles_frame.set_shadow_type(gtk.SHADOW_NONE)
        explanation.pack_start(self.newfiles_frame, False, False)

        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(0,12,12,12)
        self.newfiles_frame.add(align)

        self.newfiles_list = gtk.Label()
        self.newfiles_list.set_alignment(0, 0.5)
        self.newfiles_list.set_padding(0,12)
        align.add(self.newfiles_list)

        self.overwrite_frame = gtk.Frame(_("<b>The following files would be overwritten:</b>"))
        self.overwrite_frame.get_label_widget().set_use_markup(True)
        self.overwrite_frame.set_shadow_type(gtk.SHADOW_NONE)
        explanation.pack_start(self.overwrite_frame, False, False)

        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(0,12,12,12)
        self.overwrite_frame.add(align)

        vbox = gtk.VBox()
        align.add(vbox)

        self.overwrite_list = gtk.Label()
        self.overwrite_list.set_alignment(0, 0.5)
        self.overwrite_list.set_padding(0,12)
        vbox.pack_start(self.overwrite_list, False, False)

        self.confirm_overwrite = gtk.CheckButton(_("Confirm overwrite"))
        vbox.pack_start(self.confirm_overwrite, False, False)

        def confirm_overwrite_toggled_cb( togglebutton ):
            confirmed = togglebutton.get_active()
            self.set_page_complete(self.summary_page, confirmed)

        self.confirm_overwrite.connect( 'toggled', confirm_overwrite_toggled_cb )

        self.append_page(page)
        self.set_page_title(page, _("Create new project"))
        self.set_page_side_image(page,image)
        self.set_page_type(page, gtk.ASSISTANT_PAGE_CONFIRM)
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
                    self.newfiles_frame.hide_all()
                else:
                    self.newfiles_frame.show_all()

                no_overwrite = (overwrite_list == [])
                if no_overwrite:
                    # No files will be overwritten, we are done
                    self.overwrite_frame.hide_all()
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


gobject.type_register( NewProjectAssistant )
