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
v2.1.3) add cosine function qualifier, cs500,1,1
v2.2) Major new addition, tabbed version layout, and custom function drawing in tab2
v3.0.0) Add new tab to draw wfm, requires pyQtGraph and scipy.interpolate install
v3.0.2) Pyqt performance improv., add "mr" for aritray number of exp. ramps

TO DO) Add FFT plot functionality (with calculation time restrictions)
@author: Daryl Spencer
"""

#from PyQt4 import QtGui, QtCore
import sys
#import pyvisa as visa
from pyvisa import ResourceManager
import numpy as np
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import (QApplication,QMainWindow,QWidget,QLabel,QPalette,QLineEdit,QComboBox,
    QColor,QCheckBox,QGridLayout,QPushButton,QHBoxLayout,QVBoxLayout,QTabWidget,
    QTableWidget,QTableWidgetItem,QTextEdit)
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pyqtgraph as pg
import scipy.interpolate as interp

__version__ = '3.0.2-b1'
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

class pyqtBuilder(QWidget):

    def __init__(self):
        super(pyqtBuilder, self).__init__()
        #Variable Definitions
        self.srate=50000; #samples/s rate
        #self.datanum=10000; #number of plot data points
        self.xrange = 1e-5;
        self.yrange = 10;
        self.controls = [];
        self.xsort=[0,1e-3];
        self.ysort=[0,0];
        self.main()

    def main(self):
        numcon = 5; #Initial number of controls

        l= QGridLayout();
        # Widgets
        self.p1 = pg.PlotWidget(title='Input Ramp')
        self.p2 = pg.PlotWidget(title='Convolved')
        btn_control = QPushButton("Add Control Point")
        self.btnlbl_cload = QLabel("Cont. Load")
        self.btn_cload = QCheckBox()
        self.btn_load = QPushButton("Upload Data")
        self.dat_paste= QPushButton("Copy data to graph")
        self.xtransform = color_QLineEdit()
        self.ytransform = color_QLineEdit()
        self.xtransform.setText("1");self.xtransform.reset_my_color()
        self.ytransform.setText("1");self.ytransform.reset_my_color()
        self.dataxBox = QTextEdit()
        self.dataxBox.setTabChangesFocus(True);
        self.datayBox = QTextEdit()
        self.datayBox.setTabChangesFocus(True);
        self.table = QTableWidget(numcon,2)

        for i in range(numcon):
            self.controls.append(pg.ROI([self.xrange*i/float(numcon),self.yrange*i/float(numcon)],
                                         size=pg.Point(self.xrange/10,self.yrange/10)));

        #Widget Layout
        l.addWidget(self.p1,0,0)
#        l.addWidget(self.table,0,1)
#        l.addWidget(self.dataxBox,1,1)
        hbox = QHBoxLayout();
        for widget in [btn_control,self.btn_load,self.btnlbl_cload,self.btn_cload,
                       self.xtransform,self.ytransform]:
            hbox.addWidget(widget)
        hbox2 = QHBoxLayout();
        for widget in [self.dataxBox,self.datayBox]:
            hbox2.addWidget(widget)
        l.addLayout(hbox,1,0)
        l.addLayout(hbox2,0,1)
        l.addWidget(self.dat_paste,1,1)
        self.setLayout(l)

        #Initial Signal connections
        btn_control.clicked.connect(self.addControl); #Button signal
        self.dat_paste.clicked.connect(self.updateGraph); #Button signal
        self.connect(self.xtransform, SIGNAL('returnPressed()'), self.transformAxes)
        self.connect(self.ytransform, SIGNAL('returnPressed()'), self.transformAxes)
        for item in self.controls:
            item.sigRegionChangeFinished.connect(lambda:self.rePlot());
            self.p1.addItem(item)

        self.rePlot();

    def updateGraph(self):
        print('updating graph')
        xdata = map(float, (self.dataxBox.toPlainText().split(',')));
        ydata = map(float, (self.datayBox.toPlainText().split(',')));
        sizex = np.ptp(xdata)/10;
        sizey = np.ptp(ydata)/10;
        for control in self.controls:
            control.sigRegionChangeFinished.disconnect()
            #print('updateGraphdisconnect')
            self.p1.removeItem(control);
        self.controls=[];
        for ii in range(len(xdata)):
            self.addControl();
            #self.controls.append(pg.ROI([xdata[ii],ydata[ii]], size=pg.Point(sizex,sizey)));
            self.controls[-1].sigRegionChangeFinished.disconnect();
            self.controls[-1].setPos([xdata[ii],ydata[ii]])
            self.controls[-1].setSize(pg.Point(sizex,sizey));
            self.controls[-1].sigRegionChangeFinished.connect(lambda:self.rePlot());
        self.rePlot()

    def updateTable(self):
        print('updating table')
        xtext = ', '.join("%.5e"%x for x in self.xsort)
        ytext = ', '.join("%.5e"%y for y in self.ysort)
        self.dataxBox.setText(xtext)
        self.datayBox.setText(ytext)

    def transformAxes(self):
        xfactor = float(self.xtransform.text())
        yfactor = float(self.ytransform.text())
        for control in self.controls:
            control.sigRegionChangeFinished.disconnect();
            control.setPos(control.pos()[0]*xfactor, control.pos()[1]*yfactor)
            control.sigRegionChangeFinished.connect(lambda:self.rePlot());
        print('Factors:%f, %f'%(xfactor,yfactor))
        self.rePlot()

    def addControl(self):
        self.yrange = (self.p1.getAxis('left').range); #get yrange
        self.xrange = (self.p1.getAxis('bottom').range) #get xrange
        self.controls.append(pg.ROI([self.xrange[0]+0.9*np.ptp(self.xrange),
                                     self.yrange[0]+0.9*np.ptp(self.yrange)],
                               size=pg.Point(0.05*np.ptp(self.xrange),np.ptp(self.yrange)*0.05)));
        self.p1.addItem(self.controls[-1])
        self.controls[-1].sigRegionChangeFinished.connect(lambda:self.rePlot());


    def getControls(self):
        self.p1.findChildren(pg.graphicsItems.ROI)

    def rePlot(self):
        print('replotting')
        try:
            self.p1.clearPlots();self.p2.clearPlots();        #clear all plots
            x=[];y=[];
            for control in self.controls:
                x= np.append(x, control.pos()[0]);
                y= np.append(y, control.pos()[1]);
            self.xsort=x[np.argsort(x)];
            self.ysort=y[np.argsort(x)];
            self.updateTable();
            if len(self.controls)<2:
                return;
            if self.btn_cload.isChecked():
                self.btn_load.animateClick();
            #xplot = np.linspace(self.xsort[0],self.xsort[-1], num=self.datanum)
            xplot = np.arange(self.xsort[0],self.xsort[-1],step=1./self.srate);
            finterp = interp.interp1d(self.xsort,self.ysort,kind='linear')
            #(fknots),_,_,_ = interp.splrep(xsort,ysort)
            #finterp = interp.splev(xplot,fknots)
            yplot=finterp(xplot)
            self.p1.plot(xplot,yplot,symbol='o',pen='b',symbolSize=2,pxMode=True);   #plot drawn waveform
    #        p2.plot(time2-time2[0],ramp_0); #plot input ra,p
    #        p2.plot(time,pulse_0,pen='y') #Plot impulse resp (not normlized).
    #        ramp_resp_n1 = ramp_resp_0*np.ptp(ramp_0)/np.ptp(ramp_resp_0); #Normalize amplitudes
    #        p2.plot(time2-time2[0],ramp_resp_n1*ramp_0[-1]/ramp_resp_n1[-1],pen='c'); #Plot with normalized last pt.
    #        yplot2 = signal.convolve(impulse_resp/sum(impulse_resp),yplot); #Convolve drawn wfm with norm. imp. response
    #        p2.plot(xplot,yplot2[:len(yplot2)-len(pulse_0)+1],pen='b') #Plot convolved drawn wfm
            #Resize control points
            plotyrange = np.ptp(self.p1.getAxis('left').range); #get yrange
            plotxrange = np.ptp(self.p1.getAxis('bottom').range) #get xrange
            for control in self.controls:
                control.sigRegionChangeFinished.disconnect();
                #print('rePlotdisconnect')
                control.setSize(pg.Point(plotxrange*0.05,plotyrange*0.05))
                control.sigRegionChangeFinished.connect(lambda:self.rePlot())
        except: raise



class WFM(QMainWindow):

    def __init__(self):
        super(WFM, self).__init__()

        self.conBool=False
        self.initUI()
        self.textbox.setText('dl0.00015 rm45000000 er1e4,0.001 cs500,1,1');
        self.amp.setText('0 1 2 1');self.amp.reset_my_color()
        self.off.setText('0');self.off.reset_my_color()
        self.totalpp=0
        self.srate.setText("1e4");self.srate.reset_my_color()
        self.term.setText('50');self.term.reset_my_color()
        self.deltime.setText('0');self.deltime.reset_my_color()
        self.ttime.setText('0.1');self.ttime.reset_my_color()

    def initUI(self):
        main_frame =QWidget()
        ## Create the mpl Figure and FigCanvas objects.
        self.dpi = 100
        self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(main_frame)
        ## Add new subplot to figure, which will be changed
        self.axes = self.fig.add_subplot(111)
        ## Create the navigation toolbar, tied to the canvas
        self.mpl_toolbar = NavigationToolbar(self.canvas, main_frame)
        #Create the PyQtGraph Builder Widget
        self.builder = pyqtBuilder()
        #Create other widgets
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
        self.errlbl.setStyleSheet('color: red')
        self.ch = QComboBox(self)
        self.ch.addItems(("1","2"));
        self.chlbl = QLabel("CH:", self)
        self.filter = QComboBox(self)
        self.filter.addItems(("Step","Normal","OFF"));
        self.filterlbl = QLabel("Filter:", self)
        self.rstbox = QPushButton("Reset Instr.")
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
        self.gpibInst.setMinimumWidth(200)
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
        self.connect(self.sync, SIGNAL('stateChanged(int)'),self.syncChanged)
        self.connect(self.ch, SIGNAL('currentIndexChanged(QString)'),self.chChanged)
        self.connect(self.deltime, SIGNAL('returnPressed()'), self.textbox.change_my_color)
        self.connect(self.ttime, SIGNAL('returnPressed()'), self.textbox.change_my_color)
        self.rstbox.clicked.connect(self.resetChanged)
        self.builder.btn_load.clicked.connect(self.onChanged)
        ## Write to main window properties
        self.setGeometry(300, 300, 800, 500) #x,y,w,h
        self.setWindowTitle('33500B WFM Arb.Wfm Generator')
        self.show()

        ### Layout widgets on screen
        hboxa = QHBoxLayout()
        for w in [self.lbl, self.textbox]:
            hboxa.addWidget(w)
            hboxa.setAlignment(w, Qt.AlignVCenter)
        hboxb = QHBoxLayout()
        for w in [self.lbl2, self.amp]:
            hboxb.addWidget(w)
            hboxb.setAlignment(w, Qt.AlignVCenter)
        hbox1 = QHBoxLayout()
        for w in [self.chlbl, self.ch,
                  self.rstbox, self.gpibInst]:
            hbox1.addWidget(w)
            hbox1.setAlignment(w, Qt.AlignVCenter)
        hbox2 = QHBoxLayout()
        for w in [self.synclbl, self.sync,
                  self.deltimelbl, self.deltime,self.ttimelbl,
                  self.ttime, self.filterlbl, self.filter, self.errlbl]:
            hbox2.addWidget(w)
            hbox2.setAlignment(w, Qt.AlignVCenter)
        hbox3 = QHBoxLayout()
        for w in [self.amplbl, self.sratelbl, self.srate,
                  self.offlbl, self.off, self.termlbl, self.term,
                  self.outputlbl,self.output]:
            hbox3.addWidget(w)
            hbox3.setAlignment(w, Qt.AlignVCenter)
        #Main box
        mainWindow = QWidget();
        gridLayout = QGridLayout();
        self.tabWidget = QTabWidget();
        #Inner1, Tab boxes
        tab1Widget = QWidget();
        tab2Widget = QWidget();
        tab1Layout = QVBoxLayout();
        tab2Layout = QVBoxLayout();
        #Inner2, ControlBox
        cntLayout = QVBoxLayout()
        cntLayout.addLayout(hbox1)
        cntLayout.addLayout(hbox2)
        cntLayout.addLayout(hbox3)
        #AddWidgets and Layout
        tab1Layout.addWidget(self.canvas)
        tab1Layout.addWidget(self.mpl_toolbar)
        tab1Layout.addLayout(hboxa)
        tab1Layout.addLayout(hboxb)
        tab2Layout.addWidget(self.builder)
        gridLayout.addWidget(self.tabWidget,0,0)
        gridLayout.addLayout(cntLayout,1,0)
        self.tabWidget.addTab(tab1Widget, "Main");
        self.tabWidget.addTab(tab2Widget, "Custom")
        #Set Layout Children
        tab1Widget.setLayout(tab1Layout)
        tab2Widget.setLayout(tab2Layout)
        mainWindow.setLayout(gridLayout)
        self.setCentralWidget(mainWindow)
        #self.show()

    def fftWFM(self):
        d=1.0/float(self.srate.text())
        hs=np.fft.fft(self.datay)
        fs=np.fft.fftfreq(int(len(self.datax)),d)
        return fs, hs

    ## Define Changed Functions
    def onChanged(self):
        ind = self.tabWidget.currentIndex();
        if ind == 0:
            string = unicode(self.textbox.text()).split()
            ampString = unicode(self.amp.text()).split() #convert amplitude strings
            if len(ampString)!=len(string):
                self.errlbl.setText('Match length of inputs');
            else:
                self.errlbl.clear()
                self.buildWFM()
            self.plotUpdate()
        elif ind == 1:
            self.buildDrawing();
            #print(self.datax,self.datay)
        self.sratelbl.setText('%s Samples, SRate: (Sa/s)' %(self.samples)) #Display new Samples

#        if self.samples>65e3:
#            self.errlbl.setText('Too long, Samples<65k');

        self.totalpp=max(self.datay)-min(self.datay) #Calc Vpp
        self.amplbl.setText('Total Amp: %sVpp' %(self.totalpp)) #Display new Vpp
        self.loadWFM()
        self.termChanged()
        self.offsetChanged()
        self.srateChanged()
        self.ampChanged()
        self.filterChanged()
        self.outputChanged()
        #self.errlbl.setText('No Errors')
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
        self.errlbl.clear()
        if self.term.text()=='INF':
            self.func_write('OUTP%s:LOAD INF; *WAI' %self.ch.currentText())
            print('Termintation changed')
            self.ampChanged()
        elif int(self.term.text())<1e3:
#            term = int(self.term.text())
            self.func_write('OUTP%s:LOAD %s; *WAI' %(self.ch.currentText(),int(self.term.text())))
            print('Termination changed')
            self.ampChanged()
        else:
            self.errlbl.setText('Incorrect Termination')
        #print('%.1f' %self.func_read('OUTP:LOAD?'))

    def outputChanged(self, state=0):
        if self.output.isChecked():
            self.func_write('OUTPUT%s ON; *WAI' %self.ch.currentText())
        else:
            self.func_write('OUTPUT%s OFF; *WAI' %self.ch.currentText())

    def resetChanged(self):
        #if self.rstbox.isChecked():
        self.func_write('*RST; *WAI') #reset instrument
        self.func_write('*CLS; *WAI') #clear instrument
        #self.rstbox.setChecked(0)
        #self.textbox.change_my_color()

    def plotUpdate(self):
        #Update plots
        self.axes.clear()
        self.axes.plot(self.datax,float(self.off.text())+self.datay,'.-') #plot data
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
    def buildDrawing(self):
        self.datax=[];
        srate=float(self.srate.text()) #Read sample rate
        finterp = interp.interp1d(self.builder.xsort,self.builder.ysort,kind='linear')
        self.datax = np.arange(self.builder.xsort[0],self.builder.xsort[-1],step=1./srate)
        self.datay = finterp(self.datax)
        self.samples = len(self.datay);
        self.builder.srate = srate;
        print('replot line')

    def buildWFM(self):
        wfm=np.zeros(0)
        stor=np.zeros(0)
        aptr=0 #pointer to hold last amplitude value of section
        srate=float(self.srate.text()) #Read sample rate
        fstring = unicode(self.textbox.text()).split()
        ampString = unicode(self.amp.text()).split() #convert amplitude strings
        pi = np.pi
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
                #print('ramp')
                aptr=newpt
            elif func == 'dl': #delay
                samp=abs(int(srate*data[0]))
                newpt=aptr+float(amp1[0]) #Amp jump during delay section
                stor=np.linspace(newpt,newpt,num=samp) #Amp level during delay
                #print('delay')
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
            elif func == 'mr': #multiple exp. rise, f(t1,t2...,tn,total)=A1*exp(t1)+A2*exp(t2)+...+An*exp(tn)
                if (len(data)-1) != len(amp1): print('Match args of multi-exp.'); continue;
                samp=abs(int(srate*data[-1]))                
                x=np.linspace(0,data[-1],num=samp)
                stor=np.zeros(samp);
                for ii in range(len(data)-1):
                    stor=stor -amp1[ii]*np.exp(-data[ii]*x);
                stor = stor + np.sum(amp1[:]) + aptr
                aptr = stor[-1]
            elif func == 'cs':
            #cosine, f(freq, thetastart/pi, thetatotal/pi) = A*cosine(2pi*freq + pi*theta)
                if len(data)!=3:
                    print('Cosine needs 3 inputs (E.g.: cs500,0,1/2)'); continue;
                ttotal = (data[2])/(2*data[0])
                samp=abs(int(srate*ttotal))
                x=np.linspace(0,ttotal,num=samp)
                func=amp1[0]/2.0*np.cos(2*pi*data[0]*x+pi*data[1])
                stor=func - (func[0] - aptr)
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
            self.err=self.inst.query('SYST:ERR?')
            if self.sb==4:
                self.func_write('*CLS')
                self.errlbl.setText(str(self.err))
                print(str(self.err))
        else:
            print('not connected')
        QApplication.processEvents()

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
        rm = ResourceManager()
        print(address)
        self.inst = rm.open_resource(str(address))
        print(self.inst.query('*IDN?'))
        self.conBool=True
        self.inst.chunck_size = pow(2,20)
        self.inst.timeout = 10000;

    def gpibFind(self):
        rm = ResourceManager()
        devices=rm.list_resources()
        return devices

### Main loop
def main():
    app = QApplication(sys.argv)
    form = WFM()
    form.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

## Standalone Run in Spyder
#app = QApplication(sys.argv)
#form = WFM()
#form.show()
#self=form

### Troubleshooting
#    print(form.gpibFind())
#    x=form.gpibFind()
#    fgen=form.gpibConnect('USB0::0x0957::0x2C07::MY52814470::INSTR')
#    form.func_write('FUNC TRI')
