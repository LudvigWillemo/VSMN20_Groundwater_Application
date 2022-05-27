# -*- coding: utf-8 -*-

"""Groundwater Flow Model

This module contains a collection of five classes with combined functionality
to construct a program for finite element analysis of groundwater flow.
"""

import json
import numpy as np
import pyvtk as vtk
import tabulate as tbl

import calfem.core as cfc
import calfem.mesh as cfm
import calfem.utils as cfu
import calfem.vis_mpl as cfv
import calfem.geometry as cfg


class InputData(object):
    """Class to define geometry and manage indata for the model

    Attributes:
        version (int): Version corresponding to worksheet number
        w (float): Width of ground
        h (float): Height of ground
        d (float): Depth of dividing wall (initial if parameter study)
        t (float): Thickness of dividing wall (initial if parameter study)
        p (float): Pressure head on left side of dividing wall
        kx (float): Permeability coefficient in x-direction
        ky (float): Permeability coefficient in y-direction
        ep (list): Element thickness (calfem)
        el_size_factor (float): Maximal element size

        dStudy (bool): Flag if d is studied, otherwise t
        dEnd (float): End depth in study of d
        tEnd (float): End thickness in study of t
        steps (int): Amount of steps of parameter study
    """

    def __init__(self):
        # Standard model
        self.version = 7
        self.w = 50.
        self.h = 10.
        self.d = 2.
        self.t = 1.
        self.p = 10.
        self.kx = 20.0
        self.ky = 20.0
        self.ep = [1.0]
        self.el_size_factor = 1

        # Parameter study
        self.dStudy = True
        self.dEnd = 8.
        self.tEnd = 10.
        self.steps = 10

    def save(self, path):
        """Saves indata to a .json file

        Args:
            path (str): Path (dir + name) to write to

        Returns:
            bool: True for success, False otherwise.
        """

        input_data = {}

        input_data["version"] = self.version
        input_data["w"] = self.w
        input_data["h"] = self.h
        input_data["d"] = self.d
        input_data["t"] = self.t
        input_data["p"] = self.p
        input_data["kx"] = self.kx
        input_data["ky"] = self.ky
        input_data["ep"] = self.ep
        input_data["el_size_factor"] = self.el_size_factor

        input_data["dStudy"] = self.dStudy
        input_data["dEnd"] = self.dEnd
        input_data["tEnd"] = self.tEnd
        input_data["steps"] = self.steps

        try:
            with open(path, "w") as ofile:
                json.dump(input_data, ofile, sort_keys=True, indent=4)
            return True
        except Exception:
            print(f"The file {path} could not be written.")
            return False

    def load(self, path):
        """Reads indata from a .json file

        Args:
            path (str): Path to read from

        Returns:
            bool: True for success, False otherwise.
        """

        try:
            with open(path, "r") as ifile:
                input_data = json.load(ifile)
        except Exception:
            print(f"The file {path} could not be found or read.")
            return False

        if input_data["version"] != self.version:
            print(f"The file {path} is from different version, "
                  "loading was canceled.")
            return False

        self.w = input_data["w"]
        self.h = input_data["h"]
        self.d = input_data["d"]
        self.t = input_data["t"]
        self.p = input_data["p"]
        self.kx = input_data["kx"]
        self.ky = input_data["ky"]
        self.ep = input_data["ep"]
        self.el_size_factor = input_data["el_size_factor"]

        self.dStudy = input_data["dStudy"]
        self.dEnd = input_data["dEnd"]
        self.tEnd = input_data["tEnd"]
        self.steps = input_data["steps"]

        return True

    def geometry(self):
        """Defines problem geometry

        Returns:
            Geometry: Object containing geometric data
        """

        g = cfg.Geometry()

        w = self.w
        h = self.h
        t = self.t
        d = self.d

        # Points
        g.point([0., 0.])           # 0
        g.point([w, 0.])            # 1
        g.point([w, h])             # 2
        g.point([(w+t)/2., h])      # 3
        g.point([(w+t)/2., h-d])    # 4
        g.point([(w-t)/2., h-d])    # 5
        g.point([(w-t)/2., h])      # 6
        g.point([0., h])            # 7

        # Lines
        g.spline([0, 1])                # 0
        g.spline([1, 2])                # 1
        g.spline([2, 3], marker=20)     # 2 Open side
        g.spline([3, 4])                # 3
        g.spline([4, 5])                # 4
        g.spline([5, 6])                # 5
        g.spline([6, 7], marker=30)     # 6 Dam side
        g.spline([7, 0])                # 7

        g.surface([0, 1, 2, 3, 4, 5, 6, 7])

        return g

    def validModel(self):
        """Verifies valid model parameters

        A model is Valid if {w,h,d,t,p,kx,ky} > 0, w > t and h > d.

        Returns:
            bool: True if valid, false otherwise.
        """

        notneg = [self.w, self.h, self.d, self.t, self.p, self.kx, self.ky]
        if self.w > self.t and self.h > self.d and all(i > 0 for i in notneg):
            return True
        return False

    def validParam(self):
        """Verifies valid parameter study parameters

        A parameter study is valid if
            h > d_end > d for a study of d
            w > t_end > t for a study of t

        Returns:
            bool: True if valid, false otherwise.
        """

        if self.dStudy and self.h > self.dEnd > self.d:
            return True
        elif self.w > self.tEnd > self.t:
            return True
        return False


