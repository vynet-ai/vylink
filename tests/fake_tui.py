#!/usr/bin/env python3
"""A stand-in for an agent's terminal app, for vylink's tests: a one-line input box with a prompt mark, an optional
dim placeholder, bracketed paste, and Enter that "submits" (prints SUBMITTED: and appends the text to a log file).

usage: fake_tui.py <mark> [placeholder]     env FAKE_TUI_LOG = file that receives each submitted text
"""
import os
import re
import sys
import termios
import tty

mark = sys.argv[1] if len(sys.argv) > 1 else "❯"
placeholder = sys.argv[2] if len(sys.argv) > 2 else ""
logpath = os.environ.get("FAKE_TUI_LOG", os.devnull)
fd = sys.stdin.fileno()
old = termios.tcgetattr(fd)
out = sys.stdout
buf = ""


def draw():
    out.write("\r\x1b[2K")
    if buf:
        out.write(f"{mark} {buf}"[:90].replace("\n", " "))
    elif placeholder:
        out.write(f"\x1b[1m{mark}\x1b[0m \x1b[2m{placeholder}\x1b[0m")
    else:
        out.write(f"{mark}\xa0")
    out.flush()


tty.setraw(fd)
out.write("\x1b[?2004h")
draw()
data = b""
try:
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        data += chunk
        while data:
            if data.startswith(b"\x1b[200~"):
                end = data.find(b"\x1b[201~")
                if end < 0:
                    break
                buf += data[6:end].decode("utf-8", "replace").replace("\r", "\n")
                data = data[end + 6:]
            elif data[:1] in (b"\r", b"\n"):
                data = data[1:]
                if buf:
                    out.write("\r\x1b[2K" + "SUBMITTED: " + buf.replace("\n", " NL ") + "\r\n")
                    with open(logpath, "a", encoding="utf-8") as f:
                        f.write(buf.replace("\n", " NL ") + "\n")
                    buf = ""
            elif data[:1] == b"\x03":
                raise KeyboardInterrupt
            elif data[:1] == b"\x7f":
                buf, data = buf[:-1], data[1:]
            elif data[:1] == b"\x1b":
                m = re.match(rb"\x1b\[[0-9;?]*[A-Za-z~]", data)
                if m:
                    data = data[m.end():]
                elif len(data) < 8:
                    break
                else:
                    data = data[1:]
            else:
                n = 1
                while n <= 4:
                    try:
                        buf += data[:n].decode("utf-8")
                        break
                    except UnicodeDecodeError:
                        n += 1
                data = data[n if n <= 4 else 1:]
        draw()
except KeyboardInterrupt:
    pass
finally:
    out.write("\x1b[?2004l\r\n")
    out.flush()
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
