from qgis.PyQt.QtWidgets import QInputDialog, QFileDialog
from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsWkbTypes
import numpy as np

def calculate_angle(p0, p1, p2):
    v1 = np.array(p0) - np.array(p1)
    v2 = np.array(p2) - np.array(p1)
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 < 1e-10 or norm_v2 < 1e-10:
        return 180.0
    cosine_angle = np.clip(dot_product / (norm_v1 * norm_v2), -1.0, 1.0)
    return np.degrees(np.arccos(cosine_angle))

def filter_polygon(geometry, min_angle):
    coords = geometry.asPolygon()[0]
    new_coords = []
    spikes_removed = 0

    def check_angle(prev, curr, next):
        angle = calculate_angle(prev, curr, next)
        if angle >= min_angle:
            return curr, 0
        return None, 1

    for i in range(len(coords) - 1):
        prev, curr, next = coords[i - 1], coords[i], coords[(i + 1) % (len(coords) - 1)]
        point, spike_removed = check_angle(prev, curr, next)
        if point is not None:
            new_coords.append(point)
        spikes_removed += spike_removed

    if len(new_coords) >= 3:
        start_end_point, spike_removed = check_angle(new_coords[-1], new_coords[0], new_coords[1])
        if start_end_point is None:
            midpoint = tuple((np.array(new_coords[-1]) + np.array(new_coords[1])) / 2)
            new_coords[0] = midpoint
            spikes_removed += spike_removed
    else:
        return QgsGeometry.fromPolygonXY([[]]), spikes_removed

    new_coords.append(new_coords[0])
    filtered_geometry = QgsGeometry.fromPolygonXY([new_coords])
    return filtered_geometry, spikes_removed

def main():
    layers = [layer for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsVectorLayer)]
    if not layers:
        print("No vector layers found in the project.")
        return

    items = [layer.name() for layer in layers]
    item, ok = QInputDialog.getItem(None, "Select Layer", "Layer:", items, 0, False)
    if not ok or not item:
        return

    selected_layer = layers[items.index(item)]
    
    if selected_layer.geometryType() != QgsWkbTypes.PolygonGeometry and selected_layer.geometryType() != QgsWkbTypes.MultiPolygonGeometry:
        print("Selected layer is not a polygon or multipolygon layer.")
        return

    angle_threshold, ok = QInputDialog.getDouble(None, "Angle Threshold", "Enter the angle threshold:", 10, 0, 180, 1)
    if not ok:
        return
    
    new_features = []
    for feature in selected_layer.getFeatures():
        geometry = feature.geometry()
        new_geometry, _ = filter_polygon(geometry, angle_threshold)
        new_feature = QgsFeature(feature)
        new_feature.setGeometry(new_geometry)
        new_features.append(new_feature)

    new_layer = QgsVectorLayer(f"Polygon?crs={selected_layer.crs().authid()}", f"{selected_layer.name()}_unspiked", "memory")
    new_layer_data_provider = new_layer.dataProvider()
    new_layer_data_provider.addAttributes(selected_layer.fields())
    new_layer.updateFields()
    new_layer_data_provider.addFeatures(new_features)

    QgsProject.instance().addMapLayer(new_layer)

    export, ok = QInputDialog.getItem(None, "Export to file", "Do you want to export the result to a file?", ["Yes", "No"], 0, False)
    if ok and export == "Yes":
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Layer", "", "GeoPackage (*.gpkg)")
        if file_path:
            QgsVectorFileWriter.writeAsVectorFormat(new_layer, file_path, "UTF-8", selected_layer.crs(), "GPKG")

main()
