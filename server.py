#!/usr/bin/env python3
import os
import re
import time
import json
from typing import List

from flask import Flask, render_template, request, redirect

from ducky.parser import parse, Command
from ducky.exceptions import DuckyParseError

app = Flask(
    __name__,
    static_url_path='/static',
    static_folder='static')

# Some config
HID_DEVICE = os.environ.get('HID_DEVICE', '/dev/hidg0')
SCRIPTS_DIR = os.environ.get('SCRIPTS_DIR', '/opt/ducky-scripts')


def list_scripts():
    return os.listdir(SCRIPTS_DIR)

def write_keystrokes(commands: List[Command]):
    with open(HID_DEVICE, 'wb') as dev:
        for command in commands:
            if command.payload:
                dev.write(command.payload)
                dev.flush()
            if command.delay > 0:
                delay_seconds = command.delay / 1000.0
                time.sleep(delay_seconds)


def validate_script_name(name: str):
    if not name:
        raise ValueError('name cannot be empty')
    if not re.match(r'[\w\.\-\_]+', name):
        raise ValueError('names can contain letters, numbers, period, hyphen and underscores only.')


@app.route('/', methods=['GET', 'POST'])
def live():
    scripts = list_scripts()
    form = request.form
    if request.method == 'GET':
        load = request.args.get('load')
        if load:
            content = None
            try:
                validate_script_name(load)
            except ValueError as ve:
                return render_template('index.html', form=form, scripts=scripts, error=ve)
            path = os.path.join(SCRIPTS_DIR, load)
            try:
                with open(path, 'r') as fd:
                    content = fd.read()
            except OSError as oe:
                return render_template('index.html', form=form, scripts=scripts, error=oe)
            form = dict(**form)
            form['script'] = content
        msg = request.args.get('msg')
        return render_template('index.html', form=form, scripts=scripts, msg=msg)
    # POST
    start = time.time()
    content = form.get('script')
    action = form.get('action')
    commands = []
    try:
        commands = parse(content)
    except DuckyParseError as pe:
        return render_template('index.html', form=form, scripts=scripts, error=pe)
    
    if action == 'validate':
        return render_template('index.html', form=form, scripts=scripts, validated=True)
    
    elif action == 'save':
        try:
            validate_script_name(form.get('name'))
        except ValueError as ve:
            return render_template('index.html', form=form, scripts=scripts, error=ve)
        path = os.path.join(SCRIPTS_DIR, form.get('name'))
        try:
            with open(path, 'w') as fd:
                fd.write(content)
        except OSError as oe:
            return render_template('index.html', form=form, scripts=scripts, error=oe)
        return render_template('index.html', scripts=list_scripts(), form={})
    
    elif action == 'run':
        try:
            write_keystrokes(commands)    
        except OSError as oe:
            return render_template('index.html', form=form, scripts=scripts, error=oe)
        return render_template('index.html', form=form, scripts=scripts, success=True, took=(time.time() - start))


@app.route('/delete')
def delete_script():
    # Yes, deleting files by passing user input to a GET request is not safe.
    # Please don't expose this app to the internet or give it to anyone you don't trust.
    name = request.args.get('script')
    try:
        validate_script_name(name)
    except ValueError as ve:
        return str(ve), 400
    path = os.path.join(SCRIPTS_DIR, name)
    if not os.path.exists(path):
        return 'Script not found', 404
    try:
        os.remove(path)
    except OSError as oe:
        return str(oe), 500
    return redirect('/?msg=deleted')

