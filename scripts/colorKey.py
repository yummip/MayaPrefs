'''
DESCRIPTION :
this script allows you to color the keyframe's ticks in the timeline.

INSTALLATION :
copy the colorKey.py file in your maya scripts folder.
copy the colorKey.bmp icon in your icon folder (...\maya\<maya version>\prefs\icons).
open Maya, open the script editor and in a python tab, paste those two lines :

import colorKey as cK
cKUI = cK.ColorKey()

select both lines and middle mouse click and drag them to your shelf
assign the icon to the script via the shelf editor.

HOTKEYS :
Use the hotkey() function to add hotkeys to the ui buttons.
If you want to set a hotkey for the first left button, use as the
nameCommand : cK.hotkey(1)
Make sure the language is set to python. cK.hotkey(2) for the second button...
ON NEW MAYA STARTUP, you have to run the script at least once for the hotkeys to work.  

Help and documentation at www.guillaumegilbaud.fr
'''
import os
import cPickle as pickle
from functools import partial
import pymel.core as pmc
import maya.OpenMayaUI as OpenMayaUI
import maya.mel as mel

try:
    from PySide import QtGui, QtCore 
    from shiboken import wrapInstance
except:
    from PyQt4 import QtGui, QtCore
    from sip import wrapinstance as wrapInstance

__author__    = "Guillaume Gilbaud"
__version__   = "2.0.0"
__email__     = "guillaumegilbaud@gmail.com"


prefFileName = "kColorSettings.pref"

def show():
    
    if pmc.window("colorKeyWindow",q=True, exists=True):
        pmc.deleteUI("colorKeyWindow")
        
    if pmc.paneLayout('colorKeyPane',q=True,exists=True):
        pmc.deleteUI('colorKeyPane')
        
    if pmc.dockControl('colorKeyDocked',q=True,exists=True):
        pmc.deleteUI('colorKeyDocked')
    
    dialog = ColorKeyUI(getMayaWindow())
    dialog.show()
    

def getMayaWindow():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(long(ptr), QtGui.QMainWindow)

        
def preserveSelection(func):
    def inner(*args,**kwargs):
        sel = list(pmc.selected())
        result = func(*args,**kwargs)
        pmc.select(sel,replace=True)
        return result
    return inner


