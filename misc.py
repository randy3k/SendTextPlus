import sublime
import re


def clean(cmd):
    cmd = cmd.expandtabs(4)
    cmd = cmd.rstrip('\n')
    if len(re.findall("\n", cmd)) == 0:
        cmd = cmd.lstrip()
    return cmd


def escape_dq(cmd):
    cmd = cmd.replace('\\', '\\\\')
    cmd = cmd.replace('"', '\\"')
    return cmd


def get_syntax(view):
    pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0
    if view.score_selector(pt, "source.r"):
        return "r"
    elif view.score_selector(pt, "source.python"):
        return "python"
    elif view.score_selector(pt, "source.julia"):
        return "julia"


def syntax_settings(view, key, default=None):
    syntax = get_syntax(view)
    settings = sublime.load_settings("SendTextPlus.sublime-settings")
    ret = None
    plat = sublime.platform()
    if syntax:
        lang_settings = settings.get(syntax)
        os_settings = lang_settings.get(plat)
        if os_settings:
            ret = os_settings.get(key)
        if ret is None:
            ret = lang_settings.get(key)
    if ret is None:
        ret = settings.get("default").get(plat).get(key)
    if ret is None:
        ret = default
    return ret
