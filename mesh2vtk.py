import numpy as np
import sys
from base64 import b64encode
import zlib
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

def compress_data_to_binary(arr_, d_type):
    
    arr = np.array(arr_, dtype=d_type)
    
    m = arr.nbytes//2**15 + 1
    
    compr_chunk = []
    for i in range(m):
        if i < m-1:
            chunk = zlib.compress(arr[i*4096:(i+1)*4096])
            compr_chunk.append(chunk)
            # print(f'Chunk_{i}')
        else:
            size_last_chunk = arr[i*4096::].nbytes
            chunk = zlib.compress(arr[i*4096::])
            compr_chunk.append(chunk)
            # print(f'Chunk_{i}')

    head_arr = np.concatenate( ( [m, 2**15, size_last_chunk], [len(compr_chunk[i]) for i in range(len(compr_chunk))] ),dtype='i8')

    b64_head_arr = b64encode(head_arr.tobytes())

    sum = compr_chunk[0]
    for i in range(1,len(compr_chunk)):
        sum = sum + compr_chunk[i]

    b64_arr = b64encode(sum)

    return (b64_head_arr + b64_arr).decode('utf-8')
   
def writeVTKElements(nodes, elements, coding_type, outputfile):
    
    print(f'\nWriting VTK Elements ...')
    
    with open(outputfile,'w') as f:

        #************************** Write VTK Lines ********************************
        f.write(f'<?xml version="1.0"?>\n')

        if coding_type == "binary":
            f.write(f'<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian" header_type="UInt64" compressor="vtkZLibDataCompressor">\n')
        elif coding_type == "ascii":
            f.write(f'<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian" header_type="UInt64">\n')

        f.write(f'<UnstructuredGrid>\n')

        no_of_nodes = len(nodes)
        no_of_cells = len(elements)

        f.write(f'<Piece NumberOfPoints="{no_of_nodes}" NumberOfCells="{no_of_cells}">\n')
        
        #********************************** Points *********************************
        f.write(f'<Points>\n')

        f.write(f'<DataArray type="Float64" Name="Points" NumberOfComponents="3" format="{coding_type}">\n')
        if coding_type == "binary":
            arr_points = []
            for nid in nodes.keys():
                arr_points.extend([nodes[nid].x, nodes[nid].y, nodes[nid].z])

            compr_data = compress_data_to_binary(arr_points, 'float64')
            f.write(f"{compr_data}")
            
        elif coding_type == "ascii":
            for nid in nodes.keys():
                f.write(f' {nodes[nid].x} {nodes[nid].y} {nodes[nid].z}')
        f.write(f'\n</DataArray>\n')

        f.write(f'</Points>\n')
        #*******************************************************************************
        
        #********************************** Cells **********************************
        f.write(f'<Cells>\n')

        f.write(f'<DataArray type="Int64" Name="connectivity" format="{coding_type}">\n')
        if coding_type == "binary":
            arr_connectivity = []
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                if no_of_nid == 3:
                    for i in range(no_of_nid):
                        arr_connectivity.append(nodes[elements[eid].attached_nodes[i]].vtk_node_nid)
                elif no_of_nid == 4:
                    for i in range(no_of_nid):
                        arr_connectivity.append(nodes[elements[eid].attached_nodes[i]].vtk_node_nid)
                        #arr = np.array(arr_connectivity, dtype='float64')
                else:
                    print(f'Length of node unknown!')
                    exit
            
            compr_data = compress_data_to_binary(arr_connectivity, 'int64')
            f.write(f"{compr_data}")
    
        elif coding_type == "ascii":
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

        f.write(f'<DataArray type="Int64" Name="offsets" format="{coding_type}">\n')
        if coding_type == "binary":
            offset = 0
            arr_offset = []
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                offset += no_of_nid
                arr_offset.append(offset)

            compr_data = compress_data_to_binary(arr_offset, 'int64')
            f.write(f"{compr_data}")            

        elif coding_type == "ascii":
            offset = 0
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                offset += no_of_nid
                f.write(f' {offset}')
        f.write(f'\n</DataArray>\n')

        f.write(f'<DataArray type="UInt8" Name="types" format="{coding_type}">\n')
        if coding_type == "binary":
            arr_types = []
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                if no_of_nid == 3:
                    arr_types.append(5)
                else:
                    arr_types.append(9)

            compr_data = compress_data_to_binary(arr_types, 'uint8')
            f.write(f"{compr_data}")

        elif coding_type == "ascii":
            for eid in elements.keys():
                no_of_nid = len(elements[eid].attached_nodes)
                if no_of_nid == 3:
                    f.write(f' 5')
                else:
                    f.write(f' 9')
        f.write(f'\n</DataArray>\n')

        f.write(f'</Cells>\n')
        #*******************************************************************************

        # #********************************** Point Data **********************************
        # f.write(f'<PointData>\n')

        # f.write(f'<Array type="Int32" Name="FEM_NODE_ID" format="{coding_type}">\n')
        # if coding_type == 'binary':
        #     arr_nid_str = []
        #     for nid in nodes.keys():
        #         arr_nid_str.append(nodes[nid].fem_node_id)

        #     compr_data = compress_data_to_binary(arr_nid_str, 'uint32')
        #     f.write(f"{compr_data}")

        # elif coding_type == 'ascii':
        #     for nid in nodes.keys():
        #         f.write(f' {nodes[nid].fem_node_id}')
        # f.write(f'\n</Array>\n')
        
        # f.write(f'</PointData>\n')
        #********************************************************************************

        # #********************************** Cell Data **********************************
        # f.write(f'<CellData>\n')
        
        # f.write(f'<Array type="Int32" Name="FEM_ELEMENT_ID" format="{coding_type}">\n')
        # if coding_type == "binary":
        #     arr_eid_str = []
        #     for eid in elements.keys():
        #         arr_eid_str.append(elements[eid].fem_elem_id)

        #     arr = np.array(arr_eid_str, dtype='int32')
        #     m = arr.nbytes//2**15 + 1

        #     compr_chunk = []
        #     for i in range(m):
        #         if i < m-1:
        #             chunk = zlib.compress(arr[i*4096:(i+1)*4096])
        #             compr_chunk.append(chunk)
        #             # print(f'Chunk_{i}')
        #         else:
        #             size_last_chunk = arr[i*4096::].nbytes
        #             chunk = zlib.compress(arr[i*4096::])
        #             compr_chunk.append(chunk)
        #             # print(f'Chunk_{i}')

        #     head_arr = np.concatenate( ( [m, 2**15, size_last_chunk], [len(compr_chunk[i]) for i in range(len(compr_chunk))] ),dtype='int64')

        #     b64_head_arr = b64encode(head_arr.tobytes())

        #     sum = compr_chunk[0]
        #     for i in range(1,len(compr_chunk)):
        #         sum = sum + compr_chunk[i]

        #     b64_arr = b64encode(sum)
        #     f.write(f"{(b64_head_arr + b64_arr).decode('utf-8')}")

        # elif coding_type == "ascii":
        #     for eid in elements.keys():
        #         f.write(f' {elements[eid].fem_elem_id}')
        # f.write(f'\n</Array>\n')

        # f.write(f'</CellData>\n')
        # #********************************************************************************

        f.write(f'</Piece>\n')
        f.write(f'</UnstructuredGrid>\n')
        f.write(f'</VTKFile>\n')

        print(f' Done writing.')
        print(f' Number of Nodes: {no_of_nodes}')
        print(f' Number of Cells: {no_of_cells}')
        print(f' File written to "{outputfile}"')

#**********************************************************************************************

if __name__ == '__main__':

    inputfile = str(sys.argv[1])
    outputfile = str(sys.argv[2])
    coding_type = str(sys.argv[3])

    print(f'*****************************************************************************')
    print(f'*                                                                           *') 
    print(f'*                            m e s h  2  v t k                              *')
    print(f'*                                                                           *')
    print(f'*****************************************************************************')


    print('')
    print(f'Parse input file "{inputfile}" ...')
    nodes, elements = parse_nastran_input(inputfile)

    writeVTKElements(nodes, elements, coding_type, outputfile)

    print(f'')
    print('Done.')