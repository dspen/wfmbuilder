"""
PyQt4 GUI program for Keysight 33500B Waveform Generator
Accepts alternating ramp speed & delay numbers
Accepts voltage changes for each ramp and delay
Can change output, termination, and filter applied to arbitrary waveform

Created on June 13 2016

@author: Daryl Spencer
"""

from PyQt4 import QtGui, QtCore
import sys, visa
import numpy as np
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

__version__ = '1.2'
class WFM(QMainWindow):
    
    def __init__(self):
        super(WFM, self).__init__()
        
        self.conBool=False
        self.initUI()
        self.textbox.setText('10 .2 50 .4')
        self.amp.setText('1 0 0.5 0')

        self.off.setText('0')
        self.totalpp=0
        self.srate.setText("1e4")
        self.term.setText('50')

    def initUI(self):      
        self.main_frame =QWidget()
        ## Create the mpl Figure and FigCanvas objects. 
        self.dpi = 100
        self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        ## Add new subplot to figure, which will be changed
        self.axes = self.fig.add_subplot(111)
        ## Create the navigation toolbar, tied to the canvas
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
        
        self.textbox = QLineEdit()
        self.amp = QLineEdit()
        self.amplbl = QLabel("Total Amp: _Vpp",self)
        self.srate = QLineEdit()
        self.sratelbl = QLabel("SampleRate (Sa/s)",self)
        self.off = QLineEdit()
        self.offlbl = QLabel("offset (V)",self)
        
        self.lbl = QLabel("Alt. ramp(V/s), delay(s)",self)
        self.lbl2 = QLabel("Amp. step (V)", self)
        self.errlbl = QLabel('Error Display')
#        self.errlbl.font(QFont.Bold())

        self.filter = QComboBox(self)
        self.filter.addItems(("Step","Normal","OFF"))
        self.filterlbl = QLabel("Filter:", self)
        self.rstbox = QCheckBox()
        self.rstlbl = QLabel("Reset Instr.",self)
        self.output = QCheckBox()
        self.outputlbl = QLabel("Output On/Off", self)
        self.term = QLineEdit()
        self.termlbl = QLabel("Impedance: INF or #",self)
        self.gpibInst = QComboBox(self)
        self.gpibInst.setMaximumWidth(100)
        self.gpibInst.addItem('Select GPIB Instrument')
        self.gpibInst.addItems(self.gpibFind())
        self.inst = 'None'
        ## Signal/Slot connections
        self.connect(self.gpibInst, SIGNAL('currentIndexChanged(QString)'),self.gpibConnect)
        self.connect(self.textbox, SIGNAL('editingFinished()'), self.onChanged)
        self.connect(self.srate, SIGNAL('editingFinished()'), self.onChanged)
        self.connect(self.amp, SIGNAL('editingFinished()'), self.onChanged)        
        self.connect(self.off, SIGNAL('editingFinished()'), self.onChanged)
        self.connect(self.filter, SIGNAL('currentIndexChanged(QString)'), self.onChanged)
        self.connect(self.term, SIGNAL('editingFinished()'), self.termChanged)
        self.connect(self.output, SIGNAL('stateChanged(int)'),self.outputChanged)
#        self.connect(self.ramp1dial,SIGNAL('valueChanged(int)'),self.dataChanged)        
        ## Write to main window properties
        self.setGeometry(300, 300, 400, 400)
        self.setWindowTitle('33500B WFM Arb.Wfm Generator')
        self.show()
        
        ## Layout widgets on screen
        hbox = QHBoxLayout()
        for w in [self.lbl, self.textbox, self.rstlbl, self.rstbox, self.gpibInst]:
            hbox.addWidget(w)
            hbox.setAlignment(w, Qt.AlignVCenter)
        hbox2 = QHBoxLayout()
        for w in [self.lbl2, self.amp, self.filterlbl, self.filter, self.errlbl]:
            hbox2.addWidget(w)
            hbox2.setAlignment(w, Qt.AlignVCenter)
        hbox3 = QHBoxLayout()
        for w in [self.amplbl, self.sratelbl, self.srate,
                  self.offlbl, self.off, self.termlbl, self.term,
                  self.outputlbl,self.output]:
            hbox3.addWidget(w)
            hbox3.setAlignment(w, Qt.AlignVCenter)
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)
        vbox.addLayout(hbox)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox3)
        
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)
        
        
        
    ## Define Changed Functions
    def onChanged(self):
        
        self.axes.clear()
        string = unicode(self.textbox.text())
        self.vars = map(float, string.split())
        self.buildWFM(self.vars)
#        xrate = float(self.srate.text())
#        x= range(len(self.datay))
        x= self.datax
        y= self.datay
        #Update plots
        self.axes.plot(x,y,'.') #plot data
