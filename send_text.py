import sys
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


def send_text_terminal(cmd):
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


def send_text_iterm(cmd):
    cmd = clean(cmd)
    cmd = escape_dq(cmd)
    ver = iterm_version()
    if ver == 2.0:
        args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal ' +
                'to tell current session to write text "' + cmd + '"']
    else:
        args = ['osascript', '-e', 'tell app "iTerm" to tell the first terminal window ' +
                'to tell current session to write text "' + cmd + '"']
    subprocess.check_call(args)


def send_text_tmux(cmd, tmux="tmux"):
    cmd = clean(cmd) + "\n"
    n = 200
    chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
    for chunk in chunks:
        subprocess.call([tmux, 'set-buffer', chunk])
        subprocess.call([tmux, 'paste-buffer', '-d'])


def send_text_screen(cmd, screen="screen"):
    plat = sys.platform
    cmd = clean(cmd) + "\n"
    n = 200
    chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
    for chunk in chunks:
        if plat.startswith("linux"):
            chunk = chunk.replace("\\", r"\\")
            chunk = chunk.replace("$", r"\$")
        subprocess.call([screen, '-X', 'stuff', chunk])
