import os

import  git

import datetime
import subprocess
import sys


home = '/Users/bruno/gsgui'
if __name__ == "__main__":
    repo = git.Repo(home)
    ####
    # create a release branch
    print('BULD RELEASE')
    print('REMOVE DIST')
    if os._exists(home + '/dist'):
        os.rmdir(home + '/dist/*')
    #os.mkdir(home + '/dist')
    print('BUILD APP ...')
    subprocess.run(["pyinstaller", "gsgui.spec"])
    print('BUILD DMG')
    subprocess.run(["./build-dmg.sh"])

    print('BUILD DMG DONE')