class OutputData(object):
    """Class to store the results from the calculation

    Attributes:
        geometry (Geometry): Geometric data object
        el_type (int): Element type (3-triangle)
        dof_per_node (int): Degrees of freedom per node
        coords (array): Global coordinate matrix
        edof (array): Element topology matrix
        dofs (array): Degrees of freedom matrix

        a (array): Nodal piezometric head
        r (array): Nodal reaction flux
        ed (array): Elemental piezometric head
        qs (array): Elemental volume flux
        qt (array): Elemental hydraulic gradient
        eff_flux (array): Elemental effective flux

        range (array): Range of parameter study
        max_flux (array): Maximum effective flux of parameter study
    """

    def __init__(self):
        # Geometry and FEM
        self.geometry = None
        self.el_type = None
        self.dof_per_node = None
        self.coords = None
        self.edof = None
        self.dofs = None

        # Results
        self.a = None
        self.r = None
        self.ed = None
        self.qs = None
        self.qt = None
        self.eff_flux = None

        # Parameter study
        self.range = None
        self.max_flux = None


class Solver(object):
    """Class to handle in-/outdata with FEM solver

    Attributes:
        input_data (InputData): Object containing input data
        output_data (OutputData): Object containing output data
        basepath (str): Optional path for export to VTK
        pg (Progress): Optional progress-object to inform user of calculations
    """

    def __init__(self, input_data, output_data, pg=False, basepath=""):
        self.input_data = input_data
        self.output_data = output_data
        self.pg = pg
        self.basepath = basepath

    def execute(self):
        """Executes FEM solver routine for groundwater flow"""

        print("Solver is being executed...")
        self.pg and self.pg.set(1, "Staring solver...")
        # Above is a truncated if statement, "arg and func" = "if arg: func".
        # If pg is specified in the constructor it returns True, since all not
        # empty/zero objects return True in python.

        # Transfer input data to local references
        print("Importing data...")
        self.pg and self.pg.set(1, "Importing data...")  # Truncated "if"

        ep = self.input_data.ep
        p = self.input_data.p
        kx = self.input_data.kx
        ky = self.input_data.ky
        geometry = self.input_data.geometry()

        # Mesh generation
        print("Generating mesh...")
        self.pg and self.pg.set(3, "Generating mesh...")

        el_type = 2
        dof_per_node = 1

        mesh = cfm.GmshMeshGenerator(geometry)
        mesh.el_size_factor = self.input_data.el_size_factor
        mesh.el_type = el_type
        mesh.dofs_per_node = dof_per_node
        mesh.return_boundary_elements = True

        coords, edof, dofs, bdofs, *_ = mesh.create()

        # Additional variables
        print("Preparing additional variables...")
        self.pg and self.pg.set(18, "Preparing additional variables...")

        ndof = np.size(dofs)
        ex, ey = cfc.coordxtr(edof, coords, dofs)
        D = np.array([[kx, 0.], [0., ky]])

        # Stiffness matrix
        print("Assembling stiffness matrix...")
        self.pg and self.pg.set(20, "Assembling stiffness matrix...")

        K = np.zeros([ndof, ndof])
        for elx, ely, eldof in zip(ex, ey, edof):
            Ke = cfc.flw2te(elx, ely, ep, D)
            cfc.assem(eldof, K, Ke)

        # Load vector
        print("Assembling force vector...")
        self.pg and self.pg.set(66, "Assembling force vector...")

        f = np.zeros([ndof, 1])

        # Boundary conditions
        print("Assembling boundary conditions...")
        self.pg and self.pg.set(67, "Assembling boundary conditions...")

        bc = np.array([], "i")
        bcVal = np.array([], "f")
        bc, bcVal = cfu.applybc(bdofs, bc, bcVal, 20, 0.0)  # Open side
        bc, bcVal = cfu.applybc(bdofs, bc, bcVal, 30, p)    # Dam side

        # Solve FEM-system
        print("Solving equation system...")
        self.pg and self.pg.set(70, "Solving equation system...")

        a, r = cfc.solveq(K, f, bc, bcVal)

        # Extract element values
        print("Computing element variables...")
        self.pg and self.pg.set(80, "Computing element variables...")

        ed = cfc.extract_eldisp(edof, a)
        qs, qt = cfc.flw2ts(ex, ey, D, ed)

        # Calculating effective flux
        print("Calculating effective flux...")
        self.pg and self.pg.set(97, "Calculating effective flux...")

        eff_flux = []
        for elqs in qs:
            eff_flux.append(np.sqrt(elqs[0] ** 2 + elqs[1] ** 2))

        # Transfer local references to output data
        print("Exporting data...")
        self.pg and self.pg.set(99, "Exporting data...")

        self.output_data.geometry = geometry
        self.output_data.el_type = el_type
        self.output_data.dofs_per_node = dof_per_node
        self.output_data.coords = coords
        self.output_data.edof = edof
        self.output_data.dofs = dofs
        self.output_data.a = a
        self.output_data.r = r
        self.output_data.ed = ed
        self.output_data.qs = qs
        self.output_data.qt = qt
        self.output_data.eff_flux = eff_flux

        print("Solver is done.")
        self.pg and self.pg.set(100, "Solver is done.")

    def executeParamStudy(self):
        """Executes parameter study and exports vtk-files"""

        old_d = self.input_data.d
        old_t = self.input_data.t

        if self.input_data.dStudy:
            dRange = np.linspace(self.input_data.d, self.input_data.dEnd,
                                 self.input_data.steps)

            self.output_data.range = dRange
            self.output_data.max_flux = np.zeros(dRange.shape[0], float)

            for i, d in enumerate(dRange, 1):
                print(f"Executing for d = {d}...")
                value = int((i - 1) / self.input_data.steps * 100)
                self.pg and self.pg.set(value, f"Executing for d = {d:.2f}...")

                self.input_data.d = float(d)
                solver = Solver(self.input_data, self.output_data)
                solver.execute()

                self.output_data.max_flux[i-1] = max(self.output_data.eff_flux)
                self.exportVtk(f"{self.basepath}_d{i:03d}")
        else:
            tRange = np.linspace(self.input_data.t, self.input_data.tEnd,
                                 self.input_data.steps)

            self.output_data.range = tRange
            self.output_data.max_flux = np.zeros(tRange.shape[0], float)

            for i, t in enumerate(tRange, 1):
                print(f"Executing for t ={t}...")
                value = int((i - 1) / self.input_data.steps * 100)
                self.pg and self.pg.set(value, f"Executing for t = {t:.2f}...")

                self.input_data.t = float(t)
                solver = Solver(self.input_data, self.output_data)
                solver.execute()

                self.output_data.max_flux[i-1] = max(self.output_data.eff_flux)
                self.exportVtk(f"{self.basepath}_t{i:03d}")

        self.input_data.d = old_d
        self.input_data.t = old_t

        print("Parameter study is done.")
        self.pg and self.pg.set(100, "Parameter study is done.")

    def exportVtk(self, path):
        """Export results to VTK format"""

        print(f"Exporting results to {path}.\n")

        # Expand variables to three dimensions
        fluxmatrix = (np.c_[self.output_data.qs,
                      np.zeros(self.output_data.qs.shape[0])])
        coordmatrix = (np.c_[self.output_data.coords,
                       np.zeros(self.output_data.coords.shape[0])])

        points = coordmatrix.tolist()
        polygons = (self.output_data.edof-1).tolist()
        pointData = vtk.PointData(vtk.Scalars(
                        self.output_data.a.tolist(), name="Pizeometric head"))
        cellData = vtk.CellData(vtk.Scalars(
                       self.output_data.eff_flux, name="Effective flux"),
                       vtk.Vectors(fluxmatrix, "Flux"))
        structure = vtk.PolyData(points=points, polygons=polygons)
        vtkData = vtk.VtkData(structure, pointData, cellData)
        vtkData.tofile(path, "ascii")


