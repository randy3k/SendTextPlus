import sublime
import sublime_plugin
import os
import subprocess
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


def iTerm_version():
    try:
        args = ['osascript', '-e',
                'tell app "iTerm" to tell the first terminal to set foo to true']
        subprocess.Popen(args)
        return 2.9
    except:
        return 2.0


def sendtext(view, cmd):
    if cmd.strip() == "":
        return
    plat = sublime.platform()
    prog = syntax_settings(view, "prog")
    settings = sublime.load_settings("SendTextPlus.sublime-settings")

    if re.match('Terminal', prog):
        cmd = clean(cmd)
        cmd = escape_dq(cmd)
        args = ['osascript']
        args.extend(['-e', 'tell app "Terminal" to do script "' + cmd + '" in front window'])
        subprocess.Popen(args)

    elif re.match('iTerm', prog):
        cmd = clean(cmd)
        cmd = escape_dq(cmd)
        cmd = cmd.split("\n")
        line_len = [len(c) for c in cmd]
        k = 0
        ver = iTerm_version()
        while k < len(line_len):
            for j in range(k + 1, len(line_len) + 1):
                if sum(line_len[k:(j+1)]) > 1000:
                    break
            chunk = "\n".join(cmd[k:j])
            if ver == 2.0:
                args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal '
                        'to tell current session to write text "' + chunk + '"']
            else:
                args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal window '
                        'to tell current session to write text "' + chunk + '"']

            subprocess.check_call(args)

            # when cmd ends in a space, iterm does not execute.
            if (chunk[-1:] == ' '):
                if ver == 2.0:
                    args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal '
                            'to tell current session to write text ""']
                else:
                    args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal window '
                            'to tell current session to write text ""']
                subprocess.check_call(args)

            k = j

    elif prog == "tmux":
        cmd = clean(cmd) + "\n"
        progpath = settings.get("tmux", "tmux")
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            subprocess.call([progpath, 'set-buffer', chunk])
            subprocess.call([progpath, 'paste-buffer', '-d'])

    elif prog == "screen":
        cmd = clean(cmd) + "\n"
        progpath = settings.get("screen", "screen")
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            if plat == "linux":
                chunk = chunk.replace("\\", r"\\")
                chunk = chunk.replace("$", r"\$")
            subprocess.call([progpath, '-X', 'stuff', chunk])

    elif prog == "SublimeREPL":
        cmd = clean(cmd)
        view = sublime.active_window().active_view()
        external_id = view.scope_name(0).split(" ")[0].split(".", 1)[1]
        sublime.active_window().run_command("repl_send", {"external_id": external_id, "text": cmd})
        return

    if plat == 'windows':
        raise Exception("not yet supported")


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


class SendTextPlusCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        cmd = ''
        moved = False
        for sel in [s for s in view.sel()]:
            if sel.empty():
                if syntax_settings(view, "block", False):
                    esel = expand_block(view, sel)
                thiscmd = view.substr(view.line(esel))
                line = view.rowcol(esel.end())[0]
                if syntax_settings(view, "auto_advance", False):
                    view.sel().subtract(sel)
                    pt = view.text_point(line+1, 0)
                    view.sel().add(sublime.Region(pt, pt))
                    moved = True
            else:
                thiscmd = view.substr(sel)
            cmd += thiscmd + '\n'

        # ipython wrapper
        if get_syntax(view) == "python":
            cmd = clean(cmd)
            if len(re.findall("\n", cmd)) > 0:
                cmd = "%cpaste\n" + cmd + "\n--"

        sendtext(view, cmd)

        if moved:
            view.show(view.sel())


class SendTextPlusChangeDirCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        fname = view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return

        dirname = os.path.dirname(fname)
        syntax = get_syntax(view)

        if syntax == "r":
            cmd = "setwd(\"" + escape_dq(dirname) + "\")"
        elif syntax == "julia":
            cmd = "cd(\"" + escape_dq(dirname) + "\")"
        elif syntax == "python":
            cmd = "cd \"" + escape_dq(dirname) + "\""
        sendtext(view, cmd + "\n")
