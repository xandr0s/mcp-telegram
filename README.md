<div align="center">
  <img src="logo.png" alt="MCP Telegram Logo" width="150"/>
  <h2 style="margin-top: 0">Enable LLMs to control your Telegram</h2>
</div>

<div align="center">
    <a href="https://github.com/dryeab/mcp-telegram/stargazers"><img src="https://img.shields.io/github/stars/dryeab/mcp-telegram?style=social" alt="GitHub stars"></a>
    <a href="https://badge.fury.io/py/mcp-telegram"><img src="https://badge.fury.io/py/mcp-telegram.svg" alt="PyPI version"></a>
    <a href="https://x.com/dryeab"><img src="https://img.shields.io/twitter/follow/dryeab?style=social" alt="Twitter Follow"></a>
</div>
<h3></h3>

**Connect Large Language Models to Telegram via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction).**

Built with [Telethon](https://github.com/LonamiWebs/Telethon), this server allows AI agents to interact with Telegram, enabling features like sending/editing/deleting messages, searching chats, managing drafts, downloading media, and more using the [MTProto](https://core.telegram.org/mtproto).

---
<details>
<summary><strong>Table&nbsp;of&nbsp;Contents</strong></summary>

- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [⚙️ Usage](#️-usage)
  - [Login](#login)
  - [Connect to the MCP server](#connect-to-the-mcp-server)
- [🧰 Available Tools](#-available-tools)
  - [📨 Messaging Tools](#-messaging-tools)
  - [🔍 Search & Navigation](#-search--navigation)
  - [📝 Draft Management](#-draft-management)
  - [📂 Media Handling](#-media-handling)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)

</details>

---


## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- [`uv`](https://github.com/astral-sh/uv) Install via the [official uv guide](https://github.com/astral-sh/uv#installation).

### Installation

Install the `mcp-telegram` CLI tool:

```bash
uv tool install mcp-telegram
```

## ⚙️ Usage

> [!IMPORTANT]
> Please ensure you have read and understood Telegram's [ToS](https://telegram.org/tos) before using this tool. Misuse of this tool may result in account restrictions.

The `mcp-telegram` command-line tool is your entry point.

```bash
mcp-telegram --help # See all commands
```

### Login

First, authenticate with your Telegram account:

```bash
mcp-telegram login
```

This interactive command will prompt you for:

- **API ID & API Hash:** Obtain these from [my.telegram.org/apps](https://my.telegram.org/apps).
- **Phone Number:** Your Telegram-registered phone number (international format, e.g., `+1234567890`).
- **Verification Code:** Sent to your Telegram account upon first login.
- **2FA Password:** If you have Two-Factor Authentication enabled.

Your credentials are securely stored in the session file for future use.

> [!WARNING]
> Keep your API credentials private and never share them publicly

> [!NOTE]
> Use `mcp-telegram logout` to logout from current session or `mcp-telegram clear-session` to remove all stored session data.

### Connect to the MCP server

To use MCP Telegram with MCP clients like Claude Desktop or Cursor, you'll need to configure the MCP server. The configuration process varies by client and operating system.

For detailed setup instructions, please refer to:

- [Claude Desktop MCP Setup Guide](https://modelcontextprotocol.io/quickstart/user)
- [Cursor MCP Documentation](https://docs.cursor.com/context/model-context-protocol)

The configuration file should contain:

```json
{
  "mcpServers": {
    "mcp-telegram": {
      "command": "mcp-telegram" /* Use full path if client can't find the command (e.g. "/usr/local/bin/mcp-telegram"). See IMPORTANT section below for full path instructions. */,
      "args": ["start"],
      "env": {
        "API_ID": "<your_api_id>",
        "API_HASH": "<your_api_hash>"
      }
    }
  }
}
```

> [!Note]
> Configuration paths vary by OS and client. For example:
>
> - macOS: `~/Library/Application Support/Claude/` or `~/.cursor/`
> - Windows: `%APPDATA%\Claude\` or `%APPDATA%\Cursor\`

> [!IMPORTANT]
> If your client cannot execute `mcp-telegram` despite it being accessible in the terminal, try using the full path to the executable. You can find this by running `which mcp-telegram` (macOS/Linux) or `where mcp-telegram` (Windows) in your terminal. Replace the `command` value in the configuration with the full path.

After saving the configuration file, restart your application.

## 🧰 Available Tools

Here's a comprehensive list of tools you can use to interact with Telegram through MCP:

### 📨 Messaging Tools

| Tool             | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| `send_message`   | ✉️ Send text messages or files to any user, group, or channel |
| `edit_message`   | ✏️ Modify content of previously sent messages                 |
| `delete_message` | 🗑️ Remove one or multiple messages                            |
| `get_messages`   | 📜 Retrieve message history with advanced filtering options   |

### Group member tags

`set_member_tag(entity, member, tag, dry_run=True)` sets a group member's tag
using the connected Telegram account. It does not promote the member or change
administrator rights. Supports basic groups and supergroups.

- `entity`: group username or marked Telegram chat ID (as a string).
- `member`: user username or numeric user ID (as a string).
- `tag`: up to 16 characters; Telegram does not allow emoji. An empty string
  removes the tag. Telegram validates the final tag and permissions.
- `dry_run`: defaults to `true`. Resolves the group and user and returns their
  numeric IDs without writing. This preview does not verify membership or rights.
  Set `false` only after the user approves the exact group, member and tag.

To modify another member's tag, the connected account needs the `manage_ranks`
administrator right. Resolution and Telegram RPC errors are returned to the caller;
failed requests are not reported as successful. Unknown numeric user IDs may need
resolving through a username first, as Telegram also requires an access hash.

Example preview:

```json
{"entity": "@deckhouse_ru", "member": "@employee", "tag": "Флант"}
```

The result contains `chat_id`, `user_id`, `tag`, and `applied`. After reviewing the
preview, call with the returned numeric IDs as strings and `dry_run: false` to
apply. To remove the tag, use the same call with `tag: ""`.

### 🔍 Search & Navigation

| Tool                | Description                                             |
| ------------------- | ------------------------------------------------------- |
| `search_dialogs`    | 🔎 Find users, groups, and channels by name or username |
| `message_from_link` | 🔗 Access specific messages using Telegram links        |

### 📝 Draft Management

| Tool        | Description                                |
| ----------- | ------------------------------------------ |
| `get_draft` | 📋 View current message draft for any chat |
| `set_draft` | ✍️ Create or clear message drafts          |

### 📂 Media Handling

| Tool             | Description                                             |
| ---------------- | ------------------------------------------------------- |
| `media_download` | 📸 Download photos, videos, and documents from messages |

> [!Note]
> For detailed parameter information and example use cases, run `mcp-telegram tools` in your terminal.

## 🛠️ Troubleshooting

### Database Locked Errors

Running multiple `mcp-telegram` instances using the _same session file_ can cause `database is locked` errors due to Telethon's SQLite session storage. Ensure only one instance uses a session file at a time.

<details>
<summary>Force-Stopping Existing Processes</summary>

If you need to stop potentially stuck processes:

- **macOS / Linux:** `pkill -f "mcp-telegram"`
- **Windows:** `taskkill /F /IM mcp-telegram.exe /T` (Check Task Manager for the exact process name)

</details>

## 🤝 Contributing

We welcome contributions! If you'd like to help improve MCP Telegram, please feel free to submit issues, feature requests, or pull requests. Your feedback and contributions help make this project better for everyone.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>Made with ❤️ by <a href="https://x.com/dryeab">Yeabsira Driba</a></p>
</div>

### Read supergroup members

`list_chat_members(entity, offset=0, limit=200)` reads one membership page using
only Telegram read requests. It returns IDs, names, usernames and active aliases,
visible phone numbers, bot/deleted flags and member tags. Advance `offset` by
`returned_count`. To establish completeness, compare unique IDs with `total` and
`participants_count`; hidden members or insufficient rights may limit visibility.

### Resolve an account by phone

`resolve_phone(phone)` accepts an international number in `+digits` format.
It uses `contacts.resolvePhone` without importing contacts or sending messages.
The result has status `found`, `not_found`, or `rate_limited`; a found result
includes the account ID, name, username and active aliases. Privacy settings may
prevent a match. Requests are serialized with a three-second delay, and a
`rate_limited` result includes `retry_after` seconds.
