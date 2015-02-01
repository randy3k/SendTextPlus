import sublime
import re
from .misc import get_syntax


def expand_block_r(view, sel):
    # expand selection to {...}
    thiscmd = view.substr(view.line(sel))
    if re.match(r".*\{\s*$", thiscmd):
        esel = view.find(
            r"""^(?:.*(\{(?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^\{\}]|(?1))*\})[^\{\}\n]*)+""",
            view.line(sel).begin()
        )
        if view.line(sel).begin() == esel.begin():
            sel = esel
    return sel


def expand_block_python(view, sel):
    thiscmd = view.substr(view.line(sel))
    if re.match(r"^[ \t]*\S", thiscmd):
        indentation = re.match(r"^([ \t]*)", thiscmd).group(1)
        row = view.rowcol(sel.begin())[0]
        prevline = view.line(sel.begin())
        lastrow = view.rowcol(view.size())[0]
        while row < lastrow:
            row = row + 1
            line = view.line(view.text_point(row, 0))
            m = re.match(r"^([ \t]*)([^\n\s]+)", view.substr(line))
            if m and len(m.group(1)) <= len(indentation) and \
                    (len(m.group(1)) < len(indentation) or
                        not re.match(r"else|elif|except|finally", m.group(2))):
                sel = sublime.Region(sel.begin(), prevline.end())
                break
            elif re.match(r"^[ \t]*\S", view.substr(line)):
                prevline = line

        if row == lastrow:
            sel = sublime.Region(sel.begin(), prevline.end())
    return sel


def expand_block_julia(view, sel):
    thiscmd = view.substr(view.line(sel))
    if (re.match(r"^\s*(?:function|if|for|while)", thiscmd) and
            not re.match(r".*end\s*$", thiscmd)) or \
            (re.match(r".*begin\s*$", thiscmd)):
        indentation = re.match("^(\s*)", thiscmd).group(1)
        end = view.find("^"+indentation+"end", sel.begin())
        sel = sublime.Region(sel.begin(), view.line(end.end()).end())

    return sel


def expand_block(view, sel):
    syntax = get_syntax(view)
    if syntax == "r":
        esel = expand_block_r(view, sel)
    elif syntax == "python":
        esel = expand_block_python(view, sel)
    elif syntax == "julia":
        esel = expand_block_julia(view, sel)
    return esel
