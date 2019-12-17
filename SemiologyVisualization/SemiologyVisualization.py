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


import string
semiologies = [f'Semiology {x}' for x in string.ascii_uppercase]


class SemiologyVisualizationWidget(ScriptedLoadableModuleWidget):

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.semiologiesDict = self.getSemiologiesDict(semiologies)
    self.makeGUI()

  def makeGUI(self):
    dominantSideGroupButton = qt.QGroupBox('Dominant side')
    self.leftDominantRadioButton = qt.QRadioButton('Left')
    self.leftDominantRadioButton.setChecked(True)
    self.rightDominantRadioButton = qt.QRadioButton('Right')
    dominantSideLayout = qt.QHBoxLayout(dominantSideGroupButton)
    dominantSideLayout.addWidget(self.leftDominantRadioButton)
    dominantSideLayout.addWidget(self.rightDominantRadioButton)
    self.layout.addWidget(dominantSideGroupButton)

    ezSideGroupButton = qt.QGroupBox('Epileptogenic zone side')
    self.leftEzRadioButton = qt.QRadioButton('Left')
    self.leftEzRadioButton.setChecked(True)
    self.rightEzRadioButton = qt.QRadioButton('Right')
    ezSideLayout = qt.QHBoxLayout(ezSideGroupButton)
    ezSideLayout.addWidget(self.leftEzRadioButton)
    ezSideLayout.addWidget(self.rightEzRadioButton)
    self.layout.addWidget(ezSideGroupButton)

    semiologiesCollapsibleButton = ctk.ctkCollapsibleButton()
    semiologiesCollapsibleButton.text = 'Semiologies'
    self.layout.addWidget(semiologiesCollapsibleButton)

    semiologiesFormLayout = qt.QFormLayout(semiologiesCollapsibleButton)

    self.referencePathEdit = ctk.ctkPathLineEdit()
    # semiologiesFormLayout.addRow(
    #   "Path to reference T1 MRI: ", self.referencePathEdit)

    self.parcellationPathEdit = ctk.ctkPathLineEdit()
    # semiologiesFormLayout.addRow(
    #   "Path to GIF parcellation: ", self.parcellationPathEdit)

    self.scoresPathEdit = ctk.ctkPathLineEdit()
    self.scoresPathEdit.nameFilters = ['*.csv']
    semiologiesFormLayout.addRow(
      "Path to semiology scores: ", self.scoresPathEdit)

    # semiologiesFormLayout.addWidget(self.getSemiologiesWidget())

    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    semiologiesFormLayout.addRow(self.applyButton)

    # connections
    self.parcellationPathEdit.currentPathChanged.connect(self.onSelect)
    self.referencePathEdit.currentPathChanged.connect(self.onSelect)
    self.scoresPathEdit.currentPathChanged.connect(self.onSelect)
    self.applyButton.clicked.connect(self.onApplyButton)

    # Add vertical spacer
    self.layout.addStretch(1)

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

  def getSemiologiesDict(self, semiologies):
    semiologiesDict = {}
    for semiology in semiologies:
      semiologiesDict[semiology] = dict(
        leftCheckBox=qt.QCheckBox(),
        rightCheckBox=qt.QCheckBox(),
      )
    return semiologiesDict

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


LOREN_IPSUM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse magna purus, accumsan non laoreet id, commodo eget ligula. Vestibulum eros sem, congue non elit at, ornare vestibulum odio. Duis dapibus egestas ultricies. Morbi dignissim sapien a ipsum volutpat, a rhoncus ante finibus. Phasellus consequat et neque at dignissim. Nullam hendrerit elementum accumsan. Phasellus nec lectus id eros rutrum feugiat et eget elit. Curabitur luctus enim a consectetur pharetra. Donec convallis orci arcu, eget tempor orci faucibus non. Curabitur semper congue mattis.

Morbi facilisis eleifend enim quis dignissim. Interdum et malesuada fames ac ante ipsum primis in faucibus. In eget magna a quam gravida tincidunt. Sed convallis eget purus quis blandit. Integer et nisi ante. Sed ultrices est in neque tempus, eu tristique turpis ullamcorper. Pellentesque pharetra turpis vel mattis vestibulum.

In finibus, mauris vitae condimentum blandit, urna tortor blandit libero, ac molestie risus velit ac neque. Aliquam ornare sagittis ligula cursus tempus. Maecenas suscipit vulputate imperdiet. Ut blandit placerat porttitor. In maximus, ante quis tempus pretium, sapien neque vehicula diam, semper volutpat dui nisl gravida nunc. Quisque sagittis sit amet massa ut dictum. Quisque dignissim, orci id facilisis fermentum, tortor elit hendrerit lectus, et dictum ante magna non ligula. Fusce vitae pretium augue, porta semper ante. Maecenas porta, purus eu lobortis cursus, enim enim mollis sem, non tempus velit arcu quis augue. Etiam eu leo ipsum.

Aenean lorem dolor, congue quis iaculis vel, facilisis a nunc. Mauris accumsan sapien ut sem fermentum ultrices. Praesent volutpat mauris non erat fringilla, accumsan consequat justo rhoncus. Phasellus eu sollicitudin turpis. Curabitur sit amet rutrum purus. Proin ac velit massa. Fusce blandit turpis vel mi commodo, nec posuere lacus accumsan. Nunc est augue, imperdiet nec bibendum at, pulvinar at sapien. Curabitur ac nibh urna. Ut vitae magna mauris.

Praesent a vestibulum enim, a dignissim dui. In porttitor faucibus orci, sit amet euismod metus gravida ac. Nullam at ante purus. Morbi sed nibh ipsum. Integer imperdiet aliquet est. Fusce eu volutpat purus. Integer ac bibendum mauris, ac porta leo. Nam condimentum venenatis ligula quis iaculis. Donec risus leo, euismod in tincidunt nec, cursus sagittis massa. Pellentesque at mauris ipsum. Etiam luctus at sem at condimentum. Vivamus vestibulum dolor sit amet pretium aliquet.
"""
