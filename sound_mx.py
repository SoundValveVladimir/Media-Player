# -*- coding: utf-8 -*-
import ctypes
import functools
import inspect as _inspect
import logging
import os
import sys
from ctypes.util import find_library

logger = logging.getLogger(__name__)

__version__ = "3.0.21203"
__libvlc_version__ = "3.0.21"
__generator_version__ = "2.3"
build_date = "18.05.2025"
DEFAULT_ENCODING = "utf-8"

def str_to_bytes(s):
    if isinstance(s, str):
        return bytes(s, DEFAULT_ENCODING)
    else:
        return s

def bytes_to_str(b):
    if isinstance(b, bytes):
        return b.decode(DEFAULT_ENCODING)
    else:
        return b

def len_args(func):
    return len(_inspect.signature(func).parameters)

_internal_guard = object()

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def find_lib():
    """Загружает libvlc.dll из папки Data"""
    libname = "libvlc.dll"
    plugin_path = resource_path('Data')
    lib_path = os.path.join(plugin_path, libname)

    if os.path.exists(lib_path):
        print(f"[INFO] Загрузка {libname} из {plugin_path}")
        try:
            dll = ctypes.CDLL(lib_path)
            return dll, plugin_path
        except OSError as e:
            print(f"[ERROR] Ошибка загрузки {libname}: {e}")
            sys.exit(1)
    else:
        print(f"[ERROR] Не найден {libname} в {plugin_path}")
        sys.exit(1)

dll, plugin_path = find_lib()

class VLCException(Exception):
    pass

try:
    _Ints = (int, int)
except NameError:  # no long in Python 3+
    _Ints = int
_Seqs = (list, tuple)

class memoize_parameterless(object):

    def __init__(self, func):
        self.func = func
        self._cache = {}

    def __call__(self, obj):
        try:
            return self._cache[obj]
        except KeyError:
            v = self._cache[obj] = self.func(obj)
            return v

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, obj, objtype):
        return functools.partial(self.__call__, obj)

_default_instance = None

def get_default_instance():
    global _default_instance
    if _default_instance is None:
        _default_instance = Instance()
    return _default_instance

def try_fspath(path):
    try:
        return os.fspath(path)
    except (AttributeError, TypeError):
        return path

_Cfunctions = {}
_Globals = globals()

def _Cfunction(name, flags, errcheck, *types):
    if hasattr(dll, name) and name in _Globals:
        p = ctypes.CFUNCTYPE(*types)
        f = p((name, dll), flags)
        if errcheck is not None:
            f.errcheck = errcheck
        if __debug__:
            _Cfunctions[name] = f
        else:
            _Globals[name] = f
        return f
    raise NameError("no function %r" % (name,))

def _Cobject(cls, ctype):
    o = object.__new__(cls)
    o._as_parameter_ = ctype
    return o

def _Constructor(cls, ptr=_internal_guard):
    if ptr == _internal_guard:
        raise VLCException(
            "(INTERNAL) ctypes class. You should get references for this class through methods of the LibVLC API."
        )
    if ptr is None or ptr == 0:
        return None
    return _Cobject(cls, ctypes.c_void_p(ptr))

class _Cstruct(ctypes.Structure):
    _fields_ = []

    def __str__(self):
        l = [" %s:\t%s" % (n, getattr(self, n)) for n, _ in self._fields_]
        return "\n".join([self.__class__.__name__] + l)

    def __repr__(self):
        return "%s.%s" % (self.__class__.__module__, self)

class _Ctype(object):

    @staticmethod
    def from_param(this):
        if this is None:
            return None
        return this._as_parameter_

class ListPOINTER(object):

    def __init__(self, etype):
        self.etype = etype

    def from_param(self, param):
        if isinstance(param, _Seqs):
            return (self.etype * len(param))(*param)
        else:
            return ctypes.POINTER(param)

def string_result(result, func, arguments):
    if result:
        s = bytes_to_str(ctypes.string_at(result))
        libvlc_free(result)
        return s
    return None

def class_result(classname):

    def wrap_errcheck(result, func, arguments):
        if result is None:
            return None
        return classname(result)

    return wrap_errcheck

class Log(ctypes.Structure):
    pass

Log_ptr = ctypes.POINTER(Log)

class MediaThumbnailRequest:
    def __new__(cls, *args):
        if len(args) == 1 and isinstance(args[0], _Ints):
            return _Constructor(cls, args[0])

class FILE(ctypes.Structure):
    pass

FILE_ptr = ctypes.POINTER(FILE)

PyFile_FromFd = ctypes.pythonapi.PyFile_FromFd
PyFile_FromFd.restype = ctypes.py_object
PyFile_FromFd.argtypes = [
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
]
PyFile_AsFd = ctypes.pythonapi.PyObject_AsFileDescriptor
PyFile_AsFd.restype = ctypes.c_int
PyFile_AsFd.argtypes = [ctypes.py_object]

def module_description_list(head):
    r = []
    if head:
        item = head
        while item:
            item = item.contents
            r.append((item.name, item.shortname, item.longname, item.help))
            item = item.__next__
        libvlc_module_description_list_release(head)
    return r

def track_description_list(head):
    r = []
    if head:
        item = head
        while item:
            item = item.contents
            r.append((item.id, item.name))
            item = item.__next__
        try:
            libvlc_track_description_release(head)
        except NameError:
            libvlc_track_description_list_release(head)

    return r


class _Enum(ctypes.c_uint):
    _enum_names_ = {}

    def __str__(self):
        n = self._enum_names_.get(self.value, "") or ("FIXME_(%r)" % (self.value,))
        return ".".join((self.__class__.__name__, n))

    def __hash__(self):
        return self.value

    def __repr__(self):
        return ".".join((self.__class__.__module__, self.__str__()))

    def __eq__(self, other):
        return (isinstance(other, _Enum) and self.value == other.value) or (
            isinstance(other, _Ints) and self.value == other
        )

    def __ne__(self, other):
        return not self.__eq__(other)


class AudioEqualizer(_Ctype):
    def __new__(cls, *args):
        if len(args) == 1 and isinstance(args[0], _Ints):
            return _Constructor(cls, args[0])
        return libvlc_audio_equalizer_new()

    def get_amp_at_index(self, u_band):
        return libvlc_audio_equalizer_get_amp_at_index(self, u_band)

    def get_preamp(self):
        return libvlc_audio_equalizer_get_preamp(self)

    def release(self):
        return libvlc_audio_equalizer_release(self)

    def set_amp_at_index(self, f_amp, u_band):
        return libvlc_audio_equalizer_set_amp_at_index(self, f_amp, u_band)

    def set_preamp(self, f_preamp):
        return libvlc_audio_equalizer_set_preamp(self, f_preamp)


class EventManager(_Ctype):
    _callback_handler = None
    _callbacks = {}

    def __new__(cls, ptr=_internal_guard):
        if ptr == _internal_guard:
            raise VLCException(
                "(INTERNAL) ctypes class.\nYou should get a reference to EventManager through the MediaPlayer.event_manager() method."
            )
        return _Constructor(cls, ptr)

    def event_attach(self, eventtype, callback, *args, **kwds):
        if not isinstance(eventtype, EventType):
            raise VLCException("%s required: %r" % ("EventType", eventtype))
        if not hasattr(callback, "__call__"):
            raise VLCException("%s required: %r" % ("callable", callback))
        if len_args(callback) < 1:
            raise VLCException("%s required: %r" % ("argument", callback))

        if self._callback_handler is None:
            _called_from_ctypes = ctypes.CFUNCTYPE(
                None, ctypes.POINTER(Event), ctypes.c_void_p
            )

            @_called_from_ctypes
            def _callback_handler(event, k):
                try:
                    call, args, kwds = self._callbacks[k]
                except KeyError:
                    pass
                else:
                    call(event.contents, *args, **kwds)

            self._callback_handler = _callback_handler
            self._callbacks = {}

        k = eventtype.value
        r = libvlc_event_attach(self, k, self._callback_handler, k)
        if not r:
            self._callbacks[k] = (callback, args, kwds)
        return r

    def event_detach(self, eventtype):
        if not isinstance(eventtype, EventType):
            raise VLCException("%s required: %r" % ("EventType", eventtype))

        k = eventtype.value
        if k in self._callbacks:
            del self._callbacks[k]  # remove, regardless of libvlc return value
            libvlc_event_detach(self, k, self._callback_handler, k)


class Instance(_Ctype):
    def __new__(cls, *args):
        if len(args) == 1:
            i = args[0]
            if isinstance(i, _Ints):
                return _Constructor(cls, i)
            elif isinstance(i, str):
                args = i.strip().split()
            elif isinstance(i, _Seqs):
                args = list(i)
            else:
                raise VLCException("Instance %r" % (args,))
        else:
            args = list(args)

        if not args:  # no parameters passed
            args = ["vlc"]
        elif args[0] != "vlc":
            args.insert(0, "vlc")

        if plugin_path is not None:
            os.environ.setdefault("VLC_PLUGIN_PATH", plugin_path)

        args = [str_to_bytes(a) for a in args]
        return libvlc_new(len(args), args)

    def media_player_new(self, uri=None):

        p = libvlc_media_player_new(self)
        if uri:
            p.set_media(self.media_new(uri))
        p._instance = self
        return p

    def media_list_player_new(self):
        p = libvlc_media_list_player_new(self)
        p._instance = self
        return p

    def media_new(self, mrl, *options):
        mrl = try_fspath(mrl)
        if ":" in mrl and mrl.index(":") > 1:
            if __version__ >= "4":
                m = libvlc_media_new_location(str_to_bytes(mrl))
            else:
                m = libvlc_media_new_location(self, str_to_bytes(mrl))
        else:
            m = self.media_new_path(str_to_bytes(os.path.normpath(mrl)))
        for o in options:
            libvlc_media_add_option(m, str_to_bytes(o))
        m._instance = self
        return m

    def media_new_path(self, path):
        path = try_fspath(path)
        if __version__ >= "4":
            return libvlc_media_new_path(str_to_bytes(path))
        else:
            return libvlc_media_new_path(self, str_to_bytes(path))

    def media_list_new(self, mrls=None):
        if len_args(libvlc_media_list_new) == 1:  # API <= 3
            l = libvlc_media_list_new(self)
        else:  # API >= 4
            l = libvlc_media_list_new()
        if mrls:
            for m in mrls:
                l.add_media(m)
        l._instance = self
        return l

    def audio_output_enumerate_devices(self):
        r = []
        head = libvlc_audio_output_list_get(self)
        if head:
            i = head
            while i:
                i = i.contents
                r.append({"name": i.name, "description": i.description})
                i = i.__next__
            libvlc_audio_output_list_release(head)
        return r

    def audio_filter_list_get(self):
        return module_description_list(libvlc_audio_filter_list_get(self))

    def video_filter_list_get(self): 
        return module_description_list(libvlc_video_filter_list_get(self))

    def add_intf(self, name):
        return libvlc_add_intf(self, str_to_bytes(name))

    def audio_output_device_count(self, psz_audio_output):
        return libvlc_audio_output_device_count(self, str_to_bytes(psz_audio_output))

    def audio_output_device_id(self, psz_audio_output, i_device):
        return libvlc_audio_output_device_id(
            self, str_to_bytes(psz_audio_output), i_device
        )

    def audio_output_device_list_get(self, aout):
        return libvlc_audio_output_device_list_get(self, str_to_bytes(aout))

    def audio_output_device_longname(self, psz_output, i_device):
        return libvlc_audio_output_device_longname(
            self, str_to_bytes(psz_output), i_device
        )

    def audio_output_list_get(self):
        return libvlc_audio_output_list_get(self)

    def dialog_set_callbacks(self, p_cbs, p_data):
        return libvlc_dialog_set_callbacks(self, p_cbs, p_data)

    def get_log_verbosity(self):
        return libvlc_get_log_verbosity(self)

    def log_open(self):
        return libvlc_log_open(self)

    def log_set(self, cb, data):
        return libvlc_log_set(self, cb, data)

    def log_set_file(self, stream):
        return libvlc_log_set_file(self, stream)

    def log_unset(self):
        return libvlc_log_unset(self)

    def media_discoverer_list_get(self, i_cat, ppp_services):
        return libvlc_media_discoverer_list_get(self, i_cat, ppp_services)

    def media_discoverer_new(self, psz_name):
        return libvlc_media_discoverer_new(self, str_to_bytes(psz_name))

    def media_discoverer_new_from_name(self, psz_name):
        return libvlc_media_discoverer_new_from_name(self, str_to_bytes(psz_name))

    def media_library_new(self):
        return libvlc_media_library_new(self)

    def media_new_as_node(self, psz_name):
        return libvlc_media_new_as_node(self, str_to_bytes(psz_name))

    def media_new_callbacks(self, open_cb, read_cb, seek_cb, close_cb, opaque):
        return libvlc_media_new_callbacks(
            self, open_cb, read_cb, seek_cb, close_cb, opaque
        )

    def media_new_fd(self, fd):
        return libvlc_media_new_fd(self, fd)

    def media_new_location(self, psz_mrl):
        return libvlc_media_new_location(self, str_to_bytes(psz_mrl))

    def playlist_play(self, i_id, i_options, ppsz_options):
        return libvlc_playlist_play(self, i_id, i_options, ppsz_options)

    def release(self):
        return libvlc_release(self)

    def renderer_discoverer_list_get(self, ppp_services):
        return libvlc_renderer_discoverer_list_get(self, ppp_services)

    def renderer_discoverer_new(self, psz_name):
        return libvlc_renderer_discoverer_new(self, str_to_bytes(psz_name))

    def retain(self):
        return libvlc_retain(self)

    def set_app_id(self, id, version, icon):
        return libvlc_set_app_id(
            self, str_to_bytes(id), str_to_bytes(version), str_to_bytes(icon)
        )

    def set_exit_handler(self, cb, opaque):
        return libvlc_set_exit_handler(self, cb, opaque)

    def set_log_verbosity(self, level):
        return libvlc_set_log_verbosity(self, level)

    def set_user_agent(self, name, http):
        return libvlc_set_user_agent(self, str_to_bytes(name), str_to_bytes(http))

    def vlm_add_broadcast(
        self,
        psz_name,
        psz_input,
        psz_output,
        i_options,
        ppsz_options,
        b_enabled,
        b_loop,
    ):
        return libvlc_vlm_add_broadcast(
            self,
            str_to_bytes(psz_name),
            str_to_bytes(psz_input),
            str_to_bytes(psz_output),
            i_options,
            ppsz_options,
            b_enabled,
            b_loop,
        )

    def vlm_add_input(self, psz_name, psz_input):
        return libvlc_vlm_add_input(
            self, str_to_bytes(psz_name), str_to_bytes(psz_input)
        )

    def vlm_add_vod(
        self, psz_name, psz_input, i_options, ppsz_options, b_enabled, psz_mux
    ):
        return libvlc_vlm_add_vod(
            self,
            str_to_bytes(psz_name),
            str_to_bytes(psz_input),
            i_options,
            ppsz_options,
            b_enabled,
            str_to_bytes(psz_mux),
        )

    def vlm_change_media(
        self,
        psz_name,
        psz_input,
        psz_output,
        i_options,
        ppsz_options,
        b_enabled,
        b_loop,
    ):
        return libvlc_vlm_change_media(
            self,
            str_to_bytes(psz_name),
            str_to_bytes(psz_input),
            str_to_bytes(psz_output),
            i_options,
            ppsz_options,
            b_enabled,
            b_loop,
        )

    def vlm_del_media(self, psz_name):
        return libvlc_vlm_del_media(self, str_to_bytes(psz_name))

    @memoize_parameterless
    def vlm_get_event_manager(self):
        return libvlc_vlm_get_event_manager(self)

    def vlm_get_media_instance_length(self, psz_name, i_instance):
        return libvlc_vlm_get_media_instance_length(
            self, str_to_bytes(psz_name), i_instance
        )

    def vlm_get_media_instance_position(self, psz_name, i_instance):
        return libvlc_vlm_get_media_instance_position(
            self, str_to_bytes(psz_name), i_instance
        )

    def vlm_get_media_instance_rate(self, psz_name, i_instance):
        return libvlc_vlm_get_media_instance_rate(
            self, str_to_bytes(psz_name), i_instance
        )

    def vlm_get_media_instance_time(self, psz_name, i_instance):
        return libvlc_vlm_get_media_instance_time(
            self, str_to_bytes(psz_name), i_instance
        )

    def vlm_pause_media(self, psz_name):
        return libvlc_vlm_pause_media(self, str_to_bytes(psz_name))

    def vlm_play_media(self, psz_name):
        return libvlc_vlm_play_media(self, str_to_bytes(psz_name))

    def vlm_release(self):
        return libvlc_vlm_release(self)

    def vlm_seek_media(self, psz_name, f_percentage):
        return libvlc_vlm_seek_media(self, str_to_bytes(psz_name), f_percentage)

    def vlm_set_enabled(self, psz_name, b_enabled):
        return libvlc_vlm_set_enabled(self, str_to_bytes(psz_name), b_enabled)

    def vlm_set_input(self, psz_name, psz_input):
        return libvlc_vlm_set_input(
            self, str_to_bytes(psz_name), str_to_bytes(psz_input)
        )

    def vlm_set_loop(self, psz_name, b_loop):
        return libvlc_vlm_set_loop(self, str_to_bytes(psz_name), b_loop)

    def vlm_set_mux(self, psz_name, psz_mux):
        return libvlc_vlm_set_mux(self, str_to_bytes(psz_name), str_to_bytes(psz_mux))

    def vlm_set_output(self, psz_name, psz_output):
        return libvlc_vlm_set_output(
            self, str_to_bytes(psz_name), str_to_bytes(psz_output)
        )

    def vlm_show_media(self, psz_name):
        return libvlc_vlm_show_media(self, str_to_bytes(psz_name))

    def vlm_stop_media(self, psz_name):
        return libvlc_vlm_stop_media(self, str_to_bytes(psz_name))

    def wait(self):
        return libvlc_wait(self)


class LogIterator(_Ctype):

    def __new__(cls, ptr=_internal_guard):
        return _Constructor(cls, ptr)

    def __iter__(self):
        return self

    def __next__(self):
        if self.has_next():
            b = LogMessage()
            i = libvlc_log_iterator_next(self, b)
            return i.contents
        raise StopIteration

    def __next__(self):
        return next(self)

    def free(self):
        return libvlc_log_iterator_free(self)

    def has_next(self):
        return libvlc_log_iterator_has_next(self)


class Media(_Ctype):

    def __new__(cls, *args):
        if args:
            i = args[0]
            if isinstance(i, _Ints):
                return _Constructor(cls, i)
            if isinstance(i, Instance):
                return i.media_new(*args[1:])

        o = get_default_instance().media_new(*args)
        return o

    def get_instance(self):
        return getattr(self, "_instance", None)

    def add_options(self, *options):
        for o in options:
            self.add_option(o)

    def tracks_get(self):
        mediaTrack_pp = ctypes.POINTER(MediaTrack)()
        n = libvlc_media_tracks_get(self, ctypes.byref(mediaTrack_pp))
        info = ctypes.cast(
            mediaTrack_pp, ctypes.POINTER(ctypes.POINTER(MediaTrack) * n)
        )
        try:
            contents = info.contents
        except ValueError:
            return None
        tracks = (contents[i].contents for i in range(len(contents)))
        return tracks

    def add_option(self, psz_options):
        return libvlc_media_add_option(self, str_to_bytes(psz_options))

    def add_option_flag(self, psz_options, i_flags):
        return libvlc_media_add_option_flag(self, str_to_bytes(psz_options), i_flags)

    def duplicate(self):
        return libvlc_media_duplicate(self)

    @memoize_parameterless
    def event_manager(self):
        return libvlc_media_event_manager(self)

    def get_duration(self):
        return libvlc_media_get_duration(self)

    def get_meta(self, e_meta):
        return libvlc_media_get_meta(self, e_meta)

    def get_mrl(self):
        return libvlc_media_get_mrl(self)

    def get_parsed_status(self):
        return libvlc_media_get_parsed_status(self)

    def get_state(self):
        return libvlc_media_get_state(self)

    def get_stats(self, p_stats):
        return libvlc_media_get_stats(self, p_stats)

    def get_tracks_info(self):
        return libvlc_media_get_tracks_info(self)

    def get_type(self):
        return libvlc_media_get_type(self)

    def get_user_data(self):
        return libvlc_media_get_user_data(self)

    def is_parsed(self):
        return libvlc_media_is_parsed(self)

    def parse(self):
        return libvlc_media_parse(self)

    def parse_async(self):
        return libvlc_media_parse_async(self)

    def parse_stop(self):
        return libvlc_media_parse_stop(self)

    def parse_with_options(self, parse_flag, timeout):
        return libvlc_media_parse_with_options(self, parse_flag, timeout)

    def player_new_from_media(self):
        return libvlc_media_player_new_from_media(self)

    def release(self):
        return libvlc_media_release(self)

    def retain(self):
        return libvlc_media_retain(self)

    def save_meta(self):
        return libvlc_media_save_meta(self)

    def set_meta(self, e_meta, psz_value):
        return libvlc_media_set_meta(self, e_meta, str_to_bytes(psz_value))

    def set_user_data(self, p_new_user_data):
        return libvlc_media_set_user_data(self, p_new_user_data)

    def slaves_add(self, i_type, i_priority, psz_uri):
        return libvlc_media_slaves_add(self, i_type, i_priority, str_to_bytes(psz_uri))

    def slaves_clear(self):
        return libvlc_media_slaves_clear(self)

    def slaves_get(self, ppp_slaves):
        return libvlc_media_slaves_get(self, ppp_slaves)

    def subitems(self):
        return libvlc_media_subitems(self)


