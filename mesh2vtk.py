'''

mesh2vtk: Converts a Nastran/OptiStruct Finite Element Model into a vtu file

'''

import vtk
import numpy as np
import argparse
import time


class Node:
    def __init__(self, nid: int, vtk_nid: int):
        self.nid = nid
        self.vtk_nid = vtk_nid
        self.coordinates = []


class Element:
    def __init__(self, eid: int, vtk_eid: int):
        self.eid = eid
        self.vtk_eid = vtk_eid
        self.attached_nodes = []


class ShellProperty:
    def __init__(self, eid: int, thickness):
        self.eid = eid
        self.thickness = thickness


def string2float(string) -> float:
    if "-" in string[1:]:
        return float(string[0] + string[1:].replace("-", "e-"))
    elif "+" in string[1:]:
        return float(string[0] + string[1:].replace("+", "e+"))
    else:
        if not string:
            return 0.
        return float(string)


def ParseArgs():
    parser = argparse.ArgumentParser(description='A python tool that converts a (general purpose) Finite Element '
                                                 'Model to a VTK model')
    parser.add_argument("--inputfile", help="Path to the input file.", required=True, type=str, action='store')
    parser.add_argument("--outputfile", help="Path to the output vtu file.", required=True, type=str, action='store')
    parser.add_argument('--ascii', action='store_true', default=False, help='Optional: Data mode of vtu file. BINARY '
                                                                            'set as default mode. If this argument is '
                                                                            'passed data mode will be set to ASCII.')
    parser.add_argument('--fem_node_string', action='store_true', default=False,
                        help='Optional: Map FEM node id to vtu file.')
    parser.add_argument('--fem_element_string', action='store_true', default=False,
                        help='Optional: Map FEM element id to vtu file.')
    args = parser.parse_args()

    return args


def nastran_parser(inputfile):

    # Read entire input file and save to a list
    with open(inputfile) as f:
        lines = [line.strip() for line in f]

    elem_type_list = []
    vtk_nid = 0
    vtk_eid = 0

    nodes = {}
    elements = {}
    pshell = {}
    shell_property = {}
    coordinate_system = {}

    # Parse coordinate systems
    for line in lines:
        line = line.strip()

        if line.startswith('CORD2C'):
            coord_type = 'CORD2C'
            line_index = lines.index(line)
            first_line = [line[i:i + 8].strip() for i in range(0, len(line), 8)]
            second_line = [lines[line_index + 1][i:i + 8].strip() for i in range(0, len(lines[line_index + 1]), 8)]
            systemId = first_line[1]

            coord_point_A = np.asarray([string2float(first_line[3]), string2float(first_line[4]), string2float(first_line[5])])
            coord_point_B = np.asarray([string2float(first_line[6]), string2float(first_line[7]), string2float(first_line[8])])
            if len(second_line) < 3:
                coord_point_C = np.asarray([string2float(second_line[1]), 0., 0.])
            elif len(second_line) < 4:
                coord_point_C = np.asarray([string2float(second_line[1]), string2float(second_line[2]), 0.])
            else:
                coord_point_C = np.asarray([string2float(second_line[1]), string2float(second_line[2]), string2float(second_line[3])])

            coordinate_system[systemId] = [coord_type, coord_point_A, coord_point_B, coord_point_C]
            
    if not coordinate_system:
        pass
    else:
        print(f'Local coordinate system found:')
        print(f'   Type     Id')
        for key, value in coordinate_system.items():
            print(f'   {value[0]}   {key}')

    grid_count = 0

    # Parse nodes
    for line in lines:
        line = line.strip()

        if line.lower().startswith('grid'):
            split_strings = [line[i:i + 8].strip() for i in range(0, len(line), 8)]

            fem_nid = int(split_strings[1])

            if split_strings[2] in coordinate_system.keys():
                system_id = split_strings[2]
                coord_point_A = coordinate_system[systemId][1]
                R = string2float(split_strings[3])
                Phi_deg = string2float(split_strings[4])
                Phi_rad = (np.pi*Phi_deg)/180

                x = coord_point_A[0] + R*np.cos(Phi_rad)
                y = coord_point_A[1] + R*np.sin(Phi_rad)
                z = coord_point_A[2] + string2float(split_strings[5])

                grid_count += 1
            else:
                x = string2float(split_strings[3])
                y = string2float(split_strings[4])
                z = string2float(split_strings[5])

            nodes[fem_nid] = Node(fem_nid, vtk_nid)

            nodes[fem_nid].coordinates = np.array([x, y, z], dtype=np.float32)

            vtk_nid = vtk_nid + 1

    print(f'   {grid_count} points transformed to global coordinates')

    # Parse PSHELL properties
    for line in lines:
        line = line.strip()

        if line.lower().startswith('pshell'):
            split_strings = [line[i:i + 8].strip() for i in range(0, len(line), 8)]
            pid = split_strings[1]
            thickness = split_strings[3]

            pshell[pid] = thickness

    # Parse elements
    for line in lines:
        line = line.strip()

        elem_type = None

        if (line.lower().startswith('cquad4') or line.lower().startswith('ctria3') or
                line.lower().startswith('chexa') or line.lower().startswith('cpenta') or
                line.lower().startswith('ctetra')):

            if line.lower().startswith('cquad4'):
                elem_type = 'CQUAD4'
            elif line.lower().startswith('ctria3'):
                elem_type = 'CTRIA3'
            elif line.lower().startswith('chexa'):
                elem_type = 'CHEXA'
            elif line.lower().startswith('cpenta'):
                elem_type = 'CPENTA'
            elif line.lower().startswith('ctetra'):
                elem_type = 'CTETRA'

            if elem_type not in elem_type_list:
                elem_type_list.append(elem_type)

            if elem_type == 'CHEXA' or elem_type == 'CTETRA':
                line_index = lines.index(line)
                hex_tet_line = [line[i:i + 8].strip() for i in range(0, len(line), 8)]
                if len(hex_tet_line) == 10:
                    hex_tet_line.pop(-1)
                hex_tet_cont_line = [lines[line_index + 1][i:i + 8].strip() for i in range(0, len(lines[line_index + 1]), 8)]
                hex_tet_cont_line.pop(0)
                split_strings = hex_tet_line + hex_tet_cont_line
            else:
                split_strings = [line[i:i + 8].strip() for i in range(0, len(line), 8)]

            fem_eid = int(split_strings[1])
            elem_pid = split_strings[2]

            elements[fem_eid] = Element(fem_eid, vtk_eid)

            if elem_type == 'CQUAD4' or elem_type == 'CTRIA3':
                shell_property[vtk_eid] = ShellProperty(vtk_eid, float(pshell[elem_pid]))
            elif elem_type == 'CHEXA' or elem_type == 'CPENTA' or elem_type == 'CTETRA':
                shell_property[vtk_eid] = ShellProperty(vtk_eid, np.nan)

            nodes_list = []
            for i in [x for x in range(len(split_strings) - 3)]:
                fem_nid = int(split_strings[3 + i])
                nodes_list.append(nodes[fem_nid].vtk_nid)

            elements[fem_eid].attached_nodes = np.asarray(nodes_list)

            vtk_eid = vtk_eid + 1

    return nodes, elements, elem_type_list, pshell, shell_property, coordinate_system


