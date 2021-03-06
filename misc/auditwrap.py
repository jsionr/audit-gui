#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess, shlex, os, time

# --- <INTERFACE> ---

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

  def __init__(self, key, path, perm, fields = None):
    """ Konstruktor z dowolnym keyem, absolute pathem, prawami rwxa zapodanymi jako str, oraz opcjonalna lista fieldow jako jeden str (fieldy oddzielone spacjami, np. "pid=1005 success!=0"). """
    if path == None or key == None:
      raise Exception("Neither path nor key can be None.")
    if "key=" in key:
      raise Exception("Key contains illegal string.")
    rc = min(perm.count('r'), 1)
    wc = min(perm.count('w'), 1)
    xc = min(perm.count('x'), 1)
    ac = min(perm.count('a'), 1)
    if rc + wc + xc + ac != len(perm):
      raise Exception("Permission string should contain only letters: \'r\', \'w\', \'x\' and \'a\' (maximum 1 of each).")
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
    return self.key+" -> "+self.path+" ("+self.perm+") conditions: "+str(self.fields)

  def _composeCommand(self):
    fs = ""
    for f in self.fields:
      fs += " -F \""+f+"\""
    return "\""+self.path+"\" -p \""+self.perm+"\" -k \""+self.key+"\""+fs

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
  Moze byc ich kilka, np. w przypadku tworzenia nowego pliku (event dotyczy wtedy parent dira oraz pliku) lub polecenia mv (event dotyczy wtedy lokalizacji source i dest) itd.
  Te nazwy moga sie zaczynac np. od "../../.." (lub byc rowne "."), wiec trzeba je przetwarzyc wzgledem workingDir.
  """

  attributes = None
  """
  Dictionary z pozostalymi atrybutami eventa (z sekcji type=SYSCALL).
  Znajdzie sie tu m.in. arch, syscall, success, exit, ppid, pid, uid, comm, exe, key, generalnie wszystko co bedzie dostepne w logu.
  Wartosci liczbowe beda resolvowane do nazw (dotyczy to chyba tylko syscalla i uid/guid/fsuid/...).
  """

  def __init__(self, paths, cwd, syscall):
    """
    Konstruktor parsujacy kilka odpowiednio wycietych linijek outputu ausearch'a.
    """
    self.fileNames = []
    for p in paths:
      namep = p.find("name=")+5
      nexteqp = p.find("=", namep)
      nextp = p.rfind(" ", namep, nexteqp)
      self.fileNames.append(p[namep:nextp])
    self.workingDir = cwd[cwd.find("cwd="):len(cwd)-1]
    fdotp = syscall.find(".")
    self.time = time.strptime(syscall[syscall.find("audit(")+6:fdotp], "%m/%d/%Y %H:%M:%S")
    self.timeMilliseconds = int(syscall[fdotp+1:syscall.find(":", fdotp)])
    self.attributes = {}
    attrs = syscall[syscall.find(") :")+4:len(syscall)-1]
    startp = 0
    while True:
      nreqp = attrs.find("=", startp)
      if nreqp == -1:
	break
      nexteqp = attrs.find("=", nreqp+1)
      if (nexteqp == -1):
	nrsp = len(attrs)
      else:
	nrsp = attrs.rfind(" ", startp, nexteqp)
      self.attributes[attrs[startp:nreqp]] = attrs[nreqp+1:nrsp]
      startp = nrsp+1

  def __repr__(self):
    return "At: "+time.strftime("%d.%m.%Y %H:%M:%S", self.time)+"."+str(self.timeMilliseconds)+"\nIn working dir: "+self.workingDir+"\nFiles: "+str(self.fileNames)+"\nAttributes: "+str(self.attributes)+"\n-"

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
    key = line[keyp+4:]
    permp = line.rfind("perm=", 0, keyp)
    spacep = line.find(" ", permp, keyp)
    perm = line[permp+5:spacep]
    fields = line[spacep+1:keyp-1]
    if line[12:23] != "exit,always":
      continue
    if line[24] == 'd':
      path = line[28:permp-1]
    else:
      path = line[30:permp-1]
    sp = path.rfind("(0x")
    if sp != -1:
      path = path[0:sp-1]
    ret.append(FileWatchRule(key, path, perm, fields))
  return ret

def addActiveRule(rule):
  """
  Dodaje nowa FileWatchRule do auditda.
  """
  err = _execute("auditctl -w "+rule._composeCommand())
  if err != "":
    raise Exception(err)

def removeActiveRule(rule):
  """
  Usuwa FileWatchRule z auditda.
  """
  err = _execute("auditctl -W "+rule._composeCommand())
  if err != "":
    raise Exception(err)

def getEvents(key):
  """
  Zwraca liste FileWatchEventow pobranych z loga auditda wg zapodanego klucza.
  """
  ret = []
  for element in _execute("ausearch -i -k \""+key+"\"").split("----"):
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
  return ret

# --- </INTERFACE> ---

def _execute(command, getError = False):
  return subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[1 if getError else 0]

if os.getuid() != 0:
  raise Exception("You have to be root to use this module (try \"sudo python ...\").")

__all__ = [isDaemonRunning, setDaemonRunning, getActiveRules, addActiveRule, removeActiveRule, getEvents, FileWatchRule, FileWatchEvent]
