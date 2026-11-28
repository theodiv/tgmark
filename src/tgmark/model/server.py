"""The Bot API server's rules on the text of a message.

This module alone states the rules, each as the code of the Bot API server and TDLib
behaves at the commits that the TDLib Oracle release in the `dev` group reproduces, even
where Telegram's documentation says otherwise.
"""

# The most code points a message keeps, counted once the text is cleaned and trimmed
# (td/telegram/MessageContent.cpp, create_input_message_content()). The value is the
# default of the option message_text_length_max, which Telegram's configuration never
# lowers (td/telegram/OptionManager.cpp, OptionManager::OptionManager();
# td/telegram/ConfigManager.cpp, ConfigManager::process_config()).
MESSAGE_LENGTH = 4096

# The control characters the server turns into spaces: every C0 control character but
# the line feed and the carriage return (td/telegram/misc.cpp, clean_input_string()).
SPACED = frozenset(chr(code) for code in range(0x20) if code not in (0x0A, 0x0D))

# The characters the server removes: the carriage return, U+2028 to U+202E, and the
# combining marks U+030A, U+0333, and U+033F
# (td/telegram/misc.cpp, clean_input_string()).
REMOVED = frozenset("\r\u030a\u0333\u033f") | frozenset(map(chr, range(0x2028, 0x202F)))

# The direction marks, each of which the server turns into MARK_REPLACEMENT when another
# of the two directly follows it (td/telegram/misc.cpp, replace_offending_characters()).
DIRECTION_MARKS = frozenset("\u200e\u200f")
MARK_REPLACEMENT = "\u200c"

# The characters the server trims from both ends of a text
# (td/telegram/MessageEntity.cpp, fix_formatted_text()).
TRIMMED = " \n"

# The characters the server counts as blank: it refuses a text that holds nothing else
# (td/telegram/misc.cpp, strip_empty_characters()).
BLANK = (
    frozenset(" \n\u00a0\u1680\u180e\u202f\u205f\u2800\u3000\ufeff\ufffc")
    | frozenset(map(chr, range(0x2000, 0x2010)))
    | frozenset(map(chr, range(0xE0000, 0xE0080)))
)
