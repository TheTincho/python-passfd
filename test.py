#!/usr/bin/env python
# vim: set fileencoding=utf-8
# vim: ts=4:sw=4:et:ai:sts=4

# Copyright © 2010 Martín Ferrari <martin.ferrari@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os, unittest, socket, sys
from passfd import sendfd, recvfd

class TestPassfd(unittest.TestCase):
    def readfd_test(self, fd):
        s = fd.read(512)
        self.assertEquals(len(s), 512)
        for i in s:
            self.assertEquals(i, "\0")

    def vrfy_recv(self, tuple, msg):
        self.readfd_test(tuple[0])
        self.assertEquals(tuple[1], msg)

    def parent_tests(self, s):
        # First message is not even sent
        self.vrfy_recv(recvfd(s), "a")
        self.vrfy_recv(recvfd(s), "\0")
        self.vrfy_recv(recvfd(s), "foobar")
        self.vrfy_recv(recvfd(s, msg_buf = 11), "long string") # is long
        self.assertEquals(s.recv(8), " is long") # re-sync
        self.assertEquals(s.recv(100), "foobar")
        self.assertRaises(RuntimeError, recvfd, s) # No fd received

    def child_tests(self, s):
        f = file("/dev/zero")
        assert sendfd(s, f, "") == 0
        assert sendfd(s, f, "a") == 1
        assert sendfd(s, f, "\0") == 1
        assert sendfd(s, f, "foobar") == 6
        assert sendfd(s, f, "long string is long") == 19
        # The other side will recv() instead of recvmsg(), this fd would be
        # lost. I couldn't find any specification on this semantic
        assert sendfd(s, f, "foobar") == 6
        assert s.send("barbaz") == 6
        # Try to write!
        assert sendfd(s, f, "writing") == 7

    def test_passfd(self):
        (stream0, stream1) = socket.socketpair(socket.AF_UNIX,
                socket.SOCK_STREAM, 0)
        (dgram0, dgram1) = socket.socketpair(socket.AF_UNIX,
                socket.SOCK_DGRAM, 0)
        pid = os.fork()
        if pid == 0:
            stream0.close()
            dgram0.close()
            self.child_tests(stream1)
            self.child_tests(dgram1)
            stream1.close()
            dgram1.close()
            os._exit(0)

        stream1.close()
        dgram1.close()
        self.parent_tests(stream0)
        self.parent_tests(dgram0)
        stream0.close()
        dgram0.close()

        self.assertEquals(os.waitpid(pid, 0)[1], 0)

if __name__ == '__main__':
    unittest.main()

