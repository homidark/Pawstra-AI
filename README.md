# Pawstra AI [warning this is beta version]

A ChatGPT-style desktop chat app built with Python and Tkinter. It supports OpenRouter, OpenAI, Claude, Qwen, DeepSeek, Grok, Gemini, and Ollama (offline).

## Start

1. Install Python 3.10 or later.
2. Double-click `installer.pyw` to open the five-stage forest setup window. It checks Python and Tkinter, scans app imports, installs missing third-party packages, verifies the app, and lets you launch it. The forest has a moving-forward camera and an original flying code-cat mascot. This project currently uses only Python's standard library, so no extra packages need to be downloaded. You can also double-click `start.pyw` to open the app directly or run `python main.py` from a terminal.
3. On first launch, **API & app settings** opens in the app. Choose a provider, paste its API key, then select **Test API**. The app checks available models and sends a short test message. A green success message enables **Save & continue**. Ollama can be selected instead for local/offline use.

The animated logo is bundled in `assets/ai_orbit.gif`; keep the `assets` folder beside `main.py` when moving the app. No additional runtime packages are currently needed.

API keys are entered and pasted directly in the app, masked by default, and encrypted with Windows DPAPI in your user AppData folder. Each provider requires its own key. OpenRouter can expose models from multiple vendors through one OpenRouter key. The API test sends a very short completion request, which may incur a small provider charge.

## Everyday chat

1. Select the provider and model from the selectors beside the message composer. Available cloud models are loaded from the selected provider. For Ollama, download or select a model that is already installed locally.
2. Type a message and press **Enter** or click **Send**. Use **Shift+Enter** for a new line. Responses appear in the conversation as they arrive. Click **+** to attach supported files before sending.
3. Use the sidebar to start a new conversation or revisit another conversation during the current app session. Conversation history is kept in memory while the app is running and is not automatically restored on a later launch.

The app supports ordinary Markdown-style text, fenced code blocks, and formatted tables. Code blocks use the selected theme. Response reveal speed can be adjusted in Developer mode; setting it to zero disables the word-by-word reveal delay. The app does not execute code or raw HTML from an assistant response.

### Prompt shortcuts

The default in-app keyboard shortcuts are:

| Action | Shortcut |
| --- | --- |
| Start a new chat | `Ctrl+Shift+N` |
| Clear the current chat | `Ctrl+L` |
| Show or restore the app | `Ctrl+Shift+Space` |

Shortcuts apply while the app is focused. Change them in **Developer mode** using Tk key syntax, for example `<Control-Shift-n>`. Each configured shortcut must be valid and unique.

Slash templates add an instruction to a message before it is sent. The defaults are `/code` for a runnable solution, `/fix` for root-cause diagnosis and a focused fix, and `/explain` for a step-by-step explanation. Customize the command-to-instruction map in Developer mode as a JSON object. Command names must begin with `/`, and each instruction must be a non-empty string. For example:

```json
{
  "/summarize": "Summarize the following in five concise bullet points.",
  "/review": "Review the following code for correctness and maintainability."
}
```

Type the slash command followed by your request, such as `/review check this function`. The special exact phrase `I feel lucky` instead creates a local 666-framed easter-egg response and is not sent to an AI provider.

## Settings

Use **API & app settings** at the bottom of the sidebar to test or change provider keys, choose a dark or light theme, and set the response-token limit. The limit accepts a number or `k` notation, such as `2048` or `2k`. Provider charges and maximum output limits are controlled by each vendor and model.

The provider, model, and access-mode selectors are beside the message composer. **Strict** (default) does not perform desktop actions. **Moderate** opens recognized apps, including installed apps found by Windows shortcuts. **Full access** asks once when enabled, then opens recognized apps without per-launch confirmation. The app does not execute typed commands or command arguments.

The Settings page's **Developer mode** button opens a separate advanced-settings screen after two confirmation prompts. It includes a masked API-key field for the selected provider (test a changed key before applying), custom assistant-style instructions, prompt templates, shortcuts, and the other advanced options. The **Apply** button stays visible: it is gray with white text when there are no unsaved changes, and turns purple with white text and becomes clickable after a setting changes.

