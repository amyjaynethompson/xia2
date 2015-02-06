
import os
import sys
import inspect

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from lib.bits import inherits_from
from lib.SymmetryLib import lauegroup_to_lattice, sort_lattices

from Handlers.Streams import Chatter, Debug

class Refiner(object):
  '''An interface to present refinement functionality in a similar way to the
  scaler interface.'''

  LATTICE_POSSIBLE = 'LATTICE_POSSIBLE'
  LATTICE_IMPOSSIBLE = 'LATTICE_IMPOSSIBLE'
  LATTICE_CORRECT = 'LATTICE_CORRECT'

  def __init__(self):
    super(Refiner, self).__init__()
    # set up a framework for storing all of the input information...
    # this should really only consist of integraters...

    # key this by the epoch, if available, else will need to
    # do something different.
    self._refinr_indexers = { }

    # admin junk
    self._working_directory = os.getcwd()

    self._refinr_payload = {}
    self._refinr_refined_experiment_list = None

    # implementation dependent parameters - these should be keyed by
    # say 'mosflm':{'yscale':0.9999} etc.
    self._refinr_program_parameters = { }

    return

  # serialization functions

  def to_dict(self):
    import json
    obj = {}
    obj['__id__'] = 'Refiner'
    obj['__module__'] = self.__class__.__module__
    obj['__name__'] = self.__class__.__name__
    import inspect
    attributes = inspect.getmembers(self, lambda m:not(inspect.isroutine(m)))
    for a in attributes:
      if 0 and a[0] == '_scalr_xcrystal':
        # XXX I guess we probably want this?
        continue
      elif a[0] == '_refinr_indexers':
        d = {}
        for k, v in a[1].iteritems():
          d[k] = v.to_dict()
        obj[a[0]] = d
      elif a[0] == '_refinr_refined_experiment_list':
        if a[1] is not None:
          obj[a[0]] = a[1].to_dict()
      elif (a[0].startswith('_refinr_')):
        obj[a[0]] = a[1]
    return obj

  @classmethod
  def from_dict(cls, obj):
    import json
    assert obj['__id__'] == 'Refiner'
    return_obj = cls()
    for k, v in obj.iteritems():
      if k == '_refinr_indexers':
        v_new = {}
        for k_, v_ in v.iteritems():
          from libtbx.utils import import_python_object
          integrater_cls = import_python_object(
            import_path=".".join((v_['__module__'], v_['__name__'])),
            error_prefix='', target_must_be='', where_str='').object
          v_new[float(k_)] = integrater_cls.from_dict(v_)
        v = v_new
      elif k == '_refinr_payload':
        v_new = {}
        for k_, v_ in v.iteritems():
          try:
            v_new[float(k_)] = v_
          except ValueError, e:
            v_new[k_] = v_
        v = v_new
      if isinstance(v, dict):
        if v.get('__id__', None) == 'ExperimentList':
          from dxtbx.model.experiment.experiment_list import ExperimentListFactory
          v = ExperimentListFactory.from_dict(v)
      setattr(return_obj, k, v)
    return return_obj

  def as_json(self, filename=None, compact=False):
    import json
    obj = self.to_dict()
    if compact:
      text = json.dumps(obj, skipkeys=False, separators=(',',':'), ensure_ascii=True)
    else:
      text = json.dumps(obj, skipkeys=False, indent=2, ensure_ascii=True)

    # If a filename is set then dump to file otherwise return string
    if filename is not None:
      with open(filename, 'w') as outfile:
        outfile.write(text)
    else:
      return text

  @classmethod
  def from_json(cls, filename=None, string=None):
    import json
    from dxtbx.serialize.load import _decode_dict
    assert [filename, string].count(None) == 1
    if filename is not None:
      with open(filename, 'rb') as f:
        string = f.read()
    obj = json.loads(string, object_hook=_decode_dict)
    return cls.from_dict(obj)

  def _refine_prepare(self):
    raise RuntimeError, 'overload me'

  def _refine(self):
    raise RuntimeError, 'overload me'

  def _refine_finish(self):
    pass

  def set_working_directory(self, working_directory):
    self._working_directory = working_directory
    return

  def get_working_directory(self):
    return self._working_directory

  def set_refiner_prepare_done(self, done = True):

    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    Debug.write('Called refiner prepare done from %s %d (%s)' %
                (mod.__name__, frm[0].f_lineno, done))

    self._refinr_prepare_done = done
    return

  def set_refiner_done(self, done = True):

    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    Debug.write('Called refiner done from %s %d (%s)' %
                (mod.__name__, frm[0].f_lineno, done))

    self._refinr_done = done
    return

  def set_refiner_finish_done(self, done = True):

    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    Debug.write('Called refiner finish done from %s %d (%s)' %
                (mod.__name__, frm[0].f_lineno, done))

    self._refinr_finish_done = done
    return

  def refiner_reset(self):

    Debug.write('Refiner reset')

    self._refinr_done = False
    self._refinr_prepare_done = False
    self._refinr_finish_done = False
    self._refinr_result = None
    return

  # getters of the status - note how the gets cascade to ensure that
  # everything is up-to-date...

  def get_refiner_prepare_done(self):
    return self._refinr_prepare_done

  def get_refiner_done(self):
    if not self.get_refiner_prepare_done():
      Debug.write('Resetting refiner done as prepare not done')
      self.set_refiner_done(False)
    return self._refinr_done

  def get_refiner_finish_done(self):
    if not self.get_refiner_done():
      Debug.write(
          'Resetting refiner finish done as refinement not done')
      self.set_refiner_finish_done(False)
    return self._refinr_finish_done

  def add_refiner_indexer(self, epoch, indexer):
    '''Add an indexer to this scaler, to provide the input.'''

    ## epoch values are trusted as long as they are unique.
    ## if a collision is detected, all epoch values are replaced by an
    ## integer series, starting with 0

    #if 1 or 0 in self._refinr_indexers.keys():
      #epoch = len(self._refinr_indexers)

    #else:
      #epoch = indexer.get_integrater_epoch()

      ## FIXME This is now probably superflous?
      #if epoch == 0 and self._refinr_indexers:
        #raise RuntimeError, 'multi-sweep indexer has epoch 0'

      #if epoch in self._refinr_indexers.keys():
        #Debug.write('indexer with epoch %d already exists. will not trust epoch values' % epoch)

        ## collision. Throw away all epoch keys, and replace with integer series
        #self._refinr_indexers = dict(zip(
            #range(0,len(self._refinr_indexers)),
             #self._refinr_indexers.values()))
        #epoch = len(self._refinr_indexers)

    self._refinr_indexers[epoch] = indexer

    self.refiner_reset()

    return

  def refine(self):
    '''Actually perform the refinement - this is delegated to the
    implementation.'''

    if self._refinr_indexers == { }:
      raise RuntimeError, \
            'no Indexer implementations assigned for refinement'

    #xname = self._refinr_xcrystal.get_name()

    while not self.get_refiner_finish_done():
      while not self.get_refiner_done():
        while not self.get_refiner_prepare_done():

          #Chatter.banner('Preparing %s' % xname)

          self._refinr_prepare_done = True
          self._refine_prepare()

        #Chatter.banner('Scaling %s' % xname)

        self._refinr_done = True
        self._refinr_result = self._refine()

      self._refinr_finish_done = True
      self._refine_finish()

    return self._refinr_result

  def set_refiner_payload(self, this, value):
    self._refinr_payload[this] = value

  def get_refiner_payload(self, this):
    self.refine()
    return self._refinr_payload.get(this, None)

  def eliminate(self, indxr_print=True):
    for idxr in self._refinr_indexers.values():
      idxr.eliminate(indxr_print=indxr_print)
    self.refiner_reset()

  def get_refiner_indexer(self, epoch):
    return self._refinr_indexers.get(epoch)

  def get_indexer_low_resolution(self, epoch):
    return self._refinr_indexers[epoch].get_indexer_low_resolution()

  def get_refined_experiment_list(self, epoch):
    self.refine()
    # FIXME needs revisiting for joint refinement
    return self._refinr_refined_experiment_list[0:1]

  def get_refiner_lattice(self):
    # for now assume all indexer have the same lattice
    return self._refinr_indexers.values()[0].get_indexer_lattice()

  def set_refiner_asserted_lattice(self, asserted_lattice):
    state = self.LATTICE_POSSIBLE
    for idxr in self._refinr_indexers.values():
      state = idxr.set_indexer_asserted_lattice(asserted_lattice)
    # XXX for multiple indexers need to get some kind of consensus?
    return state

  def set_refiner_parameter(self, program, parameter, value):
    '''Set an arbitrary parameter for the program specified to
    use in refinement, e.g. the YSCALE or GAIN values in Mosflm.'''

    if not self._refinr_program_parameters.has_key(program):
      self._refinr_program_parameters[program] = { }

    self._refinr_program_parameters[program][parameter] = value
    return

  def get_refiner_parameter(self, program, parameter):
    '''Get a parameter value.'''

    try:
      return self._refinr_program_parameters[program][parameter]
    except:
      return None

  def get_refiner_parameters(self, program):
    '''Get all parameters and values.'''

    try:
      return self._refinr_program_parameters[program]
    except:
      return { }

  def set_refiner_parameters(self, parameters):
    '''Set all parameters and values.'''

    self._refinr_program_parameters = parameters
    self.set_refiner_done(False)

    return