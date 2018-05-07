"""
PyQt4 GUI program for Keysight 33500B Waveform Generator
Accepts alternating ramp speed & delay numbers
Accepts voltage changes for each ramp and delay
Can change output, termination, and filter applied to arbitrary waveform

Created on June 13 2016
v1) connect to instrument and build ch1 waveform of ramp, delay, ramp, delay, etc.
    Can vary output on/off, impedance, filter shapesample rate, and offset voltage.
v2) Add amplitude jump during delay section, total time mode for syncing
    added 2nd channel, sync timing via trigger (not via datapts). output off when switching
v2.1) added 2 string qualifier to each function builder. rm1, dl1, er1,2
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

__version__ = '2.1.1'
class color_QLineEdit(QLineEdit):

    def __init__(self):
        super(color_QLineEdit, self).__init__()

        self.textChanged.connect(self.change_my_color)
        self.returnPressed.connect(self.reset_my_color)
        
        self.reset_my_color()
        
    def change_my_color(self):
        palette = QPalette()
        palette.setColor(self.backgroundRole(), QColor('black'))
        palette.setColor(self.foregroundRole(), QColor('white'))
        self.setPalette(palette)
        
    def reset_my_color(self):
        palette = QPalette()
        palette.setColor(self.backgroundRole(), QColor('white'))
        palette.setColor(self.foregroundRole(), QColor('black'))
        self.setPalette(palette)

class WFM(QMainWindow):
    
    def __init__(self):
        super(WFM, self).__init__()
        
        self.conBool=False
        self.initUI()
        self.textbox.setText('dl0.00015 rm45000000 er1e4,0.01');
        self.amp.setText('0 1 2');self.amp.reset_my_color()
        self.off.setText('0');self.off.reset_my_color()
        self.totalpp=0
        self.srate.setText("1e4");self.srate.reset_my_color()
        self.term.setText('50');self.term.reset_my_color()
        self.deltime.setText('0');self.deltime.reset_my_color()
        self.ttime.setText('0.1');self.ttime.reset_my_color()

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
        
        self.textbox = color_QLineEdit()
        self.amp = color_QLineEdit()
        self.amplbl = QLabel("Total Amp: _Vpp",self)
        self.srate = color_QLineEdit()
        self.sratelbl = QLabel("SampleRate (Sa/s)",self)
        self.off = color_QLineEdit()
        self.offlbl = QLabel("offset (V)",self)
        
        self.lbl = QLabel("Alt. ramp(V/s), delay(s)",self)
        self.lbl2 = QLabel("Amp. step (V)", self)
        self.errlbl = QLabel('Error Display')
#        self.errlbl.font(QFont.Bold())
        self.ch = QComboBox(self)
        self.ch.addItems(("1","2"));self.ch.setCurrentIndex(0)
        self.chlbl = QLabel("CH:", self)
        self.filter = QComboBox(self)
        self.filter.addItems(("Step","Normal","OFF"))
        self.filterlbl = QLabel("Filter:", self)
        self.rstbox = QCheckBox()
        self.rstlbl = QLabel("Reset Instr.",self)
        self.output = QCheckBox()
        self.outputlbl = QLabel("Output On/Off", self)
        self.sync = QCheckBox()
        self.synclbl = QLabel("SyncArbs?", self)
        self.deltime = color_QLineEdit();
        self.deltimelbl = QLabel('Delay Time (s)',self)
        self.ttime = color_QLineEdit();
        self.ttimelbl = QLabel("Total wfm Time (s)",self);
        self.term = color_QLineEdit()
        self.termlbl = QLabel("Impedance: INF or #",self)
        self.gpibInst = QComboBox(self)
        self.gpibInst.setMaximumWidth(100)
        self.gpibInst.addItem('Select GPIB Instrument')
        self.gpibInst.addItems(self.gpibFind())
        self.inst = 'None'
        self.textstor = ['0','1'];
        self.ampstor = ['0','1'];
        self.sratestor = ['1e3','1e3'];
        self.offsetstor = ['0','0'];
        self.termstor = ['50','50'];
        self.delstor = ['0','0'];
        self.filterstor = [0,0]
        self.outputstor = ['0','0'];
        ## Signal/Slot connections
        self.connect(self.gpibInst, SIGNAL('currentIndexChanged(QString)'),self.gpibConnect)
        self.connect(self.textbox, SIGNAL('returnPressed()'), self.onChanged)
        self.connect(self.srate, SIGNAL('returnPressed()'), self.onChanged)
        self.connect(self.amp, SIGNAL('returnPressed()'), self.onChanged)        
        self.connect(self.off, SIGNAL('returnPressed()'), self.onChanged)
        self.connect(self.filter, SIGNAL('currentIndexChanged(QString)'), self.onChanged)
        self.connect(self.term, SIGNAL('returnPressed()'), self.termChanged)
        self.connect(self.output, SIGNAL('stateChanged(int)'),self.outputChanged)
        self.connect(self.rstbox, SIGNAL('stateChanged(int)'),self.resetChanged)
        self.connect(self.sync, SIGNAL('stateChanged(int)'),self.syncChanged)
        self.connect(self.ch, SIGNAL('currentIndexChanged(QString)'),self.chChanged)
        self.connect(self.deltime, SIGNAL('returnPressed()'), self.textbox.change_my_color)
        self.connect(self.ttime, SIGNAL('returnPressed()'), self.textbox.change_my_color)
        ## Write to main window properties
        self.setGeometry(300, 300, 800, 500) #x,y,w,h
        self.setWindowTitle('33500B WFM Arb.Wfm Generator')
        self.show()
        
        ## Layout widgets on screen
        hbox = QHBoxLayout()
        for w in [self.lbl, self.textbox, self.chlbl, self.ch, self.rstlbl, self.rstbox, self.gpibInst]:
            hbox.addWidget(w)
            hbox.setAlignment(w, Qt.AlignVCenter)
        hbox2 = QHBoxLayout()
        for w in [self.lbl2, self.amp, self.synclbl, self.sync, self.deltimelbl, self.deltime, 
                  self.ttimelbl, self.ttime, self.filterlbl, self.filter, self.errlbl]:
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
        self.show()
        
        
    ## Define Changed Functions
    def onChanged(self):
        string = unicode(self.textbox.text()).split()
        ampString = unicode(self.amp.text()).split() #convert amplitude strings        
        if len(ampString)!=len(string):
            self.errlbl.setText('Match length of inputs');
        else:
            self.buildWFM()
        self.plotUpdate()

        self.sratelbl.setText('%s Samples, SRate: (Sa/s)' %(self.samples)) #Display new Samples

#        if self.samples>65e3:
#            self.errlbl.setText('Too long, Samples<65k');          

        if len(ampString)==len(string):
            self.totalpp=max(self.datay)-min(self.datay) #Calc Vpp
            self.amplbl.setText('Total Amp: %sVpp' %(self.totalpp)) #Display new Vpp
            self.loadWFM()
            self.termChanged()
            self.offsetChanged()
            self.srateChanged()
            self.ampChanged()
            self.filterChanged()
            self.outputChanged()
            self.errlbl.setText('No Errors')
            self.syncChanged()

    def ampChanged(self):
        self.func_write('SOUR%s:VOLT %s; *WAI' %(self.ch.currentText(),self.totalpp)); print('Amp changed')
        
    def offsetChanged(self):
        self.func_write('SOUR%s:VOLT:OFFSET %s; *WAI' %(self.ch.currentText(),self.off.text())) ;print('Offset changed')
    
    def srateChanged(self):
        self.func_write('SOUR%s:FUNC:ARB:SRATE %s; *WAI' %(self.ch.currentText(),self.srate.text()));print('SRate Changed')
        realsrate = float(self.func_read('SOUR%s:FUNC:ARB:SRATE?' %self.ch.currentText()))
        if realsrate != float(self.srate.text()):
            print('Sample rate not worthy')
            redpalette = QPalette()
            redpalette.setColor(self.backgroundRole(), QColor('white'))
            redpalette.setColor(self.foregroundRole(), QColor('red'))
            self.srate.setPalette(redpalette)
        
    def filterChanged(self):
        self.func_write('SOUR%s:FUNC:ARB:FILTER %s; *WAI' %(self.ch.currentText(),self.filter.currentText()));print('Filter Changed')
        
    def termChanged(self):
        if self.term.text()=='INF':
            self.func_write('OUTP%s:LOAD INF; *WAI' %self.ch.currentText())
            self.ampChanged()
        elif int(self.term.text())<1e3:
#            term = int(self.term.text())
            self.func_write('OUTP%s:LOAD %s; *WAI' %(self.ch.currentText(),int(self.term.text())))
            self.ampChanged()
        else:
            self.errlbl.setText('Incorrect Termination')
#        print('%.1f' %self.func_read('OUTP:LOAD?'))
    
    def outputChanged(self, state=0):
        if self.output.isChecked():
            self.func_write('OUTPUT%s ON; *WAI' %self.ch.currentText())
        else:
            self.func_write('OUTPUT%s OFF; *WAI' %self.ch.currentText())
            
    def resetChanged(self, state=0):            
        if self.rstbox.isChecked():
            self.inst.write('*RST; *WAI') #reset instrument
            self.inst.write('*CLS; *WAI') #clear instrument
            self.rstbox.setChecked(0)
            self.textbox.change_my_color()
            
    def plotUpdate(self):
        #Update plots
        self.axes.clear()
        self.axes.plot(self.datax,self.datay,'.-') #plot data
#        self.lbl.setText(string) 
        self.canvas.draw() #update drawing
        
    def loadWFM(self):
        #Upload waveform and settings
        ch=int(self.ch.currentText())
        name='test%s' %ch
        print('Samples=%s' %len(self.datay))
        datasend=self.datay/(max(abs(self.datay)))
        
        #turn off output when updating
        self.func_write('OUTPUT%s OFF; *WAI' %self.ch.currentText())
            
        self.func_write('FORMAT:BORDER SWAPPED') #binary data format, little endian (LSB first)
        self.func_write('SOUR%s:DATA:VOLatile:CLEar; *WAI' %self.ch.currentText())
        self.inst.write_binary_values(u'SOUR%s:DATA:ARB ' %self.ch.currentText() +name+', ', datasend, datatype='f') #https://docs.python.org/2/library/struct.html
        self.sb=int(self.inst.query('*STB?'));
        if self.sb==4:
            err=self.inst.query('SYST:ERR?')
            self.inst.write('*CLS')
            print(err)
        self.func_write('SOUR%s:FUNC:ARB ' %self.ch.currentText() + name ) #use waveform in memory
#        self.arbString = ','.join(['%.5f' %num for num in datasend]) #num2str command
#        self.func_write('SOUR%s:DATA:ARB ' %self.ch.currentText() + name + ', ' + self.arbString ) #str(arb))
        self.func_write('*WAI');print('WFM Loading')   #Make sure no other commands are exectued until arb is done downloadin
        self.func_write('SOUR%s:FUNC ARB' %self.ch.currentText()) #Set to arb. waveform output
        self.func_write('SOUR%s:FUNC:ARB ' %self.ch.currentText() + name ) #use waveform in memory
        
        if self.sync.isChecked():
            self.func_write('*WAI;SOUR%s:FUNC:ARB:SYNC' %self.ch.currentText())
        print('WFM Loaded')
        #turn output back to correct state
        self.outputChanged()
        
    def chChanged(self):
        self.func_write('DISP:FOCUS CH%s; *WAI' %self.ch.currentText()); print('Channel changed')
        
        if self.textstor==['0','1']:
            load=0; #print('no loading of data')
        else:
            load=1; #print('loading data')
        ch_new=int(self.ch.currentText())-1;
        ch_old=int(not(ch_new));
#        print('Newch:%s OldCh:%s'%(ch_new,ch_old))
        self.textstor[ch_old] = self.textbox.text();
        self.ampstor[ch_old] = self.amp.text();
        self.sratestor[ch_old] = self.srate.text();
        self.offsetstor[ch_old] = self.off.text();
        self.termstor[ch_old] = self.term.text();
        self.delstor[ch_old] = self.deltime.text();
        self.filterstor[ch_old] = self.filter.currentIndex();
        self.outputstor[ch_old] = int(self.output.isChecked())
#        print(self.textstor)
        if load:
            self.textbox.setText(self.textstor[ch_new]);self.textbox.reset_my_color()
            self.amp.setText(self.ampstor[ch_new]);self.amp.reset_my_color()
            self.srate.setText(self.sratestor[ch_new]);self.srate.reset_my_color()
            self.off.setText(self.offsetstor[ch_new]);self.off.reset_my_color()
            self.term.setText(self.termstor[ch_new]);self.term.reset_my_color()
            self.deltime.setText(self.delstor[ch_new]);self.deltime.reset_my_color()
            self.filter.setCurrentIndex(self.filterstor[ch_new]);
            self.output.setChecked(bool(self.outputstor[ch_new]));
            print('loading data')
            self.buildWFM()
            self.plotUpdate()

        
#        self.textbox.setText(self.textstor[ch])

    def syncChanged(self, state=0):
        if self.sync.isChecked():
            self.func_write('FUNC:ARB:SYNC; *WAI')
            self.func_write('SOUR%s:FUNC:ARB:SYNC; *WAI' %self.ch.currentText())
            print('ArbSync On')
        elif ~self.sync.isChecked():
            print('ArbSync Not On')
#        self.onChanged();
            
            
    ##Arb WFM functions
    def buildWFM(self):
        wfm=np.zeros(0)
        stor=np.zeros(0)
        aptr=0
        srate=float(self.srate.text()) #Read sample rate
        fstring = unicode(self.textbox.text()).split()
        ampString = unicode(self.amp.text()).split() #convert amplitude strings
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
        if self.sync.isChecked():
#            ttime=float(self.ttime.text());print('ttime=%s'%ttime)
#            delta=ttime-len(wfm)/srate1;print('delta=%s'%delta);print('extrasamples=%s'%(delta*srate1))
#            wfm=np.hstack((wfm,np.ones(delta*srate1)*wfm[-1]))
            ch_new=int(self.ch.currentText())-1;
            ch_old=int(not(ch_new));
            for n in [1,2]:
                self.func_write('SOUR%s:BURS:STAT OFF' %n) #Turn off burst mode to setup settings          
                self.func_write('SOUR%s:BURST:MODE TRIG; *WAI' %n)      
                self.func_write('SOUR%s:BURST:NCYC 1' %n)
                self.func_write('TRIG%s:SOUR TIM' %n)
                self.func_write('TRIG%s:TIM %s' %(n,self.ttime.text()) )
                if n==ch_old+1:
                    self.func_write('TRIG%s:DELAY %s' %(n,self.delstor[n-1]))
                elif n==ch_new+1:
                    self.func_write('TRIG%s:DELAY %s' %(n,self.deltime.text()))
                self.func_write('SOUR%s:BURS:STAT ON' %n) #Turn on burst mode after all other settings          
        self.samples=len(wfm)
        self.datay=wfm
        self.datax=np.arange(len(wfm))/srate
                    
    ## GPIB Functions
    def func_write(self,func):
        if self.conBool:
            self.inst.write(func);
            self.sb=int(self.inst.query('*STB?'));
            if self.sb==4:
                err=self.inst.query('SYST:ERR?')
                self.inst.write('*CLS')
                print(err)
#            else: print('no error');
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
        self.inst.timeout = 10000;
        
    def gpibFind(self):
        rm = visa.ResourceManager()
        devices=rm.list_resources()
        return devices


def main():
    
    app = QtGui.QApplication(sys.argv)
    form = WFM()
    form.show()
    sys.exit(app.exec_())
    app.exec_()
    
if __name__ == "__main__":
    main()

#app = QtGui.QApplication(sys.argv)
#form = WFM()
#form.show()
#self=form
## Troubleshooting
#    print(form.gpibFind())
#    x=form.gpibFind()
#    fgen=form.gpibConnect('USB0::0x0957::0x2C07::MY52814470::INSTR')
#    form.func_write('FUNC TRI')
    