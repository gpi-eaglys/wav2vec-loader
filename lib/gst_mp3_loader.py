"""
This script does something.
"""
import os
import logging
import gi
import torch
import numpy as np
gi.require_version('Gst', '1.0')
from gi.repository import Gst

LOG = logging.getLogger(__name__)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


class Mp3ToTensor:
    """
    Sample code to show how to convert mp3 audio to torch tensor using gstreamer pipeline.

    Command line equivalent of:
        gst-launch-1.0 -e filesrc location=in.mp3 ! decodebin ! audioconvert ! audioresample ! audio/x-raw, rate=16000, channels=1, format=S16LE ! wavenc ! torchsink

    Features:
    - builds and links elements manually
    - demonstrates how to re-use the same pipeline
    """
    def __init__(self, max_buffer_size=16000*10):
        """
        Accepts maximum 10 seconds of audio.
        This buffer is preallocated.
        :param max_buffer_size:
        """
        Gst.init()
        self.pipeline = Gst.Pipeline.new("converter")

        self._el_filesrc = Gst.ElementFactory.make("filesrc", "src")

        self._el_dec = Gst.ElementFactory.make("decodebin", name="decodebin")
        self._el_conv = Gst.ElementFactory.make("audioconvert")
        self._el_resample = Gst.ElementFactory.make("audioresample")
        # set caps for audio format
        self._el_caps = Gst.ElementFactory.make("capsfilter", "caps")
        self._el_caps.set_property("caps", Gst.Caps.from_string("audio/x-raw, rate=16000, channels=1, format=S16LE"))
        # dump
        self._el_sink = Gst.ElementFactory.make("appsink", "torchsink")
        self._el_sink.set_property("sync", False)  # no clock sync is necessary
        self._el_sink.set_property("emit-signals", True)
        self._el_sink.set_property("max-buffers", 16000)  # buffer up to 1sec of audio before block
        self._el_sink.set_property("drop", False)  # do *not* ignore any frame

        self._el_sink.connect("new-sample", self._cb_on_new_sample)

        # build pipeline
        elems = [self._el_filesrc, self._el_dec, self._el_conv, self._el_resample, self._el_caps, self._el_sink]
        for elem in elems:
            if not elem:
                raise Exception("Failed to create GStreamer element.")
            self.pipeline.add(elem)

        # link elements
        for i in range(len(elems)-1):
            if elems[i].get_name() == "decodebin":  # dynamic linking for 'decodebin'
                elems[i].connect("pad-added", self._cb_on_pad_added, elems[i+1])
            else:
                elems[i].link(elems[i+1])

        # pre-allocated audio buffer
        self._buff = bytearray(max_buffer_size)
        self._buff_off = 0 # buffer offset == num of bytes arrived to appsink

    def _cb_on_new_sample(self, sink):
        """
        Callback to handle new arriving PCM data.
        """
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        success, mapinfo = buf.map(Gst.MapFlags.READ)  # access pointer to raw data
        if not success:
            return Gst.FlowReturn.ERROR
        self._buff[self._buff_off:self._buff_off + mapinfo.size] = mapinfo.data[:mapinfo.size]
        self._buff_off += mapinfo.size
        buf.unmap(mapinfo)
        # Alternatively: map to numpy buffer chunk by chunk
        # data = np.frombuffer(mapinfo.data, dtype=np.int16)
        # self.buffers.append(data)
        # self._tot_byte += len(mapinfo.data)
        # print(f"received: {mapinfo.size:,}")
        return Gst.FlowReturn.OK

    @staticmethod
    def _cb_on_pad_added(decodebin, pad, next_elem):
        """
        Callback to handle decodebin dynamically creating an output pad.
        Called when new input source is defined.
        """
        sink_pad = next_elem.get_static_pad("sink")
        if not sink_pad.is_linked():
            pad.link(sink_pad)

    def to_tensor(self, mp3_file):
        # Set input/output locations:
        self._el_filesrc.set_property("location", mp3_file)

        self._buff_off = 0  # reset buffer

        # Start processing
        msg = self.pipeline.set_state(Gst.State.PLAYING)
        if msg == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("Failed to start pipeline")

        # Wait for msg: EOS or ERROR
        bus = self.pipeline.get_bus()
        msg = bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE,
            Gst.MessageType.ERROR | Gst.MessageType.EOS
        )
        # DEBUG alternative: capture all events
        # while True:
        #     msg = bus.timed_pop(Gst.SECOND)
        #     if msg is None:
        #         print("--------------------- zombie")
        #         continue
        #     else:
        #         if msg.type == Gst.MessageType.ERROR:
        #             LOG.error(f"Failed to process {mp3_file}")
        #             break
        #         elif msg.type == Gst.MessageType.EOS:
        #             LOG.info(f"Done: {mp3_file} ({self._buff_off:,} bytes)")
        #             break
        #         elif msg.type == Gst.MessageType.STREAM_STATUS:
        #             status_type, owner = msg.parse_stream_status()
        #             # LOG.debug(f"Stream status: [{status_type.value_nick.upper()}]")
        #         elif msg.type == Gst.MessageType.STATE_CHANGED:
        #             old_state, new_state, pending_state = msg.parse_state_changed()
        #             LOG.debug(f"[{old_state.value_nick.upper()}] -> [{new_state.value_nick.upper()}]  {msg.src.get_name()}")
        #         else:
        #             LOG.debug(msg)

        # Reset pipeline (just in case)
        self.pipeline.set_state(Gst.State.NULL)
        if msg.type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            raise Exception(f"GStreamer Error: {err} ({debug})")

        tensor = torch.frombuffer(self._buff[:self._buff_off], dtype=torch.int16)

        LOG.debug(f"Done: {mp3_file} ({self._buff_off:,} bytes)")
        return tensor

