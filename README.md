# WfmBuilder

GUI based Python program to send custom waveforms to a Agilent/Keysight 33600B

## Getting Started

Initial instructions:

### Prerequisites

* Python 2.7
* pyvisa
* matplotlib
* numpy
* PyQt4
* pyqtgraph (beyond v3.0)

### Installing

I suggest downloading WinPython as it will install many prerequisites.
Use pip to install other preq's.
Download .zip file or clone from GitHub url into local directory.


## Operation

* When GUI opens, it will scan for local GPIB, USB, etc. connections.
* Select your intrument address from this list to connections
* Hit "reset" button to reset instrument.
* In the main window, you can now build a waveform using strings
### Defining waveform 1) Alt. ramp, delay
* Define waveform functions separated by space
* Begin with 2 string qualifier, followed by variable number of csv inputs to be interpreted as floats:

```
dl1e05 #delay in seconds
rm45e6 #ramp in V/s slope
er1e4,0.05 #exponential ramp with time constant in s, and total time of section
cs5e6,1,0.5  #cosine builder, set period in s, start phase/pi, end phase/pi (1,2 = valley to valley) 
```
### Defining waveform 2) Amp. step
* Then define amplitude step for each waveform

```
0 1 2 1
```
* This will turn boxes black, indicating you should hit 'enter' when selected to upload to the insturment. Instrument will turn off when uploading waveform, then go to the previous state. 

### Other options
* Can change output load, sample rate, offset voltage, and of course turn it on/off.
## Versioning

I use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/dspen/wfmbuilder/tags). 

## Authors

* **Daryl Spencer** - *Initial work* - (https://github.com/dspen)

## License

This project is licensed under the GNU GPLv3 License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments



