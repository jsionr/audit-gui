#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''

import sys

from PyQt4 import QtGui

from dialogs.main import MainDialog


def main():
    app = QtGui.QApplication(sys.argv)

    main_window = MainDialog()
    main_window.resize(800, 600)
    main_window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
