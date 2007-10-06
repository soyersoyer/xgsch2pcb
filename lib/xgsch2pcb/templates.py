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

import os
import shutil

# xgsch2pcb-specific modules
import config
from gsch2pcbproject import Gsch2PCBProject

def template_path( template, file ):
    path = os.path.join( config.templatesdir, template )
    path = os.path.join( path, file )
    return path


def replace_project_name( file, project ):
    """
Produce the filename which would exist for a given project name.

This implementation simply replaces the first occurance of the string
'template' with the project name.

It should only be called with relative paths, otherwise any prefix directory
containing the string template (e.g. the templates directory!) would be
replaced instead of the desired portion of the file name.
    """
    return file.replace( 'template', project, 1 )


def list_templates():

    template_list = []

    try:
        filelist = os.listdir( config.templatesdir )
    except:
        print "Couldn't list templates directory"
        return template_list

    filelist.sort()

    for template in filelist:
        try:
            templ = gsch2pcb_template( template )
            [name, description] = templ.read_description()
            template_list.append( [template, name, description] )
        except:
            print "Couldn't read a template in dir " + template

    return template_list


class gsch2pcb_template:

    def __init__(self, template):
        self.template = template
        self.filename = template_path( template, 'template.gsch2pcb')

        # Load the project into memory
        self.template_project = Gsch2PCBProject( self.filename )

    def read_description(self):

        file = open( template_path( self.template, 'template.txt' ), 'r' )
        name = file.readline().strip()
        blank = file.readline()
        if blank != "\n":
            print "Invalid file format for this template"
            file.close()
        # Join remaining lines in the file to a single string
        description = "".join( file.readlines() )
        file.close()
        return [name, description]


    def would_create(self, projectname):
        """Returns a list of files which this templates would create"""
        # TODO: Should this be a relative or absolute path??

        filelist = []

        # Would create a new project file:
        # TODO: Should the template have this as a relative path to some dir?
        filelist.append( os.path.basename( self.template_project.filename ) )
        # Would create the output file:
        # TODO: REMOVE HARDCODED EXTENSION
        filelist.append( self.template_project.output_name + '.pcb' )
        # would create the pages:
        filelist.extend( self.template_project.pages )

        # Substitute the templatized filenames for ones matching the new project name
        new_filelist = []
        for file in filelist:
          new_filelist.append( replace_project_name( file, projectname ) )

        return new_filelist


    def apply(self, projectname):

        # Copy the output file
        output_name = self.template_project.output_name
        new_output_name = replace_project_name( output_name, projectname )
        output_file = output_name + '.pcb'         # TODO: REMOVE HARDCODED EXTENSION
        new_output_file = new_output_name + '.pcb' # TODO: REMOVE HARDCODED EXTENSION
        shutil.copy( template_path( self.template, output_file ), new_output_file )

        # Create a new gsch2pcb project in the new location, with the new output filename
        new_project = Gsch2PCBProject( None, new_output_name )

        # Copy schematic pages, and add to the new project
        for page_file in self.template_project.pages:
            new_page_file = replace_project_name( page_file, projectname )
            shutil.copy( template_path( self.template, page_file ), new_page_file )
            new_project.add_page( new_page_file )

        # TODO: We could just hand off the new project file without saving of course?
        # TODO: REMOVE HARDCODED EXTENSION
        new_project.save(projectname + '.gsch2pcb')

