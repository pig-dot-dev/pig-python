import time

from pig import VM, APIError


def test_e2e():
    # This is an E2E test, will take a while

    # Case 1: manual lifecycle management
    print("\nCase 1: manual lifecycle management")
    print("VM()")
    vm = VM() # new vm. This doesn't create anything in the db
    assert(vm.id is None)
    print(".create()")
    vm.create() # creates a new VM in the db, assigns id
    assert(vm.id is not None)
    print(f"VM ID {vm.id} created")
    print(".connect()")
    conn = vm.connect() # since already created, vm is started, so this just connects to it
    print(f"VM ID {vm.id} connected")

    # Test all connection methods
    print("conn.type('Hello, World!')")
    conn.type("Hello, World!")
    print("conn.left_click(100, 100)")
    conn.left_click(100, 100)
    print("conn.cursor_position()")
    x, y = conn.cursor_position()
    assert(x == 100 and y == 100)
    print(f"Cursor position: {x}, {y}")
    print("conn.left_click_drag(200, 200)")
    conn.left_click_drag(200, 200)
    print("conn.double_click(300, 300)")
    conn.double_click(300, 300)
    print("conn.right_click(400, 400)")
    conn.right_click(400, 400)
    print("conn.screenshot()")
    ss = conn.screenshot() # calls screenshot under existing connection ID
    assert(len(ss) > 0)
    print(".stop()")
    vm.stop() # stops the vm
    assert(vm.id is not None)
    print(f"VM ID {vm.id} stopped")
    print("Done")

    # Case 2: restarting an existing vm
    print("\nCase 2: restarting an existing vm")
    print(f"reusing VM ID {vm.id}")
    print(".start()")
    vm.start() # starts the vm
    assert(vm.id is not None)
    print(f"VM ID {vm.id} started")
    print(".connect()")
    conn = vm.connect()
    print(f"VM ID {vm.id} connected")
    print("conn.screenshot()")
    ss = conn.screenshot()
    assert(len(ss) > 0)
    print("Done")

    # Case 3: trying to start a already running vm
    print("\nCase 3: trying to start a already running vm")
    print(f"reusing VM ID {vm.id}")
    print(".start() - should be instant")
    s = time.time()
    vm.start() # this should pass without error
    assert(vm.id is not None)
    assert(time.time() - s < 5) # should be nearly instant, but set to 5s just in case aws API is slow
    print(f"VM ID {vm.id} started")
    print(".connect()")
    conn = vm.connect()
    print(f"VM ID {vm.id} connected")
    print("conn.screenshot()")
    ss = conn.screenshot()
    assert(len(ss) > 0)
    print("Done")

    # Case 4: reinstantiating a new VM object with an existing vm
    print("\nCase 4: reinstantiating a new VM object with an existing vm")
    print(f"reusing VM ID {vm.id} on new VM object")
    vm = VM(id=vm.id)
    assert(vm.id is not None)
    print(".connect()")
    conn = vm.connect()
    print(f"VM ID {vm.id} connected")
    print("conn.screenshot()")
    ss = conn.screenshot()
    assert(len(ss) > 0)
    print("Done")

    # Case 5: trying to start a terminated vm
    print("\nCase 5: trying to start a terminated vm")
    print(f"Terminating VM ID {vm.id} to set up test")
    vm.terminate() # terminates the vm
    print("Test ready, attempting to start terminated vm")
    errored = False
    try:
        vm.start()
    except APIError:
        errored = True
        pass
    if not errored:
        raise Exception("VM should have been terminated")

    # Case 6: using context manager (temporary)
    print("\nCase 6: using context manager and temporary vm")
    print("starting fresh VM")
    vm = VM(temporary=True) # temporary vm, will be destroyed after use
    assert(vm.id is None)
    print("entering .session()")
    with vm.session() as conn:
        assert(vm.id is not None)
        print(f"VM ID {vm.id} connected")
    
        print("exiting .session()")
    # double check that the vm is terminated
    errored = False
    try:
        vm.start()
    except APIError:
        errored = True
        pass
    if not errored:
        raise Exception("VM should have been terminated")

    # Case 7: using context manager (persistent)
    print("\nCase 7: using context manager and persistent vm")
    vm = VM() # reuse existing vm
    assert(vm.id is None)
    print("entering .session()")
    with vm.session() as conn:
        assert(vm.id is not None)
        print(f"VM ID {vm.id} connected")

        print("exiting .session()")
    # double check that the vm is stopped
    print(f"VM ID {vm.id} stopped")
    print(".start()")
    vm.start()
    print("VM ID {vm.id} restarted")
    print(".terminate()")
    vm.terminate()
    print("Done")

if __name__ == "__main__":
    test_e2e()