def write_vtk(nodes, elements, elem_type_list, outputfile, dataModeASCII, fem_node_string, fem_element_string):
    # Define VTK Points
    vtk_points = vtk.vtkPoints()
    for nid in nodes.keys():
        vtk_points.InsertNextPoint(
            nodes[nid].coordinates[0],
            nodes[nid].coordinates[1],
            nodes[nid].coordinates[2]
        )

    # Define VTK Cells
    vtk_cells = vtk.vtkCellArray()

    vtk_cell_type = {
        "quad": 9,
        "tria": 6,
        "hexa": 12,
        "wedge": 13,
        "tetra10": 24,
    }

    vtk_cell_type_no = []

    for eid in elements.keys():
        # Quad elements
        if len(elements[eid].attached_nodes) == 4 and 'CQUAD4' in elem_type_list:
            quad = vtk.vtkQuad()
            for i in range(len(elements[eid].attached_nodes)):
                quad.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(quad)
            vtk_cell_type_no.append(vtk_cell_type["quad"])

        # Tria elements
        elif len(elements[eid].attached_nodes) == 3 and 'CTRIA3' in elem_type_list:
            tria = vtk.vtkTriangle()
            for i in range(len(elements[eid].attached_nodes)):
                tria.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(tria)
            vtk_cell_type_no.append(vtk_cell_type["tria"])

        # Hexa elements
        elif len(elements[eid].attached_nodes) == 8 and 'CHEXA' in elem_type_list:
            hexa = vtk.vtkHexahedron()
            for i in range(len(elements[eid].attached_nodes)):
                hexa.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(hexa)
            vtk_cell_type_no.append(vtk_cell_type["hexa"])

        # Penta elements
        elif len(elements[eid].attached_nodes) == 6 and 'CPENTA' in elem_type_list:
            wedge = vtk.vtkWedge()
            for i in range(len(elements[eid].attached_nodes)):
                wedge.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(wedge)
            vtk_cell_type_no.append(vtk_cell_type["wedge"])

        # Tetrahedra (2nd order) elements
        elif len(elements[eid].attached_nodes) == 10 and 'CTETRA' in elem_type_list:
            tetra10 = vtk.vtkQuadraticTetra()
            for i in range(len(elements[eid].attached_nodes)):
                tetra10.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(tetra10)
            vtk_cell_type_no.append(vtk_cell_type["tetra10"])

    # Create unstructured grid
    ugrid = vtk.vtkUnstructuredGrid()
    ugrid.SetPoints(vtk_points)
    ugrid.SetCells(vtk_cell_type_no, vtk_cells)

    # Add thickness values (CellData)
    element_thickness = vtk.vtkTypeFloat32Array()
    element_thickness.SetNumberOfComponents(1)
    element_thickness.SetName("SHELL_THICKNESS")

    if "CQUAD4" in elem_type_list or "CTRIA3" in elem_type_list:
        for eid in elements.keys():
            # Quad elements
            if len(elements[eid].attached_nodes) == 4 and 'CQUAD4' in elem_type_list:
                element_thickness.InsertNextValue(shell_property[elements[eid].vtk_eid].thickness)
            elif len(elements[eid].attached_nodes) == 3 and 'CTRIA3' in elem_type_list:
                element_thickness.InsertNextValue(shell_property[elements[eid].vtk_eid].thickness)
            else:
                element_thickness.InsertNextValue(shell_property[elements[eid].vtk_eid].thickness)
        ugrid.GetCellData().AddArray(element_thickness)

    # Mapping of FEM node and element ids to vtu model
    if fem_node_string:
        fem_node_id = vtk.vtkIntArray()
        fem_node_id.SetNumberOfComponents(1)
        fem_node_id.SetName("FEM_NODE_ID")
        for nid in nodes.keys():
            fem_node_id.InsertNextValue(nodes[nid].nid)
        # Add the point data to the VTK unstructured dataset
        ugrid.GetPointData().AddArray(fem_node_id)

    if fem_element_string:
        fem_element_id = vtk.vtkIntArray()
        fem_element_id.SetNumberOfComponents(1)
        fem_element_id.SetName("FEM_ELEMENT_ID")
        for eid in elements.keys():
            fem_element_id.InsertNextValue(elements[eid].eid)
        # Add the cell data to the VTK unstructured dataset
        ugrid.GetCellData().AddArray(fem_element_id)

    # Write to binary file
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetInputData(ugrid)
    writer.SetFileName(outputfile)

    if not dataModeASCII:
        writer.SetDataModeToBinary()
    else:
        writer.SetDataModeToAscii()
    writer.Write()

    print(f'')
    print(f'VTK Summary:')
    print(f'   Number of Points: {vtk_points.GetNumberOfPoints()}')
    print(f'   Number of Cells : {vtk_cells.GetNumberOfCells()}')
    print(f'   Writing output file: {outputfile}')


