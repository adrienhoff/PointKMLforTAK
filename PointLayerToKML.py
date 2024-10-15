import xml.etree.ElementTree as ET
import arcpy

input_layer = arcpy.GetParameterAsText(0)
output_kml = arcpy.GetParameterAsText(1)
name_field = arcpy.GetParameterAsText(2)
icon_href = arcpy.GetParameterAsText(3)  # Renamed to avoid conflict with 'icon' element in XML
projected_layer = "layer_projected"

arcpy.management.Project(input_layer, projected_layer, 4326)

def unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&amp;", "&")
    return s

def create_description_data(row, field_names):
    rows_html = ""
    for field_name, field_value in zip(field_names, row):
        field_value_str = str(field_value) if field_value is not None else "N/A"
        rows_html += f"""
        <tr>
          <td>{field_name}</td>
          <td>{field_value_str}</td>
        </tr>
        """
    description_data = f"""
    <![CDATA[
        <html>
            <body>
              <table border="1">
                <tr>
                  <th>Field Name</th>
                  <th>Field Value</th>
                </tr>
                {rows_html}
              </table>
            </body>
        </html>
    ]]>
    """
    return description_data.strip()  # Strip extra newlines

def create_placemark(row, description_data, name_field_index):
    placemark = ET.Element("Placemark")
    print(f"Creating placemark for row: {row}")

    # Set name
    name = ET.SubElement(placemark, "name")
    name.text = str(row[name_field_index]) if row[name_field_index] is not None else "Unnamed"

    # Set visibility
    visibility = ET.SubElement(placemark, "visibility")
    visibility.text = "true"

    # Set description
    description = ET.SubElement(placemark, "description")
    description.text = description_data

    # Set the icon style
    style = ET.SubElement(placemark, "Style")
    icon_style = ET.SubElement(style, "IconStyle")
    icon = ET.SubElement(icon_style, "Icon")
    href = ET.SubElement(icon, "href")
    href.text = icon_href

    # Set coordinates (assuming geometry is the last field)
    try:
        coordinates = ET.SubElement(placemark, "Point")
        coords = row[-1]  # Assuming last field contains coordinates
        if coords and isinstance(coords, tuple) and len(coords) >= 2:
            coordinates_elem = ET.SubElement(coordinates, "coordinates")
            coordinates_elem.text = "{},{},0".format(coords[0], coords[1])
        else:
            print(f"Invalid coordinates for row: {row}")
            return None
    except IndexError as e:
        print(f"Error accessing coordinates from row: {row}, Error: {e}")
        return None

    return placemark

def fetch_feature_layer_data(layer_name):
    with arcpy.da.SearchCursor(layer_name, ['*']) as cursor:
        field_names = [f.name for f in arcpy.ListFields(layer_name)]
        for row in cursor:
            yield row, field_names 

def main():
    feature_layer = projected_layer
    print("Generating KML file...")

    kml = ET.Element("kml",                                       )
    document = ET.SubElement(kml, "Document")
    name = ET.SubElement(document, "name")
    name.text = output_kml
    description = ET.SubElement(document, "description")
    description.text = output_kml

    for row, field_names in fetch_feature_layer_data(feature_layer):
        print(f"Fetched row: {row}")

        # Ensure the row has sufficient data
        if len(row) < 2:
            print(f"Row has insufficient data: {row}")
            continue

        # Find the index of the name_field
        try:
            name_field_index = field_names.index(name_field)
        except ValueError:
            print(f"Field '{name_field}' not found.")
            continue

        # Create description data dynamically based on field names
        description_data = create_description_data(row, field_names)

        placemark = create_placemark(row, description_data, name_field_index)
        if placemark is not None:
            document.append(placemark)

    # Write the XML tree to a file
    try:
        tree = ET.ElementTree(kml)
        tree.write(output_kml, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        print(f"Error writing KML: {e}")

    # Read the generated KML file, unescape the content, and write back
    with open(output_kml, "r") as f:
        kml_content = f.read()
        unescaped_kml_content = unescape(kml_content)

    with open(output_kml, "w") as f:
        f.write(unescaped_kml_content)

    print("KML file generated.")

if __name__ == "__main__":
    main()
