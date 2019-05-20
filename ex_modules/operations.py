# coding=utf-8

from osgeo import gdal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from PyQt5.QtWidgets import QComboBox
from .classe import *
from .pixel_db import *
import os
import numpy as np


def switch_value(value, From=None, To=None):
    if From:
        From.remove_value(value)
        To.add_value(value)


def create_raster(data, dlg, path, progress_callback, info_source):
    if info_source:
        file_dir = dlg.path_output.text()
        file_name = os.path.normpath(file_dir + path)
        xsize = info_source.RasterXSize
        ysize = info_source.RasterYSize
        geotransform = info_source.GetGeoTransform()
        projecs = info_source.GetProjection()

        os.makedirs(file_dir, exist_ok=True)

        driver = gdal.GetDriverByName('GTiff')
        data_source = driver.Create(file_name, xsize=xsize, ysize=ysize,
                                    bands=1, eType=gdal.GDT_Float32)
        data_source.GetRasterBand(1).WriteArray(data)
        data_source.SetGeoTransform(geotransform)
        data_source.SetProjection(projecs)
        progress_callback.emit('Imagem salva em <br/>---------------------------------------------<i>%s</i>' % file_name)
        return file_name
    else:
        return None


def classificar_textura(textura, dlg, progress_callback, bar_callback):
    dlg.block_inputs(True)

    if textura:
        text = 'Iniciando classificação em: <br/> --------------------------------------------- %s.' \
               % textura.GetDescription()
        progress_callback.emit(text)
        data = textura.GetRasterBand(1).ReadAsArray()
        pixels = PixelDataBase()

        count = 0
        for x in range(data.shape[0]):
            for y in range(data.shape[1]):
                pixels.inserir(['x', 'y', 'textura'], [str(x), str(y), str(data[x][y])])
                bar_callback.emit('Adquirindo valores...', int(count*100/data.size))
                count += 1

        values = pixels.consultar(['textura'])
        for i in range(len(values)):
            values[i] = values[i]['textura']

        # Obtém um vetor ordenado com os valores das texturas
        textures = Classe(valores=sorted(values), nome='Texturas')

        if dlg.box_num_classes.value() == 0:
            # Define o número de classes por Sturges
            K = 2 + int(3.322*np.log10(textures.count_values()))
            progress_callback.emit('Número de classes calculdado: <b>%d</b>' % K)
        else:
            K = dlg.box_num_classes.value()
            progress_callback.emit('Número de classes selecionado: <b>%d</b>' % K)

        # Calcula o tamanho do intervalo para uma classificação inicial das texturas
        tam = (max(textures.get_values()) - min(textures.get_values()))/K

        # Fronteira inicial do primeiro intervalo
        front_0 = min(textures.get_values())

        i = 1
        # Cria uma lista vazia para armazenar as classes
        classes_base = {}
        textures_values_base = textures.get_values().copy()
        aux = textures.get_values().copy()
        while front_0 <= max(textures.get_values())+1:
            if i <= K:
                # cria uma classe vazia
                classes_base[i] = []
                for texture in textures_values_base:
                    if (texture >= front_0)and(texture < front_0 + tam):
                        # Adiciona o valor a classe
                        classes_base[i].append(texture)
                        aux.remove(texture)
                        bar_callback.emit('Preclassificando texturas',
                                           int(100 - len(aux)*100/textures.count_values()))
                textures_values_base = aux.copy()
                i += 1
            front_0 += tam

        classes = {'total': textures.count_values()}
        for classe in classes_base:
            if classes_base[classe]:
                classes[classe] = Classe(valores=classes_base[classe], nome='classe_%d' % classe)
        del classes_base
        progress_callback.emit('Texturas pré-classificadas.')
        progress_callback.emit('Iniciando método de quebras naturais.')

        # Obtem a soma das variâncias
        bar_callback.emit('Classificando...', 0)
        SDAM = textures.sum_sqr_dev()
        del textures

        i = 0
        SDBC = 0
        for classe in classes:
            if classe != 'total':
                SDBC += classes[classe].sum_sqr_dev()
        SDCM = SDAM - SDBC
        GVF_ant = SDCM / SDAM
        progress_callback.emit('GVF inical = %.8f' % GVF_ant)

        while i < 500:
            bar_callback.emit('Classificando...', int(i/5))
            # cria uma cópia para não perder dados caso o GVF piore
            classes_copy = classes.copy()

            # Procura a classe com maior variância
            variance = 0
            index = 0
            for classe in classes_copy:
                if classe != 'total':
                    if variance < classes[classe].get_variance():
                        variance = classes[classe].get_variance()
                        index = classe

            worst_value = classes_copy[index].max_sqr_dev()
            if worst_value == max(classes_copy[index].get_values()):
                try:
                    switch_value(worst_value, From=classes_copy[index], To=classes_copy[index + 1])
                except KeyError:
                    classes_copy[index + 1] = Classe(valores=[], nome='classe_%d' % (index + 1))
                    switch_value(worst_value, From=classes_copy[index], To=classes_copy[index + 1])
            elif worst_value == min(classes_copy[index].get_values()):
                try:
                    switch_value(worst_value, From=classes_copy[index], To=classes_copy[index + 1])
                except KeyError:
                    classes_copy[index + 1] = Classe(valores=[], nome='classe_%d' % (index - 1))
                    switch_value(worst_value, From=classes_copy[index], To=classes_copy[index - 1])

            # Calcula o GVF com a cópia alterada
            SDBC = 0
            for classe in classes_copy:
                if classe != 'total':
                    SDBC += classes_copy[classe].sum_sqr_dev()
            SDCM = SDAM - SDBC
            GVF = SDCM / SDAM

            # Compara os GVF
            # Se o GVF piora encerra o loop
            if GVF > GVF_ant:
                classes = classes_copy
                GVF_ant = GVF
                i += 1
            else:
                break

        progress_callback.emit('Texturas Classificadas.')
        progress_callback.emit('GVF Final = %.8f em %d loops.' % (GVF_ant, i))
        bar_callback.emit('Texturas classificadas', 100)

        dlg.box_text.clear()
        for classe in classes:
            if classe != 'total':
                unique_values = classes[classe].get_unique_values()
                count = 0
                for value in unique_values:
                    pixels.atualizar_classe(classe, value)
                    bar_callback.emit('Atual. pixels de classe %d' % classe, int(count * 100.0 / len(unique_values)))
                    count += 1

                text = '<b>%s</b><br/>' % classes[classe].get_name()
                text += '--------------------------------------------->>>Número de pixels: %d<br/>' \
                        % classes[classe].count_values()
                text += '--------------------------------------------->>>Variância: %.5f<br/>' \
                        % classes[classe].get_variance()
                progress_callback.emit(text)

                path = '/' + classes[classe].get_name() + '.tif'
                class_data = np.zeros((data.shape[0], data.shape[1]), dtype=np.uint8)
                pixs = pixels.consultar('*', 'classe = %s' % str(classe))
                for pix in pixs:
                    class_data[pix['x']][pix['y']] = 1
                    bar_callback.emit('Renderizando classe %d' % classe, int(count*100.0/len(pixs)))
                    count += 1
                create_raster(class_data, dlg, path, progress_callback, textura)
                dlg.box_text.addItem(classes[classe].get_name())
        dlg.box_text.setEnabled(True)
        dlg.Btn_add_class.setEnabled(True)
        bar_callback.emit('Classes Renderizadas', 100)
        dlg.block_inputs(False)
        del textura
        return classes
