#!/usr/bin/env python3
import asyncio
import os

import click
import iso8601
from simple_term_menu import TerminalMenu
from tabulate import tabulate

from .pig import Client

# Global client
client = Client()

# Additional CRUD calls supported in CLI but not via SDK
async def get_machines():
    """Fetch Machines from the API"""
    url = client._api_url("machines")
    return await client._api_client.get(url)


async def get_images():
    """Fetch images from the API"""
    url = client._api_url("images")
    return await client._api_client.get(url)


async def snapshot_image(machine_id, tag):
    """Take a snapshot of a running Machine"""
    url = client._api_url("images/snapshot")
    return await client._api_client.post(url, data={"tag": tag, "machine_id": machine_id})


# CLI utils
def emoji_supported():
    """Check if terminal likely supports emoji"""
    term = os.environ.get("TERM", "")
    # Common terminals that support emoji
    emoji_terms = ["xterm-256color", "screen-256color", "iTerm.app"]
    return any(t in term for t in emoji_terms)


def prompt_for_machine_id(exclude=None):
    """ "For when user doesn't specify a machine ID"""
    machines = asyncio.run(get_machines())
    if len(machines) == 0:
        click.echo("There are no Machines in your account. Create one with `pig create`")
        return
    machines = [machine for machine in machines if machine["state"].lower() != "terminated"]
    if exclude:
        machines = [machine for machine in machines if machine["state"].lower() != exclude.lower()]
    if len(machines) == 0 and exclude:
        click.echo(f"All Machines in your account are already {exclude}")
        return
    if len(machines) == 1:
        return machines[0]["id"]
    display = []
    for machine in machines:
        dt = iso8601.parse_date(machine["created_at"])
        display.append(f"{machine['id']} - {machine['state']} - {dt.strftime('%Y-%m-%d %H:%M')}".strip())
    menu = TerminalMenu(
        display,
        menu_cursor="🐽 " if emoji_supported() else "> ",
        menu_cursor_style=("fg_yellow", "bold"),
        menu_highlight_style=(),
        clear_menu_on_exit=False,
        cycle_cursor=True,
    )
    choice = menu.show()
    if choice is None:
        return
    return machines[choice]["id"]


def prompt_for_all(action, auto_approve, exclude=None):
    """ "For when user passes in the -a flag"""
    machines = asyncio.run(get_machines())
    target_machines = [machine for machine in machines if machine["state"].lower() != "terminated"]
    if exclude:
        target_machines = [machine for machine in target_machines if machine["state"].lower() != exclude.lower()]
    if len(target_machines) == 0:
        click.echo(f"All Machines in your account are already {exclude}")
        return []
    if not auto_approve:
        if not prompt_confirm(f"You're about to {action} {len(target_machines)} Machine{'' if len(target_machines) == 1 else 's'}."):
            return []
    return [machine["id"] for machine in target_machines]


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


def print_machines(machines, show_terminated=False):
    """Display Machines in a formatted way"""
    if not machines:
        click.echo("No Machines found")
        return

    machines = machines if show_terminated else [machine for machine in machines if machine["state"].lower() != "terminated"]

    headers = ["ID", "state", "Created"]
    table_data = []
    for machine in machines:
        dt = iso8601.parse_date(machine["created_at"])
        state = click.style(machine["state"], fg="green") if machine["state"].lower() == "running" else machine["state"]
        table_data.append([machine["id"], state, dt.strftime("%Y-%m-%d %H:%M")])
    click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))


def print_images(images, all=False):
    """Display images in a formatted way"""
    if not images:
        click.echo("No images found")
        return

    if not all:
        # filter to owned images, which have a teamID
        images = [img for img in images if img["team_id"]]

    headers = ["ID", "Tag", "Parent", "state", "Created"]
    table_data = []
    for img in images:
        dt = iso8601.parse_date(img["created_at"])
        table_data.append([img["id"], img["tag"], img["parent_id"] or "base", img["state"], dt.strftime("%Y-%m-%d %H:%M")])
    click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))


# CLI entrypoints


@click.group()
def cli():
    """pig CLI for managing Windows Machines"""
    pass


@cli.command()
@click.option("--image", "-i", required=False, help="Image ID to use")
def create(image):
    """Create a new Machine"""
    click.echo("Creating Machine...")
    machine = client.machines.create(image)
    click.echo(f"Created Machine\t{machine.id}")


@cli.command()
@click.argument("id", required=False)
def connect(id):
    """Starts a connection with a Machine"""
    if not id:
        id = prompt_for_machine_id()
        if not id:
            return

    machine = client.machines.get(id)
    with machine.connect() as _:
        pass