class MediaDiscoverer(_Ctype):
    def __new__(cls, ptr=_internal_guard):
        return _Constructor(cls, ptr)

    @memoize_parameterless
    def event_manager(self):
        return libvlc_media_discoverer_event_manager(self)

    def is_running(self):
        return libvlc_media_discoverer_is_running(self)

    def localized_name(self):
        return libvlc_media_discoverer_localized_name(self)

    def media_list(self):
        return libvlc_media_discoverer_media_list(self)

    def release(self):
        return libvlc_media_discoverer_release(self)

    def start(self):
        return libvlc_media_discoverer_start(self)

    def stop(self):
        return libvlc_media_discoverer_stop(self)


class MediaLibrary(_Ctype):
    def __new__(cls, ptr=_internal_guard):
        return _Constructor(cls, ptr)

    def load(self):
        return libvlc_media_library_load(self)

    def media_list(self):
        return libvlc_media_library_media_list(self)

    def release(self):
        return libvlc_media_library_release(self)

    def retain(self):
        return libvlc_media_library_retain(self)


class MediaList(_Ctype):
    def __new__(cls, *args):
        if args:
            i = args[0]
            if isinstance(i, _Ints):
                return _Constructor(cls, i)
            if isinstance(i, Instance):
                return i.media_list_new(*args[1:])

        o = get_default_instance().media_list_new(*args)
        return o

    def get_instance(self):
        return getattr(self, "_instance", None)

    def add_media(self, mrl):
        mrl = try_fspath(mrl)
        if isinstance(mrl, str):
            mrl = (self.get_instance() or get_default_instance()).media_new(mrl)
        return libvlc_media_list_add_media(self, mrl)

    def count(self):
        return libvlc_media_list_count(self)

    def __len__(self):
        return libvlc_media_list_count(self)

    @memoize_parameterless
    def event_manager(self):
        return libvlc_media_list_event_manager(self)

    def index_of_item(self, p_md):
        return libvlc_media_list_index_of_item(self, p_md)

    def insert_media(self, p_md, i_pos):
        return libvlc_media_list_insert_media(self, p_md, i_pos)

    def is_readonly(self):
        return libvlc_media_list_is_readonly(self)

    def item_at_index(self, i_pos):
        return libvlc_media_list_item_at_index(self, i_pos)

    def __getitem__(self, i):
        return libvlc_media_list_item_at_index(self, i)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def lock(self):
        return libvlc_media_list_lock(self)

    def media(self):
        return libvlc_media_list_media(self)

    def release(self):
        return libvlc_media_list_release(self)

    def remove_index(self, i_pos):
        return libvlc_media_list_remove_index(self, i_pos)

    def retain(self):
        return libvlc_media_list_retain(self)

    def set_media(self, p_md):
        return libvlc_media_list_set_media(self, p_md)

    def unlock(self):
        return libvlc_media_list_unlock(self)


class MediaListPlayer(_Ctype):

    def __new__(cls, arg=None):
        if arg is None:
            i = get_default_instance()
        elif isinstance(arg, Instance):
            i = arg
        elif isinstance(arg, _Ints):
            return _Constructor(cls, arg)
        else:
            raise TypeError("MediaListPlayer %r" % (arg,))

        return i.media_list_player_new()

    def get_instance(self):
        return self._instance

    @memoize_parameterless
    def event_manager(self):
        return libvlc_media_list_player_event_manager(self)

    def get_media_player(self):
        return libvlc_media_list_player_get_media_player(self)

    def get_state(self):
        return libvlc_media_list_player_get_state(self)

    def is_playing(self):
        return libvlc_media_list_player_is_playing(self)

    def __next__(self):
        return libvlc_media_list_player_next(self)

    def pause(self):
        return libvlc_media_list_player_pause(self)

    def play(self):
        return libvlc_media_list_player_play(self)

    def play_item(self, p_md):
        return libvlc_media_list_player_play_item(self, p_md)

    def play_item_at_index(self, i_index):
        return libvlc_media_list_player_play_item_at_index(self, i_index)

    def __getitem__(self, i):
        return libvlc_media_list_player_play_item_at_index(self, i)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def previous(self):
        return libvlc_media_list_player_previous(self)

    def release(self):
        return libvlc_media_list_player_release(self)

    def retain(self):
        return libvlc_media_list_player_retain(self)

    def set_media_list(self, p_mlist):
        return libvlc_media_list_player_set_media_list(self, p_mlist)

    def set_media_player(self, p_mi):
        return libvlc_media_list_player_set_media_player(self, p_mi)

    def set_pause(self, do_pause):
        return libvlc_media_list_player_set_pause(self, do_pause)

    def set_playback_mode(self, e_mode):
        return libvlc_media_list_player_set_playback_mode(self, e_mode)

    def stop(self):
        return libvlc_media_list_player_stop(self)


class MediaPlayer(_Ctype):

    def __new__(cls, *args):
        if len(args) == 1 and isinstance(args[0], _Ints):
            return _Constructor(cls, args[0])

        if args and isinstance(args[0], Instance):
            instance = args[0]
            args = args[1:]
        else:
            instance = get_default_instance()

        o = instance.media_player_new()
        if args:
            o.set_media(instance.media_new(*args))
        return o

    def get_instance(self):
        return self._instance

    def set_mrl(self, mrl, *options):
        m = self.get_instance().media_new(mrl, *options)
        self.set_media(m)
        return m

    def video_get_spu_description(self):
        return track_description_list(libvlc_video_get_spu_description(self))

    def video_get_track_description(self):
        return track_description_list(libvlc_video_get_track_description(self))

    def audio_get_track_description(self):
        return track_description_list(libvlc_audio_get_track_description(self))

    def get_full_title_descriptions(self):
        titleDescription_pp = ctypes.POINTER(TitleDescription)()
        n = libvlc_media_player_get_full_title_descriptions(
            self, ctypes.byref(titleDescription_pp)
        )
        info = ctypes.cast(
            titleDescription_pp, ctypes.POINTER(ctypes.POINTER(TitleDescription) * n)
        )
        try:
            contents = info.contents
        except ValueError:
            return None
        descr = (contents[i].contents for i in range(len(contents)))
        return descr

    def get_full_chapter_descriptions(self, i_chapters_of_title):
        chapterDescription_pp = ctypes.POINTER(ChapterDescription)()
        n = libvlc_media_player_get_full_chapter_descriptions(
            self, i_chapters_of_title, ctypes.byref(chapterDescription_pp)
        )
        info = ctypes.cast(
            chapterDescription_pp,
            ctypes.POINTER(ctypes.POINTER(ChapterDescription) * n),
        )
        try:
            contents = info.contents
        except ValueError:
            # Media not parsed, no info.
            return None
        descr = (contents[i].contents for i in range(len(contents)))
        return descr

    def video_get_size(self, num=0):
        r = libvlc_video_get_size(self, num)
        if isinstance(r, tuple) and len(r) == 2:
            return r
        else:
            raise VLCException("invalid video number (%s)" % (num,))

    def set_hwnd(self, drawable):
        if not isinstance(drawable, ctypes.c_void_p):
            drawable = ctypes.c_void_p(int(drawable))
        libvlc_media_player_set_hwnd(self, drawable)

    def video_get_width(self, num=0):
        return self.video_get_size(num)[0]

    def video_get_height(self, num=0):
        return self.video_get_size(num)[1]

    def video_get_cursor(self, num=0):
        r = libvlc_video_get_cursor(self, num)
        if isinstance(r, tuple) and len(r) == 2:
            return r
        raise VLCException("invalid video number (%s)" % (num,))

    def audio_get_channel(self):
        return libvlc_audio_get_channel(self)

    def audio_get_delay(self):
        return libvlc_audio_get_delay(self)

    def audio_get_mute(self):
        return libvlc_audio_get_mute(self)

    def audio_get_track(self):
        return libvlc_audio_get_track(self)

    def audio_get_track_count(self):
        return libvlc_audio_get_track_count(self)

    def audio_get_volume(self):
        return libvlc_audio_get_volume(self)

    def audio_output_device_enum(self):
        return libvlc_audio_output_device_enum(self)

    def audio_output_device_get(self):
        return libvlc_audio_output_device_get(self)

    def audio_output_device_set(self, module, device_id):
        return libvlc_audio_output_device_set(
            self, str_to_bytes(module), str_to_bytes(device_id)
        )

    def audio_output_get_device_type(self):
        return libvlc_audio_output_get_device_type(self)

    def audio_output_set(self, psz_name):
        return libvlc_audio_output_set(self, str_to_bytes(psz_name))

    def audio_output_set_device_type(self, device_type):
        return libvlc_audio_output_set_device_type(self, device_type)

    def audio_set_callbacks(self, play, pause, resume, flush, drain, opaque):
        return libvlc_audio_set_callbacks(
            self, play, pause, resume, flush, drain, opaque
        )

    def audio_set_channel(self, channel):
        return libvlc_audio_set_channel(self, channel)

    def audio_set_delay(self, i_delay):
        return libvlc_audio_set_delay(self, i_delay)

    def audio_set_format(self, format, rate, channels):
        return libvlc_audio_set_format(self, str_to_bytes(format), rate, channels)

    def audio_set_format_callbacks(self, setup, cleanup):
        return libvlc_audio_set_format_callbacks(self, setup, cleanup)

    def audio_set_mute(self, status):
        return libvlc_audio_set_mute(self, status)

    def audio_set_track(self, i_track):
        return libvlc_audio_set_track(self, i_track)

    def audio_set_volume(self, i_volume):
        return libvlc_audio_set_volume(self, i_volume)

    def audio_set_volume_callback(self, set_volume):
        return libvlc_audio_set_volume_callback(self, set_volume)

    def audio_toggle_mute(self):
        return libvlc_audio_toggle_mute(self)

    def get_fullscreen(self):
        return libvlc_get_fullscreen(self)

    def add_slave(self, i_type, psz_uri, b_select):
        return libvlc_media_player_add_slave(
            self, i_type, str_to_bytes(psz_uri), b_select
        )

    def can_pause(self):
        return libvlc_media_player_can_pause(self)

    @memoize_parameterless
    def event_manager(self):
        return libvlc_media_player_event_manager(self)

    def get_agl(self):
        return libvlc_media_player_get_agl(self)

    def get_chapter(self):
        return libvlc_media_player_get_chapter(self)

    def get_chapter_count(self):
        return libvlc_media_player_get_chapter_count(self)

    def get_chapter_count_for_title(self, i_title):
        return libvlc_media_player_get_chapter_count_for_title(self, i_title)

    def get_fps(self):
        return libvlc_media_player_get_fps(self)

    def get_hwnd(self):
        return libvlc_media_player_get_hwnd(self)

    def get_length(self):
        return libvlc_media_player_get_length(self)

    def get_media(self):
        return libvlc_media_player_get_media(self)

    def get_nsobject(self):
        return libvlc_media_player_get_nsobject(self)

    def get_position(self):
        return libvlc_media_player_get_position(self)

    def get_rate(self):
        return libvlc_media_player_get_rate(self)

    def get_role(self):
        return libvlc_media_player_get_role(self)

    def get_state(self):
        return libvlc_media_player_get_state(self)

    def get_time(self):
        return libvlc_media_player_get_time(self)

    def get_title(self):
        return libvlc_media_player_get_title(self)

    def get_title_count(self):
        return libvlc_media_player_get_title_count(self)

    def get_xwindow(self):
        return libvlc_media_player_get_xwindow(self)

    def has_vout(self):
        return libvlc_media_player_has_vout(self)

    def is_playing(self):
        return libvlc_media_player_is_playing(self)

    def is_seekable(self):
        return libvlc_media_player_is_seekable(self)

    def navigate(self, navigate):
        return libvlc_media_player_navigate(self, navigate)

    def next_chapter(self):
        return libvlc_media_player_next_chapter(self)

    def next_frame(self):
        return libvlc_media_player_next_frame(self)

    def pause(self):
        return libvlc_media_player_pause(self)

    def play(self):
        return libvlc_media_player_play(self)

    def previous_chapter(self):
        return libvlc_media_player_previous_chapter(self)

    def program_scrambled(self):
        return libvlc_media_player_program_scrambled(self)

    def release(self):
        return libvlc_media_player_release(self)

    def retain(self):
        return libvlc_media_player_retain(self)

    def set_agl(self, drawable):
        return libvlc_media_player_set_agl(self, drawable)

    def set_android_context(self, p_awindow_handler):
        return libvlc_media_player_set_android_context(self, p_awindow_handler)

    def set_chapter(self, i_chapter):
        return libvlc_media_player_set_chapter(self, i_chapter)

    def set_equalizer(self, p_equalizer):
        return libvlc_media_player_set_equalizer(self, p_equalizer)

    def set_evas_object(self, p_evas_object):
        return libvlc_media_player_set_evas_object(self, p_evas_object)

    def set_media(self, p_md):
        return libvlc_media_player_set_media(self, p_md)

    def set_nsobject(self, drawable):
        return libvlc_media_player_set_nsobject(self, drawable)

    def set_pause(self, do_pause):
        return libvlc_media_player_set_pause(self, do_pause)

    def set_position(self, f_pos):
        return libvlc_media_player_set_position(self, f_pos)

    def set_rate(self, rate):
        return libvlc_media_player_set_rate(self, rate)

    def set_renderer(self, p_item):
        return libvlc_media_player_set_renderer(self, p_item)

    def set_role(self, role):
        return libvlc_media_player_set_role(self, role)

    def set_time(self, i_time):
        return libvlc_media_player_set_time(self, i_time)

    def set_title(self, i_title):
        return libvlc_media_player_set_title(self, i_title)

    def set_video_title_display(self, position, timeout):
        return libvlc_media_player_set_video_title_display(self, position, timeout)

    def set_xwindow(self, drawable):
        return libvlc_media_player_set_xwindow(self, drawable)

    def stop(self):
        return libvlc_media_player_stop(self)

    def will_play(self):
        return libvlc_media_player_will_play(self)

    def set_fullscreen(self, b_fullscreen):
        return libvlc_set_fullscreen(self, b_fullscreen)

    def toggle_fullscreen(self):
        return libvlc_toggle_fullscreen(self)

    def toggle_teletext(self):
        return libvlc_toggle_teletext(self)

    def video_get_adjust_float(self, option):
        return libvlc_video_get_adjust_float(self, option)

    def video_get_adjust_int(self, option):
        return libvlc_video_get_adjust_int(self, option)

    def video_get_aspect_ratio(self):
        return libvlc_video_get_aspect_ratio(self)

    def video_get_chapter_description(self, i_title):
        return libvlc_video_get_chapter_description(self, i_title)

    def video_get_crop_geometry(self):
        return libvlc_video_get_crop_geometry(self)

    def video_get_logo_int(self, option):
        return libvlc_video_get_logo_int(self, option)

    def video_get_marquee_int(self, option):
        return libvlc_video_get_marquee_int(self, option)

    def video_get_marquee_string(self, option):
        return libvlc_video_get_marquee_string(self, option)

    def video_get_scale(self):
        return libvlc_video_get_scale(self)

    def video_get_spu(self):
        return libvlc_video_get_spu(self)

    def video_get_spu_count(self):
        return libvlc_video_get_spu_count(self)

    def video_get_spu_delay(self):
        return libvlc_video_get_spu_delay(self)

    def video_get_teletext(self):
        return libvlc_video_get_teletext(self)

    def video_get_title_description(self):
        return libvlc_video_get_title_description(self)

    def video_get_track(self):
        return libvlc_video_get_track(self)

    def video_get_track_count(self):
        return libvlc_video_get_track_count(self)

    def video_set_adjust_float(self, option, value):
        return libvlc_video_set_adjust_float(self, option, value)

    def video_set_adjust_int(self, option, value):
        return libvlc_video_set_adjust_int(self, option, value)

    def video_set_aspect_ratio(self, psz_aspect):
        return libvlc_video_set_aspect_ratio(self, str_to_bytes(psz_aspect))

    def video_set_callbacks(self, lock, unlock, display, opaque):
        return libvlc_video_set_callbacks(self, lock, unlock, display, opaque)

    def video_set_crop_geometry(self, psz_geometry):
        return libvlc_video_set_crop_geometry(self, str_to_bytes(psz_geometry))

    def video_set_deinterlace(self, psz_mode):
        return libvlc_video_set_deinterlace(self, str_to_bytes(psz_mode))

    def video_set_format(self, chroma, width, height, pitch):
        return libvlc_video_set_format(self, str_to_bytes(chroma), width, height, pitch)

    def video_set_format_callbacks(self, setup, cleanup):
        return libvlc_video_set_format_callbacks(self, setup, cleanup)

    def video_set_key_input(self, on):
        return libvlc_video_set_key_input(self, on)

    def video_set_logo_int(self, option, value):
        return libvlc_video_set_logo_int(self, option, value)

    def video_set_logo_string(self, option, psz_value):
        return libvlc_video_set_logo_string(self, option, str_to_bytes(psz_value))

    def video_set_marquee_int(self, option, i_val):
        return libvlc_video_set_marquee_int(self, option, i_val)

    def video_set_marquee_string(self, option, psz_text):
        return libvlc_video_set_marquee_string(self, option, str_to_bytes(psz_text))

    def video_set_mouse_input(self, on):
        return libvlc_video_set_mouse_input(self, on)

    def video_set_scale(self, f_factor):
        return libvlc_video_set_scale(self, f_factor)

    def video_set_spu(self, i_spu):
        return libvlc_video_set_spu(self, i_spu)

    def video_set_spu_delay(self, i_delay):
        return libvlc_video_set_spu_delay(self, i_delay)

    def video_set_subtitle_file(self, psz_subtitle):
        return libvlc_video_set_subtitle_file(self, str_to_bytes(psz_subtitle))

    def video_set_teletext(self, i_page):
        return libvlc_video_set_teletext(self, i_page)

    def video_set_track(self, i_track):
        return libvlc_video_set_track(self, i_track)

    def video_take_snapshot(self, num, psz_filepath, i_width, i_height):
        return libvlc_video_take_snapshot(
            self, num, str_to_bytes(psz_filepath), i_width, i_height
        )

    def video_update_viewpoint(self, p_viewpoint, b_absolute):
        return libvlc_video_update_viewpoint(self, p_viewpoint, b_absolute)


class Renderer(_Ctype):
    def __new__(cls, ptr=_internal_guard):
        return _Constructor(cls, ptr)

    def flags(self):
        return libvlc_renderer_item_flags(self)

    def hold(self):
        return libvlc_renderer_item_hold(self)

    def icon_uri(self):
        return libvlc_renderer_item_icon_uri(self)

    def name(self):
        return libvlc_renderer_item_name(self)

    def release(self):
        return libvlc_renderer_item_release(self)

    def type(self):
        return libvlc_renderer_item_type(self)


class RendererDiscoverer(_Ctype):
    def __new__(cls, ptr=_internal_guard):
        return _Constructor(cls, ptr)

    @memoize_parameterless
    def event_manager(self):
        return libvlc_renderer_discoverer_event_manager(self)

    def release(self):
        return libvlc_renderer_discoverer_release(self)

    def start(self):
        return libvlc_renderer_discoverer_start(self)

    def stop(self):
        return libvlc_renderer_discoverer_stop(self)


class AudioOutputChannel(_Enum):

    _enum_names_ = {
        -1: "Error",
        1: "Stereo",
        2: "RStereo",
        3: "Left",
        4: "Right",
        5: "Dolbys",
    }


AudioOutputChannel.Dolbys = AudioOutputChannel(5)
AudioOutputChannel.Error = AudioOutputChannel(-1)
AudioOutputChannel.Left = AudioOutputChannel(3)
AudioOutputChannel.RStereo = AudioOutputChannel(2)
AudioOutputChannel.Right = AudioOutputChannel(4)
AudioOutputChannel.Stereo = AudioOutputChannel(1)


class AudioOutputDeviceTypes(_Enum):

    _enum_names_ = {
        -1: "Error",
        1: "Mono",
        2: "Stereo",
        4: "_2F2R",
        5: "_3F2R",
        6: "_5_1",
        7: "_6_1",
        8: "_7_1",
        10: "SPDIF",
    }


