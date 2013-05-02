#
# <license>
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# 
# 
# Copyright 2013 Sapphire Open Systems
#  
# </license>
#

import os
import shutil
import logging
import json
import multiprocessing
import subprocess
import shlex
import uuid
import crcmod
import struct
from datetime import datetime
import argparse
import uuid

from sapphire.core import settings

from intelhex import IntelHex

import global_settings

SETTINGS_DIR = os.path.dirname(os.path.abspath(global_settings.__file__))


def runcmd(cmd, tofile=False, tolog=True):
    logging.debug(cmd)

    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
     
    output = ''

    for line in p.stdout.readlines():
        output += line
    
    if output != '':
        if not tofile and tolog:
            logging.warn(output)

        elif tofile:
           f = open(tofile, 'w')
           f.write(output)
           f.close()

    p.wait()

    return output

class SettingsParseException(Exception):
    pass

class ProjectNotFoundException(Exception):
    pass

def get_builder(target_dir):
    builder = Builder(target_dir)
    
    modes = {"os": OSBuilder, "loader": LoaderBuilder, "app": AppBuilder, "lib": LibBuilder}

    return modes[builder.settings["BUILD_TYPE"]](target_dir)

class Builder(object):
    def __init__(self, target_dir):
        self.target_dir = target_dir
        
        self.settings = self.get_settings()

        self.proj_name = str(self.settings["PROJ_NAME"]) # convert from unicode
        self.fwid = self.settings["FWID"]

        try:
            self.includes = self.settings["LIBRARIES"]
        except:
            self.includes = list()

    def init_logging(self):
        try:
            os.remove(self.settings["LOG_FILENAME"])

        except:
            pass

        file_logger = logging.FileHandler(filename=self.settings["LOG_FILENAME"])
        file_logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s >>> %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        file_logger.setFormatter(formatter)
        logging.getLogger('').addHandler(file_logger)

    def get_settings(self):
        settings = self._get_default_settings()
        app_settings = self._get_local_settings()
        
        # override defaults with app settings
        for k, v in app_settings.iteritems():
            settings[k] = v
        
        return settings

    def _get_default_settings(self):
        try:
            return json.loads(open(os.path.join(SETTINGS_DIR, 'settings.json')).read())
        
        except ValueError:
            raise SettingsParseException

    def _get_local_settings(self):
        # load app settings file
        try:
            f = open(os.path.join(self.target_dir, "settings.json"))
        
        # file does not exist
        except IOError:
            return dict()
        
        try:
            # parse settings
            app_settings = json.loads(f.read())
        
        except ValueError:
            raise SettingsParseException

        return app_settings
    
    def list_source(self):
        source_files = []

        for f in os.listdir(self.target_dir):
             
            if f.endswith('.c'):
               source_files.append(os.path.join(self.target_dir, f))

        return source_files

    def get_buildnumber(self):
        try:
            f = open(os.path.join(self.target_dir, self.settings["BUILD_NUMBER_FILE"]), 'r')
            build_number = f.read()
            f.close()

        except IOError:
            f = open(os.path.join(self.target_dir, self.settings["BUILD_NUMBER_FILE"]), 'w')
            build_number = "0"
            f.write(build_number)
            f.close()
        
        return int(build_number)
    
    def set_buildnumber(self, value):
        f = open(os.path.join(self.target_dir, self.settings["BUILD_NUMBER_FILE"]), 'w')
        f.write("%d" % (value))
        f.close()

    buildnumber = property(get_buildnumber, set_buildnumber)

    def get_version(self):
        s = "%s.%04d" % (str(self.settings["PROJ_VERSION"]), self.buildnumber)
        return s
    
    version = property(get_version)

    def clean(self):
        logging.info('Cleaning %s' % (self.target_dir))
        
        for f in os.listdir(self.target_dir):
            for filetype in self.settings["CLEAN_FILES"]:
                if f.lower().endswith(filetype):
                    try:
                        os.remove(os.path.join(self.target_dir, f))    
                        
                        logging.info('> Removing %s' % (f))

                    except:
                        raise

            if f in self.settings["CLEAN_DIRS"]:
                try:    
                    shutil.rmtree(os.path.join(self.target_dir, f), True)
                    logging.info('> Removing %s' % (f))

                except:
                    raise
        
    def build(self):
        logging.info("Building %s" % (self.settings["PROJ_NAME"]))

        self.pre_process()
        self.compile()
        self.link()
        self.post_process()
        
        save_project_info(self.proj_name, self.target_dir)

    def pre_process(self):
        # inc build number
        self.buildnumber += 1

    def compile(self):
        logging.info("Compiling %s" % (self.proj_name))
        
        # save working dir
        cwd = os.getcwd()

        # change to target dir        
        os.chdir(self.target_dir)

        try:
            os.mkdir(self.settings["OBJ_DIR"])
            os.mkdir(self.settings["DEP_DIR"])

        except OSError:
            raise

        pool = multiprocessing.Pool()

        source_files = self.list_source()

        for source_file in source_files:
            # get dir and filename components
            source_path, source_fname = os.path.split(source_file)

            # build command string
            cmd = self.settings["CC"] + ' -c %s ' % (source_fname)
            
            for include in self.includes:
                include_dir = get_project_builder(include).target_dir

                cmd += '-I%s ' % (include_dir)

            for flag in self.settings["C_FLAGS"]:
                cmd += flag + ' '
                
            cmd += '%(DEP_DIR)/%(SOURCE_FNAME).o.d' + ' '
            cmd += '-o ' + '%(OBJ_DIR)/%(SOURCE_FNAME).o' + ' '
            
            cmd = cmd.replace('%(OBJ_DIR)', self.settings["OBJ_DIR"])
            cmd = cmd.replace('%(SOURCE_FNAME)', source_fname)
            cmd = cmd.replace('%(DEP_DIR)', self.settings["DEP_DIR"])
            
            # replace windows path separators with unix
            cmd = cmd.replace('\\', '/')

            pool.apply_async(runcmd, args = (cmd, ))

        pool.close()
        pool.join()

        # change back to working dir    
        os.chdir(cwd)

    def link(self):
        pass

    def post_process(self):
        pass


