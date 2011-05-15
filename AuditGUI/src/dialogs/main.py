# -*- encoding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''
import os
import logging

from PyQt4 import uic
from PyQt4.QtCore import QSize
from PyQt4.QtGui import QMainWindow
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QFileDialog

from dialogs.logs import LogsDialog
from logic import auditwrap


log = logging.getLogger(__name__)


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

        self.__rule_editor = RuleEditor(self)

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


class RuleEditor(object):

    def __init__(self, dialog):
        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__install()

    def __install(self):
        self.__ui.buttonAdd.clicked.connect(self.__add_rule)

    def __add_rule(self):
        log.info("Adding new rule...")

        name = unicode(self.__ui.textName.text())
        path = unicode(self.__ui.textPath.text())
        fields = unicode(self.__ui.textRule.text()).strip() or None

        perm = []
        if self.__ui.checkR.isChecked():
            perm.append("r")
        if self.__ui.checkW.isChecked():
            perm.append("w")
        if self.__ui.checkX.isChecked():
            perm.append("x")
        if self.__ui.checkA.isChecked():
            perm.append("a")

        try:
            rule = auditwrap.FileWatchRule(name, path, "".join(perm), fields)
            auditwrap.addActiveRule(rule)
        except auditwrap.AuditwrapError, e:
            log.error("Cannot add rule: %s" % e)
        else:
            log.info("Added rule %s" % name)




























