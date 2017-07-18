# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
import json
from collections import OrderedDict

import pytest

from gcdt.utils import version, __version__, retries,  \
    get_command, dict_merge, get_env, get_context, flatten, json2table, \
    fix_old_kumo_config
from gcdt_testtools.helpers import create_tempfile, preserve_env  # fixtures!

from . import here


PY3 = sys.version_info[0] >= 3


def test_version(capsys):
    version()
    out, err = capsys.readouterr()
    assert out.strip().startswith('gcdt version %s' % __version__)


# would love to use logging for that...
#def test_version(caplog):
#    # https://github.com/eisensheng/pytest-catchlog
#    version()
#
#    record_tuples = list(caplog.records)
#    assert record_tuples[0].getMessage().startswith('gcdt version ')
#    assert record_tuples[0].levelno == logging.INFO


def test_retries_backoff():
    state = {'r': 0, 'h': 0, 'backoff': 2, 'tries': 5, 'mydelay': 0.1}

    def a_hook(tries_remaining, e, delay):
        assert tries_remaining == (state['tries'] - state['r'])
        assert str(e) == 'test retries!'
        assert delay == state['mydelay']
        state['mydelay'] *= state['backoff']
        state['h'] += 1

    @retries(state['tries'], delay=0.1, backoff=state['backoff'], hook=a_hook)
    def works_after_four_tries():
        state['r'] += 1
        if state['r'] < 5:
            raise Exception('test retries!')

    works_after_four_tries()
    assert state['r'] == 5


def test_retries_until_it_works():
    state = {'r': 0, 'h': 0}

    def a_hook(tries_remaining, e, delay):
        state['h'] += 1

    @retries(20, delay=0, exceptions=(ZeroDivisionError,), hook=a_hook)
    def works_after_four_tries():
        state['r'] += 1
        if state['r'] < 5:
            x = 5/0

    works_after_four_tries()
    assert state['r'] == 5
    assert state['h'] == 4


def test_retries_raises_exception():
    state = {'r': 0, 'h': 0, 'tries': 5}

    def a_hook(tries_remaining, e, delay):
        assert tries_remaining == (state['tries'] - state['r'])
        assert str(e) in ['division by zero', 'integer division or modulo by zero']
        assert delay == 0.0
        state['h'] += 1

    @retries(state['tries'], delay=0,
             exceptions=(ZeroDivisionError,), hook=a_hook)
    def never_works():
        state['r'] += 1
        x = 5/0

    try:
        never_works()
    except ZeroDivisionError:
        pass
    else:
        raise Exception("Failed to Raise ZeroDivisionError")

    assert state['r'] == 5
    assert state['h'] == 4


def test_command_version():
    arguments = {
        '-f': False,
        'configure': False,
        'delete': False,
        'version': True
    }
    assert get_command(arguments) == 'version'


def test_command_delete_f():
    arguments = {
        '-f': True,
        'configure': False,
        'delete': True,
        'version': False
    }
    assert get_command(arguments) == 'delete'


def test_dict_merge():
    a = {'1': 1, '2': [2], '3': {'3': 3}}
    dict_merge(a, {'3': 3})
    assert a == {'1': 1, '2': [2], '3': 3}

    dict_merge(a, {'4': 4})
    assert a == {'1': 1, '2': [2], '3': 3, '4': 4}

    dict_merge(a, {'4': {'4': 4}})
    assert a == {'1': 1, '2': [2], '3': 3, '4': {'4': 4}}

    dict_merge(a, {'4': {'5': 5}})
    assert a == {'1': 1, '2': [2], '3': 3, '4': {'4': 4, '5': 5}}

    dict_merge(a, {'2': [2, 2], '4': [4]})
    assert a == {'1': 1, '2': [2, 2], '3': 3, '4': [4]}


def test_get_env(preserve_env):
    # used in cloudformation!
    os.environ['ENV'] = 'LOCAL'
    assert get_env() == 'local'

    del os.environ['ENV']
    assert get_env() == None

    os.environ['ENV'] = 'NONE_SENSE'
    assert get_env() == 'none_sense'