if __name__ == '__main__':
    print(f'')
    print(f'==================================================')
    print(f'                     _     ____        _   _      ')
    print(f' _ __ ___   ___  ___| |__ |___ \__   _| |_| | __  ')
    print(f"| '_ ` _ \ / _ \/ __| '_ \  __) \ \ / / __| |/ /  ")
    print(f'| | | | | |  __/\__ \ | | |/ __/ \ V /| |_|   <   ')
    print(f'|_| |_| |_|\___||___/_| |_|_____| \_/  \__|_|\_\  ')
    print(f'')
    print(f'==================================================')

    args = ParseArgs()

    inputfile = args.inputfile
    outputfile = args.outputfile
    dataModeASCII = args.ascii
    fem_node_string = args.fem_node_string
    fem_element_string = args.fem_element_string

    print(f'')

    solver = None
    if 'fem' in inputfile.lower():
        solver = 'OptiStruct'
    elif 'bdf' in inputfile.lower() or 'dat' in inputfile.lower():
        solver = 'Nastran'
    elif 'inp' in inputfile.lower():
        solver = 'Abaqus'

    print(f'Parsing {solver} input file: {inputfile}')
    print(f'Binary vtu file data mode: {not dataModeASCII} ')
    print(f'')

    start_time = time.time()

    nodes, elements, elem_type_list, pshell, shell_property, coordinate_system = nastran_parser(inputfile)

    # print(elem_type_list)

    # for nid in nodes.keys():
    #     print(nodes[nid].nid, nodes[nid].vtk_nid, nodes[nid].coordinates)

    # for eid in elements.keys():
    #     print(elements[eid].eid, elements[eid].vtk_eid, elements[eid].attached_nodes)
    #
    # for eid in shell_property.keys():
    #     print(shell_property[eid].eid, shell_property[eid].thickness)

    # for sid in coordinate_system.keys():
    #     print(f'System id {sid}: {coordinate_system[sid]}')

    write_vtk(nodes, elements, elem_type_list, outputfile, dataModeASCII, fem_node_string, fem_element_string)

    end_time = time.time()

    print(f'')
    print(f'Done. Elapsed time: {(end_time - start_time):.3f} seconds')
