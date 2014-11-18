import os
import sys
if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                               'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

import libtbx.load_env
from libtbx import easy_run
from libtbx.test_utils import approx_equal, open_tmp_directory, show_diff

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_xds_indexer():
  if not have_dials_regression:
    print "Skipping exercise_xds_indexer(): dials_regression not configured"
    return

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from Modules.Indexer.XDSIndexerII import XDSIndexerII
  indexer = XDSIndexerII()
  indexer.set_working_directory(tmp_dir)
  indexer.setup_from_image(template %1)

  from Schema.XCrystal import XCrystal
  from Schema.XWavelength import XWavelength
  from Schema.XSweep import XSweep
  cryst = XCrystal("CRYST1", None)
  wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())
  directory, image = os.path.split(template %1)
  sweep = XSweep('SWEEP1', wav, directory=directory, image=image)
  indexer.set_indexer_sweep(sweep)

  indexer.index()

  assert approx_equal(indexer.get_indexer_cell(),
                      (78.0833, 78.0833, 78.0833, 90, 90, 90))
  experiment = indexer.get_indexer_experiment_list()[0]
  sgi = experiment.crystal.get_space_group().info()
  assert sgi.type().number() == 197

  beam_centre = indexer.get_indexer_beam_centre()
  assert approx_equal(beam_centre, (94.4236, 94.5116), eps=1e-4)
  assert indexer.get_indexer_images() == [(1, 45)]
  print indexer.get_indexer_experiment_list()[0].crystal
  print indexer.get_indexer_experiment_list()[0].detector


def run():
  exercise_xds_indexer()
  print "OK"


if __name__ == '__main__':
  run()
