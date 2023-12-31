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

from gi.repository import GObject
import subprocess, shutil, re, os, sys, time, stat
import dbus

import config, funcs

# i18n
import gettext
t = gettext.translation(config.PACKAGE, config.localedir, fallback=True)
_ = t.gettext

class PCBManager( GObject.GObject ):

    __gsignals__ = { "update-complete" :
                      ( 0,                        # No special flags
                        GObject.TYPE_NONE,        # Return type
                        (GObject.TYPE_BOOLEAN, )  # Pass a bool to signal
                       ) }
    
    def __init__(self, project):
        super().__init__()

        self.project = project
       
        # TODO: Need to think about whether these are relative or absolute paths
        self.project_dir = self.project.filename.rsplit('.', 1)[0]
        self.output_name = self.project.output_name

        self.pcb = None
        self.pcb_obj = None
        self.pcb_iface = None
        self.pcb_actions_iface = None
        
        self.cofunc = None
        
        self.toolpath = funcs.find_tool_path( 'pcb' )
        self.gsch2pcbpath = funcs.find_tool_path( 'gsch2pcb' )

        if not (self.toolpath and self.gsch2pcbpath):
            exception_txt = ''
            if not self.toolpath:
                exception_txt = exception_txt + \
                    _("\nCouldn't find 'pcb' executable")
            if not self.gsch2pcbpath:
                exception_txt = exception_txt + \
                    _("\nCouldn't find 'gsch2pcb' executable")
            raise Exception(exception_txt)

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
        subprocess.Popen([self.toolpath, os.path.abspath( self.output_name + ".pcb" )])
        while not self.is_layout_open():
            time.sleep( 0.1 )
        assert self.is_layout_open()


    def is_layout_open(self):
       
        try:
            pcb_instances = self.dbus_iface.ListQueuedOwners('org.seul.geda.pcb')
        except:
            #print "is_layout_open(): DEBUG: Couldn't find any PCB instances"
            return False
        
        found_our_file = False
        
        for pcb in pcb_instances:
            #print 'is_layout_open(): DEBUG: Found PCB instance at unique name ' + pcb

            pcb_obj = self.session_bus.get_object(pcb, '/org/seul/geda/pcb')
            pcb_iface = dbus.Interface(pcb_obj, 'org.seul.geda.pcb')

            ohdear = False            
            try:
                filename = pcb_iface.GetFilename()
            except:
                print('is_layout_open(): DEBUG Exception calling pcb_iface.GetFilename()')
                ohdear = True

            if not ohdear:
                #print 'is_layout_open(): DEBUG: Filename is ' + filename
    
                if filename == os.path.abspath( self.output_name ) + ".pcb":
                    found_our_file = True
                    break
        
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
        
        layout_mtime = os.stat(self.output_name + ".pcb")[stat.ST_MTIME]

        schematic_mtime = layout_mtime
        for page in schematics:
            mtime = os.stat(page)[stat.ST_MTIME]
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

        print(_("********START UPDATING********"))
        
        # TODO: TELL PCB TO IGNORE USER ACTIONS

        # Move current layout to backup if it exists
        if os.path.exists(self.output_name + ".pcb"):
            shutil.move(self.output_name + ".pcb", self.output_name + ".backup.pcb")
        
        # Save layout
        if self.pcb_actions_iface.ExecAction( "SaveTo", [ "Layout", self.output_name + ".pcb" ] ):
            error_restore_backup()
            # TODO: TELL PCB TO ALLOW USER ACTIONS
            # TODO: ERROR MESSAGE TO USER
            return []

        # Copy saved layout to backup
        shutil.copy(self.output_name + ".pcb", self.output_name + ".savedbackup.pcb")
        
        # Create gsch2pcb project file
        self.project.save( self.output_name + ".tmp.gsch2pcb" )
        
        # Run gsch2pcb
        gsch2pcb_cmd = [self.gsch2pcbpath, '-q', self.output_name + '.tmp.gsch2pcb']
        gsch2pcb_output = subprocess.Popen(gsch2pcb_cmd, stdout=subprocess.PIPE)
        gsch2pcb_stdout, gsch2pcb_stderr = gsch2pcb_output.communicate()
        lines = gsch2pcb_stdout.splitlines()
        unfound = []
        gsch2pcb_backup = None
        for line in lines:
            print("<gsch2pcb>:", line)

            search = b' is backed up as '
            found_idx = line.find( search )
            if found_idx >= 0:
                # The last character is a ".", so don't return that.
                gsch2pcb_backup = line[ found_idx + len(search) : len(line) -1 ]

            search = b': can\'t find PCB element for footprint '
            found_idx = line.find( search )
            if found_idx >= 0:
                refdes = line[ 0 : found_idx ]
                end_fp_idx = line.find( b" (value=", found_idx )
                footprint = line[ found_idx + len( search ) : end_fp_idx ]
                unfound.append( [ refdes, footprint ] )

        # TODO: Report to the user the backup filename made by xgsch2pcb (or us?)
        #       if they don't like the changes.

        # TODO: HANDLE ERROR OUTPUT FROM gsch2pcb!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # Load new layout (if gsch2pcb modified it)
        # otherwise, don't force the revert as it destroys the users UNDO history
        if gsch2pcb_backup:
            if self.pcb_actions_iface.ExecAction("LoadFrom", [ "Revert", self.output_name + ".pcb" ]):
                error_restore_backup()
                # TODO: TELL PCB TO ALLOW USER ACTIONS
                # TODO: ERROR MESSAGE TO USER
                return []

        # Delete rats
        if self.pcb_actions_iface.ExecAction("DeleteRats", ["AllRats"]):
            # TODO: WARNING TO USER?
            pass

        # Load netlist
        if self.pcb_actions_iface.ExecAction("LoadFrom", ["Netlist", self.output_name + ".net"]):
            # TODO: WARNING TO THE USER?
            pass

        # If new elements exist, put them in the paste-buffer
        # FIXME: This overwrites the pastebuffer... hopefully the user didn't have anything useful in there!
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

        print(_("********DONE UPDATING********"))
        return unfound

GObject.type_register( PCBManager )

