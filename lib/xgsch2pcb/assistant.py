# -*-Python-*-

# xgsch2pcb - a GUI for gsch2pcb
# Copyright (C) 2007 Peter Clifton <pcjc2@cam.ac.uk>
#
# Emulate a GtkAssistant (available in GTK+2.10 onwards using <= GTK+2.8
# Based in part on the GtkAssistant implementation in GTK+2.10
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

import gtk, gtk.gdk, pango, gobject

import gettext
t = gettext.translation('xgsch2pcb', fallback=True)
_ = t.ugettext


ASSISTANT_PAGE_CONTENT  = 0
ASSISTANT_PAGE_INTRO    = 1
ASSISTANT_PAGE_CONFIRM  = 2
ASSISTANT_PAGE_SUMMARY  = 3
ASSISTANT_PAGE_PROGRESS = 4


class AssistantPage(object):

    def __init__(self):
        self.page = None
        self.type = ASSISTANT_PAGE_CONTENT
        self.complete = False
        self.title = None
        self.header_image = None
        self.sidebar_image = None
        self.notebook_no = 0

class Assistant(gtk.Window):


    __gsignals__ = { 'apply'   : ( gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   ( )),
                     'cancel'  : ( gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   ( ) ),
                     'close'   : ( gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   ( )),
                     'prepare' : ( gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   (gobject.TYPE_OBJECT, )),
                   }

    def __init__(self):
        gtk.Window.__init__(self)

        self.parent_window = None
        self.cancel  = gtk.Button( stock = gtk.STOCK_CANCEL )
        self.forward = gtk.Button( stock = gtk.STOCK_GO_FORWARD )
        self.back    = gtk.Button( stock = gtk.STOCK_GO_BACK )
        self.apply   = gtk.Button( stock = gtk.STOCK_APPLY )
        self.close   = gtk.Button( stock = gtk.STOCK_CLOSE )
        #self.last    = gtk.Button( stock = gtk.STOCK_GOTO_LAST )

        self.cancel.set_no_show_all(True)
        self.forward.set_no_show_all(True)
        self.back.set_no_show_all(True)
        self.apply.set_no_show_all(True)
        self.close.set_no_show_all(True)
        #self.last.set_no_show_all(True)

        self.pages = []
        self.current_page = None
        self.visited_pages = []

        vbox = gtk.VBox()
        vbox.set_spacing( 12 )

        self.notebook = gtk.Notebook()
        self.notebook.set_show_tabs(False)
        vbox.pack_start( self.notebook, True, True)

        self.buttonbox = gtk.HButtonBox()
        self.buttonbox.set_layout( gtk.BUTTONBOX_END )
        self.buttonbox.set_spacing( 6 )
        self.buttonbox.add( self.cancel )
        self.buttonbox.add( self.back )
        self.buttonbox.add( self.forward )
        #self.buttonbox.add( self.last )
        self.buttonbox.add( self.apply )
        self.buttonbox.add( self.close )
        vbox.pack_start( self.buttonbox, False, False)

        self.add( vbox )

        self.set_button_state()

        def cancel_clicked_cb(button):
            self.emit( 'cancel' )

        def forward_clicked_cb(button):
            if self.current_page:
                self.visited_pages.append( self.current_page )
            index = self.find_page_info_index( self.current_page )
            self.set_page( self.pages[ index + 1 ] )

        def back_clicked_cb(button):
            # skip progress pages when going back
            index = len(self.visited_pages) - 1
            page_info = self.visited_pages[index]
            while (page_info.type == ASSISTANT_PAGE_PROGRESS or
                   not page_info.page.flags() | gtk.VISIBLE):
                del self.visited_pages[index]
                index = index - 1
                page_info = self.visited_pages[index]
            del self.visited_pages[index]
            self.set_page( page_info )

        def apply_clicked_cb(button):
            self.emit( 'apply' )
            self.destroy()

        def close_clicked_cb(button):
            self.emit( 'close' )
            self.destroy()

        #def last_clicked_cb(self, button):
        #    print "LAST"

        self.cancel.connect( 'clicked', cancel_clicked_cb )
        self.forward.connect( 'clicked', forward_clicked_cb )
        self.back.connect( 'clicked', back_clicked_cb )
        self.apply.connect( 'clicked', apply_clicked_cb )
        self.close.connect( 'clicked', close_clicked_cb )
        #self.last.connect( 'clicked', last_clicked_cb )

    def set_button_state(self):
        if not self.current_page:
            self.cancel.set_sensitive(True)
            self.forward.set_sensitive(False)
            self.cancel.show()
            self.forward.show()
            self.back.hide()
            self.apply.hide()
            self.close.hide()
            #self.last.hide()
        elif self.current_page.type == ASSISTANT_PAGE_INTRO:
            self.cancel.set_sensitive(True)
            self.forward.set_sensitive(self.current_page.complete)
            self.cancel.show()
            self.forward.show()
            self.back.hide()
            self.apply.hide()
            self.close.hide()
            #self.compute_last_button_state()
        elif self.current_page.type == ASSISTANT_PAGE_CONFIRM:
            self.cancel.set_sensitive(True)
            self.back.set_sensitive(True)
            self.apply.set_sensitive(self.current_page.complete)
            self.cancel.show()
            self.back.show()
            self.apply.show()
            self.forward.hide()
            self.close.hide()
            #self.last.hide()
        elif self.current_page.type == ASSISTANT_PAGE_CONTENT:
            self.cancel.set_sensitive(True)
            self.back.set_sensitive(True);
            self.forward.set_sensitive(self.current_page.complete)
            self.cancel.show()
            self.back.show()
            self.forward.show()
            self.apply.hide()
            self.close.hide()
            #self.compute_last_button_state()
        elif self.current_page.type == ASSISTANT_PAGE_SUMMARY:
            self.close.set_sensitive(True)
            self.close.show()
            self.cancel.hide()
            self.back.hide()
            self.forward.hide()
            self.apply.hide()
            #self.last.hide()
        elif self.current_page.type == ASSISTANT_PAGE_PROGRESS:
            self.cancel.set_sensitive(self.current_page.complete)
            self.back.set_sensitive(self.current_page.complete)
            self.forward.set_sensitive(self.current_page.complete)
            cancel.show()
            self.back.show()
            self.forward.show()
            self.apply.hide()
            self.close.hide()
            #self.last.hide()

        if not self.visited_pages:
            self.back.hide()

    def find_page_info_index(self, page_info):
        return self.pages.index( page_info )

    def find_page_info(self, page):
        for page_info in self.pages:
            if page_info.page is page:
                return page_info
        return None

    def set_page_colors(self, title, eb_title, eb_side):
        title.ensure_style()
        style = title.get_style()
        title.modify_bg(gtk.STATE_NORMAL, style.bg[gtk.STATE_SELECTED])
        title.modify_fg(gtk.STATE_NORMAL, style.fg[gtk.STATE_SELECTED])
        eb_title.modify_bg(gtk.STATE_NORMAL, style.bg[gtk.STATE_SELECTED])
        eb_side.modify_bg(gtk.STATE_NORMAL, style.bg[gtk.STATE_SELECTED])

    def set_title_font(self, title):
        desc = pango.FontDescription()
        size = self.style.font_desc.get_size()
        desc.set_weight( pango.WEIGHT_ULTRABOLD )
        desc.set_size( int(size * pango.SCALE_XX_LARGE) )
        title.modify_font( desc )

    def append_page(self, page):
        page_info = AssistantPage()
        page_info.page = page
        page_info.title = gtk.Label()
        page_info.title.set_alignment(0, 0.5)
        page_info.title.set_padding(6, 10)
        page_info.sidebar_image = gtk.Image()
        self.pages.append( page_info )

        table = gtk.Table(2,2)
        page_info.notebook_no = self.notebook.append_page( table )

        # Event box hack so we can change its background
        eb_title = gtk.EventBox()
        eb_title.add( page_info.title )

        al_side = gtk.Alignment()
        al_side.add( page_info.sidebar_image )

        # Event box hack so we can change its background
        eb_side = gtk.EventBox()
        eb_side.add( al_side )

        table.attach(eb_title, 0, 2, 0, 1, gtk.EXPAND|gtk.FILL, 0)
        table.attach(eb_side, 0, 1, 1, 2, 0, gtk.EXPAND|gtk.FILL)
        table.attach(page_info.page, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL)

        self.set_page_colors( page_info.title, eb_title, eb_side )
        self.set_title_font( page_info.title)
        page_info.title.show()

        if not self.current_page:
            self.set_page( page_info )

    def set_page(self, page_info):
        self.emit( 'prepare', page_info.page )
        self.current_page = page_info
        self.set_button_state()
        self.notebook.set_current_page( page_info.notebook_no )

    def set_page_type(self, page, type):
        page_info = self.find_page_info( page )
        page_info.type = type

    def set_page_title(self, page, title):
        page_info = self.find_page_info( page )
        page_info.title.set_text( title )

    def set_page_side_image(self, page, pixbuf=None):
        page_info = self.find_page_info( page )
        page_info.sidebar_image.set_from_pixbuf( pixbuf )

    def set_page_complete(self, page, complete):
        page_info = self.find_page_info( page )
        page_info.complete = complete
        self.set_button_state()

    # Unused gtk.Assistant API we won't reimplement
    """
    def get_current_page()
    def set_current_page(page_num)
    def get_n_pages()
    def get_nth_page(page_num)
    def prepend_page(page)
    def insert_page(page, position)
    def set_forward_page_func(page_func, data)
    def get_page_type(page)
    def get_page_title(page)
    def set_page_header_image(page, pixbuf=None)
    def get_page_header_image(page)
    def get_page_side_image(page)
    def get_page_complete(page)
    def add_action_widget(child)
    def remove_action_widget(child)
    def update_buttons_state()
    """

gobject.type_register( Assistant )
