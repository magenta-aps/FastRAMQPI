<!--
SPDX-FileCopyrightText: 2021 Magenta ApS <https://magenta.dk>
SPDX-License-Identifier: MPL-2.0
-->

# FastRAMQPI

FastRAMQPI is an opinionated library for FastAPI and RAMQP.

It is implemented as a thin wrapper around `FastAPI` and `RAMQP`.
It is very MO specific.

## Usage

```python
from typing import Any

from fastapi import APIRouter
from fastapi import FastAPI
from fastramqpi.config import Settings as FastRAMQPISettings
from fastramqpi.main import FastRAMQPI
from gql.client import AsyncClientSession
from pydantic import BaseSettings
from pydantic import Field
from ramqp.depends import Context
from ramqp.depends import RateLimit
from ramqp.mo import MORouter
from ramqp.mo import PayloadUUID


class Settings(BaseSettings):
    class Config:
        frozen = True
        env_nested_delimiter = "__"

    fastramqpi: FastRAMQPISettings = Field(
        default_factory=FastRAMQPISettings, description="FastRAMQPI settings"
    )


fastapi_router = APIRouter()
amqp_router = MORouter()


@amqp_router.register("engagement")
async def listen_to_engagements(context: Context, uuid: PayloadUUID, _: RateLimit) -> None:
    graphql_session: AsyncClientSession = context["graphql_session"]
    program_settings = context["user_context"]["settings"]
    print(uuid)


def create_fastramqpi(**kwargs: Any) -> FastRAMQPI:
    settings = Settings(**kwargs)
    fastramqpi = FastRAMQPI(
        application_name="os2mo-example-integration", settings=settings.fastramqpi
    )
    fastramqpi.add_context(settings=settings)

    # Add our AMQP router(s)
    amqpsystem = fastramqpi.get_amqpsystem()
    amqpsystem.router.registry.update(amqp_router.registry)

    # Add our FastAPI router(s)
    app = fastramqpi.get_app()
    app.include_router(fastapi_router)

    return fastramqpi


def create_app(**kwargs: Any) -> FastAPI:
    fastramqpi = create_fastramqpi(**kwargs)
    return fastramqpi.get_app()
```

### Metrics
FastRAMQPI Metrics are exported via `prometheus/client_python` on the FastAPI's `/metrics`.


## Autogenerated GraphQL Client
FastRAMQPI exposes an
[authenticated httpx client](https://docs.authlib.org/en/latest/client/api.html#authlib.integrations.httpx_client.AsyncOAuth2Client)
through the dependency injection system. While it is possible to call the OS2mo
API directly through it, the recommended approach is to define a properly-typed
GraphQL client in the integration and configure it to make calls through the
authenticated client. Instead of manually implementing such client, we strongly
recommend to use the
[**Ariadne Code Generator**](https://github.com/mirumee/ariadne-codegen), which
generates an integration-specific client based on the general OS2mo GraphQL
schema and the exact queries and mutations the integration requires.

To integrate such client, first add and configure the codegen:
```toml
# pyproject.toml

[tool.poetry.dependencies]
ariadne-codegen = {extras = ["subscriptions"], version = "^0.7.1"}

[tool.ariadne-codegen]
# Ideally, the GraphQL client is generated as part of the build process and
# never committed to git. Unfortunately, most of our tools and CI analyses the
# project directly as it is in Git. In the future - when the CI templates
# operate on the built container image - only the definition of the schema and
# queries should be checked in.
#
# The default package name is `graphql_client`. Make it more obvious that the
# files are not to be modified manually.
target_package_name = "autogenerated_graphql_client"
target_package_path = "my_integration/"
client_name = "GraphQLClient"
schema_path = "schema.graphql"  # curl -O http://localhost:5000/graphql/v8/schema.graphql
queries_path = "queries.graphql"
plugins = [
    # Return values directly when only a single top field is requested
    "ariadne_codegen.contrib.shorter_results.ShorterResultsPlugin",
]
[tool.ariadne-codegen.scalars.DateTime]
type = "datetime.datetime"
[tool.ariadne-codegen.scalars.UUID]
type = "uuid.UUID"
```
Where you replace `"my_integration/"` with the path to your integration.

Grab OS2mo's GraphQL schema:
```bash
curl -O http://localhost:5000/graphql/v8/schema.graphql
```
Define your queries:
```gql
# queries.graphql

# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0

query Version {
  version {
    mo_version
    mo_hash
  }
}
```
Generate the client - you may have to activate some virtual environment:
```bash
ariadne-codegen
```
The client class is passed to FastRAMQPI on startup. This will ensure it is
automatically opened and closed and configured with authentication:

```python
# app.py
from autogenerated_graphql_client import GraphQLClient


def create_app(**kwargs: Any) -> FastAPI:
    fastramqpi = FastRAMQPI(..., graphql_client_cls=GraphQLClient)
    ...
```
The FastRAMQPI framework cannot define the annotated type for the GraphQL client
since its methods depend on the specific queries required by the integration.
Therefore, each implementing integration needs to define their own:
```python
# depends.py
from typing import Annotated

from fastapi import Depends
from ramqp.depends import from_context

from my_integration.autogenerated_graphql_client import GraphQLClient as _GraphQLClient

GraphQLClient = Annotated[_GraphQLClient, Depends(from_context("graphql_client"))]
```
Finally, we can define our AMQP handler to use the GraphQL client:
```python
# events.py
from . import depends


@router.register("*")
async def handler(mo: depends.GraphQLClient) -> None:
    version = await mo.version()
    print(version)
```

To get REUSE working, you might consider adding the following to `.reuse/dep5`:
```text
Files: my_integration/autogenerated_graphql_client/*
Copyright: Magenta ApS <https://magenta.dk>
License: MPL-2.0
```


## Development

### Prerequisites

- [Poetry](https://github.com/python-poetry/poetry)

### Getting Started

1. Clone the repository:
```
git clone git@git.magenta.dk:rammearkitektur/FastRAMQPI.git
```

2. Install all dependencies:
```
poetry install
```

3. Set up pre-commit:
```
poetry run pre-commit install
```

### Running the tests

You use `poetry` and `pytest` to run the tests:

`poetry run pytest`

You can also run specific files

`poetry run pytest tests/<test_folder>/<test_file.py>`

and even use filtering with `-k`

`poetry run pytest -k "Manager"`

You can use the flags `-vx` where `v` prints the test & `x` makes the test stop if any tests fails (Verbose, X-fail)

## Authors

Magenta ApS <https://magenta.dk>

## License

This project uses: [MPL-2.0](LICENSES/MPL-2.0.txt)

This project uses [REUSE](https://reuse.software) for licensing.
All licenses can be found in the [LICENSES folder](LICENSES/) of the project.
