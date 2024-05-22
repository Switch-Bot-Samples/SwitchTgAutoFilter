import os
from importlib import import_module
from logging import getLogger

LOG = getLogger(__name__)


def load_modules(path):
    for root, __, files in os.walk(path):
        files_count = 0
        for f in files:
            if f.startswith("__") or not f.endswith(".py"):
                continue
            try:
                module_path = (
                    os.path.join(root, f)[:-3].replace("\\", ".").replace("/", ".")
                )

                import_module(module_path)
            except Exception as er:
                print(er)
            files_count += 1
        if files_count:
            name = root.replace('/', '.').replace("\\", ".")
            print(f"Loaded {files_count} files from {name}")
    LOG.info("Completed loading modules.")