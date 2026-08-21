def get_materials(smd_file):
    materials = []

    with open(smd_file, "r") as file:
        lines = file.readlines()

    in_triangles = False
    line_number = 0

    for line in lines:
        line = line.strip()

        if line == "triangles":
            in_triangles = True
            line_number = 0
            continue

        if line == "end" and in_triangles:
            break

        if not in_triangles or not line:
            continue

        # Every triangle consists of:
        #
        # material
        # vertex
        # vertex
        # vertex
        #
        # Therefore the material is every 4th line.

        if line_number == 0:
            if line not in materials:
                materials.append(line)

        line_number += 1

        if line_number == 4:
            line_number = 0

    return materials