AudioOutputDeviceTypes.Error = AudioOutputDeviceTypes(-1)
AudioOutputDeviceTypes.Mono = AudioOutputDeviceTypes(1)
AudioOutputDeviceTypes.SPDIF = AudioOutputDeviceTypes(10)
AudioOutputDeviceTypes.Stereo = AudioOutputDeviceTypes(2)
AudioOutputDeviceTypes._2F2R = AudioOutputDeviceTypes(4)
AudioOutputDeviceTypes._3F2R = AudioOutputDeviceTypes(5)
AudioOutputDeviceTypes._5_1 = AudioOutputDeviceTypes(6)
AudioOutputDeviceTypes._6_1 = AudioOutputDeviceTypes(7)
AudioOutputDeviceTypes._7_1 = AudioOutputDeviceTypes(8)


class DialogQuestionType(_Enum):

    _enum_names_ = {
        0: "DIALOG_QUESTION_NORMAL",
        1: "DIALOG_QUESTION_WARNING",
        2: "DIALOG_QUESTION_CRITICAL",
    }


DialogQuestionType.DIALOG_QUESTION_CRITICAL = DialogQuestionType(2)
DialogQuestionType.DIALOG_QUESTION_NORMAL = DialogQuestionType(0)
DialogQuestionType.DIALOG_QUESTION_WARNING = DialogQuestionType(1)


class EventType(_Enum):

    _enum_names_ = {
        0: "MediaMetaChanged",
        1: "MediaSubItemAdded",
        2: "MediaDurationChanged",
        3: "MediaParsedChanged",
        4: "MediaFreed",
        5: "MediaStateChanged",
        6: "MediaSubItemTreeAdded",
        0x100: "MediaPlayerMediaChanged",
        257: "MediaPlayerNothingSpecial",
        258: "MediaPlayerOpening",
        259: "MediaPlayerBuffering",
        260: "MediaPlayerPlaying",
        261: "MediaPlayerPaused",
        262: "MediaPlayerStopped",
        263: "MediaPlayerForward",
        264: "MediaPlayerBackward",
        265: "MediaPlayerEndReached",
        266: "MediaPlayerEncounteredError",
        267: "MediaPlayerTimeChanged",
        268: "MediaPlayerPositionChanged",
        269: "MediaPlayerSeekableChanged",
        270: "MediaPlayerPausableChanged",
        271: "MediaPlayerTitleChanged",
        272: "MediaPlayerSnapshotTaken",
        273: "MediaPlayerLengthChanged",
        274: "MediaPlayerVout",
        275: "MediaPlayerScrambledChanged",
        276: "MediaPlayerESAdded",
        277: "MediaPlayerESDeleted",
        278: "MediaPlayerESSelected",
        279: "MediaPlayerCorked",
        280: "MediaPlayerUncorked",
        281: "MediaPlayerMuted",
        282: "MediaPlayerUnmuted",
        283: "MediaPlayerAudioVolume",
        284: "MediaPlayerAudioDevice",
        285: "MediaPlayerChapterChanged",
        0x200: "MediaListItemAdded",
        513: "MediaListWillAddItem",
        514: "MediaListItemDeleted",
        515: "MediaListWillDeleteItem",
        516: "MediaListEndReached",
        0x300: "MediaListViewItemAdded",
        769: "MediaListViewWillAddItem",
        770: "MediaListViewItemDeleted",
        771: "MediaListViewWillDeleteItem",
        0x400: "MediaListPlayerPlayed",
        1025: "MediaListPlayerNextItemSet",
        1026: "MediaListPlayerStopped",
        0x500: "MediaDiscovererStarted",
        1281: "MediaDiscovererEnded",
        1282: "RendererDiscovererItemAdded",
        1283: "RendererDiscovererItemDeleted",
        0x600: "VlmMediaAdded",
        1537: "VlmMediaRemoved",
        1538: "VlmMediaChanged",
        1539: "VlmMediaInstanceStarted",
        1540: "VlmMediaInstanceStopped",
        1541: "VlmMediaInstanceStatusInit",
        1542: "VlmMediaInstanceStatusOpening",
        1543: "VlmMediaInstanceStatusPlaying",
        1544: "VlmMediaInstanceStatusPause",
        1545: "VlmMediaInstanceStatusEnd",
        1546: "VlmMediaInstanceStatusError",
    }


EventType.MediaDiscovererEnded = EventType(1281)
EventType.MediaDiscovererStarted = EventType(0x500)
EventType.MediaDurationChanged = EventType(2)
EventType.MediaFreed = EventType(4)
EventType.MediaListEndReached = EventType(516)
EventType.MediaListItemAdded = EventType(0x200)
EventType.MediaListItemDeleted = EventType(514)
EventType.MediaListPlayerNextItemSet = EventType(1025)
EventType.MediaListPlayerPlayed = EventType(0x400)
EventType.MediaListPlayerStopped = EventType(1026)
EventType.MediaListViewItemAdded = EventType(0x300)
EventType.MediaListViewItemDeleted = EventType(770)
EventType.MediaListViewWillAddItem = EventType(769)
EventType.MediaListViewWillDeleteItem = EventType(771)
EventType.MediaListWillAddItem = EventType(513)
EventType.MediaListWillDeleteItem = EventType(515)
EventType.MediaMetaChanged = EventType(0)
EventType.MediaParsedChanged = EventType(3)
EventType.MediaPlayerAudioDevice = EventType(284)
EventType.MediaPlayerAudioVolume = EventType(283)
EventType.MediaPlayerBackward = EventType(264)
EventType.MediaPlayerBuffering = EventType(259)
EventType.MediaPlayerChapterChanged = EventType(285)
EventType.MediaPlayerCorked = EventType(279)
EventType.MediaPlayerESAdded = EventType(276)
EventType.MediaPlayerESDeleted = EventType(277)
EventType.MediaPlayerESSelected = EventType(278)
EventType.MediaPlayerEncounteredError = EventType(266)
EventType.MediaPlayerEndReached = EventType(265)
EventType.MediaPlayerForward = EventType(263)
EventType.MediaPlayerLengthChanged = EventType(273)
EventType.MediaPlayerMediaChanged = EventType(0x100)
EventType.MediaPlayerMuted = EventType(281)
EventType.MediaPlayerNothingSpecial = EventType(257)
EventType.MediaPlayerOpening = EventType(258)
EventType.MediaPlayerPausableChanged = EventType(270)
EventType.MediaPlayerPaused = EventType(261)
EventType.MediaPlayerPlaying = EventType(260)
EventType.MediaPlayerPositionChanged = EventType(268)
EventType.MediaPlayerScrambledChanged = EventType(275)
EventType.MediaPlayerSeekableChanged = EventType(269)
EventType.MediaPlayerSnapshotTaken = EventType(272)
EventType.MediaPlayerStopped = EventType(262)
EventType.MediaPlayerTimeChanged = EventType(267)
EventType.MediaPlayerTitleChanged = EventType(271)
EventType.MediaPlayerUncorked = EventType(280)
EventType.MediaPlayerUnmuted = EventType(282)
EventType.MediaPlayerVout = EventType(274)
EventType.MediaStateChanged = EventType(5)
EventType.MediaSubItemAdded = EventType(1)
EventType.MediaSubItemTreeAdded = EventType(6)
EventType.RendererDiscovererItemAdded = EventType(1282)
EventType.RendererDiscovererItemDeleted = EventType(1283)
EventType.VlmMediaAdded = EventType(0x600)
EventType.VlmMediaChanged = EventType(1538)
EventType.VlmMediaInstanceStarted = EventType(1539)
EventType.VlmMediaInstanceStatusEnd = EventType(1545)
EventType.VlmMediaInstanceStatusError = EventType(1546)
EventType.VlmMediaInstanceStatusInit = EventType(1541)
EventType.VlmMediaInstanceStatusOpening = EventType(1542)
EventType.VlmMediaInstanceStatusPause = EventType(1544)
EventType.VlmMediaInstanceStatusPlaying = EventType(1543)
EventType.VlmMediaInstanceStopped = EventType(1540)
EventType.VlmMediaRemoved = EventType(1537)


class LogLevel(_Enum):

    _enum_names_ = {
        0: "DEBUG",
        2: "NOTICE",
        3: "WARNING",
        4: "ERROR",
    }


LogLevel.DEBUG = LogLevel(0)
LogLevel.ERROR = LogLevel(4)
LogLevel.NOTICE = LogLevel(2)
LogLevel.WARNING = LogLevel(3)


class MediaDiscovererCategory(_Enum):

    _enum_names_ = {
        0: "devices",
        1: "lan",
        2: "podcasts",
        3: "localdirs",
    }


MediaDiscovererCategory.devices = MediaDiscovererCategory(0)
MediaDiscovererCategory.lan = MediaDiscovererCategory(1)
MediaDiscovererCategory.localdirs = MediaDiscovererCategory(3)
MediaDiscovererCategory.podcasts = MediaDiscovererCategory(2)


class MediaParseFlag(_Enum):

    _enum_names_ = {
        0x0: "local",
        0x1: "network",
        0x2: "fetch_local",
        0x4: "fetch_network",
        0x8: "do_interact",
    }


MediaParseFlag.do_interact = MediaParseFlag(0x8)
MediaParseFlag.fetch_local = MediaParseFlag(0x2)
MediaParseFlag.fetch_network = MediaParseFlag(0x4)
MediaParseFlag.local = MediaParseFlag(0x0)
MediaParseFlag.network = MediaParseFlag(0x1)


class MediaParsedStatus(_Enum):

    _enum_names_ = {
        1: "skipped",
        2: "failed",
        3: "timeout",
        4: "done",
    }


MediaParsedStatus.done = MediaParsedStatus(4)
MediaParsedStatus.failed = MediaParsedStatus(2)
MediaParsedStatus.skipped = MediaParsedStatus(1)
MediaParsedStatus.timeout = MediaParsedStatus(3)


class MediaPlayerRole(_Enum):

    _enum_names_ = {
        0: "_None",
        1: "Music",
        2: "Video",
        3: "Communication",
        4: "Game",
        5: "Notification",
        6: "Animation",
        7: "Production",
        8: "Accessibility",
        9: "Test",
    }


MediaPlayerRole.Accessibility = MediaPlayerRole(8)
MediaPlayerRole.Animation = MediaPlayerRole(6)
MediaPlayerRole.Communication = MediaPlayerRole(3)
MediaPlayerRole.Game = MediaPlayerRole(4)
MediaPlayerRole.Music = MediaPlayerRole(1)
MediaPlayerRole.Notification = MediaPlayerRole(5)
MediaPlayerRole.Production = MediaPlayerRole(7)
MediaPlayerRole.Test = MediaPlayerRole(9)
MediaPlayerRole.Video = MediaPlayerRole(2)
MediaPlayerRole._None = MediaPlayerRole(0)


class MediaSlaveType(_Enum):

    _enum_names_ = {
        0: "subtitle",
        1: "audio",
    }


MediaSlaveType.audio = MediaSlaveType(1)
MediaSlaveType.subtitle = MediaSlaveType(0)


class MediaType(_Enum):

    _enum_names_ = {
        0: "unknown",
        1: "file",
        2: "directory",
        3: "disc",
        4: "stream",
        5: "playlist",
    }


MediaType.directory = MediaType(2)
MediaType.disc = MediaType(3)
MediaType.file = MediaType(1)
MediaType.playlist = MediaType(5)
MediaType.stream = MediaType(4)
MediaType.unknown = MediaType(0)


class Meta(_Enum):

    _enum_names_ = {
        0: "Title",
        1: "Artist",
        2: "Genre",
        3: "Copyright",
        4: "Album",
        5: "TrackNumber",
        6: "Description",
        7: "Rating",
        8: "Date",
        9: "Setting",
        10: "URL",
        11: "Language",
        12: "NowPlaying",
        13: "Publisher",
        14: "EncodedBy",
        15: "ArtworkURL",
        16: "TrackID",
        17: "TrackTotal",
        18: "Director",
        19: "Season",
        20: "Episode",
        21: "ShowName",
        22: "Actors",
        23: "AlbumArtist",
        24: "DiscNumber",
        25: "DiscTotal",
    }


Meta.Actors = Meta(22)
Meta.Album = Meta(4)
Meta.AlbumArtist = Meta(23)
Meta.Artist = Meta(1)
Meta.ArtworkURL = Meta(15)
Meta.Copyright = Meta(3)
Meta.Date = Meta(8)
Meta.Description = Meta(6)
Meta.Director = Meta(18)
Meta.DiscNumber = Meta(24)
Meta.DiscTotal = Meta(25)
Meta.EncodedBy = Meta(14)
Meta.Episode = Meta(20)
Meta.Genre = Meta(2)
Meta.Language = Meta(11)
Meta.NowPlaying = Meta(12)
Meta.Publisher = Meta(13)
Meta.Rating = Meta(7)
Meta.Season = Meta(19)
Meta.Setting = Meta(9)
Meta.ShowName = Meta(21)
Meta.Title = Meta(0)
Meta.TrackID = Meta(16)
Meta.TrackNumber = Meta(5)
Meta.TrackTotal = Meta(17)
Meta.URL = Meta(10)


class NavigateMode(_Enum):

    _enum_names_ = {
        0: "activate",
        1: "up",
        2: "down",
        3: "left",
        4: "right",
        5: "popup",
    }


NavigateMode.activate = NavigateMode(0)
NavigateMode.down = NavigateMode(2)
NavigateMode.left = NavigateMode(3)
NavigateMode.popup = NavigateMode(5)
NavigateMode.right = NavigateMode(4)
NavigateMode.up = NavigateMode(1)


class PlaybackMode(_Enum):

    _enum_names_ = {
        0: "default",
        1: "loop",
        2: "repeat",
    }


PlaybackMode.default = PlaybackMode(0)
PlaybackMode.loop = PlaybackMode(1)
PlaybackMode.repeat = PlaybackMode(2)


class Position(_Enum):

    _enum_names_ = {
        -1: "disable",
        0: "center",
        1: "left",
        2: "right",
        3: "top",
        4: "top_left",
        5: "top_right",
        6: "bottom",
        7: "bottom_left",
        8: "bottom_right",
    }


Position.bottom = Position(6)
Position.bottom_left = Position(7)
Position.bottom_right = Position(8)
Position.center = Position(0)
Position.disable = Position(-1)
Position.left = Position(1)
Position.right = Position(2)
Position.top = Position(3)
Position.top_left = Position(4)
Position.top_right = Position(5)


class State(_Enum):

    _enum_names_ = {
        0: "NothingSpecial",
        1: "Opening",
        2: "Buffering",
        3: "Playing",
        4: "Paused",
        5: "Stopped",
        6: "Ended",
        7: "Error",
    }


State.Buffering = State(2)
State.Ended = State(6)
State.Error = State(7)
State.NothingSpecial = State(0)
State.Opening = State(1)
State.Paused = State(4)
State.Playing = State(3)
State.Stopped = State(5)


class TeletextKey(_Enum):

    _enum_names_ = {
        7471104: "red",
        6750208: "green",
        7929856: "yellow",
        6422528: "blue",
        6881280: "index",
    }


TeletextKey.blue = TeletextKey(6422528)
TeletextKey.green = TeletextKey(6750208)
TeletextKey.index = TeletextKey(6881280)
TeletextKey.red = TeletextKey(7471104)
TeletextKey.yellow = TeletextKey(7929856)


class TrackType(_Enum):

    _enum_names_ = {
        -1: "unknown",
        0: "audio",
        1: "video",
        2: "ext",
    }


TrackType.audio = TrackType(0)
TrackType.ext = TrackType(2)
TrackType.unknown = TrackType(-1)
TrackType.video = TrackType(1)


class VideoAdjustOption(_Enum):

    _enum_names_ = {
        0: "Enable",
        1: "Contrast",
        2: "Brightness",
        3: "Hue",
        4: "Saturation",
        5: "Gamma",
    }


VideoAdjustOption.Brightness = VideoAdjustOption(2)
VideoAdjustOption.Contrast = VideoAdjustOption(1)
VideoAdjustOption.Enable = VideoAdjustOption(0)
VideoAdjustOption.Gamma = VideoAdjustOption(5)
VideoAdjustOption.Hue = VideoAdjustOption(3)
VideoAdjustOption.Saturation = VideoAdjustOption(4)


class VideoLogoOption(_Enum):

    _enum_names_ = {
        0: "logo_enable",
        1: "logo_file",
        2: "logo_x",
        3: "logo_y",
        4: "logo_delay",
        5: "logo_repeat",
        6: "logo_opacity",
        7: "logo_position",
    }


VideoLogoOption.logo_delay = VideoLogoOption(4)
VideoLogoOption.logo_enable = VideoLogoOption(0)
VideoLogoOption.logo_file = VideoLogoOption(1)
VideoLogoOption.logo_opacity = VideoLogoOption(6)
VideoLogoOption.logo_position = VideoLogoOption(7)
VideoLogoOption.logo_repeat = VideoLogoOption(5)
VideoLogoOption.logo_x = VideoLogoOption(2)
VideoLogoOption.logo_y = VideoLogoOption(3)


class VideoMarqueeOption(_Enum):

    _enum_names_ = {
        0: "Enable",
        1: "Text",
        2: "Color",
        3: "Opacity",
        4: "Position",
        5: "Refresh",
        6: "Size",
        7: "Timeout",
        8: "X",
        9: "Y",
    }


VideoMarqueeOption.Color = VideoMarqueeOption(2)
VideoMarqueeOption.Enable = VideoMarqueeOption(0)
VideoMarqueeOption.Opacity = VideoMarqueeOption(3)
VideoMarqueeOption.Position = VideoMarqueeOption(4)
VideoMarqueeOption.Refresh = VideoMarqueeOption(5)
VideoMarqueeOption.Size = VideoMarqueeOption(6)
VideoMarqueeOption.Text = VideoMarqueeOption(1)
VideoMarqueeOption.Timeout = VideoMarqueeOption(7)
VideoMarqueeOption.X = VideoMarqueeOption(8)
VideoMarqueeOption.Y = VideoMarqueeOption(9)


class VideoOrient(_Enum):

    _enum_names_ = {
        0: "top_left",
        1: "top_right",
        2: "bottom_left",
        3: "bottom_right",
        4: "left_top",
        5: "left_bottom",
        6: "right_top",
        7: "right_bottom",
    }


VideoOrient.bottom_left = VideoOrient(2)
VideoOrient.bottom_right = VideoOrient(3)
VideoOrient.left_bottom = VideoOrient(5)
VideoOrient.left_top = VideoOrient(4)
VideoOrient.right_bottom = VideoOrient(7)
VideoOrient.right_top = VideoOrient(6)
VideoOrient.top_left = VideoOrient(0)
VideoOrient.top_right = VideoOrient(1)


class VideoProjection(_Enum):

    _enum_names_ = {
        0: "rectangular",
        1: "equirectangular",
        0x100: "cubemap_layout_standard",
    }


VideoProjection.cubemap_layout_standard = VideoProjection(0x100)
VideoProjection.equirectangular = VideoProjection(1)
VideoProjection.rectangular = VideoProjection(0)


class ModuleDescription(_Cstruct):
    """Description of a module."""

    pass


ModuleDescription._fields_ = (
    ("name", ctypes.c_char_p),
    ("shortname", ctypes.c_char_p),
    ("longname", ctypes.c_char_p),
    ("help", ctypes.c_char_p),
    ("next", ctypes.POINTER(ModuleDescription)),
)


class RdDescription(_Cstruct):

    pass


RdDescription._fields_ = (
    ("name", ctypes.c_char_p),
    ("longname", ctypes.c_char_p),
)


class MediaStats(_Cstruct):
    pass


MediaStats._fields_ = (
    ("read_bytes", ctypes.c_int),
    ("input_bitrate", ctypes.c_float),
    ("demux_read_bytes", ctypes.c_int),
    ("demux_bitrate", ctypes.c_float),
    ("demux_corrupted", ctypes.c_int),
    ("demux_discontinuity", ctypes.c_int),
    ("decoded_video", ctypes.c_int),
    ("decoded_audio", ctypes.c_int),
    ("displayed_pictures", ctypes.c_int),
    ("lost_pictures", ctypes.c_int),
    ("played_abuffers", ctypes.c_int),
    ("lost_abuffers", ctypes.c_int),
    ("sent_packets", ctypes.c_int),
    ("sent_bytes", ctypes.c_int),
    ("send_bitrate", ctypes.c_float),
)


class MediaTrackInfo(_Cstruct):
    class U(ctypes.Union):
        class Audio(_Cstruct):
            pass

        Audio._fields_ = (
            ("channels", ctypes.c_uint),
            ("rate", ctypes.c_uint),
        )

        class Video(_Cstruct):
            pass

        Video._fields_ = (
            ("height", ctypes.c_uint),
            ("width", ctypes.c_uint),
        )

        pass

    U._fields_ = (
        ("audio", U.Audio),
        ("video", U.Video),
    )

    pass


