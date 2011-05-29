# -*- encoding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''
import os
import logging
import re

from PyQt4 import uic
from PyQt4.QtCore import QObject
from PyQt4.QtCore import QThread
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QDialog

from logic import auditwrap
from auditgui import log


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
        self.__data_filter = DataFilter(self, self.__logs_viewer)


class DataFilter(QObject):

    def __init__(self, dialog, logs_viewer):
        super(DataFilter, self).__init__(dialog)

        self.__logs_viewer = logs_viewer
        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__logs = dialog.ui.logs

        self.__init_logic()

    def __init_logic(self):
        self.__ui.buttonFilter.clicked.connect(self.apply_filter)
        self.__ui.buttonClear.clicked.connect(self.clear)

    def apply_filter(self):
        filter = Filter()
        filter.path = str(self.__ui.pathInput.text()).strip()
        filter.user = str(self.__ui.userInput.text()).strip()
        filter.pid = str(self.__ui.pidInput.text()).strip()
        filter.prog = str(self.__ui.execInput.text()).strip()
        filter.type = str(self.__ui.typeBox.itemText(self.__ui.typeBox.currentIndex()));
        filter.rule = str(self.__ui.ruleInput.text()).strip()

        self.__logs_viewer.set_filter(filter)
        self.__logs_viewer.refresh()


    def clear(self):
        self.__ui.pathInput.setText('')
        self.__ui.userInput.setText('')
        self.__ui.pidInput.setText('')
        self.__ui.execInput.setText('')
        self.__ui.typeBox.setCurrentIndex(0)
        self.__ui.ruleInput.setText('')

        self.__logs_viewer.set_filter(None)


class Filter(object):

    def __init__(self):
        self.path = ''
        self.user = ''
        self.pid = ''
        self.prog = ''
        self.type = ''
        self.rule = ''

    def get_uid(self):
        ##TODO
        return self.user

class LogsViewer(QObject):

    def __init__(self, dialog):
        super(LogsViewer, self).__init__(dialog)

        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__logs = dialog.ui.logs
        self.__data_builder = None
        self.__filter = None

    def refresh(self):
        log.info("Refreshing logs...")
        pb = self.__ui.progressBar
        pb.setValue(0)
        pb.setRange(0, 0)

        self.__logs.clear()

        self.__data_builder = DataBuilder(self.__dialog)
        self.__data_builder.filter = self.__filter;
        self.__data_builder.rule_key = self.__dialog.rule_key
        self.__data_builder.finished.connect(self.__show_data)
        self.__data_builder.start()

        self.__status_updater = QTimer(self.__dialog)
        self.__status_updater.timeout.connect(self.__update_status)
        self.__status_updater.start(1000)

    def set_filter(self, filter):
        self.__filter = filter

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

    perm_map = {'r' : 'read',
                'w' : 'write',
                'x' : 'execute'}

    def __init__(self, parent):
        super(DataBuilder, self).__init__(parent)

        self.filter = None
        self.rule_key = ""
        self.status = auditwrap.ProcessingStatus()
        self.data = {}

    def run(self):
        if self.rule_key:
            rule = None
            subrules = None
            for rule_tmp, subrules_tmp in auditwrap.getMainRules().iteritems():
                if rule_tmp.key == self.rule_key:
                    rule = rule_tmp
                    subrules = subrules_tmp
                    break
            if rule is not None:
                self.__process_rule(rule, subrules)
        else:
            for rule, subrules in auditwrap.getMainRules().iteritems():
                self.__process_rule(rule, subrules)

    def __process_rule(self, rule, subrules):

        key = rule.key

        self.status.desc = "Processing rule '%s'..." % key

        subevents = {}

        for subrule in subrules:
            events = auditwrap.getEvents(subrule.key, self.status)
            subevents[subrule.perm] = events

        self.status.desc = "Finalizing rule '%s'..." % key

        data = self.data.setdefault(key, {})

        for perm, events in subevents.iteritems():
            for event in events:
                user = event.attributes.get('uid', '?')
                pid = event.attributes.get('pid', '?')
                syscall = DataBuilder.perm_map[perm]
                exe = event.attributes.get('exe', '')
                comm = event.attributes.get('comm', '')

                if self.filter is not None:
                    f_uid = self.filter.get_uid()
                    prog_pattern = '.*(' + self.filter.prog + ')+'
                    if len(f_uid) > 0 and user != f_uid:
                        continue
                    if len(self.filter.pid) > 0 and pid != self.filter.pid:
                        continue
                    if len(self.filter.prog) > 0 and re.match(prog_pattern, exe) is None:
                        continue
                    if self.filter.type != 'all' and syscall != type:
                        continue
                    ##TODO rule


                for file in event.fileNames:
                    log.info(file)
                    if file.startswith('/'):
                        path = file
                    else:
                        path = os.path.join(event.workingDir, file.lstrip('./'))
                    path.rstrip('/')


                    log.info(path)

                    if self.filter is not None and re.match(self.filter.path, path) is None:
                        continue

                    if path not in data:
                        path_data = data.setdefault(path, {})
                    else:
                        path_data = data[path]

                    if user not in path_data:
                        user_data = path_data.setdefault(user, {})
                    else:
                        user_data = path_data[user]
                    if pid not in user_data:
                        pid_data = user_data.setdefault(pid, {'exe': '', 'comm': ''})
                    else:
                        pid_data = user_data[pid]

                    if syscall not in pid_data:
                        pid_data[syscall] = 0
                    pid_data[syscall] += 1

                    if exe:
                        pid_data['exe'] = exe
                    if comm:
                        pid_data['comm'] = comm



