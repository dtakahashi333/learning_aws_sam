"""
hello_world.app

AWS Lambda handlers for a simple chatbot project.
Includes:
- hello_handler: returns "Hello"
- goodbye_handler: returns "Goodbye"
- Database session helpers
"""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import dashscope  # type: ignore[import]
import psycopg2
from openai import OpenAI

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


def chatbot_handler(event, context):
    """
    AWS Lambda handler for managing a chat session with a language model.

    This function:
    - Retrieves the session ID from request headers (x-session-id).
    - Fetches the existing session data from the database or creates a new session.
    - Appends the user's message to the session.
    - Sends the message history to the language model for generating a response.
    - Updates the session data in the database.
    - Returns the updated session data and session ID in the response headers.

    Args:
        event (dict): The Lambda event payload, expected to contain:
            - "headers": dict containing "x-session-id"
            - "body": dict containing "message" from the user
        context (LambdaContext): Runtime information provided by AWS Lambda
            (unused in this handler).

    Returns:
        dict: HTTP-style response with the following keys:
            - statusCode (int): 200 for success, 400 for missing message
            - headers (dict): contains "x-session-id"
            - body (str): JSON-encoded session data (on success) or empty (on error)
    """
    _ = context

    # Below code is how to access the local PostgreSQL which is running as a docker container.
    # conn = psycopg2.connect(
    #     host=os.environ['PG_HOST'],
    #     port=os.environ['PG_PORT'],
    #     user=os.environ['PG_USER'],
    #     password=os.environ['PG_PASSWORD'],
    #     dbname=os.environ['PG_DB']
    # )
    # cur = conn.cursor()
    # # Example: create table if not exists
    # cur.execute("""
    #     CREATE TABLE IF NOT EXISTS messages (
    #         id SERIAL PRIMARY KEY,
    #         user_id TEXT,
    #         role TEXT,
    #         message TEXT,
    #         timestamp TIMESTAMPTZ DEFAULT now()
    #     );
    # """)
    # conn.commit()

    # # Example: insert a message
    # cur.execute(
    #     "INSERT INTO messages (user_id, role, text) VALUES (%s, %s, %s)",
    #     ("user123", "user", "Hello World")
    # )
    # conn.commit()

    # # Example: fetch last 5 messages
    # cur.execute("SELECT user_id, role, text, timestamp FROM messages ORDER BY id DESC LIMIT 5")
    # rows = cur.fetchall()
    # cur.close()
    # conn.close()

    # # Convert datetime to string
    # result = []
    # for row in rows:
    #     result.append({
    #         "user_id": row[0],
    #         "role": row[1],
    #         "text": row[2],
    #         "timestamp": row[3].isoformat() if row[3] else None
    #     })

    # return {
    #     "statusCode": 200,
    #     "body": json.dumps(result)
    # }

    # api_key = os.environ['DASHSCOPE_API_KEY']
    # print(f"API key: `{api_key}`")
    # return {
    #     "statusCode": 200,
    #     "body": api_key,
    # }

    conn = get_db_conn()

    # Get session_id from headers
    headers = event.get("headers", {})
    session_id = headers.get("x-session-id")

    # Retrieve the existing session data.
    session_id, session_data = get_session_data(conn, session_id)

    # Append a new user message
    # message = event.get("body", {}).get("message", "")
    # Parse body if it's a string
    body = event.get("body", "{}")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            # If not JSON, treat it as empty
            body = {}
    print(f"body: {json.dumps(body)}")
    message = body.get("message", "")
    print(f"message: {message}")
    if message:
        session_data["messages"].append({"role": "user", "content": message})

        # Send the user message with the previous contents to the LLM agent.
        response = generate_llm_response(session_data, api_type="dashscope")
        print("generate_llm_response() successfully finished!")
        session_data["messages"].append({"role": "assistant", "content": response})

        # Save the session data.
        save_session_data(conn, session_id, session_data)

        # Return session ID in header
        return {
            "statusCode": 200,
            "headers": {"x-session-id": session_id},
            "body": json.dumps(session_data),
        }

    # Return session ID in header
    return {
        "statusCode": 400,
        "headers": {"x-session-id": session_id},
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
# Database connection (cached to reduce Lambda cold-start)
# ---------------------------------------------------------------------------


# pylint produces: "W0212: Access to a protected member _conn of a client class (protected-access)"
def get_db_conn():
    """
    Get or create a cached PostgreSQL database connection.

    This function reuses a connection across multiple calls (e.g., in AWS Lambda)
    to reduce cold-start overhead. The connection is stored as a function attribute.

    Returns:
        psycopg2.extensions.connection: A live PostgreSQL database connection.
    """
    if not hasattr(get_db_conn, "_conn"):
        get_db_conn._conn = psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            dbname=os.getenv("PG_DB"),
        )
    return get_db_conn._conn


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def get_session_data(conn, session_id):
    """
    Retrieve or create a chat session in the database.

    If `session_id` is provided and exists, fetch the existing session data.
    If `session_id` is not provided or does not exist, create a new session
    for a guest user with an expiration timestamp 1 hour from now.

    Args:
        conn (psycopg2.extensions.connection): Active database connection.
        session_id (str | None): Existing session ID or None for new session.

    Returns:
        tuple: (session_id (str), session_data (dict)) if session exists or is created.
        dict: HTTP-style error dictionary if session_id was provided but not found:
            {
                "statusCode": 404,
                "body": json.dumps({"error": "Session not found"})
            }
    """
    cur = conn.cursor()

    if not session_id:
        # Generate a new session for guests
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        initial_data = {"messages": []}

        cur.execute(
            "INSERT INTO sessions (session_id, data, expires_at) VALUES (%s, %s, %s)",
            (session_id, json.dumps(initial_data), expires_at),
        )
        conn.commit()
        session_data = initial_data
    else:
        # Retrieve existing session
        cur.execute("SELECT data FROM sessions WHERE session_id = %s", (session_id,))
        row = cur.fetchone()
        if row:
            session_data = row[0]
        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Session not found"}),
            }

    cur.close()

    return session_id, session_data


