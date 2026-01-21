#!/usr/bin/env python3
import os

from orchestrator import Orchestrator

os.environ.setdefault("ESCDELAY", "25")


def main():
    orchestrator = Orchestrator(start_path=os.getcwd())
    orchestrator.run()


if __name__ == "__main__":
    main()