class LibBuilder(Builder):
    def __init__(self, *args, **kwargs):
        super(LibBuilder, self).__init__(*args, **kwargs)
        
        self.includes.append(self.settings["OS_PROJECT"])

    def link(self):
        logging.info("Linking %s" % (self.proj_name))
        
        # save working dir
        cwd = os.getcwd()

        # change to target dir        
        os.chdir(self.target_dir)

        # build command string
        cmd = self.settings["AR"] + ' '
       
        for flag in self.settings["AR_FLAGS"]:
            cmd += flag + ' '

        cmd += self.proj_name + '.a' + ' '
        
        obj_dir = self.settings["OBJ_DIR"]

        for source in self.list_source():
            source_path, source_fname = os.path.split(source)
            cmd += obj_dir + '/' + source_fname + '.o' + ' '
        
        # replace windows path separators with unix
        cmd = cmd.replace('\\', '/')

        runcmd(cmd)

        # change back to working dir    
        os.chdir(cwd)


class OSBuilder(LibBuilder):
    def __init__(self, *args, **kwargs):
        super(OSBuilder, self).__init__(*args, **kwargs)
 

class HexBuilder(Builder):
    def __init__(self, *args, **kwargs):
        super(HexBuilder, self).__init__(*args, **kwargs)
        
        self.includes.append(self.settings["OS_PROJECT"])

    def link(self):
        logging.info("Linking %s" % (self.proj_name))

        # build command string
        cmd = self.settings["CC"] + ' '
        
        for flag in self.settings["C_FLAGS"]:
            cmd += flag + ' '
            
        cmd += '%(DEP_DIR)/%(SOURCE_FNAME).o.d' + ' '
        
        # save working dir
        cwd = os.getcwd()

        # change to target dir        
        os.chdir(self.target_dir)

        obj_dir = self.settings["OBJ_DIR"]

        # source object files
        for source in self.list_source():
            source_path, source_fname = os.path.split(source)
            cmd += obj_dir + '/' + source_fname + '.o' + ' '
        
        # linker flags        
        for flag in self.settings["LINK_FLAGS"]:
            cmd += flag + ' '
        
        # included libraries
        for include in self.includes:
            include_dir = get_project_builder(include).target_dir

            cmd += '%s ' % (include_dir + '/' + include + '.a')

        cmd = cmd.replace('%(OBJ_DIR)', obj_dir)
        cmd = cmd.replace('%(DEP_DIR)', self.settings["DEP_DIR"])
        cmd = cmd.replace('%(SOURCE_FNAME)', self.proj_name)
        cmd = cmd.replace("%(LINKER_SCRIPT)", os.path.join(SETTINGS_DIR, "linker.x"))
        cmd = cmd.replace("%(APP_NAME)", self.settings["PROJ_NAME"])
        cmd = cmd.replace("%(TARGET_DIR)", self.target_dir)

        # replace windows path separators with unix
        cmd = cmd.replace('\\', '/')

        runcmd(cmd)

        logging.info("Generating output files")
        
        runcmd('avr-objcopy -O ihex -R .eeprom main.elf main.hex')
        runcmd('avr-size -C main.elf --mcu=atmega128rfa1')
        runcmd('avr-objdump -h -S -l main.elf', tofile='main.lss')
        runcmd('avr-nm -n main.elf', tofile='main.sym')
            
        # change back to working dir    
        os.chdir(cwd)


