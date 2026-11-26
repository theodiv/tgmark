# Changelog

All notable changes to TGMark are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Accept `bytes` in `convert`, decoded in the encoding that a UTF-8, UTF-16BE,
  or UTF-16LE byte order mark names, else as UTF-8. Each byte sequence the
  encoding refuses becomes U+FFFD, with an `undecodable-bytes` diagnostic.
- Add the `tgmark` command, which converts a file or stdin of up to 4 MiB and
  writes each message's Bot API parameters to stdout as a line of JSON, with
  each diagnostic on stderr as a warning line that ends in its code.
  `--max-length`, `--max-parts`, and `--strict` set the options of `convert`
  they name, and `--strict` exits `65` at the earliest condition.

### Changed

- Point a release's docs links, in its PyPI description and its `Documentation`
  URL, at its own tag; the installed code and every other link stay the same.
  Previously, they opened the docs on `main`, which can describe features the
  release lacks.

## [0.1.0] - 2026-11-18

### Added

- Add `convert`, which turns plain text into Telegram messages that the Bot API
  server keeps exactly as sent, and reports each change it makes as a diagnostic
  with a code, a line, and a column. `strict=True` raises `ConversionError` at
  the earliest change instead.
- Split text longer than one message into several, each ending at the last
  paragraph break, line break, sentence end, or space that fits, and cut a
  grapheme cluster only when it alone is longer than a message, with a
  `cluster-too-long` diagnostic. Add `max_length` to lower the length of each
  message and `max_parts` to cap their number, dropping the rest with a
  `truncated` diagnostic.

[Unreleased]: https://github.com/theodiv/tgmark/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/theodiv/tgmark/releases/tag/v0.1.0
