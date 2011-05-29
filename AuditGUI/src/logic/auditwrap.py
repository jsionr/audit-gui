#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import shlex
import os
import time
import re

# --- <INTERFACE> ---


class AuditwrapError(Exception):
    pass

class FileWatchRule:
    """
    Pojedynczy rule, po stworzeniu jest juz tylko read-only.
    Bedzie zwracany przez funkcje listujace oraz ma byc przekazywany do funkcji dodajacych/usuwajacych rule.
    Jak widac, jest to tylko Value Object, nie ma na nim metod typu setActive(), itd. Do tego trzeba uzyc funkcji modulu.
    """

    key = None
    """
    No domysl sie.
    Dodam tylko, ze ograniczenie podawane przez man (31 bajtow klucza) chyba nie obowiazuje.
    """

    path = None
    """
    Absolutny path do obserwowanego pliku/katalogu.
    """

    perm = None
    """
    Prawa rwxa w postaci str.
    """

    fields = None
    """
    Lista warunkow reguly (czyli tzw. fieldow), np: ["pid=1005", "success!=0"].
    Zwroc uwage, ze tutaj jest lista, lecz konstruktor oczekuje fieldow w postaci pojedynczego stringa.
    """

    def __init__(self, key, path, perm, fields=None):
        """ Konstruktor z dowolnym keyem, absolute pathem, prawami rwxa zapodanymi jako str, 
        oraz opcjonalna lista fieldow jako jeden str (fieldy oddzielone spacjami, np. "pid=1005 success!=0"). """
        if path == None or key == None:
            raise AuditwrapError("Neither path nor key can be None.")
        if "key=" in key:
            raise AuditwrapError("Key contains illegal string.")
        rc = min(perm.count('r'), 1)
        wc = min(perm.count('w'), 1)
        xc = min(perm.count('x'), 1)
        ac = min(perm.count('a'), 1)
        if rc + wc + xc + ac != len(perm):
            raise AuditwrapError("Permission string should contain only letters: \'r\', \'w\', \'x\' and \'a\' (maximum 1 of each).")
        self.key = key
        self.path = path
        self.perm = perm
        self.fields = []
        if fields != None and fields != "":
            fields = fields.split(' ')
            for f in fields:
                if f[0:3] != "(0x":
                    self.fields.append(f)

    def __repr__(self):
        return self.key + " -> " + self.path + " (" + self.perm + ") conditions: " + str(self.fields)

    def _composeCommand(self):
        fs = ""
        for f in self.fields:
            fs += " -F \"" + f + "\""
        return "\"" + self.path + "\" -p \"" + self.perm + "\" -k \"" + self.key + "\"" + fs


class FileWatchEvent:
    """
    Pojedynczy event dotyczacy file watcha czytany z loga (grupa wpisow o tym samym msg id)
    """

    time = None
    """
    Czas zdarzenia podany jako pythonowy struct_time.
    """

    timeMilliseconds = None
    """
    W struct_time chyba nie ma miejsca na ta informacje, a audit ja dostarcza.
    """

    workingDir = None
    """
    Absolutny path do katalogu, z ktorego wydano polecenie triggerujace rule.
    """

    fileNames = None
    """
    Lista relatywnych (wzgledem workingDir) nazw plikow, ktorych dotyczy event.
    Moze byc ich kilka, np. w przypadku tworzenia nowego pliku (event dotyczy wtedy parent dira oraz pliku) 
    lub polecenia mv (event dotyczy wtedy lokalizacji source i dest) itd.
    Te nazwy moga sie zaczynac np. od "../../.." (lub byc rowne "."), wiec trzeba je przetwarzyc wzgledem workingDir.
    """

    attributes = None
    """
    Dictionary z pozostalymi atrybutami eventa (z sekcji type=SYSCALL).
    Znajdzie sie tu m.in. arch, syscall, success, exit, ppid, pid, uid, comm, exe, key, generalnie wszystko 
    co bedzie dostepne w logu.
    Wartosci liczbowe beda resolvowane do nazw (dotyczy to chyba tylko syscalla i uid/guid/fsuid/...).
    """

    re_attrs = re.compile("(\w+)=(\S+)")
    re_time = re.compile(r".*(\d\d\.\d\d\.\d\d\d\d \d\d:\d\d:\d\d)\.(\d+):(\d+).*")

    def __init__(self, paths, cwd, syscall):
        """
        Konstruktor parsujacy kilka odpowiednio wycietych linijek outputu ausearch'a.
        """
        self.fileNames = []
        for path in paths:
            attrs = self.__get_attrs(path)
            self.fileNames.append(attrs['name'])

        attrs = self.__get_attrs(cwd)
        self.workingDir = attrs['cwd']

        timegroups = re.match(self.re_time, syscall).groups()
        try:
            self.time = time.strptime(timegroups[0], "%m/%d/%Y %H:%M:%S")
        except:
            self.time = time.strptime(timegroups[0], "%d.%m.%Y %H:%M:%S")
        self.timeMilliseconds = int(timegroups[1])

        self.attributes = self.__get_attrs(syscall)

    def __get_attrs(self, line):
        return dict(re.findall(self.re_attrs, line))

    def __repr__(self):
        return "At: " + time.strftime("%d.%m.%Y %H:%M:%S", self.time) + "." + str(self.timeMilliseconds) + \
            "\nIn working dir: " + self.workingDir + "\nFiles: " + str(self.fileNames) + "\nAttributes: " + \
            str(self.attributes) + "\n"


