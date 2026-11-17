# TGMark

Turn any text into messages Telegram never refuses.

[![License: MIT](https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/theodiv/tgmark/main/pyproject.toml&query=$.project.license&style=flat-square&label=License&color=yellow)](https://github.com/theodiv/tgmark/blob/main/LICENSE)
[![Python: 3.11+](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/theodiv/tgmark/main/pyproject.toml&style=flat-square&label=Python)](https://www.python.org/downloads/)
[![CI](https://img.shields.io/github/actions/workflow/status/theodiv/tgmark/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/theodiv/tgmark/actions/workflows/ci.yml)

---

## Status

Pre-release: TGMark is in development and nothing is published. The first
release is `0.1.0`; the [changelog](https://github.com/theodiv/tgmark/blob/main/CHANGELOG.md)
records every change until then.

## Overview

TGMark turns plain text into Telegram messages that the Bot API server accepts
and keeps exactly as sent, and reports each change it makes to get there. It
serves Python bot authors whose text comes from elsewhere, such as an LLM's
reply or a script's output. Sending the messages stays with the caller's Bot
API client.

## Features

- **Kept as sent** — the characters the server removes or replaces are removed
  or replaced first, so the server keeps every message exactly as `convert`
  returns it.
- **Every change reported** — each repair or removal comes back as a diagnostic
  with a stable code, a line, and a column, and never quotes the input.
- **Strict mode** — `strict=True` raises `ConversionError` at the earliest
  change instead, for text that must arrive as written.

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

## Documentation

- [Library](https://github.com/theodiv/tgmark/blob/main/docs/library.md) — every
  public name, with its parameters, return value, and exceptions.
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