@cli.command()
@click.argument("ids", nargs=-1, required=False)
@click.option("--all", "-a", is_flag=True, help="Start all Machines")
@click.option("-y", "auto_approve", is_flag=True, help="Skip confirmation prompt")
def start(ids, all, auto_approve):
    """Start an existing Machine"""
    if all:
        ids = prompt_for_all("start", auto_approve, exclude="Running")
        if len(ids) == 0:
            return
    if not ids and not all:
        ids = [prompt_for_machine_id(exclude="Running")]
        if ids[0] is None:
            return
        if len(ids) == 0:
            return

    # Get all in flight at the same time
    async def start_machine(id):
        try:
            machine = await client.machines.get.aio(id)
            click.echo(f"Starting {id}...")
            await machine.start.aio()
            click.echo("Started")
        except Exception as e:
            click.echo(f"Failed to start Machine {id}: {str(e)}", err=True)

    async def run_starts():
        await asyncio.gather(*[start_machine(id) for id in ids])

    asyncio.run(run_starts())


@cli.command()
@click.argument("ids", nargs=-1, required=False)
@click.option("--all", "-a", is_flag=True, help="Stop all Machines")
@click.option("-y", "auto_approve", is_flag=True, help="Skip confirmation prompt")
def stop(ids, all, auto_approve):
    """Stop an existing Machine"""
    if all:
        ids = prompt_for_all("stop", auto_approve, exclude="Stopped")
        if len(ids) == 0:
            return
    if not ids and not all:
        ids = [prompt_for_machine_id(exclude="Stopped")]
        if ids[0] is None:
            return

    async def stop_machine(id):
        try:
            machine = await client.machines.get.aio(id)
            click.echo(f"Stopping {id}...")
            await machine.stop.aio()
            click.echo("Stopped")
        except Exception as e:
            click.echo(f"Failed to stop Machine {id}: {str(e)}", err=True)

    async def run_stops():
        await asyncio.gather(*[stop_machine(id) for id in ids])

    asyncio.run(run_stops())


@cli.command()
@click.argument("ids", nargs=-1, required=False)
@click.option("--all", "-a", is_flag=True, help="Terminate all Machines")
@click.option("-y", "auto_approve", is_flag=True, help="Skip confirmation prompt")
def terminate(ids, all, auto_approve):
    """Terminate an existing Machine"""
    if all:
        ids = prompt_for_all("terminate", auto_approve)
        if len(ids) == 0:
            return
    if not ids and not all:
        ids = [prompt_for_machine_id()]
        if ids[0] is None:
            return

    # Get all in flight at the same time
    async def terminate_machine(id):
        try:
            machine = await client.machines.get.aio(id)
            click.echo(f"Terminating {id}...")
            await machine.terminate.aio()
            click.echo("Terminated")
        except Exception as e:
            click.echo(f"Failed to terminate Machine {id}: {str(e)}", err=True)

    async def run_terminates():
        await asyncio.gather(*[terminate_machine(id) for id in ids])

    asyncio.run(run_terminates())


@cli.command()
@click.option("--all", "-a", is_flag=True, help="Show all Machines, including terminated ones")
def ls(all):
    """List all Machines"""
    machines = asyncio.run(get_machines())
    print_machines(machines, show_terminated=all)


@cli.group()
def img():
    """Commands for managing Machine images"""
    pass


@img.command()
@click.option("--all", "-a", is_flag=True, help="Show all images, including Pig standard images")
def ls(all):  # noqa: F811
    """List all images"""
    images = asyncio.run(get_images())
    print_images(images, all)


@img.command()
@click.option("--machine", "m", required=True, help="Machine ID to snapshot")
@click.option("--tag", "-t", required=True, help='Tag (name) for the snapshot. Example: --tag my_snapshot or --tag "My Snapshot"')
@click.option("-y", "auto_approve", is_flag=True, help="Skip confirmation prompt")
def snapshot(machine, tag, auto_approve):
    """Take a snapshot of a running Machine"""
    if not auto_approve:
        if not prompt_confirm("This will take up to 15 minutes to complete, and will permanently terminate the parent Machine."):
            return

    click.echo(f"Snapshotting Machine\t{machine}...")
    asyncio.run(snapshot_image(machine, tag))
    click.echo(f"Image snapshot started, check back at `pig img ls` for state.")


# Add img to cli group
cli.add_command(img)


def main():
    cli()
