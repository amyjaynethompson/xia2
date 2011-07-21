#!/usr/bin/env python
# FormatSMVRigakuSaturn.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the SMV image reader for Rigaku Saturn images.
# Inherits from FormatSMV.

import time
from scitbx import matrix

from FormatSMV import FormatSMV

class FormatSMVRigakuSaturn(FormatSMV):
    '''A class for reading SMV format Rigaku Saturn images, and correctly
    constructing a model for the experiment from this.'''

    @staticmethod
    def understand(image_file):
        '''Check to see if this looks like a Rigaku Saturn SMV format image,
        i.e. we can make sense of it. Essentially that will be if it contains
        all of the keys we are looking for.'''

        if FormatSMV.understand(image_file) == 0:
            return 0

        size, header = FormatSMV.get_smv_header(image_file)

        wanted_header_items = [
            'DETECTOR_NUMBER', 'DETECTOR_NAMES',
            'CRYSTAL_GONIO_NUM_VALUES', 'CRYSTAL_GONIO_NAMES',
            'CRYSTAL_GONIO_UNITS', 'CRYSTAL_GONIO_VALUES',
            'DTREK_DATE_TIME',
            'ROTATION', 'ROTATION_AXIS_NAME', 'ROTATION_VECTOR',
            'SOURCE_VECTORS', 'SOURCE_WAVELENGTH',
            'SOURCE_POLARZ', 'DIM', 'SIZE1', 'SIZE2',
            ]

        for header_item in wanted_header_items:
            if not header_item in header:
                return 0

        detector_prefix = header['DETECTOR_NAMES'].split()[0].strip()

        more_wanted_header_items = [
            'DETECTOR_DIMENSIONS', 'DETECTOR_SIZE', 'DETECTOR_VECTORS',
            'GONIO_NAMES', 'GONIO_UNITS', 'GONIO_VALUES', 'GONIO_VECTORS',
            'SPATIAL_BEAM_POSITION'
            ]

        for header_item in more_wanted_header_items:
            if not '%s%s' % (detector_prefix, header_item) in header:
                return 0

        return 2

    def __init__(self, image_file):
        '''Initialise the image structure from the given file, including a
        proper model of the experiment. Easy from Rigaku Saturn images as
        they contain everything pretty much we need...'''

        assert(FormatSMVRigakuSaturn.understand(image_file) > 0)
        
        FormatSMV.__init__(self, image_file)

        return

    def _xgoniometer(self):
        '''Initialize the structure for the goniometer - this will need to
        correctly compose the axes given in the image header. In this case
        this is made rather straightforward as the image header has the
        calculated rotation axis stored in it. We could work from the
        rest of the header and construct a goniometer model.'''

        axis = tuple(map(float, self._header_dictionary[
            'ROTATION_VECTOR'].split()))

        return self._xgoniometer_factory.KnownAxis(axis)

    def _xdetector(self):
        '''Return a model for the detector, allowing for two-theta offsets
        and the detector position. This will be rather more complex...'''

        detector_name = self._header_dictionary[
            'DETECTOR_NAMES'].split()[0].strip()

        detector_axes = map(float, self._header_dictionary[
            '%sDETECTOR_VECTORS' % detector_name].split())

        detector_fast = matrix.col(tuple(detector_axes[:3]))
        detector_slow = matrix.col(tuple(detector_axes[3:]))

        beam_pixels = map(float, self._header_dictionary[
            '%sSPATIAL_DISTORTION_INFO' % detector_name].split()[:2])
        pixel_size = map(float, self._header_dictionary[
            '%sSPATIAL_DISTORTION_INFO' % detector_name].split()[2:])
        image_size = map(int, self._header_dictionary[
            '%sDETECTOR_DIMENSIONS' % detector_name].split())

        detector_origin = - (beam_pixels[0] * pixel_size[0] * detector_fast + \
                             beam_pixels[1] * pixel_size[1] * detector_slow)

        gonio_axes = map(float, self._header_dictionary[
            '%sGONIO_VECTORS' % detector_name].split())
        gonio_values = map(float, self._header_dictionary[
            '%sGONIO_VALUES' % detector_name].split())
        gonio_units = self._header_dictionary[
            '%sGONIO_UNITS' % detector_name].split()
        gonio_num_axes = int(self._header_dictionary[
            '%sGONIO_NUM_VALUES' % detector_name])

        rotations = []
        translations = []

        for j, unit in enumerate(gonio_units):
            axis = matrix.col(gonio_axes[3 * j:3 * (j + 1)])
            if unit == 'deg':
                rotations.append(axis.axis_and_angle_as_r3_rotation_matrix(
                    gonio_values[j], deg = True))
                translations.append(matrix.col((0.0, 0.0, 0.0)))
            elif unit == 'mm':
                rotations.append(matrix.sqr((1.0, 0.0, 0.0,
                                             0.0, 1.0, 0.0,
                                             0.0, 0.0, 1.0)))
                translations.append(gonio_values[j] * axis)
            else:
                raise RuntimeError, 'unknown axis unit %s' % unit

        rotations.reverse()
        translations.reverse()

        for j in range(gonio_num_axes):
            detector_fast = rotations[j] * detector_fast
            detector_slow = rotations[j] * detector_slow
            detector_origin = rotations[j] * detector_origin
            detector_origin = translations[j] + detector_origin

        overload = int(self._header_dictionary['SATURATED_VALUE'])

        return self._xdetector_factory.Complex(
            detector_origin.elems, detector_fast.elems, detector_slow.elems,
            pixel_size, image_size, overload)

    def _xbeam(self):
        '''Return a simple model for the beam.'''

        beam_direction = map(float, self._header_dictionary[
            'SOURCE_VECTORS'].split()[:3])
        
        polarization = map(float, self._header_dictionary[
            'SOURCE_POLARZ'].split())

        p_fraction = polarization[0]
        p_plane = polarization[1:]
        
        wavelength = float(self._header_dictionary['SCAN_WAVELENGTH'])
        
        return self._xbeam_factory.Complex(
            beam_direction, p_fraction, p_plane, wavelength)

    def _xscan(self):
        '''Return the scan information for this image.'''

        rotation = map(float, self._header_dictionary['ROTATION'].split())

        format = self._xscan_factory.Format('SMV') 
        epoch = time.mktime(time.strptime(self._header_dictionary[
            'DTREK_DATE_TIME'], '%d-%b-%Y %H:%M:%S'))

        exposure_time = rotation[3]
        osc_start = rotation[0]
        osc_range = rotation[2]

        return self._xscan_factory.Single(
            self._image_file, format, exposure_time,
            osc_start, osc_range, epoch)

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print FormatSMVRigakuSaturn.understand(arg)
