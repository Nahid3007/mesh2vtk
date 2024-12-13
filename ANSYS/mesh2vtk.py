'''

mesh2vtk: Converts an ANSYS Finite Element Model into a vtu file

usage: mesh2vtk.py [-h] --inputfile INPUTFILE --outputfile OUTPUTFILE [--ascii] [--fem_node_string] [--fem_element_string]

options:
  -h, --help            show this help message and exit
  --inputfile INPUTFILE
                        Path to the input file.
  --outputfile OUTPUTFILE
                        Path to the output vtu file.
  --ascii               Optional: Data mode of vtu file. BINARY set as default mode. If this argument is passed data
                        mode will be set to ASCII.
  --fem_node_string     Optional: Map FEM node id to vtu file.
  --fem_element_string  Optional: Map FEM element id to vtu file.
  
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


def parse_ansys_file(inputfile):

    # Read entire input file and save to a list
    with open(inputfile) as f:
        lines = [line.rstrip() for line in f]

    elem_type_list = []
    vtk_nid = 0
    vtk_eid = 0

    nodes = {}
    elements = {}

    grid_count = 0

    bNodes = False
    bElems = False

    temp = []
    elems_line_181 = []
    elems_line_187 = []
    elems_line_186 = []
    elems_line_185 = []
    elem_type_list = []
    
    for line in lines:
        
        #**** parse nodes
        if line.strip().lower().startswith('nblock'):
            bNodes = True
        elif bNodes and not line.startswith('-1'):
            if line.strip().startswith('('):
                continue
            
            fem_nid = line[0:9].strip()
            grid_count += 1

            x_coord = line[10:30].strip()
            y_coord = line[30:50].strip()
            z_coord = line[50:70].strip()

            nodes[fem_nid] = Node(fem_nid, vtk_nid)
            nodes[fem_nid].coordinates = np.array([x_coord, y_coord, z_coord], dtype=np.float32)

            vtk_nid = vtk_nid + 1
    
        #**** parse elements
        elif line.strip().lower().startswith('et,'): 
            etype_no = line.split(',')[2]
            elem_type_list.append(etype_no)

            bNodes = False
            bElems = True

        elif bElems and not line.startswith('-1'):
            if line.strip().startswith('(') or line.strip().startswith('eblock') or line.strip().startswith('keyo'):
                continue
            
            if etype_no == '187': # 2n order tetra element (10 nodes)
                elems_line_187.append(line)
            
            elif etype_no == '186': # 20 node solid element (hex)
                elems_line_186.append(line)
                
            elif etype_no == '185': # 8 node solid element (hex)
                elems_line_185.append(line)
                
            elif etype_no == '181': # shell elements
                elems_line_181.append(line)
            
        else:
            bNodes = False
            bElems = False

    if '181' in elem_type_list:
        for i in range(len(elems_line_181)):
                fem_eid = elems_line_181[i][91:99].strip()

                elements[fem_eid] = Element(fem_eid, vtk_eid)

                attached_nodes_1st_line = [nodes[str(int(elems_line_181[i][99:135][j:j+9]))].vtk_nid for j in range(0, len(elems_line_181[i][99:135]), 9)]
                                
                # for 3-node shell element
                if len(set(attached_nodes_1st_line[2:])) == 1:
                    attached_nodes_1st_line = attached_nodes_1st_line[0:3] 
                
                elements[fem_eid].attached_nodes = attached_nodes_1st_line

                vtk_eid = vtk_eid + 1

    if '185' in elem_type_list:
        for i in range(len(elems_line_185)):
                fem_eid = elems_line_185[i][91:99].strip()

                elements[fem_eid] = Element(fem_eid, vtk_eid)

                attached_nodes_1st_line = [nodes[str(int(elems_line_185[i][99:173][j:j+9]))].vtk_nid for j in range(0, len(elems_line_185[i][99:173]), 9)]
                                
                # for 4-node tet element
                if len(set(attached_nodes_1st_line[4:])) == 1:
                    attached_nodes_1st_line = attached_nodes_1st_line[0:3] + [attached_nodes_1st_line[5]] 
                
                elements[fem_eid].attached_nodes = attached_nodes_1st_line

                vtk_eid = vtk_eid + 1

    if '186' in elem_type_list:
        for i in range(len(elems_line_186)):
            if i % 2 == 0: 
                fem_eid = elems_line_186[i][91:99].strip()

                elements[fem_eid] = Element(fem_eid, vtk_eid)

                attached_nodes_1st_line = [nodes[str(int(elems_line_186[i][99:173][j:j+9]))].vtk_nid for j in range(0, len(elems_line_186[i][99:173]), 9)]
                attached_nodes_2nd_line = [nodes[str(int(elems_line_186[i+1][0:][j:j+9]))].vtk_nid for j in range(0, len(elems_line_186[i+1][0:]), 9)]
                
                elements[fem_eid].attached_nodes = attached_nodes_1st_line + attached_nodes_2nd_line

                vtk_eid = vtk_eid + 1
                
    if '187' in elem_type_list:
        for i in range(len(elems_line_187)):
            if i % 2 == 0: 
                fem_eid = elems_line_187[i][91:99].strip()

                elements[fem_eid] = Element(fem_eid, vtk_eid)

                attached_nodes_1st_line = [nodes[str(int(elems_line_187[i][99:173][j:j+9]))].vtk_nid for j in range(0, len(elems_line_187[i][99:173]), 9)]
                attached_nodes_2nd_line = [nodes[str(int(elems_line_187[i+1][0:][j:j+9]))].vtk_nid for j in range(0, len(elems_line_187[i+1][0:]), 9)]
                
                elements[fem_eid].attached_nodes = attached_nodes_1st_line + attached_nodes_2nd_line

                vtk_eid = vtk_eid + 1
                
    return nodes, elements, elem_type_list, temp

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
        "tria": 5,
        "tetra4": 10,
        "hexa": 12,
        "wedge": 13,
        "tetra10": 24,
        "hexa20": 25,
    }

    vtk_cell_type_no = []

    for eid in elements.keys():
        
        # Quad elements
        if len(elements[eid].attached_nodes) == 4 and '181' in elem_type_list:
            quad = vtk.vtkQuad()
            for i in range(len(elements[eid].attached_nodes)):
                quad.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(quad)
            vtk_cell_type_no.append(vtk_cell_type["quad"])

        # Tria elements
        elif len(elements[eid].attached_nodes) == 3 and '181' in elem_type_list:
            tria = vtk.vtkTriangle()
            for i in range(len(elements[eid].attached_nodes)):
                tria.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(tria)
            vtk_cell_type_no.append(vtk_cell_type["tria"])

        # Tetra elements
        elif len(elements[eid].attached_nodes) == 4 and '185' in elem_type_list:
            tetra4 = vtk.vtkTetra()
            for i in range(len(elements[eid].attached_nodes)):
                tetra4.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(tetra4)
            vtk_cell_type_no.append(vtk_cell_type["tetra4"])

        # Hexa elements
        elif len(elements[eid].attached_nodes) == 8 and '185' in elem_type_list:
            hexa = vtk.vtkHexahedron()
            for i in range(len(elements[eid].attached_nodes)):
                hexa.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(hexa)
            vtk_cell_type_no.append(vtk_cell_type["hexa"])

        # Tetrahedra (2nd order) elements
        elif len(elements[eid].attached_nodes) == 10 and '187' in elem_type_list:
            tetra10 = vtk.vtkQuadraticTetra()
            for i in range(len(elements[eid].attached_nodes)):
                tetra10.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(tetra10)
            vtk_cell_type_no.append(vtk_cell_type["tetra10"])
 
       # Hexahedra (2nd order) elements
        elif len(elements[eid].attached_nodes) == 20 and '186' in elem_type_list:
            hexa20 = vtk.vtkQuadraticHexahedron()
            for i in range(len(elements[eid].attached_nodes)):
                hexa20.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(hexa20)
            vtk_cell_type_no.append(vtk_cell_type["hexa20"]) 

        # Penta elements (SOON AVAILABLE)
        elif len(elements[eid].attached_nodes) == 6 and 'CPENTA' in elem_type_list:
            wedge = vtk.vtkWedge()
            for i in range(len(elements[eid].attached_nodes)):
                wedge.GetPointIds().SetId(i, elements[eid].attached_nodes[i])
            vtk_cells.InsertNextCell(wedge)
            vtk_cell_type_no.append(vtk_cell_type["wedge"])

        # Pyramid elements (SOON AVAILABLE)

    # Create unstructured grid
    ugrid = vtk.vtkUnstructuredGrid()
    ugrid.SetPoints(vtk_points)
    ugrid.SetCells(vtk_cell_type_no, vtk_cells)

    # Mapping of FEM node and element ids to vtu model
    if fem_node_string:
        fem_node_id = vtk.vtkIntArray()
        fem_node_id.SetNumberOfComponents(1)
        fem_node_id.SetName("FEM_NODE_ID")
        for nid in nodes.keys():
            fem_node_id.InsertNextValue(int(nodes[nid].nid))
        # Add the point data to the VTK unstructured dataset
        ugrid.GetPointData().AddArray(fem_node_id)

    if fem_element_string:
        fem_element_id = vtk.vtkIntArray()
        fem_element_id.SetNumberOfComponents(1)
        fem_element_id.SetName("FEM_ELEMENT_ID")
        for eid in elements.keys():
            fem_element_id.InsertNextValue(int(elements[eid].eid))
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
    print(f"| '_  _ \ / _ \/ __| '_ \  __) \ \ / / __| |/ /  ")
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
    
    print(f'Binary vtu file data mode: {not dataModeASCII} ')    
    print(f'Parsing input file: {inputfile}')
    
    print(f'') 
    
    start_time = time.time()

    nodes, elements, elem_type_list, temp = parse_ansys_file(inputfile)

    #************************ FOR DEBUGGING
    #for nid in nodes.keys():
    #    print(nodes[nid].nid, nodes[nid].vtk_nid, nodes[nid].coordinates)

    #for eid in elements.keys():
    #    print(elements[eid].vtk_eid, elements[eid].attached_nodes)

    # print(temp)
    #************************

    print(f'Write vtu file ...')
    write_vtk(nodes, elements, elem_type_list, outputfile, dataModeASCII, fem_node_string, fem_element_string)

    end_time = time.time()

    print(f'')
    print(f'Elapsed time: {(end_time - start_time):.3f} seconds')
    print(f'Done.')