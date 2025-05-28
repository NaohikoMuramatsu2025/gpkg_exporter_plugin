from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsProject,
    QgsMapLayer,
    QgsVectorFileWriter,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer
)
from osgeo import gdal
import os
import tempfile
import shutil

class MyGpkgExporter:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
            icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        except Exception:
            icon = QIcon()

        self.action = QAction(icon, "全レイヤをGPKGにエクスポート（構造保持）", self.iface.mainWindow())
        self.action.triggered.connect(self.export_to_gpkg)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&GPKGエクスポーター", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&GPKGエクスポーター", self.action)

    def export_to_gpkg(self):
        output_filename, _ = QFileDialog.getSaveFileName(None, "GPKGファイル保存", "", "GeoPackage Files (*.gpkg)")
        if not output_filename:
            return

        if not output_filename.lower().endswith(".gpkg"):
            output_filename += ".gpkg"

        if os.path.exists(output_filename):
            reply = QMessageBox.question(None, "確認", f"{output_filename} は既に存在します。上書きしますか？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
            os.remove(output_filename)

        result_summary = ""
        used_names = set()
        root = QgsProject.instance().layerTreeRoot()
        layer_info = self.get_layer_paths(root)

        temp_dir = tempfile.mkdtemp()

        try:
            temp_gpkg_files = []

            for full_name, layer in layer_info:
                layer_name = full_name
                i = 1
                while layer_name in used_names:
                    layer_name = f"{full_name}_{i}"
                    i += 1
                used_names.add(layer_name)

                temp_path = os.path.join(temp_dir, f"{layer_name}.gpkg")
                result, error = QgsVectorFileWriter.writeAsVectorFormat(
                    layer,
                    temp_path,
                    "UTF-8",
                    layer.crs(),
                    "GPKG",
                    False,
                    ["layerName=" + layer_name]
                )

                if result != QgsVectorFileWriter.NoError:
                    result_summary += f"{layer_name}: 失敗\n"
                    continue

                temp_gpkg_files.append((temp_path, layer_name))
                result_summary += f"{layer_name}: 保存成功\n"

            # 最終統合
            for i, (temp_path, layer_name) in enumerate(temp_gpkg_files):
                gdal.VectorTranslate(
                    output_filename,
                    temp_path,
                    accessMode="overwrite" if i == 0 else "append",
                    layerName=layer_name
                )

            QMessageBox.information(None, "GPKG出力結果", result_summary)

        finally:
            shutil.rmtree(temp_dir)

    def get_layer_paths(self, group, parent_path=""):
        layer_info = []
        for child in group.children():
            if isinstance(child, QgsLayerTreeGroup):
                group_path = f"{parent_path}{child.name()}_"
                layer_info.extend(self.get_layer_paths(child, group_path))
            elif isinstance(child, QgsLayerTreeLayer):
                layer = child.layer()
                if layer and layer.type() == QgsMapLayer.VectorLayer:
                    full_name = f"{parent_path}{layer.name()}"
                    layer_info.append((full_name, layer))
        return layer_info
