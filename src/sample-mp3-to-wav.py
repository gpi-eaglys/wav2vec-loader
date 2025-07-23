"""
This script does something.
"""
import logging
import os
import time

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


LOG = logging.getLogger(__name__)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def get_pipe_mp3_to_wav() -> str:
    """
    location={mp3_file}
    :param mp3_file:
    :return:
    """
    return f"filesrc name=src  " \
           "! decodebin ! audioconvert ! audioresample " \
           "! audio/x-raw, rate=16000, channels=1, format=S16LE "\
           "! wavenc " \
           "! filesink name=sink"""


def get_pipe_minimal() -> str:
    return "audiotestsrc wave=sine freq=440 num-buffers=16000 " \
           "! audioresample "\
           "! audio/x-raw,rate=16000 ! wavenc "\
           "! filesink location=fake440.wav"


class GstPipeline:
    def __init__(self, name: str):
        self.pipe_str = get_pipe_mp3_to_wav()
        Gst.init(None)
        self.pipeline = Gst.parse_launch(self.pipe_str)
        self.pipeline.set_name(name)
        self.filesrc = self.pipeline.get_by_name("src")
        self.filesink = self.pipeline.get_by_name("sink")
        # self.loop = GLib.MainLoop()
        self.init()

    def process(self, audio_path: str, output_path: str, blocking: bool = True):
        outdir = os.path.dirname(output_path)
        if outdir != "":
            os.makedirs(outdir, exist_ok=True)
        self.pipeline.set_state(Gst.State.NULL)  # Reset pipeline
        self.filesrc.set_property("location", audio_path)
        self.filesink.set_property("location", output_path)
        self.pipeline.set_state(Gst.State.PLAYING)

        if blocking:
            bus = self.pipeline.get_bus()
            msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
            self.pipeline.set_state(Gst.State.NULL)
        print("Done")

    def handle_bus_messages(self, bus, msg):
        print(msg)

    def init(self):
        input_pipeline_bus = self.pipeline.get_bus()
        input_pipeline_bus.add_signal_watch()
        input_pipeline_bus.connect("message", self.handle_bus_messages)

        # input_pipeline_bus.connect("message", AudioDataProvider._gst_on_msg, loop, src)

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        # self.loop.run()

    def teardown(self):
        self.pipeline.set_state(Gst.State.NULL)





def dev() -> None:
    gst_chain = "filesrc location={}  ! decodebin ! audioconvert ! audioresample !  audio/x-raw, rate=16000, channels=1, format=S16LE ! wavenc ! appsink name=sink"

    fpath_mp3 = "/home/kinoko/GIT/eaglys/wav2vec-loader/data/mp3/0a/common_voice_ja_36339466.mp3"
    fpath_wav = "{}.wav".format(os.path.splitext(os.path.basename(fpath_mp3))[0])

    gst = GstPipeline("mp3-converter")
    gst.process(fpath_mp3, fpath_wav)


if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(module)s.%(funcName)s %(message)s", level=logging.DEBUG)
    dev()
