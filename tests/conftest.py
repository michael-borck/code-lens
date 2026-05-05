# tests/conftest.py
import json
import pytest

VALID_PYTHON = '''\
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}"

def evens(n: int) -> list[int]:
    return [x for x in range(n) if x % 2 == 0]

if __name__ == "__main__":
    print(greet("world"))
'''

PYTHON_WITH_ISSUES = '''\
import os, sys

def bad():
    try:
        x = 1
    except:
        pass
    print("debug")
    todo = [i for i in range(10)]  # TODO fix this
    return todo
'''

VALID_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><title>Test Page</title></head>
<body>
  <header><h1>Hello</h1></header>
  <main>
    <p>Content</p>
    <img src="a.png" alt="An image">
    <label for="name">Name</label>
    <input id="name" type="text">
  </main>
  <footer><p>Footer</p></footer>
</body>
</html>"""

DIV_SOUP_HTML = """\
<!DOCTYPE html>
<html><head><title>Test</title></head>
<body>
  <div><div><div><div>content</div></div></div></div>
  <div onclick="doThing()" onchange="other()">click</div>
  <div><img src="x.png"><input type="text"></div>
</body>
</html>"""

VALID_CSS = """\
body { margin: 0; padding: 0; }
.container { display: flex; justify-content: center; }
.grid-layout { display: grid; grid-template-columns: 1fr 1fr; }
:root { --primary: #333; }
@media (max-width: 768px) { .container { flex-direction: column; } }
"""

FLOAT_CSS = """\
.sidebar { float: left; width: 200px; }
.content { float: left; width: calc(100% - 200px); }
.clearfix::after { content: ""; display: table; clear: both; }
"""

VALID_JS = """\
import { helper } from './utils.js';

function greet(name) {
  // say hello
  console.log('Hello ' + name);
  return name;
}

const double = (x) => x * 2;
const asyncLoad = async () => { return await fetch('/api'); };
"""

VALID_TS = """\
import { Component } from '@angular/core';

function greet(name: string): string {
  return `Hello, ${name}`;
}

interface User {
  name: string;
  age: number;
}

type ID = string | number;

const add = (a: number, b: number): number => a + b;
"""

VALID_SQL = """\
SELECT id, name FROM users WHERE active = 1;
SELECT u.id, o.total FROM users u JOIN orders o ON u.id = o.user_id;
INSERT INTO logs (user_id, action) VALUES (1, 'login');
UPDATE users SET last_login = NOW() WHERE id = 1;
DELETE FROM sessions WHERE expired = 1;
"""

UNSAFE_SQL = """\
UPDATE users SET name = 'hacked';
DELETE FROM logs;
SELECT * FROM users;
"""

VALID_NOTEBOOK = {
    "nbformat": 4,
    "nbformat_minor": 4,
    "cells": [
        {
            "cell_type": "markdown",
            "source": "# Analysis",
            "metadata": {},
            "outputs": [],
        },
        {
            "cell_type": "code",
            "source": "x = 1\nprint(x)",
            "execution_count": 1,
            "metadata": {},
            "outputs": [],
        },
        {
            "cell_type": "code",
            "source": "%matplotlib inline\nimport os",
            "execution_count": 2,
            "metadata": {},
            "outputs": [],
        },
    ],
    "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
}

NOTEBOOK_WITH_OUTPUTS = {
    "nbformat": 4,
    "nbformat_minor": 4,
    "cells": [
        {
            "cell_type": "code",
            "source": "print('hello')",
            "execution_count": 1,
            "metadata": {},
            "outputs": [{"output_type": "stream", "name": "stdout", "text": "hello\n"}],
        },
        {
            "cell_type": "code",
            "source": "print('world')",
            "execution_count": 3,
            "metadata": {},
            "outputs": [],
        },
    ],
    "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
}