class ColorKey(object):
    
    @classmethod
    def importPref(cls):
        '''Import user preferences from file. If preference file doesn't exist, use default values.'''
        
        prefDir = pmc.internalVar(userPrefDir=True)
        if prefFileName in os.listdir(prefDir):
            prefFile = prefDir+prefFileName
            with open(prefFile,'rb') as fh:
                data = pickle.load(fh)
        else:
            data = {
                    'color1':['',(255,255,0),'_1'],
                    'color2':['',(255,0,0),'_2'],
                    'color3':['',(0,255,0),'_3'],
                    'color4':['',(255,0,255),'_4'],
                    'color5':['',(0,0,255),'_5'],
                    'color6':['',(0,255,255),'_6'],
                    'keyframing':-2,
                    }
        return data
    
    
    @classmethod
    def exportPref(cls,data,labelObject,buttonObject,keyframingButtonGrp):
        ''' Save user preferences to file. Call applyPref().
        
        :param data: dictionary. Main ui button's colors, labels... keyframing preference.
        :param labelObject: list of the 6 color key label objects from settings ui.
        :param buttonObject: list of the 6 color key buttons objects from settings ui.
        :param keyframingButtonGrp: the keyframing option buttonGrp object from settings ui.
        '''
        
        # Labels
        for i,j in enumerate(labelObject):
            data['color%s'%str(i+1)][0] = j.text()
        
        # Colors
        for i,j in enumerate(buttonObject):
            data['color%s'%str(i+1)][1] = (j.property('rgb')[0],j.property('rgb')[1],j.property('rgb')[2])
        
        # Keyframing option
        data['keyframing'] = keyframingButtonGrp.checkedId()
        
        prefDir = pmc.internalVar(userPrefDir=True)
        prefFile = prefDir+prefFileName
        with open(prefFile,'wb') as fh:
            pickle.dump(data, fh, pickle.HIGHEST_PROTOCOL)
        
        ColorKey.applyPref(data)
        
        
    @classmethod
    def applyPref(cls,data):
        '''Apply user preferences by updating keyticks colors in the timeline, and redraw the main UI.
        
        :param data: dictionary. Main ui button's colors, labels... keyframing preference. 
        '''
        
        rgbValues = []
        for i,j in enumerate(sorted(data)):
            if i != 6:
                rgbValues.append((float(data[j][1][0])/255.0,float(data[j][1][1])/255.0,float(data[j][1][2])/255.0))
        
        # Timeline keyticks color
        cKanimCrvs = [animCrv for animCrv in pmc.ls(type='animCurveTU') if 'coloredKey_' in animCrv.name()]
        for anmC in cKanimCrvs:
            colorID = pmc.listAttr(anmC, ud=True)[0]

            if colorID == '_1':
                anmC.curveColor.set(rgbValues[0],type='float3')
            elif colorID == '_2':
                anmC.curveColor.set(rgbValues[1],type='float3')
            elif colorID == '_3':
                anmC.curveColor.set(rgbValues[2],type='float3')
            elif colorID == '_4':
                anmC.curveColor.set(rgbValues[3],type='float3')
            elif colorID == '_5':
                anmC.curveColor.set(rgbValues[4],type='float3')
            elif colorID == '_6':
                anmC.curveColor.set(rgbValues[5],type='float3')
            
        # Update colorKey UI
        show()
        
        pmc.deleteUI('colorKeySettingsWindow')
        
            
    def __init__(self):
        
        pass
        
            
    def getInfo(self,color,colorID,keyframingOption):
        ''' Gather informations about the current selection, the current time and possible time range highligted in the timeline.
        Convert color argument into a tuple if it is not already. 
        Either call addColoredKey() or addNonColoredKey() or both, depending on gathered informations and user preferences.
        
        :param color: rgb values corresponding to one of the ui button's color
        :param colorID: string representing one of the ui button. Used to update keytick's color in the timeline.
        :param keyframingOption : int representing the keyframing option
        '''
        
        #Selection
        sel = list(pmc.selected())
        if not sel:
            pmc.confirmDialog(title='Color key error', message='Nothing selected! Please select something.',button='OK', defaultButton='OK')
            return
        
        # Color
        if not isinstance(color,tuple):
            color = color.getRgb()
        
        #Current frame
        currentFrame = int(pmc.currentTime(q=True))
        
        #Highlighted time range
        playBackSlider = mel.eval('$tmpVar=$gPlayBackSlider')
        if pmc.timeControl(playBackSlider,q=True, rangeVisible=True) ==True:
            rangeHighlighted = pmc.timeControl(playBackSlider, q=True, rangeArray=True)
            lowerBound = int(rangeHighlighted[0])
            upperBound = int(rangeHighlighted[1])
            
            # If a time range is highlighted, call addColorKey() only
            self.addColoredKey(color, colorID,sel,currentFrame,lowerBound,upperBound)
        
        else:
            onlyKeyedAttrPb = []
            # Only call addNonColoredKey() if keyframing preference is set to keyframe all or keyframe only keyed attr
            if keyframingOption != -4:
                onlyKeyedAttrPb = self.addNonColoredKey(sel)
            
            # If user preference is set to key only keyed attr and none of the attributes of a node have ever been keyframed,
            # warn the user.
            if onlyKeyedAttrPb:
                for node in onlyKeyedAttrPb:
                    pmc.warning('Your keyframing preference is currently set to keyframe only keyed attributes. None of the attributes of %s have ever been keyframed, skipped. See script editor for more.'%node)
            
            # Every other case
            else:
                self.addColoredKey(color,colorID,sel,currentFrame,currentFrame,currentFrame)
            
    
    @preserveSelection
    def addColoredKey(self,color,colorID, sel,currentFrame=None,lowerBound=None,upperBound=None):
        ''' 
        Create coloredKey attribute(s) with a unique suffix, and keyframe them at a given frame or relevant frames in a time range.
        Connect associated anim curves with color (ui button's color) and colorID ("reference" to the button) arguments.
        Enable the useCurveColor attribute of the anim curves will change the keyticks color.
        
        First check and try to delete coloredKey attributes and associated anim curves that are not in use anymore or shouldn't (trying
        to solve multiple keyframing/deleting keyframes scenarios). 
        
        :param color: tuple rgb values.
        :param colorID: string name. Used to update keytick's color in the timeline.
        :param sel: list of nodes.
        :param currentFrame: current time.
        :param lowerBound: lower bound of a timeline highligted range.
        :param upperBound: upper bound of a timeline highligted range.
        '''
        for node in sel:
            time = []
            pmc.select(node,replace=True)
            cKattrs = pmc.listAttr(ud=True, st='coloredKey_*')
        
            if not cKattrs:
                cKattrs=['coloredKey_0']
                time.append(currentFrame)
            
            else:
                # Delete coloredKey anim curves and associated attributes in the given time range
                time.append(currentFrame)
                animCrv = [pmc.ls(obj)[0] for obj in pmc.keyframe(node,q=True,name=True,t=(lowerBound,upperBound+1)) if obj.find('coloredKey_') != -1]
                if animCrv:
                    for anmC in animCrv:
                        numberOfKeys = anmC.numKeys()
                        if numberOfKeys > 1:
                            for i in reversed(range(0,numberOfKeys)):
                                if anmC.getWeightsLocked(i):
                                    anmC.remove(i)
                        attr = anmC.inputs(plugs=True)
                        try:
                            if anmC.getTime(0) in range(lowerBound,upperBound+1):
                                time.append(anmC.getTime(0))
                                pmc.delete(anmC)
                                try:
                                    pmc.deleteAttr(attr)
                                except TypeError:
                                    pmc.warning('%s : attribute doesn\'t exist, skipped.'%attr)
                        
                        except RuntimeError:
                            attrOff = [a for a in pmc.listAttr(node,ud=True,string='coloredKey_*')]
                            for a in attrOff:
                                if pmc.PyNode('%s.%s'%(node,a)).isMuted() != True:
                                    pmc.deleteAttr('%s.%s'%(node,a))
                                                
            # Create new coloredKey attribute
            if len(time)!=1:
                time = time[1:]
            for t in time:                                          
                suffix = int(cKattrs[-1].rpartition('_')[2])+1 
                cKattr = 'coloredKey_%s' %suffix
                cKattrs.append(cKattr)
                node.addAttr(cKattr,at=bool,dv=1,k=True,h=True)
                pmc.setKeyframe(at=cKattr,time=t)
                
                cKattr = pmc.ls('%s.%s'%(node,cKattr))[0]
                animCrv = cKattr.inputs()[0]
                cKattr >> '%s.useCurveColor'%animCrv
                animCrv.curveColor.set(float(color[0])/255.0, float(color[1])/255.0, float(color[2])/255.0, type='double3')
                animCrv.setWeighted(True)
                animCrv.setWeightsLocked(0,False)
                animCrv.addAttr(colorID,at=bool,k=False,h=True)
                pmc.mute(cKattr)
                    

    def addNonColoredKey(self,sel):
        ''' Read user preferences, filter attributes on nodes to either keyframe all visible,keyable attributes of a node or only attributes
        that have already been keyed.

        :param sel: list of nodes.
        :return result: list.
        '''
        data = ColorKey.importPref()
        result=[]
        
        for node in sel:
            attrs = pmc.listAttr(node,k=True,v=True)
            
            if data['keyframing'] == -2:                # Keyframe all attributes
                attrsToKey = [pmc.PyNode('%s.%s'%(node,attr)) for attr in attrs]
                self.keyframeNonColoredKey(attrsToKey)
                
            else:                                       # Keyframe only keyed attributes
                animCurves = []
                for attr in attrs:
                    anmC = pmc.keyframe('%s.%s'%(node,attr),q=True,name=True)
                    if anmC:
                        animCurves.append(pmc.PyNode(anmC[0]))

                if not animCurves:                      # Attributes have never been keyframed, append node to result
                    result.append(node)
                else:
                    attrsToKey = [anmCrv.outputs(plugs=True)[0] for anmCrv in animCurves]
                    self.keyframeNonColoredKey(attrsToKey)
                    
        return result
        
                        
    def keyframeNonColoredKey(self,attrs):
        ''' Compare the value of an attribute with the value of the attribute's anim curve at the current time. If the values are the same
        insert a keyframe, if not set a keyframe.
        
        :param attrs: list of attributes
        '''
        for attr in attrs:
            keyframeValue = pmc.keyframe(attr, q=True, eval=True)

            if not keyframeValue:
                pmc.setKeyframe(attr)    
            else:
                if attr.get() != keyframeValue[0]:
                    pmc.setKeyframe(attr)
                else:
                    pmc.setKeyframe(attr, i=True)
            

    def deleteColoredKey(self):
        ''' Delete every coloredKey attributes and associated anim curves for the currently selected object(s).'''
        
        sel = list(pmc.selected())
        if not sel:
            pmc.confirmDialog(title='Color key error', message='Nothing selected! Please select something.',button='OK', defaultButton='OK')
            return
        
        warning = pmc.confirmDialog(title='remove keyticks color?', message='This will remove every colorKey keytick\'s color for the currently selected object(s).\nContinue?', button=['Yes','No'], defaultButton='Yes',cancelButton='No', dismissString='No')
        if warning == 'No':
            return
        else:
            for node in sel:
                animCrv = [pmc.ls(obj)[0] for obj in pmc.keyframe(node,q=True,name=True) if obj.find('coloredKey_') != -1]
                if animCrv:
                    for anmC in animCrv:
                        attr = anmC.inputs(plugs=True)
                        pmc.delete(anmC)
                        try:
                            pmc.deleteAttr(attr)
                        except TypeError:
                            pmc.warning('%s : attribute doesn\'t exist, skipped.'%attr)


