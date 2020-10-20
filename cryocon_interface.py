#!/usr/bin/env python
# coding: utf-8

# # GUI Interface for CryoCon Temperature Controller
# 
# ## Requirements
# Ensure that `import-ipynb` module is installed
# 
# ## Compiling
# 1. Ensure fbs is installed `pip install fbs`
# 2. Iniate a project `python3 -m fbs startproject`
# 3. Freeze the binary `python3 -m fbs freeze`
# 4. Create an installer `python3 -m fbs installer`
# 
# ## Converting to .py
# To save this file for use as a CLI, convert it to a .py file using `jupyter nbconvert --to python <filename>`

# In[1]:


import os
import sys
import re
import serial
import pytemperature as pytemp
from functools import partial

# PyQt
from PyQt5 import QtGui

from PyQt5.QtCore import (
    Qt,
    QCoreApplication,
    QTimer,
    QThread
)

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QFileDialog,
    QMessageBox
)

# controller
from importlib import reload
import cryocon_controller as cryo


# In[2]:


reload( cryo )


# In[8]:


class CryoconInterface( QWidget ):
    
    #--- window close ---
    def closeEvent( self, event ):
        self.delete_controller()
        event.accept()
        
    
    #--- destructor ---
    def __del__( self ):
        self.delete_controller()
        
    
    #--- initializer ---
    def __init__( self, resources ): # FREEZE
    # def __init__( self ):
        super().__init__()
        
        #--- instance variables ---
        image_folder = resources + '/images/' # FREEZE
        # image_folder = os.getcwd() + '/images/' 
    
        self.img_redLight = QtGui.QPixmap(    image_folder + 'red-light.png'    ).scaledToHeight( 32 )        
        self.img_greenLight = QtGui.QPixmap(  image_folder + 'green-light.png'  ).scaledToHeight( 32 )
        self.img_yellowLight = QtGui.QPixmap( image_folder + 'yellow-light.png' ).scaledToHeight( 32 )
        
        self.ports  = self.getComPorts()
        self.port   = None
        self.inst   = None # the instrument
        self.channels = {} # storage for ui elements
        
        #--- timers ---
        # temperature update
        self.tmr_temp = QTimer()
        self.tmr_temp.setInterval( 1000 )
        self.tmr_temp.timeout.connect(
            self.update_channels_temp_ui
        )
        
        # range control
        self.tmr_range = QTimer()
        self.tmr_range.setInterval( 250 )
        self.tmr_range.timeout.connect(
            self.adjust_range
        )
        
        # debounce
        self.tmr_debounce = QTimer()
        self.tmr_debounce.setInterval( 500 )
        self.tmr_debounce.setSingleShot( True )
        
        #--- init UI ---
        self.init_ui()
        self.register_connections()
        
        #--- init variables ---
        
        

    def init_ui( self ):
        #--- main window ---
        self.setGeometry( 100, 100, 600, 200 )
        self.setWindowTitle( 'Cryocon Controller' )
        
        lo_main = QVBoxLayout()
        lo_main.addLayout( self.ui_mainToolbar() )
        lo_main.addLayout( self.ui_settings() )
