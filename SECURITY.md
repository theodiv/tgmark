# Security Policy

## Supported Versions

Only the latest released version of TGMark receives security fixes. Older
releases are not patched.

## Reporting a Vulnerability

Report vulnerabilities privately; never open a public issue for one.

- **GitHub private vulnerability reporting** (preferred): open a draft advisory
  on the [security advisories page](https://github.com/theodiv/tgmark/security/advisories/new).
- **Email**: `theodiv@gmail.com`.

## Disclosure Process

1. The maintainer acknowledges the report within **72 hours**.
2. The maintainer confirms or declines the report and assesses its severity
   within **7 days** of receiving it.
3. The fix is developed and tested in the advisory's temporary private fork.
4. Disclosure is coordinated with the reporter, targeting **30 days** from
   confirmation; complex issues may take longer.
5. The patched release and the advisory are published together.
6. The advisory credits the reporter unless anonymity is requested.

## Threat Model

- **Unbounded work** — conversion runs in time and memory linear in the input,
  with no recursion and no regular expression with nested quantifiers, so a long
  or crafted text cannot stall the caller.
- **Input in diagnostics** — a diagnostic or a `ConversionError` names a line
  and a column and never quotes the input, so logging one copies no message text
  into the logs.
- **Message floods** — long input splits into as many messages as it needs, so
  text from an untrusted source can make a bot send hundreds; `max_parts` caps
  the count and drops the rest with a `truncated` diagnostic.

## Out of Scope

- The behavior of the Telegram Bot API server itself: which messages it accepts,
  and what it keeps of their text and formatting. Report it on the
  [telegram-bot-api issue tracker](https://github.com/tdlib/telegram-bot-api/issues).
- The caller's own files and code: the input the caller passes to TGMark, and
  what the caller does with the messages it returns.

## Hardening

- **Cap the message count** of text from an untrusted source: `max_parts` keeps
  one input from flooding a chat or using up the bot's rate limit.
