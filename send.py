import sublime
import subprocess
from .misc import clean, escape_dq, syntax_settings


def sendtext_terminal(cmd):
    cmd = clean(cmd)
    cmd = escape_dq(cmd)
    args = ['osascript']
    args.extend(['-e', 'tell app "Terminal" to do script "' + cmd + '" in front window'])
    subprocess.Popen(args)


def iterm_version():
    try:
        args = ['osascript', '-e',
                'tell app "iTerm" to tell the first terminal to set foo to true']
        subprocess.check_call(args)
        return 2.0
    except:
        return 2.9


def sendtext_iterm(cmd):
    cmd = clean(cmd)
    cmd = escape_dq(cmd)
    cmd = cmd.split("\n")
    line_len = [len(c)+1 for c in cmd]
    k = 0
    ver = iterm_version()
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

        # when chunk ends in a space, iterm does not execute.
        if (chunk[-1:] == ' '):
            if ver == 2.0:
                args += ['-e', 'tell app "iTerm" to tell the first terminal '
                         'to tell current session to write text ""']
            else:
                args += ['-e', 'tell app "iTerm" to tell the first terminal window '
                         'to tell current session to write text ""']

        subprocess.check_call(args)

        k = j


def sendtext_tmux(cmd, tmux="tmux"):
    cmd = clean(cmd) + "\n"
    n = 200
    chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
    for chunk in chunks:
        subprocess.call([tmux, 'set-buffer', chunk])
        subprocess.call([tmux, 'paste-buffer', '-d'])


def sendtext_screen(cmd, screen="screen"):
    plat = sublime.platform()
    cmd = clean(cmd) + "\n"
    n = 200
    chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
    for chunk in chunks:
        if plat == "linux":
            chunk = chunk.replace("\\", r"\\")
            chunk = chunk.replace("$", r"\$")
        subprocess.call([screen, '-X', 'stuff', chunk])


def sendtext(view, cmd):
    if cmd.strip() == "":
        return
    plat = sublime.platform()
    prog = syntax_settings(view, "prog")
    settings = sublime.load_settings("SendTextPlus.sublime-settings")

    if prog == 'Terminal':
        sendtext_terminal(cmd)

    elif prog == 'iTerm':
        sendtext_iterm(cmd)

    elif prog == "tmux":
        sendtext_tmux(cmd, settings.get("tmux", "tmux"))

    elif prog == "screen":
        sendtext_screen(cmd, settings.get("screen", "screen"))

    elif prog == "SublimeREPL":
        cmd = clean(cmd)
        view = sublime.active_window().active_view()
        external_id = view.scope_name(0).split(" ")[0].split(".", 1)[1]
        sublime.active_window().run_command("repl_send", {"external_id": external_id, "text": cmd})
        return

    if plat == 'windows':
        raise Exception("not yet supported")
