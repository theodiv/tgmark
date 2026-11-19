# TGMark

Turn any text into messages Telegram never refuses.

[![License: MIT](https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/theodiv/tgmark/main/pyproject.toml&query=$.project.license&style=flat-square&label=License&color=yellow)](https://github.com/theodiv/tgmark/blob/main/LICENSE)
[![Python: 3.11+](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/theodiv/tgmark/main/pyproject.toml&style=flat-square&label=Python)](https://www.python.org/downloads/)
[![CI](https://img.shields.io/github/actions/workflow/status/theodiv/tgmark/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/theodiv/tgmark/actions/workflows/ci.yml)

---

## Overview

TGMark turns plain text into Telegram messages that the Bot API server accepts
and keeps exactly as sent, split to fit its limits, and reports each change it
makes to get there. It serves Python bot authors whose text comes from
elsewhere, such as an LLM's reply, and scripts that post CI results or
monitoring alerts, through the `tgmark` command. Sending the messages stays with
the caller's Bot API client.

## Features

- **Kept as sent** — the characters the server removes or replaces are removed
  or replaced first, so the server keeps every message exactly as `convert`
  returns it.
- **Split to fit** — text longer than one message splits at the last paragraph
  break, line break, sentence end, or space that fits, and keeps flags, emoji
  sequences, and accented letters whole wherever they fit; `max_length` lowers
  the limit and `max_parts` caps the count.
- **Bytes as read** — `bytes` decode in the encoding their byte order mark
  names, UTF-8, UTF-16BE, or UTF-16LE, else as UTF-8, so a file or a pipe
  converts as read; each byte sequence the encoding refuses becomes U+FFFD with
  a diagnostic.
- **Every change reported** — each repair or removal comes back as a diagnostic
  with a stable code, a line, and a column, and never quotes the input.
- **Strict mode** — `strict=True` raises `ConversionError` at the earliest
  change instead, for text that must arrive as written.
- **Command line** — `tgmark` converts a file or stdin and writes each message's
  Bot API parameters to stdout as a line of JSON, with each diagnostic
  on stderr.

## Example

```pycon
>>> from tgmark import convert
>>> conversion = convert("Build #42:\tpassed\n", source="plain", target="entities")
>>> conversion.messages[0].params()
{'text': 'Build #42: passed'}
>>> conversion.diagnostics
(Diagnostic(code='control-character', message='control character replaced with a space', line=1, column=11),)
```

## Requirements

Python 3.11 or later. No runtime dependencies.

## Installation

```console
$ pip install tgmark
```

`pipx` installs the `tgmark` command in an environment of its own:

```console
$ pipx install tgmark
```

## Documentation

- [Library](https://github.com/theodiv/tgmark/blob/main/docs/library.md) — every
  public name, with its parameters, return value, and exceptions.
- [Command Line](https://github.com/theodiv/tgmark/blob/main/docs/cli.md) —
  the `tgmark` command: its usage, output, and exit codes.
- [Behavior](https://github.com/theodiv/tgmark/blob/main/docs/behavior.md) —
  what happens to the input, step by step, and the limits on it.
- [Compatibility](https://github.com/theodiv/tgmark/blob/main/docs/compatibility.md) —
  what a release may change, and what stays stable.

## Contributing

Development setup, coding standards, and the pull request process are documented
in the [contributing guide](https://github.com/theodiv/tgmark/blob/main/CONTRIBUTING.md).

## Code of Conduct

Expectations for every participant are set in the
[code of conduct](https://github.com/theodiv/tgmark/blob/main/CODE_OF_CONDUCT.md).

## Changelog

Every change is recorded in the [changelog](https://github.com/theodiv/tgmark/blob/main/CHANGELOG.md).

## Security

The vulnerability reporting and disclosure process is documented in the
[security policy](https://github.com/theodiv/tgmark/blob/main/SECURITY.md).

---

Distributed under the [MIT License](https://github.com/theodiv/tgmark/blob/main/LICENSE).
