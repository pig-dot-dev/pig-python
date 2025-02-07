import argparse

from pig import Client
client = Client()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vmid", required=True)
    args = parser.parse_args()

    vm = client.machines.get(args.vmid)
    with vm.connect() as conn:
        conn.key("h e l l o")

if __name__ == "__main__":
    main()
