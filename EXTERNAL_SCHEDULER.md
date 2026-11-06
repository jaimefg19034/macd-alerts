# External scheduler for MACD alerts

This repository already supports `workflow_dispatch` in `.github/workflows/macd-alerts.yml`. An external scheduler can call GitHub's workflow-dispatch API every five minutes, while the existing GitHub schedule remains enabled as a backup.

## 1. Create a narrowly scoped GitHub token

1. Open https://github.com/settings/personal-access-tokens/new
2. Choose **Fine-grained token**.
3. Give it a name such as `macd-external-scheduler`.
4. Set an expiry date (for example, 90 days; renew it before it expires).
5. Under **Resource owner**, select your GitHub account.
6. Under **Repository access**, choose **Only select repositories** and select `macd-alerts`.
7. Under **Repository permissions**, set **Actions: Read and write**. Leave all other permissions at **No access**.
8. Generate the token and copy it once. Treat it like a password. Do not paste it into chat, a GitHub issue, or the repository.

## 2. Create the free external schedule

1. Create/sign in to an account at https://cron-job.org/.
2. Create a new cron job.
3. Set the title to `MACD GitHub Actions trigger`.
4. Set the URL to:

   `https://api.github.com/repos/jaimefg19034/macd-alerts/actions/workflows/macd-alerts.yml/dispatches`

5. Set the request method to **POST**.
6. Add these custom headers:

   - `Accept` = `application/vnd.github+json`
   - `Authorization` = `Bearer YOUR_FINE_GRAINED_TOKEN` (replace the placeholder with the token; do not include angle brackets)
   - `X-GitHub-Api-Version` = `2022-11-28`
   - `Content-Type` = `application/json`

7. Set the request body to:

   `{"ref":"main"}`

8. Set the schedule to every 5 minutes (`*/5 * * * *`) and enable the job.
9. Run a test execution once. A successful GitHub dispatch normally returns HTTP **204**. Then check the repository's **Actions** tab for a new `MACD hourly alerts` run with event **workflow_dispatch**.

## 3. Important notes

- Keep the existing GitHub `schedule` trigger enabled as a backup.
- The script tracks processed hourly candle timestamps, so repeated five-minute checks should not resend the same signal.
- The external scheduler is also best-effort; it can be delayed and does not guarantee exact timing.
- If the GitHub token expires or is revoked, the external requests will stop triggering runs. Replace the token in cron-job.org, not in this repository.
- Never commit the token or add it to the repository's files or GitHub Actions logs.
