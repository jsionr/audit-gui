# -*- encoding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''
import os
import logging

from PyQt4 import uic
from PyQt4.QtCore import QObject
from PyQt4.QtCore import QThread
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QDialog

from logic import auditwrap


log = logging.getLogger(__name__)


class LogsDialog(QDialog):

    def __init__(self, parent, rule_key=None):
        super(LogsDialog, self).__init__(parent)
        self.ui = uic.loadUi("layouts/logs.ui", self)
        self.rule_key = rule_key
        self.__init_ui()
        self.__init_logic()

    def __init_ui(self):
        pass

    def __init_logic(self):
        self.ui.buttonClose.clicked.connect(self.close)

        self.__logs_viewer = LogsViewer(self)
        self.ui.buttonRefresh.clicked.connect(self.__logs_viewer.refresh)
        self.__logs_viewer.refresh()


class LogsViewer(QObject):

    def __init__(self, dialog):
        super(LogsViewer, self).__init__(dialog)

        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__logs = dialog.ui.logs
        self.__data_builder = None

    def refresh(self):
        log.info("Refreshing logs...")
        pb = self.__ui.progressBar
        pb.setValue(0)
        pb.setRange(0, 0)

        self.__logs.clear()

        self.__data_builder = DataBuilder(self.__dialog)
        self.__data_builder.rule_key = self.__dialog.rule_key
        self.__data_builder.finished.connect(self.__show_data)
        self.__data_builder.start()

        self.__status_updater = QTimer(self.__dialog)
        self.__status_updater.timeout.connect(self.__update_status)
        self.__status_updater.start(1000)

    def __show_data(self):
        log.info("Showing data...")

        self.__status_updater.stop()

        data = self.__data_builder.data
        self.__data_builder = None

        pb = self.__ui.progressBar

        pb.setFormat("Showing data...")
        pb.setValue(0)
        pb.setRange(0, 0)

        html = []
        for rule, rule_data in data.iteritems():
            html.append("<h2>Rule: %s</h2>" % rule)
            for path, path_data in rule_data.iteritems():
                html.append('<h4 class="path">Path: %s</h4>' % path)
                for user, user_data in path_data.iteritems():
                    html.append('<h4 class="user">User: %s</h4>' % user)
                    for pid, pid_data in user_data.iteritems():
                        html.append('<h4 class="pid">PID: %s ---- %s (%s)</h4>' % (pid, pid_data['comm'], pid_data['exe']))
                        html.append('<ul class="calls">')
                        for name, val in pid_data.iteritems():
                            if name not in ['comm', 'exe']:
                                html.append("<li>%s = %s</li>" % (name, val))
                        html.append("</ul>")

        doc = self.__logs.document()
        doc.setDefaultStyleSheet("""
            h2 {background: #e8a49b;}
            .path {margin-left: 20px; background: #b1e89b;}
            .user {margin-left: 40px; background: #9b9be8;}
            .pid {margin-left: 60px; background: #9bc5e8;}
            .calls {margin-left: 60px;}
        """)
        doc.setHtml("\n".join(html))

        pb.setFormat("Done")
        pb.setRange(0, 1)
        pb.setValue(1)

        log.info("Showing data: done.")

    def __update_status(self):
        if not self.__data_builder:
            return

        status = self.__data_builder.status
        pb = self.__ui.progressBar

        format = status.desc + " %p% (%v/%m)"

        if pb.format() != format:
            pb.setFormat(format)
        if pb.maximum() != status.total:
            pb.setRange(0, status.total)
        pb.setValue(status.current)


class DataBuilder(QThread):

    def __init__(self, parent):
        super(DataBuilder, self).__init__(parent)

        self.rule_key = ""
        self.status = auditwrap.ProcessingStatus()
        self.data = {}

    def run(self):
        if self.rule_key:
            self.__process_rule(self.rule_key)
        else:
            for rule in auditwrap.getActiveRules():
                self.__process_rule(rule.key)

    def __process_rule(self, key):
        self.status.desc = "Processing rule '%s'..." % key
        events = auditwrap.getEvents(key, self.status)
        self.status.desc = "Finalizing rule '%s'..." % key

        data = self.data.setdefault(key, {})

        for event in events:
            user = event.attributes.get('uid', '?')
            pid = event.attributes.get('pid', '?')
            syscall = event.attributes['syscall']
            exe = event.attributes.get('exe', '')
            comm = event.attributes.get('comm', '')

            for file in event.fileNames:
                path = os.path.join(event.workingDir, file.lstrip('./'))

                path_data = data.setdefault(path, {})
                user_data = path_data.setdefault(user, {})
                pid_data = user_data.setdefault(pid, {'exe': '', 'comm': ''})

                if syscall not in pid_data:
                    pid_data[syscall] = 0
                pid_data[syscall] += 1

                if exe:
                    pid_data['exe'] = exe
                if comm:
                    pid_data['comm'] = comm

