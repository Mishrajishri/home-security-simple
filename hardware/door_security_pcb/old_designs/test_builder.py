import os, sys
import pcbnew

def test():
    print("KiCad pcbnew version:", pcbnew.GetBuildVersion())

if __name__ == "__main__":
    test()
