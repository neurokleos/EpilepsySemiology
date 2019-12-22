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
    self.semiologiesDict = self.logic.getSemiologiesDict(semiologies)
    self.parcellation = GIFParcellation(
      segmentationPath=self.logic.getGifSegmentationPath(),
      colorTablePath=self.logic.getGifTablePath(),
    )
    self.makeGUI()
    slicer.semiologyVisualization = self

  def makeGUI(self):
    self.makeDominantHemisphereButton()
    self.makeEzHemisphereButton()
    self.makeColorsButton()
    self.makeSemiologiesButton()
    self.makeLoadDataButton()
    self.makeApplyButton()

    # Add vertical spacer
    self.layout.addStretch(1)

  def makeDominantHemisphereButton(self):
    dominantHemisphereGroupButton = qt.QGroupBox('Dominant hemisphere')
    self.leftDominantRadioButton = qt.QRadioButton('Left')
    self.leftDominantRadioButton.setChecked(True)
    self.rightDominantRadioButton = qt.QRadioButton('Right')
    dominantHemisphereLayout = qt.QHBoxLayout(dominantHemisphereGroupButton)
    dominantHemisphereLayout.addWidget(self.leftDominantRadioButton)
    dominantHemisphereLayout.addWidget(self.rightDominantRadioButton)
    self.layout.addWidget(dominantHemisphereGroupButton)

  def makeEzHemisphereButton(self):
    ezHemisphereGroupButton = qt.QGroupBox('Epileptogenic zone')
    self.leftEzRadioButton = qt.QRadioButton('Left')
    self.leftEzRadioButton.setChecked(True)
    self.rightEzRadioButton = qt.QRadioButton('Right')
    ezHemisphereLayout = qt.QHBoxLayout(ezHemisphereGroupButton)
    ezHemisphereLayout.addWidget(self.leftEzRadioButton)
    ezHemisphereLayout.addWidget(self.rightEzRadioButton)
    self.layout.addWidget(ezHemisphereGroupButton)

  def makeColorsButton(self):
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
    self.layout.addWidget(self.colorSelector)

  def makeSemiologiesButton(self):
    semiologiesCollapsibleButton = ctk.ctkCollapsibleButton()
    semiologiesCollapsibleButton.text = 'Semiologies'
    self.layout.addWidget(semiologiesCollapsibleButton)

    semiologiesFormLayout = qt.QFormLayout(semiologiesCollapsibleButton)
    semiologiesFormLayout.addWidget(self.getSemiologiesWidget())

  def makeLoadDataButton(self):
    self.loadDataButton = qt.QPushButton('Load data')
    self.loadDataButton.clicked.connect(self.onLoadDataButton)
    self.layout.addWidget(self.loadDataButton)

  def makeApplyButton(self):
    self.applyButton = qt.QPushButton('Apply')
    self.applyButton.enabled = False
    self.applyButton.clicked.connect(self.onApplyButton)
    self.layout.addWidget(self.applyButton)

  def getSemiologiesWidget(self):
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

  def updateColors(self):
    self.parcellation.setRandomColors()

    # if self.useGifColors:
    #   parcellation.setOriginalColors()
    # else:
    #   scores = self.getScores()
    #   parcellation.setScoresColors(scores)

  # Slots
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
    self.referenceVolumeNode = slicer.util.loadVolume(
      str(logic.getDefaultReferencePath()))
    self.parcellationLabelMapNode = logic.loadParcellation(
      logic.getDefaultParcellationPath())
    slicer.util.setSliceViewerLayers(
      label=None,
    )
    self.parcellation.load()
    self.applyButton.enabled = True

  def onApplyButton(self):
    colorNode = slicer.util.getFirstNodeByClassByName(
      'vtkMRMLColorTableNode',
      'Cividis',
    )
    scoresDict = self.logic.getTestScores()
    self.scoresVolumeNode = self.logic.getScoresVolumeNode(
      scoresDict, colorNode, self.parcellationLabelMapNode)
    self.parcellation.setScoresColors(scoresDict, colorNode)
    # # self.parcellationPathEdit.addCurrentPathToHistory()
    # # self.referencePathEdit.addCurrentPathToHistory()
    # self.scoresPathEdit.addCurrentPathToHistory()

    # logic = SemiologyVisualizationLogic()
    # self.referenceVolumeNode = slicer.util.loadVolume(
    #   str(logic.getDefaultReferencePath()))
    # self.parcellationVolumeNode = logic.loadParcellation(
    #   logic.getDefaultParcellationPath())
    # # self.referenceVolumeNode = slicer.util.loadVolume(
    # #   self.referencePathEdit.currentPath)
    # # self.parcellationVolumeNode = logic.loadParcellation(
    # #   self.parcellationPathEdit.currentPath)
    # # self.parcellationSegmentationNode = logic.labelMapToSegmentation(
    # #   self.parcellationVolumeNode)
    # self.scoresNode = logic.getScoresVolumeNode(
    #   self.scoresPathEdit.currentPath,
    #   self.parcellationVolumeNode,
    # )
    slicer.util.setSliceViewerLayers(
      foreground=self.scoresVolumeNode,
      foregroundOpacity=0,
      labelOpacity=0,
    )
    self.scoresVolumeNode.GetDisplayNode().SetInterpolate(False)


#
# SemiologyVisualizationLogic
#

class SemiologyVisualizationLogic(ScriptedLoadableModuleLogic):

  def getSemiologiesDict(self, semiologies):
    semiologiesDict = {}
    for semiology in semiologies:
      semiologiesDict[semiology] = dict(
        leftCheckBox=qt.QCheckBox(),
        rightCheckBox=qt.QCheckBox(),
      )
    return semiologiesDict

  def loadParcellation(self, imagePath, gifVersion=None):
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
      color = BLACK
      opacity = 0
      if label in scoresDict:
        score = scoresDict[label]
        if score > 0:
          opacity = 1
          score -= minScore
          score /= maxScore
          color = self.getColorFromScore(score, colorNode)
      segment.SetColor(color)
      self.setSegmentOpacity(segment, opacity, dimension=2)
      self.setSegmentOpacity(segment, opacity, dimension=3)
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
