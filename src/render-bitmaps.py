#!/usr/bin/python3
#
# Legal Stuff:
#
# This file is part of the Moka Icon Theme and is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free Software
# Foundation; version 3.
#
# This file is part of the Moka Icon Theme and is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <https://www.gnu.org/licenses/lgpl-3.0.txt>
#
#
# Thanks to the GNOME icon developers for the original version of this script
import os
import sys
import xml.sax
import subprocess
import argparse

INKSCAPE = '/usr/bin/inkscape'
OPTIPNG = '/usr/bin/optipng'
MAINDIR = '../usr/share/icons/Mint-C'
SOURCES = ['actions', 'apps', 'categories', 'devices', 'mimetypes', 'status']

# the resolution that non-hi-dpi icons are rendered at (may be 90 or 96 depending on your inkscape build)
inkscape_version = str(subprocess.check_output(['inkscape', '-V'])).split(' ')[1].split('.')
inkscape_version = float(inkscape_version[0] + '.' + inkscape_version[1])
if inkscape_version < 0.92: # inkscape version 0.92 changed the default dpi from 90 to 96
    DPI_1_TO_1 = 90
else:
    DPI_1_TO_1 = 96
# DPI multipliers to render at
DPIS = [1, 2] # for hidpi icons change to [1, 2] (not yet supported in Mint-Y)

def main(args, SRC):

    def optimize_png(png_file):
        if os.path.exists(OPTIPNG):
            process = subprocess.Popen([OPTIPNG, '-quiet', '-o7', png_file])
            process.wait()

    def inkscape_render_rect(icon_file, rect, dpi, output_file):
        process = subprocess.Popen([INKSCAPE, '--batch-process', '--export-dpi', str(dpi),
               '-i', rect,
               '-o', output_file, icon_file])
        process.wait()
        optimize_png(output_file)

    class ContentHandler(xml.sax.ContentHandler):
        ROOT = 0
        SVG = 1
        LAYER = 2
        OTHER = 3
        TEXT = 4
        def __init__(self, path, file_name, force=False, filter=None):
            self.stack = [self.ROOT]
            self.inside = [self.ROOT]
            self.path = path
            self.rects = []
            self.state = self.ROOT
            self.chars = ""
            self.force = force
            self.filter = filter
            self.file_name = file_name

        def endDocument(self):
            pass

        def startElement(self, name, attrs):
            if self.inside[-1] == self.ROOT:
                if name == "svg":
                    self.stack.append(self.SVG)
                    self.inside.append(self.SVG)
                    return
            elif self.inside[-1] == self.SVG:
                for attr in attrs.values():
                    if attr == 'Baseplate':
                        self.stack.append(self.LAYER)
                        self.inside.append(self.LAYER)
                        self.context = None
                        self.icon_name = None
                        self.rects = []
                        return
            elif self.inside[-1] == self.LAYER:
                for attr in attrs.values():
                    if attr == "context":
                        self.stack.append(self.TEXT)
                        self.inside.append(self.TEXT)
                        self.text='context'
                        self.chars = ""
                        return
                    if attr == "icon-name":
                        self.stack.append(self.TEXT)
                        self.inside.append(self.TEXT)
                        self.text='icon-name'
                        self.chars = ""
                        return
                    if name == "rect":
                        self.rects.append(attrs)

            self.stack.append(self.OTHER)


        def endElement(self, name):
            stacked = self.stack.pop()
            if self.inside[-1] == stacked:
                self.inside.pop()

            if stacked == self.TEXT and self.text is not None:
                assert self.text in ['context', 'icon-name']
                if self.text == 'context':
                    self.context = self.chars
                elif self.text == 'icon-name':
                    self.icon_name = self.chars
                self.text = None
            elif stacked == self.LAYER:
                assert self.icon_name
                assert self.context

                if self.filter is not None and not self.icon_name in self.filter:
                    return

                if (self.icon_name != self.file_name):
                    print(f"icon name in {self.file_name} is wrong: {self.icon_name}")
                    sys.exit(1)
                for rect in self.rects:
                    for dpi_factor in DPIS:
                        width = rect['width']
                        height = rect['height']
                        id = rect['id']
                        dpi = DPI_1_TO_1 * dpi_factor

                        size_str = "%s" % (width)
                        if dpi_factor != 1:
                            size_str += "@%sx" % dpi_factor

                        dir = os.path.join(MAINDIR, self.context, size_str)
                        outfile = os.path.join(dir, self.icon_name+'.png')
                        if not os.path.exists(dir):
                            os.makedirs(dir)
                        # Do a time based check!
                        if self.force or not os.path.exists(outfile):
                            print (self.context, self.icon_name, self.file_name)
                            inkscape_render_rect(self.path, id, dpi, outfile)
                            #sys.stdout.write('.')
                        else:
                            stat_in = os.stat(self.path)
                            stat_out = os.stat(outfile)
                            if stat_in.st_mtime > stat_out.st_mtime:
                                print (self.context, self.icon_name, self.file_name)
                                inkscape_render_rect(self.path, id, dpi, outfile)
                                #sys.stdout.write('.')
                            #else:
                            #    sys.stdout.write('-')
                        sys.stdout.flush()
                #sys.stdout.write('\n')
                #sys.stdout.flush()

        def characters(self, chars):
            self.chars += chars.strip()


    if not args.svg:
        if not os.path.exists(MAINDIR):
            os.mkdir(MAINDIR)
        print ('')
        print ('Rendering from SVGs in', SRC)
        print ('')
        for file in sorted(os.listdir(SRC)):
            if file[-4:] == '.svg':
                path = os.path.join(SRC, file)
                icon_name = file.replace(".svg", "")
                handler = ContentHandler(path, icon_name)
                xml.sax.parse(open(path), handler)
        print ('')
    else:
        path = os.path.join(SRC, args.svg + '.svg')

        if os.path.exists(os.path.join(path)):
            icon_name = args.svg
            handler = ContentHandler(path, icon_name, True, filter=args.filter)
            xml.sax.parse(open(path), handler)
        else:
            # icon not in this directory, try the next one
            pass

parser = argparse.ArgumentParser(description='Render icons from SVG to PNG')

parser.add_argument('svg', type=str, nargs='?', metavar='SVG',
                    help="Optional SVG names (without extensions) to render. If not given, render all icons")
parser.add_argument('filter', type=str, nargs='?', metavar='FILTER',
                    help="Optional filter for the SVG file")

args = parser.parse_args()

for source in SOURCES:
    if os.path.exists(os.path.join('.', source)):
        SRC = os.path.join('.', source)
        main(args, SRC)
