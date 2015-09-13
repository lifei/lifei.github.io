"""

"""

import os
import subprocess
import sys
import threading
import time
import yaml

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer



class ChangedFileEventHandler(PatternMatchingEventHandler):

    def __init__(self, target, src='.', patterns=None, ignore_patterns=None,
                 ignore_directories=False,
                 cmd='/usr/bin/rsync -azR --files-from=- {0} {1}'):
        super(ChangedFileEventHandler, self).__init__(
            patterns, ignore_patterns, ignore_directories)

        self.src = src
        self.target = target
        self.cmd = cmd.format(src, target)
        self.paths = set()
        self.lock = threading.Lock()

    def on_any_event(self, event):
        """

        @type event: watchdog.events.FileSystemEvent
        """

        self.add(event.src_path)
        if hasattr(event, 'dest_path'):
            self.add(event.dest_path)


    def add(self, path):
        relpath = os.path.relpath(path, self.src).replace('\\', '/')
        self.paths.add(relpath)

    def sync(self):

        with self.lock:
            paths = list(self.paths)
            self.paths.clear()

        if not paths:
            return

        for _ in range(3):
            p = subprocess.Popen(self.cmd, shell=True, stdin=subprocess.PIPE)
            p.communicate('\n'.join(paths))
            p.wait()
            if p.returncode == 0:
                break

            print 'retrying...'


def load_config():

    with open(sys.argv[1], 'rb') as fp:
        return yaml.load(fp.read())


if __name__ == '__main__':

    config = load_config()
    observer = Observer()

    handlers = []

    for params in config['handers']:

        print params

        paths = params['paths']
        del params['paths']

        for path in paths:
            handler = ChangedFileEventHandler(**params)
            handlers.append(handler)
            observer.schedule(handler, path, recursive=True)

    observer.start()
    print 'start...'
    try:
        while True:
            for handler in handlers:
                handler.sync()
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
