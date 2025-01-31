import argparse

from pig import VM


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vmid", required=True)
    args = parser.parse_args()

    vm = VM(id=args.vmid)
    conn = vm.connect()

    # Open search using key shortcut
    conn.key("h e l l o")
    # conn.cmd("dir")
    # conn.powershell("ls", close_after=True)


if __name__ == "__main__":
    main()
