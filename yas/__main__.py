"""yas 包入口：python -m yas <command>。"""
from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())