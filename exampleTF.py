# -*- coding: utf-8 -*-
"""
Created on Wed Mar 21 00:23:19 2018
Practice using Scipy functions

@author: Daryl

https://stackoverflow.com/questions/12233702/fitting-transfer-function-models-in-scipy-signal
https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.deconvolve.html
https://stackoverflow.com/questions/38146985/inverse-filtering-using-python
https://stackoverflow.com/questions/20036663/understanding-numpys-convolve
"""

from scipy.optimize import curve_fit
import scipy.signal as signal
import matplotlib.pyplot as plt
import numpy as np

plt.close('all')


def buildWFM(ftext, amptext, srate=1e5, plot=True):
    wfm=np.zeros(0)
    stor=np.zeros(0)
    aptr=0
    fstring = unicode(ftext).split()
    ampString = unicode(amptext).split() #convert amplitude strings
#        amp1=map(float,ampString) #map amplitude data to numbers
#        fdata = map(float, fstring)
    
    
    for i in range(len(fstring)):
        func = fstring[i][:2]; #read first 2 strings for func
        data = map(float,fstring[i][2:].split(',')); #read remainder for constant
        amp1 = map(float,ampString[i].split(','))
        if func == 'rm': #ramp
            if data==0: print('ramp0');continue;
            samp=abs(int(amp1[0]*srate/data[0]))
            newpt=aptr+float(data[0])*samp/srate
            stor=np.linspace(aptr,newpt,num=samp)
#                print('ramp')
            aptr=newpt
        elif func == 'dl': #delay
            samp=abs(int(srate*data[0]))
            newpt=aptr+float(amp1[0]) #Amp jump during delay section
            stor=np.linspace(newpt,newpt,num=samp) #Amp level during delay
#                print('delay')
            aptr=newpt
        elif func == 'er': #build exponential rise f(t1,ttotal)=A-A*exp(-t1)
            if len(data)!=2: print('Exp. needs 2 inputs (E.g.: er5,10)'); continue;
            samp=abs(int(srate*data[1]))
            x=np.linspace(0,data[1],num=samp)
            stor=-amp1[0]*np.exp(-data[0]*x)+aptr+amp1[0]
            aptr=stor[-1]
        elif func == 'dr': #double exp. rise, f(t1,t2,ttotal)=A1*exp(t1)+A2*exp(t2)
            if len(data)!=3: print('Exp. needs 3 inputs (E.g.: dr5,10,0.1)'); continue;
            samp=abs(int(srate*data[2]))
            x=np.linspace(0,data[2],num=samp)
            stor=-amp1[0]*np.exp(-data[0]*x) - amp1[1]*np.exp(-data[1]*x) + aptr + (amp1[0]+amp1[1]);
            aptr=stor[-1]
        else: print('Badly formed function at pos%s'%(i+1))
        wfm=np.hstack((wfm,stor))
        wfmT=np.linspace(0, len(wfm)/srate, num=len(wfm))
        if plot:
            plt.figure()
            plt.plot(wfmT, wfm)
    return wfmT, wfm
#
def buildWave(wfm, num=3, start=0, srate=1e5, plot=True):
    wfm = np.tile(wfm,num)
    wfmT=np.linspace(0, len(wfm)/srate, num=len(wfm))
    if plot:
        plt.figure()
        plt.plot(wfmT, wfm)
    return wfmT, wfm

def convolveWFM(impulse, wfm, plot=True):
    wfmcon = signal.convolve(impulse, wfm);
    wfmT=np.linspace(0, len(wfmcon)/srate, num=len(wfmcon))
    if plot:
        plt.figure()
        plt.plot(wfmT, wfmcon)
    return wfmT, wfmcon

def buildFFT(wfm, srate=1e5, plot=True):
    n = len(wfm)
    d = 1./srate
    hs = np.fft.fft(wfm)
    hs = np.fft.fftshift(hs)
    amps = np.abs(hs)
    fs = np.fft.fftfreq(n, d)
    fs = np.fft.fftshift(fs)
    if plot:
        plt.figure()
        plt.semilogx(fs, 20*np.log10(amps), '.-', markersize=2)
        plt.ylim([-100, plt.ylim()[1]])
    return fs, hs