class ProcessingStatus(object):

    def __init__(self):
        self.current = 0
        self.total = 0
        self.desc = ""



def isDaemonRunning():
    """
    No domysl sie.
    """
    return "auditd is running" in _execute("service auditd status")

def setDaemonRunning(running):
    """
    No domysl sie.
    """
    _execute("service auditd " + ("start" if running else "stop"))

def getActiveRules():
    """
    Zwraca liste aktywnych w auditd'cie FileWatchRule.
    """
    ret = []
    for line in _execute("auditctl -l").splitlines():
        keyp = line.rfind("key=")
        if (keyp == -1):
            continue
        key = line[keyp + 4:]
        permp = line.rfind("perm=", 0, keyp)
        spacep = line.find(" ", permp, keyp)
        perm = line[permp + 5:spacep]
        fields = line[spacep + 1:keyp - 1]
        if line[12:23] != "exit,always":
            continue
        if line[24] == 'd':
            path = line[28:permp - 1]
        else:
            path = line[30:permp - 1]
        sp = path.rfind("(0x")
        if sp != -1:
            path = path[0:sp - 1]
        ret.append(FileWatchRule(key, path, perm, fields))
    return ret

def getMainRules():

    active = getActiveRules()
    rules_tmp = {}
    for rule in active:
        if rule.perm in ['r', 'w', 'x'] and rule.key.endswith(rule.perm):
            key = rule.key[0:-1]
            if key not in rules_tmp:
                rules_tmp[key] = [rule]
            else:
                rules_tmp[key].append(rule)

    rules = dict()
    for key in rules_tmp.keys():
        perm_str = ""
        path = ""
        fields = []
        for rule in rules_tmp[key]:
            perm_str += rule.perm
            path = rule.path
            fields = rule.fields
        m_rule = FileWatchRule(key, path, perm_str, ' '.join(fields))
        rules[m_rule] = rules_tmp[key]
    return rules

def addActiveRule(rule, subrules):
    """
    Dodaje nowa FileWatchRule do auditda.
    """
    # rules[rule] = subrules
    for subrule in subrules:
        err = _execute("auditctl -w " + subrule._composeCommand())
        if err != "":
            raise AuditwrapError(err)

def removeActiveRule(rule):
    """
    Usuwa FileWatchRule z auditda.
    """
    rules = getMainRules()
    for rule_tmp, subrules in rules.iteritems():
        if rule.key == rule_tmp.key:
            for subrule in subrules:
                err = _execute("auditctl -W " + subrule._composeCommand())
                if err != "":
                    raise AuditwrapError(err)
            break

def getEvents(key, status=None):
    """
    Zwraca liste FileWatchEventow pobranych z loga auditda wg zapodanego klucza.
    """
    if not status:
        status = ProcessingStatus()

    ret = []

    elements = _execute("ausearch -i -k \"" + key + "\"").split("----")
    status.total = len(elements)
    for i, element in enumerate(elements):
        paths = []
        cwd = None
        syscall = None
        for line in element.splitlines():
            if line[5:9] == "PATH":
                paths.insert(0, line)
            if line[5:8] == "CWD":
                cwd = line
            if line[5:12] == "SYSCALL":
                syscall = line
        if len(paths) > 0 and cwd != None and syscall != None:
            ret.append(FileWatchEvent(paths, cwd, syscall))
        status.current = i + 1
    return ret

# --- </INTERFACE> ---

def _execute(command, getError=False):
    return subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()[1 if getError else 0]

if os.getuid() != 0:
    raise AuditwrapError("You have to be root to use this module.")

__all__ = [isDaemonRunning, setDaemonRunning, getActiveRules, addActiveRule, removeActiveRule, getEvents,
           FileWatchRule, FileWatchEvent]
