#!/usr/bin/env python
# Integrate.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Integration using DIALS.

from __future__ import division
import os

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def Integrate(DriverType = None):
  '''A factory for IntegrateWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class IntegrateWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.integrate')

      self._experiments_filename = None
      self._reflections_filename = None
      self._integrated_filename = None
      self._profile_fitting = True
      self._outlier_algorithm = None
      self._background_algorithm = None
      self._phil_file = None
      self._mosaic = None
      self._d_max = None
      self._d_min = None
      self._use_threading = False
      self._scan_range = []
      self._reflections_per_degree = None

      return

    def set_use_threading(self, use_threading):
      self._use_threading = use_threading

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename
      return

    def get_experiments_filename(self):
      return self._experiments_filename

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filename = reflections_filename
      return

    def get_reflections_filename(self):
      return self._reflections_filename

    def set_profile_fitting(self, profile_fitting):
      self._profile_fitting = profile_fitting
      return

    def get_profile_fitting(self):
      return self._profile_fitting

    def set_background_outlier_algorithm(self, algorithm):
      self._outlier_algorithm = algorithm
      return

    def get_background_outlier_algorithm(self):
      return self._outlier_algorithm

    def set_background_algorithm(self, algorithm):
      self._background_algorithm = algorithm
      return

    def get_background_algorithm(self):
      return self._background_algorithm

    def set_reflections_per_degree(self, reflections_per_degree):
      self._reflections_per_degree = reflections_per_degree

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def set_d_max(self, d_max):
      self._d_max = d_max
      return

    def set_d_min(self, d_min):
      self._d_min = d_min
      return

    def add_scan_range(self, start, stop):
      self._scan_range.append((start, stop))

    def get_integrated_filename(self):
      return self._integrated_filename

    def get_mosaic(self):
      return self._mosaic

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.integrate')

      self.clear_command_line()
      self.add_command_line('input.experiments=%s' % self._experiments_filename)
      nproc = Flags.get_parallel()
      self.set_cpu_threads(nproc)

      if self._use_threading:
        self.add_command_line('nthreads=%i' %nproc)
        nproc = 1

      self.add_command_line('nproc=%i' % nproc)
      self.add_command_line(('input.reflections=%s' % self._reflections_filename))
      self._integrated_filename = os.path.join(
        self.get_working_directory(), '%d_integrated.pickle' %self.get_xpid())
      self.add_command_line('output.reflections=%s' % self._integrated_filename)
      self.add_command_line(
        'profile.fitting=%s' % self._profile_fitting)
      if self._outlier_algorithm is not None:
        self.add_command_line(
          'outlier.algorithm=%s' % self._outlier_algorithm)
      if self._background_algorithm is not None:
        self.add_command_line(
          'background.algorithm=%s' % self._background_algorithm)
      if self._phil_file is not None:
        self.add_command_line('%s' % self._phil_file)
      if self._d_max is not None:
        self.add_command_line('prediction.dmax=%f' % self._d_max)
      if self._d_min is not None and self._d_min > 0.0:
        self.add_command_line('prediction.dmin=%f' % self._d_min)
      for scan_range in self._scan_range:
        self.add_command_line('scan_range=%d,%d' %scan_range)
      if self._reflections_per_degree is not None:
        self.add_command_line('reflections_per_degree=%d' %self._reflections_per_degree)
        self.add_command_line('integrate_all_reflections=False')

      self.start()
      self.close_wait()

      for record in self.get_all_output():
        if 'There was a problem allocating memory for shoeboxes' in record:
          raise RuntimeError(
'''dials.integrate requires more memory than is available.
Try using a machine with more memory or using fewer processor.''')

      self.check_for_errors()

      for record in self.get_all_output():
        if 'Sigma_m' in record:
          self._mosaic = float(record.split()[-2])

      return

  return IntegrateWrapper()
