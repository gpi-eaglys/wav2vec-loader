# Data Loading for Wav2Vec
Custom data loader for wav2vec training

# Dev notes

## Python bindings  gstreamer  
* both system and python dependencies are needed

``` 
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