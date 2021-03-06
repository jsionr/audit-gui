# -*- encoding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''
import os
import logging

from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtCore import QObject
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import QSize
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QMainWindow
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QFileDialog
from PyQt4.QtGui import QMessageBox

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
        self.a_new = QAction(QIcon("layouts/icons/new.png"), "New", self)
        self.a_save = QAction(QIcon("layouts/icons/save.png"), "Save", self)
        self.a_load = QAction(QIcon("layouts/icons/load.png"), "Load", self)

        self.a_analyze_log = QAction(QIcon("layouts/icons/logs.png"),
                                     "Log analysis and visualization", self)

        self.ui.toolbarMain.setIconSize(QSize(24, 24))
        self.ui.toolbarMain.addAction(self.a_new)
        self.ui.toolbarMain.addAction(self.a_save)
        self.ui.toolbarMain.addAction(self.a_load)
        self.ui.toolbarMain.addSeparator()
        self.ui.toolbarMain.addAction(self.a_analyze_log)

        self.ui.tableRules.setColumnWidth(0, 150)
        self.ui.tableRules.setColumnWidth(1, 300)
        self.ui.tableRules.setColumnWidth(2, 100)

    def __init_logic(self):
        self.a_analyze_log.triggered.connect(self.__show_logs_dialog)
        self.ui.buttonBrowse.clicked.connect(self.__choose_path)

        self.rule_editor = RuleEditor(self)

        self.rule_viewer = RuleViewer(self)
        self.rule_viewer.refresh()

        def row_selected(row):
            self.rule_editor.load_rule(self.rule_viewer.get_rule(row))

        self.rule_viewer.onRowSelected.connect(row_selected)

        self.__refresher = QTimer(self)
        self.__refresher.timeout.connect(self.rule_viewer.refresh)
        self.__refresher.start(60000)

    def __setup(self):
        login = self.user_sys_login()
        self.ui.statusBar.showMessage("Hello %s!" % login, 10000)

    def __show_logs_dialog(self):
        idx = self.rule_viewer.selected_row
        if idx >= 0:
            sel_rul = self.rule_viewer.get_rule(idx)
            dialog = LogsDialog(self, sel_rul.key)

        else:
            dialog = LogsDialog(self)
        dialog.show()

    def __choose_path(self):
        path = QFileDialog.getExistingDirectory(self, "Browse...")
        if path:
            self.ui.textPath.setText(path)

    def user_sys_login(self):
        return os.environ.get("USERNAME", os.environ.get("LOGIN", "unknown"))


class RuleViewer(QObject):

    onRowSelected = pyqtSignal(int)

    def __init__(self, dialog):
        super(RuleViewer, self).__init__(dialog)

        self.selected_row = -1
        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__table = dialog.ui.tableRules
        self.__rules = []
        self.__install()

    def refresh(self):
        log.info("Refresh rules")

        self.selected_row = -1
        self.__table.clearContents()
        self.__table.setRowCount(0)
        self.__rules = auditwrap.getMainRules().keys()
        for rule in self.__rules:
            self.__insert_row([rule.key, rule.path, rule.perm, " ".join(rule.fields)])

    def get_rule(self, index):
        return self.__rules[index]

    def __install(self):
        self.__table.cellClicked.connect(self.__on_selected)

    def __on_selected(self, row, col):
        log.info("Selected rule idx: %d" % row)
        self.selected_row = row
        self.onRowSelected.emit(row)

    def __insert_row(self, values):
        rows = self.__table.rowCount()
        self.__table.setRowCount(rows + 1)

        for i, value in enumerate(values):
            label = QLabel(value, self.__table)
            self.__table.setCellWidget(rows, i, label)

        return rows


