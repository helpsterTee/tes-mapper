import struct
import sys
import time
import json
import os
from PyQt5.QtCore import QDir, Qt
from PyQt5.QtGui import QBrush, QPen
from PyQt5.QtWidgets import (QAction, QApplication, QFileDialog, QLabel, QToolButton, QFileDialog,
        QMainWindow, QMenu, QMessageBox, QScrollArea, QSizePolicy, QGridLayout, QLayout, QListWidget, QWidget, QCheckBox, QTabWidget,
        QGraphicsScene, QGraphicsView)

class Button(QToolButton):
    def __init__(self, text, parent=None):
        super(Button, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setText(text)

    def sizeHint(self):
        size = super(Button, self).sizeHint()
        size.setHeight(size.height() + 20)
        size.setWidth(max(size.width(), size.height()))
        return size

class MainWin(QMainWindow):
    files = []

    def __init__(self):
        super(MainWin, self).__init__()

        self.setupGUI()

        self.setWindowTitle("TES Mapper")
        self.resize(500, 400)

        # config
        self.config = json.loads(open('config.json').read())

    def setupGUI(self):
        tabmain = QTabWidget()
        self.setCentralWidget(tabmain)

        # GPS Converter
        widget = QWidget()
        mainLayout = QGridLayout()
        widget.setLayout(mainLayout)
        self.openButton = self.createButton("Open Files", self.openFileClicked)
        mainLayout.addWidget(self.openButton, 0, 0)
        self.listWidget = QListWidget()
        mainLayout.addWidget(self.listWidget, 2, 0, 1, 2)
        self.runConvButton = self.createButton("Run Conversion", self.runConversionClicked)
        mainLayout.addWidget(self.runConvButton, 0, 1)
        self.runConvButton.setEnabled(False)
        self.multiCheckbox = self.createCheckbox("Multiple Markers per Map")
        mainLayout.addWidget(self.multiCheckbox, 1,1)
        tabmain.addTab(widget, "GPS Data Conversion")

        # GPS View
        gpswidget = QWidget()
        gpsLayout = QGridLayout()
        gpswidget.setLayout(gpsLayout)
        gview = QGraphicsView()
        scene = QGraphicsScene()
        gview.setScene(scene)
        gpsLayout.addWidget(gview)

        blueBrush = QBrush(Qt.blue)
        mypen = QPen(Qt.black)
        scene.addRect(100, 0, 80, 100, mypen, blueBrush)


        tabmain.addTab(gpswidget, "GPS Visualisation")

    def createButton(self, text, member):
        button = Button(text)
        button.clicked.connect(member)
        return button

    def createCheckbox(self, text):
        checkbox = QCheckBox(text)
        return checkbox


    def openFileClicked(self):
        fnames = QFileDialog.getOpenFileNames(self, 'Open files',
                './')

        self.listWidget.clear()
        self.files.clear()
        if len(fnames[0]) > 0:
            self.runConvButton.setEnabled(True)
            for f in fnames[0]:
                self.listWidget.addItem(f)
                self.files.append(f)
        else:
            self.runConvButton.setEnabled(False)

    def runConversionClicked(self):
        multiPositions = []
        multiTimediffs = []
        multiNames = []
        for fi in self.files:
            positions = []
            timediffs = []
            lasttime = -1
            printedtime = False
            with open(fi, 'rb') as f:
                print("Processing ["+fi+"]")
                if os.path.splitext(fi)[1].lower() == ".nmea":
                    print("\tNMEA parsing mode")
                    for line in f:
                        parts = line.decode().split(',')
                        if parts[0] == "$GPRMC":
                            parttime = parts[1]
                            status = parts[2] #A okay, V Warnings
                            lat = parts[3]
                            latori = parts[4]
                            lon = parts[5]
                            lonori = parts[6] #1 is fix, 0 is no fix
                            speed = parts[7] #knots
                            course = parts[8] # to true north
                            date = parts[9]
                            signalValid = parts[12] # signal integrity Axx valid, Nxx invalid or no signal
                            mytime = time.strptime(date[0:2]+"."+date[2:4]+"."+"20"+date[4:6]+" - "+parttime[0:2]+':'+parttime[2:4]+':'+parttime[4:6], '%d.%m.%Y - %H:%M:%S')

                            if len(lat) > 0 and len(lon) > 0:
                                # convert to decimal degrees
                                dlat = int(lat[0:2])
                                dlon = int(lon[0:3])
                                mlat = float(lat[2:])/60.0
                                mlon = float(lon[3:])/60.0

                                rlat = dlat + mlat
                                rlon = dlon + mlon

                                positions.append([rlat, rlon])

                                if printedtime == False:
                                    print("\t"+date[0:2]+"."+date[2:4]+"."+"20"+date[4:6]+" - "+parttime[0:2]+':'+parttime[2:4]+':'+parttime[4:6])
                                    print("\tInit at: "+str([rlat, rlon]))
                                    printedtime = True

                                ticks = int(time.mktime(mytime))
                                myticks = 0
                                if lasttime == -1:
                                    lasttime = ticks
                                    myticks = 0
                                else:
                                    myticks = ticks - lasttime
                                    lasttime = ticks

                                timediffs.append(myticks*1000)
                    if self.multiCheckbox.checkState() == Qt.Unchecked:
                        with open('template.html', 'r') as template:
                            tempstr = template.read()
                            tempstr = tempstr.replace('_ACCESS_TOKEN_', self.config["mapbox_access_token"])
                            tempstr = tempstr.replace('_REPLACE_POS_', str(positions))
                            tempstr = tempstr.replace('_REPLACE_TIME_', str(timediffs))
                            tempstr = tempstr.replace('_REPLACE_MULTINAMES_', str([os.path.split(fi)[1]]))
                            tempstr = tempstr.replace('_REPLACE_MULTIMAP_', "false")
                            out = fi.replace('.NMEA', '.nmea')
                            out = out.replace('.nmea', '.html')
                            out = open(out, 'w')
                            out.write(tempstr)
                            out.close()
                    else:
                        multiPositions.append(positions)
                        multiTimediffs.append(timediffs)
                        multiNames.append(os.path.split(fi)[1])
                else:
                    print("\tTES parsing mode")
                    while True:
                        bytes = f.read(2)
                        if len(bytes) < 2:
                            break # exit if eof

                        # type of point
                        types = struct.unpack('=h', bytes)
                        #if types[0] & 1 == 1:
                        #    print('Split mark')
                        #elif types[0] & 2 == 1:
                        #    print('Interest point')
                        #elif types[0] & 4 == 1:
                        #    print('Track point')

                        # date of record
                        bytes = f.read(4)
                        date = struct.unpack('=L', bytes)

                        s = int(0)
                        smask = 63
                        s = (date[0] & smask)

                        m = int(0)
                        mmask = smask << 6
                        m = (date[0] & mmask) >> 6

                        h = int(0)
                        hmask = 31 << 12
                        h = (date[0] & hmask) >> 12

                        d = int(0)
                        dmask = 31 << 17
                        d = (date[0] & dmask) >> 17

                        mo = int(0)
                        momask = 15 << 22
                        mo = (date[0] & momask) >> 22

                        y = int(0)
                        ymask = 63 << 26
                        y = ((date[0] & ymask) >> 26) + 2000

                        if printedtime == False:
                            print('\tDate: '+str(d)+'.'+str(mo)+'.'+str(y)+" - "+str(h)+':'+str(m)+':'+str(s))
                            printedtime = True

                        mytime = time.strptime(str(d)+'.'+str(mo)+'.'+str(y)+" - "+str(h)+':'+str(m)+':'+str(s), '%d.%m.%Y - %H:%M:%S')
                        ticks = int(time.mktime(mytime))
                        myticks = 0
                        if lasttime == -1:
                            lasttime = ticks
                            myticks = 0
                        else:
                            myticks = ticks - lasttime
                            lasttime = ticks

                        # lat
                        bytes = f.read(4)
                        lat = struct.unpack('=l', bytes)
                        #print('\tLat: '+str(lat[0]*1e-7))

                        # lon
                        bytes = f.read(4)
                        lon = struct.unpack('=l', bytes)
                        #print('\tLon: '+str(lon[0]*1e-7))

                        # alt
                        bytes = f.read(2)
                        alt = struct.unpack('=h', bytes)
                        #print('\tAlt:'+str(alt[0]))
                        #print('')

                        positions.append([lat[0]*1e-7,lon[0]*1e-7]);
                        timediffs.append(myticks*1000)
                    if self.multiCheckbox.checkState() == Qt.Unchecked:
                        with open('template.html', 'r') as template:
                            tempstr = template.read()
                            tempstr = tempstr.replace('_ACCESS_TOKEN_', self.config["mapbox_access_token"])
                            tempstr = tempstr.replace('_REPLACE_POS_', str(positions))
                            tempstr = tempstr.replace('_REPLACE_TIME_', str(timediffs))
                            tempstr = tempstr.replace('_REPLACE_MULTINAMES_', str([os.path.split(fi)[1]]))
                            tempstr = tempstr.replace('_REPLACE_MULTIMAP_', "false")
                            fi = fi.replace('.TES', '.html')
                            out = open(fi, 'w')
                            out.write(tempstr)
                            out.close()
                    else:
                        multiPositions.append(positions)
                        multiTimediffs.append(timediffs)
                        multiNames.append(os.path.split(fi)[1])

        # processing of individual files finishes
        if self.multiCheckbox.checkState() == Qt.Checked:
            print("in Multimode")
            with open('template.html', 'r') as template:
                tempstr = template.read()
                tempstr = tempstr.replace('_ACCESS_TOKEN_', self.config["mapbox_access_token"])
                tempstr = tempstr.replace('_REPLACE_POS_', str(multiPositions))
                tempstr = tempstr.replace('_REPLACE_TIME_', str(multiTimediffs))
                tempstr = tempstr.replace('_REPLACE_MULTINAMES_', str(multiNames))
                tempstr = tempstr.replace('_REPLACE_MULTIMAP_', "true")
                out = open("multimap.html", 'w')
                out.write(tempstr)
                out.close()

        QMessageBox.information(self, "Information",
                                    "Processing has finished")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWin()
    mainWin.show()
    sys.exit(app.exec_())
