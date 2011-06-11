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
from PyQt4.QtGui import QFileDialog

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
        self.ui.buttonSave.clicked.connect(self.__logs_viewer.save)
        self.__logs_viewer.refresh()
        self.__data_filter = DataFilter(self, self.__logs_viewer)
        self.__data_sorter = DataSorter(self, self.__logs_viewer)

class DataSorter(QObject):

    def __init__(self, dialog, logs_viewer):
        super(DataSorter, self).__init__(dialog)

        self.__logs_viewer = logs_viewer
        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__logs = dialog.ui.logs

        self.__init_logic()

    def __init_logic(self):
        self.__ui.buttonGo.clicked.connect(self.sort)

    def sort(self):
        order_by = Sort()
        order_by.order = str(self.__ui.sortBox.itemText(self.__ui.sortBox.currentIndex())).strip();
        order_by.dir = str(self.__ui.dirBox.itemText(self.__ui.dirBox.currentIndex())).strip();
        print order_by.order, order_by.dir
        self.__logs_viewer.order(order_by)


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
        filter.groupPID = self.__ui.groupPid.isChecked()

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

class Sort(object):

    def __init__(self):

        self.order = ''
        self.dir = ''

class Filter(object):

    def __init__(self):
        self.path = ''
        self.user = ''
        self.pid = ''
        self.prog = ''
        self.type = ''
        self.rule = ''
        self.groupPID = False

    def get_uid(self):
        return self.user

class LogsViewer(QObject):

    def __init__(self, dialog):
        super(LogsViewer, self).__init__(dialog)

        self.__dialog = dialog
        self.__ui = dialog.ui
        self.__logs = dialog.ui.logs
        self.__data_builder = None
        self.__filter = None
        self.__data = None

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

    def save(self):
        path = QFileDialog.getSaveFileName(self.__dialog, "Browse...")
        f = open(path, 'w')
        f.write(self.__html)
        f.close()

    def set_filter(self, filter):
        self.__filter = filter

    def order(self, order_by):
        self.__logs.clear()
        self.__process_data(order_by)

    def __show_data(self):
        log.info("Showing data...")

        self.__status_updater.stop()


        self.__data = self.__data_builder.data
        self.__data_builder = None

        self.__process_data()


    def __process_data(self, order_by=None):

        pb = self.__ui.progressBar

        pb.setFormat("Showing data...")
        pb.setValue(0)
        pb.setRange(0, 0)

        data = self.__data

        if order_by is not None:
            print order_by.order, order_by.dir

        rules = data.iteritems()
        if order_by is not None and order_by.order == "by rule name":
            print "rule"
            if order_by.dir == "asc":
                rules = sorted(rules)
            else:
                rules = sorted(rules, reverse=True)

        html = []
        for rule, rule_data in rules:
            html.append("<h2>Rule: %s</h2>" % rule)

            paths = rule_data.iteritems()
            if order_by is not None and order_by.order == "by path":
                print "path"
                if order_by.dir == "asc":
                    paths = sorted(paths)
                else:
                    paths = sorted(paths, reverse=True)

            for path, path_data in paths:
                html.append('<h4 class="path">Path: %s</h4>' % path)

                users = path_data.iteritems()
                if order_by is not None and order_by.order == "by user name":
                    if order_by.dir == "asc":
                        users = sorted(users)
                    else:
                        users = sorted(users, reverse=True)

                for user, user_data in users:
                    html.append('<h4 class="user">User: %s</h4>' % user)

                    progs = user_data.iteritems()
                    if order_by is not None and order_by.order == "by PID":
                        if order_by.dir == "asc":
                            progs = sorted(progs)
                        else:
                            progs = sorted(progs, reverse=True)
                    elif order_by is not None and order_by.order == "by command":
                        print "command"
                        if order_by.dir == "asc":
                            progs = sorted(progs, key=lambda p: p[1]['comm'])
                        else:
                            progs = sorted(progs, key=lambda p: p[1]['comm'], reverse=True)

                    for prog, prog_data in progs:
                        if self.__filter is not None and self.__filter.groupPID:
                            html.append('<h4 class="prog">%s (%s)</h4>' % (prog, prog_data['exe']))
                        else:
                            html.append('<h4 class="prog">PID: %s ---- %s (%s)</h4>' % (prog, prog_data['comm'], prog_data['exe']))
                        html.append('<ul class="calls">')
                        for name, val in prog_data.iteritems():
                            if name not in ['comm', 'exe']:
                                html.append("<li>%s = %s</li>" % (name, val))
                        html.append("</ul>")

        doc = self.__logs.document()
        doc.setDefaultStyleSheet("""
            h2 {background: #e8a49b;}
            .path {margin-left: 20px; background: #b1e89b;}
            .user {margin-left: 40px; background: #9b9be8;}
            .prog {margin-left: 60px; background: #9bc5e8;}
            .calls {margin-left: 60px;}
        """)
        doc.setHtml("\n".join(html))

        self.__html = "\n".join(html)

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

                prog = pid
                if self.filter is not None and self.filter.groupPID:
                    prog = comm

                if self.filter is not None:
                    f_uid = self.filter.get_uid()
                    prog_pattern = '.*(' + self.filter.prog + ')+'
                    if len(f_uid) > 0 and user != f_uid:
                        continue
                    if len(self.filter.pid) > 0 and pid != self.filter.pid:
                        continue
                    if len(self.filter.prog) > 0 and re.match(prog_pattern, exe) is None:
                        continue
                    if self.filter.type != 'all' and syscall != self.filter.type:
                        continue
                    ##TODO rule


                for file in event.fileNames:
                    if file.startswith('/'):
                        path = file
                    else:
                        path = os.path.join(event.workingDir, file.lstrip('./'))
                    path.rstrip('/')

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
                    if prog not in user_data:
                        prog_data = user_data.setdefault(prog, {'exe': '', 'comm': ''})
                    else:
                        prog_data = user_data[prog]

                    if syscall not in prog_data:
                        prog_data[syscall] = 0
                    prog_data[syscall] += 1

                    if exe:
                        prog_data['exe'] = exe
                    if comm:
                        prog_data['comm'] = comm



