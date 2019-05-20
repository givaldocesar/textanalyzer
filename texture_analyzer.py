# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TextureAnalyzer
                                 A QGIS plugin
 Procura identificar as texturas presentes em um dado conjuntos de imagens raster.
 Gerado por Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-05-02
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Givaldo Cesar/DECart/UFPE
        email                : givaldocesar@live.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   Este programa é um software grátis; você pode redistribuir e/ou       *
 *   modificar sob os termos da GNU General Public Licens como publicado   *
 *   pela Free Software Foundation; versão 2 da Licença, ou (a sua opção)  *
 *   qualquer versão posterior.                                            *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
from qgis.core import QgsProject, QgsRasterLayer
from .ex_modules import *

# Inicializa os recursos Qt do arquivo resources.py
from .resources import *

# Importa o código para a janela de diálogo
from .texture_analyzer_dialog import TextureAnalyzerDialog
import os.path


class TextureAnalyzer:
    def __init__(self, iface):
        # Salva a referência  para a interface QGIS
        self.iface = iface
        # Inicializa o diretório de plugins
        self.plugin_dir = os.path.dirname(__file__)
        # Inicializa a localidade
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'TextureAnalyzer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declara os atributos da instância
        self.actions = []
        self.menu = self.tr(u'&Texture Analyzer')

        # Checa se o plugin foi iniciado pela primeira vez na sessão atual do QGIS
        # Deve ser posto em initGui() para sobreviver ao reinicio do plugin
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('TextureAnalyzer', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adiciona o ícone do plugin a barra de ferramentas
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        icon_path = ':/plugins/texture_analyzer/images/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Iniciar'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # será atribuido False em run()
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Texture Analyzer'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        # Cria a janela com os elementos (depois da tradução) e mantém a referÊncia
        # Só cria a GUI uma vez na execução, então irá carregar apenas quando o plugin for iniciado
        if self.first_start:
            self.first_start = False
            self.dlg = TextureAnalyzerDialog()

        # Adiciona a informação as comboboxs
        self.dlg.att_comboboxes()

        # Exibe a janela
        self.dlg.show()

        # Inicialização
        self.dlg.logboard.clear()
        self.dlg._att_log('Iniciado!')
        self.dlg.log_label.setText('')
        self.dlg.block_inputs(False)
        self.dlg.progressBar.setValue(0)
        self.dlg.box_text.clear()
        self.dlg.box_text.setEnabled(False)
        self.dlg.textures = {}
        self.dlg.start = False

        # Executa o evento de loop da janela
        result = self.dlg.exec_()

