"""
Multiprocess dataloader for audio data.
"""
import logging
import os
import time
import random
import shutil
from typing import Callable, List, Dict
import datetime
import numpy as np

import torch
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


LOG = logging.getLogger(__name__)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))


def organize_cv_mp3():
    dpath_mp3 = os.path.normpath(os.path.join(DATA_DIR, "mp3"))
    copy_tasks = []
    for fname in os.listdir(dpath_mp3):
        if not fname.endswith(".mp3"):
            continue
        *_, serial = os.path.splitext(fname)[0].split("_")
        dname: str = "{:02x}".format(int(serial) % 256)

        fpath_src = os.path.join(dpath_mp3, fname)
        fpath_trg = os.path.join(dpath_mp3, dname, fname)
        if not os.path.isfile(fpath_trg):
            copy_tasks.append((fpath_src, fpath_trg))

    dnames = {os.path.dirname(t[1]) for t in copy_tasks}
    for dname in dnames:
        os.makedirs(dname, exist_ok=True)

    for src, dst in copy_tasks:
        shutil.move(src, dst)


def import_gst():
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
    Gst.init(None)
    print("GStreamer version:", Gst.version_string())


class GstPipeline:
    def __init__(self, pipe):
        self.pipe_str = pipe
        self.pipe = Gst.parse_launch(self.pipe_str)

    def init(self):
        input_pipeline_bus = self.get_bus()
        input_pipeline_bus.add_signal_watch()
        input_pipeline_bus.connect("message", AudioDataProvider._gst_on_msg, loop, src)

    def teardown(self):
        self.pipe


class AudioData:
    def __init__(self, uid: str = None, path: str = None):
        self.uid = None
        self.path = path
        self.samples = None


class AudioDataProvider(torch.utils.data.IterableDataset):
    """
    Caching
    (1) mp3 -> pcm
       - pipeline: 'gst mp3_to_wav'
       - input:  .mp3 file
       - output:  raw audio (bytes)

    (2) Augmentation

    (3)


    iter:   iterates over


    """
    @staticmethod
    def init(worker_id):
        worker_info = torch.utils.data.get_worker_info()
        prov: AudioDataProvider = worker_info.dataset  # the dataset copy in this worker process
        prov.id = worker_info.id
        prov.pid = os.getpid()

        for uid in prov._uids:
            *_, serial = os.path.basename(uid).split("_")
            if int(serial) % worker_info.num_workers == prov.id:
                prov._data.append(AudioData(uid=uid, path=prov._fun_uid2path(uid)))
        LOG.info(f"audio provider={prov.id} size={len(prov._data)}")

    def __init__(self, uid_file: str, uid2path_fun: Callable[[str], str]):
        """
        Called only once, copied to other processes

        :param uid_file: list of utterance ids
        """
        super(AudioDataProvider).__init__()
        self.id = -1
        self.pid = -1
        self._fun_uid2path: Callable = uid2path_fun
        self._data: List[AudioData] = []
        self._uids: List[str] = []
        with open(uid_file, "r") as fh:
            for line in fh:
                line = line.strip()
                if line == "":
                    continue
                self._uids.append(line)

        self._gst_pipelines = {
            "mp3_to_pcm": "filesrc location={}  ! decodebin ! audioconvert ! audioresample !  audio/x-raw, rate=16000, channels=1, format=S16LE ! wavenc ! appsink name=sink",
            "mp3_to_pcm": "appsrc name=src ! ",
        }

    def _gst_on_sample(self, sink, src):
        sample = sink.emit('pull-sample')
        inp_buf = sample.get_buffer()
        result, map_info = inp_buf.map(Gst.MapFlags.READ)
        if result:
            # 映像フレーム取得
            frame_bgr = np.ndarray(shape=(), dtype=np.int16, buffer=map_info.data)
        return Gst.FlowReturn.OK

    @staticmethod
    def _gst_on_msg(bus, message, loop, src):
        t = message.type
        src_name = message.src.get_name()
        if t == Gst.MessageType.EOS:
            print(f"{src_name} received End-Of-Stream")
        if src_name == "input_pipeline":
            src.emit('end-of-stream')
        elif src_name == "output_pipeline":
            loop.quit()

    def _gst_teardown(self):

    def setup(self):
        gst_pipeline_in = Gst.parse_launch(self._gst_pipelines["mp3_to_pcm"])
        gst_pipeline_out = Gst.parse_launch(self._gst_pipelines["mp3_to_pcm"])

        src = gst_pipeline_out.get_by_name("src")
        sink = gst_pipeline_in.get_by_name("sink")

        sink.set_property("emit-signals", True)
        sink.connect("new-sample", self._gst_on_sample, src)

        loop = GLib.MainLoop()

        # for pipe_name, pipe_str in self._gst_pipelines.items():

        input_pipeline.set_name("input_pipeline")

        # バスの設定
        input_pipeline_bus = gst_pipeline_in.get_bus()
        input_pipeline_bus.add_signal_watch()
        input_pipeline_bus.connect("message", AudioDataProvider._gst_on_msg, loop, src)
        output_pipeline_bus = gst_pipeline_out.get_bus()
        output_pipeline_bus.add_signal_watch()
        output_pipeline_bus.connect("message", AudioDataProvider._gst_on_msg, loop, src)

        # start pipelines
        gst_pipeline_in.set_state(Gst.State.PLAYING)
        gst_pipeline_out.set_state(Gst.State.PLAYING)

        try:
            loop.run()
        except KeyboardInterrupt:
            pass
        # パイプラインを停止
        gst_pipeline_in.set_state(Gst.State.NULL)
        gst_pipeline_out.set_state(Gst.State.NULL)


    def __iter__(self):
        for audio in self._data:
            #TODO: read from file, convert, augment
            time.sleep(1 + random.random()*1)
            size = random.randint(2, 16)
            yield {"label": audio.uid, "samples": torch.rand(size,)}