#        self.lbl.setText(string) 
        self.canvas.draw() #update drawing
        self.sratelbl.setText('%s Samples, SRate: (Sa/s)' %(self.samples)) #Display new Samples

        if self.samples>10e3:
            self.errlbl.setText('Too long, reduce Samples<10k')
        else:
            self.totalpp=max(self.datay)-min(self.datay) #Calc Vpp
            self.amplbl.setText('Total Amp: %sVpp' %(self.totalpp)) #Display new Vpp
            self.loadWFM()
            self.termChanged()
            self.offsetChanged()
            self.srateChanged()
            self.ampChanged()
            self.filterChanged()
            self.errlbl.setText('No Errors (yet)')

    def ampChanged(self):
        self.func_write('VOLT %s; *WAI' %self.totalpp); print('Amp changed')
        
    def offsetChanged(self):
        self.func_write('VOLT:OFFSET %s; *WAI' %self.off.text()) ;print('Offset changed')
    
    def srateChanged(self):
        self.func_write('FUNC:ARB:SRATE %s; *WAI' %self.srate.text());print('SRate Changed')

    def filterChanged(self):
        self.func_write('FUNC:ARB:FILTER %s; *WAI' %self.filter.currentText());print('Filter Changed')
        
    def termChanged(self):
        if self.term.text()=='INF':
            self.func_write('OUTP:LOAD INF; *WAI')
            self.ampChanged()
        elif int(self.term.text())<1e3:
#            term = int(self.term.text())
            self.func_write('OUTP:LOAD %s; *WAI' %int(self.term.text()))
            self.ampChanged()
        else:
            self.errlbl.setText('Incorrect Termination')
#        print('%.1f' %self.func_read('OUTP:LOAD?'))
    
    def outputChanged(self, state=0):
        if state==2:
            self.func_write('OUTPUT ON; *WAI')
        elif state==0:
            self.func_write('OUTPUT OFF; *WAI')
    def loadWFM(self):
        self.func_write('SOUR:DATA:VOLatile:CLEar; *WAI')
        #Upload waveform and settings
        name='test'
        print('Samples=%s' %len(self.datay))
        datasend=self.datay/(max(abs(self.datay)))
        self.arbString = ','.join(['%.5f' %num for num in datasend]) #num2str command
        self.func_write('SOUR:DATA:ARB ' + name + ', ' + self.arbString) #str(arb))
        self.func_write('*WAI');print('WFM Loading')   #Make sure no other commands are exectued until arb is done downloadin
        self.func_write('FUNC ARB') #Set to arb. waveform output
        self.func_write('SOUR:FUNC:ARB ' + name) #use waveform in memory
        print('WFM Loaded')
            
    ##Arb WFM functions
    def buildWFM(self,data):
        wfm=np.zeros(0)
        stor=np.zeros(0)
        aptr=0
#        amp1=float(self.amp.text())
        ampString = unicode(self.amp.text())
        amp1=map(float,ampString.split())
        srate1=float(self.srate.text())
        for i in range(len(data)):
            if i%2==0: #even=ramp
                samp=abs(int(amp1[i]*srate1/data[i]))
                newpt=aptr+float(data[i])*samp/srate1
                stor=np.linspace(aptr,newpt,num=samp)
#                print('ramp')
                aptr=newpt
            elif i%2!=0: #odd=delay
                samp=abs(int(srate1*data[i]))
                stor=np.linspace(aptr,aptr,num=samp)
#                print('delay')
            wfm=np.hstack((wfm,stor))
        self.samples=len(wfm)
        self.datay=wfm
        self.datax=np.arange(len(wfm))/srate1
                    
    ## GPIB Functions
    def func_write(self,func):
        if self.conBool:
            self.inst.write(func)   
        else:
            print('not connected')
    def func_read(self,func):
        if self.conBool:
            result=self.inst.query(func)
            return result
        else:
            print('not connected')
    def gpibDisconnect(self):
        self.inst.close()
        self.outputChanged(2) #turn off
        
    def gpibConnect(self,address):    
        rm = visa.ResourceManager()
        self.inst = rm.open_resource(address)
        print(self.inst.query('*IDN?'))
        if self.rstbox.checkState() ==2:
            self.inst.write('*RST; *WAI') #reset instrument
            self.inst.write('*CLS; *WAI') #clear instrument
        self.conBool=True
        self.inst.chunck_size = pow(2,20)
    def gpibFind(self):
        rm = visa.ResourceManager()
        devices=rm.list_resources()
        return devices
        

        
#def main():
#    
#    app = QtGui.QApplication(sys.argv)
#    form = WFM()
#    form.show()
##    sys.exit(app.exec_())
##    app.exec_()
#    
#if __name__ == "__main__":
#    main()

app = QtGui.QApplication(sys.argv)
form = WFM()
form.show()
## Troubleshooting
#    print(form.gpibFind())
#    x=form.gpibFind()
#    fgen=form.gpibConnect('USB0::0x0957::0x2C07::MY52814470::INSTR')
#    form.func_write('FUNC TRI')
    