import csv
import logging
from pathlib import Path
from abc import ABC, abstractmethod

import numpy as np
import SimpleITK as sitk

import vtk, qt, ctk, slicer
import sitkUtils as su
from slicer.ScriptedLoadableModule import *


BLACK = 0, 0, 0
GRAY = 0.5, 0.5, 0.5
LIGHT_GRAY = 0.75, 0.75, 0.75
WHITE = 1, 1, 1

#
# SemiologyVisualization
#

class SemiologyVisualization(ScriptedLoadableModule):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Semiology Visualization"
    self.parent.categories = ["Epilepsy Semiology"]
    self.parent.dependencies = []
    self.parent.contributors = ["Fernando Perez-Garcia (University College London)"]
    self.parent.helpText = """
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
""" # replace with organization, grant and thanks.

#
# SemiologyVisualizationWidget
#


import string
semiologies = [f'Semiology {x}' for x in string.ascii_uppercase]


class SemiologyVisualizationWidget(ScriptedLoadableModuleWidget):

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.logic = SemiologyVisualizationLogic()
    self.parcellation = GIFParcellation(
      segmentationPath=self.logic.getGifSegmentationPath(),
      colorTablePath=self.logic.getGifTablePath(),
    )
    self.makeGUI()
    self.parcellationLabelMapNode = None
    slicer.semiologyVisualization = self
    self.logic.installRepository()

  def makeGUI(self):
    self.makeLoadDataButton()
    self.makeSettingsButton()
    self.makeSemiologiesButton()
    self.makeUpdateButton()

    # Add vertical spacer
    self.layout.addStretch(1)

  def makeSettingsButton(self):
    self.settingsCollapsibleButton = ctk.ctkCollapsibleButton()
    self.settingsCollapsibleButton.enabled = False
    self.settingsCollapsibleButton.text = 'Settings'
    self.settingsLayout = qt.QFormLayout(self.settingsCollapsibleButton)
    self.layout.addWidget(self.settingsCollapsibleButton)

    self.makeDominantHemisphereButton()
    self.makeEzHemisphereButton()
    self.makeColorsButton()
    self.autoUpdateCheckBox = qt.QCheckBox()
    self.autoUpdateCheckBox.setChecked(True)
    self.settingsLayout.addRow('Auto-update: ', self.autoUpdateCheckBox)

  def makeDominantHemisphereButton(self):
    self.leftDominantRadioButton = qt.QRadioButton('Left')
    self.rightDominantRadioButton = qt.QRadioButton('Right')
    self.leftDominantRadioButton.setChecked(True)
    dominantHemisphereLayout = qt.QHBoxLayout()
    dominantHemisphereLayout.addWidget(self.leftDominantRadioButton)
    dominantHemisphereLayout.addWidget(self.rightDominantRadioButton)
    self.leftDominantRadioButton.toggled.connect(self.onAutoUpdateButton)
    self.rightDominantRadioButton.toggled.connect(self.onAutoUpdateButton)
    self.settingsLayout.addRow(
      'Dominant hemisphere: ', dominantHemisphereLayout)

  def makeEzHemisphereButton(self):
    self.leftEzRadioButton = qt.QRadioButton('Left')
    self.rightEzRadioButton = qt.QRadioButton('Right')
    self.leftEzRadioButton.setChecked(True)
    ezHemisphereLayout = qt.QHBoxLayout()
    ezHemisphereLayout.addWidget(self.leftEzRadioButton)
    ezHemisphereLayout.addWidget(self.rightEzRadioButton)
    self.leftEzRadioButton.toggled.connect(self.onAutoUpdateButton)
    self.rightEzRadioButton.toggled.connect(self.onAutoUpdateButton)
    self.settingsLayout.addRow('Epileptogenic zone: ', ezHemisphereLayout)

  def makeColorsButton(self):
    self.logic.removeColorMaps()
    self.colorSelector = slicer.qMRMLColorTableComboBox()
    self.colorSelector.nodeTypes = ["vtkMRMLColorNode"]
    self.colorSelector.hideChildNodeTypes = (
      "vtkMRMLDiffusionTensorDisplayPropertiesNode",
      "vtkMRMLProceduralColorNode",
    )
    self.colorSelector.addEnabled = False
    self.colorSelector.removeEnabled = False
    self.colorSelector.noneEnabled = False
    self.colorSelector.selectNodeUponCreation = True
    self.colorSelector.showHidden = True
    self.colorSelector.showChildNodeTypes = True
    self.colorSelector.setMRMLScene(slicer.mrmlScene)
    self.colorSelector.setToolTip("Choose a colormap")
    self.colorSelector.currentNodeID = 'vtkMRMLColorTableNodeFileCividis.txt'
    self.colorSelector.currentNodeID = None
    self.colorSelector.currentNodeChanged.connect(self.onAutoUpdateButton)
    self.settingsLayout.addRow('Colormap: ', self.colorSelector)

  def makeSemiologiesButton(self):
    self.semiologiesCollapsibleButton = ctk.ctkCollapsibleButton()
    self.semiologiesCollapsibleButton.enabled = False
    self.semiologiesCollapsibleButton.text = 'Semiologies'
    self.semiologiesCollapsibleButton.setChecked(False)
    self.layout.addWidget(self.semiologiesCollapsibleButton)

    semiologiesFormLayout = qt.QFormLayout(self.semiologiesCollapsibleButton)
    semiologiesFormLayout.addWidget(self.getSemiologiesWidget())

  def makeLoadDataButton(self):
    self.loadDataButton = qt.QPushButton('Load data')
    self.loadDataButton.clicked.connect(self.onLoadDataButton)
    self.layout.addWidget(self.loadDataButton)

  def makeUpdateButton(self):
    self.updateButton = qt.QPushButton('Update')
    self.updateButton.enabled = False
    self.updateButton.clicked.connect(self.updateColors)
    self.layout.addWidget(self.updateButton)

  def getSemiologiesWidget(self):
    from mega_analysis import get_all_semiology_terms
    self.semiologiesDict = self.logic.getSemiologiesDict(
      get_all_semiology_terms(), self.onAutoUpdateButton)
    semiologiesWidget = qt.QWidget()
    semiologiesLayout = qt.QGridLayout(semiologiesWidget)
    semiologiesLayout.addWidget(qt.QLabel('<b>Semiology</b>'), 0, 0)
    semiologiesLayout.addWidget(qt.QLabel('<b>Left</b>'), 0, 1)
    semiologiesLayout.addWidget(qt.QLabel('<b>Right</b>'), 0, 2)
    iterable = enumerate(self.semiologiesDict.items(), start=1)
    for row, (semiology, widgetsDict) in iterable:
      semiologiesLayout.addWidget(qt.QLabel(semiology), row, 0)
      semiologiesLayout.addWidget(widgetsDict['leftCheckBox'], row, 1)
      semiologiesLayout.addWidget(widgetsDict['rightCheckBox'], row, 2)
    return semiologiesWidget

  def getScoresFromGUI(self):
    from mega_analysis import get_scores
    semiologyTerm = self.semiologyTermFromGUI()
    if semiologyTerm is None:
      return
    scoresDict = get_scores(
      semiology_term=semiologyTerm,
    )
    return scoresDict

  def semiologyTermFromGUI(self):
    """TODO"""
    for (semiologyTerm, widgetsDict) in self.semiologiesDict.items():
      if widgetsDict['leftCheckBox'].isChecked() or widgetsDict['rightCheckBox'].isChecked():
        result = semiologyTerm
        break
    else:
      result = None
    return result

  # Slots
  def onAutoUpdateButton(self):
    if self.autoUpdateCheckBox.isChecked():
      self.updateColors()

  def updateColors(self):
    colorNode = self.colorSelector.currentNode()
    if colorNode is None:
      slicer.util.errorDisplay('No color node is selected')
    scoresDict = self.getScoresFromGUI()
    try:
      self.scoresVolumeNode = self.logic.getScoresVolumeNode(
        scoresDict, colorNode, self.parcellationLabelMapNode)
    except Exception as e:
      print(e)
      print('Error getting parcellation label map. Click on "Load data"')
      return
    self.parcellation.setScoresColors(scoresDict, colorNode)

    slicer.util.setSliceViewerLayers(
      foreground=self.scoresVolumeNode,
      foregroundOpacity=0,
      labelOpacity=0,
    )
    self.scoresVolumeNode.GetDisplayNode().SetInterpolate(False)

  def onSelect(self):
    # parcellationPath = Path(self.parcellationPathEdit.currentPath)
    # referencePath = Path(self.referencePathEdit.currentPath)
    # parcellationIsFile = parcellationPath.is_file()
    # referenceIsFile = referencePath.is_file()
    # if not parcellationIsFile:
    #   print(parcellationIsFile, 'does not exist')
    # if not referenceIsFile:
    #   print(referenceIsFile, 'does not exist')
    # self.applyButton.enabled = parcellationIsFile and referenceIsFile

    scoresPath = Path(self.scoresPathEdit.currentPath)
    scoresIsFile = scoresPath.is_file()
    if not scoresIsFile:
      print(scoresIsFile, 'does not exist')
    self.applyButton.enabled = scoresIsFile

  def onLoadDataButton(self):
    logic = SemiologyVisualizationLogic()
    self.referenceVolumeNode = self.logic.loadVolume(
      logic.getDefaultReferencePath())
    self.parcellationLabelMapNode = logic.loadParcellation(
      logic.getDefaultParcellationPath())
    slicer.util.setSliceViewerLayers(
      label=None,
    )
    self.parcellation.load()
    self.updateButton.enabled = True
    self.semiologiesCollapsibleButton.enabled = True
    self.settingsCollapsibleButton.enabled = True


