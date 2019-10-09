cmake_minimum_required(VERSION 3.13.4)

project(EpilepsySemiology)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/EpilepsySemiology")
set(EXTENSION_CATEGORY "Visualization")
set(EXTENSION_CONTRIBUTORS "Fernando Perez-Garcia (University College London)")
set(EXTENSION_DESCRIPTION "This is an example of a simple extension")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/EpilepsySemiology.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/EpilepsySemiology/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SemiologyVisualization)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
