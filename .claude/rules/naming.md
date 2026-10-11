# Naming

New code follows these rules. Code written before them does not all follow yet, so an older name is
not a precedent. A few older names stay as they are by decision and are not renamed: `create_app`,
`startup`, `get_alembic_config`, `get_managed_session`, and the `e` in `except Exception as e:` in
`app/core/database.py`.

## Functions get verbs, values get nouns

A function's name starts with a verb — a one-line private helper, a method and a test helper
included. A function is never named by a bare noun:

- `async_engine()` -> `get_async_engine()`
- `async_session_factory()` -> `get_async_session_factory()`

A bare noun is reserved for a value: `current_genre = await self.get_genre_by_id(_id)`. A property
reads like a value, so it is named like one, and so is a pytest fixture that a test asks for by
name (`session`, `member_client`, `mock_broker`) and a constant
(`POSTGRES_INDEXES_NAMING_CONVENTION`, not `HOW_TO_NAME_INDEXES`; `MAX_GENRE_NAME_LENGTH`, not
`GENRE_NAME_TOO_LONG`). A value is not named by a participle or a bare adjective either:
`existing_user`, not `existing`; `raw_message`, not `raw`.

## The verb says what the function actually does

`get_` is only for handing back something that already exists: a field, an object built once and
cached (`get_settings`, `get_broker`, `get_aioboto_session`), or a row that has to be there -
`get_by_id` raises `NotFoundError` when it is not. Anything that looks something up or transforms
it takes the verb this repo uses for that shape of work:

- `find_…`      looks something up by a name or a key and may find nothing - `find_user_by_email`
  returns `UserSchema | None`
- `list_…`      every row of one kind - `list_genres`, `list_all`, `list_keys`
- `create_…`    one row inserted - `create_genre`, `create_user`
- `update_…`    one row changed - `update_genre`
- `delete_…`    rows or objects removed - `delete_genre`, `delete_all_objects`
- `build_…`     assembles a structure or a prompt in memory - `build_user_creation_exchange` makes
  a new `RabbitExchange` on every call
- `validate_…`  holds a value against a rule and raises a domain exception when the rule is
  broken - `_validate_unique_name`
- `parse_…`     unstructured input -> typed shape, with nothing but the input - `parse_cors_origins`
- `normalize_…` one spelling out of many - `_normalize_name`
- `send_…`      a message handed to an outside service - `send_email`
- `publish_…`   a message put on a broker exchange - `_publish_user_creation_message`
- `open_…`      an async context manager that owns its client - `open_s3_client`

A shape of work the list does not cover gets a verb that names it as exactly - `compute_…` for a
numeric result, `format_…` for a display string - and that verb is then the one to reuse.

A second way to build an object is a classmethod named `from_<source>`, which says what the object
is built from - `Redis.from_url(url)`, `UserCreationMessage.from_user(user)` - not one more optional
argument on `__init__`.

`_handle_genre_name` is wrong where `_validate_unique_name` is right: the verb must name the
operation, not gesture at it.

## The noun names the domain type

Qualify with the type the function works on: `get_genre_by_id`, not `get_by_id`, for a route
handler; `_publish_user_creation_message`, not `_publish_message`; `find_user_by_email`, not
`find_by_email`, in a service.

## Names reveal intent

A name says why the thing exists, what it does and how it is used. If it needs a comment or a look
into the body to answer that, rename it.

- `q_test` -> `user_creation_queue`
- `random.random() < 0.5` -> `random.random() < SIMULATED_FAILURE_RATE`
- `if settings.ENVIRONMENT in (Environment.PRODUCTION, Environment.DEV) and settings.RUN_MIGRATIONS`
  -> `if should_run_migrations(settings)`
- a nested expression that needs explaining gets a named intermediate value instead:
  `created_user = UserSchema.model_validate(response.json())`

## Booleans read as a yes/no statement

- Variables, fields, arguments and predicate functions start with `is_`, `has_`, `can_` or
  `should_`: `should_fail`, `is_active`, `is_rate_limited`.
