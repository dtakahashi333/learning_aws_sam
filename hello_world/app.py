"""
hello_world.app

AWS Lambda handlers for a simple chatbot project.
Includes:
- hello_handler: returns "Hello"
- goodbye_handler: returns "Goodbye"
- Database session helpers
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import aiohttp
import asyncpg  # type: ignore[import]
import dashscope  # type: ignore[import]  # noqa: F401
from openai import AsyncOpenAI

# import requests


# ---------------------------------------------------------------------------
# Lambda Handlers
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e
    _ = event
    _ = context

    # Print all environment variables
    print(dict(os.environ))

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "hello world",
                # "location": ip.text.replace("\n", "")
            }
        ),
    }


def hello_handler(event, context):
    """
    AWS Lambda handler that returns a simple greeting message "Hello".

    Args:
        event (dict): The event data passed by AWS Lambda (ignored in this handler).
        context (LambdaContext): Runtime information provided by AWS Lambda (ignored).

    Returns:
        dict: A dictionary containing:
            - statusCode (int): HTTP status code 200.
            - body (str): The response message "Hello".
    """
    _ = event
    _ = context
    return {
        "statusCode": 200,
        "body": "Hello",
    }


def goodbye_handler(event, context):
    """
    AWS Lambda handler that returns a simple farewell message "Goodbye".

    Args:
        event (dict): The event data passed by AWS Lambda (ignored in this handler).
        context (LambdaContext): Runtime information provided by AWS Lambda (ignored).

    Returns:
        dict: A dictionary containing:
            - statusCode (int): HTTP status code 200.
            - body (str): The response message "Goodbye".
    """
    _ = event
    _ = context
    return {
        "statusCode": 200,
        "body": "Goodbye",
    }


# ---------------------------------------------------------------------------
# AWS Lambda entrypoint (required wrapper)
# ---------------------------------------------------------------------------


def chatbot_handler(event, context):
    """
    Synchronous AWS Lambda entry point for the async chatbot handler.

    This function serves as a wrapper that executes the asynchronous
    `chatbot_handler_async` using `asyncio.run`, enabling compatibility
    with AWS Lambda's synchronous invocation model.

    Args:
        event (dict): The Lambda event payload passed to the async handler.
        context (LambdaContext): Runtime information provided by AWS Lambda.

    Returns:
        dict: HTTP-style response returned by `chatbot_handler_async`.

    Raises:
        Exception: Propagates any exception raised by the async handler.
    """

    # Print all environment variables
    print(dict(os.environ))

    return asyncio.run(chatbot_handler_async(event, context))


# ---------------------------------------------------------------------------
# Async Lambda handler
# ---------------------------------------------------------------------------


async def chatbot_handler_async(event, context):
    """
    AWS Lambda handler for managing a chat session with a language model.

    This asynchronous function:
    - Retrieves the session ID from request headers (X-Session-Id)
    - Fetches or creates a session in the database
    - Appends the user's message to the session
    - Sends the message history to an LLM to generate a response
    - Persists the updated session data
    - Returns the session data and session ID in the response

    Args:
        event (dict): The Lambda event payload, expected to contain:
            - "headers": dict containing "X-Session-Id" (optional)
            - "body": JSON string or dict containing "message"
        context (LambdaContext): Runtime information provided by AWS Lambda
            (unused in this handler).

    Returns:
        dict: HTTP-style response with:
            - statusCode (int): 200 for success, 400 for missing message
            - headers (dict): contains "X-Session-Id"
            - body (str): JSON-encoded session data (on success)

    Raises:
        ValueError: If the session is not found.
        asyncpg.PostgresError: If a database operation fails.
        aiohttp.ClientError: If the LLM API request fails.
    """
    # 👇 handle preflight request
    if event["httpMethod"] == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,X-Session-Id",
                "Access-Control-Expose-Headers": "X-Session-Id",
            },
            "body": "",
        }

    _ = context

    pool = await get_db_pool()

    headers = event.get("headers") or {}
    session_id = headers.get("X-Session-Id")

    try:
        session_id, session_data = await get_session_data(pool, session_id)
    except ValueError:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Session not found"}),
        }

    body = event.get("body", "{}")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {}

    message = body.get("message", "")

    if message:
        session_data["messages"].append(
            {
                "role": "user",
                "content": message,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        response = await generate_llm_response(
            session_data, api_type=os.getenv("CHAT_API_TYPE", "openapi")
        )

        session_data["messages"].append(
            {
                "role": "assistant",
                "content": response,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        await save_session_data(pool, session_id, session_data)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # 👈 CORS
                "Access-Control-Allow-Headers": "Content-Type,X-Session-Id",  # 👈 CORS
                "Access-Control-Expose-Headers": "X-Session-Id",  # 👈 expose custom header to browser
                "X-Session-Id": session_id,  # 👈 your custom header
            },
            "body": json.dumps({"reply": response}),
        }

    return {
        "statusCode": 400,
        "headers": {"X-Session-Id": session_id},
    }


# pylint produces: "W0603: Using the global statement (global-statement)"
# # Private module-level variable (no global statement needed)
# __DB_CONN = None


# def get_db_conn():
#     """
#     Get or create a cached PostgreSQL database connection.

