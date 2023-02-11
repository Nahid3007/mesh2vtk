import numpy as np
import networkx as nx
from itertools import combinations

def parse_nastran_input(inputfile):

    with open(inputfile) as f:
        lines = [line.strip() for line in f]

    grid_tupels = {}

    for line in lines:
        if line.startswith('CTRIA3'):
            elem_id = line[8:16].strip()
            n1 = line[24:32].strip()
            n2 = line[32:40].strip()
            n3 = line[40:48].strip()

            grid_tupels[elem_id] = [(n1,n2), (n2,n3), (n3,n1)]

        elif line.startswith('CQUAD4'):
            elem_id = line[8:16].strip()
            n1 = line[24:32].strip()
            n2 = line[32:40].strip()
            n3 = line[40:48].strip()
            n4 = line[48:56].strip()

            grid_tupels[elem_id] = [(n1,n2), (n2,n3), (n3,n4), (n4,n1)]

    return grid_tupels

def create_part_ids(grid_tupels):

    # Create a graph
    G = nx.Graph()

    # Add nodes to the graph with attributes
    for eid,attached_nodes_tupels in grid_tupels.items():
        G.add_node(eid, attribute=attached_nodes_tupels)


    # Iterate through all pairs of nodes in the graph
    for node1, node2 in combinations(G.nodes(), 2):
        
        # Check if the nodes have the same attribute
        attr_n1 = [tuple(sorted(list(tups))) for tups in G.nodes[node1]['attribute']]
        attr_n2 = [tuple(sorted(list(tups))) for tups in G.nodes[node2]['attribute']]
        if any(tuple in attr_n1 for tuple in attr_n2):
            G.add_edge(node1, node2) # Add an edge between the nodes

    # Get the number of connected components in the graph
    num_connected_components = nx.number_connected_components(G)
    print("Number of connected components:", num_connected_components)

    part_ids = {}
    # map the nodes in each connected subgraph with an assosicated part id number
    for i, subgraph in enumerate(nx.connected_components(G)):
        part_ids[i+1] = list(subgraph)
        
    return part_ids

grid_tupels = parse_nastran_input('nastran_test_model.bdf')

part_ids = create_part_ids(grid_tupels)

print('\nPart IDs:')
print(part_ids)