#
# SemiologyVisualizationLogic
#

class SemiologyVisualizationLogic(ScriptedLoadableModuleLogic):

  def getSemiologiesDict(self, semiologies, slot):
    semiologiesDict = {}
    for semiology in semiologies:
      leftCheckBox = qt.QCheckBox()
      rightCheckBox = qt.QCheckBox()
      leftCheckBox.toggled.connect(slot)
      rightCheckBox.toggled.connect(slot)
      semiologiesDict[semiology] = dict(
          leftCheckBox=leftCheckBox,
          rightCheckBox=rightCheckBox,
      )
    return semiologiesDict

  def loadVolume(self, imagePath):
    stem = Path(imagePath).name.split('.')[0]
    try:
      volumeNode = slicer.util.getNode(stem)
    except slicer.util.MRMLNodeNotFoundException:
      volumeNode = slicer.util.loadVolume(str(imagePath))
    return volumeNode

  def loadParcellation(self, imagePath, gifVersion=None):
    stem = Path(imagePath).name.split('.')[0]
    try:
      volumeNode = slicer.util.getNode(stem)
    except Exception as e:  # slicer.util.MRMLNodeNotFoundException:
      print(e)
      volumeNode = slicer.util.loadLabelVolume(str(imagePath))
      colorNode = self.getGifColorNode(version=gifVersion)
      displayNode = volumeNode.GetDisplayNode()
      displayNode.SetAndObserveColorNodeID(colorNode.GetID())
    return volumeNode

  def getGifTablePath(self, version=None):
    version = 3 if version is None else version
    colorDir = self.getResourcesDir() / 'Color'
    filename = f'BrainAnatomyLabelsV{version}_0.txt'
    colorPath = colorDir / filename
    return colorPath

  def getGifSegmentationPath(self):
    return self.getImagesDir() / 'MNI_152_gif_cerebrum.seg.nrrd'

  def getGifColorNode(self, version=None):
    colorPath = self.getGifTablePath(version=version)
    colorNodeName = colorPath.stem
    className = 'vtkMRMLColorTableNode'
    colorNode = slicer.util.getFirstNodeByClassByName(className, colorNodeName)
    if colorNode is None:
      colorNode = slicer.util.loadColorTable(str(colorPath))
    return colorNode

  def getGifSegmentationNode(self):
    return slicer.util.loadSegmentation(str(self.getGifSegmentationPath()))

  def getResourcesDir(self):
    moduleDir = Path(slicer.util.modulePath(self.moduleName)).parent
    resourcesDir = moduleDir / 'Resources'
    return resourcesDir

  def getImagesDir(self):
    return self.getResourcesDir() / 'Image'

  def getDefaultReferencePath(self):
    return self.getImagesDir() / 'MNI_152_mri.nii.gz'

  def getDefaultParcellationPath(self):
    return self.getImagesDir() / 'MNI_152_gif.nii.gz'

  def getScoresVolumeNode(self, scoresDict, colorNode, parcellationLabelMapNode):
    parcellationImage = su.PullVolumeFromSlicer(parcellationLabelMapNode)
    parcellationArray = sitk.GetArrayViewFromImage(parcellationImage)
    scoresArray = np.zeros_like(parcellationArray)

    for (label, score) in scoresDict.items():
      label = int(label)
      score = float(score)
      labelMask = parcellationArray == label
      scoresArray[labelMask] = score

    scoresImage = self.getImageFromArray(scoresArray, parcellationImage)
    scoresName = 'Scores'
    scoresVolumeNode = su.PushVolumeToSlicer(scoresImage, name=scoresName)
    displayNode = scoresVolumeNode.GetDisplayNode()
    displayNode.SetAutoThreshold(False)
    displayNode.SetAndObserveColorNodeID(colorNode.GetID())
    displayNode.SetLowerThreshold(1)
    displayNode.ApplyThresholdOn()
    displayNode.SetAutoWindowLevel(False)
    windowMin = scoresArray[scoresArray > 0].min()
    windowMax = scoresArray.max()
    displayNode.SetWindowLevelMinMax(windowMin, windowMax)
    return scoresVolumeNode

  def getImageFromArray(self, array, referenceImage):
    image = sitk.GetImageFromArray(array)
    image.SetDirection(referenceImage.GetDirection())
    image.SetOrigin(referenceImage.GetOrigin())
    image.SetSpacing(referenceImage.GetSpacing())
    return image

  def readScores(self, scoresPath):
    with open(scoresPath) as csvfile:
      reader = csv.reader(csvfile)
      next(reader)  # assume there is a header row
      scoresDict = {int(label): float(score) for (label, score) in reader}
    return scoresDict

  def getTestScores(self):
    scoresPath = self.getResourcesDir() / 'Test' / 'head.csv'
    return self.readScores(scoresPath)

  def removeColorMaps(self):
    for colorNode in slicer.util.getNodesByClass('vtkMRMLColorTableNode'):
      if colorNode.GetName() not in COLORMAPS:
        slicer.mrmlScene.RemoveNode(colorNode)

  def installRepository(self):
    repoDir = Path('~/git/Epilepsy-Repository/').expanduser()
    slicer.util.pip_install(
      # 'git+https://github.com/thenineteen/Epilepsy-Repository#egg=mega_analysis',
      f'--editable {repoDir}',
    )


class SemiologyVisualizationTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SemiologyVisualization1()

  def test_SemiologyVisualization1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import SampleData
    SampleData.downloadFromURL(
      nodeNames='FA',
      fileNames='FA.nrrd',
      uris='http://slicer.kitware.com/midas3/download?items=5767',
      checksums='SHA256:12d17fba4f2e1f1a843f0757366f28c3f3e1a8bb38836f0de2a32bb1cd476560')
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = SemiologyVisualizationLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')


class Parcellation(ABC):
  def __init__(self, segmentationPath):
    self.segmentationPath = Path(segmentationPath)
    self.segmentationNode = None
    self._labelMap = None

  # @property
  # def label_map(self):
  #   if self._labelMap is None:
  #     self._labelMap = sitk.ReadImage(str(self.parcellation_path))
  #     if 'float' in self._labelMap.GetPixelIDTypeAsString():
  #       self._labelMap = sitk.Cast(self._labelMap, sitk.sitkUInt16)
  #   return self._labelMap

  # Note that @property must come before @abstractmethod
  @property
  @abstractmethod
  def colorTable(self):
    pass

  @property
  def segmentation(self):
    return self.segmentationNode.GetSegmentation()

  def getSegmentIDs(self):
    stringArray = vtk.vtkStringArray()
    self.segmentation.GetSegmentIDs(stringArray)
    segmentIDs = [
        stringArray.GetValue(n)
        for n in range(stringArray.GetNumberOfValues())
    ]
    return segmentIDs

  def getSegments(self):
    return [self.segmentation.GetSegment(x) for x in self.getSegmentIDs()]

  def load(self):
    stem = self.segmentationPath.name.split('.')[0]
    try:
      node = slicer.util.getNode(stem)
      logging.info(f'Segmentation found in scene: {stem}')
    except slicer.util.MRMLNodeNotFoundException:
      logging.info(f'Segmentation not found in scene: {stem}')
      node = slicer.util.loadSegmentation(str(self.segmentationPath))
    self.segmentationNode = node
    self.segmentationNode.GetDisplayNode().SetOpacity2DFill(1)

  def isValidNumber(self, number):
    return self.colorTable.isValidNumber(number)

  def getColorFromName(self, name):
    return self.colorTable.getColorFromName(name)

  def getColorFromSegment(self, segment):
    return self.getColorFromName(segment.GetName())

  def getLabelFromName(self, name):
    return self.colorTable.getLabelFromName(name)

  def getLabelFromSegment(self, segment):
    return self.getLabelFromName(segment.GetName())

  def setOriginalColors(self):
    segments = self.getSegments()
    numSegments = len(segments)
    progressDialog = slicer.util.createProgressDialog(
      value=0,
      maximum=numSegments,
      windowTitle='Setting colors...',
    )
    for i, segment in enumerate(segments):
      progressDialog.setValue(i)
      progressDialog.setLabelText(segment.GetName())
      slicer.app.processEvents()
      color = self.getColorFromSegment(segment)
      segment.SetColor(color)
      self.setSegmentOpacity(segment, 1, dimension=2)
      self.setSegmentOpacity(segment, 1, dimension=3)
    progressDialog.setValue(numSegments)
    slicer.app.processEvents()
    progressDialog.close()

  def setScoresColors(self, scoresDict, colorNode):
    segments = self.getSegments()
    numSegments = len(segments)
    progressDialog = slicer.util.createProgressDialog(
      value=0,
      maximum=numSegments,
      windowTitle='Setting colors...',
    )
    for i, segment in enumerate(segments):
      progressDialog.setValue(i)
      progressDialog.setLabelText(segment.GetName())
      slicer.app.processEvents()
      label = self.getLabelFromSegment(segment)
      scores = np.array(list(scoresDict.values()))
      scores = scores[scores > 0]  # do I want this?
      minScore = min(scores)
      maxScore = max(scores)
      color = LIGHT_GRAY
      opacity2D = 0
      opacity3D = 1
      if label in scoresDict:
        score = scoresDict[label]
        if score > 0:
          opacity2D = 1
          opacity3D = 1
          score -= minScore
          score /= maxScore
          color = self.getColorFromScore(score, colorNode)
      segment.SetColor(color)
      self.setSegmentOpacity(segment, opacity2D, dimension=2)
      self.setSegmentOpacity(segment, opacity3D, dimension=3)
    progressDialog.setValue(numSegments)
    slicer.app.processEvents()
    progressDialog.close()

  def getColorFromScore(self, normalizedScore, colorNode):
    """This method is very important"""
    numColors = colorNode.GetNumberOfColors()
    scoreIndex = int((numColors - 1) * normalizedScore)
    colorAlpha = 4 * [0]
    colorNode.GetColor(scoreIndex, colorAlpha)
    color = np.array(colorAlpha[:3])
    return color

  def setRandomColors(self):
    """For debugging purposes"""
    segments = self.getSegments()
    numSegments = len(segments)
    progressDialog = slicer.util.createProgressDialog(
        value=0,
        maximum=numSegments,
        windowTitle='Setting colors...',
    )
    for i, segment in enumerate(segments):
      progressDialog.setValue(i)
      slicer.app.processEvents()
      color = self.getRandomColor()
      segment.SetColor(color)
    progressDialog.setValue(numSegments)
    slicer.app.processEvents()
    progressDialog.close()

  def getRandomColor(self, normalized=True):
    return np.random.rand(3)

  def setSegmentOpacity(self, segment, opacity, dimension):
    displayNode = self.segmentationNode.GetDisplayNode()
    if dimension == 2:
      displayNode.SetSegmentOpacity2DFill(segment.GetName(), opacity)
      displayNode.SetSegmentOpacity2DOutline(segment.GetName(), opacity)
    elif dimension == 3:
      displayNode.SetSegmentOpacity3D(segment.GetName(), opacity)


