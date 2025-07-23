"""
Demonstration of creating an mp3-to-wav GST pipeline in Python
"""
import logging
import os

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst


LOG = logging.getLogger(__name__)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(REPO_DIR, "data")


class Mp3ToWavConverter:
    """
    Sample mp3-to-wav converter to demonstrate GST pipeline in pure Python.
    Command line equivalent of:
        gst-launch-1.0 -e filesrc location=in.mp3 ! decodebin ! audioconvert ! audioresample ! audio/x-raw, rate=16000, channels=1, format=S16LE ! wavenc ! filesink location=out.wav

    Features:
    - builds and links elements manually
    - demonstrates how to re-use the same pipeline
    """
    def __init__(self):
        Gst.init()
        self.pipeline = Gst.Pipeline.new("converter")

        self._elem_filesrc = Gst.ElementFactory.make("filesrc", "src")

        self._elem_dec = Gst.ElementFactory.make("decodebin", name="decodebin")
        self._elem_conv = Gst.ElementFactory.make("audioconvert")
        self._elem_resample = Gst.ElementFactory.make("audioresample")
        # set caps for audio format
        self._elem_caps = Gst.ElementFactory.make("capsfilter", "caps")
        self._elem_caps.set_property("caps", Gst.Caps.from_string("audio/x-raw, rate=16000, channels=1, format=S16LE"))
        # dump
        self._elem_wavenc = Gst.ElementFactory.make("wavenc")
        self._elem_sink = Gst.ElementFactory.make("filesink")

        # build pipeline
        elems = [self._elem_filesrc, self._elem_dec, self._elem_conv, self._elem_resample, self._elem_caps, self._elem_wavenc, self._elem_sink]
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

    @staticmethod
    def _cb_on_pad_added(decodebin, pad, next_elem):
        """
        This callback is called when decodebin creates an output pad dynamically (when new input source is defined)
        """
        sink_pad = next_elem.get_static_pad("sink")
        if not sink_pad.is_linked():
            pad.link(sink_pad)

    def convert(self, in_mp3, out_wav):
        # Set input/output locations:
        self._elem_filesrc.set_property("location", in_mp3)
        self._elem_sink.set_property("location", out_wav)

        # Reset pipeline -> rebuilds dynamic pads
        # self.pipeline.set_state(Gst.State.NULL)

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
        #     msg = self.bus.timed_pop(Gst.SECOND)
        #     if msg is None:
        #         print("--------------------- zombie")
        #         continue
        #     else:
        #         if msg.type == Gst.MessageType.ERROR:
        #             LOG.error(f"Failed to process {audio_path}")
        #             break
        #         elif msg.type == Gst.MessageType.EOS:
        #             LOG.info(f"Done: {output_path}")
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

        ok = self.pipeline.set_state(Gst.State.NULL)

        LOG.info(f"Converted: {out_wav}")



def test_batch():
    """
    Converts all mp3 files in 'data' dir to wav file in 'build' dir
    """
    outdir = os.path.join(REPO_DIR, "build", "wav")
    # create output dirs in advance
    for i in range(256):
        os.makedirs(os.path.join(outdir, f"{i:02x}"), exist_ok=True)

    converter = Mp3ToWavConverter()

    for root, _, fnames in os.walk(DATA_DIR):
        for fname in [f for f in fnames if f.endswith(".mp3")]:
            fpath_mp3 = os.path.join(root, fname)
            relpath_mp3 = os.path.relpath(fpath_mp3, DATA_DIR)  # relative to

            fname_wav = "{}.wav".format(os.path.splitext(relpath_mp3)[0]).replace("mp3/", "")
            fpath_wav = os.path.join(outdir, fname_wav)
            converter.convert(fpath_mp3, fpath_wav)

def test_one() -> None:
    fpath_mp3 = os.path.join(DATA_DIR, "mp3", "0a", "common_voice_ja_36339466.mp3")
    fpath_wav = os.path.join(REPO_DIR, "build", "wav", "0a", "common_voice_ja_36339466.mp3")

    assert os.path.isfile(fpath_mp3)
    os.makedirs(os.path.dirname(fpath_wav), exist_ok=True)

    converter = Mp3ToWavConverter()
    converter.convert(fpath_mp3, fpath_wav)


if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(module)s.%(funcName)s %(message)s", level=logging.DEBUG)
    # test_one()
    test_batch()
