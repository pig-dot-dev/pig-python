import argparse
from pig import VM

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vmid', required=True)
    args = parser.parse_args()

    vm = VM(id=args.vmid)
    conn = vm.connect()
    conn.left_click(100, 100)
    conn.type("Hello World")
    conn.right_click(200, 200)
    conn.screenshot()
    # conn.yield_control()
    # conn.await_control()

if __name__ == "__main__":
   main()