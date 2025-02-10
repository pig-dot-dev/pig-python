# For testing against a local Piglet

from pig import Client, APIError

client = Client()

def test_local():
    machine = client.machines.local()
    with machine.connect() as conn:
        conn.key("super+r")
        conn.type("hello")
        conn.mouse_move(x=100, y=400)
        conn.left_click(x=100, y=400)

if __name__ == "__main__":
    test_local()