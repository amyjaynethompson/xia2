#!/usr/bin/env python
# Phil.py
#   Copyright (C) 2012 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Phil parameter setting - to get a single place where complex parameters to
# set for individual programs can be found. Initially this will be just a 
# couple for XDS.

from libtbx.phil import parse

class _Phil:
    def __init__(self):
        self._working_phil = parse("""
xds.parameter {
  delphi = 5
    .type = float
}
""")
        return

    def show(self):
        self._working_phil.show()
        return

    def get_xds_parameter_delphi(self):
        return self._working_phil.extract().xds.parameter.delphi

Phil = _Phil()

if __name__ == '__main__':
    print Phil.get_xds_parameter_delphi()