#     Returns:
#         psycopg2.extensions.connection: Active database connection.
#     """
#     global __DB_CONN
#     if __DB_CONN is None:
#         __DB_CONN = psycopg2.connect(
#             host=os.getenv("PG_HOST"),
#             port=os.getenv("PG_PORT"),
#             user=os.getenv("PG_USER"),
#             password=os.getenv("PG_PASSWORD"),
#             dbname=os.getenv("PG_DB"),
#         )
#     return __DB_CONN


# ---------------------------------------------------------------------------
# Async DB Pool (cached across Lambda invocations)
# ---------------------------------------------------------------------------


# pylint produces: "W0212: Access to a protected member _conn of a client class (protected-access)"
async def get_db_pool():
    """
    Get or create a cached PostgreSQL connection pool.

    This asynchronous function initializes and caches an asyncpg connection pool
    for reuse across multiple invocations (e.g., in AWS Lambda) to reduce
    connection overhead and improve performance.

    Returns:
        asyncpg.pool.Pool: An active asyncpg connection pool.

    Raises:
        asyncpg.PostgresError: If the connection pool cannot be created.
    """
    get_db_pool._pool = await asyncpg.create_pool(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT", 5432)),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        database=os.getenv("PG_DB"),
        min_size=1,
        max_size=5,
    )
    return get_db_pool._pool


# ---------------------------------------------------------------------------
# Session helpers (async)
# ---------------------------------------------------------------------------


