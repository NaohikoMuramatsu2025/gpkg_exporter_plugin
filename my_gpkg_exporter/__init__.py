def classFactory(iface):
    print("===> GPKG Exporter: __init__.py 読み込み成功")  
    from .my_gpkg_exporter import MyGpkgExporter
    return MyGpkgExporter(iface)
