import sys

sys.dont_write_bytecode = True

from app import entrypoint

if __name__ == "__main__":
    entrypoint()
