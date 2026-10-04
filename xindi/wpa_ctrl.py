"""Inline port of wpa_supplicant's control interface client library
(src/common/wpa_ctrl.c from hostap, UNIX domain socket variant) which the C++
program links as libwpa_client.

Messages are byte strings.
"""

import errno
import os
import select
import socket
import time

CONFIG_CTRL_IFACE_CLIENT_DIR = "/tmp"
CONFIG_CTRL_IFACE_CLIENT_PREFIX = "wpa_ctrl_"

# Events from wpa_ctrl.h used by the program
WPA_EVENT_CONNECTED = "CTRL-EVENT-CONNECTED "
WPA_EVENT_DISCONNECTED = "CTRL-EVENT-DISCONNECTED "
WPA_EVENT_SCAN_RESULTS = "CTRL-EVENT-SCAN-RESULTS "
WPS_EVENT_AP_AVAILABLE = "WPS-AP-AVAILABLE "    # note the trailing space (as in wpa_ctrl.h)

_counter = 0


class wpa_ctrl(object):
    def __init__(self):
        self.s = None
        self.local = ""
        self.dest = ""


def wpa_ctrl_open(ctrl_path):
    return wpa_ctrl_open2(ctrl_path, None)


def wpa_ctrl_open2(ctrl_path, cli_path):
    global _counter
    if ctrl_path is None:
        return None
    ctrl = wpa_ctrl()
    try:
        ctrl.s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM, 0)
    except OSError:
        return None

    _counter += 1
    tries = 0
    while True:
        if cli_path and cli_path.startswith("/"):
            ctrl.local = "%s/%s%d-%d" % (cli_path, CONFIG_CTRL_IFACE_CLIENT_PREFIX, os.getpid(), _counter)
        else:
            ctrl.local = "%s/%s%d-%d" % (CONFIG_CTRL_IFACE_CLIENT_DIR, CONFIG_CTRL_IFACE_CLIENT_PREFIX,
                                         os.getpid(), _counter)
        tries += 1
        try:
            ctrl.s.bind(ctrl.local)
            break
        except OSError as e:
            if e.errno == errno.EADDRINUSE and tries < 2:
                # getpid() returns unique identifier for this instance of
                # wpa_ctrl, so the existing socket file must have been left
                # by unclean termination of an earlier run. Remove the file
                # and try again.
                try:
                    os.unlink(ctrl.local)
                except OSError:
                    pass
                continue
            ctrl.s.close()
            return None

    ctrl.dest = ctrl_path
    try:
        ctrl.s.connect(ctrl.dest)
    except OSError:
        ctrl.s.close()
        try:
            os.unlink(ctrl.local)
        except OSError:
            pass
        return None

    # Make socket non-blocking so that we don't hang forever if target dies unexpectedly.
    ctrl.s.setblocking(False)
    return ctrl


def wpa_ctrl_close(ctrl):
    if ctrl is None:
        return
    try:
        os.unlink(ctrl.local)
    except OSError:
        pass
    try:
        ctrl.s.close()
    except OSError:
        pass


def wpa_ctrl_request(ctrl, cmd, reply_size, msg_cb=None):
    """Send a command and wait for the reply.

    Returns ``(ret, reply_bytes)``; ``ret`` is 0 on success, -1 on error and -2
    on timeout (no reply within 10 seconds).  ``reply_size`` is the size of
    the caller's reply buffer (``*reply_len`` on entry).
    """
    if isinstance(cmd, str):
        cmd = cmd.encode("utf-8", "surrogateescape")
    started_at = None
    while True:
        try:
            ctrl.s.send(cmd)
            break
        except (BlockingIOError, InterruptedError):
            # Must be a non-blocking socket... Try for a bit longer before giving up.
            if started_at is None:
                started_at = time.monotonic()
            elif time.monotonic() - started_at > 5:
                return -1, b""
            time.sleep(1)
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EBUSY, errno.EWOULDBLOCK):
                if started_at is None:
                    started_at = time.monotonic()
                elif time.monotonic() - started_at > 5:
                    return -1, b""
                time.sleep(1)
                continue
            return -1, b""

    while True:
        try:
            rlist, _, _ = select.select([ctrl.s], [], [], 10)
        except InterruptedError:
            continue
        except (OSError, ValueError):
            return -1, b""
        if ctrl.s in rlist:
            try:
                reply = ctrl.s.recv(reply_size)
            except OSError:
                return -1, b""
            res = len(reply)
            if (res > 0 and reply[0:1] == b"<") or (res > 6 and reply[:7] == b"IFNAME="):
                # This is an unsolicited message from wpa_supplicant, not the
                # reply to the request. Use msg_cb to report this to the caller.
                if msg_cb:
                    if res == reply_size:
                        res = reply_size - 1
                    msg_cb(reply[:res], res)
                continue
            return 0, reply
        else:
            return -2, b""


def _wpa_ctrl_attach_helper(ctrl, attach):
    ret, buf = wpa_ctrl_request(ctrl, b"ATTACH" if attach else b"DETACH", 10, None)
    if ret < 0:
        return ret
    if len(buf) == 3 and buf == b"OK\n":
        return 0
    return -1


def wpa_ctrl_attach(ctrl):
    return _wpa_ctrl_attach_helper(ctrl, 1)


def wpa_ctrl_detach(ctrl):
    return _wpa_ctrl_attach_helper(ctrl, 0)


def wpa_ctrl_recv(ctrl, reply_size):
    """Returns ``(ret, data)``"""
    try:
        data = ctrl.s.recv(reply_size)
    except OSError:
        return -1, b""
    return 0, data


def wpa_ctrl_pending(ctrl):
    try:
        rlist, _, _ = select.select([ctrl.s], [], [], 0)
    except (OSError, ValueError):
        return -1
    return 1 if ctrl.s in rlist else 0


def wpa_ctrl_get_fd(ctrl):
    return ctrl.s.fileno()