class RuleEditor(QObject):

    def __init__(self, dialog):
        super(RuleEditor, self).__init__(dialog)

        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__loaded_rule = None
        self.__install()

    def clear(self):
        log.info("Clearing...")

        self.__loaded_rule = None
        self.__set_gui("", "", "", "")

    def load_rule(self, rule):
        log.info("Loading rule...")

        self.__loaded_rule = rule
        self.__set_gui(rule.key, rule.path, " ".join(rule.fields), rule.perm)

    def __set_gui(self, name, path, rule, perm):
        self.__ui.textName.setText(name)
        self.__ui.textPath.setText(path)
        self.__ui.textRule.setText(rule)

        self.__ui.checkR.setCheckState("r" in perm and Qt.Checked or Qt.Unchecked)
        self.__ui.checkW.setCheckState("w" in perm and Qt.Checked or Qt.Unchecked)
        self.__ui.checkX.setCheckState("x" in perm and Qt.Checked or Qt.Unchecked)
        self.__ui.checkA.setCheckState("a" in perm and Qt.Checked or Qt.Unchecked)

    def __install(self):
        self.__ui.buttonAdd.clicked.connect(self.__add_rule)
        self.__ui.buttonDelete.clicked.connect(self.__del_rule)
        self.__ui.buttonUpdate.clicked.connect(self.__update_rule)
        self.__ui.buttonClear.clicked.connect(self.clear)


    def __add_rule(self):
        log.info("Adding new rule...")

        name = str(self.__ui.textName.text()).strip()
        path = str(self.__ui.textPath.text()).strip()
        fields = str(self.__ui.textRule.text()).strip() or None

        rules = dict()
        perm = []
        if self.__ui.checkR.isChecked():
            rules['r'] = ''
            perm.append("r")
        if self.__ui.checkW.isChecked():
            rules['w'] = ''
            perm.append("w")
        if self.__ui.checkX.isChecked():
            rules['x'] = ''
            perm.append("x")
        if self.__ui.checkA.isChecked():
            rules['r'] = ''
            rules['w'] = ''
            rules['x'] = ''
            perm.append("a")
        perm_str = "".join(perm)

        if not name or not path or len(rules.keys()) == 0 :
            return self.__warning("Rule", "Cannot add rule! Fill in the required fields.")

        try:
            for perm in rules.keys():
                rule = auditwrap.FileWatchRule(name + perm, path, perm, fields)
                rules[perm] = rule
            mainRule = auditwrap.FileWatchRule(name, path, perm_str, fields)
            auditwrap.addActiveRule(mainRule, rules.values())
        except auditwrap.AuditwrapError, e:
            self.__error("Rule", "Cannot add rule: %s" % e)
        else:
            self.__info("Rule", "Rule '%s' has been added" % name)
            self.clear()
            self.__dialog.rule_viewer.refresh()

    def __del_rule(self):
        log.info("Deleting new rule...")

        if not self.__loaded_rule:
            return self.__warning("Rule", "Cannot delete: no selected rule")

        try:
            auditwrap.removeActiveRule(self.__loaded_rule)
        except auditwrap.AuditwrapError, e:
            self.__error("Rule", "Cannot delete rule: %s" % e)
        else:
            self.__info("Rule", "Rule '%s' has been deleted" % self.__loaded_rule.key)
            self.clear()
            self.__dialog.rule_viewer.refresh()

    def __update_rule(self):
        log.info("Updating rule...")

        if not self.__loaded_rule:
            return self.__warning("Rule", "Cannot update: no selected rule")

        try:
            auditwrap.removeActiveRule(self.__loaded_rule)
        except auditwrap.AuditwrapError, e:
            self.__error("Rule", "Cannot update rule: %s" % e)
        else:
            self.__info("Rule", "Rule '%s' has been deleted" % self.__loaded_rule.key)
            self.__add_rule()

    def __error(self, title, desc):
        QMessageBox.warning(self.__dialog, title, desc)
        log.error(desc)

    def __warning(self, title, desc):
        QMessageBox.warning(self.__dialog, title, desc)
        log.warning(desc)

    def __info(self, title, desc, msg_box=False, status=True):
        if msg_box:
            QMessageBox.information(self.__dialog, title, desc)
        if status:
            self.__dialog.statusBar.showMessage(desc, 30000)
        log.info(desc)






















