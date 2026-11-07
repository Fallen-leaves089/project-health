# Contributing

[中文](CONTRIBUTING.md) | **English**

Thank you for improving this skill package. It is built for real project health checks, so the most valuable contributions are usually not another pretty checklist. They are:

- a reproducible environment trap (command, error, workaround, and verification result)
- a negative case that proves a guard script can actually fail
- a workflow change that reduces false negatives

## Issues

Use a prefix in the title:

- `[Bug]`: a workflow, script, or documentation error
- `[Pitfall]`: a new Windows or cross-platform environment trap
- `[Feature]`: a new review dimension or reporting capability
- `[Security]`: a possible sanitization leak (do not paste the sensitive value)

Please include:

1. the trigger scenario
2. actual behavior
3. expected behavior
4. the smallest reproduction command or steps
5. the environment (OS, PowerShell version, relevant tool versions)

## Pull requests

- Keep changes small and solve one problem per change.
- Update `CHANGELOG.md` when behavior changes.
- When adding a pitfall, document "trap / workaround / verification", not just the conclusion.
- Every new guard script must include positive and negative cases. A guard that only reports green is not accepted.
- Run the verifier before submitting:

  ```bash
  python -B -m unittest discover -s tests -p "test_*.py"
  python3 scripts/verify_package.py
  ```

  On Windows you can also run:

  ```powershell
  python -B -m unittest discover -s tests -p "test_*.py"
  python scripts\verify_package.py
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-package.ps1
  ```

- Do not commit personal absolute paths, real usernames, project or client names, domains, private IPs, secrets, or unsanitized logs.
- All text files must be UTF-8 without BOM.

## License and contribution grant

This project uses the PolyForm Noncommercial License 1.0.0. By submitting a contribution, you agree that:

- your contribution is provided under the same license and may be used, modified, and distributed for noncommercial purposes
- you retain copyright in your contribution but do not gain a commercial license to the project
- commercial licensing remains a separate written agreement between the project author and the user; see `COMMERCIAL.en.md`

If you do not want to grant contributions on these terms, please do not submit a pull request. Open an issue first to discuss alternatives.

## Code of conduct

- Focus on reproducible facts, not people.
- Do not publish anyone else's secrets, customer data, or unsanitized logs.
- Do not treat "it works on my machine" as "it works everywhere"; include the environment and command.
