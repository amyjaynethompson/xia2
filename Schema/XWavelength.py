#!/usr/bin/env python
# XWavelength.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# A versioning object representing the wavelength level in the .xinfo
# hierarchy. This will include all of the methods for performing operations
# on a wavelength as well as stuff for integration with the rest of the
# .xinfo hierarchy.
# 
# The following are properties defined for an XWavelength object:
# 
# wavelength
# f_pr
# f_prpr
#
# However, these objects are not versioned, since they do not (in the current
# implementation) impact on the data reduction process. These are mostly
# passed through.
#
# FIXME 05/SEP/06 this also needs to be able to handle the information
#                 pertaining to the lattice, because it is critcial that
#                 all of the sweeps for a wavelength share the same
#                 lattice.
# 
# FIXME 05/SEP/06 also don't forget about ordering the sweeps in collection
#                 order for the data reduction, to make sure that we 
#                 reduce the least damaged data first.

from XSweep import XSweep

class XWavelength(Object):
    '''An object representation of a wavelength, which will after data
    reduction correspond to an MTZ hierarchy dataset.'''

    def __init__(self, name, crystal, wavelength,
                 f_pr = 0.0, f_prpr = 0.0):
        '''Create a new wavelength named name, belonging to XCrystal object
        crystal, with wavelength and optionally f_pr, f_prpr assigned.'''

        # check that the crystal is an XCrystal

        if not crystal.__class__.__name__ == 'XCrystal':
            pass

        # set up this object

        self._name = name
        self._crystal = crystal
        self._wavelength = wavelength
        self._f_pr = f_pr
        self._f_prpr = f_prpr
        
        # then create space to store things which are contained
        # in here - the sweeps

        self._sweeps = []

        return

    def get_wavelength(self):
        return self._wavelength

    def get_fpr(self):
        return self._fpr

    def get_fprpr(self):
        return self._fprpr

    def get_crystal(self):
        return self._crystal

    def get_name(self):
        return self._name

    def add_sweep(self, name, directory, image,
                  beam = None, resolution = None):
        '''Add a sweep to this wavelength.'''

        self._sweeps.append(XSweep(name, self, directory, image,
                                   beam = beam,
                                   resolution = resolution))

        return

    def get_sweeps(self):
        return self._sweeps

    
