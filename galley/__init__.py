"""Init."""
import os
from pathlib import Path
import sys

from cleo import Application, Command

import aiohttp
from aiohttp_swagger3 import SwaggerFile, SwaggerUiSettings
from loguru import logger
from tortoise import Tortoise

from .views import BookPage, BookRevision, create_book


async def setup(app):
    """Set up app config."""
    await Tortoise.init(db_url=app['dburi'],
                        modules={'models': ['galley.models']})
    await Tortoise.generate_schemas()


class ServerCommand(Command):
    """Start listening with aiohttp server.

    start_server
        {--host=0.0.0.0 : Host to listen on}
        {--port=8080 : Port to listen on}
        {--dburi=sqlite://test.sqlite : DBURI}
        {--debug : Debug and verbose mode}
        {--gunicorn : Enable gunicorn}
        {--logs=logs/ : Log folder}
        {--prefix= : API prefix to expose}
    """

    project_dir = Path('.').absolute()
    project_name = os.getenv('project_name', sys.argv[0].split('/')[-1])

    def handle(self):
        """Handle command."""
        debug = os.getenv('DEBUG', self.option('debug'))
        host = os.getenv('HOST', self.option('host'))
        port = os.getenv('PORT', self.option('port'))
        database = os.getenv("DBURI", self.option('dburi'))
        app = aiohttp.web.Application(debug=debug)
        spec = str((self.project_dir / 'openapi' / 'schema.yml').absolute())
        app['dburi'] = database
        app['router'] = SwaggerFile(
            app,
            spec_file=spec,
            swagger_ui_settings=SwaggerUiSettings(path="/docs/"))
        app['router'].add_post('/book/', create_book)
        app['router'].add_view('/book/{book_id}/{page}', BookPage)
        app['router'].add_view('/book/{book_id}/{page}/{revision}',
                               BookRevision)
        app.on_startup.append(setup)
        aiohttp.web.run_app(app, host=host, port=int(port), access_log=None)


def run_app():
    """Run app."""
    application = Application()
    application.add(ServerCommand())
    application.run()


if __name__ == "__main__":
    run_app()
