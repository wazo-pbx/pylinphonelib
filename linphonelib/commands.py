# -*- coding: utf-8 -*-

# Copyright (C) 2013-2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import itertools
import pexpect

from linphonelib.exceptions import ExtensionNotFoundException
from linphonelib.exceptions import LinphoneException
from linphonelib.exceptions import NoActiveCallException


class _BaseCommand(object):

    _successes = []
    _fails = []
    _defaults = [pexpect.EOF, pexpect.TIMEOUT]

    def execute(self, process):
        cmd_string = self._build_command_string()
        process.sendline(cmd_string)
        result = process.expect(self._param_list())
        self._handle_result(result)

    def _param_list(self):
        return list(itertools.chain(self._successes, self._fails, self._defaults))

    def _handle_result(self, result):
        raise NotImplementedError('No result handler on command %s', self.__class__)


class AnswerCommand(_BaseCommand):

    _successes = ['Call \d+ with .* connected.']
    _fails = ['There are no calls to answer.']

    def __eq__(self, other):
        return type(self) == type(other)

    def _handle_result(self, result):
        if result >= len(self._successes):
            print 'throw'
            raise LinphoneException('Failed to answer the call')

    @staticmethod
    def _build_command_string():
        return 'answer'


class CallCommand(_BaseCommand):

    _successes = [
        'Remote ringing.',
        'Call answered by <sip:.*>.',
    ]
    _fails = ['Not Found']

    def __init__(self, exten):
        self._exten = exten

    def __eq__(self, other):
        return self._exten == other._exten

    def _handle_result(self, result):
        if result == 2:
            raise ExtensionNotFoundException('Failed to call %s' % self._exten)
        elif result > len(self._successes):
            raise LinphoneException('Failed to call %s' % self._exten)

    def _build_command_string(self):
        return 'call %s' % self._exten


class HangupCommand(_BaseCommand):

    _successes = ['Call ended']
    _fails = ['No active calls']

    def __eq__(self, other):
        return type(self) == type(other)

    def _build_command_string(self):
        return 'terminate'

    def _handle_result(self, result):
        last_success = len(self._successes)
        last_fail = len(self._fails) + last_success
        if result < last_success:
            return
        elif result < last_fail:
            fail_idx = result - last_success
            if self._fails[fail_idx] == 'No active calls':
                raise NoActiveCallException()
            else:
                raise LinphoneException('Hangup failed: %s', self._fails[fail_idx])
        if result >= len(self._successes):
            raise LinphoneException('Hangup failed')


class RegisterCommand(_BaseCommand):

    _successes = ['Registration on sip:.* successful.']
    _fails = ['Registration on sip:.* failed:.*']

    def __init__(self, uname, passwd, hostname):
        self._uname = uname
        self._passwd = passwd
        self._hostname = hostname

    def __eq__(self, other):
        return (
            self._uname == other._uname
            and self._passwd == other._passwd
            and self._hostname == other._hostname
        )

    def _handle_result(self, result):
        if result == 1:
            raise LinphoneException('Registration failed')
        elif result == 2:
            raise LinphoneException('Registration returned no result')
        elif result == 3:
            raise LinphoneException('pexpect timeout on registration')

    def _build_command_string(self):
        cmd_string = 'register sip:%(name)s@%(host)s %(host)s %(passwd)s'
        return cmd_string % {'name': self._uname, 'passwd': self._passwd, 'host': self._hostname}


class UnregisterCommand(_BaseCommand):

    _successes = ['Unregistration on sip:.* done.']
    _fails = ['unregistered']

    def __eq__(self, other):
        return type(other) == type(self)

    def _handle_result(self, result):
        if result != 0:
            raise LinphoneException('Unregister failed')

    def _build_command_string(self):
        return 'unregister'
