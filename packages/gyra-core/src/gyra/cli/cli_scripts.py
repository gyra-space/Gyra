import copy
import logging

import click

# Removed logging.basicConfig to prevent duplicate log output
# The actual logging setup is handled by gyra.util.logger.setup_logging
# which is called during application initialization

logger = logging.getLogger("gyra_cli")


@click.group()
@click.option(
    "--log-level",
    required=False,
    type=str,
    default="warn",
    help="Log level",
)
@click.version_option()
def cli(log_level: str):
    logger.setLevel(logging.getLevelName(log_level.upper()))


def add_command_alias(command, name: str, hidden: bool = False, parent_group=None):
    if not parent_group:
        parent_group = cli
    new_command = copy.deepcopy(command)
    new_command.hidden = hidden
    parent_group.add_command(new_command, name=name)


@click.group()
def start():
    """Start specific server."""
    pass


@click.group()
def stop():
    """Start specific server."""
    pass


@click.group()
def install():
    """Install dependencies, plugins, etc."""
    pass


@click.group()
def db():
    """Manage your metadata database and your datasources."""
    pass


@click.group()
def new():
    """New a template."""
    pass


@click.group()
def app():
    """Manage your apps(gyras)."""
    pass


@click.group()
def repo():
    """The repository to install the gyras from."""
    pass


@click.group()
def run():
    """Run your gyras."""
    pass


@click.command(name="quickstart")
@click.option(
    "-c",
    "--config",
    type=str,
    default=None,
    required=False,
    help="Config file path (optional)",
)
@click.option(
    "-p",
    "--port",
    type=int,
    default=8888,
    help="Server port (default: 8888)",
)
@click.option(
    "-h",
    "--host",
    type=str,
    default="0.0.0.0",
    help="Server host (default: 0.0.0.0)",
)
def quickstart(config: str, port: int, host: str):
    """Quick start Gyra server with zero configuration.

    Examples:
        gyra quickstart                    # Start with zero config
        gyra quickstart -p 8888            # Start on port 8888
        gyra quickstart -c config.toml     # Start with config file

    After starting, open http://localhost:8888 to configure models and settings.
    """
    import os
    import sys

    if config:
        os.environ["GYRA_CONFIG_FILE"] = config
    if port != 8888:
        os.environ["GYRA_WEB_PORT"] = str(port)
    if host != "0.0.0.0":
        os.environ["GYRA_WEB_HOST"] = host

    try:
        from gyra_app.gyra_server import run_webserver

        run_webserver(config)
    except ImportError as e:
        click.echo(f"Error: Failed to import gyra_app: {e}", err=True)
        click.echo("Please ensure gyra-app package is installed.", err=True)
        sys.exit(1)


@click.group()
def net():
    """Net tools."""
    pass


@click.group()
def tool():
    """GYRA Tools."""


stop_all_func_list = []


@click.command(name="all")
def stop_all():
    """Stop all servers"""
    for stop_func in stop_all_func_list:
        stop_func()


cli.add_command(start)
cli.add_command(stop)
cli.add_command(db)
cli.add_command(new)
cli.add_command(app)
cli.add_command(repo)
cli.add_command(run)
cli.add_command(net)
cli.add_command(tool)
cli.add_command(quickstart)
add_command_alias(stop_all, name="all", parent_group=stop)

try:
    from gyra_app._cli import (
        _stop_all_gyra_server,
        migration,
        start_webserver,
        stop_webserver,
    )

    add_command_alias(start_webserver, name="webserver", parent_group=start)
    add_command_alias(stop_webserver, name="webserver", parent_group=stop)
    add_command_alias(start_webserver, name="all", parent_group=start, hidden=True)
    add_command_alias(migration, name="migration", parent_group=db)
    stop_all_func_list.append(_stop_all_gyra_server)

except ImportError as e:
    logging.warning(f"Integrating gyra webserver command line tool failed: {e}")

# Knowledge CLI module not yet implemented
# try:
#     from gyra_app.knowledge._cli.knowledge_cli import knowledge_cli_group
#
#     add_command_alias(knowledge_cli_group, name="knowledge", parent_group=cli)
# except ImportError as e:
#     logging.warning(f"Integrating gyra knowledge command line tool failed: {e}")


try:
    from gyra.util.tracer.tracer_cli import trace_cli_group

    add_command_alias(trace_cli_group, name="trace", parent_group=cli)
except ImportError as e:
    logging.warning(f"Integrating gyra trace command line tool failed: {e}")

try:
    from gyra_serve.utils.cli import serve

    add_command_alias(serve, name="serve", parent_group=new)
except ImportError as e:
    logging.warning(f"Integrating gyra serve command line tool failed: {e}")


try:
    from gyra.util.cli.flow_compat import tool_flow_cli_group
    from gyra.util.gyras.cli import (
        add_repo,
        list_installed_apps,
        list_repos,
        new_gyras,
        reinstall,
        remove_repo,
        update_repo,
    )
    from gyra.util.gyras.cli import install as app_install
    from gyra.util.gyras.cli import list_all_apps as app_list_remote
    from gyra.util.gyras.cli import uninstall as app_uninstall

    add_command_alias(list_repos, name="list", parent_group=repo)
    add_command_alias(add_repo, name="add", parent_group=repo)
    add_command_alias(remove_repo, name="remove", parent_group=repo)
    add_command_alias(update_repo, name="update", parent_group=repo)
    add_command_alias(app_install, name="install", parent_group=app)
    add_command_alias(app_uninstall, name="uninstall", parent_group=app)
    add_command_alias(reinstall, name="reinstall", parent_group=app)
    add_command_alias(app_list_remote, name="list-remote", parent_group=app)
    add_command_alias(list_installed_apps, name="list", parent_group=app)
    add_command_alias(new_gyras, name="app", parent_group=new)
    add_command_alias(tool_flow_cli_group, name="flow", parent_group=tool)

except ImportError as e:
    logging.warning(f"Integrating gyra gyras command line tool failed: {e}")

try:
    from gyra_client._cli import flow as run_flow

    add_command_alias(run_flow, name="flow", parent_group=run)
except ImportError as e:
    logging.warning(f"Integrating gyra client command line tool failed: {e}")

try:
    from gyra.util.network._cli import start_forward

    add_command_alias(start_forward, name="forward", parent_group=net)
except ImportError as e:
    logging.warning(f"Integrating gyra net command line tool failed: {e}")


def main():
    return cli()


if __name__ == "__main__":
    main()