### Developer mode reference

Developer mode groups less frequently used options into sections:

- **Shortcuts & prompts:** set the three in-app shortcuts and edit the slash-template JSON.
- **Web search & profile:** optionally enable automatic web search, configure a search key, and write custom assistant instructions. Personal instructions are added to the built-in assistant style; they do not replace it. The selected provider's API key is also available here and remains masked.
- **Code & output:** choose a code-block color theme, enable table formatting, and set response reveal speed. Raw HTML execution and LaTeX rendering are not available; those options remain disabled.
- **Network & context:** set an HTTP, HTTPS, or SOCKS5 proxy, request timeout, custom request headers, and approximate auto-summarization threshold. A zero threshold disables automatic summarization. Summarization condenses older context for a request without deleting the visible chat messages.
- **Audio preferences:** store preferences for a speech engine, such as an endpoint, model path, and voice. The app does not bundle microphone transcription or speech playback, so saving these values does not activate audio input or output.
- **Backup & inspector:** choose whether to create scheduled conversation backups, select the backup folder and schedule, show the optional cat companion, and enable the in-memory request inspector. The inspector keeps up to 100 recent request records and can include message text.

Changing the selected provider's API key in Developer mode requires a successful **Test API** before **Apply** will save it. Search and speech keys are optional and separate from the AI provider key. The Apply button validates settings such as the proxy URL, request timeout, summary threshold, prompt-template JSON, and shortcut syntax. If validation fails, read the status message, correct the value, and apply again.

API test results are color-coded: green **SUCCESS!** means the test message received a response; yellow **LIMITED** indicates quota, credit, or permission trouble; red **FAILED!** indicates an invalid key, unavailable API, or another error.

## Offline models

Install and start [Ollama](https://ollama.com/download), choose **Ollama (Offline)** in the provider menu, then select **Get offline model** and enter a model name such as `llama3.2:3b`. Downloaded models run locally through Ollama.

## Attachments

Select **+** beside the message box to attach PNG, JPEG, or WebP images, or UTF-8 text/code files. Images are limited to 10 MB each and text files to 2 MB each. Attachments are included when the message is sent to the selected provider; use Ollama to keep supported images and text local. Vision support depends on the selected model.

## Data, privacy, and safety

- Cloud prompts and attachments go to the selected provider. Review its privacy policy before sending sensitive information. Ollama can process supported content locally.
- API keys are masked and encrypted with Windows DPAPI. The optional inspector is in-memory, may contain message text, and is not saved to disk.
- Backups and exports can contain conversation content. Store them in a location you trust and remove exported copies when no longer needed. Backups are not a chat-history restore feature.
- App control is limited to opening recognized applications. The app does not run arbitrary shell commands or command arguments. Full access removes the per-app confirmation only after you explicitly accept its warning when enabling that mode.
- Web searches send the search query to the configured search service. A blank search key uses DuckDuckGo's public HTML results; a Tavily key uses Tavily.

## Requirements and troubleshooting

- Python 3.10 or later with Tkinter.
- No extra Python packages are needed for cloud providers.
- If `python` is not recognized, install Python and enable **Add Python to PATH**.
- If Ollama cannot connect, make sure the Ollama app/service is running.
- A successful key check does not guarantee sufficient account credits for normal usage; check the provider account if the test reports **LIMITED**.
- If a provider's models do not appear, verify the provider selection and internet connection, then reopen Settings and run **Test API**. Some providers restrict model-list access independently of chat access.
- If an API request times out, check your connection, provider status, proxy settings, and request-timeout value. The allowed timeout is 5 to 600 seconds.
- If **Apply** reports invalid settings, inspect the displayed error. Common causes include malformed prompt-template JSON, duplicate shortcuts, an invalid proxy address, or a timeout outside the allowed range.
- If an attachment is rejected, confirm it is a supported image or text/code extension, is under the per-file size limit, and that text files use UTF-8 encoding.
- If a backup or export fails, check that the destination folder exists and that Windows allows the app to write there.
- If the animated logo does not appear after moving the project, restore the `assets` directory next to `main.py`.