- Positive form: `is_active`, not `is_not_blocked` - a negative name turns every check into a double
  negative.
- A boolean argument hides a second function. `send_email(message, send_as_html=True)` says nothing
  where it is called; write `send_html_email(message)`.

## No disinformation, no noise

- A name never claims a shape the value does not have:
  - `create_users` registers one user -> `create_user`
  - `create_genres_factory` returns one genre and no factory -> `create_genre`
  - `genres = await service.create_genre(genre)` holds one genre -> `genre`
  - `exc = get_user_creation_exchange()` reads as an exception -> `exchange`
- Names of different things never differ by a word that says nothing about the difference:
  `get_broker` beside `get_rabbit_broker`. The word that separates two names is the thing that
  separates the two objects: `GenreCreateSchema` beside `GenreCreateUpdate` -> `GenreCreateSchema`
  and `GenreUpdateSchema`.
- Words that distinguish nothing are not names: `data`, `info`, `item`, `obj`, `result`, `value`,
  `tmp`, `stub`. If `user` and `user_data` both exist, the reader cannot tell which one to pass. A
  word like that is fine once something qualifies it: `cached_value`, `validation_result`.
- No numbered series: `genre1`, `genre2` -> `requested_genre`, `other_genre`; `test_success2`,
  `test_success3` -> one name per scenario.

## Whole, searchable words

- Write the word out: `error`, `message`, `exchange`, `dependency`, `connection`, `queue` - not
  `e`, `msg`, `exc`, `dep`, `conn`, `q` (`exc` is an exchange in one file and an exception in the
  next). A name must be pronounceable in review and findable by search.
- The names of things stay as the world spells them: `id`, `url`, `s3`, `ses`, `cors`, `ttl`,
  `llm`. A unit closes a constant in the same way: `CACHE_TTL_SECONDS`, `MAX_UPLOAD_SIZE_BYTES`.
- Length follows scope. A single letter is acceptable only as a counter in a loop of a few lines; a
  comprehension or lambda variable is the singular of its collection -
  `[genre.model_dump() for genre in genres]`.
- No type or role encoded in the name: `email`, not `email_str`; `genres`, not `genres_list`;
  `EmailSender`, not `IEmailSender` or `EmailSenderProtocol`. The leading underscore is not such a
  prefix: it is how Python marks a name private to its module, and a private function keeps it.

## One word per concept, one concept per word

- Before adding a verb, check the list above for one that already means it. Two words for one
  operation - `get_all_genres` beside `list_genres`, `make_…` beside `build_…` - make the reader
  look for a difference that is not there.
- A verb keeps one meaning everywhere: `create_…` inserts a row and `build_…` assembles an object
  in memory (`GenreCreationFactory.build()`), so do not use one for the other.
- Plain over clever: `delete_all_objects`, not `nuke_bucket`.

## The name tells everything the function does

- A side effect belongs in the name: a getter that creates the row when it is missing is
  `get_or_create_genre`, not `get_genre`.
- If the honest name needs `and`, the function does two things - split it.
- The name stays at the caller's level and says what, not how: `register_user`, not
  `insert_user_row`.

## Types and classes get nouns

A class, protocol or type alias is a noun phrase: `GenreRepository`, `EmailMessage`,
`UserCreationStatus`. `Manager`, `Processor`, `Helper` and `Utils` name no responsibility - say what
the type holds or does instead.

## Just enough context

- A value that is unclear on its own takes its context from the class that owns it: `subject` and
  `body` are clear as fields of `EmailMessage`. A loose value takes a qualifying word instead:
  `url` -> `minio_endpoint_url`. Several loose values that share a prefix belong in a schema.
- Do not repeat what the owner already says: `genre.name`, not `genre.genre_name`.
- Use the word the business uses for a domain thing and the pattern name for a technical one:
  `genre`, `user`, `registration`; `…Repository`, `…Service`, `…UseCase`, `…Schema`, `…Model`,
  `…Factory`.
