# Data Loading for Wav2vec model tuning
Experimenting with custom data loaders for wav2vec fine-tuning. \
Ultimate goal:  \
* to speed up training by optimizing data loading
Intermediate goals: \
* converting mp3 to PCM in memory (no file IO)
* applying audio agumentation in memory
* caching data - as much as possible  
* sensible logging 
  * not using don't use tqdm 
  * as a matter of fact: minimizing  stdout usage 

# Experiments 

## Experiment 1
* using custom data loader: 
  * gstreamer-based audio processing 
  * loads mp3 and converts it to PCM
  * converts PCM to torch tensor
* process: single iteration over an epoch of data batches 
  * variable number of processes (1-16) (16 cores on the running PC)
  * variable batch size (1-20)
* data: 
  * input: 100 mp3 files
  * output: padded tensors - direct input to wav2vec fine-tuning
  * labels -> dummy labels are generated
* source code: [exp1-parallel-audio-loader.py](src/exp1-parallel-audio-loader.py)

### Results

![exp1-boxplot-per-jobs.png](data/pix/exp1-boxplot-per-jobs.png)

Notes:
* number of jobs == number of data loader workers
* process data loading is the slowest
* increasing num of workers beyond a point does not improve speed 
  * torch documentation suggest setting the number of workers to the number of physical cores
    * hm, how about physcial cores -1? 
  * but the optimal number of workers depends on several other factors -> try and experiment

![exp1-boxplot-per-batchsize.png](data/pix/exp1-boxplot-per-batchsize.png)

Notes:
* variation is rather small
* single batch size is sub-optimal


### How many processes?
* how many data loader workers to be selected?   
* it depends... 
   * processing duration within each dataloader (load and collate)
   * speed of IO: wherever the data comes from (local FS, NFS/SMB mount)
   * number of physical CPU cores in the system
   * GPU processing time of a batch
* advice: try it yourself 

### What batch size?
* must be set in a way to maximize GPU utilization - without out-of-memory errors

# Setup
## Installing gstreamer for Python  
* DOES *NOT* install out of the box
* both system and Python dependencies must be installed carefully
* the following setup worked for me (WSL/Ubuntu 24.04)
```bash 
sudo apt  install gstreamer1.0-tools \
                  gstreamer1.0-plugins-{base,good,bad,ugly} \
                  gstreamer1.0-libav \
                  gir1.2-gst-1.0
```

```bash
# works
pip install pygobject==3.50.0
pip install PyGObject-stubs==2.13.0

# fails: pip install pygobject
```



