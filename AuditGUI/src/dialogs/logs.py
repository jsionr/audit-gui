# -*- encoding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''

from PyQt4 import uic
from PyQt4.QtGui import QDialog


class LogsDialog(QDialog):
    
    def __init__(self, parent):
        super(LogsDialog, self).__init__(parent)
        self.ui = uic.loadUi("layouts/logs.ui", self)

