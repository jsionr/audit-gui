# -*- encoding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''
import os

from PyQt4 import uic
from PyQt4.QtCore import QSize
from PyQt4.QtGui import QMainWindow
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QFileDialog

from dialogs.logs import LogsDialog


class MainDialog(QMainWindow):
    
    def __init__(self):
        super(MainDialog, self).__init__()
        self.ui = uic.loadUi("layouts/main.ui", self)
        self.__init_gui()
        self.__init_logic()
        self.__setup()

    def __init_gui(self):
        self.a_new = QAction("New", self)
        self.a_save = QAction("Save", self)
        self.a_load = QAction("Load", self)
        
        
        self.a_analyze_log = QAction("Log analysis and visualization", self)
        
        self.ui.toolbarMain.setIconSize(QSize(24, 24))
        self.ui.toolbarMain.addAction(self.a_new)
        self.ui.toolbarMain.addAction(self.a_save)
        self.ui.toolbarMain.addAction(self.a_load)
        self.ui.toolbarMain.addSeparator()
        self.ui.toolbarMain.addAction(self.a_analyze_log)
    
    def __init_logic(self):
        self.a_analyze_log.triggered.connect(self.__show_logs_dialog)
        self.ui.buttonBrowse.clicked.connect(self.__choose_path)
    
    def __setup(self):
        login = self.user_sys_login()
        self.ui.statusBar.showMessage("Hello %s!" % login, 10000)
        
    def __show_logs_dialog(self):
        dialog = LogsDialog(self)
        dialog.show()
        
    def __choose_path(self):
        path = QFileDialog.getExistingDirectory(self, "Browse...")
        if path:
            self.ui.textPath.setText(path)
        
    def user_sys_login(self):
        return os.environ.get("USERNAME", os.environ.get("LOGIN", "unknown"))
