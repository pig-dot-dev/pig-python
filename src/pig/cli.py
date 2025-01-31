#!/usr/bin/env python3
import asyncio
import os

import click
import iso8601
from simple_term_menu import TerminalMenu
from tabulate import tabulate

from .pig import BASE_URL, VM, APIClient

API_KEY = os.environ.get("PIG_SECRET_KEY")
if not API_KEY:
    raise ValueError("PIG_SECRET_KEY environment variable not set")

# Additional CRUD calls supported in CLI but not via SDK


async def get_vms():
    """Fetch VMs from the API"""
    client = APIClient(base_url=BASE_URL, api_key=API_KEY)
    return await client.get("vms")


async def get_images():
    """Fetch images from the API"""
    client = APIClient(base_url=BASE_URL, api_key=API_KEY)
    return await client.get("images")


async def snapshot_image(vm_id, tag):
    """Take a snapshot of a running VM"""
    client = APIClient(base_url=BASE_URL, api_key=API_KEY)
    response = await client.post(f"vms/{vm_id}/image/snapshot", data={"tag": tag})
    return response


# CLI utils


def emoji_supported():
    """Check if terminal likely supports emoji"""
    term = os.environ.get("TERM", "")
    # Common terminals that support emoji
    emoji_terms = ["xterm-256color", "screen-256color", "iTerm.app"]
    return any(t in term for t in emoji_terms)


def prompt_for_vm_id(exclude=None):
    """ "For when user doesn't specify a vm ID"""
    vms = asyncio.run(get_vms())
    if len(vms) == 0:
        click.echo("There are no VMs in your account. Create one with `pig create`")
        return
    vms = [vm for vm in vms if vm["status"].lower() != "terminated"]
    if exclude:
        vms = [vm for vm in vms if vm["status"].lower() != exclude.lower()]
    if len(vms) == 0 and exclude:
        click.echo(f"All VMs in your account are already {exclude}")
        return
    if len(vms) == 1:
        return vms[0]["id"]
    display = []
    for vm in vms:
        dt = iso8601.parse_date(vm["created_at"])
        status = click.style(vm["status"], fg="green") if vm["status"].lower() == "running" else vm["status"]
        display.append(f"{vm['id']} ({status}) {dt.strftime('%Y-%m-%d %H:%M')}")
    menu = TerminalMenu(
        display,
        menu_cursor="🐽 " if emoji_supported() else "> ",
        menu_cursor_style=("fg_yellow", "bold"),
        menu_highlight_style=(),
        clear_menu_on_exit=False,
    )
    choice = menu.show()
    if choice is None:
        return
    return vms[choice]["id"]


def prompt_for_all(action, exclude=None):
    """ "For when user passes in the -a flag"""
    vms = asyncio.run(get_vms())
    target_vms = [vm for vm in vms if vm["status"].lower() != "terminated"]
    if exclude:
        target_vms = [vm for vm in target_vms if vm["status"].lower() != exclude.lower()]
    if len(target_vms) == 0:
        click.echo(f"All VMs in your account are already {exclude}")
        return []
    if not prompt_confirm(f"You're about to {action} {len(target_vms)} VM{'' if len(target_vms) == 1 else 's'}."):
        return []
    return [vm["id"] for vm in target_vms]


def prompt_confirm(message):
    click.echo(message + " Continue?\n")
    options = ["Abort", "Continue"]
    menu = TerminalMenu(
        options,
        menu_cursor="🐽 " if emoji_supported() else "> ",
        menu_highlight_style=(),
        clear_menu_on_exit=False,
    )
    choice = menu.show()
    click.echo()
    if choice is None:
        return False
    return choice == 1


def print_vms(vms, show_terminated=False):
    """Display VMs in a formatted way"""
    if not vms:
        click.echo("No VMs found")
        return

    vms = vms if show_terminated else [vm for vm in vms if vm["status"].lower() != "terminated"]

    headers = ["ID", "Status", "Created"]
    table_data = []
    for vm in vms:
        dt = iso8601.parse_date(vm["created_at"])
        status = click.style(vm["status"], fg="green") if vm["status"].lower() == "running" else vm["status"]
        table_data.append([vm["id"], status, dt.strftime("%Y-%m-%d %H:%M")])
    click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))


def print_images(images, all=False):
    """Display images in a formatted way"""
    if not images:
        click.echo("No images found")
        return

    if not all:
        # filter to owned images, which have a teamID
        images = [img for img in images if img["team_id"]]

    headers = ["ID", "Tag", "Parent", "Created"]
    table_data = []
    for img in images:
        dt = iso8601.parse_date(img["created_at"])
        table_data.append([img["id"], img["tag"], img["parent_id"] or "base", dt.strftime("%Y-%m-%d %H:%M")])
    click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))


