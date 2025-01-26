#!/usr/bin/env python3
import os

import click
import iso8601
from tabulate import tabulate

from .pig import BASE_URL, VM, APIClient

API_KEY = os.environ.get("PIG_SECRET_KEY")
if not API_KEY:
    raise ValueError("PIG_SECRET_KEY environment variable not set")

def get_vms():
    """Fetch VMs from the API"""
    client = APIClient(base_url=BASE_URL, api_key=API_KEY)
    return client.get(f"vms")

def print_vms(vms, show_terminated=False):
    """Display VMs in a formatted way"""
    if not vms:
        click.echo("No VMs found")
        return
    
    vms = vms if show_terminated else [vm for vm in vms if vm['status'].lower() != 'terminated']
        
    headers = ['ID', 'Status', 'Created']
    table_data = []
    for vm in vms:
        dt = iso8601.parse_date(vm['created_at'])
        status = click.style(vm['status'], fg='green') if vm['status'].lower() == 'running' else vm['status']
        table_data.append([vm['id'], status, dt.strftime("%Y-%m-%d %H:%M")])
    click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))

@click.group()
def cli():
    """pig CLI for managing Windows VMs"""
    pass

@cli.command()
def create():
    """Create a new VM"""
    vm = VM()
    click.echo("Creating VM...")
    vm.create()
    click.echo(f"Created VM\t{vm.id}")

@cli.command()
@click.argument('id', required=True)
def connect(id):
    """Starts a connection with a VM"""
    vm = VM(id=id)
    _conn = vm.connect() # Prints url

@cli.command()
@click.argument('id')
def start(id):
    """Start an existing VM"""
    vm = VM(id=id)
    click.echo(f"Starting VM\t{id}...")
    vm.start()
    click.echo("Started")

@cli.command()
@click.argument('id')
def stop(id):
    """Stop a VM"""
    vm = VM(id=id)
    click.echo(f"Stopping VM\t{id}...")
    vm.stop()
    click.echo("Stopped")

@cli.command()
@click.argument('id')
def terminate(id):
    """Terminate and delete a VM"""
    vm = VM(id=id)
    click.echo(f"Terminating VM\t{id}...")
    vm.terminate()
    click.echo("Terminated")

@cli.command()
@click.option('--all', '-a', is_flag=True, help='Show all VMs, including terminated ones')
def ls(all):
    """List all VMs"""
    vms = get_vms()
    print_vms(vms, show_terminated=all)

def main():
    cli()