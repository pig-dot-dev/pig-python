from pig import VM


def test_vm_quick():
    print("\nUsing context manager and temporary vm")
    print("starting fresh VM")
    vm = VM(temporary=True)  # temporary vm, will be destroyed after use
    assert vm.id is None
    print("entering .session()")
    with vm.session() as conn:
        assert vm.id is not None
        print(f"VM ID {vm.id} connected")
        conn.right_click(100, 100)
        conn.screenshot()
        print("exiting .session()")


if __name__ == "__main__":
    test_vm_quick()
