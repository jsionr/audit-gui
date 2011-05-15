#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2011-04-17

@author: quermit
'''
import os
import sys
import logging

from PyQt4 import QtGui


log = logging.getLogger("auditgui")


def configure_logging():
    format = '%(levelname)-8s %(name)-20s %(message)s'
    logging.basicConfig(format=format, level=logging.DEBUG)
    logging.getLogger("PyQt4").setLevel(logging.WARNING)


def main():
    configure_logging()

    log.info("Initializing...")

    if os.path.exists('src'):
        os.chdir('src')

    app = QtGui.QApplication(sys.argv)

    try:
        from dialogs.main import MainDialog
    except Exception, e:
        log.error("Error: %s" % e)
        return

    log.info("Loading GUI...")

    main_window = MainDialog()
    main_window.resize(800, 600)
    main_window.show()

    log.info("Ready.")

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
