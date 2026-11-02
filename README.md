# FTP Program

**Category:** Networking

## Problem

A file transfer program which can transfer files back and forth from a remote web sever.

## Solution

A `ftplib`-based client supporting directory listings plus download/upload. The demo also includes `MiniFTPServer`, a small loopback FTP server (USER/PASS, PASV, LIST, RETR, STOR, DELE) so the whole transfer path can be exercised without an external host.

## How to run

Requires Python 3.8+ and no third-party packages.

```bash
python3 main.py --host ftp.example.com --list
python3 main.py --host ftp.example.com --get remote.txt
python3 main.py --host ftp.example.com --put local.txt
python3 main.py --demo
```

## Example

```text
welcome: 220 MiniFTP ready
listing:
  -rw-r--r-- 1 demo demo       28 Jan 01 00:00 hello.txt
downloaded: Hello from the FTP server.
upload exists: True
```

## Attribution

The problem statement is from [karan/Projects](https://github.com/karan/Projects), a list of practical projects that anyone can solve in any programming language (MIT License, Copyright (c) 2013 Karan Goel). The Python solution in this repository was implemented by [bspreston-esq](https://github.com/bspreston-esq).

This repository is part of the [Projects-Python-All](https://github.com/bspreston-esq/Projects-Python-All) collection.
