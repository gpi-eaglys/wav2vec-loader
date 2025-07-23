"""
Multiprocess dataloader for audio data.
"""
import os
import logging
import random
import datetime
from typing import Callable, List, Dict
import torch

from gst_mp3_loader import Mp3ToTensor


LOG = logging.getLogger(__name__)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))


class AudioData:
    def __init__(self, uid: str = None, path: str = None):
        self.uid = uid
        self.path = path
        self.samples = None


class AudioDataLoader(torch.utils.data.IterableDataset):
    """
    Caching
    (1) mp3 -> tensor
       - using GST pipeline

    (2) Caching

    """
    @staticmethod
    def init(worker_id):
        """
        Called in every worker process.
        Gets a copy of 'AudioDataLoader'

        :param worker_id:
        :return:
        """
        worker_info = torch.utils.data.get_worker_info()
        loader: AudioDataLoader = worker_info.dataset  # copoy of dataset in this worker process
        loader.id = worker_info.id
        loader.pid = os.getpid()

        for uid in loader._uids:
            *_, serial = os.path.basename(uid).split("_")
            if int(serial) % worker_info.num_workers == loader.id:
                loader._data.append(AudioData(uid=uid, path=loader._fun_uid2path(uid)))
        LOG.debug(f"audio provider={loader.id} size={len(loader._data)}")

        # each worker has its instance of GStreamer processor
        loader.gst_pipeline = Mp3ToTensor()


    def __init__(self, uid_file: str, uid2path_fun: Callable[[str], str]):
        """
        Called only once, copied to other processes

        :param uid_file: list of utterance ids
        """
        super(AudioDataLoader).__init__()
        self.id = -1
        self.pid = -1
        self._fun_uid2path: Callable = uid2path_fun
        self._data: List[AudioData] = []
        self._uids: List[str] = [] # this will be copied to all processes
        LOG.debug(f"Loading uid file: {uid_file}")
        with open(uid_file, "r") as fh:
            for line in fh:
                line = line.strip()
                if line == "":
                    continue
                self._uids.append(line)
        self.gst_pipeline = None  # to be populated in the worker process


    def __iter__(self):
        audio: AudioData
        for audio in self._data:
            tensor = self.gst_pipeline.to_tensor(audio.path)
            #TODO: read from file, convert, augment
            # time.sleep(1 + random.random()*1)
            size = random.randint(2, 16)
            yield {"label": audio.uid, "samples": tensor}


class Collator:
    """
    Runs on the same process as the data loader worker.
    Collates data from a single loader.

    Expected input for wav2vec2
    ['input_values', 'attention_mask', 'labels']

    pad for labels      :-100
    pad for input_values:   0
    pad for attention_mask: 0 (vs 1)
    """
    def __init__(self):
        self.pad_lab = -100
        self.pad_audio = 0
        self.pad_mask = 0

    def collate(self, batch: List[Dict]):
        tensors = [d["samples"] for d in batch]
        max_len = max(t.size(0) for t in tensors)

        # allocate 2D
        mat_samples = torch.full((len(batch), max_len), fill_value=self.pad_audio, dtype=tensors[0].dtype)
        mat_mask =  torch.full((len(batch), max_len), fill_value=self.pad_mask, dtype=tensors[0].dtype)
        # TODO: pre-allocate matrices in __init__
        # TODO: get max sizes for audio and for labels => possible

        # fill in
        for idx, tensor in enumerate(tensors):
            mat_samples[idx, :tensor.shape[0]] = tensor
            mat_mask[idx, :tensor.shape[0]] = 1

        LOG.debug(f"Collating {len(batch)} samples")
        return {
            "input_values": mat_samples,
            "attention_mask": mat_mask
        }




def test_tensor_loader(batch_size=4, num_workers=3) -> None:
    """
    Loads 100 audio in parallel
    :return:
    """
    fpath_uid = os.path.join(DATA_DIR, "sample-100.uid")

    collator = Collator()
    data_provider = AudioDataLoader(uid_file=fpath_uid,
                                      uid2path_fun=lambda x: os.path.join(DATA_DIR, "mp3", f"{x}.mp3"))

    t0 = datetime.datetime.now()
    data_loader = torch.utils.data.DataLoader(dataset=data_provider,
                                              batch_size=batch_size, num_workers=num_workers,
                                              worker_init_fn=AudioDataLoader.init,
                                              collate_fn=collator.collate,
                                              pin_memory=True)
    n_sample, n_batch = 0, 0
    for batch in data_loader:
        n_batch += 1
        n_sample_in_batch = batch["input_values"].shape[0]
        n_sample += n_sample_in_batch
        LOG.debug(f"batch {n_batch:3d}. size={n_sample_in_batch}")

    t1 = datetime.datetime.now()
    LOG.info(f"Loaded {n_sample:,} samples in\t{n_batch:,}\tbatches - batch-size\t{batch_size}\tnum_worker\t{num_workers}\t{(t1 - t0).total_seconds()}")


def run_exp1():
    for batch_size in range(1, 21):
        for num_workers in range(1, 17):
            test_tensor_loader(batch_size=batch_size, num_workers=num_workers)


if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s [PID:%(process)d] [%(levelname)s] %(module)s.%(funcName)s %(message)s", level=logging.INFO)
    #test_tensor_loader(batch_size=4, num_workers=3)
    run_exp1()