class GIFParcellation(Parcellation):
  def __init__(self, segmentationPath, colorTablePath):
    Parcellation.__init__(self, segmentationPath)
    self.colorTablePath = colorTablePath
    self._colorTable = None

  @property
  def colorTable(self):
    return self._colorTable

  def load(self):
    super().load()
    self._colorTable = GIFColorTable(self.colorTablePath)


class ColorTable(ABC):
  def __init__(self, path):
    self.structuresDict = self.readColorTable(path)

  def getStructureNameFromLabelNumber(self, labelNumber):
    return self.structuresDict[labelNumber]['name']

  def isValidNumber(self, number):
    return number in self.structuresDict

  @staticmethod
  def readColorTable(path):
    structuresDict = {}
    with open(path) as f:
      for row in f:
        label, name, *color, _ = row.split()
        label = int(label)
        color = np.array(color, dtype=np.float) / 255
        structuresDict[label] = dict(name=name, color=color)
    return structuresDict

  def getColorFromName(self, name):
    for structureDict in self.structuresDict.values():
      if structureDict['name'] == name:
        color = structureDict['color']
        break
    else:
      raise KeyError(f'Structure {name} not found in color table')
    return color

  def getLabelFromName(self, name):
    for label, structureDict in self.structuresDict.items():
      if structureDict['name'] == name:
        result = label
        break
    else:
      raise KeyError(f'Structure {name} not found in color table')
    return result


class GIFColorTable(ColorTable):
  pass


COLORMAPS = [
  'Cividis',
  'Plasma',
  'Viridis',
  'Magma',
  'Inferno',
  'Grey',
  'Red',
  'Green',
  'Blue',
  'Yellow',
  'Cyan',
  'Magenta',
]