class ColorKeyUI(QtGui.QDialog):
    ''' Color key UI'''
    
    def __init__(self, parent=None):
        super(ColorKeyUI, self).__init__(parent)
        self.setWindowTitle("Keyframe colors")
        self.setObjectName("colorKeyWindow")
        self.setModal(False)
        
        # Import preferences
        data = ColorKey.importPref()
        
        # Docking
        floatingLayout = pmc.paneLayout('colorKeyPane',configuration='single')
        pmc.control("colorKeyWindow",e=True,p=floatingLayout)

        if pmc.about(v=True) == '2016':
            pmc.dockControl('colorKeyDocked',area='bottom',allowedArea = ['bottom','top'],content=floatingLayout,floating=True,w=500,h=80,fixedWidth=True,label='Color Key')
        else:
            pmc.dockControl('colorKeyDocked',area='bottom',allowedArea = ['bottom','top'],content=floatingLayout,floating=True,w=500,h=80,sizeable=False,label='Color Key')
        
        # Menu
        menuBar = QtGui.QMenuBar(self)
        optionsMenu = QtGui.QMenu('Options')
        menuBar.addMenu(optionsMenu)
        
        # Menu item : filter graph editor
        self.filterGraphAction = QtGui.QAction(self)
        self.filterGraphAction.setText('Filter graph editor')
        self.filterGraphAction.setCheckable(True)
        self.filterGraphAction.setChecked(True)
        optionsMenu.addAction(self.filterGraphAction)
        
        # Menu item : settings
        settingsAction = QtGui.QAction(self)
        settingsAction.setText('Settings')
        optionsMenu.addAction(settingsAction)
        
        optionsMenu.addSeparator()
        
        # Menu item : remove colors
        removeColorAction = QtGui.QAction(self)
        removeColorAction.setText('Remove colors')
        optionsMenu.addAction(removeColorAction)
        
        optionsMenu.addSeparator()
        
        # Menu item : help
        helpAction = QtGui.QAction(self)
        helpAction.setText('Help + hotkeys')
        optionsMenu.addAction(helpAction)
        
        # MainVbox
        mainVbox=QtGui.QVBoxLayout(self)
        mainVbox.insertSpacing(0,10)
            
        # Buttons
        hbox = QtGui.QHBoxLayout()
        mainVbox.addLayout(hbox)
        color1Btn = QtGui.QPushButton(data['color1'][0])
        color1Btn.setStyleSheet("background:rgb%s;height:8px;color:black;"%str(data['color1'][1]))
        color2Btn = QtGui.QPushButton(data['color2'][0])
        color2Btn.setStyleSheet("background:rgb%s;height:8px;color:black;"%str(data['color2'][1]))
        color3Btn = QtGui.QPushButton(data['color3'][0])
        color3Btn.setStyleSheet("background:rgb%s;height:8px;color:black;"%str(data['color3'][1]))
        color4Btn = QtGui.QPushButton(data['color4'][0])
        color4Btn.setStyleSheet("background:rgb%s;height:8px;color:black;"%str(data['color4'][1]))
        color5Btn = QtGui.QPushButton(data['color5'][0])
        color5Btn.setStyleSheet("background:rgb%s;height:8px;color:black;"%str(data['color5'][1]))
        color6Btn = QtGui.QPushButton(data['color6'][0])
        color6Btn.setStyleSheet("background:rgb%s;height:8px;color:black;"%str(data['color6'][1]))
        hbox.addWidget(color1Btn)
        hbox.addWidget(color2Btn)
        hbox.addWidget(color3Btn)
        hbox.addWidget(color4Btn)
        hbox.addWidget(color5Btn)
        hbox.addWidget(color6Btn)
        
        #Keyframing option info text
        hbox = QtGui.QHBoxLayout()
        mainVbox.addLayout(hbox,0)
        label = QtGui.QLabel('keyframing option : ')
        hbox.addWidget(label)
        
        if data['keyframing'] == -2:
            keyframeOption = 'Keyframe all attributes'
        elif data['keyframing'] == -3:
            keyframeOption = 'Keyframe only keyed attributes'
        else:
            keyframeOption = 'Just add colors'
        
        label = QtGui.QLabel(keyframeOption)
        label.setStyleSheet("color:orange;")
        emptyLabel = QtGui.QLabel()
        emptyLabel.setMinimumWidth(300)
        hbox.addWidget(label)
        hbox.addWidget(emptyLabel)
        
        # Connections
        cK = ColorKey()
        color1Btn.released.connect(partial(cK.getInfo,color1Btn.palette().color(QtGui.QPalette.Button),'_1',data['keyframing']))
        color2Btn.released.connect(partial(cK.getInfo,color2Btn.palette().color(QtGui.QPalette.Button),'_2',data['keyframing']))
        color3Btn.released.connect(partial(cK.getInfo,color3Btn.palette().color(QtGui.QPalette.Button),'_3',data['keyframing']))
        color4Btn.released.connect(partial(cK.getInfo,color4Btn.palette().color(QtGui.QPalette.Button),'_4',data['keyframing']))
        color5Btn.released.connect(partial(cK.getInfo,color5Btn.palette().color(QtGui.QPalette.Button),'_5',data['keyframing']))
        color6Btn.released.connect(partial(cK.getInfo,color6Btn.palette().color(QtGui.QPalette.Button),'_6',data['keyframing']))
        
        self.filterGraphAction.triggered.connect(self.graphEditorFilter)
        settingsAction.triggered.connect(self.showSettingsWindow)
        removeColorAction.triggered.connect(self.removeColor)
        helpAction.triggered.connect(self.openHelp)
        
        
    def graphEditorFilter(self):
        '''
        Create an itemFilterAttr to hide the display of coloredKey_ attributes in the graph editor.
        It will first delete any previous cKattrFilter if found.
        '''
        filter = pmc.ls('cKattrFilter',exactType='objectMultiFilter')
        if filter:
            pmc.setAttr('cKattrFilter.disable',1)
            pmc.delete('cKattrFilter')
            
        if self.filterGraphAction.isChecked():
            cKattrFilter = pmc.itemFilterAttr('cKattrFilter', bn='coloredKey_*', negate=True)
            pmc.outlinerEditor('graphEditor1OutlineEd', edit=True, attrFilter=cKattrFilter) 
        

    def showSettingsWindow(self):

        if pmc.window('colorKeySettingsWindow',q=True, exists=True):
            pmc.deleteUI('colorKeySettingsWindow')
        dialog = ColorKeySettingsUI(getMayaWindow())
        dialog.show()
        
    def removeColor(self):
        
        cK = ColorKey()
        cK.deleteColoredKey()
    
    
    def openHelp(self):
        
        pmc.showHelp("http://www.guillaumegilbaud.fr/scripts.html",a=True)
        

