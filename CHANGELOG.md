# Changelog

All notable changes to TGMark are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
