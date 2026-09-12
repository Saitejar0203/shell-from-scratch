"""Turn command-line text into words and redirection instructions."""


def parse_command(command):
    """Read words and operators, respecting quotes and backslash escapes.

    Tokens are (kind, value, quoted). Word values are strings; redirect
    values are (descriptor, mode), such as (2, "a") for stderr append.
    """
    tokens = []
    current = []
    quote = None
    argument_started = False
    argument_quoted = False

    characters = iter(enumerate(command))
    for index, character in characters:
        if quote is not None:
            if character == quote:
                quote = None
            elif quote == '"' and character == "\\":
                _, escaped = next(characters, (None, None))
                if escaped is None:
                    raise ValueError("unmatched quote")
                if escaped not in '\\"$`':
                    current.append("\\")
                current.append(escaped)
            else:
                current.append(character)
        elif character == "\\":
            _, escaped = next(characters, (None, None))
            if escaped is None:
                raise ValueError("trailing backslash")
            current.append(escaped)
            argument_started = True
            argument_quoted = True
        elif character in "\"'":
            quote = character
            argument_started = True
            argument_quoted = True
        elif character in "&|":
            if argument_started:
                tokens.append(("word", "".join(current), argument_quoted))
            tokens.append(("background" if character == "&" else "pipe", character, False))
            current = []
            argument_started = False
            argument_quoted = False
        elif character == ">":
            word = "".join(current)
            descriptor = 1
            if argument_started and not argument_quoted and word.isdecimal():
                if word not in ("1", "2"):
                    raise ValueError("only stdout and stderr redirection are supported")
                descriptor = int(word)
            elif argument_started:
                tokens.append(("word", word, argument_quoted))
            mode = "w"
            if index + 1 < len(command) and command[index + 1] == ">":
                next(characters)
                mode = "a"
            tokens.append(("redirect", (descriptor, mode), False))
            current = []
            argument_started = False
            argument_quoted = False
        elif character in " \t":
            if argument_started:
                tokens.append(("word", "".join(current), argument_quoted))
                current = []
                argument_started = False
                argument_quoted = False
        else:
            current.append(character)
            argument_started = True

    if quote is not None:
        raise ValueError("unmatched quote")
    if argument_started:
        tokens.append(("word", "".join(current), argument_quoted))

    # Each token retains its kind, text, and quote information.
    return tokens


def extract_redirections(tokens):
    """Separate command words from ordered (descriptor, path, mode) actions."""
    arguments = []
    quoted_arguments = []
    destinations = []
    index = 0
    while index < len(tokens):
        kind, value, quoted = tokens[index]
        if kind == "redirect":
            descriptor, mode = value
            operator = ">>" if mode == "a" else ">"
            index += 1
            if index == len(tokens) or tokens[index][0] != "word":
                raise ValueError(f"expected filename after {descriptor}{operator}")
            destinations.append((descriptor, tokens[index][1], mode))
        else:
            arguments.append(value)
            quoted_arguments.append(quoted)
        index += 1
    return arguments, quoted_arguments, destinations


def extract_background(tokens):
    """Remove a final unquoted &, rejecting unsupported command lists."""
    background = bool(tokens and tokens[-1][0] == "background")
    if background:
        tokens = tokens[:-1]
    if any(kind == "background" for kind, _, _ in tokens):
        raise ValueError("& is only supported at the end of a command")
    if background and not tokens:
        raise ValueError("expected command before &")
    return tokens, background


def split_pipeline(tokens):
    """Split on operator tokens, never quoted or escaped pipe characters."""
    stages = [[]]
    for token in tokens:
        if token[0] == "pipe":
            if not stages[-1]:
                raise ValueError("expected command before pipe")
            stages.append([])
        else:
            stages[-1].append(token)
    if len(stages) > 1 and not stages[-1]:
        raise ValueError("expected command after pipe")
    return stages
