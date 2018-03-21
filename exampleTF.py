# -*- coding: utf-8 -*-
"""
Created on Wed Mar 21 00:23:19 2018

@author: Daryl
https://stackoverflow.com/questions/12233702/fitting-transfer-function-models-in-scipy-signal

Need to plot impulse response
"""

from scipy.optimize import curve_fit
import scipy.signal as signal
import matplotlib.pyplot as plt
import numpy as np

plt.close('all')
b = signal.lti([], 10, 10)

#%% Impulse function
length = 100
c = np.exp(-np.arange(length)/10)
#signal.impulse(c)

#%% Plots
w, h = signal.freqresp(b)

plt.figure()
plt.semilogx(w, 20*np.log10(abs(h)))
ax1=plt.gca()
ax2=ax1.twinx()
plt.semilogx(w, 180./np.pi*np.unwrap(np.angle(h)), 'g')
