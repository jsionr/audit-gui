# Audit GUI #

GUI for linux audit daemon.

## What is it? ##

Audit GUI is a **Python** based graphical user interface facilitating the usage of a standard linux **audit** daemon (regarding filesystem access monitoring).

## How does it work? ##

The application serves as a **wxWidget** front-end, mainly dispatching linux shell commands (e.g. _auditctl_, _ausearch_) and parsing _auditd logs_. Entire set of filesystem watch rules is kept within _auditd configuration_.

## Main features ##

### Managing the list of _auditd watch rules_ ###

The main window of Audit GUI contains a list of active filesystem watch rules, as obtained from _auditd configuration_ (yes, it actually shows rules, which might have been added earlier e.g. by hand).

<img src='http://audit-gui.googlecode.com/svn/trunk/misc/main.png' width='800' />

Every watch is composed of:
  * **name** - an arbitrary string, helpful for identifying the watch
  * **path** - a filesystem path to a file or directory which should be monitored (in case of a directory, all sub-directories are taken into consideration as well)
  * **permission filter** - a combination of _read_, _write_, _execute_ and _access_ actions, which should trigger the rule
  * **detailed rule** - any string accepted by _-F_ option of _auditctl_ command, i.e. denoting a _rule field_, such as "pid=1005" or "success!=0". Please consult _man auditctl_ for details

Rules can be easily added/update/deleted from the list. All changes are dynamically applied (and thus immediately reflected in _auditd configuration_).

### Viewing visualized log data ###

Right after applying a filesystem watch, _auditd_ begins to register every occurrence of a rule in a log file. At any moment, user may decide to view the events gathered so far.

<img src='http://audit-gui.googlecode.com/svn/trunk/misc/logs.png' width='800' />

The log visualization component included in Audit GUI allows you to:
  * **view** aggregated read/write/execute/access events, categorized by:
    * rule name
    * path (and file name)
    * user (that triggered the rule)
    * pid (together with shell command and binary path)
  * **filter** interesting events according to above categories
  * **sort** all events according to above categories
  * **group** all events by their triggering PID
  * **save** entire reports for future analysis

## Demo movie ##

![http://img.youtube.com/vi/lxP6iqQsvpQ/1.jpg](http://img.youtube.com/vi/lxP6iqQsvpQ/1.jpg)![http://img.youtube.com/vi/lxP6iqQsvpQ/2.jpg](http://img.youtube.com/vi/lxP6iqQsvpQ/2.jpg)![http://img.youtube.com/vi/lxP6iqQsvpQ/3.jpg](http://img.youtube.com/vi/lxP6iqQsvpQ/3.jpg)

Please [click here](http://www.youtube.com/watch?v=lxP6iqQsvpQ) to see how easy-to-use the Audit GUI is.