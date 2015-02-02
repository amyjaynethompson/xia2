#!/usr/bin/env python
# XDSRefiner.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from Schema.Interfaces.Refiner import Refiner
from Handlers.Streams import Debug, Chatter
from Handlers.Flags import Flags

import os
import math

from lib.bits import auto_logfiler
from Handlers.Files import FileHandler

from Wrappers.XDS.XDSXycorr import XDSXycorr as _Xycorr
from Wrappers.XDS.XDSInit import XDSInit as _Init

class XDSRefiner(Refiner):

  def __init__(self):
    super(XDSRefiner, self).__init__()

  # factory functions
  def ExportXDS(self):
    from Wrappers.Dials.ExportXDS import ExportXDS as _ExportXDS
    export_xds = _ExportXDS()
    export_xds.set_working_directory(self.get_working_directory())
    auto_logfiler(export_xds)
    return export_xds

  def Xycorr(self):
    xycorr = _Xycorr()
    xycorr.set_working_directory(self.get_working_directory())

    xycorr.setup_from_imageset(self.get_imageset())

    if self.get_distance():
      xycorr.set_distance(self.get_distance())

    if self.get_wavelength():
      xycorr.set_wavelength(self.get_wavelength())

    auto_logfiler(xycorr, 'XYCORR')

    return xycorr

  def Init(self):
    from Handlers.Phil import PhilIndex
    init = _Init(params=PhilIndex.params.xds.init)
    init.set_working_directory(self.get_working_directory())

    init.setup_from_imageset(self.get_imageset())

    if self.get_distance():
      init.set_distance(self.get_distance())

    if self.get_wavelength():
      init.set_wavelength(self.get_wavelength())

    auto_logfiler(init, 'INIT')

    return init

  def _refine_prepare(self):
    for epoch, idxr in self._refinr_indexers.iteritems():

      experiments = idxr.get_indexer_experiment_list()
      assert len(experiments) == 1 # currently only handle one lattice/sweep
      experiment = experiments[0]
      crystal_model = experiment.crystal
      lattice = idxr.get_indexer_lattice()

      # check if the lattice was user assigned...
      user_assigned = idxr.get_indexer_user_input_lattice()

      # hack to figure out if we did indexing with Dials - if so then need to
      # run XYCORR, INIT, and then dials.export_xds before we are ready to
      # integrate with XDS
      from Modules.Indexer.DialsIndexer import DialsIndexer
      if isinstance(idxr, DialsIndexer):
        all_images = idxr.get_matching_images()
        first = min(all_images)
        last = max(all_images)

        last_background = int(round(5.0 / idxr.get_phi_width())) - 1 + first
        last_background = min(last, last_background)

        # next start to process these - first xycorr
        # FIXME run these *afterwards* as then we have a refined detector geometry
        # so the parallax correction etc. should be slightly better.

        #self._indxr_images = [(first, last)]
        xycorr = self.Xycorr()
        xycorr.set_data_range(first, last)
        xycorr.set_background_range(first, last_background)
        xycorr.run()

        for file in ['X-CORRECTIONS.cbf',
                     'Y-CORRECTIONS.cbf']:
          self._xds_data_files[file] = xycorr.get_output_data_file(file)

        # next start to process these - then init

        init = self.Init()

        for file in ['X-CORRECTIONS.cbf',
                     'Y-CORRECTIONS.cbf']:
          init.set_input_data_file(file, self._xds_data_files[file])

        init.set_data_range(first, last)
        init.set_background_range(first, last_background)
        init.run()

        for file in ['BLANK.cbf',
                     'BKGINIT.cbf',
                     'GAIN.cbf']:
          self._xds_data_files[file] = init.get_output_data_file(file)

        exporter = self.ExportXDS()
        exporter.set_experiments_filename(
          idxr.get_indexer_solution()['experiments_file'])
        exporter.run()

        for file in ['XPARM.XDS']:
          self._xds_data_files[file] = os.path.join(
            idxr.get_working_directory(), 'xds', file)

        for k, v in self._xds_data_files:
          idxr.set_indexer_payload(k, v)

      # check that the indexer is an XDS indexer - if not then
      # create one...

      elif not idxr.get_indexer_payload('XPARM.XDS'):
        Debug.write('Generating an XDS indexer')

        idxr_old = idxr

        idxr = XDSIndexer()
        idxr.set_indexer_sweep(idxr_old.get_indexer_sweep())
        self._refinr_indexers[epoch] = idxr
        self.set_refiner_prepare_done(False)

        # note to self for the future - this set will reset the
        # integrater prepare done flag - this means that we will
        # go through this routine all over again. However this
        # is not a problem as all that will happen is that the
        # results will be re-got, no additional processing will
        # be performed...


        # set the indexer up as per the frameprocessor interface...
        # this would usually happen within the IndexerFactory.

        idxr.set_indexer_sweep_name(idxr_old.get_indexer_sweep_name())

        idxr.setup_from_imageset(idxr_old.get_imageset())
        idxr.set_working_directory(idxr_old.get_working_directory())

        if idxr_old.get_frame_wedge():
          wedge = idxr_old.get_frame_wedge()
          Debug.write('Propogating wedge limit: %d %d' % wedge)
          idxr.set_frame_wedge(wedge[0], wedge[1], apply_offset = False)

        if idxr_old.get_reversephi():
          Debug.write('Propogating reverse-phi...')
          idxr.set_reversephi()

        # now copy information from the old indexer to the new
        # one - lattice, cell, distance etc.

        # bug # 2434 - providing the correct target cell
        # may be screwing things up - perhaps it would
        # be best to allow XDS just to index with a free
        # cell but target lattice??
        cell = crystal_model.get_unit_cell().parameters()
        if Flags.get_relax():
          Debug.write(
              'Inputting target cell: %.2f %.2f %.2f %.2f %.2f %.2f' % \
              cell)
          idxr.set_indexer_input_cell(cell)
        input_cell = cell

        # propogate the wavelength information...
        if idxr_old.get_wavelength():
          idxr.set_wavelength(idxr_old.get_wavelength())

        from cctbx.sgtbx import bravais_types
        lattice = str(
          bravais_types.bravais_lattice(group=crystal_model.get_space_group()))
        idxr.set_indexer_input_lattice(lattice)

        if user_assigned:
          Debug.write('Assigning the user given lattice: %s' % \
                      lattice)
          idxr.set_indexer_user_input_lattice(True)

        idxr.set_detector(experiment.detector)
        idxr.set_beam_obj(experiment.beam)
        idxr.set_goniometer(experiment.goniometer)

        # re-get the unit cell &c. and check that the indexing
        # worked correctly

        Debug.write('Rerunning indexing with XDS')

        experiments = idxr.get_indexer_experiment_list()
        assert len(experiments) == 1 # currently only handle one lattice/sweep
        experiment = experiments[0]
        crystal_model = experiment.crystal

        # then in here check that the target unit cell corresponds
        # to the unit cell I wanted as input...? now for this I
        # should probably compute the unit cell volume rather
        # than comparing the cell axes as they may have been
        # switched around...

        # FIXME comparison needed



  def _refine(self):
    import copy
    from dxtbx.model.experiment.experiment_list import ExperimentList
    self._refinr_refined_experiment_list = ExperimentList()
    for epoch, idxr in self._refinr_indexers.iteritems():
      self._refinr_payload[epoch] = copy.deepcopy(idxr._indxr_payload)
      self._refinr_refined_experiment_list.extend(
        idxr.get_indexer_experiment_list())

  def _refine_finish(self):
    pass
