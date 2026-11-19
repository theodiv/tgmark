# Command Line

*Added in the next release.*

The `tgmark` command: its usage, input, output, and exit codes. What a
result means: [Behavior](behavior.md).

## Usage

`tgmark --help` prints:

```text
usage: tgmark -s SOURCE -t TARGET [-h] [-V] [FILE]

Convert text into Telegram messages that the Bot API server keeps as sent.

positional arguments:
  FILE                 the input file, at most 4 MiB; stdin when absent or -

options:
  -s, --source SOURCE  the format of the text: plain
  -t, --target TARGET  the form of each message: entities
  -h, --help           show this help message and exit
  -V, --version        show program's version number and exit

Writes each message's Bot API parameters to stdout as a line of JSON.
```

## Options

- `-s`, `--source` — passed to `convert` as
  `source` ([Library](library.md#convert)).
- `-t`, `--target` — passed to `convert` as
  `target` ([Library](library.md#convert)).

## Input

`FILE`, or stdin when `FILE` is absent or `-`, as bytes: at most 4 MiB, decoded
as `convert` decodes `bytes` ([Library](library.md#convert)), whatever the
locale. More than 4 MiB is refused with exit code `65`.

## Output

One line of JSON per message on stdout, in order: the object `Message.params()`
returns ([Library](library.md#message)), in ASCII, each other character escaped
as `\uXXXX`, or as two of them past U+FFFF. Nothing when no message remains
to send.

## Exit Codes

| Code | Meaning                                                         |
| ---  | ---                                                             |
| `0`  | The input is converted, with a warning line for each diagnostic |
| `1`  | An unexpected failure, reported in one line                     |
| `2`  | The arguments are invalid                                       |
| `65` | The input holds more than 4 MiB                                 |
| `66` | `FILE` cannot be opened                                         |
| `74` | Reading `FILE` or stdin, or writing stdout, fails               |

## Diagnostics

| Prefix              | When                                        |
| ---                 | ---                                         |
| `tgmark: error: `   | A failure that sets a non-zero exit code    |
| `tgmark: warning: ` | A condition that leaves the exit code alone |

A warning line reports one diagnostic of the conversion
([Library](library.md#diagnostic)): its message, its line and column, and its
code in brackets. An error line names what failed, and a path in it shows at
most its last 32 characters, each non-printable character escaped. An interrupt
ends the command with `tgmark: error: interrupted` and exit code `1`.

## Examples

```console
$ printf 'Build #42:\tpassed\n' | tgmark -s plain -t entities
tgmark: warning: control character replaced with a space at line 1, column 11 [control-character]
{"text": "Build #42: passed"}
```

```console
$ printf 'Café 👋\n' > greeting.txt
$ tgmark --source plain --target entities greeting.txt
{"text": "Café 👋"}
```

```console
$ tgmark -s plain -t entities missing.txt
tgmark: error: cannot open 'missing.txt': No such file or directory
```
