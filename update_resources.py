import sublime
import os
import shutil


def update_resources(binname):
    # from https://github.com/weslly/ColorPicker/blob/master/sublimecp.py
    targetdir = os.path.join(sublime.packages_path(), 'User', 'SendText+', 'bin')
    targetpath = os.path.join(targetdir, binname)
    respath = 'Packages/SendText+/bin/' + binname
    pkgpath = os.path.join(sublime.installed_packages_path(), 'SendText+.sublime-package')
    unpkgpath = os.path.join(sublime.packages_path(), 'SendText+', 'bin', binname)

    if os.path.exists(targetpath):
        targetinfo = os.stat(targetpath)
    else:
        if not os.path.exists(targetdir):
            os.makedirs(targetdir, 0o755)
        targetinfo = None

    if os.path.exists(unpkgpath):
        pkginfo = os.stat(unpkgpath)
    elif os.path.exists(pkgpath):
        pkginfo = os.stat(pkgpath)
    else:
        return

    if targetinfo is None or targetinfo.st_mtime < pkginfo.st_mtime:
        print("* Updating " + targetpath)
        if sublime.version() < '3000':
            shutil.copy2(unpkgpath, targetpath)
        else:
            data = sublime.load_binary_resource(respath)
            with open(targetpath, 'wb') as binfile:
                binfile.write(data)
                binfile.close()

    if not os.access(targetpath, os.X_OK):
        os.chmod(targetpath, 0o755)


def plugin_loaded():
    if sublime.platform() == "windows":
        update_resources("AutoHotkeyU32.exe")
        update_resources("Cmder.ahk")
        update_resources("Cygwin.ahk")
        update_resources("RStudio.ahk")