def save_session_data(conn, session_id, session_data):
    """
    Update the stored session data for a given session ID.

    Args:
        conn (psycopg2.extensions.connection): Active database connection.
        session_id (str): The session ID to update.
        session_data (dict): The chat session data to store.

    Returns:
        None
    """
    cur = conn.cursor()

    cur.execute(
        "UPDATE sessions SET data = %s WHERE session_id = %s",
        (json.dumps(session_data), session_id),
    )
    conn.commit()

    cur.close()


def generate_llm_response(session_data, api_type="openai"):
    """
    Generate a response from a language model based on the current session.

    Args:
        session_data (dict): Current session data containing previous messages.
        api_type (str, optional): The type of API or model to use (default "openai").

    Returns:
        dict | str: The generated LLM response, format depends on implementation.
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        *session_data["messages"],
    ]
    print(f"messages: {json.dumps(messages)}")
    if api_type == "openai":
        # OpenAI Chat Completion: Mature community ecosystem. Offers the lowest cost for migrating existing applications
        # or integrating third-party tools.
        client = OpenAI(
            # If the environment variable is not set, replace the following line with: api_key="sk-xxx"
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            # The following is the base_url for the Singapore region.
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        completion = client.chat.completions.create(
            model="qwen-plus",  # Model list: https://www.alibabacloud.com/help/en/model-studio/getting-started/models
            messages=messages,
            # extra_body={"enable_thinking": False},
        )
        print(f"response type: {type(completion)}")
        print(completion.model_dump_json())
        return parse_response(completion, api_type)
    elif api_type == "dashscope":
        # DashScope: Native interface from Model Studio. Offers the most complete set of features and parameters.
        # This is the base URL for the Singapore region.
        dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        response = dashscope.Generation.call(
            # No DASHSCOPE_API_KEY set? Use api_key="sk-xxx" instead.
            # API keys differ by region. Get an API key: https://www.alibabacloud.com/help/zh/model-studio/get-api-key.
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            model="qwen-plus",  # Replace qwen-plus as needed — model list: https://www.alibabacloud.com/help/zh/model-studio/getting-started/models
            messages=messages,
            result_format="message",
        )
        print(f"response type: {type(response)}")
        print(response)
        return parse_response(response, api_type)
    raise ValueError(f"Unsupported api_type: {api_type}")


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
        # return response["output"]["choices"][0]["message"]["content"]
        return response.output.choices[0].message.content
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
