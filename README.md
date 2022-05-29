# Groundwater flow Application
This is the final hand in of the course Software Development for Technical Applications VSMN20 at Lund University. Its aim is to produce an interactive finite element program which will be iteratively developed within python. The purpose of this Readme-file is to give guidance of the structure of the program and the files contained within the project. 

## Documentation
The documentation is available at: https://ludvigwillemo.github.io/

The code will be available at: https://github.com/LudvigWillemo/VSMN20_Groundwater_Application

## Directory
This directory contains a number of files, the content is outlined in the following list
- **Assets:** Folder containing UI assets such as icons.
- **Data:** Folder containing data files
  - **data_v4.json:** Outdated data from version 4, won't load
  - **data.json:** Example data that can be loaded
- **Examples:** Folder containing parameterstudy with paraview animation
  - **example.text:** Parameters for the two studies
  - **example_dFlux.mp4:** Animation of flux for study of d
  - **example_dPizeo.mp4:** Animation of pizeometric head for study of d
  - **example_tFlux.mp4:** Animation of flux for study of t
  - **example_tPizeo.mp4:** Animation of pizeometric head for study of t
- **MkDocs:** Folder containing documentation
- **flowmodel.py:** Flow model module in python
- **GWapp.py:** App executable using the flowmodel.py
- **segmenttimer.py:** Stopwatch module to time code
- **modern.ui:** Main application pyqt ui file
- **progress.ui:** Progressbar pyqt ui file
