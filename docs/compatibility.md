# Compatibility

What callers can rely on across releases.

## Versioning

Releases follow Semantic Versioning. Before 1.0.0, a minor release may break a
covered surface, and its changelog entry says so with **Breaking:**; a patch
release never breaks. From 1.0.0, only a major release breaks, after a minor
release has deprecated what it removes: the old form keeps working and warns,
naming its replacement and the release that removes it. A security fix may break
a surface in a patch release, and its changelog entry names the old and the
new behavior.

## What Is Covered

- Every name in `tgmark.__all__`, with its parameters and return values.
- The command's flags, output, exit codes, and diagnostic prefixes.
- The behavior these pages describe.

## What Is Not Covered

- Names that start with `_`, and behavior these pages do not describe.
- The wording of exception messages.
- The wording of a diagnostic's `message`, and of a diagnostic line after its
  prefix, apart from the code in brackets that ends a warning line.
- Development releases (`.devN`) and release candidates (`rcN`).

## Diagnostic Codes

A diagnostic code keeps its name and its condition once released: no release
renames, removes, or reuses one, and each warning line of the command ends with
the code of the diagnostic it reports, in brackets.

## Python Versions

Python 3.11 to 3.15. A minor release may drop a Python version after its end of
life, and its changelog entry names it.