MediaTrackInfo._fields_ = (
    ("codec", ctypes.c_uint32),
    ("id", ctypes.c_int),
    ("type", TrackType),
    ("profile", ctypes.c_int),
    ("level", ctypes.c_int),
    ("u", MediaTrackInfo.U),
)


class AudioTrack(_Cstruct):
    pass


AudioTrack._fields_ = (
    ("channels", ctypes.c_uint),
    ("rate", ctypes.c_uint),
)


class VideoViewpoint(_Cstruct):

    pass


VideoViewpoint._fields_ = (
    ("yaw", ctypes.c_float),
    ("pitch", ctypes.c_float),
    ("roll", ctypes.c_float),
    ("field_of_view", ctypes.c_float),
)


class VideoTrack(_Cstruct):
    pass


VideoTrack._fields_ = (
    ("height", ctypes.c_uint),
    ("width", ctypes.c_uint),
    ("sar_num", ctypes.c_uint),
    ("sar_den", ctypes.c_uint),
    ("frame_rate_num", ctypes.c_uint),
    ("frame_rate_den", ctypes.c_uint),
    ("orientation", VideoOrient),
    ("projection", VideoProjection),
    ("pose", VideoViewpoint),
)


class SubtitleTrack(_Cstruct):
    pass


SubtitleTrack._fields_ = (("encoding", ctypes.c_char_p),)


class MediaTrack(_Cstruct):
    pass


MediaTrack._fields_ = (
    ("codec", ctypes.c_uint32),
    ("original_fourcc", ctypes.c_uint32),
    ("id", ctypes.c_int),
    ("type", TrackType),
    ("profile", ctypes.c_int),
    ("level", ctypes.c_int),
    ("audio", ctypes.POINTER(AudioTrack)),
    ("video", ctypes.POINTER(VideoTrack)),
    ("subtitle", ctypes.POINTER(SubtitleTrack)),
    ("bitrate", ctypes.c_uint),
    ("language", ctypes.c_char_p),
    ("description", ctypes.c_char_p),
)


class MediaSlave(_Cstruct):

    pass


MediaSlave._fields_ = (
    ("uri", ctypes.c_char_p),
    ("type", MediaSlaveType),
    ("priority", ctypes.c_uint),
)


class TrackDescription(_Cstruct):

    pass


TrackDescription._fields_ = (
    ("id", ctypes.c_int),
    ("name", ctypes.c_char_p),
    ("next", ctypes.POINTER(TrackDescription)),
)


class TitleDescription(_Cstruct):
    pass


TitleDescription._fields_ = (
    ("duration", ctypes.c_int64),
    ("name", ctypes.c_char_p),
    ("flags", ctypes.c_uint),
)


class ChapterDescription(_Cstruct):

    pass


ChapterDescription._fields_ = (
    ("time_offset", ctypes.c_int64),
    ("duration", ctypes.c_int64),
    ("name", ctypes.c_char_p),
)


class AudioOutput(_Cstruct):

    pass


AudioOutput._fields_ = (
    ("name", ctypes.c_char_p),
    ("description", ctypes.c_char_p),
    ("next", ctypes.POINTER(AudioOutput)),
)


class AudioOutputDevice(_Cstruct):

    pass


AudioOutputDevice._fields_ = (
    ("next", ctypes.POINTER(AudioOutputDevice)),
    ("device", ctypes.c_char_p),
    ("description", ctypes.c_char_p),
)


class MediaDiscovererDescription(_Cstruct):

    pass


MediaDiscovererDescription._fields_ = (
    ("name", ctypes.c_char_p),
    ("longname", ctypes.c_char_p),
    ("cat", MediaDiscovererCategory),
)


class Event(_Cstruct):

    class U(ctypes.Union):

        class MediaMetaChanged(_Cstruct):
            pass

        MediaMetaChanged._fields_ = (("meta_type", Meta),)

        class MediaSubitemAdded(_Cstruct):
            pass

        MediaSubitemAdded._fields_ = ()

        class MediaDurationChanged(_Cstruct):
            pass

        MediaDurationChanged._fields_ = (("new_duration", ctypes.c_int64),)

        class MediaParsedChanged(_Cstruct):
            pass

        MediaParsedChanged._fields_ = (("new_status", ctypes.c_int),)

        class MediaFreed(_Cstruct):
            pass

        MediaFreed._fields_ = ()

        class MediaStateChanged(_Cstruct):
            pass

        MediaStateChanged._fields_ = (("new_state", ctypes.c_int),)

        class MediaSubitemtreeAdded(_Cstruct):
            pass

        MediaSubitemtreeAdded._fields_ = ()

        class MediaPlayerBuffering(_Cstruct):
            pass

        MediaPlayerBuffering._fields_ = (("new_cache", ctypes.c_float),)

        class MediaPlayerChapterChanged(_Cstruct):
            pass

        MediaPlayerChapterChanged._fields_ = (("new_chapter", ctypes.c_int),)

        class MediaPlayerPositionChanged(_Cstruct):
            pass

        MediaPlayerPositionChanged._fields_ = (("new_position", ctypes.c_float),)

        class MediaPlayerTimeChanged(_Cstruct):
            pass

        MediaPlayerTimeChanged._fields_ = (("new_time", ctypes.c_longlong),)

        class MediaPlayerTitleChanged(_Cstruct):
            pass

        MediaPlayerTitleChanged._fields_ = (("new_title", ctypes.c_int),)

        class MediaPlayerSeekableChanged(_Cstruct):
            pass

        MediaPlayerSeekableChanged._fields_ = (("new_seekable", ctypes.c_int),)

        class MediaPlayerPausableChanged(_Cstruct):
            pass

        MediaPlayerPausableChanged._fields_ = (("new_pausable", ctypes.c_int),)

        class MediaPlayerScrambledChanged(_Cstruct):
            pass

        MediaPlayerScrambledChanged._fields_ = (("new_scrambled", ctypes.c_int),)

        class MediaPlayerVout(_Cstruct):
            pass

        MediaPlayerVout._fields_ = (("new_count", ctypes.c_int),)

        class MediaListItemAdded(_Cstruct):
            pass

        MediaListItemAdded._fields_ = (("index", ctypes.c_int),)

        class MediaListWillAddItem(_Cstruct):
            pass

        MediaListWillAddItem._fields_ = (("index", ctypes.c_int),)

        class MediaListItemDeleted(_Cstruct):
            pass

        MediaListItemDeleted._fields_ = (("index", ctypes.c_int),)

        class MediaListWillDeleteItem(_Cstruct):
            pass

        MediaListWillDeleteItem._fields_ = (("index", ctypes.c_int),)

        class MediaListPlayerNextItemSet(_Cstruct):
            pass

        MediaListPlayerNextItemSet._fields_ = ()

        class MediaPlayerSnapshotTaken(_Cstruct):
            pass

        MediaPlayerSnapshotTaken._fields_ = (("filename", ctypes.c_char_p),)

        class MediaPlayerLengthChanged(_Cstruct):
            pass

        MediaPlayerLengthChanged._fields_ = (("new_length", ctypes.c_longlong),)

        class VlmMediaEvent(_Cstruct):
            pass

        VlmMediaEvent._fields_ = (
            ("media_name", ctypes.c_char_p),
            ("instance_name", ctypes.c_char_p),
        )

        class MediaPlayerMediaChanged(_Cstruct):
            pass

        MediaPlayerMediaChanged._fields_ = ()

        class MediaPlayerEsChanged(_Cstruct):
            pass

        MediaPlayerEsChanged._fields_ = (
            ("type", TrackType),
            ("id", ctypes.c_int),
        )

        class MediaPlayerAudioVolume(_Cstruct):
            pass

        MediaPlayerAudioVolume._fields_ = (("volume", ctypes.c_float),)

        class MediaPlayerAudioDevice(_Cstruct):
            pass

        MediaPlayerAudioDevice._fields_ = (("device", ctypes.c_char_p),)

        class RendererDiscovererItemAdded(_Cstruct):
            pass

        RendererDiscovererItemAdded._fields_ = ()

        class RendererDiscovererItemDeleted(_Cstruct):
            pass

        RendererDiscovererItemDeleted._fields_ = ()

        pass

    U._fields_ = (
        ("media_meta_changed", U.MediaMetaChanged),
        ("media_subitem_added", U.MediaSubitemAdded),
        ("media_duration_changed", U.MediaDurationChanged),
        ("media_parsed_changed", U.MediaParsedChanged),
        ("media_freed", U.MediaFreed),
        ("media_state_changed", U.MediaStateChanged),
        ("media_subitemtree_added", U.MediaSubitemtreeAdded),
        ("media_player_buffering", U.MediaPlayerBuffering),
        ("media_player_chapter_changed", U.MediaPlayerChapterChanged),
        ("media_player_position_changed", U.MediaPlayerPositionChanged),
        ("media_player_time_changed", U.MediaPlayerTimeChanged),
        ("media_player_title_changed", U.MediaPlayerTitleChanged),
        ("media_player_seekable_changed", U.MediaPlayerSeekableChanged),
        ("media_player_pausable_changed", U.MediaPlayerPausableChanged),
        ("media_player_scrambled_changed", U.MediaPlayerScrambledChanged),
        ("media_player_vout", U.MediaPlayerVout),
        ("media_list_item_added", U.MediaListItemAdded),
        ("media_list_will_add_item", U.MediaListWillAddItem),
        ("media_list_item_deleted", U.MediaListItemDeleted),
        ("media_list_will_delete_item", U.MediaListWillDeleteItem),
        ("media_list_player_next_item_set", U.MediaListPlayerNextItemSet),
        ("media_player_snapshot_taken", U.MediaPlayerSnapshotTaken),
        ("media_player_length_changed", U.MediaPlayerLengthChanged),
        ("vlm_media_event", U.VlmMediaEvent),
        ("media_player_media_changed", U.MediaPlayerMediaChanged),
        ("media_player_es_changed", U.MediaPlayerEsChanged),
        ("media_player_audio_volume", U.MediaPlayerAudioVolume),
        ("media_player_audio_device", U.MediaPlayerAudioDevice),
        ("renderer_discoverer_item_added", U.RendererDiscovererItemAdded),
        ("renderer_discoverer_item_deleted", U.RendererDiscovererItemDeleted),
    )

    pass


class EventUnion(ctypes.Union):

    _fields_ = [
        ("meta_type", ctypes.c_uint),
        ("new_child", ctypes.c_uint),
        ("new_duration", ctypes.c_longlong),
        ("new_status", ctypes.c_int),
        ("media", ctypes.c_void_p),
        ("new_state", ctypes.c_uint),
        ("new_cache", ctypes.c_float),
        ("new_position", ctypes.c_float),
        ("new_time", ctypes.c_longlong),
        ("new_title", ctypes.c_int),
        ("new_seekable", ctypes.c_longlong),
        ("new_pausable", ctypes.c_longlong),
        ("new_scrambled", ctypes.c_longlong),
        ("new_count", ctypes.c_longlong),
        ("filename", ctypes.c_char_p),
        ("new_length", ctypes.c_longlong),
    ]


Event._fields_ = (
    ("type", EventType),
    ("obj", ctypes.c_void_p),
    ("u", EventUnion),
)


class DialogCbs(_Cstruct):

    PfDisplayError = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p
    )
    PfDisplayError.__doc__ = """ """

    PfDisplayLogin = ctypes.CFUNCTYPE(
        None,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_bool,
    )
    PfDisplayLogin.__doc__ = """ """

    PfDisplayQuestion = ctypes.CFUNCTYPE(
        None,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        DialogQuestionType,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    PfDisplayQuestion.__doc__ = """ """

    PfDisplayProgress = ctypes.CFUNCTYPE(
        None,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_bool,
        ctypes.c_float,
        ctypes.c_char_p,
    )
    PfDisplayProgress.__doc__ = """ """

    PfCancel = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
    PfCancel.__doc__ = """ """

    PfUpdateProgress = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_char_p
    )
    PfUpdateProgress.__doc__ = """ """

    pass


DialogCbs._fields_ = (
    ("pf_display_error", DialogCbs.PfDisplayError),
    ("pf_display_login", DialogCbs.PfDisplayLogin),
    ("pf_display_question", DialogCbs.PfDisplayQuestion),
    ("pf_display_progress", DialogCbs.PfDisplayProgress),
    ("pf_cancel", DialogCbs.PfCancel),
    ("pf_update_progress", DialogCbs.PfUpdateProgress),
)


class LogMessage(_Cstruct):
    pass


LogMessage._fields_ = (
    ("severity", ctypes.c_int),
    ("type", ctypes.c_char_p),
    ("name", ctypes.c_char_p),
    ("header", ctypes.c_char_p),
    ("message", ctypes.c_char_p),
)


class AudioCleanupCb(ctypes.c_void_p):

    pass


class AudioDrainCb(ctypes.c_void_p):

    pass


class AudioFlushCb(ctypes.c_void_p):

    pass


class AudioPauseCb(ctypes.c_void_p):

    pass


class AudioPlayCb(ctypes.c_void_p):

    pass


class AudioResumeCb(ctypes.c_void_p):

    pass


class AudioSetVolumeCb(ctypes.c_void_p):

    pass


class AudioSetupCb(ctypes.c_void_p):

    pass


class Callback(ctypes.c_void_p):

    pass


class LogCb(ctypes.c_void_p):

    pass


class MediaCloseCb(ctypes.c_void_p):

    pass


class MediaOpenCb(ctypes.c_void_p):

    pass


class MediaReadCb(ctypes.c_void_p):

    pass


class MediaSeekCb(ctypes.c_void_p):

    pass


class VideoCleanupCb(ctypes.c_void_p):

    pass


class VideoDisplayCb(ctypes.c_void_p):

    pass


class VideoFormatCb(ctypes.c_void_p):

    pass


class VideoLockCb(ctypes.c_void_p):

    pass


class VideoUnlockCb(ctypes.c_void_p):

    pass


class CallbackDecorators(object):

    AudioCleanupCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
    AudioCleanupCb.__doc__ = """ """
    AudioDrainCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
    AudioDrainCb.__doc__ = """ """
    AudioFlushCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
    AudioFlushCb.__doc__ = """ """
    AudioPauseCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
    AudioPauseCb.__doc__ = """ """
    AudioPlayCb = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_int64
    )
    AudioPlayCb.__doc__ = """ """

    AudioResumeCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
    AudioResumeCb.__doc__ = """ """
    AudioSetVolumeCb = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_float, ctypes.c_bool
    )
    AudioSetVolumeCb.__doc__ = """ """

    AudioSetupCb = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    )
    AudioSetupCb.__doc__ = """ """

    Callback = ctypes.CFUNCTYPE(None, ctypes.POINTER(Event), ctypes.c_void_p)
    Callback.__doc__ = """ """

    LogCb = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_int, Log_ptr, ctypes.c_char_p, ctypes.c_void_p
    )
    LogCb.__doc__ = """ """

    MediaCloseCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
    MediaCloseCb.__doc__ = """ """

    MediaOpenCb = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_uint64),
    )
    MediaOpenCb.__doc__ = """ """

    MediaReadCb = ctypes.CFUNCTYPE(
        ctypes.c_ssize_t,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_size_t,
    )
    MediaReadCb.__doc__ = """ """

    MediaSeekCb = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint64)
    MediaSeekCb.__doc__ = """ """

    VideoCleanupCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
    VideoCleanupCb.__doc__ = """ """

    VideoDisplayCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
    VideoDisplayCb.__doc__ = """ """

    VideoFormatCb = ctypes.CFUNCTYPE(
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    )
    VideoFormatCb.__doc__ = """ """
    VideoLockCb = ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
    )
    VideoLockCb.__doc__ = """ """
    VideoUnlockCb = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
    )
    VideoUnlockCb.__doc__ = """ """

cb = CallbackDecorators


def libvlc_add_intf(p_instance, name):
    f = _Cfunctions.get("libvlc_add_intf", None) or _Cfunction(
        "libvlc_add_intf",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, name)


def libvlc_audio_equalizer_get_amp_at_index(p_equalizer, u_band):
    f = _Cfunctions.get("libvlc_audio_equalizer_get_amp_at_index", None) or _Cfunction(
        "libvlc_audio_equalizer_get_amp_at_index",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_float,
        AudioEqualizer,
        ctypes.c_uint,
    )
    return f(p_equalizer, u_band)


def libvlc_audio_equalizer_get_band_count():
    f = _Cfunctions.get("libvlc_audio_equalizer_get_band_count", None) or _Cfunction(
        "libvlc_audio_equalizer_get_band_count", (), None, ctypes.c_uint
    )
    return f()


def libvlc_audio_equalizer_get_band_frequency(u_index):
    f = _Cfunctions.get(
        "libvlc_audio_equalizer_get_band_frequency", None
    ) or _Cfunction(
        "libvlc_audio_equalizer_get_band_frequency",
        ((1,),),
        None,
        ctypes.c_float,
        ctypes.c_uint,
    )
    return f(u_index)


def libvlc_audio_equalizer_get_preamp(p_equalizer):
    f = _Cfunctions.get("libvlc_audio_equalizer_get_preamp", None) or _Cfunction(
        "libvlc_audio_equalizer_get_preamp",
        ((1,),),
        None,
        ctypes.c_float,
        AudioEqualizer,
    )
    return f(p_equalizer)


def libvlc_audio_equalizer_get_preset_count():
    f = _Cfunctions.get("libvlc_audio_equalizer_get_preset_count", None) or _Cfunction(
        "libvlc_audio_equalizer_get_preset_count", (), None, ctypes.c_uint
    )
    return f()