class Report(object):
    """Class to present in-/outdata as a report

    Attributes:
        input_data (InputData): Object containing input data
        output_data (OutputData): Object containing output data
        report (str): String to print out as report
    """

    def __init__(self, input_data, output_data):
        self.input_data = input_data
        self.output_data = output_data
        self.report = ""

    def clear(self):
        """Clears report"""

        self.report = ""

    def add_text(self, text=""):
        """Adds a new line of text to report

        Args:
            text (str, optional): Text to add to report (defult is "")
        """

        self.report += str(text) + "\n"

    def __str__(self):
        self.clear()

        # Banner
        s = f"Report of Groundwater flow | Version {self.input_data.version}"
        self.add_text(f"{'':=^60}\n{s:^60}\n{'':=^60}")

        # Model input
        self.add_text()
        self.add_text(f"{' Model input ':~^60}")

        self.add_text("Element dimensions [m]")
        self.add_text(f"w: {self.input_data.w}")
        self.add_text(f"h: {self.input_data.h}")
        self.add_text(f"d: {self.input_data.d}")
        self.add_text(f"t: {self.input_data.t}")
        self.add_text(f"p: {self.input_data.p}")

        self.add_text()
        self.add_text("Permeability [m/day]")
        self.add_text(f"kx: {self.input_data.kx}")
        self.add_text(f"ky: {self.input_data.ky}")

        self.add_text()
        self.add_text("Thickness [m]")
        self.add_text(f"ep: {self.input_data.ep}")

        self.add_text()
        self.add_text("Maximum element size [-]")
        self.add_text(f"el_size_factor: {self.input_data.el_size_factor}")

        # Model output
        self.add_text()
        self.add_text(f"{' Model Output ':~^60}")

        self.add_text("Number of nodes [-]")
        self.add_text(f"nnode: {self.output_data.coords.shape[0]}")

        self.add_text()
        self.add_text("Number of elements [-]")
        self.add_text(f"nnode: {self.output_data.edof.shape[0]}")

        self.add_text()
        self.add_text("Maximal effective flux [m^2/day]")
        self.add_text(f"Max eff_flux: {max(self.output_data.eff_flux):.2f}")

        # Per node data
        self.add_text()
        self.add_text("Per Node")
        table = tbl.tabulate(
            {"\nNode": self.output_data.dofs,
             "X-coord\n[m]": self.output_data.coords[:, 0],
             "Y-coord\n[m]": self.output_data.coords[:, 1],
             "Pizeometric\nhead [m]": self.output_data.a},
            headers="keys",
            numalign="center",
            floatfmt=(".0f", ".2f", ".2f", ".2f"),
            tablefmt="simple",
        )
        self.add_text(table)

        # Per element data
        self.add_text()
        self.add_text("Per Element" + "{'[m^2/day]':>38}")
        table = tbl.tabulate(
            {"\nElem": np.arange(1, np.shape(self.output_data.edof)[0] + 1),
             "node\n1": self.output_data.edof[:, 0],
             "node\n2": self.output_data.edof[:, 1],
             "node\n3": self.output_data.edof[:, 2],
             "\n  x  ": self.output_data.qs[:, 0],
             "Flux\n  y  ": self.output_data.qs[:, 1],
             "\n eff ": self.output_data.eff_flux},
            headers="keys",
            numalign="center",
            floatfmt=(".0f", ".0f", ".0f", ".0f", ".2f", ".2f", ".2f", ".2f"),
            tablefmt="simple",
        )
        self.add_text(table)

        self.add_text(f"{'':=^60}")

        return self.report


