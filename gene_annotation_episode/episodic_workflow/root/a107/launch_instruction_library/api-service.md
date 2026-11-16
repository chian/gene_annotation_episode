# Bound API/service information

An API/service resource child investigates how to execute the assigned job
through its actual service. That remains a different episode structure from
local compute or PBS. These instructions supply known service information;
they do not install a resource binding or turn arbitrary HTTP documentation
into an available tool. Use only operations in the current episode's actual
catalog and preserve the parent's algorithm/database/input constraints.

The current checkout binds `launch_api` through `ExecutionEpisodes` →
`HMMERAPIExecution` → the native `PublicClients` HTTP operations. The API episode
chooses each bounded operation in the shared loop. `ExecutionProgressProvider`
supplies independent exact-job observations to ordinary monitor episodes;
`results` acquires the explicitly requested page. Internal ToolRegistry
publication retains native scientific records; there are no ordinary `public.hmmer.*`
execution/discovery tools. Network access and the response at the
selected operation determine actual availability; configuration alone does not.

The [provider's API guide](https://hmmer-web-docs.readthedocs.io/en/latest/api.html)
documents asynchronous JSON submission and result acquisition:

- POST `https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/phmmer`
- POST `https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/hmmscan`
- GET `https://www.ebi.ac.uk/Tools/hmmer/api/v1/result/{id}`

The actual client also uses GET `/Tools/hmmer/api/v1/search/{id}` for status
and GET `/Tools/hmmer/api/v1/search/databases` for current database metadata.
The provider's [OpenAPI schema](https://www.ebi.ac.uk/Tools/hmmer/api/v1/openapi.json)
is the machine-readable contract.

The service documentation describes more algorithms than the bound search
operation permits. This binding accepts only single-protein `phmmer` and
`hmmscan`; a documented endpoint does not enable `hmmsearch`, `jackhmmer` or
batch execution.