def libvlc_audio_equalizer_get_preset_name(u_index):
    f = _Cfunctions.get("libvlc_audio_equalizer_get_preset_name", None) or _Cfunction(
        "libvlc_audio_equalizer_get_preset_name",
        ((1,),),
        None,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    return f(u_index)


def libvlc_audio_equalizer_new():
    f = _Cfunctions.get("libvlc_audio_equalizer_new", None) or _Cfunction(
        "libvlc_audio_equalizer_new", (), class_result(AudioEqualizer), ctypes.c_void_p
    )
    return f()


def libvlc_audio_equalizer_new_from_preset(u_index):
    f = _Cfunctions.get("libvlc_audio_equalizer_new_from_preset", None) or _Cfunction(
        "libvlc_audio_equalizer_new_from_preset",
        ((1,),),
        class_result(AudioEqualizer),
        ctypes.c_void_p,
        ctypes.c_uint,
    )
    return f(u_index)


def libvlc_audio_equalizer_release(p_equalizer):
    f = _Cfunctions.get("libvlc_audio_equalizer_release", None) or _Cfunction(
        "libvlc_audio_equalizer_release", ((1,),), None, None, AudioEqualizer
    )
    return f(p_equalizer)


def libvlc_audio_equalizer_set_amp_at_index(p_equalizer, f_amp, u_band):
    f = _Cfunctions.get("libvlc_audio_equalizer_set_amp_at_index", None) or _Cfunction(
        "libvlc_audio_equalizer_set_amp_at_index",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        AudioEqualizer,
        ctypes.c_float,
        ctypes.c_uint,
    )
    return f(p_equalizer, f_amp, u_band)


def libvlc_audio_equalizer_set_preamp(p_equalizer, f_preamp):
    f = _Cfunctions.get("libvlc_audio_equalizer_set_preamp", None) or _Cfunction(
        "libvlc_audio_equalizer_set_preamp",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        AudioEqualizer,
        ctypes.c_float,
    )
    return f(p_equalizer, f_preamp)


def libvlc_audio_filter_list_get(p_instance):
    f = _Cfunctions.get("libvlc_audio_filter_list_get", None) or _Cfunction(
        "libvlc_audio_filter_list_get",
        ((1,),),
        None,
        ctypes.POINTER(ModuleDescription),
        Instance,
    )
    return f(p_instance)


def libvlc_audio_get_channel(p_mi):
    f = _Cfunctions.get("libvlc_audio_get_channel", None) or _Cfunction(
        "libvlc_audio_get_channel", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_audio_get_delay(p_mi):
    f = _Cfunctions.get("libvlc_audio_get_delay", None) or _Cfunction(
        "libvlc_audio_get_delay", ((1,),), None, ctypes.c_int64, MediaPlayer
    )
    return f(p_mi)


def libvlc_audio_get_mute(p_mi):
    f = _Cfunctions.get("libvlc_audio_get_mute", None) or _Cfunction(
        "libvlc_audio_get_mute", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_audio_get_track(p_mi):
    f = _Cfunctions.get("libvlc_audio_get_track", None) or _Cfunction(
        "libvlc_audio_get_track", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_audio_get_track_count(p_mi):
    f = _Cfunctions.get("libvlc_audio_get_track_count", None) or _Cfunction(
        "libvlc_audio_get_track_count", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_audio_get_track_description(p_mi):
    f = _Cfunctions.get("libvlc_audio_get_track_description", None) or _Cfunction(
        "libvlc_audio_get_track_description",
        ((1,),),
        None,
        ctypes.POINTER(TrackDescription),
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_audio_get_volume(p_mi):
    f = _Cfunctions.get("libvlc_audio_get_volume", None) or _Cfunction(
        "libvlc_audio_get_volume", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_audio_output_device_count(p_instance, psz_audio_output):
    f = _Cfunctions.get("libvlc_audio_output_device_count", None) or _Cfunction(
        "libvlc_audio_output_device_count",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_audio_output)


def libvlc_audio_output_device_enum(mp):
    f = _Cfunctions.get("libvlc_audio_output_device_enum", None) or _Cfunction(
        "libvlc_audio_output_device_enum",
        ((1,),),
        None,
        ctypes.POINTER(AudioOutputDevice),
        MediaPlayer,
    )
    return f(mp)


def libvlc_audio_output_device_get(mp):
    f = _Cfunctions.get("libvlc_audio_output_device_get", None) or _Cfunction(
        "libvlc_audio_output_device_get",
        ((1,),),
        string_result,
        ctypes.c_void_p,
        MediaPlayer,
    )
    return f(mp)


def libvlc_audio_output_device_id(p_instance, psz_audio_output, i_device):
    f = _Cfunctions.get("libvlc_audio_output_device_id", None) or _Cfunction(
        "libvlc_audio_output_device_id",
        (
            (1,),
            (1,),
            (1,),
        ),
        string_result,
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_audio_output, i_device)


def libvlc_audio_output_device_list_get(p_instance, aout):
    f = _Cfunctions.get("libvlc_audio_output_device_list_get", None) or _Cfunction(
        "libvlc_audio_output_device_list_get",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.POINTER(AudioOutputDevice),
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, aout)


def libvlc_audio_output_device_list_release(p_list):
    f = _Cfunctions.get("libvlc_audio_output_device_list_release", None) or _Cfunction(
        "libvlc_audio_output_device_list_release",
        ((1,),),
        None,
        None,
        ctypes.POINTER(AudioOutputDevice),
    )
    return f(p_list)


def libvlc_audio_output_device_longname(p_instance, psz_output, i_device):
    f = _Cfunctions.get("libvlc_audio_output_device_longname", None) or _Cfunction(
        "libvlc_audio_output_device_longname",
        (
            (1,),
            (1,),
            (1,),
        ),
        string_result,
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_output, i_device)


def libvlc_audio_output_device_set(mp, module, device_id):
    f = _Cfunctions.get("libvlc_audio_output_device_set", None) or _Cfunction(
        "libvlc_audio_output_device_set",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    return f(mp, module, device_id)


def libvlc_audio_output_get_device_type(p_mi):
    f = _Cfunctions.get("libvlc_audio_output_get_device_type", None) or _Cfunction(
        "libvlc_audio_output_get_device_type", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_audio_output_list_get(p_instance):
    f = _Cfunctions.get("libvlc_audio_output_list_get", None) or _Cfunction(
        "libvlc_audio_output_list_get",
        ((1,),),
        None,
        ctypes.POINTER(AudioOutput),
        Instance,
    )
    return f(p_instance)


def libvlc_audio_output_list_release(p_list):
    f = _Cfunctions.get("libvlc_audio_output_list_release", None) or _Cfunction(
        "libvlc_audio_output_list_release",
        ((1,),),
        None,
        None,
        ctypes.POINTER(AudioOutput),
    )
    return f(p_list)


def libvlc_audio_output_set(p_mi, psz_name):
    f = _Cfunctions.get("libvlc_audio_output_set", None) or _Cfunction(
        "libvlc_audio_output_set",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_char_p,
    )
    return f(p_mi, psz_name)


def libvlc_audio_output_set_device_type(p_mp, device_type):
    f = _Cfunctions.get("libvlc_audio_output_set_device_type", None) or _Cfunction(
        "libvlc_audio_output_set_device_type",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mp, device_type)


def libvlc_audio_set_callbacks(mp, play, pause, resume, flush, drain, opaque):
    f = _Cfunctions.get("libvlc_audio_set_callbacks", None) or _Cfunction(
        "libvlc_audio_set_callbacks",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        AudioPlayCb,
        AudioPauseCb,
        AudioResumeCb,
        AudioFlushCb,
        AudioDrainCb,
        ctypes.c_void_p,
    )
    return f(mp, play, pause, resume, flush, drain, opaque)


def libvlc_audio_set_channel(p_mi, channel):
    f = _Cfunctions.get("libvlc_audio_set_channel", None) or _Cfunction(
        "libvlc_audio_set_channel",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, channel)


def libvlc_audio_set_delay(p_mi, i_delay):
    f = _Cfunctions.get("libvlc_audio_set_delay", None) or _Cfunction(
        "libvlc_audio_set_delay",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int64,
    )
    return f(p_mi, i_delay)


def libvlc_audio_set_format(mp, format, rate, channels):
    f = _Cfunctions.get("libvlc_audio_set_format", None) or _Cfunction(
        "libvlc_audio_set_format",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_char_p,
        ctypes.c_uint,
        ctypes.c_uint,
    )
    return f(mp, format, rate, channels)


def libvlc_audio_set_format_callbacks(mp, setup, cleanup):
    f = _Cfunctions.get("libvlc_audio_set_format_callbacks", None) or _Cfunction(
        "libvlc_audio_set_format_callbacks",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        AudioSetupCb,
        AudioCleanupCb,
    )
    return f(mp, setup, cleanup)


def libvlc_audio_set_mute(p_mi, status):
    f = _Cfunctions.get("libvlc_audio_set_mute", None) or _Cfunction(
        "libvlc_audio_set_mute",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, status)


def libvlc_audio_set_track(p_mi, i_track):
    f = _Cfunctions.get("libvlc_audio_set_track", None) or _Cfunction(
        "libvlc_audio_set_track",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_track)


def libvlc_audio_set_volume(p_mi, i_volume):
    f = _Cfunctions.get("libvlc_audio_set_volume", None) or _Cfunction(
        "libvlc_audio_set_volume",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_volume)


def libvlc_audio_set_volume_callback(mp, set_volume):
    f = _Cfunctions.get("libvlc_audio_set_volume_callback", None) or _Cfunction(
        "libvlc_audio_set_volume_callback",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        AudioSetVolumeCb,
    )
    return f(mp, set_volume)


def libvlc_audio_toggle_mute(p_mi):
    f = _Cfunctions.get("libvlc_audio_toggle_mute", None) or _Cfunction(
        "libvlc_audio_toggle_mute", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_chapter_descriptions_release(p_chapters, i_count):
    f = _Cfunctions.get("libvlc_chapter_descriptions_release", None) or _Cfunction(
        "libvlc_chapter_descriptions_release",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        ctypes.POINTER(ctypes.POINTER(ChapterDescription)),
        ctypes.c_uint,
    )
    return f(p_chapters, i_count)


def libvlc_clearerr():
    f = _Cfunctions.get("libvlc_clearerr", None) or _Cfunction(
        "libvlc_clearerr", (), None, None
    )
    return f()


def libvlc_clock():
    f = _Cfunctions.get("libvlc_clock", None) or _Cfunction(
        "libvlc_clock", (), None, ctypes.c_int64
    )
    return f()


def libvlc_dialog_dismiss(p_id):
    f = _Cfunctions.get("libvlc_dialog_dismiss", None) or _Cfunction(
        "libvlc_dialog_dismiss", ((1,),), None, ctypes.c_int, ctypes.c_void_p
    )
    return f(p_id)


def libvlc_dialog_get_context(p_id):
    f = _Cfunctions.get("libvlc_dialog_get_context", None) or _Cfunction(
        "libvlc_dialog_get_context", ((1,),), None, ctypes.c_void_p, ctypes.c_void_p
    )
    return f(p_id)


def libvlc_dialog_post_action(p_id, i_action):
    f = _Cfunctions.get("libvlc_dialog_post_action", None) or _Cfunction(
        "libvlc_dialog_post_action",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_int,
    )
    return f(p_id, i_action)


def libvlc_dialog_post_login(p_id, psz_username, psz_password, b_store):
    f = _Cfunctions.get("libvlc_dialog_post_login", None) or _Cfunction(
        "libvlc_dialog_post_login",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_bool,
    )
    return f(p_id, psz_username, psz_password, b_store)


def libvlc_dialog_set_callbacks(p_instance, p_cbs, p_data):
    f = _Cfunctions.get("libvlc_dialog_set_callbacks", None) or _Cfunction(
        "libvlc_dialog_set_callbacks",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        ctypes.POINTER(DialogCbs),
        ctypes.c_void_p,
    )
    return f(p_instance, p_cbs, p_data)


def libvlc_dialog_set_context(p_id, p_context):
    f = _Cfunctions.get("libvlc_dialog_set_context", None) or _Cfunction(
        "libvlc_dialog_set_context",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )
    return f(p_id, p_context)


def libvlc_errmsg():
    f = _Cfunctions.get("libvlc_errmsg", None) or _Cfunction(
        "libvlc_errmsg", (), None, ctypes.c_char_p
    )
    return f()


def libvlc_event_attach(p_event_manager, i_event_type, f_callback, user_data):
    f = _Cfunctions.get("libvlc_event_attach", None) or _Cfunction(
        "libvlc_event_attach",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        EventManager,
        ctypes.c_uint,
        Callback,
        ctypes.c_void_p,
    )
    return f(p_event_manager, i_event_type, f_callback, user_data)


def libvlc_event_detach(p_event_manager, i_event_type, f_callback, p_user_data):
    f = _Cfunctions.get("libvlc_event_detach", None) or _Cfunction(
        "libvlc_event_detach",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        EventManager,
        ctypes.c_uint,
        Callback,
        ctypes.c_void_p,
    )
    return f(p_event_manager, i_event_type, f_callback, p_user_data)


def libvlc_event_type_name(event_type):
    f = _Cfunctions.get("libvlc_event_type_name", None) or _Cfunction(
        "libvlc_event_type_name", ((1,),), None, ctypes.c_char_p, ctypes.c_uint
    )
    return f(event_type)


def libvlc_free(ptr):
    f = _Cfunctions.get("libvlc_free", None) or _Cfunction(
        "libvlc_free", ((1,),), None, None, ctypes.c_void_p
    )
    return f(ptr)


def libvlc_get_changeset():
    f = _Cfunctions.get("libvlc_get_changeset", None) or _Cfunction(
        "libvlc_get_changeset", (), None, ctypes.c_char_p
    )
    return f()


def libvlc_get_compiler():
    f = _Cfunctions.get("libvlc_get_compiler", None) or _Cfunction(
        "libvlc_get_compiler", (), None, ctypes.c_char_p
    )
    return f()


def libvlc_get_fullscreen(p_mi):
    f = _Cfunctions.get("libvlc_get_fullscreen", None) or _Cfunction(
        "libvlc_get_fullscreen", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_get_log_verbosity(p_instance):
    f = _Cfunctions.get("libvlc_get_log_verbosity", None) or _Cfunction(
        "libvlc_get_log_verbosity", ((1,),), None, ctypes.c_uint, Instance
    )
    return f(p_instance)


def libvlc_get_version():
    f = _Cfunctions.get("libvlc_get_version", None) or _Cfunction(
        "libvlc_get_version", (), None, ctypes.c_char_p
    )
    return f()


def libvlc_log_clear(p_log):
    f = _Cfunctions.get("libvlc_log_clear", None) or _Cfunction(
        "libvlc_log_clear", ((1,),), None, None, Log_ptr
    )
    return f(p_log)


def libvlc_log_close(p_log):
    f = _Cfunctions.get("libvlc_log_close", None) or _Cfunction(
        "libvlc_log_close", ((1,),), None, None, Log_ptr
    )
    return f(p_log)


def libvlc_log_count(p_log):
    f = _Cfunctions.get("libvlc_log_count", None) or _Cfunction(
        "libvlc_log_count", ((1,),), None, ctypes.c_uint, Log_ptr
    )
    return f(p_log)


def libvlc_log_get_context(ctx, module, file):
    f = _Cfunctions.get("libvlc_log_get_context", None) or _Cfunction(
        "libvlc_log_get_context",
        (
            (1,),
            (1,),
            (1,),
            (2,),
        ),
        None,
        None,
        Log_ptr,
        ListPOINTER(ctypes.c_char_p),
        ListPOINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_uint),
    )
    return f(ctx, module, file)


def libvlc_log_get_iterator(p_log):
    f = _Cfunctions.get("libvlc_log_get_iterator", None) or _Cfunction(
        "libvlc_log_get_iterator",
        ((1,),),
        class_result(LogIterator),
        ctypes.c_void_p,
        Log_ptr,
    )
    return f(p_log)


def libvlc_log_get_object(ctx, name, header, id):
    f = _Cfunctions.get("libvlc_log_get_object", None) or _Cfunction(
        "libvlc_log_get_object",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Log_ptr,
        ListPOINTER(ctypes.c_char_p),
        ListPOINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_uint),
    )
    return f(ctx, name, header, id)


def libvlc_log_iterator_free(p_iter):
    f = _Cfunctions.get("libvlc_log_iterator_free", None) or _Cfunction(
        "libvlc_log_iterator_free", ((1,),), None, None, LogIterator
    )
    return f(p_iter)


def libvlc_log_iterator_has_next(p_iter):
    f = _Cfunctions.get("libvlc_log_iterator_has_next", None) or _Cfunction(
        "libvlc_log_iterator_has_next", ((1,),), None, ctypes.c_int, LogIterator
    )
    return f(p_iter)


def libvlc_log_iterator_next(p_iter, p_buf):
    f = _Cfunctions.get("libvlc_log_iterator_next", None) or _Cfunction(
        "libvlc_log_iterator_next",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.POINTER(LogMessage),
        LogIterator,
        ctypes.POINTER(LogMessage),
    )
    return f(p_iter, p_buf)


def libvlc_log_open(p_instance):
    f = _Cfunctions.get("libvlc_log_open", None) or _Cfunction(
        "libvlc_log_open", ((1,),), None, Log_ptr, Instance
    )
    return f(p_instance)


def libvlc_log_set(p_instance, cb, data):
    f = _Cfunctions.get("libvlc_log_set", None) or _Cfunction(
        "libvlc_log_set",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        LogCb,
        ctypes.c_void_p,
    )
    return f(p_instance, cb, data)


def libvlc_log_set_file(p_instance, stream):
    f = _Cfunctions.get("libvlc_log_set_file", None) or _Cfunction(
        "libvlc_log_set_file",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        FILE_ptr,
    )
    return f(p_instance, stream)


def libvlc_log_unset(p_instance):
    f = _Cfunctions.get("libvlc_log_unset", None) or _Cfunction(
        "libvlc_log_unset", ((1,),), None, None, Instance
    )
    return f(p_instance)


def libvlc_media_add_option(p_md, psz_options):
    f = _Cfunctions.get("libvlc_media_add_option", None) or _Cfunction(
        "libvlc_media_add_option",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        Media,
        ctypes.c_char_p,
    )
    return f(p_md, psz_options)


def libvlc_media_add_option_flag(p_md, psz_options, i_flags):
    f = _Cfunctions.get("libvlc_media_add_option_flag", None) or _Cfunction(
        "libvlc_media_add_option_flag",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Media,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    return f(p_md, psz_options, i_flags)


def libvlc_media_discoverer_event_manager(p_mdis):
    f = _Cfunctions.get("libvlc_media_discoverer_event_manager", None) or _Cfunction(
        "libvlc_media_discoverer_event_manager",
        ((1,),),
        class_result(EventManager),
        ctypes.c_void_p,
        MediaDiscoverer,
    )
    return f(p_mdis)


def libvlc_media_discoverer_is_running(p_mdis):
    f = _Cfunctions.get("libvlc_media_discoverer_is_running", None) or _Cfunction(
        "libvlc_media_discoverer_is_running",
        ((1,),),
        None,
        ctypes.c_int,
        MediaDiscoverer,
    )
    return f(p_mdis)


def libvlc_media_discoverer_list_get(p_inst, i_cat, ppp_services):
    f = _Cfunctions.get("libvlc_media_discoverer_list_get", None) or _Cfunction(
        "libvlc_media_discoverer_list_get",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_size_t,
        Instance,
        MediaDiscovererCategory,
        ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(MediaDiscovererDescription))),
    )
    return f(p_inst, i_cat, ppp_services)


def libvlc_media_discoverer_list_release(pp_services, i_count):
    f = _Cfunctions.get("libvlc_media_discoverer_list_release", None) or _Cfunction(
        "libvlc_media_discoverer_list_release",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        ctypes.POINTER(ctypes.POINTER(MediaDiscovererDescription)),
        ctypes.c_size_t,
    )
    return f(pp_services, i_count)


def libvlc_media_discoverer_localized_name(p_mdis):
    f = _Cfunctions.get("libvlc_media_discoverer_localized_name", None) or _Cfunction(
        "libvlc_media_discoverer_localized_name",
        ((1,),),
        string_result,
        ctypes.c_void_p,
        MediaDiscoverer,
    )
    return f(p_mdis)


def libvlc_media_discoverer_media_list(p_mdis):
    f = _Cfunctions.get("libvlc_media_discoverer_media_list", None) or _Cfunction(
        "libvlc_media_discoverer_media_list",
        ((1,),),
        class_result(MediaList),
        ctypes.c_void_p,
        MediaDiscoverer,
    )
    return f(p_mdis)


def libvlc_media_discoverer_new(p_inst, psz_name):
    f = _Cfunctions.get("libvlc_media_discoverer_new", None) or _Cfunction(
        "libvlc_media_discoverer_new",
        (
            (1,),
            (1,),
        ),
        class_result(MediaDiscoverer),
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_inst, psz_name)


def libvlc_media_discoverer_new_from_name(p_inst, psz_name):
    f = _Cfunctions.get("libvlc_media_discoverer_new_from_name", None) or _Cfunction(
        "libvlc_media_discoverer_new_from_name",
        (
            (1,),
            (1,),
        ),
        class_result(MediaDiscoverer),
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_inst, psz_name)


def libvlc_media_discoverer_release(p_mdis):
    f = _Cfunctions.get("libvlc_media_discoverer_release", None) or _Cfunction(
        "libvlc_media_discoverer_release", ((1,),), None, None, MediaDiscoverer
    )
    return f(p_mdis)


def libvlc_media_discoverer_start(p_mdis):
    f = _Cfunctions.get("libvlc_media_discoverer_start", None) or _Cfunction(
        "libvlc_media_discoverer_start", ((1,),), None, ctypes.c_int, MediaDiscoverer
    )
    return f(p_mdis)


def libvlc_media_discoverer_stop(p_mdis):
    f = _Cfunctions.get("libvlc_media_discoverer_stop", None) or _Cfunction(
        "libvlc_media_discoverer_stop", ((1,),), None, None, MediaDiscoverer
    )
    return f(p_mdis)


def libvlc_media_duplicate(p_md):
    f = _Cfunctions.get("libvlc_media_duplicate", None) or _Cfunction(
        "libvlc_media_duplicate", ((1,),), class_result(Media), ctypes.c_void_p, Media
    )
    return f(p_md)


def libvlc_media_event_manager(p_md):
    f = _Cfunctions.get("libvlc_media_event_manager", None) or _Cfunction(
        "libvlc_media_event_manager",
        ((1,),),
        class_result(EventManager),
        ctypes.c_void_p,
        Media,
    )
    return f(p_md)


def libvlc_media_get_codec_description(i_type, i_codec):
    f = _Cfunctions.get("libvlc_media_get_codec_description", None) or _Cfunction(
        "libvlc_media_get_codec_description",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_char_p,
        TrackType,
        ctypes.c_uint32,
    )
    return f(i_type, i_codec)


def libvlc_media_get_duration(p_md):
    f = _Cfunctions.get("libvlc_media_get_duration", None) or _Cfunction(
        "libvlc_media_get_duration", ((1,),), None, ctypes.c_longlong, Media
    )
    return f(p_md)


def libvlc_media_get_meta(p_md, e_meta):
    f = _Cfunctions.get("libvlc_media_get_meta", None) or _Cfunction(
        "libvlc_media_get_meta",
        (
            (1,),
            (1,),
        ),
        string_result,
        ctypes.c_void_p,
        Media,
        Meta,
    )
    return f(p_md, e_meta)


def libvlc_media_get_mrl(p_md):
    f = _Cfunctions.get("libvlc_media_get_mrl", None) or _Cfunction(
        "libvlc_media_get_mrl", ((1,),), string_result, ctypes.c_void_p, Media
    )
    return f(p_md)


def libvlc_media_get_parsed_status(p_md):
    f = _Cfunctions.get("libvlc_media_get_parsed_status", None) or _Cfunction(
        "libvlc_media_get_parsed_status", ((1,),), None, MediaParsedStatus, Media
    )
    return f(p_md)


def libvlc_media_get_state(p_md):
    f = _Cfunctions.get("libvlc_media_get_state", None) or _Cfunction(
        "libvlc_media_get_state", ((1,),), None, State, Media
    )
    return f(p_md)


def libvlc_media_get_stats(p_md, p_stats):
    f = _Cfunctions.get("libvlc_media_get_stats", None) or _Cfunction(
        "libvlc_media_get_stats",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Media,
        ctypes.POINTER(MediaStats),
    )
    return f(p_md, p_stats)


def libvlc_media_get_tracks_info(p_md):
    f = _Cfunctions.get("libvlc_media_get_tracks_info", None) or _Cfunction(
        "libvlc_media_get_tracks_info",
        (
            (1,),
            (2,),
        ),
        None,
        ctypes.c_int,
        Media,
        ctypes.POINTER(ctypes.POINTER(MediaTrackInfo)),
    )
    return f(p_md)


def libvlc_media_get_type(p_md):
    f = _Cfunctions.get("libvlc_media_get_type", None) or _Cfunction(
        "libvlc_media_get_type", ((1,),), None, MediaType, Media
    )
    return f(p_md)


def libvlc_media_get_user_data(p_md):
    f = _Cfunctions.get("libvlc_media_get_user_data", None) or _Cfunction(
        "libvlc_media_get_user_data", ((1,),), None, ctypes.c_void_p, Media
    )
    return f(p_md)


def libvlc_media_is_parsed(p_md):
    f = _Cfunctions.get("libvlc_media_is_parsed", None) or _Cfunction(
        "libvlc_media_is_parsed", ((1,),), None, ctypes.c_int, Media
    )
    return f(p_md)


def libvlc_media_library_load(p_mlib):
    f = _Cfunctions.get("libvlc_media_library_load", None) or _Cfunction(
        "libvlc_media_library_load", ((1,),), None, ctypes.c_int, MediaLibrary
    )
    return f(p_mlib)


def libvlc_media_library_media_list(p_mlib):
    f = _Cfunctions.get("libvlc_media_library_media_list", None) or _Cfunction(
        "libvlc_media_library_media_list",
        ((1,),),
        class_result(MediaList),
        ctypes.c_void_p,
        MediaLibrary,
    )
    return f(p_mlib)


def libvlc_media_library_new(p_instance):
    f = _Cfunctions.get("libvlc_media_library_new", None) or _Cfunction(
        "libvlc_media_library_new",
        ((1,),),
        class_result(MediaLibrary),
        ctypes.c_void_p,
        Instance,
    )
    return f(p_instance)


def libvlc_media_library_release(p_mlib):
    f = _Cfunctions.get("libvlc_media_library_release", None) or _Cfunction(
        "libvlc_media_library_release", ((1,),), None, None, MediaLibrary
    )
    return f(p_mlib)


def libvlc_media_library_retain(p_mlib):
    f = _Cfunctions.get("libvlc_media_library_retain", None) or _Cfunction(
        "libvlc_media_library_retain", ((1,),), None, None, MediaLibrary
    )
    return f(p_mlib)


def libvlc_media_list_add_media(p_ml, p_md):
    f = _Cfunctions.get("libvlc_media_list_add_media", None) or _Cfunction(
        "libvlc_media_list_add_media",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaList,
        Media,
    )
    return f(p_ml, p_md)


def libvlc_media_list_count(p_ml):
    f = _Cfunctions.get("libvlc_media_list_count", None) or _Cfunction(
        "libvlc_media_list_count", ((1,),), None, ctypes.c_int, MediaList
    )
    return f(p_ml)


def libvlc_media_list_event_manager(p_ml):
    f = _Cfunctions.get("libvlc_media_list_event_manager", None) or _Cfunction(
        "libvlc_media_list_event_manager",
        ((1,),),
        class_result(EventManager),
        ctypes.c_void_p,
        MediaList,
    )
    return f(p_ml)


def libvlc_media_list_index_of_item(p_ml, p_md):
    f = _Cfunctions.get("libvlc_media_list_index_of_item", None) or _Cfunction(
        "libvlc_media_list_index_of_item",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaList,
        Media,
    )
    return f(p_ml, p_md)


def libvlc_media_list_insert_media(p_ml, p_md, i_pos):
    f = _Cfunctions.get("libvlc_media_list_insert_media", None) or _Cfunction(
        "libvlc_media_list_insert_media",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaList,
        Media,
        ctypes.c_int,
    )
    return f(p_ml, p_md, i_pos)


def libvlc_media_list_is_readonly(p_ml):
    f = _Cfunctions.get("libvlc_media_list_is_readonly", None) or _Cfunction(
        "libvlc_media_list_is_readonly", ((1,),), None, ctypes.c_int, MediaList
    )
    return f(p_ml)


def libvlc_media_list_item_at_index(p_ml, i_pos):
    f = _Cfunctions.get("libvlc_media_list_item_at_index", None) or _Cfunction(
        "libvlc_media_list_item_at_index",
        (
            (1,),
            (1,),
        ),
        class_result(Media),
        ctypes.c_void_p,
        MediaList,
        ctypes.c_int,
    )
    return f(p_ml, i_pos)


def libvlc_media_list_lock(p_ml):
    f = _Cfunctions.get("libvlc_media_list_lock", None) or _Cfunction(
        "libvlc_media_list_lock", ((1,),), None, None, MediaList
    )
    return f(p_ml)


def libvlc_media_list_media(p_ml):
    f = _Cfunctions.get("libvlc_media_list_media", None) or _Cfunction(
        "libvlc_media_list_media",
        ((1,),),
        class_result(Media),
        ctypes.c_void_p,
        MediaList,
    )
    return f(p_ml)


def libvlc_media_list_new(p_instance):
    f = _Cfunctions.get("libvlc_media_list_new", None) or _Cfunction(
        "libvlc_media_list_new",
        ((1,),),
        class_result(MediaList),
        ctypes.c_void_p,
        Instance,
    )
    return f(p_instance)


def libvlc_media_list_player_event_manager(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_event_manager", None) or _Cfunction(
        "libvlc_media_list_player_event_manager",
        ((1,),),
        class_result(EventManager),
        ctypes.c_void_p,
        MediaListPlayer,
    )
    return f(p_mlp)


def libvlc_media_list_player_get_media_player(p_mlp):
    f = _Cfunctions.get(
        "libvlc_media_list_player_get_media_player", None
    ) or _Cfunction(
        "libvlc_media_list_player_get_media_player",
        ((1,),),
        class_result(MediaPlayer),
        ctypes.c_void_p,
        MediaListPlayer,
    )
    return f(p_mlp)


def libvlc_media_list_player_get_state(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_get_state", None) or _Cfunction(
        "libvlc_media_list_player_get_state", ((1,),), None, State, MediaListPlayer
    )
    return f(p_mlp)


def libvlc_media_list_player_is_playing(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_is_playing", None) or _Cfunction(
        "libvlc_media_list_player_is_playing",
        ((1,),),
        None,
        ctypes.c_int,
        MediaListPlayer,
    )
    return f(p_mlp)


def libvlc_media_list_player_new(p_instance):
    f = _Cfunctions.get("libvlc_media_list_player_new", None) or _Cfunction(
        "libvlc_media_list_player_new",
        ((1,),),
        class_result(MediaListPlayer),
        ctypes.c_void_p,
        Instance,
    )
    return f(p_instance)


def libvlc_media_list_player_next(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_next", None) or _Cfunction(
        "libvlc_media_list_player_next", ((1,),), None, ctypes.c_int, MediaListPlayer
    )
    return f(p_mlp)


def libvlc_media_list_player_pause(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_pause", None) or _Cfunction(
        "libvlc_media_list_player_pause", ((1,),), None, None, MediaListPlayer
    )
    return f(p_mlp)


def libvlc_media_list_player_play(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_play", None) or _Cfunction(
        "libvlc_media_list_player_play", ((1,),), None, None, MediaListPlayer
    )
    return f(p_mlp)


def libvlc_media_list_player_play_item(p_mlp, p_md):
    f = _Cfunctions.get("libvlc_media_list_player_play_item", None) or _Cfunction(
        "libvlc_media_list_player_play_item",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaListPlayer,
        Media,
    )
    return f(p_mlp, p_md)


def libvlc_media_list_player_play_item_at_index(p_mlp, i_index):
    f = _Cfunctions.get(
        "libvlc_media_list_player_play_item_at_index", None
    ) or _Cfunction(
        "libvlc_media_list_player_play_item_at_index",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaListPlayer,
        ctypes.c_int,
    )
    return f(p_mlp, i_index)


def libvlc_media_list_player_previous(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_previous", None) or _Cfunction(
        "libvlc_media_list_player_previous",
        ((1,),),
        None,
        ctypes.c_int,
        MediaListPlayer,
    )
    return f(p_mlp)


def libvlc_media_list_player_release(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_release", None) or _Cfunction(
        "libvlc_media_list_player_release", ((1,),), None, None, MediaListPlayer
    )
    return f(p_mlp)


def libvlc_media_list_player_retain(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_retain", None) or _Cfunction(
        "libvlc_media_list_player_retain", ((1,),), None, None, MediaListPlayer
    )
    return f(p_mlp)


def libvlc_media_list_player_set_media_list(p_mlp, p_mlist):
    f = _Cfunctions.get("libvlc_media_list_player_set_media_list", None) or _Cfunction(
        "libvlc_media_list_player_set_media_list",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaListPlayer,
        MediaList,
    )
    return f(p_mlp, p_mlist)


def libvlc_media_list_player_set_media_player(p_mlp, p_mi):
    f = _Cfunctions.get(
        "libvlc_media_list_player_set_media_player", None
    ) or _Cfunction(
        "libvlc_media_list_player_set_media_player",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaListPlayer,
        MediaPlayer,
    )
    return f(p_mlp, p_mi)


def libvlc_media_list_player_set_pause(p_mlp, do_pause):
    f = _Cfunctions.get("libvlc_media_list_player_set_pause", None) or _Cfunction(
        "libvlc_media_list_player_set_pause",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaListPlayer,
        ctypes.c_int,
    )
    return f(p_mlp, do_pause)


def libvlc_media_list_player_set_playback_mode(p_mlp, e_mode):
    f = _Cfunctions.get(
        "libvlc_media_list_player_set_playback_mode", None
    ) or _Cfunction(
        "libvlc_media_list_player_set_playback_mode",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaListPlayer,
        PlaybackMode,
    )
    return f(p_mlp, e_mode)


def libvlc_media_list_player_stop(p_mlp):
    f = _Cfunctions.get("libvlc_media_list_player_stop", None) or _Cfunction(
        "libvlc_media_list_player_stop", ((1,),), None, None, MediaListPlayer
    )
    return f(p_mlp)


def libvlc_media_list_release(p_ml):
    f = _Cfunctions.get("libvlc_media_list_release", None) or _Cfunction(
        "libvlc_media_list_release", ((1,),), None, None, MediaList
    )
    return f(p_ml)


def libvlc_media_list_remove_index(p_ml, i_pos):
    f = _Cfunctions.get("libvlc_media_list_remove_index", None) or _Cfunction(
        "libvlc_media_list_remove_index",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaList,
        ctypes.c_int,
    )
    return f(p_ml, i_pos)


def libvlc_media_list_retain(p_ml):
    f = _Cfunctions.get("libvlc_media_list_retain", None) or _Cfunction(
        "libvlc_media_list_retain", ((1,),), None, None, MediaList
    )
    return f(p_ml)


def libvlc_media_list_set_media(p_ml, p_md):
    f = _Cfunctions.get("libvlc_media_list_set_media", None) or _Cfunction(
        "libvlc_media_list_set_media",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaList,
        Media,
    )
    return f(p_ml, p_md)


def libvlc_media_list_unlock(p_ml):
    f = _Cfunctions.get("libvlc_media_list_unlock", None) or _Cfunction(
        "libvlc_media_list_unlock", ((1,),), None, None, MediaList
    )
    return f(p_ml)


def libvlc_media_new_as_node(p_instance, psz_name):
    f = _Cfunctions.get("libvlc_media_new_as_node", None) or _Cfunction(
        "libvlc_media_new_as_node",
        (
            (1,),
            (1,),
        ),
        class_result(Media),
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name)


def libvlc_media_new_callbacks(instance, open_cb, read_cb, seek_cb, close_cb, opaque):
    f = _Cfunctions.get("libvlc_media_new_callbacks", None) or _Cfunction(
        "libvlc_media_new_callbacks",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        class_result(Media),
        ctypes.c_void_p,
        Instance,
        MediaOpenCb,
        MediaReadCb,
        MediaSeekCb,
        MediaCloseCb,
        ctypes.c_void_p,
    )
    return f(instance, open_cb, read_cb, seek_cb, close_cb, opaque)


def libvlc_media_new_fd(p_instance, fd):
    f = _Cfunctions.get("libvlc_media_new_fd", None) or _Cfunction(
        "libvlc_media_new_fd",
        (
            (1,),
            (1,),
        ),
        class_result(Media),
        ctypes.c_void_p,
        Instance,
        ctypes.c_int,
    )
    return f(p_instance, fd)


def libvlc_media_new_location(p_instance, psz_mrl):
    f = _Cfunctions.get("libvlc_media_new_location", None) or _Cfunction(
        "libvlc_media_new_location",
        (
            (1,),
            (1,),
        ),
        class_result(Media),
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_mrl)


def libvlc_media_new_path(p_instance, path):
    f = _Cfunctions.get("libvlc_media_new_path", None) or _Cfunction(
        "libvlc_media_new_path",
        (
            (1,),
            (1,),
        ),
        class_result(Media),
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, path)


def libvlc_media_parse(p_md):
    f = _Cfunctions.get("libvlc_media_parse", None) or _Cfunction(
        "libvlc_media_parse", ((1,),), None, None, Media
    )
    return f(p_md)


def libvlc_media_parse_async(p_md):
    f = _Cfunctions.get("libvlc_media_parse_async", None) or _Cfunction(
        "libvlc_media_parse_async", ((1,),), None, None, Media
    )
    return f(p_md)


def libvlc_media_parse_stop(p_md):
    f = _Cfunctions.get("libvlc_media_parse_stop", None) or _Cfunction(
        "libvlc_media_parse_stop", ((1,),), None, None, Media
    )
    return f(p_md)


def libvlc_media_parse_with_options(p_md, parse_flag, timeout):
    f = _Cfunctions.get("libvlc_media_parse_with_options", None) or _Cfunction(
        "libvlc_media_parse_with_options",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Media,
        MediaParseFlag,
        ctypes.c_int,
    )
    return f(p_md, parse_flag, timeout)


def libvlc_media_player_add_slave(p_mi, i_type, psz_uri, b_select):
    f = _Cfunctions.get("libvlc_media_player_add_slave", None) or _Cfunction(
        "libvlc_media_player_add_slave",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        MediaSlaveType,
        ctypes.c_char_p,
        ctypes.c_bool,
    )
    return f(p_mi, i_type, psz_uri, b_select)


def libvlc_media_player_can_pause(p_mi):
    f = _Cfunctions.get("libvlc_media_player_can_pause", None) or _Cfunction(
        "libvlc_media_player_can_pause", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_event_manager(p_mi):
    f = _Cfunctions.get("libvlc_media_player_event_manager", None) or _Cfunction(
        "libvlc_media_player_event_manager",
        ((1,),),
        class_result(EventManager),
        ctypes.c_void_p,
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_media_player_get_agl(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_agl", None) or _Cfunction(
        "libvlc_media_player_get_agl", ((1,),), None, ctypes.c_uint32, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_chapter(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_chapter", None) or _Cfunction(
        "libvlc_media_player_get_chapter", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_chapter_count(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_chapter_count", None) or _Cfunction(
        "libvlc_media_player_get_chapter_count",
        ((1,),),
        None,
        ctypes.c_int,
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_media_player_get_chapter_count_for_title(p_mi, i_title):
    f = _Cfunctions.get(
        "libvlc_media_player_get_chapter_count_for_title", None
    ) or _Cfunction(
        "libvlc_media_player_get_chapter_count_for_title",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_title)


def libvlc_media_player_get_fps(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_fps", None) or _Cfunction(
        "libvlc_media_player_get_fps", ((1,),), None, ctypes.c_float, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_full_chapter_descriptions(
    p_mi, i_chapters_of_title, pp_chapters
):
    f = _Cfunctions.get(
        "libvlc_media_player_get_full_chapter_descriptions", None
    ) or _Cfunction(
        "libvlc_media_player_get_full_chapter_descriptions",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int,
        ctypes.POINTER(ctypes.POINTER(ChapterDescription)),
    )
    return f(p_mi, i_chapters_of_title, pp_chapters)


def libvlc_media_player_get_full_title_descriptions(p_mi, titles):
    f = _Cfunctions.get(
        "libvlc_media_player_get_full_title_descriptions", None
    ) or _Cfunction(
        "libvlc_media_player_get_full_title_descriptions",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.POINTER(ctypes.POINTER(TitleDescription)),
    )
    return f(p_mi, titles)


def libvlc_media_player_get_hwnd(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_hwnd", None) or _Cfunction(
        "libvlc_media_player_get_hwnd", ((1,),), None, ctypes.c_void_p, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_length(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_length", None) or _Cfunction(
        "libvlc_media_player_get_length", ((1,),), None, ctypes.c_longlong, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_media(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_media", None) or _Cfunction(
        "libvlc_media_player_get_media",
        ((1,),),
        class_result(Media),
        ctypes.c_void_p,
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_media_player_get_nsobject(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_nsobject", None) or _Cfunction(
        "libvlc_media_player_get_nsobject", ((1,),), None, ctypes.c_void_p, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_position(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_position", None) or _Cfunction(
        "libvlc_media_player_get_position", ((1,),), None, ctypes.c_float, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_rate(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_rate", None) or _Cfunction(
        "libvlc_media_player_get_rate", ((1,),), None, ctypes.c_float, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_role(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_role", None) or _Cfunction(
        "libvlc_media_player_get_role", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_state(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_state", None) or _Cfunction(
        "libvlc_media_player_get_state", ((1,),), None, State, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_time(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_time", None) or _Cfunction(
        "libvlc_media_player_get_time", ((1,),), None, ctypes.c_longlong, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_title(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_title", None) or _Cfunction(
        "libvlc_media_player_get_title", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_title_count(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_title_count", None) or _Cfunction(
        "libvlc_media_player_get_title_count", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_get_xwindow(p_mi):
    f = _Cfunctions.get("libvlc_media_player_get_xwindow", None) or _Cfunction(
        "libvlc_media_player_get_xwindow", ((1,),), None, ctypes.c_uint32, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_has_vout(p_mi):
    f = _Cfunctions.get("libvlc_media_player_has_vout", None) or _Cfunction(
        "libvlc_media_player_has_vout", ((1,),), None, ctypes.c_uint, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_is_playing(p_mi):
    f = _Cfunctions.get("libvlc_media_player_is_playing", None) or _Cfunction(
        "libvlc_media_player_is_playing", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_is_seekable(p_mi):
    f = _Cfunctions.get("libvlc_media_player_is_seekable", None) or _Cfunction(
        "libvlc_media_player_is_seekable", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_navigate(p_mi, navigate):
    f = _Cfunctions.get("libvlc_media_player_navigate", None) or _Cfunction(
        "libvlc_media_player_navigate",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, navigate)


def libvlc_media_player_new(p_libvlc_instance):
    f = _Cfunctions.get("libvlc_media_player_new", None) or _Cfunction(
        "libvlc_media_player_new",
        ((1,),),
        class_result(MediaPlayer),
        ctypes.c_void_p,
        Instance,
    )
    return f(p_libvlc_instance)


def libvlc_media_player_new_from_media(p_md):
    f = _Cfunctions.get("libvlc_media_player_new_from_media", None) or _Cfunction(
        "libvlc_media_player_new_from_media",
        ((1,),),
        class_result(MediaPlayer),
        ctypes.c_void_p,
        Media,
    )
    return f(p_md)


def libvlc_media_player_next_chapter(p_mi):
    f = _Cfunctions.get("libvlc_media_player_next_chapter", None) or _Cfunction(
        "libvlc_media_player_next_chapter", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_next_frame(p_mi):
    f = _Cfunctions.get("libvlc_media_player_next_frame", None) or _Cfunction(
        "libvlc_media_player_next_frame", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_pause(p_mi):
    f = _Cfunctions.get("libvlc_media_player_pause", None) or _Cfunction(
        "libvlc_media_player_pause", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_play(p_mi):
    f = _Cfunctions.get("libvlc_media_player_play", None) or _Cfunction(
        "libvlc_media_player_play", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_previous_chapter(p_mi):
    f = _Cfunctions.get("libvlc_media_player_previous_chapter", None) or _Cfunction(
        "libvlc_media_player_previous_chapter", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_program_scrambled(p_mi):
    f = _Cfunctions.get("libvlc_media_player_program_scrambled", None) or _Cfunction(
        "libvlc_media_player_program_scrambled",
        ((1,),),
        None,
        ctypes.c_int,
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_media_player_release(p_mi):
    f = _Cfunctions.get("libvlc_media_player_release", None) or _Cfunction(
        "libvlc_media_player_release", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_retain(p_mi):
    f = _Cfunctions.get("libvlc_media_player_retain", None) or _Cfunction(
        "libvlc_media_player_retain", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_set_agl(p_mi, drawable):
    f = _Cfunctions.get("libvlc_media_player_set_agl", None) or _Cfunction(
        "libvlc_media_player_set_agl",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint32,
    )
    return f(p_mi, drawable)


def libvlc_media_player_set_android_context(p_mi, p_awindow_handler):
    f = _Cfunctions.get("libvlc_media_player_set_android_context", None) or _Cfunction(
        "libvlc_media_player_set_android_context",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_void_p,
    )
    return f(p_mi, p_awindow_handler)


def libvlc_media_player_set_chapter(p_mi, i_chapter):
    f = _Cfunctions.get("libvlc_media_player_set_chapter", None) or _Cfunction(
        "libvlc_media_player_set_chapter",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_chapter)


def libvlc_media_player_set_equalizer(p_mi, p_equalizer):
    f = _Cfunctions.get("libvlc_media_player_set_equalizer", None) or _Cfunction(
        "libvlc_media_player_set_equalizer",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        AudioEqualizer,
    )
    return f(p_mi, p_equalizer)


def libvlc_media_player_set_evas_object(p_mi, p_evas_object):
    f = _Cfunctions.get("libvlc_media_player_set_evas_object", None) or _Cfunction(
        "libvlc_media_player_set_evas_object",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_void_p,
    )
    return f(p_mi, p_evas_object)


def libvlc_media_player_set_hwnd(p_mi, drawable):
    f = _Cfunctions.get("libvlc_media_player_set_hwnd", None) or _Cfunction(
        "libvlc_media_player_set_hwnd",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_void_p,
    )
    return f(p_mi, drawable)


def libvlc_media_player_set_media(p_mi, p_md):
    f = _Cfunctions.get("libvlc_media_player_set_media", None) or _Cfunction(
        "libvlc_media_player_set_media",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        Media,
    )
    return f(p_mi, p_md)


def libvlc_media_player_set_nsobject(p_mi, drawable):
    f = _Cfunctions.get("libvlc_media_player_set_nsobject", None) or _Cfunction(
        "libvlc_media_player_set_nsobject",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_void_p,
    )
    return f(p_mi, drawable)


def libvlc_media_player_set_pause(mp, do_pause):
    f = _Cfunctions.get("libvlc_media_player_set_pause", None) or _Cfunction(
        "libvlc_media_player_set_pause",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(mp, do_pause)


def libvlc_media_player_set_position(p_mi, f_pos):
    f = _Cfunctions.get("libvlc_media_player_set_position", None) or _Cfunction(
        "libvlc_media_player_set_position",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_float,
    )
    return f(p_mi, f_pos)


def libvlc_media_player_set_rate(p_mi, rate):
    f = _Cfunctions.get("libvlc_media_player_set_rate", None) or _Cfunction(
        "libvlc_media_player_set_rate",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_float,
    )
    return f(p_mi, rate)


def libvlc_media_player_set_renderer(p_mi, p_item):
    f = _Cfunctions.get("libvlc_media_player_set_renderer", None) or _Cfunction(
        "libvlc_media_player_set_renderer",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        Renderer,
    )
    return f(p_mi, p_item)


def libvlc_media_player_set_role(p_mi, role):
    f = _Cfunctions.get("libvlc_media_player_set_role", None) or _Cfunction(
        "libvlc_media_player_set_role",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, role)


def libvlc_media_player_set_time(p_mi, i_time):
    f = _Cfunctions.get("libvlc_media_player_set_time", None) or _Cfunction(
        "libvlc_media_player_set_time",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_longlong,
    )
    return f(p_mi, i_time)


def libvlc_media_player_set_title(p_mi, i_title):
    f = _Cfunctions.get("libvlc_media_player_set_title", None) or _Cfunction(
        "libvlc_media_player_set_title",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_title)


def libvlc_media_player_set_video_title_display(p_mi, position, timeout):
    f = _Cfunctions.get(
        "libvlc_media_player_set_video_title_display", None
    ) or _Cfunction(
        "libvlc_media_player_set_video_title_display",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        Position,
        ctypes.c_uint,
    )
    return f(p_mi, position, timeout)


def libvlc_media_player_set_xwindow(p_mi, drawable):
    f = _Cfunctions.get("libvlc_media_player_set_xwindow", None) or _Cfunction(
        "libvlc_media_player_set_xwindow",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint32,
    )
    return f(p_mi, drawable)


def libvlc_media_player_stop(p_mi):
    f = _Cfunctions.get("libvlc_media_player_stop", None) or _Cfunction(
        "libvlc_media_player_stop", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_player_will_play(p_mi):
    f = _Cfunctions.get("libvlc_media_player_will_play", None) or _Cfunction(
        "libvlc_media_player_will_play", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_media_release(p_md):
    f = _Cfunctions.get("libvlc_media_release", None) or _Cfunction(
        "libvlc_media_release", ((1,),), None, None, Media
    )
    return f(p_md)


def libvlc_media_retain(p_md):
    f = _Cfunctions.get("libvlc_media_retain", None) or _Cfunction(
        "libvlc_media_retain", ((1,),), None, None, Media
    )
    return f(p_md)


def libvlc_media_save_meta(p_md):
    f = _Cfunctions.get("libvlc_media_save_meta", None) or _Cfunction(
        "libvlc_media_save_meta", ((1,),), None, ctypes.c_int, Media
    )
    return f(p_md)


def libvlc_media_set_meta(p_md, e_meta, psz_value):
    f = _Cfunctions.get("libvlc_media_set_meta", None) or _Cfunction(
        "libvlc_media_set_meta",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Media,
        Meta,
        ctypes.c_char_p,
    )
    return f(p_md, e_meta, psz_value)


def libvlc_media_set_user_data(p_md, p_new_user_data):
    f = _Cfunctions.get("libvlc_media_set_user_data", None) or _Cfunction(
        "libvlc_media_set_user_data",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        Media,
        ctypes.c_void_p,
    )
    return f(p_md, p_new_user_data)


def libvlc_media_slaves_add(p_md, i_type, i_priority, psz_uri):
    f = _Cfunctions.get("libvlc_media_slaves_add", None) or _Cfunction(
        "libvlc_media_slaves_add",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Media,
        MediaSlaveType,
        ctypes.c_uint,
        ctypes.c_char_p,
    )
    return f(p_md, i_type, i_priority, psz_uri)


def libvlc_media_slaves_clear(p_md):
    f = _Cfunctions.get("libvlc_media_slaves_clear", None) or _Cfunction(
        "libvlc_media_slaves_clear", ((1,),), None, None, Media
    )
    return f(p_md)


def libvlc_media_slaves_get(p_md, ppp_slaves):
    f = _Cfunctions.get("libvlc_media_slaves_get", None) or _Cfunction(
        "libvlc_media_slaves_get",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_uint,
        Media,
        ctypes.POINTER(ctypes.POINTER(MediaSlave)),
    )
    return f(p_md, ppp_slaves)


def libvlc_media_slaves_release(pp_slaves, i_count):
    f = _Cfunctions.get("libvlc_media_slaves_release", None) or _Cfunction(
        "libvlc_media_slaves_release",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        ctypes.POINTER(ctypes.POINTER(MediaSlave)),
        ctypes.c_uint,
    )
    return f(pp_slaves, i_count)


def libvlc_media_subitems(p_md):
    f = _Cfunctions.get("libvlc_media_subitems", None) or _Cfunction(
        "libvlc_media_subitems",
        ((1,),),
        class_result(MediaList),
        ctypes.c_void_p,
        Media,
    )
    return f(p_md)


def libvlc_media_tracks_get(p_md, tracks):
    f = _Cfunctions.get("libvlc_media_tracks_get", None) or _Cfunction(
        "libvlc_media_tracks_get",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_uint,
        Media,
        ctypes.POINTER(ctypes.POINTER(MediaTrack)),
    )
    return f(p_md, tracks)


def libvlc_media_tracks_release(p_tracks, i_count):
    f = _Cfunctions.get("libvlc_media_tracks_release", None) or _Cfunction(
        "libvlc_media_tracks_release",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        ctypes.POINTER(ctypes.POINTER(MediaTrack)),
        ctypes.c_uint,
    )
    return f(p_tracks, i_count)


def libvlc_module_description_list_release(p_list):
    f = _Cfunctions.get("libvlc_module_description_list_release", None) or _Cfunction(
        "libvlc_module_description_list_release",
        ((1,),),
        None,
        None,
        ctypes.POINTER(ModuleDescription),
    )
    return f(p_list)


def libvlc_new(argc, argv):
    f = _Cfunctions.get("libvlc_new", None) or _Cfunction(
        "libvlc_new",
        (
            (1,),
            (1,),
        ),
        class_result(Instance),
        ctypes.c_void_p,
        ctypes.c_int,
        ListPOINTER(ctypes.c_char_p),
    )
    return f(argc, argv)


def libvlc_playlist_play(p_instance, i_id, i_options, ppsz_options):
    f = _Cfunctions.get("libvlc_playlist_play", None) or _Cfunction(
        "libvlc_playlist_play",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        ctypes.c_int,
        ctypes.c_int,
        ListPOINTER(ctypes.c_char_p),
    )
    return f(p_instance, i_id, i_options, ppsz_options)


def libvlc_printerr(fmt):
    f = _Cfunctions.get("libvlc_printerr", None) or _Cfunction(
        "libvlc_printerr", ((1,),), None, ctypes.c_char_p, ctypes.c_char_p
    )
    return f(fmt)


def libvlc_release(p_instance):
    f = _Cfunctions.get("libvlc_release", None) or _Cfunction(
        "libvlc_release", ((1,),), None, None, Instance
    )
    return f(p_instance)


def libvlc_renderer_discoverer_event_manager(p_rd):
    f = _Cfunctions.get("libvlc_renderer_discoverer_event_manager", None) or _Cfunction(
        "libvlc_renderer_discoverer_event_manager",
        ((1,),),
        class_result(EventManager),
        ctypes.c_void_p,
        RendererDiscoverer,
    )
    return f(p_rd)


def libvlc_renderer_discoverer_list_get(p_inst, ppp_services):
    f = _Cfunctions.get("libvlc_renderer_discoverer_list_get", None) or _Cfunction(
        "libvlc_renderer_discoverer_list_get",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_size_t,
        Instance,
        ctypes.POINTER(ctypes.POINTER(ctypes.POINTER(RdDescription))),
    )
    return f(p_inst, ppp_services)


def libvlc_renderer_discoverer_list_release(pp_services, i_count):
    f = _Cfunctions.get("libvlc_renderer_discoverer_list_release", None) or _Cfunction(
        "libvlc_renderer_discoverer_list_release",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        ctypes.POINTER(ctypes.POINTER(RdDescription)),
        ctypes.c_size_t,
    )
    return f(pp_services, i_count)


def libvlc_renderer_discoverer_new(p_inst, psz_name):
    f = _Cfunctions.get("libvlc_renderer_discoverer_new", None) or _Cfunction(
        "libvlc_renderer_discoverer_new",
        (
            (1,),
            (1,),
        ),
        class_result(RendererDiscoverer),
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_inst, psz_name)


def libvlc_renderer_discoverer_release(p_rd):
    f = _Cfunctions.get("libvlc_renderer_discoverer_release", None) or _Cfunction(
        "libvlc_renderer_discoverer_release", ((1,),), None, None, RendererDiscoverer
    )
    return f(p_rd)


def libvlc_renderer_discoverer_start(p_rd):
    f = _Cfunctions.get("libvlc_renderer_discoverer_start", None) or _Cfunction(
        "libvlc_renderer_discoverer_start",
        ((1,),),
        None,
        ctypes.c_int,
        RendererDiscoverer,
    )
    return f(p_rd)


def libvlc_renderer_discoverer_stop(p_rd):
    f = _Cfunctions.get("libvlc_renderer_discoverer_stop", None) or _Cfunction(
        "libvlc_renderer_discoverer_stop", ((1,),), None, None, RendererDiscoverer
    )
    return f(p_rd)


def libvlc_renderer_item_flags(p_item):
    f = _Cfunctions.get("libvlc_renderer_item_flags", None) or _Cfunction(
        "libvlc_renderer_item_flags", ((1,),), None, ctypes.c_int, Renderer
    )
    return f(p_item)


def libvlc_renderer_item_hold(p_item):
    f = _Cfunctions.get("libvlc_renderer_item_hold", None) or _Cfunction(
        "libvlc_renderer_item_hold",
        ((1,),),
        class_result(Renderer),
        ctypes.c_void_p,
        Renderer,
    )
    return f(p_item)


def libvlc_renderer_item_icon_uri(p_item):
    f = _Cfunctions.get("libvlc_renderer_item_icon_uri", None) or _Cfunction(
        "libvlc_renderer_item_icon_uri", ((1,),), None, ctypes.c_char_p, Renderer
    )
    return f(p_item)


def libvlc_renderer_item_name(p_item):
    f = _Cfunctions.get("libvlc_renderer_item_name", None) or _Cfunction(
        "libvlc_renderer_item_name", ((1,),), None, ctypes.c_char_p, Renderer
    )
    return f(p_item)


def libvlc_renderer_item_release(p_item):
    f = _Cfunctions.get("libvlc_renderer_item_release", None) or _Cfunction(
        "libvlc_renderer_item_release", ((1,),), None, None, Renderer
    )
    return f(p_item)


def libvlc_renderer_item_type(p_item):
    f = _Cfunctions.get("libvlc_renderer_item_type", None) or _Cfunction(
        "libvlc_renderer_item_type", ((1,),), None, ctypes.c_char_p, Renderer
    )
    return f(p_item)


def libvlc_retain(p_instance):
    f = _Cfunctions.get("libvlc_retain", None) or _Cfunction(
        "libvlc_retain", ((1,),), None, None, Instance
    )
    return f(p_instance)


def libvlc_set_app_id(p_instance, id, version, icon):
    f = _Cfunctions.get("libvlc_set_app_id", None) or _Cfunction(
        "libvlc_set_app_id",
        (
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    return f(p_instance, id, version, icon)


LibvlcSetExitHandlerCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


def libvlc_set_exit_handler(p_instance, cb, opaque):
    f = _Cfunctions.get("libvlc_set_exit_handler", None) or _Cfunction(
        "libvlc_set_exit_handler",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        LibvlcSetExitHandlerCb,
        ctypes.c_void_p,
    )
    return f(p_instance, cb, opaque)


def libvlc_set_fullscreen(p_mi, b_fullscreen):
    f = _Cfunctions.get("libvlc_set_fullscreen", None) or _Cfunction(
        "libvlc_set_fullscreen",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, b_fullscreen)


def libvlc_set_log_verbosity(p_instance, level):
    f = _Cfunctions.get("libvlc_set_log_verbosity", None) or _Cfunction(
        "libvlc_set_log_verbosity",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        ctypes.c_uint,
    )
    return f(p_instance, level)


def libvlc_set_user_agent(p_instance, name, http):
    f = _Cfunctions.get("libvlc_set_user_agent", None) or _Cfunction(
        "libvlc_set_user_agent",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    return f(p_instance, name, http)


def libvlc_title_descriptions_release(p_titles, i_count):
    f = _Cfunctions.get("libvlc_title_descriptions_release", None) or _Cfunction(
        "libvlc_title_descriptions_release",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        ctypes.POINTER(ctypes.POINTER(TitleDescription)),
        ctypes.c_uint,
    )
    return f(p_titles, i_count)


def libvlc_toggle_fullscreen(p_mi):
    f = _Cfunctions.get("libvlc_toggle_fullscreen", None) or _Cfunction(
        "libvlc_toggle_fullscreen", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_toggle_teletext(p_mi):
    f = _Cfunctions.get("libvlc_toggle_teletext", None) or _Cfunction(
        "libvlc_toggle_teletext", ((1,),), None, None, MediaPlayer
    )
    return f(p_mi)


def libvlc_track_description_list_release(p_track_description):
    f = _Cfunctions.get("libvlc_track_description_list_release", None) or _Cfunction(
        "libvlc_track_description_list_release",
        ((1,),),
        None,
        None,
        ctypes.POINTER(TrackDescription),
    )
    return f(p_track_description)


def libvlc_track_description_release(p_track_description):
    f = _Cfunctions.get("libvlc_track_description_release", None) or _Cfunction(
        "libvlc_track_description_release",
        ((1,),),
        None,
        None,
        ctypes.POINTER(TrackDescription),
    )
    return f(p_track_description)


def libvlc_video_filter_list_get(p_instance):
    f = _Cfunctions.get("libvlc_video_filter_list_get", None) or _Cfunction(
        "libvlc_video_filter_list_get",
        ((1,),),
        None,
        ctypes.POINTER(ModuleDescription),
        Instance,
    )
    return f(p_instance)


def libvlc_video_get_adjust_float(p_mi, option):
    f = _Cfunctions.get("libvlc_video_get_adjust_float", None) or _Cfunction(
        "libvlc_video_get_adjust_float",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_float,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, option)


def libvlc_video_get_adjust_int(p_mi, option):
    f = _Cfunctions.get("libvlc_video_get_adjust_int", None) or _Cfunction(
        "libvlc_video_get_adjust_int",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, option)


def libvlc_video_get_aspect_ratio(p_mi):
    f = _Cfunctions.get("libvlc_video_get_aspect_ratio", None) or _Cfunction(
        "libvlc_video_get_aspect_ratio",
        ((1,),),
        string_result,
        ctypes.c_void_p,
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_video_get_chapter_description(p_mi, i_title):
    f = _Cfunctions.get("libvlc_video_get_chapter_description", None) or _Cfunction(
        "libvlc_video_get_chapter_description",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.POINTER(TrackDescription),
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_title)


def libvlc_video_get_crop_geometry(p_mi):
    f = _Cfunctions.get("libvlc_video_get_crop_geometry", None) or _Cfunction(
        "libvlc_video_get_crop_geometry",
        ((1,),),
        string_result,
        ctypes.c_void_p,
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_video_get_cursor(p_mi, num):
    f = _Cfunctions.get("libvlc_video_get_cursor", None) or _Cfunction(
        "libvlc_video_get_cursor",
        (
            (1,),
            (1,),
            (2,),
            (2,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    )
    return f(p_mi, num)


def libvlc_video_get_height(p_mi):
    f = _Cfunctions.get("libvlc_video_get_height", None) or _Cfunction(
        "libvlc_video_get_height", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_logo_int(p_mi, option):
    f = _Cfunctions.get("libvlc_video_get_logo_int", None) or _Cfunction(
        "libvlc_video_get_logo_int",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, option)


def libvlc_video_get_marquee_int(p_mi, option):
    f = _Cfunctions.get("libvlc_video_get_marquee_int", None) or _Cfunction(
        "libvlc_video_get_marquee_int",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, option)


def libvlc_video_get_marquee_string(p_mi, option):
    f = _Cfunctions.get("libvlc_video_get_marquee_string", None) or _Cfunction(
        "libvlc_video_get_marquee_string",
        (
            (1,),
            (1,),
        ),
        string_result,
        ctypes.c_void_p,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, option)


def libvlc_video_get_scale(p_mi):
    f = _Cfunctions.get("libvlc_video_get_scale", None) or _Cfunction(
        "libvlc_video_get_scale", ((1,),), None, ctypes.c_float, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_size(p_mi, num):
    f = _Cfunctions.get("libvlc_video_get_size", None) or _Cfunction(
        "libvlc_video_get_size",
        (
            (1,),
            (1,),
            (2,),
            (2,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    )
    return f(p_mi, num)


def libvlc_video_get_spu(p_mi):
    f = _Cfunctions.get("libvlc_video_get_spu", None) or _Cfunction(
        "libvlc_video_get_spu", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_spu_count(p_mi):
    f = _Cfunctions.get("libvlc_video_get_spu_count", None) or _Cfunction(
        "libvlc_video_get_spu_count", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_spu_delay(p_mi):
    f = _Cfunctions.get("libvlc_video_get_spu_delay", None) or _Cfunction(
        "libvlc_video_get_spu_delay", ((1,),), None, ctypes.c_int64, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_spu_description(p_mi):
    f = _Cfunctions.get("libvlc_video_get_spu_description", None) or _Cfunction(
        "libvlc_video_get_spu_description",
        ((1,),),
        None,
        ctypes.POINTER(TrackDescription),
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_video_get_teletext(p_mi):
    f = _Cfunctions.get("libvlc_video_get_teletext", None) or _Cfunction(
        "libvlc_video_get_teletext", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_title_description(p_mi):
    f = _Cfunctions.get("libvlc_video_get_title_description", None) or _Cfunction(
        "libvlc_video_get_title_description",
        ((1,),),
        None,
        ctypes.POINTER(TrackDescription),
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_video_get_track(p_mi):
    f = _Cfunctions.get("libvlc_video_get_track", None) or _Cfunction(
        "libvlc_video_get_track", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_track_count(p_mi):
    f = _Cfunctions.get("libvlc_video_get_track_count", None) or _Cfunction(
        "libvlc_video_get_track_count", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_get_track_description(p_mi):
    f = _Cfunctions.get("libvlc_video_get_track_description", None) or _Cfunction(
        "libvlc_video_get_track_description",
        ((1,),),
        None,
        ctypes.POINTER(TrackDescription),
        MediaPlayer,
    )
    return f(p_mi)


def libvlc_video_get_width(p_mi):
    f = _Cfunctions.get("libvlc_video_get_width", None) or _Cfunction(
        "libvlc_video_get_width", ((1,),), None, ctypes.c_int, MediaPlayer
    )
    return f(p_mi)


def libvlc_video_new_viewpoint():
    f = _Cfunctions.get("libvlc_video_new_viewpoint", None) or _Cfunction(
        "libvlc_video_new_viewpoint", (), None, ctypes.POINTER(VideoViewpoint)
    )
    return f()


def libvlc_video_set_adjust_float(p_mi, option, value):
    f = _Cfunctions.get("libvlc_video_set_adjust_float", None) or _Cfunction(
        "libvlc_video_set_adjust_float",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.c_float,
    )
    return f(p_mi, option, value)


def libvlc_video_set_adjust_int(p_mi, option, value):
    f = _Cfunctions.get("libvlc_video_set_adjust_int", None) or _Cfunction(
        "libvlc_video_set_adjust_int",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.c_int,
    )
    return f(p_mi, option, value)


def libvlc_video_set_aspect_ratio(p_mi, psz_aspect):
    f = _Cfunctions.get("libvlc_video_set_aspect_ratio", None) or _Cfunction(
        "libvlc_video_set_aspect_ratio",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_char_p,
    )
    return f(p_mi, psz_aspect)


def libvlc_video_set_callbacks(mp, lock, unlock, display, opaque):

    f = _Cfunctions.get("libvlc_video_set_callbacks", None) or _Cfunction(
        "libvlc_video_set_callbacks",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        VideoLockCb,
        VideoUnlockCb,
        VideoDisplayCb,
        ctypes.c_void_p,
    )
    return f(mp, lock, unlock, display, opaque)


def libvlc_video_set_crop_geometry(p_mi, psz_geometry):
    f = _Cfunctions.get("libvlc_video_set_crop_geometry", None) or _Cfunction(
        "libvlc_video_set_crop_geometry",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_char_p,
    )
    return f(p_mi, psz_geometry)


def libvlc_video_set_deinterlace(p_mi, psz_mode):
    f = _Cfunctions.get("libvlc_video_set_deinterlace", None) or _Cfunction(
        "libvlc_video_set_deinterlace",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_char_p,
    )
    return f(p_mi, psz_mode)


def libvlc_video_set_format(mp, chroma, width, height, pitch):
    f = _Cfunctions.get("libvlc_video_set_format", None) or _Cfunction(
        "libvlc_video_set_format",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_char_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
    )
    return f(mp, chroma, width, height, pitch)


def libvlc_video_set_format_callbacks(mp, setup, cleanup):
    f = _Cfunctions.get("libvlc_video_set_format_callbacks", None) or _Cfunction(
        "libvlc_video_set_format_callbacks",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        VideoFormatCb,
        VideoCleanupCb,
    )
    return f(mp, setup, cleanup)


def libvlc_video_set_key_input(p_mi, on):
    f = _Cfunctions.get("libvlc_video_set_key_input", None) or _Cfunction(
        "libvlc_video_set_key_input",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, on)


def libvlc_video_set_logo_int(p_mi, option, value):
    f = _Cfunctions.get("libvlc_video_set_logo_int", None) or _Cfunction(
        "libvlc_video_set_logo_int",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.c_int,
    )
    return f(p_mi, option, value)


def libvlc_video_set_logo_string(p_mi, option, psz_value):
    f = _Cfunctions.get("libvlc_video_set_logo_string", None) or _Cfunction(
        "libvlc_video_set_logo_string",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.c_char_p,
    )
    return f(p_mi, option, psz_value)


def libvlc_video_set_marquee_int(p_mi, option, i_val):
    f = _Cfunctions.get("libvlc_video_set_marquee_int", None) or _Cfunction(
        "libvlc_video_set_marquee_int",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.c_int,
    )
    return f(p_mi, option, i_val)


def libvlc_video_set_marquee_string(p_mi, option, psz_text):
    f = _Cfunctions.get("libvlc_video_set_marquee_string", None) or _Cfunction(
        "libvlc_video_set_marquee_string",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.c_char_p,
    )
    return f(p_mi, option, psz_text)


def libvlc_video_set_mouse_input(p_mi, on):
    f = _Cfunctions.get("libvlc_video_set_mouse_input", None) or _Cfunction(
        "libvlc_video_set_mouse_input",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_uint,
    )
    return f(p_mi, on)


def libvlc_video_set_scale(p_mi, f_factor):
    f = _Cfunctions.get("libvlc_video_set_scale", None) or _Cfunction(
        "libvlc_video_set_scale",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_float,
    )
    return f(p_mi, f_factor)


def libvlc_video_set_spu(p_mi, i_spu):
    f = _Cfunctions.get("libvlc_video_set_spu", None) or _Cfunction(
        "libvlc_video_set_spu",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_spu)


def libvlc_video_set_spu_delay(p_mi, i_delay):
    f = _Cfunctions.get("libvlc_video_set_spu_delay", None) or _Cfunction(
        "libvlc_video_set_spu_delay",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int64,
    )
    return f(p_mi, i_delay)


def libvlc_video_set_subtitle_file(p_mi, psz_subtitle):
    f = _Cfunctions.get("libvlc_video_set_subtitle_file", None) or _Cfunction(
        "libvlc_video_set_subtitle_file",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_char_p,
    )
    return f(p_mi, psz_subtitle)


def libvlc_video_set_teletext(p_mi, i_page):
    f = _Cfunctions.get("libvlc_video_set_teletext", None) or _Cfunction(
        "libvlc_video_set_teletext",
        (
            (1,),
            (1,),
        ),
        None,
        None,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_page)


def libvlc_video_set_track(p_mi, i_track):
    f = _Cfunctions.get("libvlc_video_set_track", None) or _Cfunction(
        "libvlc_video_set_track",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_int,
    )
    return f(p_mi, i_track)


def libvlc_video_take_snapshot(p_mi, num, psz_filepath, i_width, i_height):
    f = _Cfunctions.get("libvlc_video_take_snapshot", None) or _Cfunction(
        "libvlc_video_take_snapshot",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.c_uint,
        ctypes.c_char_p,
        ctypes.c_uint,
        ctypes.c_uint,
    )
    return f(p_mi, num, psz_filepath, i_width, i_height)


def libvlc_video_update_viewpoint(p_mi, p_viewpoint, b_absolute):
    f = _Cfunctions.get("libvlc_video_update_viewpoint", None) or _Cfunction(
        "libvlc_video_update_viewpoint",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        MediaPlayer,
        ctypes.POINTER(VideoViewpoint),
        ctypes.c_bool,
    )
    return f(p_mi, p_viewpoint, b_absolute)


def libvlc_vlm_add_broadcast(
    p_instance,
    psz_name,
    psz_input,
    psz_output,
    i_options,
    ppsz_options,
    b_enabled,
    b_loop,
):

    f = _Cfunctions.get("libvlc_vlm_add_broadcast", None) or _Cfunction(
        "libvlc_vlm_add_broadcast",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ListPOINTER(ctypes.c_char_p),
        ctypes.c_int,
        ctypes.c_int,
    )
    return f(
        p_instance,
        psz_name,
        psz_input,
        psz_output,
        i_options,
        ppsz_options,
        b_enabled,
        b_loop,
    )


def libvlc_vlm_add_input(p_instance, psz_name, psz_input):
    f = _Cfunctions.get("libvlc_vlm_add_input", None) or _Cfunction(
        "libvlc_vlm_add_input",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name, psz_input)


def libvlc_vlm_add_vod(
    p_instance, psz_name, psz_input, i_options, ppsz_options, b_enabled, psz_mux
):
    f = _Cfunctions.get("libvlc_vlm_add_vod", None) or _Cfunction(
        "libvlc_vlm_add_vod",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ListPOINTER(ctypes.c_char_p),
        ctypes.c_int,
        ctypes.c_char_p,
    )
    return f(
        p_instance, psz_name, psz_input, i_options, ppsz_options, b_enabled, psz_mux
    )


def libvlc_vlm_change_media(
    p_instance,
    psz_name,
    psz_input,
    psz_output,
    i_options,
    ppsz_options,
    b_enabled,
    b_loop,
):
    f = _Cfunctions.get("libvlc_vlm_change_media", None) or _Cfunction(
        "libvlc_vlm_change_media",
        (
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ListPOINTER(ctypes.c_char_p),
        ctypes.c_int,
        ctypes.c_int,
    )
    return f(
        p_instance,
        psz_name,
        psz_input,
        psz_output,
        i_options,
        ppsz_options,
        b_enabled,
        b_loop,
    )


def libvlc_vlm_del_media(p_instance, psz_name):
    f = _Cfunctions.get("libvlc_vlm_del_media", None) or _Cfunction(
        "libvlc_vlm_del_media",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name)


def libvlc_vlm_get_event_manager(p_instance):
    f = _Cfunctions.get("libvlc_vlm_get_event_manager", None) or _Cfunction(
        "libvlc_vlm_get_event_manager",
        ((1,),),
        class_result(EventManager),
        ctypes.c_void_p,
        Instance,
    )
    return f(p_instance)


def libvlc_vlm_get_media_instance_length(p_instance, psz_name, i_instance):
    f = _Cfunctions.get("libvlc_vlm_get_media_instance_length", None) or _Cfunction(
        "libvlc_vlm_get_media_instance_length",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_name, i_instance)


def libvlc_vlm_get_media_instance_position(p_instance, psz_name, i_instance):
    f = _Cfunctions.get("libvlc_vlm_get_media_instance_position", None) or _Cfunction(
        "libvlc_vlm_get_media_instance_position",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_float,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_name, i_instance)


def libvlc_vlm_get_media_instance_rate(p_instance, psz_name, i_instance):
    f = _Cfunctions.get("libvlc_vlm_get_media_instance_rate", None) or _Cfunction(
        "libvlc_vlm_get_media_instance_rate",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_name, i_instance)


def libvlc_vlm_get_media_instance_time(p_instance, psz_name, i_instance):
    f = _Cfunctions.get("libvlc_vlm_get_media_instance_time", None) or _Cfunction(
        "libvlc_vlm_get_media_instance_time",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_name, i_instance)


def libvlc_vlm_pause_media(p_instance, psz_name):
    f = _Cfunctions.get("libvlc_vlm_pause_media", None) or _Cfunction(
        "libvlc_vlm_pause_media",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name)


def libvlc_vlm_play_media(p_instance, psz_name):
    f = _Cfunctions.get("libvlc_vlm_play_media", None) or _Cfunction(
        "libvlc_vlm_play_media",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name)


def libvlc_vlm_release(p_instance):
    f = _Cfunctions.get("libvlc_vlm_release", None) or _Cfunction(
        "libvlc_vlm_release", ((1,),), None, None, Instance
    )
    return f(p_instance)


def libvlc_vlm_seek_media(p_instance, psz_name, f_percentage):
    f = _Cfunctions.get("libvlc_vlm_seek_media", None) or _Cfunction(
        "libvlc_vlm_seek_media",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_float,
    )
    return f(p_instance, psz_name, f_percentage)


def libvlc_vlm_set_enabled(p_instance, psz_name, b_enabled):
    f = _Cfunctions.get("libvlc_vlm_set_enabled", None) or _Cfunction(
        "libvlc_vlm_set_enabled",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_name, b_enabled)


def libvlc_vlm_set_input(p_instance, psz_name, psz_input):
    f = _Cfunctions.get("libvlc_vlm_set_input", None) or _Cfunction(
        "libvlc_vlm_set_input",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name, psz_input)


def libvlc_vlm_set_loop(p_instance, psz_name, b_loop):
    f = _Cfunctions.get("libvlc_vlm_set_loop", None) or _Cfunction(
        "libvlc_vlm_set_loop",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_int,
    )
    return f(p_instance, psz_name, b_loop)


def libvlc_vlm_set_mux(p_instance, psz_name, psz_mux):
    f = _Cfunctions.get("libvlc_vlm_set_mux", None) or _Cfunction(
        "libvlc_vlm_set_mux",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name, psz_mux)


def libvlc_vlm_set_output(p_instance, psz_name, psz_output):
    f = _Cfunctions.get("libvlc_vlm_set_output", None) or _Cfunction(
        "libvlc_vlm_set_output",
        (
            (1,),
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name, psz_output)


def libvlc_vlm_show_media(p_instance, psz_name):
    f = _Cfunctions.get("libvlc_vlm_show_media", None) or _Cfunction(
        "libvlc_vlm_show_media",
        (
            (1,),
            (1,),
        ),
        string_result,
        ctypes.c_void_p,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name)


def libvlc_vlm_stop_media(p_instance, psz_name):
    f = _Cfunctions.get("libvlc_vlm_stop_media", None) or _Cfunction(
        "libvlc_vlm_stop_media",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_int,
        Instance,
        ctypes.c_char_p,
    )
    return f(p_instance, psz_name)


def libvlc_vprinterr(fmt, ap):
    f = _Cfunctions.get("libvlc_vprinterr", None) or _Cfunction(
        "libvlc_vprinterr",
        (
            (1,),
            (1,),
        ),
        None,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_void_p,
    )
    return f(fmt, ap)


def libvlc_wait(p_instance):
    f = _Cfunctions.get("libvlc_wait", None) or _Cfunction(
        "libvlc_wait", ((1,),), None, None, Instance
    )
    return f(p_instance)


def callbackmethod(callback):
    return callback


if not hasattr(dll, "libvlc_free"):
    libc_path = find_library("c")
    if libc_path:
        libc = ctypes.CDLL(libc_path)
        libvlc_free = libc.free
    else:
        def libvlc_free(p):
            pass
    libvlc_free.argtypes = [ctypes.c_void_p]


def _dot2int(v):
    """(INTERNAL) Convert 'i.i.i[.i]' str to int."""
    t = [int(i) for i in v.split(".")]
    if len(t) == 3:
        if t[2] < 100:
            t.append(0)
        else:
            t[2:4] = divmod(t[2], 100)
    elif len(t) != 4:
        raise ValueError('"i.i.i[.i]": %r' % (v,))
    if min(t) < 0 or max(t) > 255:
        raise ValueError("[0..255]: %r" % (v,))
    i = t.pop(0)
    while t:
        i = (i << 8) + t.pop(0)
    return i


def hex_version():
    try:
        return _dot2int(__version__)
    except (NameError, ValueError):
        return 0


def libvlc_hex_version():
    try:
        return _dot2int(bytes_to_str(libvlc_get_version()).split()[0])
    except ValueError:
        return 0


def debug_callback(event, *args, **kwds):
    l = ["event %s" % (event.type,)]
    if args:
        l.extend(list(map(str, args)))
    if kwds:
        l.extend(sorted("%s=%s" % t for t in list(kwds.items())))
    print(("Debug callback (%s)" % ", ".join(l)))


def print_python():
    import platform
    print(f"Python {platform.python_version()} on {platform.system()} {platform.release()}")


def print_version():
    try:
        print(("%s: %s (%s)" % (os.path.basename(__file__), __version__, build_date)))
        print(("libVLC: %s (%#x)" % (bytes_to_str(libvlc_get_version()), libvlc_hex_version())))
        # print('libVLC %s' % bytes_to_str(libvlc_get_compiler()))
        if plugin_path:
            print(("plugins: %s" % plugin_path))
    except Exception:
        print(("Error: %s" % sys.exc_info()[1]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        from msvcrt import getch
    except ImportError:
        import termios
        import tty

        def getch():
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            return ch

    def end_callback(event):
        print(("End of media stream (event %s)" % event.type))
        sys.exit(0)

    echo_position = False

    def pos_callback(event, player):
        if echo_position:
            sys.stdout.write("\r%s to %.2f%% (%.2f%%)"
                % (event.type, event.u.new_position * 100, player.get_position() * 100)
            )
            sys.stdout.flush()

    if "-h" in sys.argv[:2] or "--help" in sys.argv[:2]:
        print(("Usage: %s [options] <movie_filename>" % sys.argv[0]))
        print("Once launched, type ? for help.")
        print("")

    elif "-v" in sys.argv[:2] or "--version" in sys.argv[:2]:
        print_version()
        print_python()
        print("")

    else:
        movie = os.path.expanduser(sys.argv.pop())
        if not os.access(movie, os.R_OK):
            print(("Error: %s file not readable" % movie))
            sys.exit(1)

        instance = Instance(["--sub-source=marq"] + sys.argv[1:])
        try:
            media = instance.media_new(movie)
        except (AttributeError, NameError) as e:
            print((
                "%s: %s (%s %s vs LibVLC %s)"
                % (
                    e.__class__.__name__,
                    e,
                    sys.argv[0],
                    __version__,
                    libvlc_get_version(),
                )
            ))
            sys.exit(1)
        player = instance.media_player_new()
        player.set_media(media)
        player.play()
        player.video_set_marquee_int(VideoMarqueeOption.Enable, 1)
        player.video_set_marquee_int(VideoMarqueeOption.Size, 24)  # pixels
        if False:
            player.video_set_marquee_int(VideoMarqueeOption.Timeout, 5000)
            t = media.get_mrl()
        else:
            player.video_set_marquee_int(VideoMarqueeOption.Timeout, 0)
            player.video_set_marquee_int(VideoMarqueeOption.Refresh, 1000)
            t = "%Y-%m-%d  %H:%M:%S"
        player.video_set_marquee_string(VideoMarqueeOption.Text, str_to_bytes(t))
        event_manager = player.event_manager()
        event_manager.event_attach(EventType.MediaPlayerEndReached, end_callback)
        event_manager.event_attach(EventType.MediaPlayerPositionChanged, pos_callback, player)

        def mspf():
            return int(1000 // (player.get_fps() or 25))

        def print_info():
            try:
                print_version()
                media = player.get_media()
                print(("State: %s" % player.get_state()))
                print(("Media: %s" % bytes_to_str(media.get_mrl())))
                print(("Track: %s/%s" % (player.video_get_track(), player.video_get_track_count())))
                print(("Current time: %s/%s" % (player.get_time(), media.get_duration())))
                print(("Position: %s" % player.get_position()))
                print(("FPS: %s (%d ms)" % (player.get_fps(), mspf())))
                print(("Rate: %s" % player.get_rate()))
                print(("Video size: %s" % str(player.video_get_size(0))))
                print(("Scale: %s" % player.video_get_scale()))
                print(("Aspect ratio: %s" % player.video_get_aspect_ratio()))
            # print('Window:' % player.get_hwnd()
            except Exception:
                print(("Error: %s" % sys.exc_info()[1]))

        def sec_forward():
            player.set_time(player.get_time() + 1000)

        def sec_backward():
            player.set_time(player.get_time() - 1000)

        def frame_forward():
            player.set_time(player.get_time() + mspf())

        def frame_backward():
            player.set_time(player.get_time() - mspf())

        def print_help():
            print("Single-character commands:")
            for k, m in sorted(keybindings.items()):
                m = (m.__doc__ or m.__name__).splitlines()[0]
                print(("  %s: %s." % (k, m.rstrip("."))))
            print("0-9: go to that fraction of the movie")

        def quit_app():
            sys.exit(0)

        def toggle_echo_position():
            global echo_position
            echo_position = not echo_position

        keybindings = {
            " ": player.pause,
            "+": sec_forward,
            "-": sec_backward,
            ".": frame_forward,
            ",": frame_backward,
            "f": player.toggle_fullscreen,
            "i": print_info,
            "p": toggle_echo_position,
            "q": quit_app,
            "?": print_help,
        }

        print(("Press q to quit, ? to get help.%s" % os.linesep))
        while True:
            k = getch()
            print(("> %s" % k))
            if k in keybindings:
                keybindings[k]()
            elif k.isdigit():
                player.set_position(float("0." + k))