This is a Python wrapper for GitHub's GraphQL API.

At the moment of this writing, there was no package I could find that had features I needed (support for Projects)
so I decided to start my own.


The module basically consists of auto-generate code using an excellent GraphQL library called [sgqlc](https://github.com/profusion/sgqlc)
that does all the heavy lifting of interacting with a GraphQL endpoint in object-oriented way.


The schema.json and github_schema.py files were generated (just following sgqlc documentation) by running:
```sh
python \
    -m sgqlc.introspection \
    --exclude-deprecated \
    -H "Authorization: bearer ${TOKEN}" \
    https://server.com/graphql \
    schema.json
```
and then:
```sh
sgqlc-codegen schema schema.json github_schema.py
```

One benefit of GraphQL is to dynamically create queries and request only data needed for the particular case, however the module
could still implements few frequently-used functions for convenience. For now, I'm including example.py with couple of those.