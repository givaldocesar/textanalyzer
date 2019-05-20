# -*- coding: utf-8 -*-

from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool
from PyQt5.QtGui import QPixmap
from qgis.utils import iface
from qgis.core import QgsProject, QgsRasterLayer
from datetime import datetime
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from .ex_modules import *
import numpy as np
import matplotlib.pyplot as plt

# Isto carrega seu arquivo .ui para que o PyQt possa povoar seu plugin com os elementos do Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'texture_analyzer_dialog_base.ui'))

file_filter = '''Todos os arquivos (*);; 
                 TIFF (*.tiff; *.tif; *.geotiff; *.geotif);;
                 JPEG (*.jpg; *.jpeg);;
                 PNG  (*.png)'''


class TextureAnalyzerDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(TextureAnalyzerDialog, self).__init__(parent)
        self.setupUi(self)

        QgsProject.instance().layerWasAdded.connect(self.att_comboboxes)
        QgsProject.instance().layerRemoved.connect(self.att_comboboxes)

        self.start = False
        self.mask = 0
        self.class_textures = {}
        self.values_textures = []
        self.threadpool = QThreadPool()

        QtWidgets.QMessageBox.warning(self, 'AVISO!!!', 'Utilizar imagens com extensões diferentes resultará ' +
                                                        'em dados inapropriados e falha no processamento.')

        if 'Windows' in os.environ['OS']:
            self.path_output.setText(os.environ['HOME'] + '\Desktop\Results')

        self.box_bands = [self.box_banda_1, self.box_banda_2, self.box_banda_3, self.box_banda_4, self.box_banda_5,
                          self.box_banda_6, self.box_banda_7]

        for box in self.box_bands:
            box.setToolTip('Necessário carregar as imagens no QGIS para que se possa utilizá-las.')
        self.box_num_classes.setToolTip('Deixar ZERO para cálculo automático de número de classes.')

        self.box_text.activated.connect(self._att_text_information)

        # Funções dos botões
        self.Btn_export.clicked.connect(self._export)
        self.Btn_clear.clicked.connect(self.logboard.clear)
        self.Btn_compute.clicked.connect(self._compute)
        self.Btn_classify.clicked.connect(self._classify)
        self.Btn_quit.clicked.connect(self.close)
        self.Btn_output.clicked.connect(self._set_output_path)
        self.Btn_add_class.clicked.connect(self._add_raster_layer)

        # Logos
        self.lasenso.setPixmap(QPixmap(':/plugins/texture_analyzer/images/lasenso.png'))
        self.decart.setPixmap(QPixmap(':/plugins/texture_analyzer/images/decart.png'))
        self.ctg.setPixmap(QPixmap(':/plugins/texture_analyzer/images/ctg.png'))
        self.ufpe.setPixmap(QPixmap(':/plugins/texture_analyzer/images/ufpe.png'))

        self.canvas = None

    def _att_log(self, text):
        time = datetime.now().strftime('%d/%m/%Y %H:%M:%S.%f')
        msg = '<b>' + time + '</b>' + ' --- ' + text
        self.logboard.append(msg)
        del time

    def _att_logbar(self, text, progress):
        self.log_label.setText(text)
        self.progressBar.setValue(progress)

    def att_comboboxes(self):
        # Obtém as camadas ativas no projeto
        layers = QgsProject.instance().mapLayers()
        layers_names = ['']

        # Separa as camadas rasters do projeto
        for layer in layers:
            if type(layers[layer]) == QgsRasterLayer:
                layers_names.append(layers[layer].name())

        for box in self.box_bands:
            box.clear()
            box.addItems(layers_names)
        del layers, layers_names

    def _att_text_information(self, index):
        classe = self.class_textures[index+1]
        self.class_name.setText(classe.get_name())
        self.label_num_pix.setText(str(classe.count_values()))
        self.label_med.setText('%.3f' % classe.get_media())
        self.label_var.setText('%.3f' % classe.get_variance())

    def _add_raster_layer(self):
        classe = self.class_textures[self.box_text.currentIndex() + 1]
        path = self.path_output.text() + '\%s.tif' % classe.get_name()
        if not iface.addRasterLayer(path):
            QtWidgets.QMessageBox.warning(self, 'AVISO!!!', 'O arquivo de imagem não se encontra no diretório de saída.')

    def _add_texture_band(self, filename):
        if filename:
            iface.addRasterLayer(filename)

    def gen_bar_plot(self):
        # Gráficos
        cols = []
        values = []
        for classe in self.class_textures:
            if classe != 'total':
                cols.append(self.class_textures[classe].get_name())
                values.append((self.class_textures[classe].count_values())*100.0/self.class_textures['total'])

        figure = Figure()
        plotter = figure.add_subplot(1, 1, 1)
        plotter.set_xlabel('%')
        plotter.set_yticklabels(cols, fontdict={'size': 8})
        plotter.barh(cols, values)

        self.mplvl.removeItem(self.mplvl.itemAt(0))
        canvas = FigureCanvas(figure)
        self.mplvl.addWidget(canvas)

    def set_textures(self, textures):
        self.class_textures = textures

    def block_inputs(self, value):
        self.Btn_compute.setEnabled(not value)
        self.Btn_classify.setEnabled(not value)
        for box in self.box_bands:
            box.setEnabled(not value)

    def _export(self):
        log = self.logboard.toPlainText()
        file_path, type_file = QtWidgets.QFileDialog.getSaveFileName(self, 'Salvar em: ', '', 'TXT (*.txt)')
        if file_path:
            arq = open(file_path, 'w')
            arq.writelines(log)
            arq.close()
            del arq
        del log, file_path, type_file

    def _set_output_path(self):
        file_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Salvar em:', os.environ['HOME'])
        self.path_output.setText(file_path)
        del file_path

    def _compute(self):
        self.mask = self.box_mask.value()
        self._att_log('Tamanho da máscara: <b>%d x %d<b>' % (self.mask, self.mask))

        if self.start:
            self._att_log('---------------<b>Reiniciado</b>----------------')

        _worker = Worker(self._compute_all_textures)
        _worker.signals.progress.connect(self._att_log)
        _worker.signals.progress_bar.connect(self._att_logbar)
        _worker.signals.result.connect(self._add_texture_band)
        self.threadpool.start(_worker)
        self.start = True

    def _compute_all_textures(self, progress_callback, bar_callback):
        self.block_inputs(True)

        textures = []
        data_source = None
        for i in range(1, 8):
            band_name = self.box_bands[i-1].currentText()
            if band_name:
                progress_callback.emit('Obtendo dados da imagem <b>%d</b>...' % i)
                layer = QgsProject.instance().mapLayersByName(band_name)[0]
                data_source = gdal.Open(layer.dataProvider().dataSourceUri())
                for n in range(1, data_source.RasterCount+1):
                    layer_data = data_source.GetRasterBand(n).ReadAsArray()
                    if n == 1:
                        progress_callback.emit('%d pixels obtidos!' % layer_data.size)
                    progress_callback.emit('Calculando texturas da imagem <b>%d</b> banda <b>%d</b>...' % (i, n))
                    textures.append(self._compute_texture(layer_data, bar_callback, i))

        if textures:
            try:
                texture_band = np.zeros(textures[0].shape)
                for texture in textures:
                    texture_band += texture**2
            except ValueError:
                progress_callback.emit('<font color="#990000">Imagens com extensões diferentes.</font>')
            else:
                texture_band = np.sqrt(texture_band)
                bar_callback.emit('Texturas Calculadas', 100)
                self.block_inputs(False)
                self.block_inputs(False)
                for texture in textures:
                    self.values_textures.append(texture[1])
                return create_raster(texture_band, self, "\Texture_Band.tif", progress_callback, data_source)
        else:
            self.block_inputs(False)
            return None

    def _compute_texture(self, band_data, bar_callback, band):
        bar_callback.emit('Calculando banda %d' % band, 0)
        width = band_data.shape[0]
        heigth = band_data.shape[1]
        texture = np.zeros((width, heigth), dtype=np.float32)
        count = 1
        for x in range(width):
            for y in range(heigth):
                # Encontra os valores dos pixels próximos
                vizinhos = []
                for i in range(self.mask):
                    for j in range(self.mask):
                        if (x+i-1 >= 0)and(x+i-1 < width)and(y+j-1 >= 0)and(y+j-1 < heigth):
                            vizinhos.append(band_data[x+i-1][y+j-1])

                # Computa a textura
                median = np.median(vizinhos) # Mediana
                mean = np.mean(vizinhos)     # Média
                meddev = 0                   # Desvio-Mediano
                stddev = np.std(vizinhos)    # Desvio-padrão
                for value in vizinhos:
                    meddev += abs(value - median)
                meddev = meddev/len(vizinhos)

                text = np.sqrt(mean**2 + median**2 + stddev**2 + meddev**2)

                texture[x][y] = text
                bar_callback.emit('Calculando banda %d' % band, int(count*100/band_data.size))
                count += 1
        return texture

    def _classify(self):
        texture_band = gdal.Open(self.path_output.text() + "\Texture_Band.tif")
        if texture_band:
            _worker = Worker(classificar_textura, texture_band, self)
            _worker.signals.progress.connect(self._att_log)
            _worker.signals.progress_bar.connect(self._att_logbar)
            _worker.signals.result.connect(self.set_textures)
            _worker.signals.finished.connect(self.gen_bar_plot)
            self.threadpool.start(_worker)
        else:
            answer = QtWidgets.QMessageBox.question(self, 'AVISO!!!',
                                                    'Banda de textura não encontrada. Deseja encontrá-la??',
                                                    QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)

            if answer == QtWidgets.QMessageBox.Yes:
                filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Abrir banda de textura: ', '', file_filter)
                if filepath:
                    texture_band = gdal.Open(filepath)
                    _worker = Worker(classificar_textura, texture_band, self)
                    _worker.signals.progress.connect(self._att_log)
                    _worker.signals.progress_bar.connect(self._att_logbar)
                    _worker.signals.result.connect(self.set_textures)
                    _worker.signals.finished.connect(self.gen_bar_plot)
                    self.threadpool.start(_worker)
