import numpy as np
import argparse
import base64, zlib
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
    parser = argparse.ArgumentParser(description='================== mesh2vtk - A FE mesh converter ==================')
    parser.add_argument("--infile", help="Input FE NASTRAN/OptiStruct file.", required=True, type=str, action='store')
    parser.add_argument("--outfile", help="Name of the converted vtu file.", required=True, type=str, action='store')
    parser.add_argument("--ASCII", help="If defined ascii representation. Default: binary.", required=False, action='store_true', default=False)
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

def fem_nid_str(nodes):
    arr_nid_str = []
    for nid in nodes.keys():
        arr_nid_str.append(nodes[nid].fem_node_id)
        
    return np.asarray(arr_nid_str, dtype=np.int64)

def fem_eid_str(elements):
    arr_eid_str = []
    for eid in elements.keys():
        arr_eid_str.append(elements[eid].fem_elem_id)

    return np.asarray(arr_eid_str, dtype=np.int64)

def points_str(nodes):
    arr_points = []
    for nid in nodes.keys():
        arr_points.extend([nodes[nid].x, nodes[nid].y, nodes[nid].z])

    return np.asarray(arr_points, dtype=np.float64)

def cell_connectivity(elements, nodes):
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
            
    return np.asarray(arr_connectivity, dtype=np.int64)

def cell_offset(elements):
    offset = 0
    arr_offset = []
    for eid in elements.keys():
        no_of_nid = len(elements[eid].attached_nodes)
        offset += no_of_nid
        arr_offset.append(offset)

    return np.asarray(arr_offset, dtype=np.int64)

def cell_types(elements):
    arr_types = []
    for eid in elements.keys():
        no_of_nid = len(elements[eid].attached_nodes)
        if no_of_nid == 3:
            arr_types.append(5)
        else:
            arr_types.append(9)

    return np.asarray(arr_types, dtype=np.uint64)

def compress_data_to_binary(arr):

    m = arr.nbytes//2**15 + 1 # number of chunks

    # divide array in chunks and compress
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

        #************************** VTK Header ********************************
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
            arr_nid_str = fem_nid_str(nodes)
            compr_data = compress_data_to_binary(arr_nid_str)
            f.write(f"          {compr_data}")
        else:
            arr_nid_str = fem_nid_str(nodes)
            f.write(f"          ")
            for i in arr_nid_str:
                f.write(f' {i}')
        f.write(f'\n        </DataArray>\n')
        f.write(f'      </PointData>\n')
        
        #********************************** Cell Data **********************************
        f.write(f'      <CellData>\n')
        f.write(f'        <DataArray type="Int64" Name="FEM_ELEMENT_ID" format="{coding_type}">\n')
        if binary:
            arr_eid_str = fem_eid_str(elements)
            compr_data = compress_data_to_binary(arr_eid_str)
            f.write(f"          {compr_data}")
        else:
            arr_eid_str = fem_eid_str(elements)
            f.write(f"          ")
            for i in arr_eid_str:
                f.write(f' {i}')
        f.write(f'\n        </DataArray>\n')
        f.write(f'      </CellData>\n')
        
        #********************************** Points *********************************
        f.write(f'      <Points>\n')
        f.write(f'        <DataArray type="Float64" Name="Points" NumberOfComponents="3" format="{coding_type}">\n')
        if binary:
            arr_points = points_str(nodes)
            compr_data = compress_data_to_binary(arr_points)
            f.write(f"          {compr_data}")     
        else:
            arr_points = points_str(nodes)
            f.write(f"          ")
            for i in arr_points:
                f.write(f' {i}')
        f.write(f'\n        </DataArray>\n')
        f.write(f'      </Points>\n')
        
        #********************************** Cells **********************************
        f.write(f'      <Cells>\n')
        f.write(f'        <DataArray type="Int64" Name="connectivity" format="{coding_type}">\n')
        if binary:
            arr_connectivity = cell_connectivity(elements, nodes)
            compr_data = compress_data_to_binary(arr_connectivity)
            f.write(f"          {compr_data}")
        else:
            arr_connectivity = cell_connectivity(elements, nodes)
            f.write(f"          ")
            for i in arr_connectivity:
                f.write(f' {i}')
        f.write(f'\n        </DataArray>\n')

        f.write(f'        <DataArray type="Int64" Name="offsets" format="{coding_type}">\n')
        if binary:
            arr_offset = cell_offset(elements)
            compr_data = compress_data_to_binary(arr_offset)
            f.write(f"          {compr_data}")            
        else:
            arr_offset = cell_offset(elements)
            f.write(f"          ")
            for i in arr_offset:
                f.write(f' {i}')
        f.write(f'\n        </DataArray>\n')

        f.write(f'        <DataArray type="UInt64" Name="types" format="{coding_type}">\n')
        if binary:
            arr_types = cell_types(elements)
            compr_data = compress_data_to_binary(arr_types)
            f.write(f"          {compr_data}")
        else:
            arr_types = cell_types(elements)
            f.write(f"          ")
            for i in arr_types:
                f.write(f' {i}')
        f.write(f'\n        </DataArray>\n')
        f.write(f'      </Cells>\n')
 
        #*******************************************************************************
        f.write(f'    </Piece>\n')
        f.write(f'  </UnstructuredGrid>\n')
        f.write(f'</VTKFile>\n')

        print(f' Number of Points : {no_of_nodes}')
        print(f' Number of Cells  : {no_of_cells}')
        print(f' ')
        print(f' File written to "{outputfile}"')
   
if __name__ == '__main__':

    args = ParseArgs()

    inputfile  = args.infile
    outputfile = args.outfile
    ascii_      = args.ASCII

    if ascii_ == False:
        coding_type = 'binary'
        binary = True
    else:
        coding_type = 'ascii'
        binary = False
   
    print(f'') 
    print(f'==================================================')  
    print(f'                     _     ____        _   _      ')
    print(f' _ __ ___   ___  ___| |__ |___ \__   _| |_| | __  ')
    print(f"| '_ ` _ \ / _ \/ __| '_ \  __) \ \ / / __| |/ /  ")
    print(f'| | | | | |  __/\__ \ | | |/ __/ \ V /| |_|   <   ')
    print(f'|_| |_| |_|\___||___/_| |_|_____| \_/  \__|_|\_\  ')
    print(f'')                                                            
    print(f'==================================================') 

    print('')
    if '.bdf' or '.BDF' or '.dat' in inputfile:
        print(f'Input deck type    : NASTRAN')
    else:
        print(f'Input deck not supported.')

    print(f'Binary compression : {binary}')

    print('')
    print(f'Parse input file "{inputfile}" ...')
    
    nodes, elements = parse_nastran_input(inputfile)

    writeVTKElements(nodes, elements, coding_type, outputfile)

    print(f'')
    print('Done.')