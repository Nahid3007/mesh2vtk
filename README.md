
# **mesh2vtk: FEM to VTK Converter** (still in development 🚧)

`mesh2vtk` is a Python script that converts (currently focused) ANSYS Finite Element Model files into VTK Unstructured Grid (`.vtu`) files. This tool is designed for visualizing and analyzing FEM data in tools like ParaView.

---

## **Features**
- Converts FEM nodes and elements to VTK-compatible formats.
- Maps FEM node and element IDs to the `.vtu` file (optional).
- Outputs in binary or ASCII format.

---

## **Installation**

### **Requirements**
- Python 3.8 or higher
- Python libraries:
  - `vtk`
  - `numpy`

Install the required libraries using:

```bash
pip install vtk numpy
```

---

## **Usage**

Run the script with the following options:

```bash
python mesh2vtk.py --inputfile INPUTFILE --outputfile OUTPUTFILE [options]
```

### **Options**
| **Option**                | **Description**                                                                 |
|---------------------------|---------------------------------------------------------------------------------|
| `--ascii`                 | Output the `.vtu` file in ASCII format (default is binary).                     |
| `--fem_node_string`       | Map FEM node IDs to the `.vtu` file.                                            |
| `--fem_element_string`    | Map FEM element IDs to the `.vtu` file.                                         |

### **Example**

```bash
python mesh2vtk.py --inputfile model.dat --outputfile model.vtu --ascii --fem_node_string --fem_element_string
```

This command:
- Reads `model.dat`.
- Outputs `model.vtu` in ASCII format.
- Includes FEM node and element IDs in the output.

---

## **Supported Element Types**

- Supports the following ANSYS (most used) element types:


| **Element Type**             | **Nodes** | **VTK Cell Type**        |
|-------------------------------|-----------|--------------------------|
| 10-node tetrahedron (ET,187) | 10        | Quadratic tetrahedron    |
| 20-node hexahedron (ET,186)  | 20        | Quadratic hexahedron     |
| 8-node hexahedron (ET,185)  | 8        | Linear hexahedron     |

to be edited ...

---

## **Output Details**

- The `.vtu` file contains:
  - **Points**: Node coordinates.
  - **Cells**: FEM elements mapped to VTK cell types.
  - **Attributes** (optional):
    - FEM node IDs (`FEM_NODE_ID`).
    - FEM element IDs (`FEM_ELEMENT_ID`).

---

## **VTK Summary**

The script outputs key statistics about the generated `.vtu` file, including:
- Number of points (nodes).
- Number of cells (elements).

---

## **Performance**
Execution time is displayed at the end of the run, providing insight into processing efficiency.

---

## **Acknowledgments**
Built using:
- [VTK](https://vtk.org/)
- [ParaView](https://www.paraview.org)


For feedback or contributions, feel free to create an issue or submit a pull request.