def test_get_context():
    context = get_context('awsclient', 'env', 'tool', 'command',
                          arguments={'foo': 'bar'})

    assert context['_awsclient'] == 'awsclient'
    assert context['env'] == 'env'
    assert context['tool'] == 'tool'
    assert context['command'] == 'command'
    assert context['_arguments'] == {'foo': 'bar'}
    assert 'gcdt-bundler' in context['plugins']
    assert 'gcdt-lookups' in context['plugins']


def test_flatten():
    actual = flatten(['junk', ['nested stuff'], [], [[]] ])
    assert actual == ['junk', 'nested stuff']


# 3 tests moved from test_ramuda.py
def test_json2table():
    data = {
        'sth': 'here',
        'number': 1.1,
        'ResponseMetadata': 'bla'
    }
    expected = u'\u2552\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2564\u2550\u2550\u2550\u2550\u2550\u2550\u2555\n\u2502 sth    \u2502 here \u2502\n\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2524\n\u2502 number \u2502 1.1  \u2502\n\u2558\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2567\u2550\u2550\u2550\u2550\u2550\u2550\u255b'
    actual = json2table(data)
    assert actual == expected


def test_json2table_create_lambda_response():
    response = OrderedDict([
        ('CodeSha256', 'CwEvufZaAmNgUnlA6yTJGi8p8MNR+mNcCNYPOIwsTNM='),
        ('FunctionName', 'jenkins-gcdt-lifecycle-for-ramuda'),
        ('CodeSize', 430078),
        ('MemorySize', 256),
        ('FunctionArn', 'arn:aws:lambda:eu-west-1:644239850139:function:jenkins-gcdt-lifecycle-for-ramuda'),
        ('Version', '13'),
        ('Role', 'arn:aws:iam::644239850139:role/lambda/dp-dev-store-redshift-cdn-lo-LambdaCdnRedshiftLoad-DD2S84CZFGT4'),
        ('Timeout', 300),
        ('LastModified', '2016-08-23T15:27:07.658+0000'),
        ('Handler', 'handler.handle'),
        ('Runtime', 'python2.7'),
        ('Description', 'lambda test for ramuda')
    ])

    expected_file = here('resources/expected/expected_json2table.txt')
    with open(expected_file) as efile:
        expected = efile.read()
        if not PY3:
            expected = expected.decode('utf-8')
    actual = json2table(response)  #.encode('utf-8')
    assert actual == expected


def test_json2table_exception():
    data = json.dumps({
        'sth': 'here',
        'number': 1.1,
        'ResponseMetadata': 'bla'
    })
    actual = json2table(data)
    assert actual == data


def test_fix_old_kumo_config():
    config = {
        'kumo': {
            'cloudformation': {
                'StackName': 'my_stack_name',
                'InstanceType': 't2.micro'
            }
        }
    }
    exp_config = {
        'kumo': {
            'stack': {
                'StackName': 'my_stack_name'
            },
            'parameters': {
                'InstanceType': 't2.micro'
            }
        }
    }

    fix_old_kumo_config(config)
    assert config == exp_config


def test_fix_old_kumo_config_no_change():
    config = {
        'kumo': {
            'stack': {
                'StackName': 'my_stack_name'
            },
            'parameters': {
                'InstanceType': 't2.micro'
            }
        }
    }
    exp_config = {
        'kumo': {
            'stack': {
                'StackName': 'my_stack_name'
            },
            'parameters': {
                'InstanceType': 't2.micro'
            }
        }
    }

    fix_old_kumo_config(config)
    assert config == exp_config


def test_fix_old_kumo_config_no_parameters():
    config = {
        'kumo': {
            'cloudformation': {
                'StackName': 'my_stack_name',
            }
        }
    }
    exp_config = {
        'kumo': {
            'stack': {
                'StackName': 'my_stack_name'
            }
        }
    }

    fix_old_kumo_config(config)
    assert config == exp_config

# TODO get_outputs_for_stack
# TODO test_make_command