def deconvolveWFM(wfm, impulse_resp, plot=True):
    padL = len(impulse_resp)-1
    wfm = np.pad(wfm, (0,padL), 'constant')
    precomp, remainder = signal.deconvolve(wfm, impulse_resp)
    if plot:
        plt.figure()
        plt.plot(wfm)
        plt.plot(precomp)
        plt.xlabel('Sample')
        plt.ylabel('Amplitude')
    return precomp, remainder

srate=1.0e2
c = np.exp(-np.arange(10)/10)
wfmT, wfm = buildWFM('dl2 rm5 dl2 rm-.2 dl1', '0 2.5 0 2.5 0', srate=srate)
wavT, wav = buildWave(wfm, num=5, srate=srate)
wfmT, wfmcon = convolveWFM(c, wav)
buildFFT(wav, srate=srate)


#%% Smooth square wave
sig = wfm
#sig = np.repeat([0., 1.,1., 1., 0.], 1000)
sigfs, sighs = buildFFT(sig)
plt.xlabel('Freq. (Hz)')
plt.ylabel('Filter Amp. Response (dB)')
#win = signal.exponential(int(10*srate), center=0, sym=0, tau=int(1*srate))
win=signal.hann(int(10000/srate), sym=1)+1e-2*np.ones(int(10000/srate))
win=win[len(win)/2:]
win=win/sum(win)
precomp, remainder = deconvolveWFM(sig, win)
filtered = signal.convolve(sig, win, mode='full')# / sum(win)
adjusted = signal.convolve(precomp, win, mode='full')

import matplotlib.pyplot as plt
fig, (ax_orig, ax_win, ax_filt, ax_prec, ax_adjusted) = plt.subplots(5, 1, sharex=True)
ax_orig.plot(sig)
ax_orig.set_title('Original pulse')
ax_orig.margins(0, 0.1)
ax_win.plot(win)
ax_win.set_title('Filter impulse response')
ax_win.margins(0, 0.1)
ax_filt.plot(filtered)
ax_filt.set_title('Filtered signal')
ax_filt.margins(0, 0.1)
ax_prec.plot(precomp)
ax_prec.set_title('Precompensate signal')
ax_prec.margins(0, 0.1)
ax_adjusted.plot(adjusted)
ax_adjusted.set_title('Adjusted signal')
ax_adjusted.margins(0, 0.1)
fig.tight_layout()
fig.show()

#%% Convolve function, ptsC = n1+n2-1 (for n2>n1); also: 1+ |n1-n2| + 2*(min(n1,n2)-1)
original = [0, 1, 0, 0, 1, 1, 0, 0]
#original = np.ones(8)
impulse_response = [2, 1, 0]
#impulse_response = np.pad(impulse_response, (0,len(original)-len(impulse_response)), 'constant')
recorded = signal.convolve(impulse_response, original, mode='full')

recovered, remainder = signal.deconvolve(recorded, impulse_response)

print([original,recorded,recovered])
plt.figure();
plt.plot(original)
plt.plot(recorded)
plt.plot(recovered)
#%% Deconvolve function, ptsD = 1+|na-nb|. Zeropad orginal (longer wave) by nb-1
original = [0, 1, 0, 0, 1, 1, 0, 0]
#original = np.ones(8)
impulse_response = [2, 1, 0]
padL = len(impulse_response)-1
originalpd = np.pad(original, (padL,padL), 'constant')
#precomp, remainder = signal.deconvolve(original, impulse_response)
precomp, remainder = deconvolveWFM(original, impulse_response)
recorded = signal.convolve(impulse_response, precomp, mode='full')


print([original,recorded,recovered])
plt.figure();
plt.plot(original[:-padL])
plt.plot(precomp)
plt.plot(recorded[:-padL])
#%%% Impulse example 2
imp = signal.unit_impulse(100, 'mid')
b, a = signal.butter(4, 0.2)
response = signal.lfilter(b, a, imp)
plt.figure();
plt.plot(np.arange(-50, 50), imp)
plt.plot(np.arange(-50, 50), response)
plt.margins(0.1, 0.1)
plt.xlabel('Time [samples]')
plt.ylabel('Amplitude')
plt.grid(True)
plt.show()
#%% Plots
w, h = signal.freqresp(b)

plt.figure()
plt.semilogx(w, 20*np.log10(abs(h)))
ax1=plt.gca()
ax2=ax1.twinx()
plt.semilogx(w, 180./np.pi*np.unwrap(np.angle(h)), 'g')
