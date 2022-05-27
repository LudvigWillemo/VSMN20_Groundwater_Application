# -*- coding: utf-8 -*-

"""Groundwater flow app

This program contains three classes and a main-script for launching an app off
groundwater flow. Through the use of flowmodel.py results can be ploted for
individual executions. Parameter studies are possible, with results exported
to VTK-files which can be visualized within Paraview. The app utilizes pyqt5
with the design mainly being made whithin Qt Designer.

Classes:
    SolverThread: Class to use a separate thread for execute
    Progress: Class to display window of calculation progress
    MainWindow: Class to create app

Author: Ludvig Willemo
"""

import sys
import ctypes
import os.path
from os import mkdir
import flowmodel as fm
import calfem.vis_mpl as cfv
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas

from PyQt5.uic import loadUi
from PyQt5.QtCore import QThread, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog,
                             QMessageBox, QSizeGrip, QMenu, QVBoxLayout)


class SolverThread(QThread):
    """Class to use a separate thread for execute

    Attributes:
        solver (Solver): Solver object with FEM routines
        paraStudy (bool): Flag if parameter study or not

    Methods:
        run: Executes FEM analysis
    """

    def __init__(self, solver, paramStudy=False):
        QThread.__init__(self)
        self.solver = solver
        self.paraStudy = paramStudy

    def __del__(self):
        self.wait()

    def run(self):
        """Executes FEM analysis"""

        if self.paraStudy:
            self.solver.executeParamStudy()
        else:
            self.solver.execute()


class Progress(QMainWindow):
    """Class to display window of calculation progress

    Attributes:
        ui (QWidget): Object containing all UI elements

    Methods:
        set: Sets calculation procentage and segment name
        exit: Resets UI elements and close window
    """

    def __init__(self, dir):
        QMainWindow.__init__(self)
        self.ui = loadUi(dir + "progress.ui", self)

        # Remove default window borders
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set(self, proc, seg):
        """Sets calculation procentage and segment name

        Args:
            proc (int): Calculation procentage
            seg (str): Segmentation name
        """

        # The reference ".ui" is not necessary, hence it is skiped throughout
        self.progressLabel.setText(f"{proc}%")
        string = f"{seg}\n{self.loadLabel.text()}"
        self.loadLabel.setText(string)

    def exit(self):
        """Resets UI elements and close window"""

        self.progressLabel.setText("0%")
        self.loadLabel.setText("")
        self.close()


