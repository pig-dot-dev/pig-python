import asyncio
import time

from pig import Client, APIError

client = Client()

def test_e2e():
    # This is an E2E test, will take a while

    # Case 1: manual lifecycle management
    print("\nCase 1: manual lifecycle management")
    print("Creating new machine")
    vm = client.machines.create()  # new vm
    assert vm.id is not None
    print(f"VM ID {vm.id} created")
    print(".connect()")
    with vm.connect() as conn:  # since already created, vm is started, so this just connects to it
        print(f"VM ID {vm.id} connected")

        # Test all connection methods
        print("conn.type('Hello, World!')")
        conn.type("Hello, World!")
        print("conn.left_click(100, 100)")
        conn.left_click(100, 100)
        print("conn.cursor_position()")
        x, y = conn.cursor_position()
        assert x == 100 and y == 100
        print(f"Cursor position: {x}, {y}")
        print("conn.left_click_drag(200, 200)")
        conn.left_click_drag(200, 200)
        print("conn.double_click(300, 300)")
        conn.double_click(300, 300)
        print("conn.right_click(400, 400)")
        conn.right_click(400, 400)
        print("conn.screenshot()")
        ss = conn.screenshot()  # calls screenshot under existing connection ID
        assert len(ss) > 0
    
    print(".stop()")
    vm.stop()  # stops the vm
    assert vm.id is not None
    print(f"VM ID {vm.id} stopped")
    print("Done")

    # Case 2: restarting an existing vm
    print("\nCase 2: restarting an existing vm")
    print(f"reusing VM ID {vm.id}")
    print(".start()")
    vm.start()  # starts the vm
    assert vm.id is not None
    print(f"VM ID {vm.id} started")
    with vm.connect() as conn:
        print(f"VM ID {vm.id} connected")
        print("conn.screenshot()")
        ss = conn.screenshot()
        assert len(ss) > 0
    print("Done")

    # Case 3: trying to start an already running vm
    print("\nCase 3: trying to start an already running vm")
    print(f"reusing VM ID {vm.id}")
    print(".start() - should be instant")
    s = time.time()
    vm.start()  # this should pass without error
    assert vm.id is not None
    assert time.time() - s < 5  # should be nearly instant, but set to 5s just in case aws API is slow
    print(f"VM ID {vm.id} started")
    with vm.connect() as conn:
        print(f"VM ID {vm.id} connected")
        print("conn.screenshot()")
        ss = conn.screenshot()
        assert len(ss) > 0
    print("Done")

    # Case 4: getting an existing vm by ID
    print("\nCase 4: getting an existing vm by ID")
    print(f"reusing VM ID {vm.id}")
    vm = client.machines.get(vm.id)
    assert vm.id is not None
    with vm.connect() as conn:
        print(f"VM ID {vm.id} connected")
        print("conn.screenshot()")
        ss = conn.screenshot()
        assert len(ss) > 0
    print("Done")

    # Case 5: trying to start a terminated vm
    print("\nCase 5: trying to start a terminated vm")
    print(f"Terminating VM ID {vm.id} to set up test")
    vm.terminate()  # terminates the vm
    print("Test ready, attempting to start terminated vm")
    errored = False
    try:
        vm.start()
    except APIError:
        errored = True
        pass
    if not errored:
        raise Exception("VM should have been terminated")

    # Case 6: using temporary vm
    print("\nCase 6: using temporary vm")
    print("starting fresh temporary VM")
    with client.machines.temporary() as vm:
        assert vm.id is not None
        with vm.connect() as conn:
            print(f"VM ID {vm.id} connected")
            print("doing some work...")
    print("session closed, vm should be terminated")
    # double check that the vm is terminated
    errored = False
    try:
        vm.start()
    except APIError:
        errored = True
        pass
    if not errored:
        raise Exception("VM should have been terminated")

    # Case 8: using async versions of the client
    print("\nCase 8: using async versions of the client")

    async def do_it():
        async with client.machines.temporary.aio() as vm:
            print("connecting to vm")
            async with vm.connect.aio() as conn:
                assert vm.id is not None
                print(f"VM ID {vm.id} connected")
                print("await asyncio.gather of click.aio, type.aio, mouse_move.aio")
                await asyncio.gather(
                    conn.left_click.aio(x=330, y=750),
                    conn.type.aio("excel"),
                    conn.mouse_move.aio(x=500, y=750),
                )

                print("doing more async operations...")
                await asyncio.gather(
                    conn.left_click.aio(x=330, y=750),
                    conn.type.aio("excel"),
                    conn.mouse_move.aio(x=500, y=750),
                )

    asyncio.run(do_it())
    print("done with async")


if __name__ == "__main__":
    test_e2e()
