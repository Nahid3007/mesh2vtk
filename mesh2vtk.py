import numpy as np
import sys
import base64
import zlib
import argparse
import os
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

def ParseArgs():
    parser = argparse.ArgumentParser(description='=== Convert a FE mesh to vtk ===')
    parser.add_argument("--inpath", help="Input path (relative, absolute) to input files directory.", required=True, type=str, action='store')
    parser.add_argument("--outfile", help="Name of the output text file.", required=True, type=str, action='store')
    parser.add_argument("--binary", help="base64 binary encoding. If 'False' ascii.", required=False, action='store_false', default=True)
    args = parser.parse_args()
    
    return args
    
def parse_nastran_input(inputfile):

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

def compress_data_to_binary(arr):

    m = arr.nbytes//2**15 + 1

    compr_chunk = []

    for i in range(m):
        chunk = zlib.compress(arr[i*4096:(i+1)*4096],level=-1)
        compr_chunk.append(chunk)

    size_of_last_chunk = arr[(m-1)*4096::].nbytes

    header_arr = np.array([m, 2**15, size_of_last_chunk],dtype=np.uint64)

    for i in range(len(compr_chunk)):
        header_arr = (np.append(header_arr, len(compr_chunk[i]))).astype('uint64')

    b64_head_arr = base64.b64encode(header_arr.tobytes())

    sum = compr_chunk[0]
    for i in range(1,len(compr_chunk)):
        sum = sum + compr_chunk[i]

    b64_arr = base64.b64encode(sum)

    return (b64_head_arr + b64_arr).decode('utf-8')
   