class MainWindow(QMainWindow):
    """Class to create app

    Attributes:
        path (str): String of current model/file path
        dir (str): String of current directory name

        app (QApplication):
        pg (Progress): Object for progress window
        visualization (Visualization): Object for plotting output data
        input_data (InputData): Object containing input data
        output_data (OutputData): Object containing output data
        ui (QWidget): Object containing all UI elements
        canvas (FigureCanvasQTAgg): Canvas to draw figures on

        offset (-): Temporary variable for movement of window
        windowed (bool): Flag if app is windowed or not

    Methods:
        updateControls: Updates interface from model variables
        updateModel: Updates model variables from interface
        updateEnd: Updates end at radio button interaction
        updateName: Extracts and updates model name in UI

        onActionNew: Creates new model
        onActionOpen: Opens saved model
        onActionSave: Saves current model
        onActionSaveAs: Saves current model as new file

        onActionExecute: Executes calculations on current model
        onExecuteParamStudy: Executes parameter study
        onSolverFinished: Routines when solver is finished

        showGeo: Plots geometry
        showMesh: Plots mesh
        showPizeo: Plots pizeometric head
        showEff: Plots effective flux
        showParam: Plots maximum effective flux for parameter study
        updateCanvas: Updates canvas figure
        clearCanvas: Clears canvas of figures
        message: Tells user that no results exist

        exit: Asks before terminating program
        maximize: Maximizes or restores window

        mousePressEvent: Initiates window movement
        mouseMoveEvent: Moves window
        mouseReleaseEvent: Suspend window movement
    """

    def __init__(self):
        super(QMainWindow, self).__init__()
        # File Attributes
        self.path = ""
        self.dir = os.path.dirname(__file__) + "\\"

        # Window attributes
        self.app = app
        self.pg = Progress(self.dir)
        self.visualization = None
        self.input_data = fm.InputData()
        self.output_data = fm.OutputData()
        self.ui = loadUi(self.dir + "mainwindow.ui", self)
        self.canvas = Canvas()

        # Flag attributes
        self.offset = None
        self.windowed = True

        # Create directory for VTK exports
        vtkdir = self.dir + "\\VTK\\"
        not os.path.isdir(vtkdir) and mkdir(vtkdir)
        # Above is a truncated if statement, "arg and func" = "if arg: func".

        # Window buttons
        self.exitButton.clicked.connect(self.exit)
        self.maxiButton.clicked.connect(self.maximize)
        self.miniButton.clicked.connect(lambda: self.showMinimized())

        # Ploting buttons
        self.showGeoButton.clicked.connect(self.showGeo)
        self.showMeshButton.clicked.connect(self.showMesh)
        self.showPizeoButton.clicked.connect(self.showPizeo)
        self.showEffButton.clicked.connect(self.showEff)
        self.showParamButton.clicked.connect(self.showParam)

        # Utility buttons
        self.executeButton.clicked.connect(self.onActionExecute)
        self.clearCanvasButton.clicked.connect(self.clearCanvas)

        # Mesh size slider
        self.meshSlider.valueChanged.connect(
            lambda: self.meshLabel.setText(str(self.meshSlider.value()/10)))

        # Parameter study interface
        self.dRadio.toggled.connect(self.updateEnd)
        self.paraButton.clicked.connect(self.onExecuteParamStudy)

        # Visualization canvas
        self.canvas.figure.set_facecolor("#F1FAEE")
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.figureFrame.setLayout(self.layout)

        # Sizegrip to resize window, southwest corner
        self.sizegrip = QSizeGrip(self.cornerFrame)
        self.sizegrip.setToolTip("Grip to move")

        # Remove default window borders
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set program (taskbar) icon, gives Windows an unique application ID
        self.setWindowIcon(QIcon(self.dir + r"Assets\icon.png"))
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GWapp")

        # Menubar menus
        stylesheet = """
        QMenu {
            color: rgb(241, 250, 238);
            background-color: rgb(15, 27, 44);
            border: 5px solid rgb(15, 27, 44);
        }
        QMenu::item:selected {
            background-color: rgb(29, 53, 87);
        }"""

        # File menu
        file = QMenu()
        file.setStyleSheet(stylesheet)
        file.addAction(QIcon(self.dir + r"Assets\page.png"), "New",
                       self.onActionNew, QKeySequence(Qt.CTRL + Qt.Key_N))
        file.addAction(QIcon(self.dir + r"Assets\open.png"), "Open",
                       self.onActionOpen, QKeySequence(Qt.CTRL + Qt.Key_O))
        file.addSeparator()
        file.addAction(QIcon(self.dir + r"Assets\save.png"), "Save",
                       self.onActionSave, QKeySequence(Qt.CTRL + Qt.Key_S))
        file.addAction(QIcon(self.dir + r"Assets\saveas.png"), "SaveAs",
                       self.onActionSaveAs, QKeySequence(Qt.CTRL + Qt.ALT +
                       Qt.Key_S))
        file.addSeparator()
        file.addAction(QIcon(self.dir + r"Assets\cross.png"), "Exit",
                       self.exit, QKeySequence(Qt.CTRL + Qt.Key_E))
        self.fileButton.setMenu(file)

        # Utility menu
        util = QMenu()
        util.setStyleSheet(stylesheet)
        util.addAction(QIcon(self.dir + r"Assets\play.png"), "Execute",
                       self.onActionExecute, QKeySequence(Qt.CTRL +
                       Qt.Key_Return))
        util.addAction(QIcon(self.dir + r"Assets\para.png"),
                       "Parameter study", self.onExecuteParamStudy,
                       QKeySequence(Qt.CTRL + Qt.ALT + Qt.Key_Return))
        util.addSeparator()
        util.addAction(QIcon(self.dir + r"Assets\clear.png"),
                       "Clear Canvas", self.clearCanvas,
                       QKeySequence(Qt.CTRL + Qt.Key_C))
        self.utilButton.setMenu(util)

        self.show()
        self.raise_()

    """ I/O Methods """
    def updateControls(self):
        """Updates interface from model variables"""

        self.wEdit.setText(str(self.input_data.w))
        self.hEdit.setText(str(self.input_data.h))
        self.dEdit.setText(str(self.input_data.d))
        self.tEdit.setText(str(self.input_data.t))
        self.pEdit.setText(str(self.input_data.p))
        self.kxEdit.setText(str(self.input_data.kx))
        self.kyEdit.setText(str(self.input_data.ky))
        self.meshLabel.setText(str(self.input_data.el_size_factor))
        self.meshSlider.setValue(int(self.input_data.el_size_factor*10))

        self.stepEdit.setText(str(self.input_data.steps))
        if self.input_data.dStudy:
            self.dRadio.setChecked(True)
            self.endEdit.setText(str(self.input_data.dEnd))
        else:
            self.tRadio.setChecked(True)
            self.endEdit.setText(str(self.input_data.tEnd))

    def updateModel(self):
        """Updates model variables from interface"""

        try:
            self.input_data.w = float(self.wEdit.text())
            self.input_data.h = float(self.hEdit.text())
            self.input_data.d = float(self.dEdit.text())
            self.input_data.t = float(self.tEdit.text())
            self.input_data.p = float(self.pEdit.text())
            self.input_data.kx = float(self.kxEdit.text())
            self.input_data.ky = float(self.kyEdit.text())
            self.input_data.el_size_factor = float(self.meshSlider.value()/10)

            self.input_data.dStudy = self.dRadio.isChecked()
            self.input_data.steps = int(self.stepEdit.text())
            if self.input_data.dStudy:
                self.input_data.dEnd = float(self.endEdit.text())
            else:
                self.input_data.tEnd = float(self.endEdit.text())
        except Exception:
            QMessageBox.information(self, "Message", "Model could not be "
                                    "updated, \ninput should be a float.")

    def updateEnd(self):
        """Updates end at radio button interaction"""

        if self.dRadio.isChecked():
            self.input_data.tEnd = float(self.endEdit.text())
            self.endEdit.setText(str(self.input_data.dEnd))
        else:
            self.input_data.dEnd = float(self.endEdit.text())
            self.endEdit.setText(str(self.input_data.tEnd))

    def updateName(self):
        """Extracts and updates model name in UI"""

        name = os.path.basename(self.path).replace(".json", "")
        self.nameLabel.setText(name)

    def onActionNew(self):
        """Creates new model"""

        self.path = ""
        self.visualization = None
        self.reportPlainEdit.setPlainText("")
        self.input_data = fm.InputData()
        self.output_data = fm.OutputData()
        self.updateControls()
        self.updateName()

    def onActionOpen(self):
        """Opens saved model"""

        temp_path, _ = QFileDialog.getOpenFileName(
                           self.ui, "Open model", self.dir, "Model (*.json)")
        if temp_path != "":
            if self.input_data.load(temp_path):
                self.path = temp_path
                self.updateControls()
                self.updateName()
                self.clearCanvas()
                self.visualization = None
                self.reportPlainEdit.setPlainText("")
            else:
                QMessageBox.information(
                    self, "Message", f"The file {os.path.basename(temp_path)} "
                    "could not be read or was from\na different version than "
                    f"the current version: {self.input_data.version}.")

    def onActionSave(self):
        """Saves current model"""

        self.updateModel()
        temp_path = self.path
        if temp_path == "":
            temp_path, _ = QFileDialog.getSaveFileName(
                             self.ui, "Save model", self.dir, "Model (*.json)")
        if temp_path != "":
            if self.input_data.save(temp_path):
                self.path = temp_path
                self.updateName()
            else:
                QMessageBox.information(
                    self, "Message", f"The file {os.path.basename(temp_path)} "
                    "could not be saved.")

    def onActionSaveAs(self):
        """Saves current model as new file"""

        self.updateModel()
        temp_path, _ = QFileDialog.getSaveFileName(
                          self.ui, "Save model", self.dir, "Model (*.json)")
        if temp_path != "":
            if self.input_data.save(temp_path):
                self.path = temp_path
                self.updateName()
            else:
                QMessageBox.information(
                    self, "Message", f"The file {os.path.basename(temp_path)} "
                    "could not be saved.")

    """ Utility methods """
    def onActionExecute(self):
        """Executes calculations on current model"""

        self.updateModel()
        if self.input_data.validModel():
            self.pg.show()
            self.clearCanvas()
            self.setEnabled(False)
            self.solver = fm.Solver(self.input_data, self.output_data, self.pg)
            self.solverThread = SolverThread(self.solver)
            self.solverThread.finished.connect(self.onSolverFinished)
            self.solverThread.start()
        else:
            QMessageBox.information(
                self, "Message", "Invalid model inputs. All inputs shall be "
                "larger than zero,\nthe geometry also requires that w>t and "
                "h>d.")

    def onExecuteParamStudy(self):
        """Executes parameter study"""

        self.updateModel()
        if self.input_data.validModel() and self.input_data.validParam():
            self.pg.show()
            self.clearCanvas()
            self.setEnabled(False)
            basepath = (self.dir + "VTK\\"
                        + os.path.basename(self.path).replace(".json", ""))
            self.solver = fm.Solver(self.input_data, self.output_data,
                                    self.pg, basepath)
            self.solverThread = SolverThread(self.solver, True)
            self.solverThread.finished.connect(self.onSolverFinished)
            self.solverThread.start()
        elif self.input_data.validModel():
            QMessageBox.information(
                self, "Message", "Invalid model inputs. All inputs shall be "
                "larger than zero, \nthe geometry also requires that w>t and "
                "h>d.")
        else:
            QMessageBox.information(
                self, "Message", "Invalid parameter-study inputs. All inputs "
                "should be larger than \nzero, the geometry also requires that"
                " w > tEnd > t and h > dEnd > d")

    def onSolverFinished(self):
        """Routines when solver is finished"""

        self.visualization = fm.Visualization(
                                self.input_data, self.output_data)
        if self.solverThread.paraStudy:
            self.reportPlainEdit.setPlainText("")
        else:
            txt = str(fm.Report(self.input_data, self.output_data))
            self.reportPlainEdit.setPlainText(txt)
            
        self.tabWidget.setCurrentIndex(0)
        self.setEnabled(True)
        self.pg.exit()

    """ Ploting Methods """
    def showGeo(self):
        """Plots geometry"""

        if self.visualization is not None:
            self.updateCanvas(self.visualization.showGeometry(False))
        else:
            self.message()

    def showMesh(self):
        """Plots mesh"""

        if self.visualization is not None:
            self.updateCanvas(self.visualization.showMesh(False))
        else:
            self.message()

    def showPizeo(self):
        """Plots pizeometric head"""

        if self.visualization is not None:
            self.updateCanvas(self.visualization.showPiezo(False))
        else:
            self.message()

    def showEff(self):
        """Plots effective flux"""

        if self.visualization is not None:
            self.updateCanvas(self.visualization.showEff(False))
        else:
            self.message()

    def showParam(self):
        """Plots maximum effective flow for parameter study"""

        if self.output_data.max_flux is not None:
            self.updateCanvas(self.visualization.showParam(False))
        else:
            QMessageBox.information(
                self, "Message", "No parameter study has been calculated.")

    def updateCanvas(self, canvas):
        """Updates canvas with new figure"""

        self.tabWidget.setCurrentIndex(1)
        self.visualization.closeAll()
        self.layout.replaceWidget(self.canvas, canvas)
        self.canvas = canvas
        self.canvas.figure.set_facecolor("#F1FAEE")
        self.canvas.draw()

    def clearCanvas(self):
        """Clears canvas of figures"""

        cfv.plt.close()
        canvas = Canvas()
        canvas.figure.set_facecolor("#F1FAEE")
        self.layout.replaceWidget(self.canvas, canvas)
        self.canvas = canvas

    def message(self):
        """Tells user that no results exist"""

        QMessageBox.information(
            self, "Message", "No results has been calculated.")

    """ UI Methods """
    def exit(self):
        """Asks before terminating program"""

        q = QMessageBox.question(
                self, "Exit", "Are you sure you want to exit the program?",
                QMessageBox.Yes | QMessageBox.No)
        if q == QMessageBox.Yes:
            self.app.exit()
            self.close()

    def maximize(self):
        """Maximizes or restores window"""

        if self.windowed:
            self.showMaximized()
            self.windowed = False
            self.maxiButton.setToolTip("Restore")
            self.maxiButton.setIcon(QIcon(self.dir + r"Assets\store.png"))
        else:
            self.showNormal()
            self.windowed = True
            self.maxiButton.setToolTip("Maximize")
            self.maxiButton.setIcon(QIcon(self.dir + r"Assets\maxi.png"))

    """ Window Movement """
    def mousePressEvent(self, event):
        """Initiates window movement"""

        if event.button() == Qt.LeftButton:  # If (leftbutton clicked)
            self.offset = event.pos()        # Store initial position

    def mouseMoveEvent(self, event):
        """Moves window"""

        # If (leftbutton held, windowed, offset exist)
        if (event.buttons() == Qt.LeftButton and
                self.windowed and self.offset is not None):
            self.move(self.pos() + event.pos() - self.offset)
            # Move relative offset

    def mouseReleaseEvent(self, event):
        """Suspend window movement"""

        self.offset = None  # On release, reset offset which prevents movement


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    widget.updateControls()
    sys.exit(app.exec_())
