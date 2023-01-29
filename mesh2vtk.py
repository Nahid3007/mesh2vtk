import numpy as np
import sys
from dataclasses import dataclass

@dataclass
class Node:
    fem_node_id: int
    vtk_node_nid: int
    x: float
    y: float
    z: float

@dataclass
class Element:
    fem_elem_id: int
    vtk_elem_id: int
    attached_nodes: list[int]

def parse_input(inputfile):

    with open(inputfile) as f:
        lines = [line.strip() for line in f]

    nodes = {}
    elements = {}

    vtk_node_id = 0
    vtk_elem_id = 0

    for line in lines:
        if line.startswith('GRID'):
            fem_node_id = line[8:16].strip()
            x = float(line[24:32].strip())
            try:
                y = float(line[32:40].strip())
            except ValueError:
                y = 0.
            try:
                z = float(line[40:48].strip())
            except ValueError:
                z = 0.

            nodes[fem_node_id] = Node(fem_node_id, vtk_node_id, x, y, z)

            vtk_node_id += 1

        elif line.startswith('CTRIA3'):
            fem_elem_id = line[8:16].strip()
            n1 = line[24:32].strip()
            n2 = line[32:40].strip()
            n3 = line[40:48].strip()

            elements[fem_elem_id] = Element(fem_elem_id, vtk_elem_id, [n1, n2, n3])

            vtk_elem_id += 1

        elif line.startswith('CQUAD4'):
            fem_elem_id = line[8:16].strip()
            n1 = line[24:32].strip()
            n2 = line[32:40].strip()
            n3 = line[40:48].strip()
            n4 = line[48:56].strip()

            elements[fem_elem_id] = Element(fem_elem_id, vtk_elem_id, [n1, n2, n3, n4])

            vtk_elem_id += 1

    return nodes, elements

def writeVTKElements(nodes, elements, outputfile):

    print(f'\nWriting VTK Elements ...')
    
    with open(outputfile,'w') as f:

        #************************** Write VTK Lines ********************************
        f.write(f'<?xml version="1.0"?>\n')
        f.write(f'<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">\n')
        f.write(f'<UnstructuredGrid>\n')

        no_of_nodes = len(nodes)
        no_of_cells = len(elements)

        f.write(f'<Piece NumberOfPoints="{no_of_nodes}" NumberOfCells="{no_of_cells}">\n')
        
        #********************************** Points *********************************
        f.write(f'<Points>\n')

        f.write(f'<DataArray type="Float64" Name="Points" NumberOfComponents="3" format="ascii">\n')
        for nid in nodes.keys():
            f.write(f' {nodes[nid].x} {nodes[nid].y} {nodes[nid].z}')
        f.write(f'\n</DataArray>\n')

        f.write(f'</Points>\n')
        #*******************************************************************************
        
        #********************************** Cells **********************************
        f.write(f'<Cells>\n')

        f.write(f'<DataArray type="Int32" Name="connectivity" format="ascii">\n')
        for eid in elements.keys():
            no_of_nid = len(elements[eid].attached_nodes)
            if no_of_nid == 3:
                for i in range(no_of_nid):
                    f.write(f' {nodes[elements[eid].attached_nodes[i]].vtk_node_nid}')
            elif no_of_nid == 4:
                for i in range(no_of_nid):
                    f.write(f' {nodes[elements[eid].attached_nodes[i]].vtk_node_nid}')
            else:
                print(f'Length of node unknown!')
                exit
        f.write(f'\n</DataArray>\n')

        f.write(f'<DataArray type="Int32" Name="offsets" format="ascii">\n')
        offset = 0
        for eid in elements.keys():
            no_of_nid = len(elements[eid].attached_nodes)
            offset += no_of_nid
            f.write(f' {offset}')
        f.write(f'\n</DataArray>\n')

        f.write(f'<DataArray type="Int32" Name="types" format="ascii">\n')
        for eid in elements.keys():
            no_of_nid = len(elements[eid].attached_nodes)
            if no_of_nid == 3:
                f.write(f' 5')
            else:
                f.write(f' 9')
        f.write(f'\n</DataArray>\n')

        f.write(f'</Cells>\n')
        #*******************************************************************************

        #********************************** Cell Data **********************************
        f.write(f'<CellData>\n')
        
        f.write(f'<Array type="Int32" Name="FEM_ELEMENT_ID" format="ascii">\n')
        for eid in elements.keys():
            f.write(f' {elements[eid].fem_elem_id}')
        f.write(f'\n</Array>\n')

        f.write(f'</CellData>\n')
        #********************************************************************************

        #********************************** Point Data **********************************
        f.write(f'<PointData>\n')

        f.write(f'<Array type="Int32" Name="FEM_NODE_ID" format="ascii">\n')
        for nid in nodes.keys():
            f.write(f' {nodes[nid].fem_node_id}')
        f.write(f'\n</Array>\n')
        
        f.write(f'</PointData>\n')
        #********************************************************************************

        f.write(f'</Piece>\n')
        f.write(f'</UnstructuredGrid>\n')
        f.write(f'</VTKFile>\n')

        print(f' Number of Nodes: {no_of_nodes}')
        print(f' Number of Cells: {no_of_cells}')
        print(f' File written to "{outputfile}"')

#**********************************************************************************************

if __name__ == '__main__':

    inputfile = str(sys.argv[1])
    outputfile = str(sys.argv[2])

    print(f'*****************************************************************************')
    print(f'*                                                                           *') 
    print(f'*                            M E S H  2  V T K                              *')
    print(f'*                                                                           *')
    print(f'*****************************************************************************')


    print('')
    print(f'Parse input file "{inputfile}" ...')
    nodes, elements = parse_input(inputfile)

    writeVTKElements(nodes, elements, outputfile)

    print(f'')
    print('Done.')