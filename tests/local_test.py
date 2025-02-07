# For testing against a local Piglet

from pig import Client, APIError

client = Client()

def test_local():
    machine = client.machines.local()
    with machine.connect() as conn:
        conn.left_click(x=100, y=200)
        conn.type("hello")
        conn.left_click(x=100, y=400)
        conn.type("world")

if __name__ == "__main__":
    test_local()