async def get_session_data(pool, session_id=None, user_id=None):
    """
    Retrieve or create a chat session in the database.

    This asynchronous function acquires a connection from the database pool
    and either fetches an existing session by session_id or creates a new session
    with an optional user_id if no session_id is provided.

    Args:
        pool (asyncpg.pool.Pool): An active asyncpg connection pool.
        session_id (str | None): Existing session ID to fetch. If None, a new session is created.
        user_id (str | None, optional): User ID to associate with a new session. Defaults to None.

    Returns:
        tuple[str, dict]: A tuple containing:
            - session_id (str): The session ID
            - session_data (dict): The session data

    Raises:
        ValueError: If a session_id is provided but not found.
        asyncpg.PostgresError: If a database operation fails.
    """
    async with pool.acquire() as conn:
        if not session_id:
            # Create a new session
            session_id = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=1
            )  # naive datetime for TIMESTAMP
            initial_data = {"messages": []}

            await conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, data, expires_at)
                VALUES ($1, $2, $3, $4)
                """,
                session_id,
                user_id,
                json.dumps(initial_data),
                expires_at,
            )
            return session_id, initial_data

        # Fetch existing session
        row = await conn.fetchrow(
            """
            SELECT session_id, user_id, data, created_at, expires_at
            FROM sessions
            WHERE session_id = $1
            """,
            session_id,
        )

        if not row:
            raise ValueError(f"Session with ID {session_id} not found")

        return session_id, json.loads(row["data"])


async def save_session_data(pool, session_id, session_data, expires_at=None):
    """
    Update the stored session data for a given session ID.

    This asynchronous function acquires a connection from the database pool
    and updates the session record in PostgreSQL. Optionally, the session's
    expiration timestamp can also be updated.

    Args:
        pool (asyncpg.pool.Pool): An active asyncpg connection pool.
        session_id (str): The session ID to update.
        session_data (dict): The chat session data to store.
        expires_at (datetime | None, optional): New expiration timestamp.
            If provided, updates the 'expires_at' column. Defaults to None.

    Returns:
        None

    Raises:
        ValueError: If the session_id does not exist in the database.
        asyncpg.PostgresError: If the database operation fails.
    """
    async with pool.acquire() as conn:
        if expires_at:
            expires_at = expires_at.replace(tzinfo=None)  # ensure naive datetime
            result = await conn.execute(
                """
                UPDATE sessions
                SET data = $1, expires_at = $2
                WHERE session_id = $3
                """,
                json.dumps(session_data),
                expires_at,
                session_id,
            )
        else:
            result = await conn.execute(
                """
                UPDATE sessions
                SET data = $1
                WHERE session_id = $2
                """,
                json.dumps(session_data),
                session_id,
            )

        if result == "UPDATE 0":
            raise ValueError(f"Session with ID {session_id} not found")

        messages = session_data["messages"]
        print(f"message length: {len(messages)}")
        if len(messages) == 1:
            first_message = messages[0]["content"]
            # 👇 use first message as title, truncated to 40 chars
            title = first_message[:40] + ("..." if len(first_message) > 40 else "")
            result = await conn.execute(
                """
                UPDATE sessions
                SET title = $1
                WHERE session_id = $2
                """,
                title,
                session_id,
            )

        if result == "UPDATE 0":
            raise ValueError(f"Session with ID {session_id} not found")


async def generate_llm_response(session_data, api_type="openai"):
    """
    Generate a response from a language model based on the current session.

    This asynchronous function constructs a message history from the session data,
    sends it to the specified LLM provider, and returns the generated assistant response.

    Args:
        session_data (dict): Current session data containing previous messages.
            Expected format:
                {
                    "messages": [
                        {"role": "user" | "assistant", "content": str},
                        ...
                    ]
                }
        api_type (str, optional): The API provider to use. Supported values:
            - "openai"
            - "dashscope"
            Defaults to "openai".

    Returns:
        str: The generated response content from the assistant.

    Raises:
        ValueError: If an unsupported api_type is provided.
    """
    filtered = [
        {"role": m["role"], "content": m["content"]} for m in session_data["messages"]
    ]
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        *filtered,
    ]

    if api_type == "openai":
        return await call_openai(messages)
    elif api_type == "dashscope":
        return await call_dashscope(messages)
    raise ValueError(f"Unsupported api_type: {api_type}")


async def call_openai(messages):
    """
    Generate a response from a language model using an OpenAI-compatible API.

    This function sends a list of chat messages to an OpenAI-compatible endpoint
    (e.g., DashScope's compatible mode) using the async OpenAI client and returns
    the parsed assistant response.

    Args:
        messages (list[dict]): A list of message objects representing the conversation
            history. Each message should follow the format:
            {"role": "user" | "assistant" | "system", "content": str}

    Returns:
        str: The generated response content from the assistant.
    """
    # OpenAI Chat Completion: Mature community ecosystem. Offers the lowest cost for migrating existing applications
    # or integrating third-party tools.
    client = AsyncOpenAI(
        # If the environment variable is not set, replace the following line with: api_key="sk-xxx"
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        # The following is the base_url for the Singapore region.
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    completion = await client.chat.completions.create(
        model="qwen-plus",  # Model list: https://www.alibabacloud.com/help/en/model-studio/getting-started/models
        messages=messages,
        # extra_body={"enable_thinking": False},
    )
    print(f"response type: {type(completion)}")
    print(completion.model_dump_json())
    return parse_response(completion, "openai")


async def call_dashscope(messages):
    """
    Generate a response from a language model using the DashScope native API.

    This function sends a list of chat messages to the DashScope generation API
    using an asynchronous HTTP request via aiohttp, and returns the parsed
    assistant response.

    Args:
        messages (list[dict]): A list of message objects representing the conversation
            history. Each message should follow the format:
            {"role": "user" | "assistant" | "system", "content": str}

    Returns:
        str: The generated response content from the assistant.
    """
    url = "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "qwen-plus",
        "input": {"messages": messages},
        "parameters": {"result_format": "message"},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()

    return parse_response(data, "dashscope")


def parse_response(response, api_type):
    """
    Extract the assistant's message content from an LLM API response.

    This function normalizes responses from different API providers
    (e.g., OpenAI, DashScope) by returning the generated text content
    from the first choice.

    Args:
        response (dict): The raw response object returned by the LLM API.
        api_type (str): The API provider type. Supported values:
            - "openai": OpenAI-compatible response format
            - "dashscope": DashScope-compatible response format

    Returns:
        str: The generated message content from the assistant.

    Raises:
        KeyError: If the expected response structure is missing required keys.
        ValueError: If an unsupported api_type is provided.
    """
    if api_type == "openai":
        # return response["choices"][0]["message"]["content"]
        return response.choices[0].message.content
    elif api_type == "dashscope":
        return response["output"]["choices"][0]["message"]["content"]
        # return response.output.choices[0].message.content
    raise ValueError(f"Unsupported api_type: {api_type}")


"""
import os
import dashscope

dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
# This is the base URL for the Singapore region.
messages = [
    {'role': 'system', 'content': 'You are a helpful assistant.'},
    {'role': 'user', 'content': 'Who are you?'}
]
response = dashscope.Generation.call(
    # No DASHSCOPE_API_KEY set? Use api_key="sk-xxx" instead.
    # API keys differ by region. Get an API key: https://www.alibabacloud.com/help/zh/model-studio/get-api-key.
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="qwen-plus", # Replace qwen-plus as needed — model list: https://www.alibabacloud.com/help/zh/model-studio/getting-started/models
    messages=messages,
    result_format='message'
    )
print(response)
"""


def history_handler(event, context):
    """
    Synchronous AWS Lambda entry point for the async history handler.

    This function serves as a wrapper that executes the asynchronous
    `history_handler_async` using `asyncio.run`, enabling compatibility
    with AWS Lambda's synchronous invocation model.

    Args:
        event (dict): The Lambda event payload passed to the async handler.
        context (LambdaContext): Runtime information provided by AWS Lambda.

    Returns:
        dict: HTTP-style response returned by `history_handler_async`.

    Raises:
        Exception: Propagates any exception raised by the async handler.
    """
    return asyncio.run(history_handler_async(event, context))


async def history_handler_async(event, context):
    """
    Retrieve the message history for a specific conversation session.

    This asynchronous handler extracts a session ID from the request path,
    fetches the corresponding session data from the database, and returns
    the conversation history as a JSON response. If the session does not
    exist, a 404 response is returned.

    Args:
        event (dict): The event payload containing request details, including
            the path with the session identifier.
        context (object): The runtime context provided by the execution
            environment (unused).

    Returns:
        dict: An HTTP response containing:
            - statusCode (int): HTTP status code (200 on success, 404 if not found).
            - headers (dict): Response headers including CORS configuration
              (present on success responses).
            - body (str): JSON-encoded string containing the session data or
              an error message.

    Raises:
        asyncpg.PostgresError: If a database operation fails.
        KeyError: If the expected path is missing from the event.
        Exception: For any unexpected errors during processing or serialization.
    """
    _ = context

    path = event["path"]
    print(path)

    session_id = path.split("/history/")[1]

    pool = await get_db_pool()

    try:
        session_id, session_data = await get_session_data(pool, session_id)
    except ValueError:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Session not found"}),
        }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # 👈 CORS
            "Access-Control-Allow-Headers": "Content-Type,X-Session-Id",  # 👈 CORS
            "Access-Control-Expose-Headers": "X-Session-Id",
        },
        "body": json.dumps(session_data),
    }


def conversations_handler(event, context):
    """
    Synchronous AWS Lambda entry point for the async conversations handler.

    This function serves as a wrapper that executes the asynchronous
    `conversations_handler_async` using `asyncio.run`, enabling compatibility
    with AWS Lambda's synchronous invocation model.

    Args:
        event (dict): The Lambda event payload passed to the async handler.
        context (LambdaContext): Runtime information provided by AWS Lambda.

    Returns:
        dict: HTTP-style response returned by `conversations_handler_async`.

    Raises:
        Exception: Propagates any exception raised by the async handler.
    """
    return asyncio.run(conversations_handler_async(event, context))


async def conversations_handler_async(event, context):
    """
    Retrieve the most recent conversations from the database.

    This asynchronous handler queries the PostgreSQL database for the latest
    conversation sessions, returning up to 20 records ordered by creation time
    in descending order. Each conversation includes its session ID, title, and
    ISO-formatted creation timestamp. The response is formatted as a JSON object
    and includes CORS headers for cross-origin access.

    Args:
        event (dict): The event payload triggering the handler (unused).
        context (object): The runtime context provided by the execution environment (unused).

    Returns:
        dict: An HTTP response containing:
            - statusCode (int): HTTP status code (200 on success).
            - headers (dict): Response headers including CORS configuration.
            - body (str): JSON-encoded string with a list of conversations.

    Raises:
        asyncpg.PostgresError: If the database query fails.
        Exception: For any unexpected errors during processing or serialization.
    """
    _ = event
    _ = context

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT session_id, title, created_at
            FROM sessions
            ORDER BY created_at DESC
            LIMIT 20
            """,
        )

        conversations = [
            {
                **dict(row),
                "created_at": (
                    row["created_at"].isoformat() if row["created_at"] else None
                ),
            }
            for row in rows
        ]

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # 👈 CORS
                "Access-Control-Allow-Headers": "Content-Type,X-Session-Id",  # 👈 CORS
                "Access-Control-Expose-Headers": "X-Session-Id",
            },
            "body": json.dumps({"conversations": conversations}),
        }
