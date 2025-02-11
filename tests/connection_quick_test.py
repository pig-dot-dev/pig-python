import argparse

from pig import Client
client = Client()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine-id", required=True)
    args = parser.parse_args()

    machine = client.machines.get(args.machine_id)
    with machine.connect() as conn:
        conn.key("h e l l o")
        print(conn.cursor_position())

if __name__ == "__main__":
    main()
