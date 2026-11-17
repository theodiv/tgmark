# Behavior

TGMark turns plain text into the text of Telegram messages that the Bot API
server keeps exactly as sent: before anything is sent, it makes each change the
server would make, and it reports each change as a diagnostic. Everything else
links here for what a result means.

## Processing

The steps run in this order:

| #   | Step                                                                                                                                                                    | Result                                                                        |
| --- | ---                                                                                                                                                                     | ---                                                                           |
| 1   | A lone surrogate, U+D800 to U+DFFF, which the server refuses as invalid UTF-8                                                                                           | U+FFFD, with a `lone-surrogate` diagnostic                                    |
| 2   | A line ending: LF, CR, or CR LF                                                                                                                                         | LF                                                                            |
| 3   | A control character, U+0000 to U+001F, other than LF                                                                                                                    | A space, as the server makes it, with a `control-character` diagnostic        |
| 4   | U+2028 to U+202E, U+030A, U+0333, or U+033F                                                                                                                             | Removed, as the server removes it, with an `unsupported-character` diagnostic |
| 5   | U+200E or U+200F directly followed by another of the two                                                                                                                | U+200C, as the server makes it, with a `direction-mark` diagnostic            |
| 6   | Spaces and line feeds at either end                                                                                                                                     | Trimmed, as the server trims them                                             |
| 7   | Nothing left but blank characters: spaces, line feeds, U+00A0, U+1680, U+180E, U+2000 to U+200F, U+202F, U+205F, U+2800, U+3000, U+FEFF, U+FFFC, and U+E0000 to U+E007F | No message, since the server refuses it, with a `blank-text` diagnostic       |
| 8   | More than 4,096 code points left                                                                                                                                        | No message, with a `text-too-long` diagnostic                                 |

## Limits

| Limit                  | Value             | Past it                                       |
| ---                    | ---               | ---                                           |
| Kept text of a message | 4,096 code points | No message, with a `text-too-long` diagnostic |

## Guarantees

- The Bot API server accepts every message `convert` returns and keeps its text
  exactly as sent, as the server's code at Bot API 10.4 behaves. TDLib Oracle,
  which reproduces that code, checks every message the tests produce.
- Only the steps in Processing lose or change text, and each step but 2 and 6
  reports every change it makes as a diagnostic.
- A diagnostic or a `ConversionError` names a line and a column of the input and
  never quotes its text.
- Outside strict mode, `convert` raises only `TypeError` and `ValueError`, for
  its arguments.
- Time and memory grow linearly with the length of the input.

Threats and how to report them: [`SECURITY.md`](../SECURITY.md).

## Out of Scope

- Sending messages, and any network access — the caller's Bot API client sends
  what `Message.params()` returns.
- Media, keyboards, link previews, and every other send parameter — the caller
  adds them to what `Message.params()` returns.
- Converting partial input as it streams in — the caller converts the whole text
  once it has it.
- The rules Telegram's backend applies after the server's code — only a send to
  Telegram itself meets them.

## Terms

- **lenient mode** — the default: each condition in Processing is repaired or
  dropped, and reported as a diagnostic.
- **strict mode** — `strict=True`: the condition at the earliest position raises
  `ConversionError` instead.