class AppBuilder(HexBuilder):
    def __init__(self, *args, **kwargs):
        super(AppBuilder, self).__init__(*args, **kwargs)

    def merge_hex(self, hex1, hex2, target):
        ih = IntelHex(hex1)
        ih.merge(IntelHex(hex2))

        ih.write_hex_file(target)

    def post_process(self):
        logging.info("Processing binaries")
        
        # save original dir
        cwd = os.getcwd()

        # change to target dir
        os.chdir(self.target_dir)

        ih = IntelHex('main.hex')
        
        fwid = uuid.UUID('{' + self.settings["FWID"] + '}')
        
        size = ih.maxaddr() - ih.minaddr() + 1
        
        # get os info
        os_project = get_project_builder(self.settings["OS_PROJECT"])

        # create firmware info structure
        fw_info = struct.pack('<I16s128s16s128s16s', 
                                size, 
                                fwid.bytes, 
                                os_project.proj_name, 
                                os_project.version, 
                                self.proj_name,
                                self.version)
        
        # insert fw info into hex
        ih.puts(0x120, fw_info)

        # compute crc
        crc_func = crcmod.predefined.mkCrcFun('crc-aug-ccitt')

        crc = crc_func(ih.tobinstr())

        logging.info("size: %d" % (size))
        logging.info("fwid: %s" % (fwid))
        logging.info("crc: 0x%x" % (crc))
        logging.info("os name: %s" % (os_project.proj_name))
        logging.info("os version: %s" % (os_project.version))
        logging.info("app name: %s" % (self.proj_name))
        logging.info("app version: %s" % (self.version))

        ih.puts(ih.maxaddr() + 1, struct.pack('>H', crc))

        ih.write_hex_file('main.hex')
        ih.tobinfile('firmware.bin')
        
        # get loader info
        loader_project = get_project_builder(self.settings["LOADER_PROJECT"])

        # create loader image
        loader_hex = os.path.join(loader_project.target_dir, "main.hex")
        self.merge_hex('main.hex', loader_hex, 'loader_image.hex')
        
        # change back to original dir
        os.chdir(cwd)


class LoaderBuilder(HexBuilder):
    def __init__(self, *args, **kwargs):
        super(LoaderBuilder, self).__init__(*args, **kwargs)


def get_project_info_dir():
    return settings.get_app_dir()

def get_project_info_file():
    return os.path.join(get_project_info_dir(), "projects.json")

def get_project_list():
    try:
        f = open(get_project_info_file(), 'r')
        data = f.read()
        f.close()
        
        return json.loads(data)
    
    except IOError:
        return dict()
        
    except ValueError:
        return dict()

def save_project_info(name, target_dir):
    data = get_project_list()
    data[name] = target_dir

    # getdata dir
    data_dir = get_project_info_dir()

    # check if data dir exists
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    f = open(get_project_info_file(), 'w')
    f.truncate(0)
    f.write(json.dumps(data, indent=4, separators=(',', ': ')))
    f.close()

    logging.info("Saving project listing to: %s" % (data_dir))

def get_project_builder(proj_name=None, fwid=None):
    projects = get_project_list()
    
    target_dir = None

    try:
        if proj_name:
            return Builder(projects[proj_name])

        elif fwid:
            for k, v in projects.iteritems():
                builder = get_project_builder(k)

                if builder.fwid == fwid:
                    return builder

    except:
        if proj_name:        
            raise ProjectNotFoundException(proj_name)
        else:
            raise ProjectNotFoundException(fwid)

    raise ProjectNotFoundException

# make a new project in the current working dir
def make_project(proj_name):
    logging.info("Creating new project: %s" % (proj_name))

    # create new firmware ID
    fwid = str(uuid.uuid4())

    # set project dir name
    project_dir = proj_name

    # create project dir
    os.mkdir(project_dir)

    # get path to project template
    template_dir = os.path.join(SETTINGS_DIR, 'project_template')

    # copy project template
    for f in os.listdir(template_dir):
        shutil.copy(os.path.join(template_dir, f), project_dir)

    # open settings file
    with open(os.path.join(project_dir, 'settings.json'), 'r+') as f:
        s = f.read()

        # replace template strings
        s = s.replace('%(PROJ_NAME)', proj_name)
        s = s.replace('%(FWID)', fwid)

        f.truncate(0)
        f.seek(0)
        f.write(s)

    logging.info("New project: '%s' created with firmware ID: %s" % (proj_name, fwid))

    save_project_info(proj_name, os.path.abspath(project_dir))

def main():
    # set global log level
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    # add a console handler to print anything INFO and above to the console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    parser = argparse.ArgumentParser(description='SapphireMake')

    parser.add_argument("--clean", "-c", action="store_true", help="clean only")
    parser.add_argument("--project", "-p", help="project to build")
    parser.add_argument("--list", "-l", action="store_true", help="list projects")
    parser.add_argument("--reset", action="store_true", help="reset project listing")
    parser.add_argument("--create", help="create a new template project")

    args = vars(parser.parse_args())

    # set target dir to cwd
    target_dir = os.getcwd()

    # check if listing  
    if args["list"]:
        projects = get_project_list()

        for key in projects:
            print "%20s %s" % (key, projects[key])

        return

    # check if reset
    if args["reset"]:
        os.remove(get_project_info_file())
        return

    # check if creating a new project
    if args["create"]:
        make_project(args["create"])
        return

    # check if project is given
    if args["project"]:
        # check if project is in the projects list
        try:
            project = get_project_builder(args["project"])
            target_dir = project.target_dir
        except KeyError:
            raise ProjectNotFoundException
    
    builder = get_builder(target_dir)
    
    # init logging
    builder.init_logging()

    # run clean    
    builder.clean()

    if not args["clean"]:
        builder.build()


if __name__ == "__main__":
    main()



