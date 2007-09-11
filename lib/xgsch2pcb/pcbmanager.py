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

# TODO: Is this needed? What version of python do we depend on?
from __future__ import generators

import commands, shutil, re, gobject, os, sys, time
import dbus, dbus.glib, dbus.service

# i18n
import gettext
t = gettext.translation('xgsch2pcb', fallback=True)
_ = t.ugettext

# xgsch2pcb-specific modules
from stat import *
from subprocess import *
from funcs import *

# Define PCB action return codes
PCB_RC_OK      = 0

class PCBManager( gobject.GObject ):

    __gsignals__ = { "update-complete" :
                      ( 0,                        # No special flags
                        gobject.TYPE_NONE,        # Return type
                        (gobject.TYPE_BOOLEAN, )  # Pass a bool to signal
                       ) }
    
    def __init__(self, project):
        gobject.GObject.__init__(self)

        self.project = project
       
        # TODO: Need to think about whether these are relative or absolute paths
        self.project_dir = self.project.filename.rsplit('.', 1)[0]
        self.output_name = self.project.output_name

        self.pcb = None
        self.pcb_obj = None
        self.pcb_iface = None
        self.pcb_actions_iface = None
        
        self.cofunc = None
        
        self.toolpath = find_tool_path( 'pcb' )
        self.gsch2pcbpath = find_tool_path( 'gsch2pcb' )

        if not (self.toolpath and self.gsch2pcbpath):
            exception_txt = ''
            if not self.toolpath:
                exception_txt = exception_txt + \
                    _("\nCouldn't find 'pcb' executable")
            if not self.gsch2pcbpath:
                exception_txt = exception_txt + \
                    _("\nCouldn't find 'gsch2pcb' executable")
            raise Exception, exception_txt

        # Setup the D-Bus connection
        # TODO: Graceful error handling
        self.session_bus = dbus.SessionBus()
        self.dbus_obj = self.session_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        self.dbus_iface = dbus.Interface(self.dbus_obj, 'org.freedesktop.DBus')
        
        self.empty_char_array = dbus.Array( '', signature="s" )

    def close_layout(self):
        # TODO: Fixme
        self.pcb_actions_iface.ExecAction( "Quit", self.empty_char_array )

    def open_layout(self):
        if self.is_layout_open():
            # TODO: Is there some clever way to bring PCB to front?
            # Possibly send it an action which does a window-manager request?
            return
        Popen([self.toolpath, self.output_name + ".pcb"])
        while not self.is_layout_open():
            time.sleep( 0.1 )
        assert self.is_layout_open()


    def is_layout_open(self):
       
        try:
            pcb_instances = self.dbus_iface.ListQueuedOwners('org.seul.geda.pcb')
        except:
            print "is_layout_open(): DEBUG: Couldn't find any PCB instances"
            return False
        
        found_our_file = False
        
        for pcb in pcb_instances:
            print 'is_layout_open(): DEBUG: Found PCB instance at unique name ' + pcb

            pcb_obj = self.session_bus.get_object(pcb, '/org/seul/geda/pcb')
            pcb_iface = dbus.Interface(pcb_obj, 'org.seul.geda.pcb')

            ohdear = False            
            try:
                filename = pcb_iface.GetFilename()
            except:
                print 'is_layout_open(): DEBUG Exception calling pcb_iface.GetFilename()'
                ohdear = True

            if not ohdear:
                print 'is_layout_open(): DEBUG: Filename is ' + filename
    
                if filename == os.path.abspath( self.output_name ) + ".pcb":
                    found_our_file = True
                    continue
        
        if not found_our_file: 
            return False
            
        pcb_actions_iface = dbus.Interface(pcb_obj, 'org.seul.geda.pcb.actions')

        # TODO: FIXME: Seems unclean to update these here
        self.pcb = pcb
        self.pcb_obj = pcb_obj
        self.pcb_iface = pcb_iface
        self.pcb_actions_iface = pcb_actions_iface

        # TODO: Check to see if the layout is actually open, not just pipe alive?
        return True

 
    def needs_updating(self, schematics):
        
        # In the future, this could save the users currently active layout
        # and then check if it is complete (via gsch2pcb), thus not relying
        # on mtime.
        
        # If the PCB layout file doesn't exist, assume that it needs updating
        if not os.path.exists(self.output_name + ".pcb"):
            if len( schematics ) > 0:
                return True
            else:
                return False
        
        layout_mtime = os.stat(self.output_name + ".pcb")[ST_MTIME]

        schematic_mtime = layout_mtime
        for page in schematics:
            mtime = os.stat(page)[ST_MTIME]
            schematic_mtime = max(mtime, schematic_mtime)

        return (layout_mtime < schematic_mtime)


    def update_layout( self, schematics ):
        
        def error_restore_backup():
            # Deliberatly leave (self.output_name + ".savedbackup.pcb") incase it is useful
            
            # Move original file backup to layout if it exists
            if os.path.exists(self.output_name + ".backup.pcb"):
                shutil.move(self.output_name + ".backup.pcb", self.output_name + ".pcb")

        def cleanup_files():

            # Move backup back to layout file if it exists
            try:
                shutil.move(self.output_name + ".backup.pcb", self.output_name + ".pcb")
            except:
                pass
            
            # Remove backup before gsch2pcb
            try:
                os.remove(self.output_name + ".savedbackup.pcb")
            except:
                pass
                
            # Clean up gsch2pcb's mess
            try:
                os.remove(self.output_name + ".tmp.gsch2pcb")
            except:
                pass

            try:
                os.remove(self.output_name + ".new.pcb")
            except:
                pass

            try:
                os.remove(self.output_name + ".cmd")
            except:
                pass


        # First check the layout is open
        if not self.is_layout_open():
            self.open_layout()

        print _("********START UPDATING********")
        
        # TODO: TELL PCB TO IGNORE USER ACTIONS

        # Move current layout to backup if it exists
        if os.path.exists(self.output_name + ".pcb"):
            shutil.move(self.output_name + ".pcb", self.output_name + ".backup.pcb")
        
        # Save layout
        if self.pcb_actions_iface.ExecAction( "SaveTo", [ "Layout", self.output_name + ".pcb" ] ):
            error_restore_backup()
            # TODO: TELL PCB TO ALLOW USER ACTIONS
            # TODO: ERROR MESSAGE TO USER
            return

        # Copy saved layout to backup
        shutil.copy(self.output_name + ".pcb", self.output_name + ".savedbackup.pcb")
        
        # Create gsch2pcb project file
        self.project.save( self.output_name + ".tmp.gsch2pcb" )
        
        # Run gsch2pcb
        # TODO: Handle via Popen like other tools?
        gsch2pcb_cmd = self.gsch2pcbpath + ' -q "' + self.output_name + '.tmp.gsch2pcb"'
        gsch2pcb_output = commands.getstatusoutput(gsch2pcb_cmd)
        lines = gsch2pcb_output[1].splitlines()
        for line in lines:
            print "<gsch2pcb>:", line

        # TODO: HANDLE ERROR OUTPUT FROM gsch2pcb!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        
        # Load layout
        if self.pcb_actions_iface.ExecAction("LoadFrom", [ "Revert", self.output_name + ".pcb" ]):
            error_restore_backup()
            # TODO: TELL PCB TO ALLOW USER ACTIONS
            # TODO: ERROR MESSAGE TO USER
            return
        
        # Delete rats
        if self.pcb_actions_iface.ExecAction("DeleteRats", ["AllRats"]):
            # TODO: WARNING TO USER?
            pass
        
        # Load netlist
        if self.pcb_actions_iface.ExecAction("LoadFrom", ["Netlist", self.output_name + ".net"]):
            # TODO: WARNING TO THE USER?
            pass
        
        # If new elements exist, put them in the paste-buffer
        newparts = self.output_name + ".new.pcb"
        if os.path.exists (newparts):
            if self.pcb_actions_iface.ExecAction("LoadFrom", ["LayoutToBuffer", newparts]):
                # TODO: WARN USER?
                pass
       
            # Paste the new components near the origin
            if self.pcb_actions_iface.ExecAction("PasteBuffer", ["ToLayout","10","10","mil"]):
                # TODO: WARN USER?
                pass
            
            # Change back to the "none" (select) tool
            if self.pcb_actions_iface.ExecAction("Mode", ["None"]):
                # TODO: WARN USER?
                pass
        
        # Run the .cmd file
        if self.pcb_actions_iface.ExecAction("ExecuteFile", [self.output_name + ".cmd"]):
            # TODO: WARN USER?
            pass
            
        # Add the rat-lines
        if self.pcb_actions_iface.ExecAction("AddRats", ["AllRats"]):
            # TODO: WARN USER?
            pass
        
        # Move original layout backup back in place, delete intermediate files
        cleanup_files()

        print _("********DONE UPDATING********")
            

gobject.type_register( PCBManager )