class Visualization(object):
    """Class to visualize outdata as plots

    Attributes:
        input_data (InputData): Object containing input data
        output_data (OutputData): Object containing output data
        
        geomFig (Figure): Figure of geometry
        meshFig (Figure): Figure of mesh
        piezoFig (Figure): Figure of piezometric head
        reacFig (Figure): Figure of reaction flux
        effFig (Figure): Figure of effective flux
        paramFig (Figure): Figure of maximal effective flux

        geom_widget (FigureCanvasQTAgg): FigureCanvas of geometry
        mesh_widget (FigureCanvasQTAgg): FigureCanvas of mesh
        piezo_widget (FigureCanvasQTAgg): FigureCanvas of piezometric head
        reac_widget (FigureCanvasQTAgg): FigureCanvas of reaction flux
        eff_widget (FigureCanvasQTAgg): FigureCanvas of effective flux
        param_widget (FigureCanvasQTAgg): FigureCanvas of maximal effective flux
    """

    def __init__(self, input_data, output_data):
        self.input_data = input_data
        self.output_data = output_data

        self.geomFig = None
        self.meshFig = None
        self.piezoFig = None
        self.reacFig = None
        self.effFig = None
        self.paramFig = None

        self.geom_widget = None
        self.mesh_widget = None
        self.piezo_widget = None
        self.reac_widget = None
        self.eff_widget = None
        self.param_widget = None

    def showAll(self):
        """Plots multiple outdata"""

        geometry = self.output_data.geometry
        el_type = self.output_data.el_type
        dofs_per_node = self.output_data.dofs_per_node
        coords = self.output_data.coords
        edof = self.output_data.edof
        a = self.output_data.a
        r = self.output_data.r
        eff_flux = self.output_data.eff_flux

        # Geometry
        cfv.set_figure_dpi(100)
        cfv.figure(fig_size=(10, 3))
        cfv.draw_geometry(geometry, title="Geometry")

        # Mesh
        cfv.figure(fig_size=(10, 3))
        cfv.draw_mesh(coords, edof, dofs_per_node, el_type,
                      filled=True, title="Mesh")

        # Piezometric head
        cfv.figure(fig_size=(10, 3))
        cfv.draw_nodal_values_shaded(a, coords, edof, title="Piezometric head")
        cfv.colorbar(orientation="vertical",
                     label=r"Piezometric head $\phi$ [m]")

        # Reaction flux
        cfv.figure(fig_size=(10, 3))
        cfv.draw_nodal_values_shaded(r, coords, edof, title="Reaction flux")
        cfv.colorbar(orientation="vertical",
                     label=r"Reaction flux $q$ [m$^2$/day]")

        # Effective flux
        cfv.figure(fig_size=(10, 3))
        cfv.draw_element_values(eff_flux, coords, edof, dofs_per_node, el_type,
                                None, False, title="Effective flux")
        cfv.colorbar(orientation="vertical",
                     label=r"Effective flux $q_{eff}$ [m$^2$/day]")

    def showGeometry(self, show=True):
        """Plots geometry

        Args:
            show (bool, optional): Flag if figures are drawn. Defaults to True.

        Returns:
            FigureCanvasQTAgg: Canvas of geometry (if show=False)
        """

        if self.geomFig is None:
            self.geomFig = cfv.figure(self.geomFig, show=show)
            self.geom_widget = cfv.figure_widget(self.geomFig, None)

        cfv.clf()
        cfv.draw_geometry(self.output_data.geometry, title="Geometry")
        if show:
            self.wait()
        else:
            return self.geom_widget

    def showMesh(self, show=True):
        """Plots mesh
        
        Args:
            show (bool, optional): Flag if figures are drawn. Defaults to True.

        Returns:
            FigureCanvasQTAgg: Canvas of mesh (if show=False)
        """

        if self.meshFig is None:
            self.meshFig = cfv.figure(self.meshFig, show=show)
            self.mesh_widget = cfv.figure_widget(self.meshFig, None)

        cfv.clf()
        cfv.draw_mesh(self.output_data.coords, self.output_data.edof,
                      self.output_data.dofs_per_node, self.output_data.el_type,
                      filled=True, title="Mesh")
        if show:
            self.wait()
        else:
            return self.mesh_widget

    def showPiezo(self, show=True):
        """Plots piezometric head
        
        Args:
            show (bool, optional): Flag if figures are drawn. Defaults to True.

        Returns:
            FigureCanvasQTAgg: Canvas of piezometric head (if show=False)
        """

        if self.piezoFig is None:
            self.piezoFig = cfv.figure(self.piezoFig, show=show)
            self.piezo_widget = cfv.figure_widget(self.piezoFig, None)

        cfv.draw_nodal_values_shaded(
                self.output_data.a, self.output_data.coords,
                self.output_data.edof, title="Piezometric head")
        cfv.colorbar(orientation="horizontal",
                     label=r"Piezometric head $\phi$ [m]")
        if show:
            self.wait()
        else:
            return self.piezo_widget

    def showReac(self, show=True):
        """Plots reaction flux
        
        Args:
            show (bool, optional): Flag if figures are drawn. Defaults to True.

        Returns:
            FigureCanvasQTAgg: Canvas of reaction flux (if show=False)
        """

        if self.reacFig is None:
            self.reacFig = cfv.figure(self.reacFig, show=show)
            self.reac_widget = cfv.figure_widget(self.reacFig, None)

        cfv.draw_nodal_values_shaded(
                self.output_data.r, self.output_data.coords,
                self.output_data.edof, title="Reaction flux")
        cfv.colorbar(orientation="horizontal",
                     label=r"Reaction flux $q$ [m$^2$/day]")
        if show:
            self.wait()
        else:
            return self.reac_widget

    def showEff(self, show=True):
        """Plots effective flux
        
        Args:
            show (bool, optional): Flag if figures are drawn. Defaults to True.

        Returns:
            FigureCanvasQTAgg: Canvas of effective flux (if show=False)
        """

        if self.effFig is None:
            self.effFig = cfv.figure(self.effFig, show=show)
            self.eff_widget = cfv.figure_widget(self.effFig, None)

        cfv.draw_element_values(
                self.output_data.eff_flux, self.output_data.coords,
                self.output_data.edof, self.output_data.dofs_per_node,
                self.output_data.el_type, None, False, title="Effective flux")
        cfv.colorbar(orientation="horizontal",
                     label=r"Effective flux $q_{eff}$ [m$^2$/day]")
        if show:
            self.wait()
        else:
            return self.eff_widget

    def showParam(self, show=True):
        """Plots maximal effective flux for parameter study
        
        Args:
            show (bool, optional): Flag if figures are drawn. Defaults to True.

        Returns:
            FigureCanvasQTAgg: Canvas of maximal effective flux for param-study (if show=False)
        """

        if self.paramFig is None:
            self.paramFig = cfv.figure(self.paramFig, show=show)
            self.param_widget = cfv.figure_widget(self.paramFig, None)

        cfv.plt.plot(self.output_data.range, self.output_data.max_flux, "bo-")
        cfv.plt.ylabel(r"Maximal flow $q_{max}$ [m$^2$/day]")
        if self.input_data.dStudy:
            cfv.plt.xlabel("Depth d [m]")
            cfv.plt.title("Parameter study of depth")
        else:
            cfv.plt.xlabel("Thickness t [m]")
            cfv.plt.title("Parameter study of thickness")
        if show:
            self.wait()
        else:
            return self.param_widget

    def closeAll(self):
        """Closes all plots and remove attributes"""

        cfv.close_all()

        self.geomFig = None
        self.meshFig = None
        self.piezoFig = None
        self.reacFig = None
        self.effFig = None
        self.paramFig = None

        self.geom_widget = None
        self.mesh_widget = None
        self.piezo_widget = None
        self.reac_widget = None
        self.eff_widget = None
        self.param_widget = None

    def wait(self):
        """Waits for plots to be closed"""

        cfv.show_and_wait()
