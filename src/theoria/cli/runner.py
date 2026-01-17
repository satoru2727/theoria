from __future__ import annotations

import asyncio
import signal
import sys
from typing import TYPE_CHECKING, Any

from theoria.cli.display import GOODBYE_MSG, INTERRUPTED_MSG
from theoria.errors import (
    AuthenticationError,
    LLMError,
    NetworkError,
    RateLimitError,
    format_auth_error,
    format_llm_error,
    format_network_error,
    format_rate_limit_error,
)

if TYPE_CHECKING:
    from rich.console import Console

    from theoria.cli.sessions.base import BaseSession


def run_session(session: BaseSession[Any], console: Console) -> None:
    async def main() -> None:
        await session.run()

    def signal_handler(_sig: int, _frame: object) -> None:
        console.print(INTERRUPTED_MSG)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print(GOODBYE_MSG)
    except AuthenticationError as e:
        console.print(format_auth_error(e.provider))
        sys.exit(1)
    except RateLimitError as e:
        console.print(format_rate_limit_error(e.retry_after))
        sys.exit(1)
    except NetworkError as e:
        console.print(format_network_error(e))
        sys.exit(1)
    except LLMError as e:
        console.print(format_llm_error(e))
        sys.exit(1)
