# vim:fileencoding=utf-8

import vim
import socket
import struct
import contextlib

fcitxsocketfile = vim.eval('s:fcitxsocketfile')


class FcitxComm(object):
    STATUS = struct.pack('i', 0)
    ACTIVATE = struct.pack('i', 1 | (1 << 16))
    DEACTIVATE = struct.pack('i', 1)
    INT_SIZE = struct.calcsize('i')

    def __init__(self, socketfile, keyboard_first=True):
        if socketfile[0] == '@':  # abstract socket
            socketfile = '\x00' + socketfile[1:]
        self.socketfile = socketfile
        self.sock = None
        self.keyboard_first = keyboard_first
        self._saved_status = self.status()

    def status(self):
        status = self._with_socket(self._status) == 2
        return status if self.keyboard_first else not status

    def activate(self):
        self._with_socket(
            self._command,
            self.ACTIVATE if self.keyboard_first else self.DEACTIVATE)

    def deactivate(self):
        self._with_socket(
            self._command,
            self.DEACTIVATE if self.keyboard_first else self.ACTIVATE)

    def restore(self):
        self.activate() if self._saved_status else self.deactivate()

    def _error(self, e):
        estr = str(e).replace('"', r'\"')
        file = self.socketfile.replace('"', r'\"')
        vim.command(
            'echohl WarningMsg | echo "fcitx.vim: socket %s error: %s" | echohl NONE'
            % (file, estr))

    def _connect(self):
        self.sock = sock = socket.socket(socket.AF_UNIX)
        sock.settimeout(0.5)
        try:
            sock.connect(self.socketfile)
            return True
        except (socket.error, socket.timeout) as e:
            self._error(e)
            return False

    def _with_socket(self, func, *args, **kwargs):
        # fcitx doesn't support connection reuse
        if not self._connect():
            return

        with contextlib.closing(self.sock):
            try:
                return func(*args, **kwargs)
            except (socket.error, socket.timeout, struct.error) as e:
                self._error(e)

    def _status(self):
        self.sock.send(self.STATUS)
        return struct.unpack('i', self.sock.recv(self.INT_SIZE))[0]

    def _command(self, cmd):
        self.sock.send(cmd)


if vim.eval('exists("g:fcitx_keyboard_first")') == '1' and vim.eval(
        'g:fcitx_keyboard_first') == '0':
    Fcitx = FcitxComm(fcitxsocketfile, keyboard_first=False)
else:
    Fcitx = FcitxComm(fcitxsocketfile, keyboard_first=True)


def fcitx2en():
    if Fcitx.status():
        vim.command('let b:inputtoggle = 1')
        Fcitx.deactivate()


def fcitx2zh():
    if vim.eval('exists("b:inputtoggle")') == '1':
        if vim.eval('b:inputtoggle') == '1':
            Fcitx.activate()
            vim.command('let b:inputtoggle = 0')
    else:
        vim.command('let b:inputtoggle = 0')
        if not Fcitx.keyboard_first:
            Fcitx.activate()


def fcitx_restore():
    Fcitx.restore()