# CLI entrypoints


@click.group()
def cli():
    """pig CLI for managing Windows VMs"""
    pass


@cli.command()
@click.option("--image", "-i", required=False, help="Image ID to use")
def create(image):
    """Create a new VM"""
    vm = VM(image=image)
    click.echo("Creating VM...")
    vm.create()
    click.echo(f"Created VM\t{vm.id}")


@cli.command()
@click.argument("id", required=False)
def connect(id):
    """Starts a connection with a VM"""
    if not id:
        id = prompt_for_vm_id()
        if not id:
            return

    vm = VM(id=id)
    _conn = vm.connect()  # Prints url


@cli.command()
@click.argument("ids", nargs=-1, required=False)
@click.option("--all", "-a", is_flag=True, help="Start all VMs")
def start(ids, all):
    """Start an existing VM"""
    if all:
        ids = prompt_for_all("start", exclude="Running")
        if len(ids) == 0:
            return
    if not ids and not all:
        ids = [prompt_for_vm_id(exclude="Running")]
        if ids[0] is None:
            return

    # Get all in flight at the same time
    async def start_vm(id):
        try:
            vm = VM(id=id)
            click.echo(f"Starting {id}...")
            await vm.start.aio()
            click.echo("Started")
        except Exception as e:
            click.echo(f"Failed to start VM {id}: {str(e)}", err=True)

    async def run_starts():
        await asyncio.gather(*[start_vm(id) for id in ids])

    asyncio.run(run_starts())


@cli.command()
@click.argument("ids", nargs=-1, required=False)
@click.option("--all", "-a", is_flag=True, help="Stop all VMs")
def stop(ids, all):
    """Stop an existing VM"""
    if all:
        ids = prompt_for_all("stop", exclude="Stopped")
        if len(ids) == 0:
            return
    if not ids:
        ids = [prompt_for_vm_id(exclude="Stopped")]
        if ids[0] is None:
            return

    async def stop_vm(id):
        try:
            vm = VM(id=id)
            click.echo(f"Stopping {id}...")
            await vm.stop.aio()
            click.echo("Stopped")
        except Exception as e:
            click.echo(f"Failed to stop VM {id}: {str(e)}", err=True)

    async def run_stops():
        await asyncio.gather(*[stop_vm(id) for id in ids])

    asyncio.run(run_stops())


@cli.command()
@click.argument("ids", nargs=-1, required=False)
@click.option("--all", "-a", is_flag=True, help="Terminate all VMs")
def terminate(ids, all):
    """Terminate an existing VM"""
    if all:
        ids = prompt_for_all("terminate")
        if len(ids) == 0:
            return
    if not ids:
        ids = [prompt_for_vm_id()]
        if ids[0] is None:
            return

    # Get all in flight at the same time
    async def terminate_vm(id):
        try:
            vm = VM(id=id)
            click.echo(f"Terminating {id}...")
            await vm.terminate.aio()
            click.echo("Terminated")
        except Exception as e:
            click.echo(f"Failed to terminate VM {id}: {str(e)}", err=True)

    async def run_terminates():
        await asyncio.gather(*[terminate_vm(id) for id in ids])

    asyncio.run(run_terminates())


@cli.command()
@click.option("--all", "-a", is_flag=True, help="Show all VMs, including terminated ones")
def ls(all):
    """List all VMs"""
    vms = asyncio.run(get_vms())
    print_vms(vms, show_terminated=all)


@cli.group()
def img():
    """Commands for managing VM images"""
    pass


@img.command()
@click.option("--all", "-a", is_flag=True, help="Show all images, including Pig standard images")
def ls(all):  # noqa: F811
    """List all images"""
    images = get_images()
    print_images(images, all)


@img.command()
@click.option("--vm", required=True, help="VM ID to snapshot")
@click.option("--tag", "-t", required=True, help='Tag (name) for the snapshot. Example: --tag my_snapshot or --tag "My Snapshot"')
def snapshot(vm, tag):
    """Take a snapshot of a running VM"""
    if not prompt_confirm("This will take up to 15 minutes to complete, and will permanently terminate the parent VM."):
        return

    click.echo(f"Snapshotting VM\t{vm}...")
    response = snapshot_image(vm, tag)
    click.echo(f"Created Image\t{response['id']}")


# Add img to cli group
cli.add_command(img)


def main():
    cli()