class ColorKeySettingsUI(QtGui.QDialog):
    ''' Color key settings UI'''
    
    def __init__(self, parent=None):
        super(ColorKeySettingsUI, self).__init__(parent)
        self.setWindowTitle('settings')
        self.setObjectName('colorKeySettingsWindow')
        self.setModal(False)
        self.setFixedSize(350,450)
        
        data = ColorKey.importPref()
        lineEditLabelObject = []
        buttonObject = []
        lineEditHotkeyObject = []
        altOptionObject = []
        ctrlOptionObject = []
        
        # MainVbox
        mainVbox = QtGui.QVBoxLayout(self)
        
        # Labels and colors
        text = QtGui.QLabel('Labels and colors')
        text.setStyleSheet("background:black;color:white;font:bold;qproperty-alignment: AlignCenter;")
        mainVbox.addWidget(text)
        
        for i in range(1,7):
            # Color title
            hbox = QtGui.QHBoxLayout()
            mainVbox.addLayout(hbox,0)
            text = QtGui.QLabel('Color %s'%i)
            text.setStyleSheet("font:bold;")
            hbox.addWidget(text)
        
            # Hbox
            hbox = QtGui.QHBoxLayout()
            mainVbox.addLayout(hbox,0)
            
            # Label
            text1 = QtGui.QLabel('Label :')
            lineEditLabel = QtGui.QLineEdit(data['color%s'%i][0])
            lineEditLabelObject.append(lineEditLabel)
            
            # Color
            text2 = QtGui.QLabel('Color :')
            pickColorButton = QtGui.QPushButton('Pick color') 
            pickColorButton.setProperty('rgb',data['color%s'%i][1])
            pixmap = QtGui.QPixmap(36,24)
            pixmap.fill( QtGui.QColor(data['color%s'%i][1][0],data['color%s'%i][1][1],data['color%s'%i][1][2]))
            pickColorButton.setIcon(QtGui.QIcon(pixmap))
            buttonObject.append(pickColorButton)
            
            # Add and connect
            hbox.addWidget(text1)
            hbox.addWidget(lineEditLabel)
            hbox.addWidget(text2)
            hbox.addWidget(pickColorButton)
            pickColorButton.released.connect(partial(self.picker,buttonObject[i-1]))
        
        # Keyframing option
        mainVbox.insertSpacing(13,10)
        text = QtGui.QLabel('Keyframing option')
        text.setStyleSheet("background:black;color:white;font:bold;qproperty-alignment: AlignCenter;")
        mainVbox.addWidget(text)
        hbox = QtGui.QHBoxLayout()
        mainVbox.addLayout(hbox,0)
        keyframingButtonGrp = QtGui.QButtonGroup(hbox)
        keyAllAttrOption = QtGui.QRadioButton('keyframe all attributes')
        keyOnlyKeyedAttrOption = QtGui.QRadioButton('keyframe only keyed attributes')
        hbox.addWidget(keyAllAttrOption)
        hbox.addWidget(keyOnlyKeyedAttrOption)
        keyframingButtonGrp.addButton(keyAllAttrOption)
        keyframingButtonGrp.addButton(keyOnlyKeyedAttrOption)
        
        hbox = QtGui.QHBoxLayout()
        mainVbox.addLayout(hbox,0)
        justAddColorOption = QtGui.QRadioButton('just add color')
        keyframingButtonGrp.addButton(justAddColorOption)
        hbox.addWidget(justAddColorOption)
        
        if data['keyframing'] == -2:
            keyAllAttrOption.setChecked(True)
        elif data['keyframing'] == -3:
            keyOnlyKeyedAttrOption.setChecked(True)
        else:
            justAddColorOption.setChecked(True)
        
        # Separator
        line = QtGui.QFrame()
        line.setFrameShape(QtGui.QFrame.HLine)
        mainVbox.addWidget(line)
        
        # Apply and cancel buttons
        hbox = QtGui.QHBoxLayout()
        mainVbox.addLayout(hbox,0)
        applyButton = QtGui.QPushButton('Apply and save')
        applyButton.setStyleSheet("height:30px;")
        cancelButton = QtGui.QPushButton('Cancel')
        cancelButton.setStyleSheet("height:30px;")
        hbox.addWidget(applyButton)
        hbox.addWidget(cancelButton)
        applyButton.released.connect(partial(ColorKey.exportPref,data,lineEditLabelObject,buttonObject,keyframingButtonGrp))
        cancelButton.released.connect(self.cancelSettings)
        
        
    def picker(self, button):
        '''
        Opens a QCOlorDialog. Uses the rgb property of the button to set the starting color. Will update rgb property and button's icon
        color when valid.
         '''
        rgbValue = QtGui.QColor(button.property('rgb')[0],button.property('rgb')[1],button.property('rgb')[2])
        
        dialog = QtGui.QColorDialog.getColor(rgbValue)
        if dialog.isValid():
            rgb = (dialog.red(),dialog.green(),dialog.blue())
            pixmap = QtGui.QPixmap(36,24)
            pixmap.fill(QtGui.QColor(rgb[0],rgb[1],rgb[2]))
            button.setProperty('rgb',rgb)
            button.setIcon(QtGui.QIcon(pixmap))
    
    
    def cancelSettings(self):
        ''' Delete settingsUI.'''
        pmc.deleteUI('colorKeySettingsWindow')
        
        
def hotkey(index):
    
    cK = ColorKey()
    data = ColorKey.importPref()
    
    if index == 1:
        cK.getInfo(data['color1'][1],'_1',data['keyframing'])
    elif index == 2:
        cK.getInfo(data['color2'][1],'_2',data['keyframing'])
    elif index == 3:
        cK.getInfo(data['color3'][1],'_3',data['keyframing'])
    elif index == 4:
        cK.getInfo(data['color4'][1],'_4',data['keyframing'])
    elif index == 5:
        cK.getInfo(data['color5'][1],'_5',data['keyframing'])
    elif index == 6:
        cK.getInfo(data['color6'][1],'_6',data['keyframing'])