#         lo_main.addSpacing( 35 )
#         lo_main.addLayout( self.ui_commands() )
        
        self.setLayout( lo_main )
        
        self.show()
       
    
    def ui_mainToolbar( self ):
        lo_mainToolbar = QHBoxLayout()
        
        self.ui_mainToolbar_comPorts( lo_mainToolbar )
        self.ui_mainToolbar_connect( lo_mainToolbar )
        self.ui_mainToolbar_enable( lo_mainToolbar )
        
        return lo_mainToolbar
    
    
    def ui_settings( self ):
        lo_settings = QHBoxLayout()
        
        self.ui_settings_channel( lo_settings, 'a' )
        self.ui_settings_channel( lo_settings, 'b' )
        
        return lo_settings
    
    
    def ui_commands( self ):
        lo_commands = QVBoxLayout()
      
        return lo_commands
        
    
    def ui_mainToolbar_comPorts( self, parent ):
        self.cmb_comPort = QComboBox()
        self.update_ports_ui()
        
        lo_comPort = QFormLayout()
        lo_comPort.addRow( 'COM Port', self.cmb_comPort )
        
        parent.addLayout( lo_comPort )
    
    
    def ui_mainToolbar_connect( self, parent ):
        # connect / disconnect
        self.lbl_statusLight = QLabel()
        self.lbl_statusLight.setAlignment( Qt.AlignCenter )
        self.lbl_statusLight.setPixmap( self.img_redLight )
        
        self.lbl_status = QLabel( 'Disconnected' )
        self.btn_connect = QPushButton( 'Connect' )
    
        lo_statusView = QVBoxLayout()
        lo_statusView.addWidget( self.lbl_statusLight )
        lo_statusView.addWidget( self.lbl_status )
        lo_statusView.setAlignment( Qt.AlignHCenter )
        
        lo_status = QHBoxLayout()
        lo_status.addLayout( lo_statusView )
        lo_status.addWidget( self.btn_connect )
        lo_status.setAlignment( Qt.AlignCenter )
        lo_status.setAlignment( Qt.AlignTop )
        parent.addLayout( lo_status )
        
    
    def ui_mainToolbar_enable( self, parent ):
        # enable/disable
        self.lbl_enableLight = QLabel()
        self.lbl_enableLight.setAlignment( Qt.AlignCenter )
        self.lbl_enableLight.setPixmap( self.img_redLight )
        
        self.lbl_enable = QLabel( 'Disabled' )
        self.btn_enable = QPushButton( 'Enable' )
        
        lo_enableView = QVBoxLayout()
        lo_enableView.addWidget( self.lbl_enableLight )
        lo_enableView.addWidget( self.lbl_enable )
        lo_enableView.setAlignment( Qt.AlignHCenter )
        
        lo_enable = QHBoxLayout()
        lo_enable.addLayout( lo_enableView )
        lo_enable.addWidget( self.btn_enable )
        lo_enable.setAlignment( Qt.AlignCenter )
        lo_enable.setAlignment( Qt.AlignTop )
        
        parent.addLayout( lo_enable )
        
        
    def ui_settings_channel( self, parent, channel, set_point = True ):
        lbl_channel = QLabel( channel.upper() )
        lbl_channel.setAlignment( Qt.AlignCenter )
        
        lbl_temp = QLabel( 'N/A' )
        lbl_temp.setAlignment( Qt.AlignCenter )
        
        lbl_unit = QLabel( 'K' )
        lbl_unit.setAlignment( Qt.AlignCenter )
        
        sb_temp = None
        if set_point:
            sb_temp = QDoubleSpinBox()
            sb_temp.setAlignment( Qt.AlignCenter )
        
        elements = {
            'lbl_channel': lbl_channel,
            'lbl_temp': lbl_temp,
            'lbl_unit': lbl_unit,
            'sb_temp': sb_temp
        }
        self.channels[ channel ] = elements
        
        lo_temp = QHBoxLayout()
        lo_temp.addStretch()
        lo_temp.addWidget( lbl_temp )
        lo_temp.addWidget( lbl_unit )
        lo_temp.addStretch()
        
        lo_channel = QVBoxLayout()
        lo_channel.setAlignment( Qt.AlignTop )
        
        lo_channel.addWidget( lbl_channel )
        lo_channel.addLayout( lo_temp )
        
        if sb_temp is not None:
            lo_channel.addWidget( sb_temp )
        
        parent.addLayout( lo_channel )
        
    #--- ui functionality ---
    
    def register_connections( self ):
        
        def handle_set_point_change( channel ):
            self.tmr_debounce.stop()
            try:
                self.tmr_debounce.timeout.disconnect()
                
            except:
                pass
                
            self.tmr_debounce.timeout.connect(
                lambda: self.set_temperature( channel )
            )
            
            self.tmr_debounce.start()
        
        
        self.cmb_comPort.currentTextChanged.connect( self.change_port )
        self.btn_connect.clicked.connect( self.toggle_connect )  
        self.btn_enable.clicked.connect( self.toggle_enable )  
        
        for ch, ch_ui in self.channels.items():
            sb_temp = ch_ui[ 'sb_temp' ]
            
            if sb_temp is not None:
                sb_temp.valueChanged.connect(
                    # must use closure to freeze channel
                    partial( handle_set_point_change, ch )  
                )

         
    def getComPorts( self ):
        """ (from https://stackoverflow.com/a/14224477/2961550)
        Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
        """
        if sys.platform.startswith( 'win' ):
            ports = [ 'COM%s' % (i + 1) for i in range( 256 ) ]
            
        elif sys.platform.startswith( 'linux' ) or sys.platform.startswith( 'cygwin' ):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob( '/dev/tty[A-Za-z]*' )
            
        elif sys.platform.startswith( 'darwin' ):
            ports = glob.glob( '/dev/tty.*' )
            
        else:
            raise EnvironmentError( 'Unsupported platform' )

        result = []
        for port in ports:
            try:
                s = serial.Serial( port )
                s.close()
                result.append( port )
                
            except ( OSError, serial.SerialException ):
                pass
            
        return result    
    
    
    #--- slot functions ---
    
    def change_port( self ):
        """
        Changes port and disconnects from current port if required
        """
        # disconnect and delete controller
        self.delete_controller()
          
        # update port
        self.update_port()
        
        
    def update_ports( self ):
        """
        Check available COMs, and update UI list
        """
        self.ports = self.getComPorts()
        self.update_ports_ui()
        
        
    def toggle_connect( self ):
        """
        Toggles connection between selected com port
        """
        # show waiting for communication
        self.lbl_status.setText( 'Waiting...' )
        self.lbl_statusLight.setPixmap( self.img_yellowLight )
        self.repaint()
        
        self.tmr_temp.stop()
        self.tmr_range.stop()
        
        # create laser controller if doesn't already exist, connect
        if self.inst is None:
            if not self.port:
                raise RuntimeError( 'Can not connect. No port selected.' )
            
            try:
                self.inst = cryo.CryoconController( self.port )
                self.inst.connect()
                
            except Exception as err:
                self.update_connected_ui( False )
                
                warning = QMessageBox()
                warning.setWindowTitle( 'Cryocon Controller Error' )
                warning.setText( 'Could not connect\n{}'.format( err ) )
                warning.exec()
            
        else:
            self.delete_controller()
        
        # update ui
        if self.inst is not None:
            connected = self.inst.connected
            self.update_connected_ui( connected )
            
            if connected:
                self.update_channels_ui()
                self.tmr_temp.start()   
            
        else:
            self.update_connected_ui( False )
            self.update_channels_temp_ui()
            
    
    def toggle_enable( self ):
        if not self.is_connected():
            return
        
        self.tmr_range.stop()
        
        # show waiting for communication
        self.lbl_enable.setText( 'Waiting...' )
        self.lbl_enableLight.setPixmap( self.img_yellowLight )
        self.repaint()
        
        if self.inst.enabled:
            self.inst.disable()
            
        else:
            self.inst.enable()
            self.tmr_range.start()
        
        self.update_enabled_ui( self.inst.enabled )
        
        
    def set_temperature( self, channel ):
        temp = self.temperature( channel )
        self.inst.set_temperature( channel, temp )
        
        
    #--- helper functions ---
    
    def delete_controller( self ):
        if self.inst is not None:
            if self.inst.connected:
                if self.inst.is_enabled():
                    self.inst.disable()
                
                self.inst.disconnect()
                
            del self.inst
            self.inst = None
            
            
    def parse_com_port( self, name ):
        pattern = "(\w+)\s*(\(\s*\w*\s*\))?"
        matches = re.match( pattern, name )
        if matches:
            name = matches.group( 1 )
            if name == 'No COM ports available...':
                return None
            else:
                return name
        else:
            return None
        
        
    def update_port( self ):
        self.port = self.cmb_comPort.currentText()
        
        
    def update_ports_ui( self ):
        self.cmb_comPort.clear()
        
        if len( self.ports ):
            self.cmb_comPort.addItems( self.ports )
            
        else:
            self.cmb_comPort.addItem( 'No COM ports available...' )
            
            
    def update_enabled_ui( self, enabled ):
        if enabled == True:
            enableText = 'Enable'
            enableLight = self.img_greenLight
            btnText = 'Disable'
            
        elif enabled == False:
            enableText = 'Disable'
            enableLight = self.img_redLight
            btnText = 'Enable'
            
        else:
            enableText = 'Error'
            enableLight = self.img_yellowLight
            btnText = 'Enable'
        
        self.lbl_enable.setText( enableText )
        self.lbl_enableLight.setPixmap( enableLight )
        self.btn_enable.setText( btnText )
            
    
    def update_connected_ui( self, connected ):
        if connected == True:
            statusText = 'Connected'
            statusLight = self.img_greenLight
            btnText = 'Disconnect'
            
        elif connected == False:
            statusText = 'Disconnected'
            statusLight = self.img_redLight
            btnText = 'Connect'
            
        else:
            statusText = 'Error'
            statusLight = self.img_yellowLight
            btnText = 'Connect'
        
        self.lbl_status.setText( statusText )
        self.lbl_statusLight.setPixmap( statusLight )
        self.btn_connect.setText( btnText )
        
        
    def update_channels_ui( self ):
        for ch, ch_ui in self.channels.items():
            # get ui elements
            ch_ui = self.channels[ ch ]
            lbl_channel = ch_ui[ 'lbl_channel' ]
            lbl_unit = ch_ui[ 'lbl_unit' ]
            sb_temp = ch_ui[ 'sb_temp' ]
            
            # update ui elements
            lbl_channel.setText( self.inst.channel_names[ ch ] )
            
            unit = self.inst.units[ ch ]
            lbl_unit.setText( unit )
            
            # hide and show set point controls
            if self.inst.get_channel_loop( ch ) is None:
                sb_temp.hide()
                
            else:
                sb_temp.show()
            
            # temperature mins and maxes
            max_temp = self.inst.channel_max_temperature( ch )
            
            min_temp = 0
            if unit == 'C':
                min_temp = pytemp.k2c( min_temp )
                
            elif unit == 'F':
                min_temp = pytemp.k2f( min_temp )
                
            sb_temp.setMinimum( min_temp )
            
            if max_temp is not None:
                sb_temp.setMaximum( max_temp )
            
            set_pt = self.inst.set_point( ch )
            if set_pt is not None:
                sb_temp.setValue( set_pt )
            
    
    def update_channels_temp_ui( self ):
        for ch, ch_ui in self.channels.items():
            ch_ui = self.channels[ ch ]
            lbl_temp = ch_ui[ 'lbl_temp' ]

            if self.inst:
                temp = self.inst.temperature( ch )
                temp = '{:.2f}'.format( temp )
                
            else:
                temp = 'N/A'
                
            lbl_temp.setText( temp )
            
        
    def is_connected( self ):   
        if self.inst is None:
            # not connected
            warning = QMessageBox()
            warning.setWindowTitle( 'CryoCon Controller Error' )
            warning.setText( 'Not connected.' )
            warning.exec()
            return False
        
        # connected
        return True
        
    
    def is_enabled( self ):
        # check if connected
        if not self.is_connected():
            return None
        
        if not self.inst.is_enabled():
            warning = QMessageBox()
            warning.setWindowTitle( 'CryoCon Controller Error' )
            warning.setText( 'Not enabled.' )
            warning.exec()
            return False
                    
        # enabled
        return True
    
    
    def temperature( self, channel ):
        sb_temp = self.channels[ channel ][ 'sb_temp' ]
        return sb_temp.value()
    
    
    def adjust_range( self ):
        """
        Automatically adjusts the range of the loop.
        """
        
        def change_range( curr, change ):
            """
            Gets the range relative to the given differing by change.
            """
            ranges = [ 'low', 'mid', 'hi' ]
            pos = ranges.index( curr )
            pos += change
            
            if ( pos < 0 ) or ( pos > len( ranges ) ):
                # index out of bounds
                return None
            
            return ranges[ pos ]
            
        # overlapping thresholds used to debounce change
        threshold_low  = 0.09
        threshold_high = 0.95
        
        for ch in self.channels.keys():
            loop = self.inst.get_channel_loop( ch )
            if loop is None:
                continue
                
            output = self.inst.get_output( loop )
            rng = self.inst.get_range( loop )
            new_rng = None
            if output < threshold_low:
                new_rng = change_range( rng, -1 ) 
                    
            elif output > threshold_high:
                new_rng = change_range( rng, 1 )
                    
            if new_rng is not None:
                 self.inst.set_range( loop, new_rng )
                    
                    
    


# In[9]:




