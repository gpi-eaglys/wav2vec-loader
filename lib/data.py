"""
Data maintenance
"""
import logging
import os
import shutil

LOG = logging.getLogger(__name__)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))


def normalize_cv_audio():
    """
    Ensures that mp3 data is split up in directories named 00-ff based on file's the serial number.
    It is possible to dump lots of CV mp3 data into data dir, this scripts make sure that data paths are normalized.
    """
    dpath_mp3 = os.path.normpath(os.path.join(DATA_DIR, "mp3"))
    mv_tasks = []
    n_mp3 = 0
    for root, _, fnames in os.walk(DATA_DIR):
        for fname in [f for f in fnames if f.endswith(".mp3")]:
            n_mp3 += 1
            *_, serial = os.path.splitext(fname)[0].split("_")
            dname: str = "{:02x}".format(int(serial) % 256)

            fpath_src = os.path.join(root, fname)
            fpath_trg = os.path.join(dpath_mp3, dname, fname)
            if fpath_src == fpath_trg:
                continue
            if not os.path.isfile(fpath_trg):
                mv_tasks.append((fpath_src, fpath_trg))

    dnames = {os.path.dirname(t[1]) for t in mv_tasks}
    for dname in dnames:
        os.makedirs(dname, exist_ok=True)

    for src, dst in mv_tasks:
        shutil.move(src, dst)
    LOG.info(f"Found {n_mp3:5,} mp3 files")
    LOG.info(f"Moved {len(mv_tasks):5,} mp3 files")


if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(module)s.%(funcName)s %(message)s", level=logging.DEBUG)
    normalize_cv_audio()
