from qgis.PyQt.QtWidgets import QInputDialog, QComboBox
from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField
from qgis.PyQt.QtCore import QVariant
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

def remove_spikes(geometry, angle_threshold):
    new_points = []
    points = geometry.asPolygon()[0]
    n = len(points)
    for i in range(n):
        p0 = points[i - 1]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        angle = calculate_angle(p0, p1, p2)
        if angle >= angle_threshold:
            new_points.append(QgsPointXY(p1))
    return QgsGeometry.fromPolygonXY([new_points])

def main():
    # Step 1: Get the layer from the user
    layers = [layer for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsVectorLayer)]
    if not layers:
        print("No vector layers found in the project.")
        return

    items = [layer.name() for layer in layers]
    item, ok = QInputDialog.getItem(None, "Select Layer", "Layer:", items, 0, False)
    if not ok or not item:
        return

    selected_layer = layers[items.index(item)]
    
    if selected_layer.geometryType() != QgsWkbTypes.PolygonGeometry:
        print("Selected layer is not a polygon layer.")
        return

    # Step 2: Process the features
    angle_threshold, ok = QInputDialog.getDouble(None, "Angle Threshold", "Enter the angle threshold:", 10, 0, 180, 1)
    if not ok:
        return
    
    new_features = []
    for feature in selected_layer.getFeatures():
        geometry = feature.geometry()
        new_geometry = remove_spikes(geometry, angle_threshold)
        new_feature = QgsFeature(feature)
        new_feature.setGeometry(new_geometry)
        new_features.append(new_feature)

    # Step 3: Create a new layer and add the processed features
    new_layer = QgsVectorLayer("Polygon?crs={}".format(selected_layer.crs().authid()), 
                               "{}_unspiked".format(selected_layer.name()), "memory")
    new_layer_data_provider = new_layer.dataProvider()
    new_layer_data_provider.addAttributes(selected_layer.fields())
    new_layer.updateFields()
    
    new_layer_data_provider.addFeatures(new_features)

    # Step 4: Save the new layer as a GeoPackage
    QgsVectorFileWriter.writeAsVectorFormat(new_layer, "/path/to/save/unspiked_layer.gpkg", 
                                            "UTF-8", selected_layer.crs(), "GPKG")
    QgsProject.instance().addMapLayer(new_layer)

main()