def writeVTKElements(nodes, elements, coding_type, outputfile):
    
    print(f'\nWriting VTK Elements ...')
    
    with open(outputfile,'w') as f:

        #************************** Write VTK Lines ********************************
        f.write(f'<?xml version="1.0"?>\n')

        if binary:
            f.write(f'<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian" header_type="UInt64" compressor="vtkZLibDataCompressor">\n')
        else:
            f.write(f'<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian" header_type="UInt64">\n')

        f.write(f'  <UnstructuredGrid>\n')

        no_of_nodes = len(nodes)
        no_of_cells = len(elements)

        f.write(f'   <Piece NumberOfPoints="{no_of_nodes}" NumberOfCells="{no_of_cells}">\n')

        #********************************** Point Data **********************************
        f.write(f'      <PointData>\n')

        f.write(f'        <DataArray type="Int64" Name="FEM_NODE_ID" format="{coding_type}">\n')
        if binary:
            arr_nid_str = []
            for nid in nodes.keys():
                arr_nid_str.append(nodes[nid].fem_node_id)

            arr_nid_str = np.asarray(arr_nid_str, dtype=np.int64)

            compr_data = compress_data_to_binary(arr_nid_str)
            f.write(f"          {compr_data}")

        else:
            for nid in nodes.keys():
                f.write(f' {nodes[nid].fem_node_id}')
        f.write(f'\n        </DataArray>\n')
        
        f.write(f'      </PointData>\n')
        
        #********************************** Cell Data **********************************
        f.write(f'      <CellData>\n')
        
        f.write(f'        <DataArray type="Int64" Name="FEM_ELEMENT_ID" format="{coding_type}">\n')
        if binary:
            arr_eid_str = []
            for eid in elements.keys():
                arr_eid_str.append(elements[eid].fem_elem_id)

            arr_eid_str = np.asarray(arr_eid_str, dtype=np.int64)

            compr_data = compress_data_to_binary(arr_eid_str)
            f.write(f"          {compr_data}")

        else:
            for eid in elements.keys():
                f.write(f' {elements[eid].fem_elem_id}')
        f.write(f'\n        </DataArray>\n')

        f.write(f'      </CellData>\n')
        
        #********************************** Points *********************************
        f.write(f'      <Points>\n')

        f.write(f'        <DataArray type="Float64" Name="Points" NumberOfComponents="3" format="{coding_type}">\n')
        if binary:
            arr_points = []
            for nid in nodes.keys():
                arr_points.extend([nodes[nid].x, nodes[nid].y, nodes[nid].z])

            arr_points = np.asarray(arr_points, dtype=np.float64)

            compr_data = compress_data_to_binary(arr_points)
            f.write(f"          {compr_data}")
            
        else:
            for nid in nodes.keys():
                f.write(f' {nodes[nid].x} {nodes[nid].y} {nodes[nid].z}')
        f.write(f'\n        </DataArray>\n')

        f.write(f'      </Points>\n')
        
        #********************************** Cells **********************************
        f.write(f'      <Cells>\n')

        f.write(f'        <DataArray type="Int64" Name="connectivity" format="{coding_type}">\n')
        if binary:
            arr_connectivity = []
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                if no_of_nid == 3:
                    for i in range(no_of_nid):
                        arr_connectivity.append(nodes[elements[eid].attached_nodes[i]].vtk_node_nid)
                elif no_of_nid == 4:
                    for i in range(no_of_nid):
                        arr_connectivity.append(nodes[elements[eid].attached_nodes[i]].vtk_node_nid)
                else:
                    print(f'Length of node unknown!')
                    exit
            
            arr_connectivity = np.asarray(arr_connectivity, dtype=np.int64)
            
            compr_data = compress_data_to_binary(arr_connectivity)
            f.write(f"          {compr_data}")
    
        else:
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
        f.write(f'\n        </DataArray>\n')

        f.write(f'        <DataArray type="Int64" Name="offsets" format="{coding_type}">\n')
        if binary:
            offset = 0
            arr_offset = []
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                offset += no_of_nid
                arr_offset.append(offset)

            arr_offset = np.asarray(arr_offset, dtype=np.int64)

            compr_data = compress_data_to_binary(arr_offset)
            f.write(f"          {compr_data}")            

        else:
            offset = 0
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                offset += no_of_nid
                f.write(f' {offset}')
        f.write(f'\n        </DataArray>\n')

        f.write(f'        <DataArray type="UInt64" Name="types" format="{coding_type}">\n')
        if binary:
            arr_types = []
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                if no_of_nid == 3:
                    arr_types.append(5)
                else:
                    arr_types.append(9)

            arr_types = np.asarray(arr_types, dtype=np.uint64)

            compr_data = compress_data_to_binary(arr_types)
            f.write(f"          {compr_data}")

        else:
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                if no_of_nid == 3:
                    f.write(f' 5')
                else:
                    f.write(f' 9')
        f.write(f'\n        </DataArray>\n')

        f.write(f'      </Cells>\n')
 
        # #*******************************************************************************
        f.write(f'    </Piece>\n')
        f.write(f'  </UnstructuredGrid>\n')
        f.write(f'</VTKFile>\n')

        print(f' Number of Nodes: {no_of_nodes}')
        print(f' Number of Cells: {no_of_cells}')
        print(f' Done writing.')
        print(f' ')
        print(f' File written to "{outputfile}"')

#**********************************************************************************************

if __name__ == '__main__':

    args = ParseArgs()

    inputfile = args.inpath
    outputfile = args.outfile
    binary = args.binary

    if binary:
        coding_type = 'binary'
    else:
        coding_type = 'ascii'

    print(f'')
    print(f'*****************************************************************************')
    print(f'*                                                                           *') 
    print(f'*                            M e s h  2  V T K                              *')
    print(f'*                                                                           *')
    print(f'*****************************************************************************')

    print('')
    if '.bdf' or '.BDF' or '.dat' in inputfile:
        print(f'Converting NASTRAN input deck')
    else:
        print(f'Input deck not supported.')

    print(f'Binary encoding = {binary}')


    print('')
    print(f'Parse input file "{inputfile}" ...')
    nodes, elements = parse_nastran_input(inputfile)

    writeVTKElements(nodes, elements, coding_type, outputfile)

    print(f'')
    print('Done.')