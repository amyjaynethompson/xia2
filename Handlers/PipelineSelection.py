#!/usr/bin/env python
# PipelineSelection.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A handler to manage the selection of pipelines through which to run xia2,
# for instance what indexer to use, what integrater and what scaler.
# This will look for a file preferences.xia in ~/.xia2 or equivalent,
# and the current working directory.

import os
import sys

def check(key, value):
    '''Check that this thing is allowed to have this value.'''

    if key == 'indexer':
        if not value in ['xds', 'mosflm', 'labelit']:
            raise RuntimeError, 'indexer %s unknown' % value

    if key == 'indexer':
        if not value in ['xds', 'mosflm']:
            raise RuntimeError, 'integrater %s unknown' % value

    if key == 'scaler':
        if not value in ['xds', 'ccp4']:
            raise RuntimeError, 'scaler %s unknown' % value

    return

preferences = { }

def get_preferences():
    global preferences

    if preferences == { }:
        search_for_preferences()

    return preferences

def add_preference(key, value):
    '''Add in run-time a preference.'''

    global preferences

    check(key, value)

    if preferences.has_key(key):
        if preferences[key] != value:
            raise RuntimeError, 'setting %s to %s: already %s' % \
                  (key, value, preferences[key])
        
    preferences[key] = value

    return

def search_for_preferences():
    '''Search for a preferences file, first in HOME then here.'''

    global preferences

    if os.name == 'nt':
        homedir = os.path.join(os.environ['HOMEDRIVE'],
                               os.environ['HOMEPATH'])
        xia2dir = os.path.join(homedir, 'xia2')
    else:
        homedir = os.environ['HOME']
        xia2dir = os.path.join(homedir, '.xia2')

    if os.path.exists(os.path.join(xia2dir, 'preferences.xia')):
        preferences = parse_preferences(
            os.path.join(xia2dir, 'preferences.xia'), preferences)

    # look also in current working directory

    if os.path.exists(os.path.join(os.getcwd(), 'preferences.xia')):
        preferences = parse_preferences(
            os.path.join(os.getcwd(), 'preferences.xia'), preferences)

    return preferences

def parse_preferences(file, preferences):
    '''Parse preferences to the dictionary.'''

    for line in open(file, 'r').readlines():

        # all lower case
        line = line.lower()

        # ignore comment lines    
        if line[0] == '!' or line[0] == '#':
            continue

        check_value(line.split(':')[0], line.split(':')[1])

        preferences[line.split(':')[0]] = line.split(':')[1]

    return preferences

if __name__== '__main__':

    print search_for_preferences()

    
