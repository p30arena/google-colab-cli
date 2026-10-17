# Windows SSH verification

This branch fixes native Windows SSH transport while keeping POSIX quoting and
the remote Linux shell unchanged. It does not claim full Windows support for
all Colab CLI commands.

## Changes

- Use `subprocess.list2cmdline` when generating a Windows OpenSSH ProxyCommand;
  POSIX continues to use `shlex.join`.
- Put Windows CRT stdin/stdout descriptors into binary mode before forwarding
  SSH bytes, preserving CR/LF and Ctrl-Z.
- Use `os.devnull` for the local known-hosts sink.
- Register only cleanup signals available on the host platform.

The quoting and signal issues were also documented in
[Le-Anh-Duy's discussion #97](https://github.com/googlecolab/google-colab-cli/discussions/97).
That discussion and its fork were design references. Current upstream already
removed `select()` on stdin and made console imports portable; those fixes are
not duplicated here. Broader Windows work exists in
[PR #167](https://github.com/googlecolab/google-colab-cli/pull/167).

## Offline checks

Base: upstream `006ff96ac2d0e4dcfb702467a76493d687929be8`.
Native Windows, Python 3.12.14; no WSL.

Eight new regression cases fail against the unmodified base and pass with this
patch. Tests cover native CommandLineToArgvW round trips with executable/key
paths containing spaces, quotes and literal shell metacharacters; unavailable
SIGHUP; the local null device; binary stream configuration; and a real subprocess
pipe carrying every byte value, including CR/LF/Ctrl-Z.

The SSH-focused suite passes 100 tests, including real loopback WebSocket
handshake/header contracts. The full suite still has unrelated upstream Windows
failures: 347 passed, 15 failed, 2 skipped on this branch. The same 15 failures
reproduce on the unmodified base (333 passed, 21 failed, 2 skipped): two help-order
assertions, two temporary-file editor-locking cases, and eleven headless REPL
console cases. This patch fixes six upstream SSH failures and adds eight passing
Windows regression cases. Changed test files pass Ruff. The five transport helper
bodies were AST-compared with the previously live-tested checkout and match
after excluding type annotations.

## Prior live integration check

[Machine-readable evidence](windows-ssh-live-result.json) records the completed
2026-10-17 test using Windows OpenSSH and the patched CLI WebSocket ProxyCommand:

- A temporary CPU runtime returned `root`, `Linux`, and a unique success marker.
- SCP uploaded and downloaded 4,096 bytes containing every possible byte value.
- The round-trip SHA256 was
  `c8f5d0341d54d951a71b136e6e2afcb14d11ed8489a7ae126a8fee0df6ecf193`.
- All three operations exited 0 without stderr.
- The temporary runtime was terminated and a subsequent server inventory was empty.

The tested transport implementation is identical to this publication branch;
this branch omits the original patch's unrelated type-hint modernization and
local workflow notes. No new Colab runtime was created for publication validation,
and no existing runtime was operated. Interactive terminal ergonomics and all
other CLI commands are outside this evidence.

## Publishing scope

Upstream currently declines external pull requests in CONTRIBUTING.md. This
patch is therefore published on a fork for review and use, rather than opening
another unsolicited upstream Windows PR. No credentials, OAuth history, SSH
private keys, local cache contents, or unrelated project data are included.
