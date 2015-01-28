import sublime
import sublime_plugin
import os
import subprocess
import re
import tempfile


def syntax_settings(lang, key, default=None):
    settings = sublime.load_settings("SendTextPlus.sublime-settings")
    ret = None
    plat = sublime.platform()
    if lang:
        lang_settings = settings.get(lang)
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


def sendtext(prog, cmd):
    if cmd.strip() == "":
        return
    plat = sublime.platform()
    settings = sublime.load_settings("SendTextPlus.sublime-settings")

    if re.match('Terminal', prog):
        cmd = clean(cmd)
        cmd = escape_dq(cmd)
        args = ['osascript']
        args.extend(['-e', 'tell app "Terminal" to do script "' + cmd + '" in front window\n'])
        subprocess.Popen(args)

    elif re.match('iTerm', prog):
        cmd = clean(cmd)
        cmd = escape_dq(cmd)
        # when cmd ends in a space, iterm does not execute. Thus append a line break.
        if (cmd[-1:] == ' '):
            cmd += '\n'
        try:
            # iterm <2.9
            args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal '
                    'to tell current session to write text "' + cmd + '"']
            subprocess.check_call(args)
        except:
            # iterm >=2.9
            args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal window '
                    'to tell current session to write text "' + cmd + '"']
            subprocess.check_call(args)

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


class SendTextPlusCommand(sublime_plugin.TextCommand):
    def get_syntax(self):
        view = self.view
        pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0
        if view.score_selector(pt, "source.r"):
            return "r"
        elif view.score_selector(pt, "source.python"):
            return "python"
        elif view.score_selector(pt, "source.julia"):
            return "julia"

    def r_expand_block(self, sel):
        # expand selection to {...} when being triggered
        view = self.view
        thiscmd = view.substr(view.line(sel))
        if re.match(r".*\{\s*$", thiscmd):
            esel = view.find(
                r"""^(?:.*(\{(?:(["\'])(?:[^\\]|\\.)*?\2|#.*$|[^\{\}]|(?1))*\})[^\{\}\n]*)+""",
                view.line(sel).begin()
            )
            if view.line(sel).begin() == esel.begin():
                sel = esel
        return sel

    def python_expand_block(self, sel):
        view = self.view
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

    def julia_expand_block(self, sel):
        view = self.view
        thiscmd = view.substr(view.line(sel))
        if (re.match(r"^\s*(?:function|if|for|while)", thiscmd) and
                not re.match(r".*end\s*$", thiscmd)) or \
                (re.match(r".*begin\s*$", thiscmd)):
            indentation = re.match("^(\s*)", thiscmd).group(1)
            end = view.find("^"+indentation+"end", sel.begin())
            sel = sublime.Region(sel.begin(), view.line(end.end()).end())

        return sel

    def run(self, edit):
        view = self.view
        syntax = self.get_syntax()
        cmd = ''
        for sel in [s for s in view.sel()]:
            if sel.empty():
                if syntax_settings(syntax, "block", False):
                    if syntax == "r":
                        esel = self.r_expand_block(sel)
                    elif syntax == "python":
                        esel = self.python_expand_block(sel)
                    elif syntax == "julia":
                        esel = self.julia_expand_block(sel)

                    thiscmd = view.substr(view.line(esel))
                    line = view.rowcol(esel.end())[0]
                else:
                    thiscmd = view.substr(view.line(sel))
                    line = view.rowcol(sel.end())[0]

                if syntax_settings(syntax, "auto_advance", False):
                    view.sel().subtract(sel)
                    pt = view.text_point(line+1, 0)
                    view.sel().add(sublime.Region(pt, pt))
            else:
                thiscmd = view.substr(sel)
            cmd += thiscmd + '\n'

        # ipython wrapper
        if syntax == "python" and syntax_settings(syntax, "ipython", False):
            cmd = clean(cmd)
            if len(re.findall("\n", cmd)) > 0:
                cmd = "%cpaste\n" + cmd + "\n--"

        prog = syntax_settings(syntax, "prog")
        sendtext(prog, cmd)

        if syntax_settings(syntax, "auto_advance", False):
            view.show(view.sel())


class SendTextPlusChangeDirCommand(sublime_plugin.TextCommand):
    def get_syntax(self):
        view = self.view
        pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0
        if view.score_selector(pt, "source.r"):
            return "r"
        elif view.score_selector(pt, "source.python"):
            return "python"
        elif view.score_selector(pt, "source.julia"):
            return "julia"

    def run(self, edit):
        fname = self.view.file_name()
        if not fname:
            sublime.error_message("Save the file!")
            return

        dirname = os.path.dirname(fname)
        syntax = self.get_syntax()
        prog = syntax_settings(syntax, "prog")

        if syntax == "r":
            cmd = "setwd(\"" + escape_dq(dirname) + "\")"
        elif syntax == "julia":
            cmd = "cd(\"" + escape_dq(dirname) + "\")"
        elif syntax == "python" and syntax_settings(syntax, "ipython", False):
            cmd = "cd \"" + escape_dq(dirname) + "\""
        sendtext(prog, cmd + "\n")
