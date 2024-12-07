# **mesh2vtk: FEM to VTK Converter (still in development 🚧)**

`mesh2vtk` is a Python script that converts (currently) ANSYS Finite Element Model files into VTK Unstructured Grid (`.vtu`) files. This tool is designed for visualizing and analyzing FEM data in tools like ParaView.

---

## **Features**
- Converts FEM nodes and elements to VTK-compatible formats.
- Supports the following ANSYS element types:
  - **ET,185: 8-node hexahedral, 6-node prism, 5-node pyramid, 4-node tetrahedral element**.
  - **ET,186: 20-node hexahedral**.
  - **ET,187: 10-node tetrahedral element**.
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




