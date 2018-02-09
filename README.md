# FAT32-carving

[BOB6]DF12_Tech_02_박강민

* src/fat32.py : source file

Environment
============

* OS: Windows 10
* Version : Python 3.6.4

Dependency
===========

* psutil

```
$ pip install psutil
```

Usage
======

* Require administrator(root) mode
* \<drive\> is Drive name as C, D, F, I
* Select carving mode to add [all]. Default is unallocated mode.

```
$ python3 fat32.py <drive> [all]
```