class Collator:
    """
    Runs on same process as data loader worker.
    Collates data from a single loader.

    ['input_values', 'attention_mask', 'labels']

    pad (labels) -100
    pad (input_values) 0
    pad(attention_mask) 0 (vs 1)
    """
    def __init__(self):
        self.pad_lab = -100
        self.pad_audio = 0
        self.pad_mask = 0
        # TODO: pre-allocate matrices in __init__
        # TODO: get max sizes for audio and for labels => possible

    def collate(self, batch: List[Dict]):
        tensors = [d["samples"] for d in batch]
        max_len = max(t.size(0) for t in tensors)

        # allocate 2D
        mat_samples = torch.full((len(batch), max_len), fill_value=self.pad_audio, dtype=tensors[0].dtype)
        mat_mask =  torch.full((len(batch), max_len), fill_value=self.pad_mask, dtype=tensors[0].dtype)
        # fill in
        for idx, tensor in enumerate(tensors):
            mat_samples[idx, :tensor.shape[0]] = tensor
            mat_mask[idx, :tensor.shape[0]] = 1

        LOG.info(f"Collating {len(batch)} samples")
        return {
            "input_values": mat_samples,
            "attention_mask": mat_mask
        }



def dev() -> None:
    fpath_uid = os.path.join(DATA_DIR, "sample-100.uid")
    # organize_cv_mp3()
    # import_gst()

    collator = Collator()
    data_provider = AudioDataProvider(uid_file=fpath_uid,
                                      uid2path_fun=lambda x: os.path.join(DATA_DIR, "mp3", f"{x}.mp3"))

    t0 = datetime.datetime.now()
    data_loader = torch.utils.data.DataLoader(data_provider, batch_size=10, num_workers=16,
                                              worker_init_fn=AudioDataProvider.init,
                                              collate_fn=collator.collate,
                                              pin_memory=True)
    n = 0
    for batch in data_loader:
        n += 1
        LOG.info(f"batch {n}. loaded={batch['input_values'].shape}")

    t1 = datetime.datetime.now()
    print(t1-t0)

if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s [PID:%(process)d] [%(levelname)s] %(module)s.%(funcName)s %(message)s", level=logging.DEBUG)
    dev()

# Data
# batch_size=10, num_workers=1   0:02:27.701387  100%
# batch_size=10, num_workers=8   0:00:34.696862
# batch_size=10, num_workers=10  0:00:29.392929
# batch_size=10, num_workers=12  0:00:19.622114
# batch_size=10, num_workers=16  0:00:18.828194   12.75% of single threaded

