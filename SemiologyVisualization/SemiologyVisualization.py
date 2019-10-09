import csv
from pathlib import Path

import numpy as np
import SimpleITK as sitk

import vtk, qt, ctk, slicer
import sitkUtils as su
from slicer.ScriptedLoadableModule import *

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

class SemiologyVisualizationWidget(ScriptedLoadableModuleWidget):

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.makeGUI()

  def makeGUI(self):
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    self.referencePathEdit = ctk.ctkPathLineEdit()
    # parametersFormLayout.addRow(
    #   "Path to reference T1 MRI: ", self.referencePathEdit)

    self.parcellationPathEdit = ctk.ctkPathLineEdit()
    # parametersFormLayout.addRow(
    #   "Path to GIF parcellation: ", self.parcellationPathEdit)

    self.scoresPathEdit = ctk.ctkPathLineEdit()
    self.scoresPathEdit.nameFilters = ['*.csv']
    parametersFormLayout.addRow(
      "Path to semiology scores: ", self.scoresPathEdit)

    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.parcellationPathEdit.currentPathChanged.connect(self.onSelect)
    self.referencePathEdit.currentPathChanged.connect(self.onSelect)
    self.scoresPathEdit.currentPathChanged.connect(self.onSelect)
    self.applyButton.clicked.connect(self.onApplyButton)

    # Add vertical spacer
    self.layout.addStretch(1)

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

  def onApplyButton(self):
    # self.parcellationPathEdit.addCurrentPathToHistory()
    # self.referencePathEdit.addCurrentPathToHistory()
    self.scoresPathEdit.addCurrentPathToHistory()

    logic = SemiologyVisualizationLogic()
    self.referenceVolumeNode = slicer.util.loadVolume(
      str(logic.getDefaultReferencePath()))
    self.parcellationVolumeNode = logic.loadParcellation(
      logic.getDefaultParcellationPath())
    # self.referenceVolumeNode = slicer.util.loadVolume(
    #   self.referencePathEdit.currentPath)
    # self.parcellationVolumeNode = logic.loadParcellation(
    #   self.parcellationPathEdit.currentPath)
    # self.parcellationSegmentationNode = logic.labelMapToSegmentation(
    #   self.parcellationVolumeNode)
    self.scoresNode = logic.getScoresVolumeNode(
      self.scoresPathEdit.currentPath,
      self.parcellationVolumeNode,
    )
    slicer.util.setSliceViewerLayers(
      foreground=self.scoresNode,
      foregroundOpacity=1,
      labelOpacity=0,
    )
    self.scoresNode.GetDisplayNode().SetInterpolate(False)


#
# SemiologyVisualizationLogic
#

class SemiologyVisualizationLogic(ScriptedLoadableModuleLogic):

  def loadParcellation(self, imagePath, gifVersion=None):
    volumeNode = slicer.util.loadLabelVolume(str(imagePath))
    colorNode = self.getGifColorNode(version=gifVersion)
    displayNode = volumeNode.GetDisplayNode()
    displayNode.SetAndObserveColorNodeID(colorNode.GetID())
    return volumeNode

  def labelMapToSegmentation(self, labelMapNode):
    pass

  def getGifColorNode(self, version=None):
    version = 3 if version is None else version
    colorDir = self.getResourcesDir() / 'Color'
    filename = f'BrainAnatomyLabelsV{version}_0.txt'
    colorPath = colorDir / filename
    colorNodeName = colorPath.stem
    className = 'vtkMRMLColorTableNode'
    colorNode = slicer.util.getFirstNodeByClassByName(className, colorNodeName)
    if colorNode is None:
      colorNode = slicer.util.loadColorTable(str(colorPath))
    return colorNode

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

  def getScoresVolumeNode(self, scoresPath, parcellationLabelMapNode):
    parcellationImage = su.PullVolumeFromSlicer(parcellationLabelMapNode)
    parcellationArray = sitk.GetArrayViewFromImage(parcellationImage)
    scoresArray = np.zeros_like(parcellationArray)

    with open(scoresPath) as csvfile:
      reader = csv.reader(csvfile)
      next(reader)  # assume there is a header row
      for (label, score) in reader:
        label = int(label)
        score = float(score)
        labelMask = parcellationArray == label
        scoresArray[labelMask] = score
    scoresImage = self.getImageFromArray(scoresArray, parcellationImage)
    scoresName = f'Scores {Path(scoresPath).stem}'
    scoresVolumeNode = su.PushVolumeToSlicer(scoresImage, name=scoresName)
    displayNode = scoresVolumeNode.GetDisplayNode()
    colorNode = slicer.util.getFirstNodeByClassByName(
      'vtkMRMLColorTableNode',
      'Plasma',
    )
    displayNode.SetAutoThreshold(False)
    displayNode.SetAndObserveColorNodeID(colorNode.GetID())
    displayNode.SetLowerThreshold(1)
    displayNode.ApplyThresholdOn()
    displayNode.SetAutoWindowLevel(False)
    displayNode.SetWindowLevelMinMax(0, 100)
    return scoresVolumeNode

  def getImageFromArray(self, array, referenceImage):
    image = sitk.GetImageFromArray(array)
    image.SetDirection(referenceImage.GetDirection())
    image.SetOrigin(referenceImage.GetOrigin())
    image.SetSpacing(referenceImage.GetSpacing())
    return image


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
